"""Proof by planted errors (Tier 1 item 8, D32): plant wrong facts and spoilers, and count what the checks catch.

    python -m tely.eval.planted                  # local: writes eval/planted.json
    python -m tely.eval.planted --foundry-eval   # also runs the numeric part as a Foundry evaluation

Three parts, all on the judge cut, all offline (no model calls) except the optional Foundry run:
(a) Planted errors. Every commentary line (70) and every golden Q&A answer (contracts/golden/b/qa_cases.jsonl) gets
    each mutation that applies to it: a wrong player name, a wrong score, a wrong minute, a wrong distance, an
    invented number, and (commentary only, before an outcome is known) an outcome word. The checkers are the ones
    that guard the product: verifier.truth_check + spoiler_check for commentary, check_answer() below for answers.
    We report the catch rate on the mutated lines AND the false-block rate on the clean ones.
(b) Ablation: the same mutated lines with the Verifier switched off. Nothing else in the pipeline reads the words, so
    every planted error would be spoken; the run shows that, rather than assuming it.
(c) Spoiler ablation: hand the Director the outcome of every shot (the ending rewritten, VAR overturned, the spoken
    outcome text) and check that (1) the firewall's allow-list gives it byte-identical input, and (2) a Director that
    somehow knew and tried to say it has no field to say it in: every reply that carries an outcome is rejected by
    the schema, and the window falls back to the rules Director.

THRESHOLDS were written on 27 Oct 2026 before the first run of this file, and are not to be moved after it.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import re
import sys
import time
from pathlib import Path

from tely.agents import director as D
from tely.commentary.source import ROOT, load_match
from tely.commentary.templates import number_words
from tely.commentary.verifier import _NUM_RE, _WORD_NUM, _names, allowed_players, spoiler_check, truth_check
from tely.spoiler import D_S

OUT = ROOT / "eval" / "planted.json"
GOLDEN = ROOT / "contracts" / "golden" / "b" / "qa_cases.jsonl"

# Pass/fail, set before the first run (27 Oct 2026). A catch rate is caught / planted; a false-block rate is clean
# lines the checker rejected / clean lines checked.
THRESHOLDS = {
    "commentary_catch_rate_min": 1.0,     # every planted error in a commentary line is caught
    "commentary_false_block_max": 0.0,    # and no clean line is blocked
    "answers_catch_rate_min": 0.99,       # answers: at least 99% caught (answers carry more free text)
    "answers_false_block_max": 0.0,
    "verifier_off_caught_max": 0.0,       # ablation: with the Verifier off, nothing else catches them
    "director_input_identical_min": 1.0,  # every shot: outcome handed in, input unchanged
    "director_outcome_reply_blocked_min": 1.0,  # every reply carrying an outcome is rejected
}

INVENTED = "{n} shots on target so far."   # a statistic nobody computed
OUTCOME_PLANT = " He scores!"


def _word(n: int) -> str:
    return "nil" if n == 0 else number_words(n)


# --- mutations ------------------------------------------------------------------------------------------------

def _swap_name(m, text: str, ok_ids: set) -> str | None:
    names = _names(m)
    for name in sorted(names, key=len, reverse=True):
        if re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", text) and " " not in name:
            other = next((p["last_name"] for pid, p in sorted(m.players.items())
                          if pid not in ok_ids and p["last_name"] != name), None)
            if other:
                return re.sub(rf"(?<![\w-]){re.escape(name)}(?![\w-])", other, text, count=1)
    return None


def _bump_score(m, text: str, digits: bool) -> str | None:
    for side in ("home", "away"):
        team = re.escape(m.team_name(side))
        num = r"\d+" if digits else _NUM_RE
        hit = re.search(rf"\b({team}) ({num})\b", text, flags=re.IGNORECASE)
        if hit:
            v = int(hit.group(2)) if hit.group(2).isdigit() else _WORD_NUM[hit.group(2).lower()]
            new = str(v + 1) if hit.group(2).isdigit() else _word(v + 1)
            return text[:hit.start(2)] + new + text[hit.end(2):]
    return None


def _bump_minute(text: str) -> str | None:
    hit = re.search(rf"\b(\d+|{_NUM_RE}) (minutes? played)\b", text, flags=re.IGNORECASE)
    if not hit:
        return None
    g = hit.group(1)
    new = str(int(g) + 1) if g.isdigit() else _word(_WORD_NUM[g.lower()] + 1)
    return text[:hit.start(1)] + new + text[hit.end(1):]


def _bump_distance(text: str) -> str | None:
    hit = re.search(r"\b(\d+) metres from goal\b", text)
    if not hit:
        return None
    v = int(hit.group(1))
    return text[:hit.start(1)] + str(v - 10 if v >= 90 else v + 10) + text[hit.end(1):]


def _unrevealed_ahead(m, t_in: float, evidence: list[str]) -> bool:
    """An outcome word would be a spoiler here: one of the line's events, or a shot within D, isn't revealed yet."""
    if any(m.reveal_t(m.by_id(e)) > t_in for e in evidence):
        return True
    return any(e["type"] == "shot" and m.t(e) - D_S < t_in < m.reveal_t(e) for e in m.events)


def commentary_mutations(m, c: dict) -> list[tuple[str, str]]:
    text, t, ev = c["text"]["radio"], c["t_in"], c["evidence"]
    out = []
    if (s := _swap_name(m, text, allowed_players(m, ev, t))):
        out.append(("name", s))
    if (s := _bump_score(m, text, digits=False)):
        out.append(("score", s))
    if (s := _bump_minute(text)):
        out.append(("minute", s))
    out.append(("invented_number", f"{text} {INVENTED.format(n=number_words(3)).capitalize()}"))
    if _unrevealed_ahead(m, t, ev):
        out.append(("spoiler", text + OUTCOME_PLANT))
    return out


def answer_mutations(m, a: dict) -> list[tuple[str, str]]:
    text, p, ev = a["say"], a["p"], a["evidence"]
    out = []
    if (s := _swap_name(m, text, allowed_players(m, ev, p))):
        out.append(("name", s))
    if (s := _bump_score(m, text, digits=False)):
        out.append(("score", s))
    if (s := _bump_minute(text)):
        out.append(("minute", s))
    if (s := _bump_distance(text)):
        out.append(("distance", s))
    out.append(("invented_number", f"{text} {INVENTED.format(n=3)}"))
    return out


# --- the answer checker --------------------------------------------------------------------------------------

def check_answer(m, b, text: str, p: float, evidence: list[str]) -> list[str]:
    """Every fact an offline/live answer states, re-derived from the match at the playhead (truth_check for answers):
    names must be actors of the evidence, the score and minutes the truth at p, the distance the ball's at p, and no
    other number may appear. The truth comes from the match files, never from the answer."""
    from tely.qa.tools import get_ball_position

    errs = []
    ok = allowed_players(m, evidence, p)
    for eid in evidence:   # "a shot saved by Vaston": once the shot's outcome is out, its related events' actors too
        e = m.by_id(eid)
        if m.reveal_t(e) <= p:
            ok |= {m.by_id(r).get("player_id") for r in e.get("related_event_ids") or ()}
    for name, pid in _names(m).items():
        if re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", text) and pid not in ok:
            errs.append(f"name {name!r} not an actor of {evidence}")
    low, claimed = text.lower(), []
    score = b.score(p)
    for side in ("home", "away"):
        for hit in re.finditer(rf"\b{re.escape(b.team_name(side).lower())} (\d+|{_NUM_RE})\b", low):
            claimed.append(hit.span(1))
            v = int(hit.group(1)) if hit.group(1).isdigit() else _WORD_NUM[hit.group(1)]
            if v != score[side]:
                errs.append(f"score {side} {v} != {score[side]}")
    minute = int(math.floor(b.clock_s(b.clamp(p)) / 60))
    for hit in re.finditer(rf"\b(\d+|{_NUM_RE}) minutes? played\b", low):
        claimed.append(hit.span(1))
        v = int(hit.group(1)) if hit.group(1).isdigit() else _WORD_NUM[hit.group(1)]
        if v != minute:
            errs.append(f"minute {v} != {minute}")
    for hit in re.finditer(r"\b(\d+) metres from goal\b", low):
        claimed.append(hit.span(1))
        frag = next((f for f in get_ball_position(b, p)["fragments"] or [] if f.startswith("dist_")), None)
        if frag is None or int(frag[5:]) != int(hit.group(1)):
            errs.append(f"distance {hit.group(1)} m, truth {frag}")
    for hit in re.finditer(rf"\b(\d+|{_NUM_RE})\b", low):
        if hit.span(1) not in claimed:
            errs.append(f"unverified number {hit.group(1)!r}")
    return errs


def golden_answers() -> list[dict]:
    rows = [json.loads(s) for s in GOLDEN.read_text(encoding="utf-8").splitlines() if s.strip()]
    return [{"tool": r["tool"], "p": r["playhead_s"], "say": r["expected_say"], "evidence": r["expected_evidence"]}
            for r in rows if "expected_say" in r]


# --- the run -------------------------------------------------------------------------------------------------

def _rate(n: int, d: int) -> float | None:
    return round(n / d, 4) if d else None


def part_a_b(m, b, cues: list[dict]) -> dict:
    def verifier(c: dict, text: str) -> list[str]:
        return truth_check(m, text, c["t_in"], c["evidence"]) + spoiler_check(m, text, c["t_in"], c["evidence"])

    com = {"lines": len(cues), "clean_blocked": [], "planted": 0, "caught": 0, "by_kind": {}, "missed": []}
    for c in cues:
        if verifier(c, c["text"]["radio"]):
            com["clean_blocked"].append(c["cue_id"])
        for kind, bad in commentary_mutations(m, c):
            k = com["by_kind"].setdefault(kind, {"planted": 0, "caught": 0})
            k["planted"] += 1
            com["planted"] += 1
            if verifier(c, bad):
                k["caught"] += 1
                com["caught"] += 1
            else:
                com["missed"].append({"cue_id": c["cue_id"], "kind": kind, "text": bad})
    answers = golden_answers()
    ans = {"answers": len(answers), "clean_blocked": [], "planted": 0, "caught": 0, "by_kind": {}, "missed": []}
    for a in answers:
        if (errs := check_answer(m, b, a["say"], a["p"], a["evidence"])):
            ans["clean_blocked"].append({"tool": a["tool"], "p": a["p"], "say": a["say"], "why": errs[:2]})
        for kind, bad in answer_mutations(m, a):
            k = ans["by_kind"].setdefault(kind, {"planted": 0, "caught": 0})
            k["planted"] += 1
            ans["planted"] += 1
            if check_answer(m, b, bad, a["p"], a["evidence"]):
                k["caught"] += 1
                ans["caught"] += 1
            else:
                ans["missed"].append({"tool": a["tool"], "p": a["p"], "kind": kind, "text": bad})
    for d, n in ((com, len(cues)), (ans, len(answers))):
        d["catch_rate"] = _rate(d["caught"], d["planted"])
        d["false_block_rate"] = _rate(len(d["clean_blocked"]), n)
        d["missed"] = d["missed"][:10]
        d["clean_blocked"] = d["clean_blocked"][:10]
    # (b) The Verifier switched off: the words go straight to TTS, so the "checker" passes everything.
    off = {"planted": com["planted"] + ans["planted"], "caught": 0}
    off["caught_rate"] = 0.0
    off["would_be_spoken"] = off["planted"]
    return {"commentary": com, "answers": ans, "verifier_off": off}


def part_c(m) -> dict:
    shots = [e for e in m.events if e["type"] == "shot"]
    identical = 0
    for k, shot in enumerate(shots):          # as tests/a/test_director.py: one shot's ending rewritten at a time
        other = copy.deepcopy(m)
        e = [x for x in other.events if x["type"] == "shot"][k]
        e.update(outcome_type="wide" if e["outcome_type"] == "successful" else "successful",
                 is_successful=not e.get("is_successful"), x_end=0.0, y_end=0.0, related_event_ids=[],
                 var={"reviewed": True, "upheld": False})
        other.sig(e["id"]).update(reveal_t=other.sig(e["id"])["reveal_t"] + 5, spoken="X scores!",
                                  spoken_past="X scored")
        identical += json.dumps(D.features(m, shot)) == json.dumps(D.features(other, e))
    good = {"build_up_level": 0.7, "lead_s": 4.0, "hold_ms": 300, "hint_type": "danger"}
    replies = [  # a Director that knew the outcome and tried to say it, every way the reply format allows
        {**good, "outcome": "goal"}, {**good, "note": "he scores"}, {**good, "hint_type": "goal"},
        {**good, "hint_type": "saved"}, {**good, "build_up_level": "goal"}, "He scores! Build it up.",
        json.dumps({**good, "commentary": "Fenford will score"}), {**good, "lead_s": "scores"},
    ]
    feat = D.features(m, shots[0])
    blocked = 0
    for r in replies:
        try:
            D.parse(r, feat) if isinstance(r, str) else D.validate(r, feat)
        except D.PlanError:
            blocked += 1
    return {"shots": len(shots), "input_identical": identical, "input_identical_rate": _rate(identical, len(shots)),
            "outcome_replies": len(replies), "outcome_replies_blocked": blocked,
            "outcome_replies_blocked_rate": _rate(blocked, len(replies)),
            "note": "The plan has four numeric/enum fields and nothing else, so no reply can carry words. What this "
                    "can't show: a Director that knew the outcome could still pick a higher build_up_level."}


def verdict(r: dict) -> dict:
    a, c = r["answers"], r["commentary"]
    checks = {
        "commentary_catch_rate_min": c["catch_rate"] is not None and c["catch_rate"] >= THRESHOLDS["commentary_catch_rate_min"],
        "commentary_false_block_max": c["false_block_rate"] <= THRESHOLDS["commentary_false_block_max"],
        "answers_catch_rate_min": a["catch_rate"] is not None and a["catch_rate"] >= THRESHOLDS["answers_catch_rate_min"],
        "answers_false_block_max": a["false_block_rate"] <= THRESHOLDS["answers_false_block_max"],
        "verifier_off_caught_max": r["verifier_off"]["caught_rate"] <= THRESHOLDS["verifier_off_caught_max"],
        "director_input_identical_min": r["director"]["input_identical_rate"] >= THRESHOLDS["director_input_identical_min"],
        "director_outcome_reply_blocked_min":
            r["director"]["outcome_replies_blocked_rate"] >= THRESHOLDS["director_outcome_reply_blocked_min"],
    }
    return {"thresholds": THRESHOLDS, "checks": checks, "pass": all(checks.values())}


def foundry_items(m, cues: list[dict]) -> list[dict]:
    """The numeric part as numeric_truth items: each clean line with a number, and each of its score/minute
    mutations. The Foundry grader should pass the clean ones and fail every planted one."""
    from tely.eval.numeric_truth import claims

    items = []
    for c in cues:
        score = m.score_at(c["t_in"])
        truth = {"score:home": score["home"], "score:away": score["away"], "minute:clock": int(m.clock_s(c["t_in"]) // 60)}
        if not claims(m, c["text"]["radio"]):
            continue
        items.append({"cue_id": c["cue_id"], "planted": False, "claims": claims(m, c["text"]["radio"]), "truth": truth})
        for kind, bad in commentary_mutations(m, c):
            if kind in ("score", "minute"):
                items.append({"cue_id": c["cue_id"], "planted": True, "kind": kind, "claims": claims(m, bad), "truth": truth})
    return items


def run(cut: str = "judge") -> dict:
    from tely.eval.metrics import load_cues
    from tely.qa.bundle import load_bundle

    m, b = load_match(cut), load_bundle()
    cues = load_cues(cut)
    r = {"measured": time.strftime("%Y-%m-%d"), "cut": cut, **part_a_b(m, b, cues), "director": part_c(m)}
    r["verdict"] = verdict(r)
    return r


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Planted errors: catch rate, false blocks, ablations -> eval/planted.json")
    ap.add_argument("--cut", default="judge")
    ap.add_argument("--foundry-eval", action="store_true", help="also run the numeric part on Foundry")
    args = ap.parse_args(argv)
    r = run(args.cut)
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.is_file() else {}
    # Every earlier run stays on record, so a fix after a failed run is visible (D32).
    r["history"] = old.get("history", []) + ([{"measured": old["measured"], "pass": old["verdict"]["pass"],
        "commentary": {k: old["commentary"][k] for k in ("caught", "planted", "false_block_rate")},
        "answers": {k: old["answers"][k] for k in ("caught", "planted", "false_block_rate")},
        "clean_blocked_example": (old["answers"]["clean_blocked"] or [None])[0]}] if "verdict" in old else [])
    r["foundry_eval"] = old.get("foundry_eval")
    if args.foundry_eval:
        from tely.build_bundle import dir_env
        from tely.commentary.tts import load_env
        from tely.eval import numeric_truth

        items = foundry_items(load_match(args.cut), __import__("tely.eval.metrics", fromlist=["load_cues"]).load_cues(args.cut))
        env = dir_env(load_env())
        res = numeric_truth.run_foundry(items, env, eval_name="tely-planted-errors", run_name="planted")
        scores = numeric_truth.item_scores(env, res) if res.get("where") == "foundry" else []
        # Foundry's own pass flag marked every item passed (its threshold is not applied as we expected), so we
        # count from its scores: a planted item is caught when Foundry scores it below 1.0, a clean one passes at 1.0.
        pairs = list(zip(items, scores)) if len(scores) == len(items) else []
        r["foundry_eval"] = {"measured": time.strftime("%Y-%m-%d"), "items": len(items),
                             "planted": sum(it["planted"] for it in items),
                             "clean": sum(not it["planted"] for it in items),
                             "planted_scored_below_1": sum(1 for it, sc in pairs if it["planted"] and sc < 1.0),
                             "clean_scored_1": sum(1 for it, sc in pairs if not it["planted"] and sc >= 1.0),
                             "scores_match_local": bool(pairs) and all(abs(sc - numeric_truth.grade({}, it)) < 1e-9
                                                                      for it, sc in pairs),
                             **res}
    OUT.write_text(json.dumps(r, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    c, a = r["commentary"], r["answers"]
    print(f"commentary: {c['caught']}/{c['planted']} caught, {len(c['clean_blocked'])}/{c['lines']} clean blocked; "
          f"answers: {a['caught']}/{a['planted']} caught, false-block {a['false_block_rate']}; "
          f"director: input identical {r['director']['input_identical']}/{r['director']['shots']}, "
          f"outcome replies blocked {r['director']['outcome_replies_blocked']}/{r['director']['outcome_replies']}; "
          f"{'PASS' if r['verdict']['pass'] else 'FAIL'}")
    return 0 if r["verdict"]["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
