# 19 — Realistic off-ball player movement for synthetic tracking (closing the realism gap)

_Accessed/compiled: 20 Oct 2026 · Priority area: Ingest (synthetic tracking realism) + Realism Bench metrics_

## TL;DR

- Research 02 found that tracking derived from formation anchors gives only **~4 km per player per 90**, with every outfielder moving in the same way. A layered **steering model** closes most of that gap without any ML. The layers are: formation anchor, ball-side shift, a compactness scale that depends on possession, role behaviours (carrier, support triangle, pressers and cover, full-back overlap, striker run in behind, recovery runs, counter-press), Ornstein-Uhlenbeck (OU) jitter, and acceleration caps taken from published acceleration-speed (A-S) profiles.
- **Our measurement** (toy 90-minute match at 25 Hz, 3 seeds, 84-line NumPy model below): **9.9–10.4 km mean per outfielder**. By position: CB 8.4–8.8, FB 10.6–10.9, CM 11.1–12.0, W 10.4–10.9, ST 9.3–9.7 km. Players spend 52–68% of the time below 6 km/h. Team length and width are 48/48 m with the ball and 41/35 m without. All of these sit inside or near the cited reference ranges.
- **Still off target** (ours): distance above 19.8 km/h is about 1.5–2× the published values, decelerations are too few and too gentle, and goalkeepers cover only about 3.2 km (we found no cited GK figure). The Realism Bench should report these gaps openly.
- **ML route, for later:** Le et al. 2017 ("data-driven ghosting") trained one LSTM per role (2×512 units) on about 100 games at 10 fps, using roll-out training so errors don't compound. Their average deviation was about 4 m. Graph and transformer models (Graph Imputer, TranSPORTmer) need real tracking data to train. Real tracking can't ship in the product, so for the hackathon we use **rules plus calibration** and cite ML as future work.

## Findings

### 1. Building blocks (primary sources)

| Block | What it gives us | Source |
|---|---|---|
| **Reynolds steering** | `seek`: desired = normalise(target − pos)·max_speed; steering = desired − velocity. `arrival`: speed ramps down linearly inside a slowing radius. `separation`: sum of (me − them)/r² over nearby agents. `pursuit`: seek the target's predicted position (pos + vel·T). Point mass with `truncate(steering, max_force)` and `truncate(velocity, max_speed)` | Reynolds, GDC 1999 |
| **Social force model** | Acceleration toward a desired velocity (relaxation), plus repulsion from other agents and from boundaries, plus attraction terms. Written as coupled Langevin equations. This is the same structure as "steer + separate + noise" | Helbing & Molnár, Phys Rev E 51 (1995) |
| **OU process** | Mean-reverting Gaussian velocity noise: dv = −θv·dt + σ√(2θ)·dW. It gives smooth, correlated jitter, unlike white noise, which produces unrealistic acceleration | Uhlenbeck & Ornstein, Phys Rev 36 (1930) |
| **A-S profile** | Maximum acceleration falls linearly with speed: a_max(v) = A0·(1 − v/S0). This is a physically grounded cap, better than a constant 4 m/s² | Morin et al. 2021 (J Biomech), as cited by Alonso-Callejo et al. 2022 |
| **Data-driven ghosting** | 100 games, ~17,400 defensive sequences, ~3M frames at 10 fps. Roles are aligned with the Hungarian algorithm to a learned 4-4-2. Features per role are absolute positions plus polar distance/angle to the ball, the goal and the modelled role (399 dimensions). One LSTM per role (2×512). Two-phase roll-out training: single players first, then joint training. Mean deviation ~4 m, versus 20–30 m for naive models | Le, Carr, Yue, Lucey, MIT SSAC 2017 |
| **Graph Imputer** | Graph networks plus a VAE that use past and future frames to impute off-screen players (DeepMind and Liverpool FC) | Omidshafiei et al., Sci Rep 2022 |
| **TranSPORTmer** | One set-attention transformer for forecasting, imputation, ball inference and state classification (pass, possession, uncontrolled, out of play) in soccer and basketball | Capellera et al., ACCV 2024 |

The structure of the ghosting paper (a role-aligned formation, features relative to the ball, the goal and the role, and one policy per role) is exactly the structure of the rule-based model below. If we ever get licence-clean tracking data, the rule policy can be swapped for a learned one role by role.

### 2. Physical reference profiles

| Metric | Reference value | Source / caveat |
|---|---|---|
| Distance per 90 (outfield, PL 2024/25) | 8.5–12.3 km (≥1,500 min). Lowest values are centre-backs (Murillo 8.5, Van Dijk 8.8). Highest are midfielders (Kulusevski 12.3, Soucek/Tonali 12.2) | Opta via premierleague.com, Mar 2025 |
| Distance by position (Spanish league + UCL) | CB 10,627 m, CM 12,027 m, WM 11,990 m | Di Salvo et al. 2007, **as cited by** Schwesig et al. 2019 (secondary) |
| Speed > 19.1 km/h | CB 397 + 215 m (19.1–23 and >23 km/h); WM 738 + 446 m | same (secondary) |
| High-intensity running, EPL 2012/13 | 1,151 ± 337 m HIR + 350 ± 139 m sprint; 57 ± 20 sprints; mean sprint 5.9 m | Barnes et al. 2014 abstract. **Thresholds not in abstract (unverified)** |
| High-intensity running by position, EPL 2005/06 | WM 3,138, CM 2,825, FB 2,605, ST 2,341, CB 1,834 m. Falls ~20% in the last 15 min | Bradley et al. 2009 abstract. **Threshold not in abstract.** These values are far too large to be >19.8 km/h, so don't use them as a >19.8 target |
| HIR ≥ 19.8 km/h | ~3% of match time; bouts 8.4 ± 2.7 s; work:rest 1:12 | Di Mascio & Bradley 2013 |
| Time in walking (PL) | Outfield maximum 77.6% (Cunha), minimum 54.2% (Soucek). Jogging is 6–15 km/h | premierleague.com Mar 2025 (walking cut-off not stated) |
| Sprint (>25 km/h) | Leaders sprint 1.04–1.17% of time; 639–702 sprints in 29 matchweeks | same |
| Activity mix (Danish top level) | Standing 19.5%, walking 41.8%, jogging 16.7%, running 16.8%, sprinting 1.4% | Mohr et al. 2003, as cited by Bloomfield et al. 2007 |
| Top speed | 37.1 km/h fastest (Van de Ven), slowest outfielder 29.4 km/h | premierleague.com Mar 2025 |
| A0 / S0 / max accel on match day | A0 8.26–8.68 m/s², S0 9.22–9.50 m/s, ACCmax 4.78–5.35 m/s² (by position) | Alonso-Callejo et al. 2022, Sci Rep |
| Accelerations > 2 m/s² (≥ 0.7 s) | Per player per match, summed over 10 phases: **≈70 accelerations, ≈87 decelerations** (our sum of their per-phase counts) | Jerome et al. 2024, EJSS, 1,083 matches |
| Distance rate by phase | Build-up 128 m/min … fast attack 196, fast defence 208 m/min. Midfielders are highest in 8 of 10 phases | same |
| Team length / width | **31–46 m / 35–48 m**. Area ~900 m². Stretch index 7–16 m. All studies show bigger shape in possession | Rico-González et al. 2022, systematic review of 13 studies |

### 3. Movement model recipe

1. **Anchor:** a 4-4-2 in the team's own frame. The block centre follows the ball (`0.55·ball_x ± 6 m` depending on possession).
2. **Compactness:** scale anchor offsets by length 1.0 and width 1.0 in possession, and by 0.75 and 0.72 out of possession. Add a lateral shift toward the ball (0.15 in possession, 0.35 out of possession). This produces the cited "bigger with the ball" pattern.
3. **Ball-centred roles** (re-assigned only when a new event arrives, to avoid flicker):
   - The receiver runs to the **pass end point** (anticipation, not chasing the moving ball).
   - The two nearest midfielders form a **support triangle** (7 m behind, ±9 m wide).
   - Out of possession, one presser plus one cover player. **Three pressers for 4 s** after a turnover (counter-press) or after a back pass of more than 5 m.
4. **In-possession runs:** wingers hold width. The ball-side full-back **overlaps** when the ball is in the attacking half. Each striker makes a 3 s **run in behind** to the last line + 4 m (Poisson, about once a minute of possession).
5. **Recovery runs:** for 6 s after losing the ball, players caught ahead of it get urgency 0.8.
6. **Steering:** arrival (`v_des = min(urgency·S0, 0.9·dist)`), plus OU jitter (σ 0.7 m/s, τ 3 s), plus separation (<3 m), with a reaction time of 0.5 s.
7. **Caps:** per-player S0 ~ N(9.35, 0.35) and A0 ~ N(8.4, 0.5), from the cited ranges. Acceleration is capped by `A0(1 − v/S0)` for urgent moves (urgency ≥ 0.65). Routine repositioning is capped at 1.8 m/s² accelerating and 1.9 m/s² decelerating. **This one change cut acceleration counts from 300–500 to 40–90 per player.**

### 4. Realism Bench metrics: reference vs ours

Ours is the mean over seeds 7/8/9 (range in brackets). Events come from the research 02 generator (1,011–1,128 events per 90). Speed bands follow Jerome et al. 2024.

| Metric | Reference | Ours (toy) | Verdict |
|---|---|---|---|
| Distance, outfield mean | 8.5–12.3 km | **10.2** (9.9–10.4) | ok |
| CB / FB / CM / W / ST km | CB lowest, CM highest | **8.6 / 10.7 / 11.6 / 10.6 / 9.4** | order ok; ST a bit low |
| % time < 6 km/h | 54–78% | 53–68% by role | ok |
| % time > 25.2 km/h | ~1.0–1.2% (leaders) | 0.8–1.9% | slightly high |
| Distance > 19.8 km/h | ~600–1,200 m (Di Salvo, secondary) | 935–2,320 m | **too high** |
| Sprints (>25.2 km/h, ≥1 s) | 31–57 (definitions vary) | 13–35 | low end (our ≥1 s rule is stricter) |
| Accelerations / decelerations >2 m/s², ≥0.7 s | ≈70 / ≈87 | 37–90 / 12–64 | accels ok, **decels low** |
| Max speed | 29.4–37.1 km/h | 31–35 km/h | ok |
| Team length in / out of possession | 31–46 m | 47.5–48.7 / 41.2–43.1 m | slightly long |
| Team width in / out of possession | 35–48 m | 47.3–48.6 / 34.5–35.1 m | ok |
| GK distance | not found (unverified) | 3.2 km | flag |

Ablation (seed 7): switching off OU jitter drops the mean from 10.1 to 9.0 km. The rest of the gain over research 02's ~4 km comes from the role behaviours. One 90-minute match simulates in ~26 s on a laptop CPU.

Bench metrics still to add: inter-player nearest-neighbour distance, stretch index (7–16 m), in/out-of-possession area (~900 m²), and the 20% drop in high-intensity running in the last 15 minutes (Bradley 2009). That last one needs a fatigue term, for example S0 decaying a few percent over the match.

## So what for us

- **Stage: Ingest.** This model drops into the event-first generator from research 02. For each frame, pass `ball`, `poss` and `aim` (the current event's end point) and it returns 22 positions. It helps:
  - **A TwinCast:** more varied motion gives the rendered video believable crowding, occlusion and sprinting for YOLO+ByteTrack to grade against.
  - **B Speed Trap:** sprints, top speeds and distance tags now fall in realistic ranges, so threshold triggers (25 km/h, 1 km milestones) fire at plausible rates.
  - **E Realism Bench:** the table above is the report card.
  - It also makes **09 Keeper Brain** and **01 Ghost Team** possible later: a ghost team is this same model run on a counterfactual ball path.
- **Recommendation:** ship the rule model with all knobs in a YAML file (`CRUISE`, urgencies, OU σ/τ, compactness factors). Make the Realism Bench auto-print the reference-vs-ours table per seed, with a green or red marker on each row. Then do one tuning pass on the three red rows:
  - High speed: cap support and carrier urgency at 0.5.
  - Decelerations: raise the routine decel cap to about 2.5 m/s², but only when the player is above 4 m/s.
  - Goalkeeper: add a GK shuffle behaviour.
- **Positioning for judges:** say we close research 02's "4 km, players move identically" gap with cited physics (A-S profile, OU, steering), and show the before/after numbers. Few competitors will measure their synthetic data against published physical-performance ranges.

## Reuse: code & links

**Per-frame movement model** (84 lines, NumPy, run and measured as above; the `Movement` class is self-contained):

```python
import numpy as np

FPS, DT = 25, 1 / 25
# 4-4-2 anchors in the team's own frame (attacking +x). Roles: 0 GK, 1 CB, 2 FB, 3 CM, 4 W, 5 ST
ANCH = np.array([(-50, 0), (-30, -22), (-34, -8), (-34, 8), (-30, 22), (-8, -22),
                 (-14, -8), (-14, 8), (-8, 22), (10, -7), (10, 7)], float)
ROLE = np.array([0, 2, 1, 1, 2, 4, 3, 3, 4, 5, 5])
CRUISE = np.array([0.30, 0.52, 0.52, 0.56, 0.52, 0.50])  # share of S0 for routine moves (tuning)

class Movement:
    """Per-frame (25 Hz) off-ball movement for 22 players, driven by ball position + possession."""
    def __init__(self, seed=0, ou_sd=0.7, ou_tau=3.0):
        r = self.rng = np.random.default_rng(seed)
        self.side = np.repeat([1.0, -1.0], 11)          # home attacks +x, away attacks -x
        self.role, self.anchor = np.tile(ROLE, 2), np.tile(ANCH, (2, 1))
        self.pos = self.anchor * np.c_[self.side, np.ones(22)]
        self.vel, self.ou = np.zeros((22, 2)), np.zeros((22, 2))
        self.S0 = np.clip(r.normal(9.35, 0.35, 22), 8.6, 10.3)   # theoretical max speed, m/s
        self.A0 = np.clip(r.normal(8.4, 0.5, 22), 7.0, 9.5)      # theoretical max accel, m/s^2
        self.run_left, self.t_turn, self.poss_prev = np.zeros(22), -99.0, 0
        self.ou_sd, self.ou_th = ou_sd, 1 / ou_tau

    def step(self, t, ball, poss, aim=None):   # poss: +1 home has ball; aim: where the ball is going
        r, s, role, P = self.rng, self.side, self.role, self.pos
        if poss != self.poss_prev: self.t_turn, self.poss_prev = t, poss
        since, inp, gk = t - self.t_turn, s == poss, role == 0
        aim = ball if aim is None else aim
        bx, by, px = ball[0] * s, ball[1], P[:, 0] * s   # x in each player's attacking frame
        ax, ay = aim[0] * s, aim[1]
        # 1) anchor + ball-side shift + compactness (team stretches with the ball, squeezes without)
        lf, wf = np.where(inp, 1.0, 0.75), np.where(inp, 1.00, 0.72)
        tx = np.clip(0.55 * bx + np.where(inp, 6, -6), -22, 22) + (self.anchor[:, 0] + 15) * lf
        ty = self.anchor[:, 1] * wf + np.where(inp, 0.15, 0.35) * by
        tx[gk], ty[gk] = -49 + 0.08 * (bx[gk] + 52.5), 0.12 * by
        urg = CRUISE[role].copy()
        # 2) recovery runs: after a turnover, players caught ahead of the ball sprint back
        rec = (~inp) & (since < 6) & (px > bx) & ~gk
        urg[rec] = 0.8
        # 3) in-possession role behaviours: wingers hold width, ball-side FB overlaps, ST runs in behind
        side_y = np.sign(self.anchor[:, 1])
        ty = np.where(inp & (role == 4), side_y * 24, ty)
        ov = inp & (role == 2) & (side_y == np.sign(by)) & (bx > 0)
        tx[ov], ty[ov], urg[ov] = bx[ov] + 8, side_y[ov] * 25, 0.6
        self.run_left = np.where(inp, np.maximum(self.run_left - DT, 0), 0)
        start = inp & (role == 5) & (self.run_left == 0) & (r.random(22) < DT / 60)
        self.run_left[start] = 3.0
        last = {tm: (P[(s != tm) & ~gk, 0] * tm).max() for tm in (1.0, -1.0)}
        run = self.run_left > 0
        tx[run] = np.minimum([last[v] + 4 for v in s[run]], 48); urg[run] = 0.9
        # 4) ball-centred behaviours: carrier + support triangle; presser(s) + cover
        key = (float(aim[0]), float(aim[1]), poss, since < 4)       # re-assign only on a new event
        if key != getattr(self, "key", None):
            d2b = np.hypot(*(P - aim).T)
            self.key, self.order = key, {tm: np.where((s == tm) & ~gk)[0][np.argsort(d2b[(s == tm) & ~gk])] for tm in (1.0, -1.0)}
        for tm in (1.0, -1.0):
            o = self.order[tm]
            if tm == poss:
                tx[o[0]], ty[o[0]], urg[o[0]] = ax[o[0]], ay, 0.55
                mids = [i for i in o[1:] if role[i] in (3, 4)][:2]       # support triangle from midfield
                for i, dy in zip(mids, (9, -9)):
                    tx[i], ty[i], urg[i] = ax[i] - 7, ay + dy, max(urg[i], 0.45)
            else:                      # press trigger: 4 s after winning/losing it, or a back pass (+5 m)
                k = 3 if (since < 4 or ax[o[0]] > bx[o[0]] + 5) else 1
                tx[o[:k]], ty[o[:k]], urg[o[:k]] = ax[o[:k]], ay, (0.8 if k == 3 else 0.55)
                c = o[k]; tx[c], ty[c], urg[c] = 0.7 * bx[c] - 15.75, 0.7 * by, max(urg[c], 0.5)
        # 5) steering: arrive + OU jitter + separation, then accel-speed profile caps
        off = np.clip(np.c_[tx * s, ty], [-52, -33.5], [52, 33.5]) - P
        dist = np.hypot(*off.T) + 1e-9
        vdes = np.minimum(urg * self.S0, 0.9 * dist)                 # arrival ramp
        self.ou += -self.ou_th * self.ou * DT + self.ou_sd * np.sqrt(2 * self.ou_th * DT) * r.standard_normal((22, 2))
        diff = P[:, None] - P[None]; dd = np.maximum(np.hypot(diff[..., 0], diff[..., 1]), 0.3) + 99 * np.eye(22)
        rep = (((s[:, None] == s[None]) & (dd < 3)) / dd ** 2)[..., None] * diff
        desired = off / dist[:, None] * vdes[:, None] + self.ou + 2.0 * rep.sum(1)
        acc = (desired - self.vel) / 0.5                             # reaction time constant
        sp = np.hypot(*self.vel.T)
        along = (acc * self.vel).sum(1) / (sp + 1e-9)
        hard = urg >= 0.65                                           # only urgent moves use full accel
        amax = np.where(along > 0, np.minimum(np.maximum(self.A0 * (1 - sp / self.S0), 0.5), np.where(hard, 9, 1.8)),
                        np.where(hard, 6.0, 1.9))                    # decel caps: tuning, unverified
        acc *= np.minimum(1, amax / (np.hypot(*acc.T) + 1e-9))[:, None]
        self.vel += acc * DT
        self.vel *= np.minimum(1, self.S0 / (np.hypot(*self.vel.T) + 1e-9))[:, None]
        self.pos = np.clip(P + self.vel * DT, [-52.5, -34], [52.5, 34])
        return self.pos
```

**Glue to the research 02 event generator, plus the core Bench metrics** (the version we ran also adds per-role band shares, sprint and acceleration counts, and team shape):

```python
def ball_track(events, n):                      # ball pos, possession (+1/-1) and pass end point per frame
    t0 = np.array([e["time_s"] for e in events])
    xs = np.array([[e["x"], e["y"], e["x_end"], e["y_end"]] for e in events], float)
    team = np.array([1 if e["team_id"] == "home" else -1 for e in events])
    tf = np.arange(n) * DT
    i = np.clip(np.searchsorted(t0, tf, "right") - 1, 0, len(events) - 1)
    seg = xs[i]; L = np.hypot(*(seg[:, 2:] - seg[:, :2]).T) + 1e-6
    f = np.clip((tf - t0[i]) * 15.0 / L, 0, 1)[:, None]          # ball travels at 15 m/s
    return seg[:, :2] + f * (seg[:, 2:] - seg[:, :2]), team[i], seg[:, 2:]

def segments(mask, min_len):                    # count runs of True lasting >= min_len frames
    d = np.diff(np.r_[0, mask.astype(int), 0])
    return int(((np.where(d == -1)[0] - np.where(d == 1)[0]) >= min_len).sum())

# ball, poss, aim = ball_track(events, 90*60*FPS); m = Movement(seed)
# pos = np.stack([m.step(k*DT, ball[k], poss[k], aim[k]).copy() for k in range(len(ball))])
# v = np.hypot(*np.diff(pos, axis=0).transpose(2, 0, 1)) / DT         # (frames, 22) m/s
# km = v.sum(0) * DT / 1000; sprints_i = segments(v[:, i] > 7.0, FPS)
# acc_i = segments(np.diff(v[:, i]) / DT > 2.0, int(0.7 * FPS))       # Jerome et al. 2024 definition
# length = np.ptp(pos[:, 1:11, 0], 1); width = np.ptp(pos[:, 1:11, 1], 1)    # home outfield shape
```

Links:
- Reynolds steering: http://www.red3d.com/cwr/steer/gdc99/
- Data-driven ghosting PDF: https://www.sloansportsconference.com/research-papers/data-driven-ghosting-using-deep-imitation-learning
- TranSPORTmer: https://arxiv.org/abs/2410.17785
- MIDAS imputation: https://arxiv.org/abs/2408.10878
- For calibration only, SkillCorner opendata (MIT, see research 02): https://github.com/SkillCorner/opendata

## Sources

- Le, Carr, Yue, Lucey — Data-Driven Ghosting using Deep Imitation Learning (MIT SSAC 2017) — https://www.sloansportsconference.com/research-papers/data-driven-ghosting-using-deep-imitation-learning — accessed 20 Oct 2026
- Omidshafiei et al. — Multiagent off-screen behavior prediction in football, Sci Rep 2022 (abstract only) — https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9126960/ — accessed 20 Oct 2026
- Capellera et al. — TranSPORTmer, ACCV 2024 (abstract only) — https://arxiv.org/abs/2410.17785 — accessed 20 Oct 2026
- MIDAS / trajectory imputation in multi-agent sports (abstract only) — https://arxiv.org/abs/2408.10878 — accessed 20 Oct 2026
- Reynolds — Steering Behaviors for Autonomous Characters (GDC 1999) — http://www.red3d.com/cwr/steer/gdc99/ — accessed 20 Oct 2026
- Helbing & Molnár — Social Force Model for Pedestrian Dynamics, Phys Rev E 51:4282 (1995) — https://arxiv.org/abs/cond-mat/9805244 — accessed 20 Oct 2026
- Uhlenbeck & Ornstein — On the Theory of the Brownian Motion, Phys Rev 36:823 (1930) — https://doi.org/10.1103/PhysRev.36.823 — accessed 20 Oct 2026
- Alonso-Callejo et al. — Effect of playing position and microcycle days on the acceleration speed profile of elite football players, Sci Rep 2022 (cites Morin et al. 2021) — https://pmc.ncbi.nlm.nih.gov/articles/PMC9649751 — accessed 20 Oct 2026
- Jerome et al. — Contextualised physical metrics: physical demands vary with phase of play, EJSS 2024 — https://pmc.ncbi.nlm.nih.gov/articles/PMC11534638/ — accessed 20 Oct 2026
- Rico-González et al. — Reference values for collective tactical behaviours, Biology of Sport 39(1) 2022 (abstract) — https://www.termedia.pl/Reference-values-for-collective-tactical-behaviours-based-on-positional-data-in-professional-football-matches-a-systematic-review,78,43095,0,1.html — accessed 20 Oct 2026
- Bradley et al. — High-intensity running in English FA Premier League soccer matches, J Sports Sci 2009 (abstract) — https://lida.sport-iat.de/ta/Record/4015478?lng=en — accessed 20 Oct 2026
- Di Mascio & Bradley — Most intense high-intensity running periods in EPL matches, JSCR 2013 (abstract) — https://sure.sunderland.ac.uk/id/eprint/3476/ — accessed 20 Oct 2026
- Barnes et al. — Evolution of physical and technical performance parameters in the EPL, IJSM 2014 (abstract) — https://lida.sport-iat.de/ta/Record/4033554?lng=en — accessed 20 Oct 2026
- Schwesig et al. 2019, Frontiers in Physiology (secondary source for Di Salvo et al. 2007 values) — https://www.frontiersin.org/journals/physiology/articles/10.3389/fphys.2019.00886/full — accessed 20 Oct 2026
- Di Salvo et al. — Performance characteristics according to playing position in elite soccer, IJSM 2007 (page blocked; speed bands via search snippet) — https://www.thieme-connect.de/products/ejournals/abstract/10.1055/s-2006-924294 — accessed 20 Oct 2026
- Bloomfield, Polman, O'Donoghue — Physical demands of different positions in FA Premier League soccer, JSSM 2007 (cites Mohr et al. 2003) — https://pmc.ncbi.nlm.nih.gov/articles/PMC3778701 — accessed 20 Oct 2026
- Opta Analyst / premierleague.com — Who tops the 2024/25 running charts? — https://www.premierleague.com/news/4272290 — accessed 20 Oct 2026
- Research 02 (our generator and the ~4 km finding) — stoynev research/02-synthetic-match-data.md — accessed 20 Oct 2026
