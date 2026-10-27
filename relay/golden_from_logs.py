"""Save the deployed relay's golden turns from its console logs to eval/live/.

    python -m relay.golden_from_logs --since 3h            # after a live test session with a real mic (needs az login)

The relay prints one {"golden_turn": {...}} JSON line per answered question (relay/voicelive.py): question, tool calls
with args and results, spoken answer, latency. No keys, tokens or audio are ever in it. Container Apps ships those lines
to the Log Analytics workspace, and this script appends the new ones to eval/live/live_<date>.jsonl, one file
per UTC day of the turn, skipping turns already saved. Then tell Nikolay: B turns them into
regression tests in pipeline/tests/.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "eval" / "live"


def az(*args: str) -> str:
    return subprocess.run(["az", *args, "-o", "json"], check=True, capture_output=True, text=True, shell=sys.platform == "win32").stdout


def fetch(rg: str, workspace: str, since: str) -> list[dict]:
    cid = json.loads(az("monitor", "log-analytics", "workspace", "show", "-g", rg, "-n", workspace, "--query", "customerId"))
    # The console-log table and its column are named differently on the two schemas; ask for both (file 21).
    q = (f"union isfuzzy=true ContainerAppConsoleLogs_CL, ContainerAppConsoleLogs | where TimeGenerated > ago({since}) "
         "| extend line = coalesce(column_ifexists('Log_s', ''), column_ifexists('Log', '')) "
         "| where line has 'golden_turn' | project TimeGenerated, line | order by TimeGenerated asc")
    rows = json.loads(az("monitor", "log-analytics", "query", "-w", cid, "--analytics-query", q))
    turns = []
    for r in rows:
        try:
            turns.append(json.loads(r["line"])["golden_turn"])
        except (KeyError, ValueError, TypeError):
            continue
    return turns


def save(turns: list[dict]) -> int:
    GOLDEN.mkdir(parents=True, exist_ok=True)
    added = 0
    for day in sorted({t["at"][:10] for t in turns}):
        f = GOLDEN / f"live_{day}.jsonl"
        have = set()
        if f.is_file():
            have = {(j.get("at"), j.get("question"), j.get("answer")) for j in map(json.loads, f.read_text(encoding="utf-8").splitlines()) if j}
        new = [t for t in turns if t["at"][:10] == day and (t.get("at"), t.get("question"), t.get("answer")) not in have]
        with f.open("a", encoding="utf-8", newline="\n") as out:
            for t in new:
                out.write(json.dumps({**t, "source": "relay console log (deployed)"}, ensure_ascii=False) + "\n")
        added += len(new)
        print(f"{f.relative_to(ROOT)}: +{len(new)}")
    return added


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--since", default="24h", help="Kusto timespan, e.g. 3h or 2d")
    ap.add_argument("-g", "--resource-group", default="rg-as-judge")
    ap.add_argument("-w", "--workspace", default="log-as-judge")
    a = ap.parse_args()
    turns = [t for t in fetch(a.resource_group, a.workspace, a.since) if t.get("outcome") != "cancelled"]
    print(f"{len(turns)} answered turns in the logs; {save(turns)} new")
    return 0


if __name__ == "__main__":
    sys.exit(main())
