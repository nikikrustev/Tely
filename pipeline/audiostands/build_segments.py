"""Cut the judge-cut match into 2 s segments for the browser's ReplaySource (file 43 §6). OWNER: B (Nikolay).

    python -m audiostands.build_segments --cut judge      # writes web/public/replay/v1/judge/segments.json

Each segment carries the ball at 10 Hz, the crowd state per end and the tension for each second, the crowd one-shots
and the earcons (thud, whistle, net...) that fall inside it. **No `cues` field** (TEAM_SPLIT.md): A's commentary track
loads cues.*.jsonl itself. Deterministic: same input bytes -> same output bytes.
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "web" / "public" / "replay" / "v1"
SEG_S, BALL_HZ = 2, 10
FORMAT_VERSION = "0.1.0"
HALF_L = 52.5


def earcons(events: list[dict], t_of, ball_rows: list, t0: float, hz: int) -> list[dict]:
    """Auditory icons from the events (file 37 §4 layer 2). A net sound plays when the ball crosses the line:
    a fact at that moment, before any VAR decision."""
    out = []
    for e in events:
        t, typ, sub = t_of(e), e["type"], e["sub_type"]
        if typ == "pass":
            out.append((t, "whistle" if sub == "kick_off" else "pass", e["x"], e["y"]))
        elif typ == "shot":
            out.append((t, "shot", e["x"], e["y"]))
            if e["outcome_type"] in ("successful", "offside"):
                k = round((t - t0) * hz)
                while k < len(ball_rows) and abs(ball_rows[k][0]) <= HALF_L:
                    k += 1
                if k < len(ball_rows):
                    out.append((round(t0 + k / hz, 2), "net", e["x_end"], e["y_end"]))
        elif typ == "goalkeeping":
            out.append((t, "save", e["x"], e["y"]))
        elif typ == "defending":
            out.append((t, "tackle", e["x"], e["y"]))
        elif typ == "misc":
            out.append((t, "whistle", e["x"], e["y"]))
    out.sort()
    return [dict(t=round(t, 2), kind=k, x=x, y=y) for t, k, x, y in out]


def segments(bundle: Path) -> dict:
    meta = json.loads((bundle / "meta.json").read_text(encoding="utf-8"))
    signals = json.loads((bundle / "signals.json").read_text(encoding="utf-8"))
    ticks = json.loads(gzip.decompress((bundle / "ticks.json.gz").read_bytes()))
    events = [json.loads(s)["event"] for s in (bundle / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    sig = signals["events"]
    t_of = lambda e: sig[e["id"]]["t"]
    rows, hz, t0 = ticks["ball"]["rows"], ticks["ball"]["hz"], ticks["t0"]
    t_end = t0 + ticks["duration_s"]
    per_s = {r["t"]: r for r in signals["per_second"]}
    icons = earcons(events, t_of, rows, t0, hz)
    shots = signals["crowd_one_shots"]
    step = hz / BALL_HZ
    segs = []
    s0 = t0
    while s0 < t_end:
        s1 = min(s0 + SEG_S, t_end)
        last = s1 >= t_end
        ball = []
        for k in range(round((s1 - s0) * BALL_HZ)):
            i = round((s0 - t0) * hz + k * step)
            x, y, z, alive, _ = rows[i]
            a, b = (i, i + 1) if i + 1 < len(rows) else (i - 1, i)     # speed from the next 25 Hz step (m/s)
            speed = math.hypot(rows[b][0] - rows[a][0], rows[b][1] - rows[a][1]) * hz
            ball.append([x, y, z, round(speed + 0.0, 1), alive])
        secs = [t for t in range(int(s0), int(s1) + (1 if last else 0)) if t in per_s]
        inside = lambda t: s0 <= t < s1 or (last and t == s1)
        segs.append(dict(
            t0=s0, t1=s1, ball=ball,
            crowd=per_s[int(s0)]["crowd"], tension=per_s[int(s0)]["tension"],
            seconds=[dict(t=t, crowd=per_s[t]["crowd"], tension=per_s[t]["tension"]) for t in secs],
            one_shots=[o for o in shots if inside(o["t"])],
            earcons=[c for c in icons if inside(c["t"])]))
        s0 = s1
    return dict(format="audiostands.segments", version=FORMAT_VERSION, match_id=meta["match"]["id"],
                t0=t0, t1=t_end, seg_s=SEG_S, ball_hz=BALL_HZ, ball_columns=["x", "y", "z", "speed", "alive"],
                segments=segs)


def write(doc: dict, path: Path) -> None:
    head = {k: v for k, v in doc.items() if k != "segments"}
    lines = ",\n".join("  " + json.dumps(s, separators=(",", ":")) for s in doc["segments"])
    text = json.dumps(head, separators=(",", ":"))[:-1] + ',"segments":[\n' + lines + "\n]}\n"
    path.write_text(text, encoding="utf-8", newline="\n")


# SEAM(B->A): A's build_bundle calls build(cut, out_dir) after build_match (pipeline/audiostands/build_bundle.py)
def build(cut: str, out_dir: Path) -> Path:
    path = out_dir / "segments.json"
    write(segments(out_dir), path)
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Write segments.json for the browser (2 s segments, no cues).")
    ap.add_argument("--cut", default="judge", choices=["judge"])
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    print(f"wrote {build(a.cut, a.out or BUNDLE / a.cut)}")
