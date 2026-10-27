"""Seeded synthetic match: the file 02 possession-chain generator with both file 33 fixes, plus keeper saves,
fouls with yellow cards, free kicks, goal kicks, blocks and a VAR-style goal check ().

 Fictional clubs and players only; nothing here comes from real match data.

Determinism (A's build reruns this, so every run must give the same bytes on every machine):
- times are whole 25 Hz frames (ints) from the period start, so an event always sits on the ball grid;
- only Python's own `random.Random` is used (Mersenne Twister: same stream on every OS and version);
- every continuous draw is rounded at once (cm, 0.001 for xG), so a last-bit difference in a platform's
  exp/log/cos can only matter if a value lands exactly on a rounding edge.

Output of generate(seed): a dict with the roster, both periods, the events (period-relative frames) and the
ball keyframes and ball-holder changes that movement.py turns into tracks. Event fields are CDF names (file 26).
"""
from __future__ import annotations

import math
import random

FPS = 25
L, W = 105.0, 68.0
HALF_L, HALF_W = L / 2, W / 2
BALL_Z, HANDS_Z = 0.11, 1.0
GENERATOR_VERSION = "0.2.0"
PERIODS = ("first_half", "second_half")
DIR = {"home": 1, "away": -1}                    # CDF: home attacks +x all match
OTHER = {"home": "away", "away": "home"}

# Tuning knobs (ours, not cited): tuned so the realism report's cited targets come out green.
P_FOUL = 0.024           # chance an open-play step ends in a foul (no cited target in our files)
P_CARD = 0.17            # yellow card per foul (no cited target in our files)
P_VAR_GOAL = 0.5         # share of goals that get a VAR-style check
P_VAR_STANDS = 0.8       # share of checked goals that stand
P_WOODWORK = 0.1         # share of off-target shots that hit the post (counted as wide + goal kick)
TOUCH_MEAN_S = 5.2       # file 02 used 3.9 s; longer here because we also simulate carries (tuned to passes/90)
SHOT_BASE = 0.056        # file 02 used 0.03 (tuned to shots/90)

TEAMS = {
    "home": dict(id="syn_reds", name="Ember Vale FC", short_name="Reds", formation="4-4-2", attacks="+x",
                 kit=dict(shirt="red", sleeves="red", shorts="white", socks="red", words="red shirts, white shorts")),
    "away": dict(id="syn_navy", name="Port Halden FC", short_name="Navy", formation="4-4-2", attacks="-x",
                 kit=dict(shirt="navy", sleeves="sky blue", shorts="navy", socks="navy",
                          words="navy shirts with sky-blue sleeves")),
}
# File 19's 4-4-2: (role, anchor x, anchor y) in the team's own frame (attacking +x), plus shirt numbers.
# Positions are named for the home team; for the away team (attacking -x) left and right swap.
SLOTS = [("GK", -50, 0, 1), ("FB", -30, -22, 2), ("CB", -34, -8, 5), ("CB", -34, 8, 4), ("FB", -30, 22, 3),
         ("W", -8, -22, 7), ("CM", -14, -8, 8), ("CM", -14, 8, 6), ("W", -8, 22, 11), ("ST", 10, -7, 9),
         ("ST", 10, 7, 10)]
POS_HOME = ["GK", "RB", "CB", "CB", "LB", "RM", "CM", "CM", "LM", "ST", "ST"]
POS_AWAY = ["GK", "LB", "CB", "CB", "RB", "LM", "CM", "CM", "RM", "ST", "ST"]

FIRST = ["Aled", "Bram", "Caio", "Dario", "Eli", "Femi", "Gus", "Hugo", "Idris", "Jonas", "Kofi", "Luka", "Mats",
         "Nico", "Omar", "Pavel", "Quinn", "Rafa", "Sami", "Teo", "Ugo", "Viktor", "Wes", "Yannick", "Zeki", "Arlo",
         "Bastian", "Cyril", "Dmitri", "Emre", "Felix", "Goran", "Henrik", "Ilan", "Jude", "Kenji", "Lars", "Milo"]
SYL_A = ["Bran", "Kel", "Mor", "Vas", "Tor", "Hal", "Dun", "Ril", "Sev", "Ast", "Orl", "Pem", "Quil", "Lom", "Nev",
         "Car", "Fen", "Gal", "Hep", "Jor", "Wex", "Ash", "Strand", "Var", "Olv", "Pell", "Mard", "Tesk"]
SYL_B = ["wick", "ard", "ley", "ova", "sen", "ani", "ford", "ez", "ski", "ton", "ini", "ell", "holm", "ade", "ic",
         "ros", "by", "dale", "ovic", "aro"]


def frames(seconds: float) -> int:
    return round(seconds * FPS)


def r2(v: float) -> float:
    return round(v + 0.0, 2)


def roster(seed: int) -> dict:
    """22 fictional players. Names come from a separate seeded stream, so they never change the match."""
    rng = random.Random(seed * 7919 + 17)
    used, players = set(), {}
    for side in ("home", "away"):
        pre = "r" if side == "home" else "n"
        for k, (role, ax, ay, shirt) in enumerate(SLOTS):
            while True:
                last = rng.choice(SYL_A) + rng.choice(SYL_B)
                if last not in used:
                    used.add(last)
                    break
            players[f"{pre}{shirt}"] = dict(side=side, slot=k, role=role, first=rng.choice(FIRST), last=last,
                                            number=shirt, position=(POS_HOME if side == "home" else POS_AWAY)[k],
                                            anchor=(ax, ay))
    return players


def xg(x: float, y: float, d: int) -> float:
    """File 02 toy xG (distance + angle to the goal centre), rounded so comparisons are platform-proof."""
    gx = d * HALF_L
    dist = math.hypot(gx - x, y)
    ang = math.atan2(7.32 * abs(gx - x), (gx - x) ** 2 + y ** 2 - (7.32 / 2) ** 2)
    return round(1 / (1 + math.exp(-(-1.6 - 0.11 * dist + 1.2 * ang))), 3)


class _Half:
    """One period. Emits events, ball keyframes and ball-holder changes, all in period-relative frames."""

    def __init__(self, seed: int, k: int, players: dict, score: dict, booked: set, kickoff_side: str):
        self.rng = random.Random(2 * seed + k)                 # file 33: two seeded halves, 2*seed + k
        self.k, self.period, self.players = k, PERIODS[k], players
        self.score, self.booked = score, booked
        added = self.rng.randint(1, 3) if k == 0 else self.rng.randint(3, 6)
        self.end_f = frames(45 * 60 + added * 60)
        self.events, self.keys, self.holders = [], [], []
        self.goals = []
        self.kickoff_side = kickoff_side

    # ---- helpers --------------------------------------------------------------------------------------
    def team_ids(self, side, gk=True):
        return [p for p, v in self.players.items() if v["side"] == side and (gk or v["role"] != "GK")]

    def gk(self, side):
        return next(p for p in self.team_ids(side) if self.players[p]["role"] == "GK")

    def est_pos(self, pid, bx, by, in_poss):
        """Rough spot of a player (file 19 step 1: block follows the ball, stretched with it, squeezed without)."""
        p = self.players[pid]
        d = DIR[p["side"]]
        ax, ay = p["anchor"]
        if p["role"] == "GK":
            return d * (-49 + 0.08 * (d * bx + HALF_L)), 0.12 * by
        lf, wf, shift, lat = (1.0, 1.0, 6, 0.15) if in_poss else (0.75, 0.72, -6, 0.35)
        tx = max(-22.0, min(22.0, 0.55 * d * bx + shift)) + (ax + 15) * lf
        return d * tx, ay * wf + lat * by

    def nearest(self, side, x, y, bx, by, in_poss, exclude=(), gk=False, top=1):
        cands = [p for p in self.team_ids(side, gk) if p not in exclude]
        scored = []
        for p in cands:
            px, py = self.est_pos(p, bx, by, in_poss)
            scored.append((round((px - x) ** 2 + (py - y) ** 2, 4), self.players[p]["slot"], p))
        scored.sort()
        return [s[2] for s in scored[:top]]

    def gauss(self, mu, sd):
        return round(self.rng.gauss(mu, sd), 3)

    def emit(self, f, **kw):
        ev = dict(period=self.period, f=f, reveal_f=f, sub_type=None, is_successful=True, outcome_type="successful",
                  receiver_id=None, recv_f=None, x_end=None, y_end=None, body_part=None, related=[], xg=None,
                  var=None, official_id=None, player_id=None, team=None)
        ev.update(kw)
        ev["seq"] = (self.k, len(self.events))
        self.events.append(ev)
        return ev

    def key(self, f, x, y, z, alive, poss, mode="lin", loft=0.0):
        self.keys.append((f, r2(x), r2(y), r2(z), alive, poss, mode, loft))

    def hold(self, f, pid):
        self.holders.append((f, pid))

    # ---- restarts -------------------------------------------------------------------------------------
    def kick_off(self, f, side):
        d = DIR[side]
        taker = next(p for p in self.team_ids(side) if self.players[p]["role"] == "ST")
        rec = self.nearest(side, -d * 9.0, -4.0, 0.0, 0.0, True, exclude=(taker,))[0]
        end = (r2(-d * self.rng.uniform(7, 11)), r2(self.rng.uniform(-6, 6)))
        return self.pass_(f, side, taker, (0.0, 0.0), end=end, receiver=rec, sub="kick_off", speed=10.0)

    # ---- actions --------------------------------------------------------------------------------------
    def pass_(self, f, side, pid, at, end=None, receiver=None, sub=None, speed=None, body=None):
        rng, d = self.rng, DIR[side]
        x, y = at
        if end is None:
            length, ang = abs(self.gauss(14, 8)), self.gauss(0, 0.9)
            for _ in range(20):                                    # file 33 fix 2: re-draw passes aimed off the pitch
                if abs(x + d * length * math.cos(ang)) < HALF_L - 0.5 and abs(y + length * math.sin(ang)) < HALF_W - 0.5:
                    break
                length, ang = abs(self.gauss(14, 8)), self.gauss(0, 0.9)
            else:                                                   # near the byline: cut it back instead (ours)
                for flip in (math.pi - ang, -ang, ang - math.pi):
                    if abs(x + d * length * math.cos(flip)) < HALF_L - 0.5 and \
                            abs(y + length * math.sin(flip)) < HALF_W - 0.5:
                        ang = flip
                        break
            xe = r2(max(-HALF_L + 0.5, min(HALF_L - 0.5, x + d * length * math.cos(ang))))
            ye = r2(max(-HALF_W + 0.5, min(HALF_W - 0.5, y + length * math.sin(ang))))
        else:
            xe, ye = end
        length = math.hypot(xe - x, ye - y)
        p_ok = 0.98 - 0.006 * length - 0.12 * (abs(d * HALF_L - xe) < 25)
        ok = sub == "kick_off" or rng.random() < p_ok
        speed = speed or round(rng.uniform(12, 18), 2)
        f1 = f + max(1, frames(length / speed))
        loft = round(min(6.0, 0.12 * (length - 25)), 2) if length > 25 else 0.0
        if body is None:
            body = "hands" if self.players[pid]["role"] == "GK" and length < 30 and sub is None else (
                "left_foot" if rng.random() < 0.25 else "right_foot")
        z0 = HANDS_Z if body == "hands" else BALL_Z
        self.key(f, x, y, z0, 1, side, "flight", loft)
        if ok:
            rec = receiver or self.pick_receiver(side, pid, xe, ye, x)
            ev = self.emit(f, type="pass", sub_type=sub, player_id=pid, team=side, x=r2(x), y=r2(y), x_end=xe,
                           y_end=ye, body_part=body, receiver_id=rec, recv_f=f1, reveal_f=f1)
            self.hold(f, rec)
            return self.carry(f1, side, rec, (xe, ye))
        cut = self.nearest(OTHER[side], xe, ye, x, y, False)[0]
        ev = self.emit(f, type="pass", sub_type=sub, player_id=pid, team=side, x=r2(x), y=r2(y), x_end=xe, y_end=ye,
                       body_part=body, is_successful=False, outcome_type="intercepted", reveal_f=f1)
        self.hold(f, cut)
        ic = self.emit(f1, type="defending", sub_type="interception", player_id=cut, team=OTHER[side], x=xe, y=ye,
                       body_part="right_foot", related=[ev["seq"]])
        ev["related"] = [ic["seq"]]
        return self.carry(f1, OTHER[side], cut, (xe, ye))

    def pick_receiver(self, side, passer, xe, ye, bx):
        """The teammate whose rough spot is nearest the pass end (sometimes the second nearest): passes go to
        someone who is actually there, so movement.py can bring that player to the ball."""
        top = self.nearest(side, xe, ye, bx, ye, True, exclude=(passer,), gk=abs(DIR[side] * HALF_L + xe) < 20,
                           top=2)
        return top[1] if len(top) > 1 and self.rng.random() < 0.25 else top[0]

    def carry(self, f, side, pid, at):
        """Receive, take a few touches (file 02 touch time), maybe dribble a few metres, then act again."""
        rng, d = self.rng, DIR[side]
        x, y = at
        touch = min(round(rng.expovariate(1 / TOUCH_MEAN_S), 3), 12.0)
        f2 = f + max(frames(touch), 4)
        clen = round(min(8.0, touch * rng.uniform(0.5, 2.0)), 2)
        ang = self.gauss(0, 0.6)
        x2 = r2(max(-HALF_L + 1, min(HALF_L - 1, x + d * clen * math.cos(ang))))
        y2 = r2(max(-HALF_W + 1, min(HALF_W - 1, y + clen * math.sin(ang))))
        self.key(f, x, y, BALL_Z, 1, side)
        return dict(f=f2, side=side, pid=pid, at=(x2, y2), restart=None)

    def step(self, st):
        """One on-ball decision by the holder: shoot, get fouled, or pass (file 02 rules)."""
        rng = self.rng
        f, side, pid, (x, y) = st["f"], st["side"], st["pid"], st["at"]
        d = DIR[side]
        if st["restart"]:
            return self.pass_(f, side, pid, (x, y), sub=st["restart"])
        dist_to_goal = math.hypot(d * HALF_L - x, y)
        if dist_to_goal < 30 and rng.random() < SHOT_BASE + (30 - dist_to_goal) / 400:
            return self.shot(f, side, pid, (x, y))
        in_box = d * x > HALF_L - 16.5 and abs(y) < 20.16
        if not in_box and rng.random() < P_FOUL:
            return self.foul(f, side, pid, (x, y))
        return self.pass_(f, side, pid, (x, y))

    def shot(self, f, side, pid, at):
        rng, d = self.rng, DIR[side]
        x, y = at
        p = xg(x, y, d)
        goal = rng.random() < p
        outcome = "successful" if goal else rng.choice(["saved", "wide", "blocked"])
        if outcome == "wide" and rng.random() < P_WOODWORK:
            outcome = "woodwork"
        dist = math.hypot(d * HALF_L - x, y)
        body = "head" if dist < 12 and rng.random() < 0.2 else ("left_foot" if rng.random() < 0.3 else "right_foot")
        gl = d * HALF_L
        if outcome == "successful":
            end = (gl, r2(rng.uniform(-3.3, 3.3)))
        elif outcome == "saved":
            end = (r2(gl - d * rng.uniform(0.6, 1.8)), r2(rng.uniform(-2.8, 2.8)))
        elif outcome == "woodwork":
            end = (gl, 3.66 if rng.random() < 0.5 else -3.66)
        elif outcome == "wide":
            end = (gl, r2((1 if rng.random() < 0.5 else -1) * rng.uniform(4.5, 10.0)))
        else:  # blocked: a defender a few metres out
            k = min(rng.uniform(3, 8), 0.6 * dist) / max(dist, 1.0)   # never past the goal line
            end = (r2(x + (gl - x) * k), r2(y - y * k))
        speed = round(rng.uniform(15, 25) if outcome == "blocked" else rng.uniform(20, 30), 2)
        f1 = f + max(1, frames(math.hypot(end[0] - x, end[1] - y) / speed))
        z1 = round(rng.uniform(0.2, 2.2), 2) if outcome in ("successful", "saved", "woodwork") else BALL_Z
        self.key(f, x, y, 1.8 if body == "head" else BALL_Z, 1, side, "flight", 0.6 if body != "head" else 0.0)
        prev = self.events[-1] if self.events else None
        assist = [prev["seq"]] if prev and prev["type"] == "pass" and prev["receiver_id"] == pid else []
        ev = self.emit(f, type="shot", player_id=pid, team=side, x=r2(x), y=r2(y), x_end=end[0], y_end=end[1],
                       body_part=body, xg=p, is_successful=goal, outcome_type=outcome, reveal_f=f1,
                       related=assist)                            # the pass that set it up comes first
        self.hold(f, None)
        opp = OTHER[side]
        if outcome == "saved":
            keeper = self.gk(opp)
            sv = self.emit(f1, type="goalkeeping", sub_type="save", player_id=keeper, team=opp, x=end[0], y=end[1],
                           body_part="hands", related=[ev["seq"]])
            ev["related"].append(sv["seq"])
            self.hold(f1, keeper)
            self.key(f1, end[0], end[1], HANDS_Z, 1, opp)
            hold_s = round(rng.uniform(4, 9), 2)
            spot = (r2(gl - d * rng.uniform(6, 14)), r2(rng.uniform(-8, 8)))
            return dict(f=f1 + frames(hold_s), side=opp, pid=keeper, at=spot, restart=None, z=HANDS_Z)
        if outcome == "blocked":
            blocker = self.nearest(opp, end[0], end[1], x, y, False)[0]
            bl = self.emit(f1, type="defending", sub_type="block", player_id=blocker, team=opp, x=end[0], y=end[1],
                           body_part="lower_body", related=[ev["seq"]])
            ev["related"].append(bl["seq"])
            self.hold(f1, blocker)
            return self.carry(f1, opp, blocker, end)
        if outcome in ("wide", "woodwork"):
            self.key(f1, end[0], end[1], z1, 0, None)            # out of play
            restart_f = f1 + frames(round(rng.uniform(15, 25), 2))
            spot = (r2(d * (HALF_L - 5.5)), 0.0)                  # file 33 fix 1: goal kick at the defending end
            self.key(restart_f - FPS, spot[0], spot[1], BALL_Z, 0, None)
            keeper = self.gk(opp)
            self.hold(f1, keeper)
            return dict(f=restart_f, side=opp, pid=keeper, at=spot, restart="goal_kick")
        # goal: into the net, then maybe a VAR check, then kick-off (or a free kick if ruled out)
        net = (r2(gl + d * 1.2), r2(end[1] * 1.05))
        self.key(f1, end[0], end[1], z1, 1, side)
        self.key(f1 + 5, net[0], net[1], BALL_Z, 0, None)
        stands, decide_f = True, f1
        if rng.random() < P_VAR_GOAL:
            start_f = f1 + frames(round(rng.uniform(2, 4), 2))
            decide_f = start_f + frames(round(rng.uniform(15, 25), 2))
            stands = rng.random() < P_VAR_STANDS
            vc = self.emit(start_f, type="referee", sub_type="var_check", official_id="var_1",
                           outcome_type="goal_stands" if stands else "goal_disallowed", x=r2(x), y=r2(y),
                           related=[ev["seq"]], reveal_f=decide_f, var_team=side)
            ev["related"].append(vc["seq"])
            ev["var"] = {"reviewed": True, "upheld": stands}
            ev["reveal_f"] = decide_f
            if not stands:
                ev.update(is_successful=False, outcome_type="offside")
        self.key(decide_f, net[0], net[1], BALL_Z, 0, None)
        if stands:
            self.score[side] += 1
            self.goals.append((self.k, decide_f, side))
            ko_f = decide_f + frames(round(rng.uniform(30, 45), 2))
            self.key(ko_f - FPS, 0.0, 0.0, BALL_Z, 0, None)
            self.hold(f1, None)
            return dict(f=ko_f, side=opp, pid=None, at=(0.0, 0.0), restart="kick_off")
        spot = (r2(d * (HALF_L - 18)), r2(max(-20.0, min(20.0, y))))
        fk_f = decide_f + frames(round(rng.uniform(10, 20), 2))
        self.key(fk_f - FPS, spot[0], spot[1], BALL_Z, 0, None)
        taker = self.nearest(opp, spot[0], spot[1], spot[0], spot[1], True)[0]
        self.hold(decide_f, taker)
        return dict(f=fk_f, side=opp, pid=taker, at=spot, restart="free_kick")

    def foul(self, f, side, fouled, at):
        """The defending side fouls the holder: ball dead, maybe a yellow card, then a free kick."""
        rng = self.rng
        x, y = at
        opp = OTHER[side]
        fouler = self.nearest(opp, x, y, x, y, False)[0]
        card = rng.random() < P_CARD and fouler not in self.booked     # no second yellows: stays 11 v 11 (ours)
        if card:
            self.booked.add(fouler)
        self.emit(f, type="misc", sub_type="foul_committed", player_id=fouler, team=opp, x=r2(x), y=r2(y),
                  is_successful=False, outcome_type="yellow_card" if card else "unsuccessful")
        self.key(f, x, y, BALL_Z, 0, None)
        wait = rng.uniform(25, 40) if card else rng.uniform(8, 16)
        fk_f = f + frames(round(wait, 2))
        taker = fouled                                                  # the fouled player takes it
        self.key(fk_f - FPS, x, y, BALL_Z, 0, None)
        self.hold(f, taker)
        return dict(f=fk_f, side=side, pid=taker, at=(x, y), restart="free_kick")

    # ---- the period ---------------------------------------------------------------------------------
    def run(self):
        st = self.kick_off(0, self.kickoff_side)
        while True:
            if st["f"] >= self.end_f:
                break
            if st.get("restart") == "kick_off":
                self.key(st["f"], 0.0, 0.0, BALL_Z, 0, None)
                st = self.kick_off(st["f"], st["side"])
                continue
            if st["pid"] is None:
                st["pid"] = self.nearest(st["side"], st["at"][0], st["at"][1], st["at"][0], st["at"][1], True)[0]
            if st.get("z") == HANDS_Z:                     # keeper walks with the ball before releasing it
                self.key(st["f"] - 1, st["at"][0], st["at"][1], HANDS_Z, 1, st["side"])
            st = self.step(st)
        self.key(self.end_f, *self._last_ball(), BALL_Z, 0, None)
        return self

    def _last_ball(self):
        f, x, y = max((k[0], k[1], k[2]) for k in self.keys if k[0] <= self.end_f)
        return x, y


def generate(seed: int) -> dict:
    """A full synthetic match for one seed: two halves, home kicks off the first, away the second."""
    players = roster(seed)
    score, booked = {"home": 0, "away": 0}, set()
    halves = [_Half(seed, k, players, score, booked, "home" if k == 0 else "away").run() for k in range(2)]
    events = []
    for h in halves:
        events += [e for e in h.events if e["f"] < h.end_f]
    events.sort(key=lambda e: (PERIODS.index(e["period"]), e["f"], e["seq"]))
    ids = {}
    for i, e in enumerate(events):
        e["id"] = f"e{i + 1:05d}"
        ids[e["seq"]] = e["id"]
    for e in events:
        e["related_event_ids"] = [ids[s] for s in e.pop("related") if s in ids] or None
    return dict(seed=seed, version=GENERATOR_VERSION, players=players, events=events,
                periods=[dict(period=h.period, end_f=h.end_f, keys=sorted(h.keys, key=lambda k: k[0]),
                              holders=h.holders, kickoff_side=h.kickoff_side) for h in halves],
                final_score=dict(score))
