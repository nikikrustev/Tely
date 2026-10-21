"""DragonHD SSML for one commentary line. OWNER: A (potencialbg).

DragonHD has no <prosody> and no express-as; intensity comes from [style] tags, wording, <break> and a low
temperature (files 39 §4, 43 §7). All five tags below were checked on 21 Oct 2026 by rendering them with
en-US-Andrew:DragonHDLatestNeural and transcribing the audio: none of the tag words were spoken.
"""

from __future__ import annotations

import hashlib
import re
from xml.sax.saxutils import escape

DEFAULT_VOICE = "en-US-Andrew:DragonHDLatestNeural"
TEMPERATURE = 0.4  # "low" per BUILD_PLAN Stage 3: one steady commentator across lines (our pick; file 39 shows 0.6)
BANDS = ("calm", "curious", "urgent", "excited", "shouting")
NS = 'version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="http://www.w3.org/2001/mstts"'
_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def band(intensity: float) -> str:
    """calm < .25 <= curious < .5 <= urgent < .75 <= excited < .92 <= shouting (thresholds are our guesses)."""
    for limit, name in ((0.25, "calm"), (0.5, "curious"), (0.75, "urgent"), (0.92, "excited")):
        if intensity < limit:
            return name
    return "shouting"


def build_ssml(text: str, style: str, voice: str = DEFAULT_VOICE, *, pause_after_ms: int = 0,
               temperature: float = TEMPERATURE) -> str:
    """One SSML document per line. The [style] tag is repeated per sentence, because a tag ends at a sentence boundary."""
    if style not in BANDS:
        raise ValueError(f"unknown style {style!r}")
    body = " ".join(f"[{style}] {escape(s)}" for s in _SENTENCE.split(text.strip()) if s)
    if pause_after_ms:
        body += f'<break time="{pause_after_ms}ms"/>'
    return (f'<speak {NS} xml:lang="en-US"><voice name="{escape(voice)}" parameters="temperature={temperature}">'
            f"{body}</voice></speak>")


def ssml_sha256(ssml: str) -> str:
    return hashlib.sha256(ssml.encode("utf-8")).hexdigest()
