"""Ball and player tracks at 25 Hz from generator.py's output (; file 19 Movement model).



ball_rows(): the ball path from the generator's keyframes -> [x, y, z, alive, poss] per frame (contract columns).
Movement:    file 19's per-frame model (anchor + compactness, recovery runs, wingers/overlaps/runs in behind,
             support triangle, pressers + cover, arrive steering with OU jitter, separation, A-S caps), with one
             change: the player the events say has (or will receive) the ball is the one who goes to it.

Determinism: NumPy is used for element-wise maths only (+ - * / sqrt, min/max, where, clip). Those are exact
IEEE operations on every CPU. We avoid np.hypot, float reductions (sum) and unstable sorts, whose results can
depend on the CPU's SIMD path, and the random jitter comes from Python's `random.Random`, not NumPy.
"""
from __future__ import annotations

import random

import numpy as np

from .generator import FPS, HALF_L, HALF_W, SLOTS

DT = 1 / FPS
ROLE_ID = {"GK": 0, "CB": 1, "FB": 2, "CM": 3, "W": 4, "ST": 5}
CRUISE = np.array([0.30, 0.52, 0.52, 0.56, 0.52, 0.50])     # file 19: share of S0 for routine moves (tuning)


# ---------------------------------------------------------------- ball
def ball_rows(keys: list, f0: int, f1: int) -> list:
    """Rows for frames f0..f1 inclusive. Between two keyframes the ball moves in a straight line; a "flight"
    leaves the foot at 1.3x and arrives at 0.7x the average speed (grass friction) and may be lofted."""
    ks = sorted(keys, key=lambda k: k[0])          # stable: a later key at the same frame wins
    rows, j = [], 0
    for f in range(f0, f1 + 1):
        while j + 1 < len(ks) and ks[j + 1][0] <= f:
            j += 1
        a = ks[j]
        b = ks[j + 1] if j + 1 < len(ks) else a
        if f < a[0] or b[0] == a[0]:
            x, y, z = a[1], a[2], a[3]
        else:
            u = (f - a[0]) / (b[0] - a[0])
            pos = u * (1.3 - 0.3 * u) if a[6] == "flight" else u
            x, y = a[1] + (b[1] - a[1]) * pos, a[2] + (b[2] - a[2]) * pos
            z = a[3] + (b[3] - a[3]) * u + 4 * a[7] * u * (1 - u)
        alive = a[4]
        rows.append([round(x + 0.0, 2), round(y + 0.0, 2), round(max(z, 0.11) + 0.0, 2), alive,
                     a[5] if alive else None])
    return rows


def aim_points(keys: list, f0: int, f1: int) -> list:
    """Where the ball is going at each frame: the end of the current flight, else where it is."""
    ks = sorted(keys, key=lambda k: k[0])
    out, j = [], 0
    for f in range(f0, f1 + 1):
        while j + 1 < len(ks) and ks[j + 1][0] <= f:
            j += 1
        a = ks[j]
        b = ks[j + 1] if j + 1 < len(ks) else a
        out.append((b[1], b[2]) if a[6] == "flight" else None)
    return out


def runner_at(events: list, period: str, f0: int, f1: int) -> list:
    """Who is running to where the ball will be next, per frame: the receiver of the next pass (or the player who
    will cut it out, block it or save it) starts moving at the previous touch, so they arrive with the ball."""
    evs = [e for e in events if e["period"] == period]
    by_id = {e["id"]: e for e in evs}
    plan = []
    prev_f = None
    for e in evs:
        if e["type"] == "pass":
            if e["receiver_id"]:
                who = e["receiver_id"]
            else:
                rel = [by_id[i] for i in e["related_event_ids"] or () if i in by_id]
                who = rel[0]["player_id"] if rel else None
            if who:
                plan.append((prev_f if prev_f is not None else e["f"], e["reveal_f"], who, (e["x_end"], e["y_end"])))
        elif e["type"] == "shot" and e["related_event_ids"]:
            for i in e["related_event_ids"]:
                r = by_id.get(i)
                if r and r["type"] in ("goalkeeping", "defending"):
                    plan.append((e["f"], r["f"], r["player_id"], (r["x"], r["y"])))
        if e.get("player_id") and e["type"] != "referee":
            prev_f = e["f"]
    out = [None] * (f1 - f0 + 1)
    for a, b, who, xy in plan:
        for f in range(max(a, f0), min(b, f1) + 1):
            out[f - f0] = (who, xy)
    return out


def holder_at(holders: list, f0: int, f1: int) -> list:
    hs = sorted(holders, key=lambda h: h[0])
    out, j, cur = [], 0, None
    for f in range(f0, f1 + 1):
        while j < len(hs) and hs[j][0] <= f:
            cur = hs[j][1]
            j += 1
        out.append(cur)
    return out


# ---------------------------------------------------------------- players
def _len(x, y):
    return np.sqrt(x * x + y * y)


class Movement:
    """Per-frame (25 Hz) movement for 22 players (file 19), driven by the ball, possession and the holder."""

    def __init__(self, seed: int, ids: list, players: dict, ou_sd=0.7, ou_tau=3.0):
        self.rng = random.Random(seed * 104729 + 3)
        self.ids, self.index = ids, {p: i for i, p in enumerate(ids)}
        self.side = np.array([1.0 if players[p]["side"] == "home" else -1.0 for p in ids])
        self.role = np.array([ROLE_ID[players[p]["role"]] for p in ids])
        self.anchor = np.array([players[p]["anchor"] for p in ids], float)
        self.pos = self.anchor * np.c_[self.side, np.ones(22)]
        self.vel, self.ou = np.zeros((22, 2)), np.zeros((22, 2))
        self.S0 = np.clip(np.array([9.35 + 0.35 * self._normal() for _ in ids]), 8.6, 10.3)   # m/s (file 19)
        self.A0 = np.clip(np.array([8.4 + 0.5 * self._normal() for _ in ids]), 7.0, 9.5)      # m/s^2 (file 19)
        self.run_left, self.t_turn, self.poss_prev = np.zeros(22), -99.0, 0
        self.ou_sd, self.ou_th = ou_sd, 1 / ou_tau
        self.key, self.order = None, None
        self.sep_eye = 99 * np.eye(22)

    def _normal(self) -> float:
        """Approximately N(0, 1) from 4 uniforms (Irwin-Hall): additions only, so identical on every machine."""
        r = self.rng.random
        return (r() + r() + r() + r() - 2.0) * 1.7320508075688772

    def place(self, xy: np.ndarray):
        self.pos = xy.copy()

    def step(self, t: float, ball, poss: int, aim=None, holder: str | None = None, runner=None):
        s, role, P = self.side, self.role, self.pos
        if poss != self.poss_prev:
            self.t_turn, self.poss_prev = t, poss
        since, inp, gk = t - self.t_turn, s == poss, role == 0
        aim = ball if aim is None else aim
        bx, by, px = ball[0] * s, ball[1], P[:, 0] * s
        ax, ay = aim[0] * s, aim[1]
        # 1) anchor + ball-side shift + compactness
        lf, wf = np.where(inp, 1.0, 0.75), np.where(inp, 1.0, 0.72)
        tx = np.clip(0.55 * bx + np.where(inp, 6.0, -6.0), -22, 22) + (self.anchor[:, 0] + 15) * lf
        ty = self.anchor[:, 1] * wf + np.where(inp, 0.15, 0.35) * by
        tx = np.where(gk, -49 + 0.08 * (bx + 52.5), tx)
        ty = np.where(gk, 0.12 * by, ty)
        urg = CRUISE[role].copy()
        # 2) recovery runs after a turnover
        urg = np.where((~inp) & (since < 6) & (px > bx) & ~gk, 0.8, urg)
        # 3) wingers hold width, ball-side full-back overlaps, strikers run in behind
        side_y = np.sign(self.anchor[:, 1])
        ty = np.where(inp & (role == 4), side_y * 24, ty)
        ov = inp & (role == 2) & (side_y == np.sign(by)) & (bx > 0)
        tx, ty, urg = np.where(ov, bx + 8, tx), np.where(ov, side_y * 25, ty), np.where(ov, 0.6, urg)
        self.run_left = np.where(inp, np.maximum(self.run_left - DT, 0), 0)
        draws = np.array([self.rng.random() for _ in range(22)])
        start = inp & (role == 5) & (self.run_left == 0) & (draws < DT / 60)
        self.run_left = np.where(start, 3.0, self.run_left)
        run = self.run_left > 0
        if run.any():
            last = {tm: float((P[(s != tm) & ~gk, 0] * tm).max()) for tm in (1.0, -1.0)}
            line = np.array([min(last[v] + 4, 48) for v in s])
            tx, urg = np.where(run, line, tx), np.where(run, 0.9, urg)
        # 4) ball-centred roles: the holder goes to the ball; support triangle; presser(s) + cover
        key = (round(float(aim[0]), 2), round(float(aim[1]), 2), poss, since < 4, holder)
        if key != self.key:
            d2 = (P[:, 0] - aim[0]) ** 2 + (P[:, 1] - aim[1]) ** 2
            self.key = key
            self.order = {tm: [i for i in np.argsort(d2, kind="stable") if s[i] == tm and not gk[i]]
                          for tm in (1.0, -1.0)}
        hold_i = self.index.get(holder) if holder else None
        for tm in (1.0, -1.0):
            o = self.order[tm]
            if tm == poss:
                lead = hold_i if hold_i is not None and s[hold_i] == tm else o[0]
                tx[lead], ty[lead], urg[lead] = ax[lead], ay, 0.85
                mids = [i for i in o if i != lead and role[i] in (3, 4)][:2]
                for i, dy in zip(mids, (9, -9)):
                    tx[i], ty[i], urg[i] = ax[i] - 7, ay + dy, max(urg[i], 0.45)
            else:
                k = 3 if (since < 4 or ax[o[0]] > bx[o[0]] + 5) else 1
                for i in o[:k]:
                    tx[i], ty[i], urg[i] = ax[i], ay, (0.8 if k == 3 else 0.55)
                c = o[k]
                tx[c], ty[c], urg[c] = 0.7 * bx[c] - 15.75, 0.7 * by, max(urg[c], 0.5)
        if hold_i is not None and s[hold_i] != poss:      # e.g. an interceptor reaching for a pass
            tx[hold_i], ty[hold_i], urg[hold_i] = ax[hold_i], ay, 0.85
        if runner is not None and runner[0] in self.index:  # next receiver / interceptor moves into place early
            i = self.index[runner[0]]
            tx[i], ty[i], urg[i] = runner[1][0] * s[i], runner[1][1], 0.8
        # 5) steering: arrive + OU jitter + separation, then the accel-speed caps
        gx = np.clip(tx * s, -52.0, 52.0)
        gy = np.clip(ty, -33.5, 33.5)
        offx, offy = gx - P[:, 0], gy - P[:, 1]
        dist = _len(offx, offy) + 1e-9
        vdes = np.minimum(urg * self.S0, 0.9 * dist)
        noise = np.array([[self._normal(), self._normal()] for _ in range(22)])
        self.ou = self.ou - self.ou_th * self.ou * DT + self.ou_sd * np.sqrt(2 * self.ou_th * DT) * noise
        dx = P[:, None, 0] - P[None, :, 0]
        dy = P[:, None, 1] - P[None, :, 1]
        dd = np.maximum(_len(dx, dy), 0.3) + self.sep_eye
        w = ((s[:, None] == s[None, :]) & (dd < 3)) / (dd * dd)
        repx, repy = np.zeros(22), np.zeros(22)
        for j in range(22):                               # explicit sum: same order on every machine
            repx = repx + w[:, j] * dx[:, j]
            repy = repy + w[:, j] * dy[:, j]
        desx = offx / dist * vdes + self.ou[:, 0] + 2.0 * repx
        desy = offy / dist * vdes + self.ou[:, 1] + 2.0 * repy
        accx, accy = (desx - self.vel[:, 0]) / 0.5, (desy - self.vel[:, 1]) / 0.5
        sp = _len(self.vel[:, 0], self.vel[:, 1])
        along = (accx * self.vel[:, 0] + accy * self.vel[:, 1]) / (sp + 1e-9)
        hard = urg >= 0.65
        amax = np.where(along > 0,
                        np.minimum(np.maximum(self.A0 * (1 - sp / self.S0), 0.5), np.where(hard, 9.0, 1.8)),
                        np.where(hard, 6.0, 1.9))
        k_acc = np.minimum(1.0, amax / (_len(accx, accy) + 1e-9))
        vx, vy = self.vel[:, 0] + accx * k_acc * DT, self.vel[:, 1] + accy * k_acc * DT
        k_v = np.minimum(1.0, self.S0 / (_len(vx, vy) + 1e-9))
        self.vel = np.c_[vx * k_v, vy * k_v]
        self.pos = np.c_[np.clip(P[:, 0] + self.vel[:, 0] * DT, -HALF_L, HALF_L),
                         np.clip(P[:, 1] + self.vel[:, 1] * DT, -HALF_W, HALF_W)]
        return self.pos


def simulate(match: dict, period: int, f0: int, f1: int, warmup_s: float = 30.0):
    """Ball rows (25 Hz) and player positions (25 Hz, 22 x 2) for frames f0..f1 of one period.
    Movement starts warmup_s earlier from the formation, so the window opens with players already in shape."""
    per = match["periods"][period]
    ids = [p for side in ("home", "away") for p in match["players"] if match["players"][p]["side"] == side]
    ids.sort(key=lambda p: (match["players"][p]["side"] != "home", match["players"][p]["slot"]))
    w0 = max(0, f0 - round(warmup_s * FPS))
    ball = ball_rows(per["keys"], w0, f1)
    aims = aim_points(per["keys"], w0, f1)
    holders = holder_at(per["holders"], w0, f1)
    runners = runner_at(match["events"], per["period"], w0, f1)
    mv = Movement(match["seed"] * 2 + period, ids, match["players"])
    out = []
    poss_last = 0
    for k, f in enumerate(range(w0, f1 + 1)):
        x, y, _, alive, side = ball[k]
        poss = (1 if side == "home" else -1) if alive else poss_last
        poss_last = poss
        pos = mv.step(f * DT, (x, y), poss, aims[k], holders[k], runners[k])
        if f >= f0:
            out.append(pos.copy())
    return ids, ball[f0 - w0:], out
