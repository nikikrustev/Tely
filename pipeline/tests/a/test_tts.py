# OWNER: A (potencialbg). TTS cache, Azure synthesiser and voice samples, with the Speech SDK faked: no Azure in CI.
from datetime import timedelta
from types import SimpleNamespace

import pytest

from tely import voices
from tely.commentary import tts

TOO_MANY = "too_many"


class FakeSdk:
    """Just enough of azure.cognitiveservices.speech for AzureSynthesiser."""

    SpeechSynthesisOutputFormat = SimpleNamespace(Audio24Khz48KBitRateMonoMp3="mp3")
    ResultReason = SimpleNamespace(SynthesizingAudioCompleted="done")
    CancellationErrorCode = SimpleNamespace(TooManyRequests=TOO_MANY)

    def __init__(self, throttle=0, fail_keyless=False):
        self.throttle, self.fail_keyless, self.spoken = throttle, fail_keyless, []

    def SpeechConfig(self, **kw):
        return SimpleNamespace(kw=kw, set_speech_synthesis_output_format=lambda fmt: None)

    def SpeechSynthesizer(self, speech_config, audio_config):
        keyless = "token_credential" in speech_config.kw

        def speak(ssml):
            if keyless and self.fail_keyless:
                d = SimpleNamespace(reason="Error", error_code="auth", error_details="401 Unauthorized")
                return SimpleNamespace(get=lambda: SimpleNamespace(reason="canceled", cancellation_details=d))
            if self.throttle:
                self.throttle -= 1
                d = SimpleNamespace(reason="Error", error_code=TOO_MANY, error_details="429 Too many requests")
                return SimpleNamespace(get=lambda: SimpleNamespace(reason="canceled", cancellation_details=d))
            self.spoken.append((keyless, ssml))
            ok = SimpleNamespace(reason="done", audio_data=b"ID3" + b"\0" * 64, audio_duration=timedelta(seconds=1.5))
            return SimpleNamespace(get=lambda: ok)

        return SimpleNamespace(speak_ssml_async=speak)


ENV = {"SPEECH_ENDPOINT": "https://x.cognitiveservices.azure.com/"}


def test_keyless_first():
    sdk = FakeSdk()
    syn = tts.AzureSynthesiser(ENV, sdk=sdk, credential=lambda: object(), sleep=lambda s: None)
    audio, secs = syn.synthesise("<speak/>")
    assert audio.startswith(b"ID3") and secs == 1.5 and syn.auth == "keyless" and sdk.spoken[0][0] is True


def test_429_retries_with_backoff():
    slept = []
    syn = tts.AzureSynthesiser(ENV, sdk=FakeSdk(throttle=2), credential=lambda: object(), sleep=slept.append)
    syn.synthesise("<speak/>")
    assert slept == [1, 2]


def test_key_fallback_never_leaks_the_key():
    env = {**ENV, "SPEECH_KEY": "s3cr3t-value"}
    sdk = FakeSdk(fail_keyless=True)
    syn = tts.AzureSynthesiser(env, sdk=sdk, credential=lambda: object(), sleep=lambda s: None)
    syn.synthesise("<speak/>")
    assert syn.auth == "key" and sdk.spoken[0][0] is False

    class Broken(FakeSdk):
        def SpeechConfig(self, **kw):
            raise RuntimeError(f"bad config {kw.get('subscription', '')} eyJhbGc.eyJzdWIi.c2ln")

    with pytest.raises(tts.TtsError) as err:
        tts.AzureSynthesiser(env, sdk=Broken(), credential=lambda: object()).synthesise("<speak/>")
    assert "s3cr3t-value" not in str(err.value) and "eyJ" not in str(err.value)


def test_no_endpoint_or_key_is_a_clear_error():
    with pytest.raises(tts.TtsError, match="SPEECH_ENDPOINT"):
        tts.AzureSynthesiser({}, sdk=FakeSdk())


def test_cache_renders_each_hash_once_and_persists(tmp_path):
    calls = []

    class Syn:
        def synthesise(self, ssml):
            calls.append(ssml)
            return b"ID3", 2.0

    cache = tts.TtsCache(tmp_path, lambda: Syn())
    assert cache.ensure("abc", "<speak>a</speak>", "a") == 2000
    assert cache.ensure("abc", "<speak>a</speak>", "a") == 2000
    assert len(calls) == 1 and (tmp_path / "abc.mp3").is_file()
    again = tts.TtsCache(tmp_path, lambda: pytest.fail("must not connect when everything is cached"))
    assert again.has("abc") and again.duration_ms("abc") == 2000
    assert "\r" not in (tmp_path / "index.json").read_text(encoding="utf-8")


def test_voice_samples_three_voices_four_lines(tmp_path):
    picked = voices.pick_voices({"TTS_VOICE": "en-US-Brian:DragonHDLatestNeural"}, None)
    assert len(picked) == 3 == len(set(picked)) and picked[0] == "en-US-Brian:DragonHDLatestNeural"
    assert all(v.startswith("en-US-") and ":DragonHD" in v for v in picked)

    class Syn:
        calls = 0

        def synthesise(self, ssml):
            Syn.calls += 1
            return b"ID3", 1.0

    written, cache = voices.render(picked, tmp_path, lambda: Syn())
    assert len(written) == 12 and all(p.is_file() for p in written)
    assert {p.name.split("_", 1)[1] for p in written} == {"1_buildup.mp3", "2_goal.mp3", "3_miss.mp3", "4_state.mp3"}
    _, cache2 = voices.render(picked, tmp_path, lambda: Syn())
    assert Syn.calls == 12 and cache2.calls == 0
