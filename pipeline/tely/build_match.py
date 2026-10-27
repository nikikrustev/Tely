"""Build the judge-cut match bundle in the contracts/b/ format (contracts/README.md). OWNER: B (Nikolay).

    python -m tely.build_match --cut judge

Writes meta.json, events.jsonl, signals.json and ticks.json.gz to web/public/replay/v1/judge/, and
out/realism_report.md (generator over 50 seeds, movement over the cut) against the targets cited in files 02 and 19.
Deterministic: two runs give byte-identical files (see generator.py and movement.py for how).
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import math
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from . import crowd, haptics, interpret
from .generator import FPS, GENERATOR_VERSION, HALF_L, HALF_W, PERIODS, TEAMS, generate
from .movement import simulate

FORMAT_VERSION = "0.2.0"
CDF_VERSION = "0.3.2"
PLAYER_HZ = 5
KICKOFF = datetime(2026, 10, 24, 15, 0, 0, tzinfo=timezone.utc)
SECOND_HALF_START = KICKOFF + timedelta(minutes=63)     # 45 + added + a 15-minute break (fictional schedule)
ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "web" / "public" / "replay" / "v1"
CUT_FILE = Path(__file__).resolve().parents[1] / "judge_cut.json"
REPORT = ROOT / "out" / "realism_report.md"


# ---------------------------------------------------------------- time helpers
def period_start(k: int) -> datetime:
    return KICKOFF if k == 0 else SECOND_HALF_START


def iso(k: int, f: int) -> str:
    d = period_start(k) + timedelta(milliseconds=f * 1000 // FPS)
    return d.strftime("%Y-%m-%dT%H:%M:%S.") + f"{d.microsecond // 1000:03d}Z"


def match_clock(k: int, f: int) -> str:
    cs = f * 100 // FPS + (45 * 6000 if k == 1 else 0)
    return f"{cs // 6000:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


# ---------------------------------------------------------------- files
def meta_json(m: dict, cut: dict, k: int, score_at_start: dict) -> dict:
    teams = {}
    for side, t in TEAMS.items():
        ps = sorted((p for p in m["players"] if m["players"][p]["side"] == side), key=lambda p: m["players"][p]["slot"])
        teams[side] = dict(id=t["id"], name=t["name"], short_name=t["short_name"], formation=t["formation"],
                           attacks=t["attacks"], kit=t["kit"],
                           players=[dict(id=p, first_name=m["players"][p]["first"], last_name=m["players"][p]["last"],
                                         name=f"{m['players'][p]['first']} {m['players'][p]['last']}",
                                         jersey_number=m["players"][p]["number"],
                                         position=m["players"][p]["position"], is_starter=True) for p in ps])
    return dict(
        format="tely.meta", version=FORMAT_VERSION, cdf_version=CDF_VERSION, synthetic=True,
        notice="Synthetic match. Fictional clubs and players. No real match data.",
        match=dict(id=f"syn_s{m['seed']:04d}", competition="Berbata Synthetic League", season="2026-27",
                   kickoff_time=iso(0, 0), venue=dict(id="syn_emberfield", name="Emberfield")),
        periods=[dict(period=PERIODS[k], start_time=iso(k, 0), start_t=0.0,
                      clock_start="45:00.00" if k == 1 else "00:00.00")],
        pitch=dict(length_m=2 * HALF_L, width_m=2 * HALF_W, origin="centre_spot",
                   x="metres along the touchline, -52.5..52.5; home attacks +x all match (CDF)",
                   y="metres across, -34..34, bottom to top: -34 is the near (main-stand) touchline"),
        teams=teams,
        judge_cut=dict(t_start=float(cut["t_start"]), t_end=float(cut["t_end"]), seed=m["seed"], source="generator",
                       period=PERIODS[k], score_at_start=score_at_start),
        rates=dict(ball_hz=FPS, player_hz=PLAYER_HZ, signals_hz=1),
        files=dict(events="events.jsonl", signals="signals.json", ticks="ticks.json.gz"),
        officials=[dict(id="ref_1", type="main_referee"), dict(id="var_1", type="video_assistant_referee")],
        generator=dict(name="tely.generator", version=GENERATOR_VERSION),
    )


def cdf_line(e: dict, k: int, match_id: str) -> dict:
    """One CDF v0.3.2 event line in the validated shape (file 26 §2). Nothing that is not CDF goes in here."""
    ev = {"id": e["id"], "time": iso(k, e["f"]), "period": e["period"], "type": e["type"], "sub_type": e["sub_type"],
          "is_successful": e["is_successful"], "outcome_type": e["outcome_type"]}
    if e["type"] == "referee":
        ev["official_id"] = e["official_id"]
    else:
        ev["player_id"], ev["team_id"] = e["player_id"], TEAMS[e["team"]]["id"]
    rec = e["receiver_id"]
    ev.update({"receiver_id": rec, "receiver_time": iso(k, e["recv_f"]) if rec else None,
               "receiver_team_id": TEAMS[e["team"]]["id"] if rec else None, "x": e["x"], "y": e["y"],
               "x_end": e["x_end"], "y_end": e["y_end"], "body_part": e["body_part"],
               "related_event_ids": e["related_event_ids"], "match_clock": match_clock(k, e["f"])})
    if e["var"]:
        ev["var"] = e["var"]
    return {"match": {"id": match_id}, "meta": {"is_synced": True}, "event": ev}


def rows_json(obj: dict) -> str:
    """Readable but compact: one top-level key per line, one list item / event entry per line (same as the sample)."""
    out, items = ["{"], list(obj.items())
    for n, (key, v) in enumerate(items):
        comma = "," if n < len(items) - 1 else ""
        if isinstance(v, list) and v and isinstance(v[0], dict):
            body = ",\n".join("    " + json.dumps(x, separators=(",", ":")) for x in v)
            out.append(f'  "{key}": [\n{body}\n  ]{comma}')
        elif key == "events" and isinstance(v, dict):
            body = ",\n".join(f'    "{i}": ' + json.dumps(x, separators=(",", ":")) for i, x in v.items())
            out.append(f'  "{key}": {{\n{body}\n  }}{comma}')
        else:
            out.append(f'  "{key}": {json.dumps(v)}{comma}')
    return "\n".join(out + ["}"]) + "\n"


def gz(data: bytes) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, mtime=0, compresslevel=9) as f:
        f.write(data)
    return buf.getvalue()


# ---------------------------------------------------------------- build
def build(cut: dict, out_dir: Path, report: bool = True) -> dict:
    m = generate(cut["seed"])
    k = PERIODS.index(cut["period"])
    t0, t1 = int(cut["t_start"]), int(cut["t_end"])
    f0, f1 = t0 * FPS, t1 * FPS
    events = [e for e in m["events"] if e["period"] == cut["period"] and f0 <= e["f"] <= f1]

    ids, ball, pos25 = simulate(m, k, f0, f1)
    warm0 = max(0, t0 - 60)                                   # settle the crowd smoothing before the window
    if warm0 < t0:
        _, ball_w, _ = simulate(m, k, warm0 * FPS, f0, warmup_s=0.0)
        rows_all = interpret.per_second(m, k, warm0, t1, ball_w[:-1] + ball)
    else:
        rows_all = interpret.per_second(m, k, t0, t1, ball)
    warm, rows = rows_all[:t0 - warm0], rows_all[t0 - warm0:]
    mo = crowd.moments(m["events"], k)
    ends = {end: crowd.crowd_states(rows, mo, end, warm=warm) for end in ("H", "A")}

    state = interpret.State(m)
    meta = meta_json(m, cut, k, state.score(k, f0 - 1) if f0 else {"home": 0, "away": 0})
    mid = meta["match"]["id"]
    lines = [cdf_line(e, k, mid) for e in events]
    per_second = [dict(t=r["t"], win_prob=r["win_prob"], suspense=r["suspense"], tension=r["tension"],
                       danger=r["danger"], crowd={"H": ends["H"][i], "A": ends["A"][i]}, score=r["score"])
                  for i, r in enumerate(rows)]
    signals = dict(format="tely.signals", version=FORMAT_VERSION, match_id=mid, hz=1, per_second=per_second,
                   events=interpret.event_signals(events, m), crowd_one_shots=crowd.one_shots(mo, t0, t1),
                   haptics=haptics.haptic_cues(m["events"], rows, k, t0, t1))
    step = FPS // PLAYER_HZ
    players = [[round(float(v) + 0.0, 2) for xy in pos25[i] for v in xy] for i in range(0, len(pos25), step)]
    ticks = dict(format="tely.ticks", version=FORMAT_VERSION, match_id=mid, t0=float(t0), duration_s=float(t1 - t0),
                 ball=dict(hz=FPS, columns=["x", "y", "z", "alive", "poss"], rows=ball),
                 players=dict(hz=PLAYER_HZ, ids=ids, rows=players))

    out_dir.mkdir(parents=True, exist_ok=True)
    # SEAM(B->A): meta.json -> A's load_match() (contracts/b match format; judge_cut, teams, periods)
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8", newline="\n")
    # SEAM(B->A): events.jsonl -> A's planner and verifier read the CDF lines (contracts/b match format)
    (out_dir / "events.jsonl").write_text("".join(json.dumps(x, separators=(",", ":")) + "\n" for x in lines),
                                          encoding="utf-8", newline="\n")
    # SEAM(B->A): signals.json -> A's templates read tension, xg, priority, zone, crowd_one_shots (contracts/b)
    (out_dir / "signals.json").write_text(rows_json(signals), encoding="utf-8", newline="\n")
    # SEAM(B->A): ticks.json.gz -> A's Match.ball() and the spatial voice read ball x/y (contracts/b match format)
    (out_dir / "ticks.json.gz").write_bytes(gz(json.dumps(ticks, separators=(",", ":")).encode("utf-8")))
    if report:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(realism_report(cut, np.array(pos25), ids, m), encoding="utf-8", newline="\n")
    return dict(meta=meta, events=lines, signals=signals, ticks=ticks)


# ---------------------------------------------------------------- realism report
def _row(name, ours, target, ok, source):
    return f"| {name} | {ours} | {target} | {'🟢 green' if ok else '🔴 red'} | {source} |"


def realism_report(cut: dict, pos: np.ndarray, ids: list, m: dict, seeds=range(1, 51)) -> str:
    """Green/red against cited targets only (files 02 and 19). Rule: a cited range -> our mean must be inside it;
    a single cited value -> it must fall inside our 95% interval over the seeds. No thresholds of our own."""
    per = []
    for s in seeds:
        evs = generate(s)["events"]
        passes = [e for e in evs if e["type"] == "pass"]
        shots = [e for e in evs if e["type"] == "shot"]
        goals = sum(1 for e in shots if e["outcome_type"] == "successful")
        per.append(dict(passes=len(passes), shots=len(shots), goals=goals,
                        completion=sum(e["is_successful"] for e in passes) / len(passes),
                        conversion=goals / max(1, len(shots))))
    mean = {k: statistics.mean(r[k] for r in per) for k in per[0]}
    ci = {k: 1.96 * statistics.stdev(r[k] for r in per) / math.sqrt(len(per)) for k in per[0]}
    inside = lambda k, lo, hi: lo <= mean[k] <= hi
    covers = lambda k, v: mean[k] - ci[k] <= v <= mean[k] + ci[k]
    v = np.sqrt(((pos[1:] - pos[:-1]) ** 2).sum(axis=2)) * FPS          # report only: not part of the bundle
    outfield = [i for i, p in enumerate(ids) if m["players"][p]["role"] != "GK"]
    dur = (cut["t_end"] - cut["t_start"])
    km90 = v[:, outfield].sum(axis=0) / FPS / 1000 * (90 * 60 / dur)
    top_kmh = v[:, outfield].max(axis=0) * 3.6
    slow = float((v[:, outfield] < 6 / 3.6).mean())
    lines = [
        "# Realism report (Stage 1)",
        "",
        f"Generator v{GENERATOR_VERSION}, events over seeds {seeds.start}-{seeds.stop - 1} (both halves); movement over the "
        f"judge cut (seed {cut['seed']}, {cut['period']} {cut['t_start']}-{cut['t_end']} s, distance scaled to 90 min).",
        "Rule: cited range -> our mean inside it; single cited value -> inside our 95% interval. Targets: files 02 and 19.",
        "",
        "| Metric | Ours | Target | Verdict | Source |",
        "|---|---|---|---|---|",
        _row("Goals per match", f"{mean['goals']:.2f} ± {ci['goals']:.2f}", "2.93", covers("goals", 2.93),
             "file 02 (PL 2024/25)"),
        _row("Passes per match", f"{mean['passes']:.0f}", "893.4–941.0", inside("passes", 893.4, 941.0),
             "file 02 (Opta Analyst)"),
        _row("Shots per match", f"{mean['shots']:.1f}", "25.3–27.6", inside("shots", 25.3, 27.6),
             "file 02 (premierleague.com)"),
        _row("Shot conversion", f"{100 * mean['conversion']:.1f}%", "11–11.9%", inside("conversion", 0.11, 0.119),
             "file 02 (premierleague.com)"),
        _row("Pass completion", f"{100 * mean['completion']:.1f}%", "~84% (unverified)",
             covers("completion", 0.84), "file 02 (unverified)"),
        _row("Distance per 90, outfield mean", f"{km90.mean():.1f} km", "8.5–12.3 km", 8.5 <= km90.mean() <= 12.3,
             "file 19 / file 02"),
        _row("Top speed, outfield (fastest)", f"{top_kmh.max():.1f} km/h", "29.4–37.1 km/h",
             29.4 <= top_kmh.max() <= 37.1, "file 19"),
        _row("Time below 6 km/h", f"{100 * slow:.0f}%", "54–78%", 0.54 <= slow <= 0.78, "file 19"),
        "",
        "Not checked (no cited target in our files): fouls and cards per match, VAR checks, saves.",
    ]
    return "\n".join(lines) + "\n"


def load_cut() -> dict:
    if not CUT_FILE.exists():
        from .judge_cut import find
        CUT_FILE.write_text(json.dumps(find(), indent=2) + "\n", encoding="utf-8", newline="\n")
    return json.loads(CUT_FILE.read_text(encoding="utf-8"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Build the judge-cut match bundle (contracts/b format).")
    ap.add_argument("--cut", default="judge", choices=["judge"])
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--no-report", action="store_true")
    a = ap.parse_args()
    build(load_cut(), a.out or BUNDLE / a.cut, report=not a.no_report)
    print(f"wrote {a.out or BUNDLE / a.cut}" + ("" if a.no_report else f" and {REPORT}"))
