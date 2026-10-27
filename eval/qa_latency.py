"""Live Ask latency: end of the fan's speech -> first answer audio, over B's eval questions.

    python eval/qa_latency.py audio                         # once: B's questions as speech (Azure TTS, a "fan" voice)
    python eval/qa_latency.py run --relay wss://<relay>/voice --origin https://<site>
    python eval/qa_latency.py browser --site https://<site> [--relay https://<relay>] --only ball_attack
                                                            # the real page in Chromium, question as a fake mic
    python eval/qa_latency.py summarise                     # eval/live/live_*.jsonl -> eval/report.json
    python eval/build_report.py                             # -> eval/report.md

`browser` drives the deployed page itself (Playwright library; Chromium's fake mic plays the question as a WAV):
Start -> Ask -> "Ask out loud", then reads the page's golden turns (?debug=1 exposes them). The crowd duck around the
answer is B's AskController.run() and B's tests check it; the ?debug=1 panel shows the excitement level, not the duck.
`run` is a headless fan: it streams each question's PCM to the relay in real time (20 ms chunks, then silence, like an
open mic), so Voice Live's own VAD, transcription, tools and voice all run as they do for the browser. Each answered
turn is a golden record, appended to eval/live/live_<date>.jsonl.

Latency (file 40 §3, file 43 §4): `latency_ms` is measured by the relay, from the moment the fan's last word reached it
(the VAD's audio_end_ms mapped onto the audio it forwarded) to the first answer audio from Voice Live. It includes the
VAD's 500 ms end-of-turn silence, the model, the tool calls and the first TTS audio, but not the network to the fan.
`facts_latency_ms` runs to the first audio after the tool results went back, so a "Let me check" preamble
doesn't flatter it. `client_latency_ms` is what this client saw from the relay's speech_stopped message to the first answer bytes. There
is no target: file 42 records a rival's 4.66 s median, for comparison only. Percentiles are nearest-rank.
Needs (A's machine only, never CI): websockets, and azure-cognitiveservices-speech + azure-identity for `audio`.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "eval" / "qa_cases.jsonl"            # B's questions (read only)
AUDIO = ROOT / "out" / "qa_audio"                   # git-ignored
GOLDEN = ROOT / "eval" / "live"
REPORT = ROOT / "eval" / "report.json"
FAN_VOICE = "en-GB-RyanNeural"                      # not the commentator's voice, so the two never get mixed up
RATE, CHUNK_MS = 24000, 20
RIVAL_MEDIAN_S = 4.66                               # file 42, another entry's published median; comparison only
PER_SESSION = 10                                    # questions per relay session (cap is 30, file 40 §6)


def cases() -> list[dict]:
    return [json.loads(s) for s in CASES.read_text(encoding="utf-8").splitlines() if s.strip()]


# ---------------------------------------------------------------- audio
def make_audio() -> int:
    import azure.cognitiveservices.speech as speechsdk
    from azure.identity import DefaultAzureCredential

    env = dict(line.split("=", 1) for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines()
               if "=" in line and not line.lstrip().startswith("#"))
    cfg = speechsdk.SpeechConfig(token_credential=DefaultAzureCredential(), endpoint=env["SPEECH_ENDPOINT"].strip())
    cfg.speech_synthesis_voice_name = FAN_VOICE
    cfg.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Raw24Khz16BitMonoPcm)
    synth = speechsdk.SpeechSynthesizer(speech_config=cfg, audio_config=None)
    AUDIO.mkdir(parents=True, exist_ok=True)
    made = 0
    for c in cases():
        out = AUDIO / f"{c['id']}.pcm"
        if out.is_file():
            continue
        r = synth.speak_text_async(c["question"]).get()
        if r.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
            print(f"FAIL {c['id']}: {r.cancellation_details.reason}")    # no key or token is ever in this text
            return 1
        out.write_bytes(bytes(r.audio_data))
        made += 1
    print(f"audio: {made} new question clips in {AUDIO}")
    return 0


# ---------------------------------------------------------------- run
def spoiler_hits(answer: str, words: list[str]) -> list[str]:
    return [w for w in words if re.search(rf"\b{re.escape(w.lower())}\b", answer.lower())]


async def ask_one(ws, case: dict, pcm: bytes, timeout_s: float = 25.0) -> dict:
    """One question on an open relay session. Returns the relay's golden turn, plus what this client saw."""
    await ws.send(json.dumps({"type": "ask", "playhead_s": case["playhead_s"]}))
    lead = b"\x00\x00" * (RATE * 300 // 1000)        # 300 ms of room tone before the fan speaks
    chunk = RATE * CHUNK_MS // 1000 * 2
    stream = lead + pcm
    sent, stopped_at, first_audio, turn, refusal = 0, None, None, None, None
    t_end = time.monotonic() + timeout_s
    listening = False

    async def pace():                                 # real-time mic: question, then silence until the VAD stops
        nonlocal sent
        start = time.monotonic()
        k = 0
        while stopped_at is None and time.monotonic() < t_end:
            part = stream[k * chunk:(k + 1) * chunk] or b"\x00" * chunk
            await ws.send(part)
            k += 1
            sent += 1
            await asyncio.sleep(max(0.0, start + k * CHUNK_MS / 1000 - time.monotonic()))

    pacer = None
    try:
        while time.monotonic() < t_end and turn is None and refusal is None:
            msg = await asyncio.wait_for(ws.recv(), max(0.1, t_end - time.monotonic()))
            if isinstance(msg, bytes):
                if first_audio is None:
                    first_audio = time.monotonic()
                    if stopped_at is not None:
                        await ws.send(json.dumps({"type": "metrics",
                                                  "client_latency_ms": (first_audio - stopped_at) * 1000}))
                continue
            m = json.loads(msg)
            if m["type"] == "listening" and not listening:
                listening = True
                pacer = asyncio.create_task(pace())
            elif m["type"] == "speech_stopped":
                stopped_at = time.monotonic()
            elif m["type"] == "answer_done":
                turn = m["turn"]
            elif m["type"] in ("refusal", "error"):
                refusal = m
    except asyncio.TimeoutError:
        pass
    finally:
        if pacer:
            pacer.cancel()
    if turn is None:
        turn = {"outcome": "timeout" if refusal is None else f"refusal:{refusal.get('reason')}", "latency_ms": None}
    turn.update({"case_id": case["id"], "asked": case["question"], "source": "eval/qa_latency.py run (headless)",
                 "spoiler_hits": spoiler_hits(turn.get("answer") or "", case.get("expect", {}).get("spoiler_words", []))})
    return turn


async def run(relay: str, origin: str | None, only: list[str] | None) -> int:
    from websockets.asyncio.client import connect

    todo = [c for c in cases() if not only or c["id"] in only]
    missing = [c["id"] for c in todo if not (AUDIO / f"{c['id']}.pcm").is_file()]
    if missing:
        print(f"no audio for {missing}: run `python eval/qa_latency.py audio` first")
        return 1
    GOLDEN.mkdir(parents=True, exist_ok=True)
    out = GOLDEN / f"live_{date.today().isoformat()}.jsonl"
    run_id = time.strftime("%Y%m%dT%H%M%S")
    turns = []
    for i in range(0, len(todo), PER_SESSION):
        async with connect(relay, origin=origin, max_size=2**22) as ws:
            first = json.loads(await asyncio.wait_for(ws.recv(), 20))
            if first["type"] != "ready":
                print(f"relay refused: {first}")
                return 1
            for c in todo[i:i + PER_SESSION]:
                t = await ask_one(ws, c, (AUDIO / f"{c['id']}.pcm").read_bytes())
                t["run"] = run_id
                turns.append(t)
                print(f"{c['id']:<24} {t.get('outcome')!s:<10} {t.get('latency_ms')!s:>6} ms  "
                      f"Q: {t.get('question')!r}  A: {(t.get('answer') or '')[:70]!r}"
                      + (f"  SPOILER {t['spoiler_hits']}" if t["spoiler_hits"] else ""))
                await asyncio.sleep(1.0)              # let the previous answer's tail clear
    with out.open("a", encoding="utf-8", newline="\n") as f:
        for t in turns:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"wrote {len(turns)} turns to {out.relative_to(ROOT)}")
    return 0


# ---------------------------------------------------------------- browser
def wav(case: dict) -> Path:
    """The question as a mono 16-bit WAV for Chromium's fake mic: 1 s of quiet, the question, then 14 s of quiet."""
    import wave

    out = AUDIO / f"{case['id']}.wav"
    pcm = bytes(2 * RATE) + (AUDIO / f"{case['id']}.pcm").read_bytes() + bytes(2 * RATE * 14)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm)
    return out


def browser(site: str, relay: str | None, only: list[str] | None, play_s: float, headed: bool) -> int:
    from playwright.sync_api import sync_playwright

    todo = [c for c in cases() if not only or c["id"] in only]
    url = site.rstrip("/") + "/?debug=1" + (f"&relay={relay}" if relay else "")
    GOLDEN.mkdir(parents=True, exist_ok=True)
    out = GOLDEN / f"live_{date.today().isoformat()}.jsonl"
    run_id, rows = time.strftime("%Y%m%dT%H%M%S"), []
    for c in todo:
        with sync_playwright() as pw:
            b = pw.chromium.launch(headless=not headed, args=[
                "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
                f"--use-file-for-fake-audio-capture={wav(c)}", "--autoplay-policy=no-user-gesture-required"])
            page = b.new_context(permissions=["microphone"]).new_page()
            page.goto(url)
            page.wait_for_function("() => /Ready/.test(document.getElementById('status').textContent)", timeout=60_000)
            page.click("#start")                           # before "Ready" B's Start ignores the press
            page.wait_for_function("() => !document.getElementById('ask').disabled && window.telyLive",
                                   timeout=60_000)
            page.wait_for_timeout(play_s * 1000)           # let the match play a little before asking
            page.click("#ask")
            clicked = page.evaluate("() => performance.now()")
            page.click("#ask-live")
            page.wait_for_function("() => window.telyLive.turns.length > 0 || "
                                   "!document.getElementById('ask-menu').hidden", timeout=60_000)
            page.wait_for_timeout(500)
            turns = page.evaluate("() => window.telyLive.turns")
            presets = page.evaluate("() => !document.getElementById('ask-menu').hidden")
            events = page.evaluate("() => window.telyLive.events")
            b.close()
        t = turns[0] if turns else {"outcome": "fallback_to_presets" if presets else "no_turn", "latency_ms": None}
        t.update({"case_id": c["id"], "asked": c["question"], "source": f"eval/qa_latency.py browser ({site})",
                  "run": run_id,
                  # ms from pressing "Ask out loud": B's hold (if a chance is coming), our refusal, the presets
                  "page_events": [[round(t - clicked), what] for t, what in events],
                  "spoiler_hits": spoiler_hits(t.get("answer") or "", c.get("expect", {}).get("spoiler_words", []))})
        rows.append(t)
        print(f"{c['id']:<24} {t.get('outcome')!s:<10} {t.get('latency_ms')!s:>6} ms  {t['page_events']}  "
              f"Q: {t.get('question')!r}  A: {(t.get('answer') or '')[:80]!r}")
    with out.open("a", encoding="utf-8", newline="\n") as f:
        for t in rows:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} turns to {out.relative_to(ROOT)}")
    return 0


# ---------------------------------------------------------------- summarise
def pct(xs: list[float], p: float) -> float | None:
    if not xs:
        return None
    s = sorted(xs)
    return s[max(0, math.ceil(p / 100 * len(s)) - 1)]


def summary(turns: list[dict]) -> dict:
    ans = [t for t in turns if t.get("outcome") == "answered"]
    lat = [t["latency_ms"] for t in ans if isinstance(t.get("latency_ms"), (int, float))]
    facts = [t["facts_latency_ms"] for t in ans if isinstance(t.get("facts_latency_ms"), (int, float))]
    cli = [t["client_latency_ms"] for t in ans if isinstance(t.get("client_latency_ms"), (int, float))]
    return {
        "measured": time.strftime("%Y-%m-%d %H:%M"),
        "files": sorted({t["_file"] for t in turns}),
        "questions": len(turns), "answered": len(ans),
        "outcomes": {k: sum(t.get("outcome") == k for t in turns) for k in sorted({str(t.get("outcome")) for t in turns})},
        "n_latency": len(lat), "p50_ms": pct(lat, 50), "p95_ms": pct(lat, 95), "max_ms": max(lat) if lat else None,
        "facts_p50_ms": pct(facts, 50), "facts_p95_ms": pct(facts, 95),
        "client_p50_ms": pct(cli, 50), "client_p95_ms": pct(cli, 95),
        "basis": sorted({t.get("latency_basis") for t in ans if t.get("latency_basis")}),
        "tool_calls": sum(len(t.get("tool_calls") or []) for t in ans),
        "spoiler_hits": sum(len(t.get("spoiler_hits") or []) for t in turns),
        "spoiler_hit_list": [{"case_id": t.get("case_id"), "words": t["spoiler_hits"], "answer": t.get("answer")}
                             for t in turns if t.get("spoiler_hits")],
        "model": sorted({t.get("model") for t in ans if t.get("model")}),
        "voice": sorted({t.get("voice") for t in ans if t.get("voice")}),
        "rival_median_s": RIVAL_MEDIAN_S,
        "definition": "relay: fan's last word reached the relay -> first answer audio from Voice Live "
                      "(includes the 500 ms VAD silence; often a short preamble); facts: the same, to the first audio after the tool "
                      "results went back; client: relay speech_stopped message -> first answer bytes",
    }


def summarise(files: list[Path], runs: list[str] | None = None) -> int:
    files = files or sorted(GOLDEN.glob("live_*.jsonl"))
    turns = []
    for f in files:
        for s in f.read_text(encoding="utf-8").splitlines():
            if s.strip():
                turns.append({**json.loads(s), "_file": f.relative_to(ROOT).as_posix()})
    if runs:                                         # e.g. only the run on the current prompt and relay
        turns = [t for t in turns if t.get("run") in runs]
    if not turns:
        print("no golden turns yet")
        return 1
    rep = json.loads(REPORT.read_text(encoding="utf-8")) if REPORT.is_file() else {}
    rep["qa_latency"] = s = {**summary(turns), "runs": sorted({t.get("run") for t in turns if t.get("run")})}
    REPORT.write_text(json.dumps(rep, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"qa_latency: {s['answered']}/{s['questions']} answered, p50 {s['p50_ms']} ms, p95 {s['p95_ms']} ms "
          f"(client p50 {s['client_p50_ms']} ms), spoiler hits {s['spoiler_hits']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("audio")
    r = sub.add_parser("run")
    r.add_argument("--relay", required=True, help="wss://<relay host>/voice (or ws://localhost:8080/voice)")
    r.add_argument("--origin", help="Origin header, e.g. the site URL (the relay accepts only its own pages)")
    r.add_argument("--only", nargs="*", help="case ids")
    w = sub.add_parser("browser")
    w.add_argument("--site", required=True, help="the page, e.g. https://<swa host> or http://localhost:5173")
    w.add_argument("--relay", help="relay base URL to use instead of /live.json (debug override)")
    w.add_argument("--only", nargs="*", help="case ids")
    w.add_argument("--play-s", type=float, default=8.0, help="seconds of match before asking")
    w.add_argument("--headed", action="store_true")
    s = sub.add_parser("summarise")
    s.add_argument("files", nargs="*", type=Path)
    s.add_argument("--run", action="append", help="only these run ids (repeatable)")
    a = ap.parse_args(argv)
    if a.cmd == "audio":
        return make_audio()
    if a.cmd == "browser":
        return browser(a.site, a.relay, a.only, a.play_s, a.headed)
    if a.cmd == "run":
        return asyncio.run(run(a.relay, a.origin, a.only))
    return summarise([f.resolve() for f in a.files], a.run)


if __name__ == "__main__":
    sys.exit(main())
