"""truth_check and spoiler_check for one commentary line (file 22 verifier, file 43 firewall). OWNER: A (potencialbg).

truth_check re-derives every fact from the match at the line's start time; it never trusts what a template meant:
- every player named must be the actor of one of the line's evidence events (or the receiver, once revealed);
- every number spoken must be the score at t_in (paired with the right team) or the minutes played;
- no digits: Radio lines speak numbers as words.
spoiler_check: no outcome word while one of the line's own events, or any shot within D ahead, is still unrevealed.
"""

from __future__ import annotations

import re

from audiostands.commentary.source import Match
from audiostands.commentary.templates import number_words
from audiostands.spoiler import D_S, OUTCOME, PASS_OUTCOME, words

_WORD_NUM = {number_words(n): n for n in range(100)} | {"nil": 0}
_NUM_RE = "|".join(sorted(map(re.escape, _WORD_NUM), key=len, reverse=True))


def _names(m: Match) -> dict[str, str]:
    """Spoken name -> player id (surnames; full names too)."""
    out = {}
    for pid, p in m.players.items():
        out[p["last_name"]] = pid
        out[p["name"]] = pid
    return out


def allowed_players(m: Match, evidence: list[str], t_in: float) -> set[str]:
    ok = set()
    for eid in evidence:
        e = m.by_id(eid)
        ok.add(e.get("player_id"))  # referee events have none
        if e.get("receiver_id") and m.reveal_t(e) <= t_in:
            ok.add(e["receiver_id"])
    return ok


def truth_check(m: Match, text: str, t_in: float, evidence: list[str]) -> list[str]:
    errs = []
    ok = allowed_players(m, evidence, t_in)
    for name, pid in _names(m).items():
        if re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", text) and pid not in ok:
            errs.append(f"name {name!r} is not an actor of evidence {evidence} at t={t_in}")
    if re.search(r"\d", text):
        errs.append("digits in a spoken line")

    low = text.lower()
    score, minute = m.score_at(t_in), int(m.clock_s(t_in) // 60)
    claimed = []
    for side in ("home", "away"):
        team = re.escape(m.team_name(side).lower())
        for hit in re.finditer(rf"\b{team} ({_NUM_RE})\b", low):
            claimed.append(hit.span(1))
            if _WORD_NUM[hit.group(1)] != score[side]:
                errs.append(f"score: said {m.team_name(side)} {hit.group(1)}, truth is {score[side]} at t={t_in}")
    for hit in re.finditer(rf"\b({_NUM_RE}) minutes? played\b", low):
        claimed.append(hit.span(1))
        if _WORD_NUM[hit.group(1)] != minute:
            errs.append(f"clock: said {hit.group(1)} minutes, truth is {minute} at t={t_in}")
    if "inside the first minute" in low and minute != 0:
        errs.append(f"clock: said first minute, truth is {minute}")
    for hit in re.finditer(rf"\b({_NUM_RE})\b", low):
        if hit.span(1) not in claimed:
            errs.append(f"unverified number {hit.group(1)!r}")
    return errs


def spoiler_check(m: Match, text: str, t_in: float, evidence: list[str]) -> list[str]:
    said = words(text)
    errs = []
    for eid in evidence:
        e = m.by_id(eid)
        if m.reveal_t(e) > t_in and said & (OUTCOME | PASS_OUTCOME):
            errs.append(f"outcome word before {eid} is revealed at {m.reveal_t(e)}")
    for e in m.events:
        if e["type"] == "shot" and said & OUTCOME and m.t(e) - D_S < t_in < m.reveal_t(e):
            errs.append(f"outcome word within {D_S} s before shot {e['id']} is revealed")
    return errs
