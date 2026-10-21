"""Pre-synthesise SSML to MP3 with Azure Speech, cached by SSML sha256. OWNER: A (potencialbg).

HD voices are real-time only (no batch), so we render line by line in an SDK loop (file 43 §7). An existing hash is
never re-synthesised, so a rebuild makes 0 TTS calls and the replay always sounds the same.
Auth is keyless first (DefaultAzureCredential), then SPEECH_KEY from .env. Keys and tokens are never printed or logged.
The Azure SDK is imported lazily, so CI (which never installs requirements-azure.txt) can import this module.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

ROOT = Path(__file__).resolve().parents[3]
INSTALL_HINT = 'pip install -e "pipeline[dev]" -r pipeline/requirements-azure.txt'
_JWT = re.compile(r"eyJ[\w-]+\.[\w-]+\.[\w-]+")
RETRY_DELAYS_S = (1, 2, 4, 8, 16, 32)  # 429 backoff (file 43 §7); F0 allows 20 transactions per 60 s


class Synthesiser(Protocol):
    def synthesise(self, ssml: str) -> tuple[bytes, float]:
        """Return (mp3 bytes, duration in seconds)."""


class TtsError(RuntimeError):
    pass


def load_env(path: Path = ROOT / ".env") -> dict[str, str]:
    """KEY=VALUE lines from .env, overlaid by matching process env vars. Values are never printed."""
    env: dict[str, str] = {}
    if path.is_file():
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    env.update({k: v for k, v in os.environ.items() if k.startswith(("SPEECH_", "TTS_"))})
    return env


def redact(text: str, env: dict[str, str]) -> str:
    key = env.get("SPEECH_KEY")
    if key:
        text = text.replace(key, "***")
    return _JWT.sub("***", text)


def _load_sdk() -> Any:
    import azure.cognitiveservices.speech as speechsdk

    return speechsdk


def _credential() -> Any:
    from azure.identity import DefaultAzureCredential

    return DefaultAzureCredential()


class AzureSynthesiser:
    """One reused SpeechSynthesizer with MP3 output (file 39 pre-synthesis cache), keyless first."""

    def __init__(self, env: dict[str, str] | None = None, *, sdk: Any = None, credential: Callable[[], Any] = _credential,
                 sleep: Callable[[float], None] = time.sleep):
        self.env = env if env is not None else load_env()
        self.sleep = sleep
        try:
            self.sdk = sdk or _load_sdk()
        except ImportError as exc:
            raise TtsError(f"Speech SDK not installed: {INSTALL_HINT}") from exc
        endpoint, key, region = (self.env.get(k, "") for k in ("SPEECH_ENDPOINT", "SPEECH_KEY", "SPEECH_REGION"))
        self._configs: list[tuple[str, Callable[[], Any]]] = []
        if endpoint:
            # WHY: Learn "Microsoft Entra authentication with the Speech SDK": token_credential + custom-domain endpoint.
            self._configs.append(("keyless", lambda: self.sdk.SpeechConfig(token_credential=credential(), endpoint=endpoint)))
        if key:
            self._configs.append(("key", lambda: self.sdk.SpeechConfig(subscription=key, endpoint=endpoint) if endpoint
                                  else self.sdk.SpeechConfig(subscription=key, region=region)))
        if not self._configs:
            raise TtsError("SPEECH_ENDPOINT missing from .env (or SPEECH_KEY + SPEECH_REGION for the key fallback)")
        self._synth: Any = None
        self.auth = ""

    def _connect(self, label: str, make: Callable[[], Any]) -> None:
        cfg = make()
        cfg.set_speech_synthesis_output_format(self.sdk.SpeechSynthesisOutputFormat.Audio24Khz48KBitRateMonoMp3)
        self._synth = self.sdk.SpeechSynthesizer(speech_config=cfg, audio_config=None)
        self.auth = label

    def _throttled(self, details: Any) -> bool:
        code = getattr(details, "error_code", None)
        too_many = getattr(getattr(self.sdk, "CancellationErrorCode", None), "TooManyRequests", object())
        return code == too_many or "429" in str(getattr(details, "error_details", ""))

    def synthesise(self, ssml: str) -> tuple[bytes, float]:
        reasons = []
        configs = self._configs if self._synth is None else [(self.auth, None)]
        for label, make in configs:
            if make is not None:
                try:
                    self._connect(label, make)
                except Exception as exc:  # credential errors vary by environment; try the next auth method
                    reasons.append(f"{label}: {type(exc).__name__}: {exc}")
                    continue
            for attempt, delay in enumerate((0, *RETRY_DELAYS_S)):
                if delay:
                    self.sleep(delay)
                result = self._synth.speak_ssml_async(ssml).get()
                if result.reason == self.sdk.ResultReason.SynthesizingAudioCompleted:
                    return bytes(result.audio_data), result.audio_duration.total_seconds()
                details = result.cancellation_details
                if not self._throttled(details):
                    reasons.append(f"{label}: {getattr(details, 'reason', '?')}: {getattr(details, 'error_details', '')}")
                    break
            else:
                reasons.append(f"{label}: still throttled after {len(RETRY_DELAYS_S)} retries")
            self._synth = None  # this auth method failed; let the next one connect
        raise TtsError(redact("; ".join(reasons), self.env))


@dataclass
class TtsCache:
    """MP3 files named <ssml sha256>.mp3 in one folder, plus index.json with each file's real duration."""

    folder: Path
    synth_factory: Callable[[], Synthesiser]
    calls: int = 0
    chars_text: int = 0
    chars_ssml: int = 0
    _synth: Synthesiser | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        idx = self.folder / "index.json"
        self.index: dict[str, dict] = json.loads(idx.read_text(encoding="utf-8")) if idx.is_file() else {}

    def has(self, sha: str) -> bool:
        return sha in self.index and (self.folder / f"{sha}.mp3").is_file()

    def duration_ms(self, sha: str) -> int | None:
        return self.index[sha]["duration_ms"] if self.has(sha) else None

    def ensure(self, sha: str, ssml: str, text: str) -> int:
        """Render ssml unless its hash is already cached. Returns the real duration in ms."""
        if self.has(sha):
            return self.index[sha]["duration_ms"]
        if self._synth is None:
            self._synth = self.synth_factory()  # only connect to Azure if something is actually missing
        audio, seconds = self._synth.synthesise(ssml)
        self.calls += 1
        self.chars_text += len(text)
        self.chars_ssml += len(ssml)
        (self.folder / f"{sha}.mp3").write_bytes(audio)
        self.index[sha] = {"duration_ms": round(seconds * 1000), "bytes": len(audio), "text": text}
        self.save()
        return self.index[sha]["duration_ms"]

    def save(self) -> None:
        body = json.dumps(dict(sorted(self.index.items())), indent=1, ensure_ascii=False) + "\n"
        (self.folder / "index.json").write_text(body, encoding="utf-8", newline="\n")
