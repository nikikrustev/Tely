# Runs in CI with no Azure SDKs and no keys: the synthesiser is faked.
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def smoke():
    spec = importlib.util.spec_from_file_location("smoke_azure", ROOT / "scripts" / "smoke_azure.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_package_imports():
    import tely  # noqa: F401


def test_load_env_parses_and_ignores_comments(smoke, tmp_path):
    p = tmp_path / ".env"
    p.write_text('# c\nTTS_VOICE="en-US-Andrew:DragonHDLatestNeural"\nEMPTY=\nnot a line\n', encoding="utf-8")
    assert smoke.load_env(p) == {"TTS_VOICE": "en-US-Andrew:DragonHDLatestNeural", "EMPTY": ""}
    assert smoke.load_env(tmp_path / "missing") == {}


def test_redact_hides_key_and_tokens(smoke):
    env = {"SPEECH_KEY": "abc123secret"}
    msg = smoke.redact("bad key abc123secret, token eyJhbGc.eyJzdWIi.c2ln", env)
    assert "abc123secret" not in msg and "eyJ" not in msg


def test_no_config_skips_both_checks(smoke, tmp_path, capsys):
    assert smoke.run({}, tmp_path) == 1
    out = capsys.readouterr().out
    assert "Speech: SKIP" in out and "Model: SKIP" in out


class _FakeSdk:
    """Just enough of azure.cognitiveservices.speech for _synthesise()."""

    SpeechSynthesisOutputFormat = SimpleNamespace(Audio24Khz48KBitRateMonoMp3="mp3")
    ResultReason = SimpleNamespace(SynthesizingAudioCompleted="done")

    def __init__(self, fail_keyless=False):
        self.fail_keyless = fail_keyless
        self.configs = []
        self.audio = SimpleNamespace(AudioOutputConfig=lambda filename: SimpleNamespace(filename=filename))

    def SpeechConfig(self, **kw):
        cfg = SimpleNamespace(kw=kw, set_speech_synthesis_output_format=lambda fmt: None)
        self.configs.append(cfg)
        return cfg

    def SpeechSynthesizer(self, speech_config, audio_config):
        keyless = "token_credential" in speech_config.kw

        def speak(text):
            if keyless and self.fail_keyless:
                err = SimpleNamespace(reason="Error", error_details="401 Unauthorized")
                return SimpleNamespace(get=lambda: SimpleNamespace(reason="canceled", cancellation_details=err))
            Path(audio_config.filename).write_bytes(b"\xff" * 2048)
            return SimpleNamespace(get=lambda: SimpleNamespace(reason="done"))

        return SimpleNamespace(speak_text_async=speak)


ENV = {"TTS_VOICE": "en-US-Andrew:DragonHDLatestNeural", "SPEECH_ENDPOINT": "https://x.cognitiveservices.azure.com/"}


def test_speech_keyless_first(smoke, tmp_path, monkeypatch):
    sdk = _FakeSdk()
    monkeypatch.setattr(smoke, "_load_speech_sdk", lambda: sdk)
    monkeypatch.setattr(smoke, "_credential", lambda: object())
    status, detail = smoke.check_speech(ENV, tmp_path)
    assert status == "PASS" and detail.startswith("keyless")
    assert (tmp_path / "smoke.mp3").stat().st_size > 1024


def test_speech_falls_back_to_key_and_never_prints_it(smoke, tmp_path, monkeypatch, capsys):
    sdk = _FakeSdk(fail_keyless=True)
    monkeypatch.setattr(smoke, "_load_speech_sdk", lambda: sdk)
    monkeypatch.setattr(smoke, "_credential", lambda: object())
    env = {**ENV, "SPEECH_KEY": "s3cr3t-value"}
    status, detail = smoke.check_speech(env, tmp_path)
    assert status == "PASS" and detail.startswith("key auth")
    assert "s3cr3t-value" not in detail + capsys.readouterr().out
