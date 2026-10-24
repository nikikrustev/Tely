"""Lively commentary lines: the same facts as templates.py (radio_v1), said the way radio commentators say them.

OWNER: A (potencialbg). Research: file 48 (commentator language). What changes from radio_v1:
- verbs and movement ("picks it up", "lets fly", "steps in") instead of bare zone labels; natural place phrases
  ("deep in their own half", "over on the far side") and the listener's side ("to your right") where it helps;
- reactions and evaluation after the outcome is known ("What a save from...", "He'll feel he should have done
  better"), never before it: the same spoiler rules, the same verifier, the same seeded RNG;
- the shortest fallbacks are still radio_v1-plain, so a tight gap always has something that fits.
Never a number word except the score and the minutes (truth_check), and never "one" in a phrase ("this one").
Selected with build_commentary --style lively; the shipped judge track stays radio_v1 until we choose otherwise.
"""

from __future__ import annotations

from audiostands.commentary.source import Match
from audiostands.commentary.templates import (  # noqa: F401  (re-exported: the planner reads these from either set)
    BUILD_MIN_LEVEL, BUILD_MIN_XG, CROWD_HOLD_S, LEAD_S, SIDE, Draft, _rng, cap, clock_words, number_words,
    score_words, zone,
)

NAME = "lively_v1"

_THIRD = {"defensive_third": ["deep in their own half", "back in their own third"],
          "middle_third": ["in midfield", "in the middle of the park"],
          "attacking_third": ["in the final third", "in the attacking third"]}
# Said before the third, as commentators do: "over on the far side in midfield", "right below us in the final third".
_SIDE = {"near": ["right below us", "on the near side"],
         "far": ["over on the far side", "out on the far side"],
         "centre": [""]}  # the middle needs no words: "deep in their own half, to your left"
_THIRD_SHORT = {"defensive_third": "at the back", "middle_third": "in midfield", "attacking_third": "in the final third"}


def _dirn(x: float) -> str:
    """The listener's side for the ball (halfway seat: x < 0 is to the left), only when it is clearly in one half."""
    return " to your left" if x < -17.5 else " to your right" if x > 17.5 else ""


def where(m: Match, x: float, y: float, side: str, rng, with_dirn: bool = True) -> str:
    z = zone(x, y, m.meta["teams"][side]["attacks"])
    third, lane = rng.choice(_THIRD[z["third"]]), rng.choice(_SIDE[z["side"]])
    return f"{lane} {third}".strip() + (f",{_dirn(x)}" if with_dirn and _dirn(x) else "")


def _short(m: Match, t: float, side: str) -> str:
    """A short place for tight gaps: "in midfield", "deep", "in the final third"."""
    b = m.ball(t)
    return _THIRD_SHORT[zone(b["x"], b["y"], m.meta["teams"][side]["attacks"])["third"]]


def _where_at(m: Match, t: float, side: str, rng, with_dirn: bool = True) -> str:
    b = m.ball(t)
    return where(m, b["x"], b["y"], side, rng, with_dirn)


def _plain(m: Match, t: float, side: str) -> str:
    """radio_v1's zone words, for the shortest fallback."""
    b = m.ball(t)
    return cap(zone(b["x"], b["y"], m.meta["teams"][side]["attacks"])["words"])


# --- lines -------------------------------------------------------------------------------------------------------

def opener(m: Match) -> Draft:
    first = m.events[0] if m.events else None
    label = f"AI commentary, synthetic match, at {m.meta['match']['venue']['name']}."
    if first is not None and first.get("sub_type") == "kick_off" and m.t(first) <= m.t_start + 1:
        texts, evidence = [f"{label} {m.team_name(m.side(first))} get us under way.", label], (first["id"],)
    else:
        score, clock = score_words(m, m.t_start), clock_words(m, m.t_start)
        texts, evidence = [f"{label} We're with you, {clock}, and it's {score}.",
                           f"AI commentary, synthetic match. It's {score}.", "AI commentary, synthetic match."], ()
    return Draft("intro", m.t_start, 4, texts, "calm", 0.2, evidence, stale_s=0.5, key="intro")


def kits(m: Match) -> Draft:
    home, away = m.meta["teams"]["home"], m.meta["teams"]["away"]

    def dirn(team: dict) -> str:
        return "right" if team["attacks"] == "+x" else "left"

    full = (f"If you're just joining us: {home['short_name']}, in {home['kit']['words']}, are attacking to your "
            f"{dirn(home)}. {away['short_name']}, in {away['kit']['words']}, going to your {dirn(away)}.")
    short = (f"{home['short_name']} in {home['kit']['shirt']} attack to your {dirn(home)}, "
             f"{away['short_name']} in {away['kit']['shirt']} to your {dirn(away)}.")
    return Draft("kits", m.t_start, 2, [full, short], "calm", 0.2, (), stale_s=120.0, key="kits")


def describe(m: Match, e: dict) -> Draft | None:
    if e["type"] == "referee":
        return None
    t, side = m.t(e), m.side(e)
    rng = _rng(m, f"describe:{e['id']}")
    team, who = m.team_name(side), m.surname(e["player_id"])
    sig_zone = m.sig(e["id"])["zone"]
    w = _where_at(m, t, side, rng)
    if e["type"] == "pass":
        prio = 1 if m.sig(e["id"])["priority"] >= 1 else 0
        attacking = sig_zone["third"] == "attacking_third"
        lines = [f"{who} picks it up {w}.", f"{team} knocking it about {w}... {who} on the ball.",
                 f"{who}, {w}, looking for a way through.", f"Now it's {who}, {w}.",
                 f"{team} patient now. {who} has it {w}.", f"{who} takes a touch {w}, head up.",
                 f"Into {who}, {w}."]
        if attacking:
            lines += [f"{team} pushing on {w}. {who}.", f"{who} on the ball {w}, {team} probing.",
                      f"{who} {w}... what's on for him?"]
        text = rng.choice(lines)
        if e.get("sub_type") == "free_kick":
            text, prio = f"Free kick to {team}, {w}. {who} stands over it.", 1
        elif e.get("sub_type") == "goal_kick":  # never "goal": an outcome word (spoiler eval)
            text, prio = f"{team} start again from the back. {who} gets us going.", 1
        plain = f"{cap(sig_zone['words'])}, {team}. {who} on the ball."
        style = "curious" if attacking else "calm"
        return Draft("describe", t, prio, [text, f"{who}, {_short(m, t, side)}.", plain], style, m.second(t)["tension"], (e["id"],),
                     stale_s=1.0 if prio else 0.5, team=side, key=e["id"])
    if e["type"] == "defending" and e.get("sub_type") == "interception":
        text = rng.choice([f"Read it beautifully! {who} steps in, and {team} have it back.",
                           f"Nicked away by {who}! {team} win it back.",
                           f"Great anticipation from {who}! {team} are back in possession.",
                           f"And {who} gets there first! {team} ball.",
                           f"Good defending from {who}, {team} win it back.",
                           f"{who} sniffs it out and steals in!"])
        evidence = (e["id"], *(e.get("related_event_ids") or ()))
        return Draft("describe", t, 2, [text, f"{who} nicks it!"], "curious", max(m.second(t)["tension"], 0.3),
                     evidence, stale_s=1.0, reveal="outcome", team=side, key=e["id"])
    return None


HINT_TAILS = {"danger": ["this is dangerous!", "here's a real chance!", "can they find a way through?!"],
              "none": ["space opening up here!", "this could open up!"],
              "counter": ["they're away on the break!", "numbers forward on the counter!"],
              "set_piece": ["bodies in the box!", "the delivery's coming!"]}
SHORT_TAILS = {"danger": "danger!", "none": "space!", "counter": "on the break!", "set_piece": "set piece!"}


def build(m: Match, shot: dict, plan=None) -> Draft | None:
    """Look-ahead build-up: the shot's time, team and xG only, never its outcome (same rules as radio_v1)."""
    xg = m.sig(shot["id"])["xg"] or 0.0
    if plan is None:
        if xg < BUILD_MIN_XG:
            return None
        lead_s, hold_ms, hint = LEAD_S, 0, "danger" if xg >= 0.25 else "none"
        intensity = None
    else:
        if plan.build_up_level < BUILD_MIN_LEVEL:
            return None
        lead_s, hold_ms, hint, intensity = plan.lead_s, plan.hold_ms, plan.hint_type, plan.build_up_level
    t = m.t(shot) - lead_s
    if t < m.t_start:
        return None
    side = m.ball(t)["poss"] or m.side(shot)
    team = m.team_name(side)
    holder, holder_ev = m.holder_at(t)
    who = f" {m.surname(holder)}..." if holder and m.players[holder]["side"] == side else ""
    rng = _rng(m, f"build:{shot['id']}")
    tail = rng.choice(HINT_TAILS[hint])
    w = _where_at(m, t, side, rng, with_dirn=False)
    texts = [f"{team} on the charge, {w}...{who} {tail}", f"{team} pouring forward...{who} {tail}",
             f"{team} coming...{who} {tail}", f"{team}...{who} {SHORT_TAILS[hint]}", f"{team}...{who}"]
    evidence = (shot["id"],) + ((holder_ev,) if who else ())
    if intensity is None:
        intensity = min(1.0, max(m.second(t)["tension"] * 0.8, 0.5 + xg))
    return Draft("build", t, 5, texts, "urgent" if intensity < 0.75 else "excited", intensity, evidence,
                 stale_s=0.5, pause_ms=hold_ms, team=m.side(shot), tacton="attack", key=f"build:{shot['id']}")


def call(m: Match, shot: dict) -> Draft:
    who = m.surname(shot["player_id"])
    rng = _rng(m, f"call:{shot['id']}")
    if shot.get("body_part") == "head":
        text = rng.choice([f"{who} rises... the header!", f"Up goes {who}... header!"])
    else:
        text = rng.choice([f"{who} lets fly!", f"{who} shoots!", f"{who}, has a go!"])
    return Draft("call", m.t(shot) + 0.2, 3, [text, f"{who}!"], "excited", 0.8, (shot["id"],), stale_s=0.2,
                 team=m.side(shot), tacton="shot", key=f"call:{shot['id']}")


def react(m: Match, shot: dict) -> Draft:
    side, rt = m.side(shot), m.reveal_t(shot)
    rng = _rng(m, f"react:{shot['id']}")
    team, s = m.team_name(side), m.surname(shot["player_id"])
    related = [m.by_id(i) for i in shot.get("related_event_ids") or ()]
    by_type = {r["type"]: r for r in related}
    reviewed = (shot.get("var") or {}).get("reviewed", False)
    var_ids = tuple(r["id"] for r in related if r["type"] == "referee")
    if shot["outcome_type"] == "successful":
        texts = ([f"The goal stands! It counts for {team}, and listen to this place!", f"The goal stands! {team}!",
                  "The goal stands!"] if reviewed else
                 [f"Goal! It's in for {team}! Listen to this place!", f"Goal! Goal for {team}!", "Goal!"])
        return Draft("react", rt, 7, texts, "shouting", 1.0, (shot["id"], *var_ids), stale_s=1.5, pause_ms=300,
                     reveal="outcome", team=side, tacton="goal", key=f"react:{shot['id']}")
    evidence: tuple[str, ...] = (shot["id"],)
    keeper, blocker = by_type.get("goalkeeping"), by_type.get("defending")
    if shot["outcome_type"] == "saved" and keeper:
        k = m.surname(keeper["player_id"])
        text = rng.choice([f"What a save from {k}! {s} can't believe it!",
                           f"Saved! {k} at full stretch to keep out {s}!",
                           f"{k} says no! Brilliant from the keeper, {s} denied."])
        texts, evidence = [text, f"Saved by {k}!"], (shot["id"], keeper["id"])
    elif shot["outcome_type"] == "blocked" and blocker and blocker.get("sub_type") == "block":
        b = m.surname(blocker["player_id"])
        texts = [rng.choice([f"Blocked! {b} throws his body in the way!", f"Charged down by {b}! What defending!"]),
                 "Blocked!"]
        evidence = (shot["id"], blocker["id"])
    elif shot["outcome_type"] == "wide":
        texts = [rng.choice([f"Wide! {s} drags it past the post. He'll feel he should have done better.",
                             f"Oh, that's wide! {s} had a sight of it there.", f"Just wide from {s}! So close!"]),
                 f"Wide from {s}!", "Wide!"]
    elif shot["outcome_type"] == "offside":
        texts, evidence = ["No goal! VAR rules it out for offside, and that's heartbreak.", "No goal!"], \
            (shot["id"], *var_ids)
    else:
        texts = [{"saved": "Saved!", "blocked": "Blocked!", "woodwork": "Off the post!"}.get(shot["outcome_type"],
                                                                                              "Not this time!")]
    return Draft("react", rt, 7, texts, "excited", 0.85, evidence, stale_s=1.5, pause_ms=300, reveal="outcome",
                 team=side, tacton="nearMiss", key=f"react:{shot['id']}")


def var_check(m: Match, e: dict) -> list[Draft]:
    shot = m.by_id(e["related_event_ids"][0])
    t, rt, side = m.t(e), m.reveal_t(e), m.side(shot)
    ev = (e["id"], shot["id"])
    out = [Draft("var", t, 6, ["It's in the net... but hold on, VAR wants a look at it.", "Hold on... VAR is checking it."],
                 "urgent", 0.6, ev, stale_s=1.5, team=side, key=f"var:{e['id']}")]
    if rt - t > 12:
        out.append(Draft("var", t + (rt - t) / 2, 6,
                         ["Still waiting... the whole ground holding its breath.", "Still checking."],
                         "curious", 0.5, ev, stale_s=3.0, team=side, key=f"var2:{e['id']}"))
    return out


def foul(m: Match, e: dict) -> Draft | None:
    if e.get("sub_type") != "foul_committed":
        return None
    t, side = m.t(e), m.side(e)
    who = m.surname(e["player_id"])
    rng = _rng(m, f"foul:{e['id']}")
    if e["outcome_type"] == "yellow_card":
        return Draft("foul", t, 4, [f"Late challenge from {who}... and the referee goes to his pocket. Yellow card.",
                                    f"Yellow card, {who}."],
                     "urgent", 0.6, (e["id"],), stale_s=1.5, reveal="outcome", team=side, tacton="yellow",
                     key=f"foul:{e['id']}")
    text = rng.choice([f"{who} catches his man there. Free kick.", f"Clumsy from {who}. Free kick."])
    return Draft("foul", t, 1, [text, f"Foul by {who}. Free kick."], "curious", 0.4, (e["id"],), stale_s=1.0,
                 reveal="outcome", team=side, key=f"foul:{e['id']}")


def detail(m: Match, shot: dict) -> Draft | None:
    if shot["outcome_type"] != "successful":
        return None
    t = m.reveal_t(shot) + 1.2 + CROWD_HOLD_S
    scorer, side = m.surname(shot["player_id"]), m.side(shot)
    rng = _rng(m, f"detail:{shot['id']}")
    assist = next((m.by_id(i) for i in shot.get("related_event_ids") or ()
                   if m.by_id(i)["type"] == "pass" and m.by_id(i)["receiver_id"] == shot["player_id"]), None)
    finish = "rises highest and heads it in" if shot.get("body_part") == "head" else "sweeps it home"
    if assist:
        a_side = m.sig(assist["id"])["zone"]["side"]
        ball = "cross from the " + SIDE[a_side] if a_side != "centre" else "pass through the middle"
        play = f"{m.surname(assist['player_id'])}'s {ball}... and {scorer} {finish}!"
        evidence = (shot["id"], assist["id"])
    else:
        play, evidence = f"And {scorer} {finish}!", (shot["id"],)
    colour = rng.choice(["What a moment!", "Brilliantly taken!",
                         "What a header!" if shot.get("body_part") == "head" else "What a strike!"])
    state = f"{cap(score_words(m, t))}, {clock_words(m, t)}."
    return Draft("detail", t, 6, [f"{play} {colour} {state}", f"{play} {state}", f"{scorer} scores. {state}"],
                 "excited", 0.75, evidence, stale_s=8.0, reveal="outcome", team=side, key=f"detail:{shot['id']}")


def ball(m: Match, t: float, k: int = 0, near: tuple[str, ...] = (), score_due: bool = False) -> Draft | None:
    if not m.ball(t)["alive"]:
        return None
    holder, holder_ev = m.holder_at(t)
    if holder is None or holder_ev is None:
        return None
    e = m.by_id(holder_ev)
    if e["type"] != "pass" and e.get("sub_type") != "interception":
        return None
    side = m.players[holder]["side"]
    team, who = m.team_name(side), m.surname(holder)
    rng = _rng(m, f"ball:{holder_ev}:{k}")
    w = _where_at(m, t, side, rng)
    plain = _plain(m, t, side)
    third = f"{plain.split(',')[0]}, {team}."
    if any(who in s for s in near):
        bare = rng.choice([f"{team} keeping it {w}.", f"{team} on the ball {w}.", f"Patient from {team}, {w}.",
                           f"{team} moving it around {w}."])
        texts = [f"{team} in possession {w}. It's {score_words(m, t)}."] if score_due else []
        texts = list(dict.fromkeys([*texts, bare, f"{team}, {_short(m, t, side)}.", f"{plain}, {team}.", third]))
    else:
        texts = [rng.choice([f"{who} has it {w}.", f"{team} probing {w}... {who}.", f"It's {who} now, {w}.",
                             f"{team} keeping it {w}. {who} on the ball.",
                             f"{team} circulating it {w}, {who} in possession."]),
                 f"{who}, {_short(m, t, side)}.", f"{team}, {_short(m, t, side)}.", f"{plain}, {team}.", third]
    return Draft("ball", t, 0, texts, "calm", min(m.second(t)["tension"], 0.3), (holder_ev,), stale_s=0.0, team=side,
                 key=f"ball:{holder_ev}:{k}")


def state(m: Match, t: float, n: int) -> Draft:
    b = m.ball(t)
    rng = _rng(m, f"state:{n}")
    score, clock = score_words(m, t), clock_words(m, t)
    if b["alive"] and b["poss"]:
        team = m.team_name(b["poss"])
        w = _where_at(m, t, b["poss"], rng)
        texts = [rng.choice([f"{team} holding on to it {w}. It's {score}, {clock}.",
                             f"{team} with the ball {w}. {cap(score)}, {clock}."]), f"{cap(score)}, {clock}."]
    else:
        last_goal = next((e for e in reversed(m.events) if e["type"] == "shot" and e["outcome_type"] == "successful"
                          and m.reveal_t(e) <= t), None)
        if last_goal and not any(m.t(e) > m.reveal_t(last_goal) and m.t(e) <= t for e in m.events):
            scorers, restart = m.team_name(m.side(last_goal)), m.team_name(m.other(m.side(last_goal)))
            background = rng.choice([f"{scorers} still celebrating in front of their fans, {restart} waiting to go again.",
                                     f"{restart} will get us going again from the centre spot."])
            texts = [f"Ball's out. {background} {cap(score)}.", f"Ball's out. {cap(score)}, {clock}."]
        else:
            texts = [rng.choice([f"Ball's out. A moment to catch our breath. {cap(score)}, {clock}.",
                                 f"Ball's out of play. {cap(score)}, {clock}."]), f"Ball's out. {cap(score)}, {clock}."]
    return Draft("state", t, 1, texts, "calm", min(m.second(t)["tension"], 0.3), (), stale_s=0.0, key=f"state:{n}")
