#!/usr/bin/env python3
"""Stage 0 smoke test: does Azure Speech (HD voice) answer, and does the Foundry model answer?

OWNER: A (potencialbg). Run on A's machine only, after `az login`:
    pip install -e "pipeline[dev]" -r pipeline/requirements-azure.txt
    python scripts/smoke_azure.py

Auth is keyless first (DefaultAzureCredential), then SPEECH_KEY from .env as a fallback for Speech only.
This script never prints, logs or writes a key or token. CI never runs it against Azure.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
LINE = "Tely smoke test. The Reds are breaking down the far side."
QUOTA_MSG = "model quota missing: Director falls back to rules (Stage 5)"
INSTALL_HINT = 'pip install -e "pipeline[dev]" -r pipeline/requirements-azure.txt'
MIN_MP3_BYTES = 1024
SECRET_NAMES = ("SPEECH_KEY",)
# Foundry v1 endpoint scope from file 03; the classic Cognitive Services scope is the fallback (unverified which one wins).
MODEL_SCOPES = ("https://ai.azure.com/.default", "https://cognitiveservices.azure.com/.default")
_JWT = re.compile(r"eyJ[\w-]+\.[\w-]+\.[\w-]+")


def load_env(path: Path) -> dict[str, str]:
    """Parse KEY=VALUE lines from a .env file. Missing file -> {}. Values are never printed."""
    env: dict[str, str] = {}
    if not path.is_file():
        return env
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def redact(text: str, env: dict[str, str]) -> str:
    """Strip secret values and anything that looks like a bearer token from a message before printing it."""
    for name in SECRET_NAMES:
        value = env.get(name)
        if value:
            text = text.replace(value, "***")
    return _JWT.sub("***", text)


def _load_speech_sdk() -> Any:
    import azure.cognitiveservices.speech as speechsdk

    return speechsdk


def _credential() -> Any:
    from azure.identity import DefaultAzureCredential

    return DefaultAzureCredential()


def _synthesise(sdk: Any, cfg: Any, voice: str, out_path: Path) -> str | None:
    """Render LINE to out_path as MP3. Returns None on success, or a reason string."""
    cfg.speech_synthesis_voice_name = voice
    cfg.set_speech_synthesis_output_format(sdk.SpeechSynthesisOutputFormat.Audio24Khz48KBitRateMonoMp3)
    audio = sdk.audio.AudioOutputConfig(filename=str(out_path))
    synth = sdk.SpeechSynthesizer(speech_config=cfg, audio_config=audio)
    result = synth.speak_text_async(LINE).get()
    del synth  # releases the file handle on Windows before we check the size
    if result.reason == sdk.ResultReason.SynthesizingAudioCompleted:
        if out_path.is_file() and out_path.stat().st_size > MIN_MP3_BYTES:
            return None
        return f"output file missing or under {MIN_MP3_BYTES} bytes"
    details = result.cancellation_details
    return f"{details.reason}: {details.error_details}"


def check_speech(env: dict[str, str], out_dir: Path) -> tuple[str, str]:
    voice = env.get("TTS_VOICE", "")
    endpoint = env.get("SPEECH_ENDPOINT", "")
    key, region = env.get("SPEECH_KEY", ""), env.get("SPEECH_REGION", "")
    if not voice:
        return "SKIP", "TTS_VOICE missing from .env"
    if not endpoint and not (key and region):
        return "SKIP", "SPEECH_ENDPOINT missing from .env (or SPEECH_KEY + SPEECH_REGION for the key fallback)"
    try:
        sdk = _load_speech_sdk()
    except ImportError:
        return "SKIP", f"Speech SDK not installed: {INSTALL_HINT}"

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "smoke.mp3"
    attempts: list[tuple[str, Callable[[], Any]]] = []
    if endpoint:
        # WHY: Learn "Microsoft Entra authentication with the Speech SDK": token_credential + custom-domain endpoint.
        attempts.append(("keyless", lambda: sdk.SpeechConfig(token_credential=_credential(), endpoint=endpoint)))
    if key:
        attempts.append(
            ("key", lambda: sdk.SpeechConfig(subscription=key, endpoint=endpoint) if endpoint
             else sdk.SpeechConfig(subscription=key, region=region))
        )

    reasons = []
    for label, make_cfg in attempts:
        try:
            reason = _synthesise(sdk, make_cfg(), voice, out_path)
        except Exception as exc:  # SDK and credential errors vary; report and try the next auth method
            reason = f"{type(exc).__name__}: {exc}"
        if reason is None:
            shown = out_path.relative_to(ROOT) if out_path.is_relative_to(ROOT) else out_path
            return "PASS", f"{label} auth, {voice}, {shown} ({out_path.stat().st_size} bytes)"
        reasons.append(f"{label}: {reason}")
    return "FAIL", redact("; ".join(reasons), env)


def _load_openai() -> Any:
    import openai
    from azure.identity import get_bearer_token_provider

    return openai, get_bearer_token_provider


def _looks_like_quota(exc: Exception, openai: Any) -> bool:
    if isinstance(exc, getattr(openai, "NotFoundError", ())):
        return True  # DeploymentNotFound: nothing deployed because there is no quota yet
    text = str(exc).lower()
    return any(s in text for s in ("quota", "deploymentnotfound", "deployment not found", "insufficient capacity"))


def check_model(env: dict[str, str]) -> tuple[str, str]:
    resource, model = env.get("FOUNDRY_RESOURCE", ""), env.get("FOUNDRY_MODEL", "")
    if not resource or not model:
        return "SKIP", "FOUNDRY_RESOURCE or FOUNDRY_MODEL missing from .env"
    try:
        openai, get_bearer_token_provider = _load_openai()
    except ImportError:
        return "SKIP", f"openai/azure-identity not installed: {INSTALL_HINT}"

    cred = _credential()
    last = ""
    for scope in MODEL_SCOPES:
        # WHY: file 03, plain openai SDK on the v1 endpoint, no api-version, Entra token as api_key.
        client = openai.OpenAI(
            base_url=f"https://{resource}.openai.azure.com/openai/v1/",
            api_key=get_bearer_token_provider(cred, scope),
            max_retries=1,
        )
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Reply with the single word: ready"}],
                max_completion_tokens=200,
            )
        except getattr(openai, "AuthenticationError", ()) as exc:
            last = f"{type(exc).__name__}: {exc}"
            continue  # try the other token scope
        except Exception as exc:
            if _looks_like_quota(exc, openai):
                return "QUOTA", QUOTA_MSG
            return "FAIL", redact(f"{type(exc).__name__}: {exc}", env)
        reply = (resp.choices[0].message.content or "").strip()[:40]
        return "PASS", f"{model} replied {reply!r}"
    return "FAIL", redact(last, env)


def run(env: dict[str, str], out_dir: Path) -> int:
    results = {"Speech": check_speech(env, out_dir), "Model": check_model(env)}
    for name, (status, detail) in results.items():
        print(QUOTA_MSG if status == "QUOTA" else f"{name}: {status} - {detail}")
    speech_ok = results["Speech"][0] == "PASS"
    model_ok = results["Model"][0] in ("PASS", "QUOTA")
    return 0 if speech_ok and model_ok else 1


def main() -> int:
    env = load_env(ROOT / ".env")
    env.update({k: v for k, v in os.environ.items() if k in env or k.startswith(("FOUNDRY_", "SPEECH_", "TTS_"))})
    return run(env, ROOT / "out")


if __name__ == "__main__":
    sys.exit(main())
