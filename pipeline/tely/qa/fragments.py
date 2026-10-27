"""Every fixed phrase the offline Ask can play (file 43 §6).

A's answers.py renders each {id, text} with Azure TTS into answers/<sha>.mp3 and answers/index.json (id -> file).
The tools build their spoken answers from these same pieces (tools.py returns their ids as `fragments`), so the
offline clips and the live answers say the same words. Count for the judge cut: see `python -m tely.qa.fragments`.

Spoiler note: the fragment list contains every event line of the cut, so it must never be shown to the listener as a
list. The browser plays a fragment only when a tool returns it, and tools only return what is revealed by the playhead.
"""
from __future__ import annotations

import math

NUM = ["nil", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]
THIRD_WORDS = {"defensive_third": "defensive third", "middle_third": "midfield", "attacking_third": "attacking third"}
SIDE_WORDS = {"near": "near side", "centre": "centre", "far": "far side"}

STATIC = {
    "hold": "Hold that thought, watch this!",           # says THAT something is coming, never WHAT (file 40 §1)
    "back": "Back to the action.",
    "while_we_talked": "While we talked,",
    "while_away": "While you were away,",
    "and": "and",
    "then": "Before that:",
    "ball_out": "The ball is out of play.",
    "nothing_yet": "Nothing big has happened yet.",
    "nothing_missed": "Nothing big happened.",
    "no_spoilers": "I can't tell you what happens next. That's for the match to decide.",
    "no_betting": "I can't help with betting or odds. Ask me about the match instead.",
    "off_topic": "I'm just here for the match. Ask me about the score, the ball, or what just happened.",
    "not_sure": "Sorry, I didn't catch that. Try: what's the score, or where's the ball.",
    "done": "Done.",
    # Recaps (get_recap): the lead-in, then the score and the big moments, each an already verified fragment.
    "recap": "Here's the story so far.",
    "recap_ht": "That's half-time. Here's the story of the half.",
    "recap_end": "That's the end of this part of the match. Here's how it went.",
}


def num_word(n: int) -> str:
    return NUM[n] if 0 <= n < len(NUM) else str(n)


def zone_frag(team: str, side_key: str, third: str, side: str) -> tuple[str, str]:
    """('zone_H_attacking_third_near', 'Reds have it, attacking third, near side.')"""
    return f"zone_{side_key}_{third}_{side}", f"{team} have it, {THIRD_WORDS[third]}, {SIDE_WORDS[side]}."


def dist_frag(metres: float) -> tuple[str, str]:
    """Distance to goal in 5 m steps, 0-100 m (21 clips)."""
    m = int(min(100, max(0, 5 * round(metres / 5))))
    return f"dist_{m:03d}", ("On the goal line." if m == 0 else f"{m} metres from goal.")


def score_frag(home: str, away: str, minute: int, h: int, a: int) -> tuple[str, str]:
    return f"score_m{minute}_{h}_{a}", f"{home} {num_word(h)}, {away} {num_word(a)}, {minute} minutes played."


def build_fragments(bundle) -> list[dict[str, str]]:
    """All fragments for one bundle, in a stable order (static, zones, distances, score/clock, event lines)."""
    out: list[tuple[str, str]] = list(STATIC.items())
    names = {"home": bundle.team_name("home"), "away": bundle.team_name("away")}
    for key, side in (("H", "home"), ("A", "away")):
        for third in THIRD_WORDS:
            for s in SIDE_WORDS:
                out.append(zone_frag(names[side], key, third, s))
    out += [dist_frag(m) for m in range(0, 101, 5)]
    seen = set()
    # Every (minute, score) the score tool can say: each second, and each goal's reveal (bundle.score counts a goal
    # from its reveal_t, which can fall in the minute before the next whole second).
    goals = [bundle.sig(e["id"])["reveal_t"] for e in bundle.events if e["type"] == "shot" and e["outcome_type"] == "successful"]
    for t in sorted({row["t"] for row in bundle.signals["per_second"]} | {g for g in goals if bundle.t0 <= g <= bundle.t1}):
        minute = int(math.floor(bundle.clock_s(t) / 60))
        sc = bundle.score(t)
        k = (minute, sc["home"], sc["away"])
        if k not in seen:
            seen.add(k)
            out.append(score_frag(names["home"], names["away"], *k))
    # Follow my player (D34): each player's name, said when they get the ball. Only the roster: no event, no outcome.
    for pid, p in sorted(bundle.players.items()):
        out.append((f"name_{pid}", f"{p['last_name']} on the ball."))
    for e in bundle.events:
        s = bundle.sig(e["id"])
        if s["priority"] >= 1:
            out.append((f"ev_{e['id']}", s["spoken"]))          # "what just happened" (get_last_events)
        if s["priority"] >= 2:
            out.append((f"past_{e['id']}", s["spoken_past"]))   # "while we talked, ..." (catch-up, what did I miss)
    ids = [i for i, _ in out]
    assert len(ids) == len(set(ids)), "duplicate fragment id"
    return [{"id": i, "text": t} for i, t in out]


def _default() -> list[dict[str, str]]:
    from .bundle import JUDGE, load_bundle
    if not (JUDGE / "meta.json").exists():
        return [{"id": i, "text": t} for i, t in STATIC.items()]
    return build_fragments(load_bundle())


# SEAM(B->A): A's answers.py imports this (via tely.qa.FRAGMENTS) and renders every entry to audio.
FRAGMENTS: list[dict[str, str]] = _default()


if __name__ == "__main__":
    by = {}
    for f in FRAGMENTS:
        by.setdefault(f["id"].split("_")[0], []).append(f)
    print(f"{len(FRAGMENTS)} fragments, {sum(len(f['text']) for f in FRAGMENTS)} characters")
    for k, v in by.items():
        print(f"  {k:8s} {len(v)}")
