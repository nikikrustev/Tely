"""Score the eyes-closed listening test: eval/listening_test.csv -> eval/listening.json. Stdlib only, no Azure, no keys.

    python eval/score_listening.py
    python eval/build_report.py        # puts the summary into eval/report.md and eval/report.json

The protocol is eval/listening_test.md: two 3-minute clips (commentary only vs full Tely), four comprehension
probes per clip (1 = right, 0 = wrong) and our 3 x 1-5 version of RNIB's 15-point scale. The CSV has one row per
participant; c1_* is Clip 1 and c2_* is Clip 2, and `group` says which clip had the full sound.

Nothing is ever filled in: with no participants the JSON says "not run yet" and holds no numbers. A bad value stops
the script with its row number instead of being guessed. Quotes are kept only where consent_quote is yes, and a row
without consent_take_part = yes is left out of every number.

`mode` says how a row was collected: "moderated" (blank means the same: one-to-one, section 4) or "self" (tester mode,
?test=1, appended by eval/pull_feedback.py, D19). Self-run rows are summarised apart under "self_run" and never mixed
into the moderated numbers: they are mostly sighted friends with their eyes closed, answering multiple-choice probes,
and that is not evidence for blind fans (file 36).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSV = HERE / "listening_test.csv"
OUT = HERE / "listening.json"

PROBES = ("where", "side", "danger", "scored")
SCALE = ("enjoy", "access", "follow")
CLIP_COLS = PROBES + SCALE
COLUMNS = (["participant", "session_date", "group", "sight", "screen_reader", "device", "headphones", "listened_via"]
           + [f"c{i}_{k}" for i in (1, 2) for k in CLIP_COLS]
           + ["preferred", "ask_tried", "ask_worked", "consent_take_part", "consent_quote", "consent_film", "quote",
              "notes", "mode"])
# Which condition each clip had, by group (eval/listening_test.md section 1).
GROUPS = {"A": {1: "commentary", 2: "full"}, "B": {1: "full", 2: "commentary"}}
CONDITIONS = ("commentary", "full")
SIGHT = ("blind", "partially_sighted", "sighted", "sighted, eyes closed")   # the last: self-run default (D19)
MODES = ("moderated", "self")
VIA = ("own_device", "shared_audio", "in_person")
RNIB_REFERENCE = {"score": 6.1, "out_of": 15, "what": "TV football broadcasts in general",
                  "source": "RNIB, Accessibility of Football Broadcasts on TV (Nov 2022), 10 interviews (file 36)",
                  "note": "a different study and a different scale wording: a reference point, not a baseline"}
SELF_NOTE = ("Self-run, sighted volunteers: friends of the team who followed tester mode (?test=1) on their own "
             "device with nobody watching, eyes closed by request, answering multiple-choice versions of the four "
             "probes (each with \"Don't know\"). They are not blind or partially sighted fans, a multiple-choice probe "
             "is easier to get right than the moderated open question, and nobody checked that their eyes stayed "
             "closed. These results are reported apart from the moderated sessions and are not evidence for blind "
             "fans (file 36).")
SCALE_NOTE = ("Our version of RNIB's 15-point scale: enjoyment, access and following, each 1-5, added up to 3-15 "
              "(eval/listening_test.md section 6; RNIB's per-item wording is unverified).")


class CsvError(ValueError):
    pass


def _choice(row: dict, col: str, allowed: tuple[str, ...], line: int, blank_ok: bool = True) -> str | None:
    v = (row.get(col) or "").strip().lower()
    if not v and blank_ok:
        return None
    if v not in allowed:
        raise CsvError(f"row {line}: {col} = {row.get(col)!r}, expected one of {', '.join(allowed)}")
    return v


def _int(row: dict, col: str, lo: int, hi: int, line: int) -> int | None:
    v = (row.get(col) or "").strip()
    if not v:
        return None
    if not v.isdigit() or not lo <= int(v) <= hi:
        raise CsvError(f"row {line}: {col} = {v!r}, expected a whole number from {lo} to {hi}")
    return int(v)


def parse(row: dict, line: int) -> dict:
    """One CSV row -> one participant, with the two clips keyed by condition."""
    pid = (row.get("participant") or "").strip()
    if not pid:
        raise CsvError(f"row {line}: participant is empty (use P01, P02, ...)")
    group = (row.get("group") or "").strip().upper()
    if group not in GROUPS:
        raise CsvError(f"row {line}: group = {row.get('group')!r}, expected A or B")
    clips = {}
    for i in (1, 2):
        probes = {k: _int(row, f"c{i}_{k}", 0, 1, line) for k in PROBES}
        scale = {k: _int(row, f"c{i}_{k}", 1, 5, line) for k in SCALE}
        total = sum(scale.values()) if all(v is not None for v in scale.values()) else None
        clips[GROUPS[group][i]] = {"clip": i, "probes": probes, "scale": scale, "total": total}
    pref = _choice(row, "preferred", ("1", "2", "none"), line)
    return {
        "participant": pid,
        "session_date": (row.get("session_date") or "").strip() or None,
        "group": group,
        "sight": _choice(row, "sight", SIGHT, line),
        "listened_via": _choice(row, "listened_via", VIA, line),
        "headphones": _choice(row, "headphones", ("yes", "no"), line),
        "clips": clips,
        "preferred": pref if pref in (None, "none") else GROUPS[group][int(pref)],
        "ask_tried": _choice(row, "ask_tried", ("yes", "no"), line),
        "ask_worked": _choice(row, "ask_worked", ("yes", "partly", "no"), line),
        "consent": {k: _choice(row, f"consent_{k}", ("yes", "no"), line) for k in ("take_part", "quote", "film")},
        "quote": (row.get("quote") or "").strip() or None,
        "mode": _choice(row, "mode", MODES, line) or "moderated",
    }


def read(path: Path = CSV) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise CsvError(f"{path.name}: missing columns {', '.join(missing)}")
        rows = [(n, r) for n, r in enumerate(reader, start=2) if any((v or "").strip() for v in r.values())]
    out = [parse(r, n) for n, r in rows]
    seen = [p["participant"] for p in out]
    dupes = sorted({p for p in seen if seen.count(p) > 1})
    if dupes:
        raise CsvError(f"{path.name}: participant listed twice: {', '.join(dupes)}")
    return out


def _mean(xs: list[float]) -> float | None:
    return round(sum(xs) / len(xs), 2) if xs else None


def _count(values, keys) -> dict:
    return {k: sum(1 for v in values if v == k) for k in keys}


def condition_summary(people: list[dict], cond: str) -> dict:
    clips = [p["clips"][cond] for p in people]
    totals = [c["total"] for c in clips if c["total"] is not None]
    asked = [v for c in clips for v in c["probes"].values() if v is not None]
    return {
        "n": len(totals),
        "scale_mean": _mean(totals),
        "scale_min": min(totals) if totals else None,
        "scale_max": max(totals) if totals else None,
        **{f"{k}_mean": _mean([c["scale"][k] for c in clips if c["scale"][k] is not None]) for k in SCALE},
        "probes_right": sum(asked),
        "probes_asked": len(asked),
        "probes_pct": round(100 * sum(asked) / len(asked), 1) if asked else None,
    }


def summarise(people: list[dict], excluded: int = 0) -> dict:
    base = {"source": "eval/listening_test.csv", "protocol": "eval/listening_test.md"}
    if not people:
        return {"status": "not run yet", "participants": 0, "excluded_no_consent": excluded, **base}
    pairs = [(p["clips"]["full"]["total"], p["clips"]["commentary"]["total"]) for p in people
             if p["clips"]["full"]["total"] is not None and p["clips"]["commentary"]["total"] is not None]
    diffs = [f - c for f, c in pairs]
    dates = sorted(d for d in (p["session_date"] for p in people) if d)

    def probe_line(k: str, cond: str) -> str:
        vals = [p["clips"][cond]["probes"][k] for p in people if p["clips"][cond]["probes"][k] is not None]
        return f"{sum(vals)}/{len(vals)}"

    vip = [p for p in people if p["sight"] in ("blind", "partially_sighted")]
    out = {
        "status": "run",
        "participants": len(people),
        "excluded_no_consent": excluded,
        "sessions": f"{dates[0]} to {dates[-1]}" if dates else None,
        "groups": _count([p["group"] for p in people], GROUPS),
        "sight": {**_count([p["sight"] for p in people], SIGHT), "not said": sum(1 for p in people if not p["sight"])},
        "listened_via": {**_count([p["listened_via"] for p in people], VIA),
                         "not recorded": sum(1 for p in people if not p["listened_via"])},
        "conditions": {c: condition_summary(people, c) for c in CONDITIONS},
        "probes": {k: {c: probe_line(k, c) for c in CONDITIONS} for k in PROBES},
        "paired": {"n": len(diffs), "mean_full_minus_commentary": _mean(diffs),
                   "full_higher": sum(1 for d in diffs if d > 0), "same": sum(1 for d in diffs if d == 0),
                   "commentary_higher": sum(1 for d in diffs if d < 0)},
        "preferred": {**_count([p["preferred"] for p in people], CONDITIONS + ("none",)),
                      "not asked": sum(1 for p in people if p["preferred"] is None)},
        "ask": {"tried": sum(1 for p in people if p["ask_tried"] == "yes"),
                **_count([p["ask_worked"] for p in people if p["ask_tried"] == "yes"], ("yes", "partly", "no"))},
        "blind_or_partially_sighted": {"participants": len(vip),
                                       **({c: condition_summary(vip, c) for c in CONDITIONS} if vip else {})},
        "quotes": [{"participant": p["participant"], "sight": p["sight"], "quote": p["quote"]}
                   for p in people if p["quote"] and p["consent"]["quote"] == "yes"],
        "rows": [{"participant": p["participant"], "group": p["group"], "sight": p["sight"],
                  "listened_via": p["listened_via"],
                  "commentary_scale": p["clips"]["commentary"]["total"], "full_scale": p["clips"]["full"]["total"],
                  "commentary_probes": _probes(p["clips"]["commentary"]), "full_probes": _probes(p["clips"]["full"]),
                  "preferred": p["preferred"], "ask_worked": p["ask_worked"]} for p in people],
        "scale_note": SCALE_NOTE,
        "rnib_reference": RNIB_REFERENCE,
        **base,
    }
    return out


def _probes(clip: dict) -> str | None:
    vals = [v for v in clip["probes"].values() if v is not None]
    return f"{sum(vals)}/{len(vals)}" if vals else None


def score(path: Path = CSV) -> dict:
    """The moderated sessions at the top level (as before), the self-run testers apart under "self_run"."""
    everyone = read(path)
    out = {}
    for mode in MODES:
        rows = [p for p in everyone if p["mode"] == mode]
        people = [p for p in rows if p["consent"]["take_part"] == "yes"]
        out[mode] = summarise(people, excluded=len(rows) - len(people))
    return {**out["moderated"], "self_run": {**out["self"], "note": SELF_NOTE}}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Score eval/listening_test.csv into eval/listening.json")
    ap.add_argument("--csv", type=Path, default=CSV)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)
    try:
        res = score(args.csv)
    except CsvError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    args.out.write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"{res['participants']} moderated participants ({res['status']}), "
          f"{res['self_run']['participants']} self-run -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
