"""Commentary in other languages (D27): translate the English Radio track line by line, then render each line with
the multilingual Brian voice, at the English line's time. OWNER: A (potencialbg).

    python -m tely.commentary.languages --cut judge                  # every language in LANGS
    python -m tely.commentary.languages --cut judge --langs bg,es

Writes into web/public/replay/v1/<cut>/:
    cues.<lang>.radio.jsonl        the English cues with text and utterance replaced (same t_in, same evidence)
    audio/<lang>/radio/<sha>.mp3   one MP3 per line; index.json holds the real durations
    manifest.json                  tracks.<lang> added, every file's sha256 again (build_bundle.manifest)

WHY translate the finished lines and not the templates (file 35 recommends templates): the English track is 70 lines
and already verified (truth_check, spoiler_check), so a line-by-line translation keeps every fact, time and piece of
evidence the English line has. Translations are cached in commentary/l10n/<lang>.json (committed), so a rebuild makes
no model calls and no TTS calls, and the replay always sounds the same.
WHY one voice: en-US-BrianMultilingualNeural speaks every language here, so the fan hears the same commentator in each,
and the live answers (relay/voicelive.py) use the same voice. A line that runs past the next one's start is
re-rendered faster (prosody rate), so lines never overlap.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Callable, Protocol
from xml.sax.saxutils import escape

from tely.commentary.source import BUNDLE, load_match
from tely.commentary.ssml import NS, band, ssml_sha256
from tely.commentary.tts import AzureSynthesiser, Synthesiser, TtsCache, TtsError, load_env

LEVEL = "radio"
VOICE = "en-US-BrianMultilingualNeural"
L10N = Path(__file__).resolve().parent / "l10n"

# lang -> (SSML locale, name in English, the team names the commentator uses). Navy plays in navy: "the Blues".
LANGS: dict[str, tuple[str, str, tuple[str, str]]] = {
    "bg": ("bg-BG", "Bulgarian", ("Червените", "Сините")),
    "es": ("es-ES", "Spanish", ("los Rojos", "los Azules")),
    "ar": ("ar-SA", "Arabic", ("الحمر", "الزرق")),
    "fr": ("fr-FR", "French", ("les Rouges", "les Bleus")),
    "de": ("de-DE", "German", ("die Roten", "die Blauen")),
}
# Livelier lines go a little faster and higher (DragonHD's [style] tags don't exist on this voice). Ours, by ear.
BAND_PROSODY = {"calm": (0, 0), "curious": (3, 0), "urgent": (8, 3), "excited": (12, 6), "shouting": (15, 10)}
GAP_S = 0.15        # silence kept before the next line
MAX_RATE = 45       # never faster than +45 %: past that it stops sounding like speech
_DIGITS = re.compile(r"\d+")
# English words a translation must not keep (seen 27 Oct: "Rojos nil, Azules one, sixty minutes played").
_ENGLISH = {"nil", "one", "two", "three", "four", "five", "seven", "eight", "nine", "ten", "twenty", "thirty", "forty",
            "fifty", "sixty", "seventy", "eighty", "ninety", "played"}   # not "minutes" (French) or "ball" (German)


def build_ssml(text: str, locale: str, intensity: float, extra_rate: int = 0) -> str:
    rate, pitch = BAND_PROSODY[band(intensity)]
    rate = min(MAX_RATE, rate + extra_rate)
    return (f'<speak {NS} xml:lang="en-US"><voice name="{VOICE}"><lang xml:lang="{locale}">'
            f'<prosody rate="+{rate}%" pitch="+{pitch}%">{escape(text)}</prosody></lang></voice></speak>')


class Translator(Protocol):
    name: str

    def translate(self, lang: str, lines: list[str]) -> list[str]: ...


def instructions(lang: str, players: list[str]) -> str:
    _, name, (home, away) = LANGS[lang]
    return (
        f"You translate live radio football commentary from English into {name}. Each input line is spoken by a "
        "commentator to a blind fan. Translate every line as a native radio commentator would say it: short, spoken, "
        "natural football language, no longer than the English. Keep every fact exactly and add nothing. Scores, "
        f"minutes and counts are often English words (nil, one, sixty minutes played): say them the way a {name} "
        f"commentator would, in {name}. Never leave an English word in the translation. The team 'Reds' is '{home}' and the team 'Navy' is '{away}', in every line. Player names stay "
        f"exactly as written, in Latin letters: {', '.join(players)}. Return one translation per input line, in order.")


class FoundryTranslator:
    """A Foundry model deployment (FOUNDRY_PROJECT_ENDPOINT, FOUNDRY_MODEL), keyless, with a strict JSON schema."""

    def __init__(self, env: dict[str, str], players: list[str]):
        from agent_framework import Agent
        from agent_framework.foundry import FoundryChatClient
        from azure.identity import DefaultAzureCredential

        self.model = env["FOUNDRY_MODEL"]
        self.name = f"l10n_v1@{self.model}"
        self.players = players
        self.client = FoundryChatClient(project_endpoint=env["FOUNDRY_PROJECT_ENDPOINT"], model=self.model,
                                        credential=DefaultAzureCredential(exclude_interactive_browser_credential=True))
        self.Agent = Agent

    def translate(self, lang: str, lines: list[str]) -> list[str]:
        schema = {"type": "object", "additionalProperties": False, "required": ["lines"],
                  "properties": {"lines": {"type": "array", "items": {"type": "string"}}}}
        agent = self.Agent(client=self.client, name="Translator", instructions=instructions(lang, self.players))
        options = {"response_format": {"type": "json_schema", "json_schema": {"name": "lines", "schema": schema, "strict": True}},
                   "reasoning": {"effort": "low"}}
        res = asyncio.run(agent.run(json.dumps({"lines": lines}, ensure_ascii=False), options=options))
        out = json.loads(res.text)["lines"]
        if len(out) != len(lines):
            raise ValueError(f"{lang}: {len(out)} translations for {len(lines)} lines")
        return [s.strip() for s in out]


def check(en: str, tr: str, players: list[str]) -> list[str]:
    """Digits and player names survive translation unchanged; no English word is left behind."""
    errs = [f"number {n} missing" for n in _DIGITS.findall(en) if n not in tr]
    errs += [f"English word {w!r} left" for w in re.findall(r"[A-Za-z]+", tr) if w.lower() in _ENGLISH and w not in players]
    errs += [f"name {p} missing" for p in players if re.search(rf"\b{re.escape(p)}\b", en) and p not in tr]
    return errs


def load_cache(lang: str) -> dict:
    p = L10N / f"{lang}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {"translator": None, "lines": {}}


def save_cache(lang: str, cache: dict) -> None:
    L10N.mkdir(parents=True, exist_ok=True)
    cache["lines"] = dict(sorted(cache["lines"].items()))
    if "measured" in cache:
        cache["measured"] = dict(sorted(cache["measured"].items()))
    (L10N / f"{lang}.json").write_text(json.dumps(cache, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def translations(lang: str, english: list[str], players: list[str], translator: Callable[[], Translator]) -> dict[str, str]:
    """English line -> translation, from the cache; only missing lines go to the model (twice at most, then fail)."""
    cache = load_cache(lang)
    cache["lines"] = {en: tr for en, tr in cache["lines"].items() if not check(en, tr, players)}   # a stricter check re-asks
    for _ in range(2):
        missing = [s for s in dict.fromkeys(english) if s not in cache["lines"]]
        if not missing:
            break
        t = translator()
        for en, tr in zip(missing, t.translate(lang, missing)):
            if not check(en, tr, players):
                cache["lines"][en] = tr
        cache["translator"] = t.name
        save_cache(lang, cache)
    bad = [s for s in english if s not in cache["lines"]]
    if bad:
        raise ValueError(f"{lang}: {len(bad)} lines lost a number or a name in translation, e.g. {bad[0]!r}")
    return cache["lines"]


def build_lang(out_dir: Path, lang: str, cues: list[dict], t_end: float, lines: dict[str, str],
               synth_factory: Callable[[], Synthesiser], measured: dict[str, int] | None = None) -> dict:
    """measured: SSML sha -> duration of first renders that were too long (their MP3s are dropped), so a rebuild
    knows they don't fit without rendering them again."""
    locale = LANGS[lang][0]
    measured = measured if measured is not None else {}
    cache = TtsCache(out_dir / "audio" / lang / LEVEL, synth_factory)
    out, sped = [], 0
    for i, c in enumerate(cues):
        text = lines[c["text"]["radio"]]
        u = c["utterance"]
        room_ms = ((cues[i + 1]["t_in"] if i + 1 < len(cues) else t_end) - c["t_in"] - GAP_S) * 1000
        ssml = build_ssml(text, locale, u["intensity"])
        ms = measured.get(ssml_sha256(ssml)) or cache.ensure(ssml_sha256(ssml), ssml, text)
        if ms > room_ms > 0:
            measured[ssml_sha256(ssml)] = ms   # too long for its slot: once more, as much faster as it needs (capped)
            extra = min(MAX_RATE, int((ms / room_ms - 1) * 100) + 3)
            ssml = build_ssml(text, locale, u["intensity"], extra)
            ms = cache.ensure(ssml_sha256(ssml), ssml, text)
            sped += 1
        sha = ssml_sha256(ssml)
        cue = json.loads(json.dumps(c))
        cue["text"] = {LEVEL: text}
        cue["ttl_ms"] = ms
        cue["utterance"] = {**u, "lang": locale, "voice": VOICE, "ssml_sha256": sha,
                            "audio_url": f"audio/{lang}/{LEVEL}/{sha}.mp3", "duration_ms": ms}
        cue["l10n"] = {"from": "en", "fits": ms <= room_ms or room_ms <= 0}
        out.append(cue)
    # Drop the renders a faster re-render replaced, so the bundle carries only what plays.
    used = {c["utterance"]["ssml_sha256"] for c in out}
    for sha in [s for s in cache.index if s not in used]:
        (cache.folder / f"{sha}.mp3").unlink(missing_ok=True)
        del cache.index[sha]
    cache.save()
    body = "\n".join(json.dumps(c, ensure_ascii=False, separators=(",", ":")) for c in out) + "\n"
    (out_dir / f"cues.{lang}.{LEVEL}.jsonl").write_text(body, encoding="utf-8", newline="\n")
    return {"lang": lang, "lines": len(out), "tts_calls": cache.calls, "chars": cache.chars_text, "sped_up": sped,
            "overlaps": sum(not c["l10n"]["fits"] for c in out)}


def main(argv: list[str] | None = None) -> int:
    from tely import build_bundle

    ap = argparse.ArgumentParser(description="Commentary in other languages (cues, MP3s, manifest)")
    ap.add_argument("--cut", default="judge")
    ap.add_argument("--langs", default=",".join(LANGS))
    args = ap.parse_args(argv)
    langs = [s for s in args.langs.split(",") if s]
    if unknown := [s for s in langs if s not in LANGS]:
        print(f"FAIL: unknown language {unknown}; known: {', '.join(LANGS)}")
        return 1
    out_dir = BUNDLE / args.cut
    cues = [json.loads(s) for s in (out_dir / "cues.en.radio.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()]
    m = load_match(args.cut)
    players = sorted({p["last_name"] for side in ("home", "away") for p in m.meta["teams"][side]["players"]})
    env = load_env()
    env.update(build_bundle.dir_env(env))   # FOUNDRY_* from the process env win, as in build_bundle
    english = [c["text"]["radio"] for c in cues]
    try:
        for lang in langs:
            lines = translations(lang, english, players, lambda: FoundryTranslator(env, players))
            l10n = load_cache(lang)
            measured = l10n.setdefault("measured", {})
            rep = build_lang(out_dir, lang, cues, m.t_end, lines, lambda: AzureSynthesiser(env), measured)
            save_cache(lang, l10n)
            print(json.dumps(rep, ensure_ascii=False))
    except (TtsError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    old = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    man = build_bundle.manifest(args.cut, out_dir, m, old["voice"], old.get("director"))
    (out_dir / "manifest.json").write_text(json.dumps(man, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"PASS: tracks {', '.join(man['tracks'])}; {man['files']} files, {man['bytes'] / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
