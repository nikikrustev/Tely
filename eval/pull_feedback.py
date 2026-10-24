"""Pull tester-mode feedback (?test=1, D19) out of Application Insights. OWNER: A (potencialbg).

    python eval/pull_feedback.py                    # last 30 days, app and resource group from the azd env "judge"
    python eval/pull_feedback.py --paste mail.txt   # also read "Copy my answers" texts (the AS1. code line)
    python eval/score_listening.py && python eval/build_report.py

1. Runs a KQL query with `az monitor app-insights query` (needs `az login` and the application-insights extension:
   `az extension add --name application-insights`). Keyless, nothing is printed but counts.
2. Writes every event, one row each, to out/feedback/feedback.csv. out/ is git-ignored: free text may contain
   personal details, so it never goes in the repo.
3. Appends one row per tester who took part and answered the questions after BOTH clips to eval/listening_test.csv,
   with mode=self, sight "sighted, eyes closed" unless they told us otherwise, consent from their checkboxes, and no
   free text (quote and notes stay empty: the CSV is public). A tester already in the CSV is never added twice.
"""
from __future__ import annotations

import argparse
import base64
import csv
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from relay.feedback import SCHEMA  # noqa: E402  (stdlib only; the same keys the relay accepts)

sys.path.insert(0, str(ROOT / "eval"))
import score_listening as sl  # noqa: E402

RAW = ROOT / "out" / "feedback" / "feedback.csv"
# customDimensions come back base64-encoded: piped on Windows, az writes in the ANSI code page and drops Cyrillic
# (seen 24 Oct; az.cmd runs Python with -I, so PYTHONUTF8 can't fix it). Base64 is ASCII, so nothing is lost.
KQL = ("customEvents | where name == 'tester_feedback' "
       "| project timestamp, d = base64_encode_tostring(tostring(customDimensions)) | order by timestamp asc")
SCREEN_READERS = {"none": "none", "nvda": "NVDA", "jaws": "JAWS", "narrator": "Narrator", "voiceover": "VoiceOver",
                  "talkback": "TalkBack", "other": "other"}
DEVICES = {"android_phone": "Android phone", "iphone": "iPhone", "windows": "Windows computer", "mac": "Mac",
           "tablet": "tablet", "other": "other"}
SIGHT = {"blind": "blind", "partially_sighted": "partially_sighted", "sighted": "sighted, eyes closed"}


def _run(args: list[str]) -> str:
    exe = shutil.which(args[0])
    if exe is None:
        raise SystemExit(f"{args[0]} not found on PATH")
    out = subprocess.run([exe, *args[1:]], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    if out.returncode != 0:
        raise SystemExit(f"{args[0]} {args[1]} failed: {out.stderr.strip()[:400]}")
    return out.stdout


def azd_value(name: str, env: str) -> str:
    return _run(["azd", "env", "get-value", name, "-e", env]).strip()


def query(app: str, rg: str, days: int) -> list[dict]:
    """Every tester_feedback event as {"timestamp", **customDimensions}."""
    res = json.loads(_run(["az", "monitor", "app-insights", "query", "--app", app, "-g", rg,
                           "--analytics-query", KQL, "--offset", f"{days}d", "-o", "json"]))
    table = res["tables"][0]
    cols = [c["name"] for c in table["columns"]]
    events = []
    for row in table["rows"]:
        r = dict(zip(cols, row))
        dims = json.loads(base64.b64decode(r.get("d") or "e30=").decode("utf-8"))
        events.append({"timestamp": r.get("timestamp"), **{k: v for k, v in dims.items() if k in SCHEMA}})
    return events


def from_paste(text: str) -> list[dict]:
    """Events from "Copy my answers" texts: every AS1.<base64 JSON> code line (web/src/tester/payload.ts codeLine)."""
    events = []
    for m in re.finditer(r"AS1\.([A-Za-z0-9+/=]+)", text):
        for ev in json.loads(base64.b64decode(m.group(1)).decode("utf-8")):
            events.append({"timestamp": None, **{k: str(v).lower() if isinstance(v, bool) else str(v)
                                                for k, v in ev.items() if k in SCHEMA}})
    return events


def dedupe(events: list[dict]) -> list[dict]:
    """One copy per (tester, eid): a retried POST or a pasted copy of a sent answer counts once."""
    seen, out = set(), []
    for e in events:
        key = (e.get("tester"), e.get("eid"))
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def write_raw(events: list[dict], path: Path = RAW) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["timestamp", *SCHEMA], extrasaction="ignore")
        w.writeheader()
        w.writerows(events)


def per_tester(events: list[dict]) -> dict[str, dict]:
    """Each tester's latest answer of each kind (a redone task replaces the earlier answer)."""
    out: dict[str, dict] = {}
    for e in events:
        t = out.setdefault(e["tester"], {"group": e.get("group"), "first": e.get("timestamp"), "clips": {}})
        if e.get("consent_take_part") is not None:
            t["take_part"], t["quote"] = e.get("consent_take_part"), e.get("consent_quote")
        kind = e.get("kind")
        if kind == "clip" and e.get("clip") in ("1", "2"):
            t["clips"][e["clip"]] = e
        elif kind in ("ask", "overall"):
            t[kind] = e
    return out


def listening_row(tid: str, t: dict) -> dict | None:
    """A listening_test.csv row for a tester who took part and finished both clips' questions, else None."""
    if t.get("take_part") != "true" or not {"1", "2"} <= t["clips"].keys():
        return None
    o, a = t.get("overall", {}), t.get("ask")
    row = {c: "" for c in sl.COLUMNS}
    row.update({
        "participant": tid, "session_date": (t.get("first") or "")[:10], "group": t["group"],
        "sight": SIGHT.get(o.get("sight", ""), "sighted, eyes closed"),
        "screen_reader": SCREEN_READERS.get(o.get("screen_reader", ""), ""), "device": DEVICES.get(o.get("device", ""), ""),
        "headphones": {"wired": "yes", "bluetooth": "yes", "none": "no"}.get(o.get("headphones", ""), ""),
        "listened_via": "own_device", "preferred": o.get("preferred", ""),
        "consent_take_part": "yes", "consent_quote": "yes" if t.get("quote") == "true" else "no", "consent_film": "no",
        "mode": "self",
    })
    for i in ("1", "2"):
        c = t["clips"][i]
        for k in sl.PROBES:
            row[f"c{i}_{k}"] = c.get(f"{k}_ok", "")
        for k in sl.SCALE:
            row[f"c{i}_{k}"] = c.get(k, "")
    if a:
        tried = int(a.get("ask_presets", "0")) > 0 or a.get("ask_live_tried") == "true"
        row["ask_tried"] = "yes" if tried else "no"
        if tried and a.get("ask_worked") in ("yes", "partly", "no"):
            row["ask_worked"] = a["ask_worked"]
    return row


def append_listening(testers: dict[str, dict], path: Path = sl.CSV) -> list[str]:
    """Append new finished testers to the CSV; returns their codes."""
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != sl.COLUMNS:
            raise SystemExit(f"{path.name}: columns differ from score_listening.COLUMNS; fix the header first")
        have = {r["participant"] for r in reader}
    rows = [r for tid, t in sorted(testers.items()) if tid not in have and (r := listening_row(tid, t))]
    if rows:
        with path.open("a", encoding="utf-8", newline="") as f:
            csv.DictWriter(f, fieldnames=sl.COLUMNS, lineterminator="\n").writerows(rows)
    return [r["participant"] for r in rows]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Tester-mode feedback from App Insights -> out/feedback + listening CSV")
    ap.add_argument("--env", default="judge", help="azd env that holds APPLICATIONINSIGHTS_NAME and AZURE_RESOURCE_GROUP")
    ap.add_argument("--app", help="App Insights name (default: from the azd env)")
    ap.add_argument("--rg", help="resource group (default: from the azd env)")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--paste", type=Path, nargs="*", default=[], help='"Copy my answers" texts to read too')
    ap.add_argument("--no-query", action="store_true", help="only read --paste files")
    ap.add_argument("--dry-run", action="store_true", help="don't touch eval/listening_test.csv")
    args = ap.parse_args(argv)
    events: list[dict] = []
    if not args.no_query:
        app = args.app or azd_value("APPLICATIONINSIGHTS_NAME", args.env)
        rg = args.rg or azd_value("AZURE_RESOURCE_GROUP", args.env)
        events += query(app, rg, args.days)
    for p in args.paste:
        events += from_paste(p.read_text(encoding="utf-8"))
    events = dedupe([e for e in events if e.get("tester")])
    write_raw(events)
    testers = per_tester(events)
    added = [] if args.dry_run else append_listening(testers)
    finished = sum(1 for tid, t in testers.items() if listening_row(tid, t))
    print(f"{len(events)} events from {len(testers)} testers -> {RAW.relative_to(ROOT)}; "
          f"{finished} finished both clips; {len(added)} new rows in eval/listening_test.csv"
          + (" (dry run)" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
