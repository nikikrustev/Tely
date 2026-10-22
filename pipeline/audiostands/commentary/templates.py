"""Radio-level, ball-first commentary lines (file 36 design rules 1-4, file 22 template-first). OWNER: A (potencialbg).

Grammar for every live line: where (third, side), which team, then who (file 36 rule 1). The scorer is named only
after the play is described. "Ball's out" comes before any background. Phrasings vary, chosen by a seeded RNG keyed
on the event, so the same match always gives the same script. Every function returns a Draft; the planner decides
when (and whether) it is spoken, and the verifier re-checks every name and number against the match.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from audiostands.commentary.source import Match

LEAD_S = 4.0          # build-up starts 4 s before the shot (file 39 reveal policy; our guess from its 2-5 s window)
BUILD_MIN_XG = 0.08   # a chance this good gets a build-up, whatever its outcome (file 39 planner threshold)
CROWD_HOLD_S = 3.0    # let the roar carry the goal before the detail line (file 39)
THIRD = {"defensive_third": "defensive third", "middle_third": "midfield", "attacking_third": "attacking third"}
SIDE = {"near": "near side", "centre": "centre", "far": "far side"}
_ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
         "seventeen eighteen nineteen").split()
_TENS = {2: "twenty", 3: "thirty", 4: "forty", 5: "fifty", 6: "sixty", 7: "seventy", 8: "eighty", 9: "ninety"}


@dataclass
class Draft:
    kind: str                       # intro, kits, describe, build, call, react, detail, var, foul, ball, state
    t: float                        # wanted start, seconds since kick-off
    prio: int                       # placement order: higher claims its slot first
    texts: list[str]                # preferred text first, then shorter fallbacks
    style: str
    intensity: float
    evidence: tuple[str, ...] = ()
    stale_s: float = 1.0            # may slide later by up to this much, else it is dropped
    pause_ms: int = 0
    reveal: str = "none"            # "outcome" if the line says how an event ended
    team: str | None = None         # "home" / "away": whose moment it is (haptics)
    tacton: str | None = None
    key: str = field(default="")    # stable id for the RNG and the cue


def number_words(n: int) -> str:
    if 0 <= n < 20:
        return _ONES[n]
    if 20 <= n < 100:
        tens, ones = divmod(n, 10)
        return _TENS[tens] + (f"-{_ONES[ones]}" if ones else "")
    return str(n)


def zone(x: float, y: float, attacks: str) -> dict:
    """Same rule as B's signals zone (contracts/b/README.md): thirds from the team's view, sides absolute."""
    ax = x if attacks == "+x" else -x
    third = "defensive_third" if ax < -17.5 else "middle_third" if ax <= 17.5 else "attacking_third"
    side = "near" if y < -34 / 3 else "far" if y > 34 / 3 else "centre"
    return {"third": third, "side": side, "words": f"{THIRD[third]}, {SIDE[side]}"}


def zone_of_ball(m: Match, t: float, side: str) -> str:
    b = m.ball(t)
    return zone(b["x"], b["y"], m.meta["teams"][side]["attacks"])["words"]


def cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def score_words(m: Match, t: float) -> str:
    s = m.score_at(t)
    word = lambda n: "nil" if n == 0 else number_words(n)  # noqa: E731
    return f"{m.team_name('home')} {word(s['home'])}, {m.team_name('away')} {word(s['away'])}"


def clock_words(m: Match, t: float) -> str:
    minute = int(m.clock_s(t) // 60)
    if minute == 0:
        return "inside the first minute"
    return f"{number_words(minute)} minute{'s' if minute > 1 else ''} played"


def _rng(m: Match, key: str) -> random.Random:
    return random.Random(f"{m.seed}:{key}")


# --- lines -------------------------------------------------------------------------------------------------------

def opener(m: Match) -> Draft:
    """First words of the window: the AI label, then kick-off or where we join it (CLAUDE.md: every AI voice labelled)."""
    first = m.events[0] if m.events else None
    label = f"AI commentary, synthetic match, at {m.meta['match']['venue']['name']}."
    if first is not None and first.get("sub_type") == "kick_off" and m.t(first) <= m.t_start + 1:
        texts, evidence = [f"{label} {m.team_name(m.side(first))} get us under way.", label], (first["id"],)
    else:
        # A cut can open seconds before a chance (judge cut: 9 s), so this has short fallbacks and a short slot.
        score, clock = score_words(m, m.t_start), clock_words(m, m.t_start)
        texts, evidence = [f"{label} We join it with {clock}, {cap(score)}.",
                           f"AI commentary, synthetic match. {cap(score)}.", "AI commentary, synthetic match."], ()
    return Draft("intro", m.t_start, 4, texts, "calm", 0.2, evidence, stale_s=0.5, key="intro")


def kits(m: Match) -> Draft:
    """Both kits and the direction of play (file 36 rule 1), at the first quiet moment after the opener."""
    home, away = m.meta["teams"]["home"], m.meta["teams"]["away"]

    # SEAM(A->B): "to your right" assumes B's sound stage pans ball x = +52.5 to the right ear (HANDOFF to B).
    def dirn(team: dict) -> str:
        return "right" if team["attacks"] == "+x" else "left"

    full = (f"{home['short_name']}, in {home['kit']['words']}, attack to your {dirn(home)}. "
            f"{away['short_name']}, in {away['kit']['words']}, attack to your {dirn(away)}.")
    short = (f"{home['short_name']} in {home['kit']['shirt']} attack to your {dirn(home)}, "
             f"{away['short_name']} in {away['kit']['shirt']} to your {dirn(away)}.")
    return Draft("kits", m.t_start, 2, [full, short], "calm", 0.2, (), stale_s=120.0, key="kits")


def describe(m: Match, e: dict) -> Draft | None:
    """Who has the ball now, ball first. Never the receiver: that is the pass's outcome (spoiler rule)."""
    if e["type"] == "referee":
        return None  # SEAM(A->B): referee events carry official_id, never team_id/player_id (contract 0.2.0)
    t, side = m.t(e), m.side(e)
    rng = _rng(m, f"describe:{e['id']}")
    where = cap(m.sig(e["id"])["zone"]["words"])
    team, who = m.team_name(side), m.surname(e["player_id"])
    if e["type"] == "pass":
        tail = rng.choice([f"{who} on the ball.", f"{who} has it.", f"{who}, looking for a way forward.",
                           f"it's with {who}."])
        prio = 1 if m.sig(e["id"])["priority"] >= 1 else 0
        text = f"{where}, {team}. {cap(tail)}"
        if e.get("sub_type") == "free_kick":
            text, prio = f"Free kick, {where.lower()}, {team}. {who} takes it.", 1
        elif e.get("sub_type") == "goal_kick":  # never the word "goal" here: it is an outcome word (spoiler eval)
            text, prio = f"{team} restart from the back. {who} on the ball.", 1
        return Draft("describe", t, prio, [text], "calm",
                     m.second(t)["tension"], (e["id"],), stale_s=1.0 if prio else 0.5, team=side, key=e["id"])
    if e["type"] == "defending" and e.get("sub_type") == "interception":
        text = rng.choice([f"Cut out! {who} wins it back for {team}.", f"Intercepted by {who}! {team} have it back."])
        evidence = (e["id"], *(e.get("related_event_ids") or ()))
        return Draft("describe", t, 2, [text, f"Cut out by {who}!"], "curious", max(m.second(t)["tension"], 0.3),
                     evidence, stale_s=1.0, reveal="outcome", team=side, key=e["id"])
    return None


def build(m: Match, shot: dict) -> Draft | None:
    """Look-ahead build-up at shot - LEAD_S. Uses the shot's time, team and xG only, never its outcome (file 39)."""
    xg = m.sig(shot["id"])["xg"] or 0.0
    if xg < BUILD_MIN_XG:
        return None
    t = m.t(shot) - LEAD_S
    if t < m.t_start:
        return None
    side = m.ball(t)["poss"] or m.side(shot)
    team = m.team_name(side)
    holder, holder_ev = m.holder_at(t)
    who = f" {m.surname(holder)}..." if holder and m.players[holder]["side"] == side else ""
    rng = _rng(m, f"build:{shot['id']}")
    tail = rng.choice(["here's a chance!", "real danger here!"] if xg >= 0.25 else
                      ["this could open up!", "space opening up!"])
    where = zone_of_ball(m, t, side)
    # Shorter fallbacks: the build-up must fit between shot - LEAD_S and the reveal, and is never dropped for length.
    texts = [f"{cap(where)}, {team}...{who} {tail}", f"{cap(where.split(',')[0])}, {team}...{who} {tail}",
             f"{team} coming...{who} {tail}", f"{team}...{who}"]
    evidence = (shot["id"],) + ((holder_ev,) if who else ())
    # Intensity from tension (xG-weighted look-ahead, B's signals) and xG only: identical for a goal and a save.
    intensity = min(1.0, max(m.second(t)["tension"] * 0.8, 0.5 + xg))
    return Draft("build", t, 5, texts, "urgent" if intensity < 0.75 else "excited", intensity, evidence,
                 stale_s=0.5, team=m.side(shot), tacton="attack", key=f"build:{shot['id']}")


def call(m: Match, shot: dict) -> Draft:
    """The shot itself at shot + 0.2 s, with no outcome. Only fits when the ball travels long enough before reveal."""
    who = m.surname(shot["player_id"])
    text = f"{who}, the header!" if shot.get("body_part") == "head" else f"{who} shoots!"
    return Draft("call", m.t(shot) + 0.2, 3, [text, f"{who}!"], "excited", 0.8, (shot["id"],), stale_s=0.2,
                 team=m.side(shot), tacton="shot", key=f"call:{shot['id']}")


def react(m: Match, shot: dict) -> Draft:
    """The outcome, at the moment it is revealed (contracts/b spoiler rule; for a VAR review, the decision)."""
    side, rt = m.side(shot), m.reveal_t(shot)
    rng = _rng(m, f"react:{shot['id']}")
    team, s = m.team_name(side), m.surname(shot["player_id"])
    related = [m.by_id(i) for i in shot.get("related_event_ids") or ()]
    by_type = {r["type"]: r for r in related}
    reviewed = (shot.get("var") or {}).get("reviewed", False)
    var_ids = tuple(r["id"] for r in related if r["type"] == "referee")
    if shot["outcome_type"] == "successful":
        texts = ([f"The goal stands! Goal for {team}!", "The goal stands!"] if reviewed else
                 [f"Goal! Goal for {team}!", "Goal!"])
        return Draft("react", rt, 7, texts, "shouting", 1.0, (shot["id"], *var_ids), stale_s=1.5, pause_ms=300,
                     reveal="outcome", team=side, tacton="goal", key=f"react:{shot['id']}")
    evidence: tuple[str, ...] = (shot["id"],)
    keeper, blocker = by_type.get("goalkeeping"), by_type.get("defending")
    if shot["outcome_type"] == "saved" and keeper:
        k = m.surname(keeper["player_id"])
        text = rng.choice([f"Saved! {k} keeps out {s}.", f"Saved by {k}! {s} denied.", f"Saved! {k} holds on."])
        texts, evidence = [text, f"Saved by {k}!"], (shot["id"], keeper["id"])
    elif shot["outcome_type"] == "blocked" and blocker and blocker.get("sub_type") == "block":
        b = m.surname(blocker["player_id"])
        texts, evidence = [f"Blocked! {b} gets in the way.", "Blocked!"], (shot["id"], blocker["id"])
    elif shot["outcome_type"] == "wide":
        texts = [rng.choice([f"Wide! {s} sends it past the post.", f"Wide from {s}!"]), "Wide!"]
    elif shot["outcome_type"] == "offside":
        texts, evidence = ["No goal! VAR rules it out for offside.", "No goal!"], (shot["id"], *var_ids)
    else:
        texts = [{"saved": "Saved!", "blocked": "Blocked!", "woodwork": "Off the post!"}.get(shot["outcome_type"],
                                                                                              "Not this time!")]
    return Draft("react", rt, 7, texts, "excited", 0.85, evidence, stale_s=1.5, pause_ms=300, reveal="outcome",
                 team=side, tacton="nearMiss", key=f"react:{shot['id']}")


def var_check(m: Match, e: dict) -> list[Draft]:
    """A VAR review is a long wait before the outcome. Say that it is happening, never how it ends (contract 0.2.0)."""
    shot = m.by_id(e["related_event_ids"][0])
    t, rt, side = m.t(e), m.reveal_t(e), m.side(shot)
    ev = (e["id"], shot["id"])
    out = [Draft("var", t, 6, ["It's in the net... but hold on, VAR is checking it.", "VAR is checking it."],
                 "urgent", 0.6, ev, stale_s=1.5, team=side, key=f"var:{e['id']}")]
    if rt - t > 12:  # keep the wait under MAX_QUIET_S of silence
        out.append(Draft("var", t + (rt - t) / 2, 6, ["Still checking... both ends waiting on VAR.", "Still checking."],
                         "curious", 0.5, ev, stale_s=3.0, team=side, key=f"var2:{e['id']}"))
    return out


def foul(m: Match, e: dict) -> Draft | None:
    if e.get("sub_type") != "foul_committed":
        return None
    t, side = m.t(e), m.side(e)
    who, team = m.surname(e["player_id"]), m.team_name(side)
    if e["outcome_type"] == "yellow_card":
        return Draft("foul", t, 4, [f"Foul by {who}... and it's a yellow card for {team}.", f"Yellow card, {who}."],
                     "urgent", 0.6, (e["id"],), stale_s=1.5, reveal="outcome", team=side, tacton="yellow",
                     key=f"foul:{e['id']}")
    return Draft("foul", t, 1, [f"Foul by {who}. Free kick."], "curious", 0.4, (e["id"],), stale_s=1.0,
                 reveal="outcome", team=side, key=f"foul:{e['id']}")


def detail(m: Match, shot: dict) -> Draft | None:
    """After a goal and the crowd hold: describe the play, then name the scorer, then score and clock."""
    if shot["outcome_type"] != "successful":
        return None
    t = m.reveal_t(shot) + 1.2 + CROWD_HOLD_S
    scorer, side = m.surname(shot["player_id"]), m.side(shot)
    assist = next((m.by_id(i) for i in shot.get("related_event_ids") or ()
                   if m.by_id(i)["type"] == "pass" and m.by_id(i)["receiver_id"] == shot["player_id"]), None)
    finish = "heads it in" if shot.get("body_part") == "head" else "finishes"
    if assist:
        a_side = m.sig(assist["id"])["zone"]["side"]
        ball = "cross from the " + SIDE[a_side] if a_side != "centre" else "pass through the middle"
        play = f"{m.surname(assist['player_id'])}'s {ball}... and {scorer} {finish}!"
        evidence = (shot["id"], assist["id"])
    else:
        play, evidence = f"And {scorer} {finish}!", (shot["id"],)
    state = f"{cap(score_words(m, t))}, {clock_words(m, t)}."
    return Draft("detail", t, 6, [f"{play} {state}", f"{scorer} scores. {state}"], "excited", 0.75, evidence,
                 stale_s=8.0, reveal="outcome", team=side, key=f"detail:{shot['id']}")


def ball(m: Match, t: float, k: int = 0, near: tuple[str, ...] = (), score_due: bool = False) -> Draft | None:
    """In-play fill: where the ball is, whose it is, then who has it (file 36 rule 1), as known at t.

    None while nobody is known to have it (a pass in the air: the receiver is its outcome) or the ball is dead.
    Only a completed pass's receiver or an interceptor counts: after a block or a save the ball may be loose.
    k counts earlier ball lines about the same holder, so a long spell on the ball doesn't repeat itself.
    near: the texts of the lines either side. If one already names the holder, leave the name out, and give the
    score instead when score_due (nobody has said it for a while).
    """
    if not m.ball(t)["alive"]:
        return None
    holder, holder_ev = m.holder_at(t)
    if holder is None or holder_ev is None:
        return None
    e = m.by_id(holder_ev)
    if e["type"] != "pass" and e.get("sub_type") != "interception":
        return None
    side = m.players[holder]["side"]
    where, team, who = cap(zone_of_ball(m, t, side)), m.team_name(side), m.surname(holder)
    third = f"{where.split(',')[0]}, {team}."  # shortest: a tight gap still hears where the ball is
    rng = _rng(m, f"ball:{holder_ev}:{k}")
    if any(who in s for s in near):
        bare = rng.choice([f"{where}, {team}.", f"{where}, {team} keeping it.", f"{where}, {team} with the ball.",
                           f"{where}, {team} on the ball."])
        texts = [f"{where}, {team} in possession. {cap(score_words(m, t))}."] if score_due else []
        texts = list(dict.fromkeys([*texts, bare, f"{where}, {team}.", third]))
    else:
        texts = [rng.choice([f"{where}, {team}. It's with {who}.", f"{where}, {team}. {who} has it.",
                             f"{where}, {team}, {who} on the ball.", f"{where}, {team} keeping it. {who}.",
                             f"{where}, {team}. {who} in possession."]),
                 f"{where}, {team}. {who}.", f"{where}, {team}.", third]
    return Draft("ball", t, 0, texts, "calm", min(m.second(t)["tension"], 0.3), (holder_ev,), stale_s=0.0, team=side,
                 key=f"ball:{holder_ev}:{k}")


def state(m: Match, t: float, n: int) -> Draft:
    """Quiet fill: ball zone (or "ball's out"), score and clock. Keeps a blind listener oriented (file 39 §3)."""
    b = m.ball(t)
    rng = _rng(m, f"state:{n}")
    score, clock = cap(score_words(m, t)), clock_words(m, t)
    if b["alive"] and b["poss"]:
        team = m.team_name(b["poss"])
        where = cap(zone_of_ball(m, t, b["poss"]))
        texts = [rng.choice([f"{where}, {team} in possession. {score}, {clock}.",
                             f"{where}, {team} keeping it. {score}, {clock}."]), f"{score}, {clock}."]
    else:
        last_goal = next((e for e in reversed(m.events) if e["type"] == "shot" and e["outcome_type"] == "successful"
                          and m.reveal_t(e) <= t), None)
        if last_goal and not any(m.t(e) > m.reveal_t(last_goal) and m.t(e) <= t for e in m.events):
            scorers, restart = m.team_name(m.side(last_goal)), m.team_name(m.other(m.side(last_goal)))
            background = rng.choice([f"{scorers} still celebrating, {restart} waiting to restart.",
                                     f"{restart} will restart from the centre spot."])
            texts = [f"Ball's out. {background} {score}.", f"Ball's out. {score}, {clock}."]
        else:
            texts = [f"Ball's out. {score}, {clock}."]
    return Draft("state", t, 1, texts, "calm", min(m.second(t)["tension"], 0.3), (), stale_s=0.0, key=f"state:{n}")
