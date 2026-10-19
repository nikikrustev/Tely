# 08 — Pass difficulty, expected pass completion (xP) and expected threat (xT)

_Accessed/compiled: 20 Oct 2026 · Priority area: Interpret stage metrics (pass quality, value added) for 03 Dive Judges, C One Number, A TwinCast, F Graphics Desk_

## TL;DR

- **Pass difficulty is 1 − P(completion).** Every public xPass model (StatsBomb, Stats Perform/Opta, Bundesliga/AWS) is a classifier. Its inputs are start location, distance, angle, pressure, body part and play pattern, plus defenders in the lane and around the receiver when player positions exist. Our synthetic generator already knows all of these, so a 0-10 "Dive Judges" score can be `10 × (1 − xPass)`.
- **Tracking-based models do better than event-only ones.** StatsBomb reports event-only xPass at log loss 0.314 and xPass 360 (freeze frames) at 0.274. Spearman et al. (2017) built a physics model with no learning beyond 2 parameters: time-to-intercept plus a logistic (σ ≈ 0.45 s) and a control rate λ ≈ 4.3/s. We can implement a simplified version in about 25 lines of NumPy (below).
- **xT** (Karun Singh) splits the pitch into a grid. It is solved by value iteration, `xT = s·g + m·(T @ xT)`, and a move's value is `xT(end) − xT(start)`. Note: Singh's post uses **16×12**. The **12×8** grid is his downloadable "open xT" JSON, which the socceraction quick-start loads. `socceraction.xthreat.ExpectedThreat(l=16, w=12, eps=1e-5)` has `.fit()` / `.rate()`.
- **Rule risk:** the published 12×8 grid comes from **real 2017-18 Premier League data** and has no licence statement. Using it, or fitting on StatsBomb open data, means real data enters a contest that forbids it. The safest option is to fit xT on our own synthetic matches with the 30-line solver below. That is circular, but it is consistent and self-contained.
- **Broadcast precedent:** Bundesliga Match Facts "Passing Profile" (AWS, since 2021) puts xPass on TV. Each pass gets a difficulty score, and those scores roll up into "completed vs expected" and "difficult passes attempted" graphics.

## Findings

### 1. xPass / pass-difficulty models (event-only vs tracking)

| Model | Inputs (as published) | Notes |
|---|---|---|
| StatsBomb xPass (event) | start location, target distance, pass angle, under pressure, body part, pattern of play (open play / set piece) | Example: a backwards pass in your own third with no pressure is about 99%. A switch to the far flank is "closer to 40% or even less". Pass height is **not** a feature. |
| StatsBomb xPass 360 | the above + opposition around the passer, opposition "along the path of the pass" (a cone-shaped segment, PCA-compressed), opposition and teammates at the target, soft pressure at several σ | Log loss 0.314 (event) → 0.274 (360). On 740 PL games: SoccerMap 0.217 vs xPass 360 0.205. |
| Stats Perform / Opta xP | start location, angle and distance (from end location), foot vs head, cross or not, open play vs set piece | Leads to **PAx**, passes completed above expected. |
| Bundesliga / AWS xPass | 26 features computed in AWS Glue. Named ones: distance to receiver, defenders in between, pressure on the passer. Bundesliga.com also names ball height. | Supervised model in SageMaker, trained on "nearly 2 million passes". |
| Power et al. KDD 2017 "Not all passes are created equal" | tracking-based risk (chance of completion) and reward (chance the pass leads to a shot) | Bibliographic details checked on DBLP (KDD 2017, pp. 1605-1613). The full text was paywalled (403), so feature details are (unverified). |

**Event-only vs tracking.** With only event data, "defenders in lane" and "receiver marked" have to be approximated by pressure flags. With tracking data, or our synthetic positions, they can be computed exactly, and that is where the published improvement in log loss comes from. Because we generate positions, we get the "360" features at no extra cost.

**From xPass to a 0-10 "pass difficulty rating".**

1. `difficulty = 10 × (1 − p)`, where `p` is xPass. This is the simplest option and is easy to explain ("this pass had a 27% chance → difficulty 7.3").
2. **Percentile normalisation.** Rank `1 − p` against every pass in the match, or in a reference set of synthetic matches, and report the percentile / 10. This spreads the scores out, because real xPass sits mostly in the 80-99% range and option 1 would put most passes at 0-2.
3. **Execution score.** A diving judge scores difficulty and execution separately. Report `difficulty` (pre-pass) and `outcome − p` (PAx-style: +0.73 for completing a 27% pass). StatsBomb bins passes by xPass bracket (for example "0-30%", "60-80%", ">90%") to compare players. We can reuse those buckets as the judges' "tariff" bands.

### 2. Physics / interception model from tracking (Spearman et al. 2017)

From the paper summary (the primary PDF on ResearchGate returned 403), the model works like this. The ball's initial velocity comes from its first 0.4 s, with drag but no Magnus or rolling. Each player's time-to-intercept is limited by speed and acceleration. Arrival uncertainty is a logistic with σ = 0.45 ± 0.05 s. Control once the player arrives follows `1 − e^(−λt)` with λ = 4.30 ± 1.14 /s. The data was 10,875 passes from 38 Crystal Palace 2015-16 matches. On a 12-game test set the model predicted 80.5% of pass outcomes and 67.9% of receivers correctly. These parameter values are from a secondary summary; the same σ and λ (0.45 and 4.3) are hard-coded in the Friends of Tracking pitch-control code, which supports them.

Laurie Shaw's Friends of Tracking implementation (`Metrica_PitchControl.py`, based on Spearman 2018) uses these defaults: `max_player_speed=5`, `reaction_time=0.7`, `tti_sigma=0.45`, `lambda_att=4.3`, `lambda_gk = 3×lambda_def`, `average_ball_speed=15` m/s. Its time to intercept is `reaction + |target − (pos + vel·reaction)| / vmax`. Its interception probability is the logistic `1/(1+exp(−π/√3/σ·(T − tti)))`.

**Simplified version for us** (code below): the ball moves in a straight line at 15 m/s. We sample points every 1 m along the pass. Each defender gets a logistic chance of reaching the lane before the ball, and the probability of a clean pass is the product of (1 − the worst point for each defender). We then multiply by the chance that the receiver reaches the target. It has no drag and no control integral, but it is deterministic, explainable ("defender #4 was 0.3 s from cutting it out"), and needs no training data. On a test, a back pass came out at 0.95, a through ball past a centre-back at 0.004, and a wide pass into space at 0.79.

### 3. Expected threat (xT)

- **Grid.** Singh's post uses 16×12 = 192 zones. socceraction's defaults are also `l=16, w=12`. The **12×8** grid is the downloadable `open_xt_12x8_v1.json` ("league-wide xT values from the 2017-18 Premier League season"). Its values run from about 0.006 (own corner) to 0.257 (central zone at the goal mouth).
- **Model.** Each zone has a shoot probability `s` and a move probability `m`, which sum to 1. It also has a goal probability given a shot, `g`, and a transition matrix `T` (zone → zone) for successful moves. The update is `xT(z) = s·g + m·Σ T(z→z')·xT(z')`.
- **Solving.** Start with xT = 0 and iterate. Iteration 1 is just xG. Iteration n means "probability of scoring within the next n actions". Singh found 4-5 iterations enough. socceraction iterates until the change is below `eps=1e-5`.
- **Valuing actions.** For a successful pass or carry, the value is `xT(end) − xT(start)`, with bilinear interpolation optional (`rate(actions, use_interpolation=True)`). Failed moves, shots and defensive actions get no xT in the basic model. If we divide `T` by **all** move attempts (not just successful ones), failures leak value implicitly.
- **socceraction API** (MIT licence, Python 3.9-3.12): `xTModel = xthreat.ExpectedThreat(l=16, w=12)`, then `xTModel.fit(actions_ltr)`, then `xTModel.rate(xthreat.get_successful_move_actions(actions))`. Use `xthreat.load_model(url)` for a saved grid. Actions must be in SPADL format with play normalised left-to-right.

### 4. VAEP (alternative)

VAEP values a game state as `V(S) = P_scores − P_concedes` for the team in possession within the **next 10 actions**, using the **last 3 actions** as the state. Two gradient-boosted classifiers give the two probabilities. The value of an action is `ΔP_scores − ΔP_concedes`. VAEP rates every action (including failed passes, tackles and shots) and uses context, so it is richer than xT. It also needs many labelled matches to train, which pushes us back towards real data. In socceraction it is `fs.gamestates(actions, 3)`, then labels, then `vaepformula.value(actions, p_scores, p_concedes)`.

### 5. Data options and rule risk

| Option | Rule risk | Comment |
|---|---|---|
| Karun Singh's open 12×8 JSON | **High.** Derived from real PL 2017-18 data, no licence statement found | Fine for a private sanity check, but do not ship it. |
| Fit xT / xPass on StatsBomb open data offline, ship only weights | Medium-high. It is still real-match-derived, and StatsBomb open data has its own terms (unverified) | Flag it to the judges if used at all. |
| **Fit xT on our synthetic matches** (recommended) | None | Circular (the generator's own tendencies come back out), but it is consistent and reproducible, and it doubles as a realism check for E Realism Bench. |
| Heuristic or physics xPass (no training) | None | Weights are set by hand, so they are explainable and need no data. |

### 6. Broadcast presentation

The AWS / DFL "Passing Profile" (launched in September 2021) gives three things. It computes a completion probability for each pass. It aggregates them into completed minus expected (for example, two 40% passes both completed = +1.2). It renders a direction/distribution graphic, a "difficult passes attempted, completion rate, short vs long ratio" card, and a half-time two-player comparison. No latency figures are published. This precedent supports our approach: a per-pass number feeds an aggregate card plus a head-to-head template.

## So what for us

- **Interpret stage → 03 Dive Judges:** use the heuristic score as the "tariff" (difficulty 0-10), PAx-style `outcome − p` as "execution", and xT added as the "style" panel. Show all three as a judges' scorecard cue. Evidence ids = pass event id + the defender ids found in the lane, so the fact-checker can verify "2 defenders in the lane".
- **A TwinCast / E Realism Bench:** compute xPass with the physics model on **ground-truth** positions and again on **CV-detected** positions. The gap between them is a clean "how good is our tracking" metric. Fit xT on 50-100 synthetic matches and publish the grid alongside the realism report.
- **C One Number:** cumulative "xT added" per player, or "PAx", is a single number that works well for a one-metric viewing mode.
- **Render:** cue fields `metric: "pass_difficulty"`, `value: 7.3`, `p_complete: 0.27`, `xt_added: 0.081`, `text.casual: "A 1-in-4 pass. He found it."`, `text.analyst: "xPass 27%, 1 defender in lane, receiver under pressure, +0.08 xT"`.
- **Do not** ship the 12×8 PL grid or anything trained on real matches. Mention in the README that every model is either hand-set or fitted on synthetic data.

## Reuse: code & links

**Lane defenders + heuristic difficulty (0-10)**. The weights are hand-set; tune them so the median synthetic pass is about 1.5-2.5.

```python
import numpy as np
PITCH_L, PITCH_W = 105.0, 68.0

def lane_defenders(start, end, defenders, width=2.0):
    """Defenders within `width` m of the segment start->end (ignores those behind passer / beyond target+1m)."""
    s, e = np.asarray(start, float), np.asarray(end, float)
    d = np.asarray(defenders, float).reshape(-1, 2); v = e - s; L2 = float(v @ v)
    if L2 == 0 or len(d) == 0: return 0
    t = ((d - s) @ v) / L2
    dist = np.linalg.norm(d - (s + np.outer(np.clip(t, 0, 1), v)), axis=1)
    return int(((t > 0) & (t < 1 + 1 / np.sqrt(L2)) & (dist <= width)).sum())

def pressure_on(p, defenders, radius=5.0):
    d = np.asarray(defenders, float).reshape(-1, 2)
    return 0.0 if len(d) == 0 else float(max(0.0, 1 - np.linalg.norm(d - p, axis=1).min() / radius))

def pass_difficulty(start, end, defenders, attack_dir=+1, height="ground", body_part="foot"):
    """Returns (difficulty 0..10, pseudo-xPass)."""
    s, e = np.asarray(start, float), np.asarray(end, float)
    dist = float(np.linalg.norm(e - s))
    forward = attack_dir * (e[0] - s[0]) / dist if dist else 0.0            # -1 back .. +1 straight forward
    depth = e[0] / PITCH_L if attack_dir > 0 else 1 - e[0] / PITCH_L
    z = (-3.2 + 0.055 * dist + 0.9 * max(forward, 0)
         + 1.2 * pressure_on(s, defenders) + 1.0 * pressure_on(e, defenders, 4.0)
         + 0.8 * lane_defenders(s, e, defenders)
         + 0.6 * (height == "high") + 0.7 * (body_part == "head")
         + 2.4 * max(0.0, depth - 2 / 3))                                    # into final third
    p_fail = 1 / (1 + np.exp(-z))
    return round(10 * p_fail, 1), round(1 - p_fail, 3)
# defs=[(60,30),(70,40),(80,34),(55,20)]: back pass (50,34)->(40,30) = 0.7; through ball ->(88,34) = 7.3
```

**Simplified Spearman time-to-intercept xPass** (parameters from Spearman / Friends of Tracking):

```python
def p_pass_tti(start, end, defenders, def_vel=None, receiver=None,
               ball_speed=15.0, vmax=5.0, reaction=0.7, sigma=0.45, step=1.0):
    s, e = np.asarray(start, float), np.asarray(end, float); L = np.linalg.norm(e - s)
    pts = s + np.outer(np.linspace(step / L, 1, max(int(L / step), 1)), e - s)
    t_ball = np.linalg.norm(pts - s, axis=1) / ball_speed
    D = np.asarray(defenders, float).reshape(-1, 2)
    V = np.zeros_like(D) if def_vel is None else np.asarray(def_vel, float).reshape(-1, 2)
    tti = reaction + np.linalg.norm(pts[None] - (D + V * reaction)[:, None], axis=2) / vmax
    k = np.pi / np.sqrt(3) / sigma
    p = np.prod(1 - (1 / (1 + np.exp(-k * (t_ball[None] - tti)))).max(axis=1))
    if receiver is not None:                       # receiver anticipates: no reaction delay
        p *= 1 / (1 + np.exp(-k * (t_ball[-1] - np.linalg.norm(e - receiver) / vmax)))
    return float(p)
```

**xT value iteration in NumPy** (tested on 20k synthetic events: it converged in 27 iterations at eps 1e-5 and gave a sensible goal-mouth peak):

```python
def xt_value_iteration(shots, goals, moves, move_success, l=12, w=8, eps=1e-5, max_iter=100):
    """shots/goals/moves: (w,l) count grids; move_success: (N,4) int array (c0,r0,c1,r1)."""
    n = l * w; total = shots + moves
    with np.errstate(divide="ignore", invalid="ignore"):
        p_shot = np.nan_to_num(shots / total); p_move = np.nan_to_num(moves / total)
        p_goal = np.nan_to_num(goals / shots)
    T = np.zeros((n, n)); c0, r0, c1, r1 = move_success.T
    np.add.at(T, (r0 * l + c0, r1 * l + c1), 1.0)
    T /= np.maximum(moves.reshape(n, 1), 1)        # / all attempts -> failed moves lose value
    gs, pm, xT = (p_shot * p_goal).ravel(), p_move.ravel(), np.zeros(n)
    for it in range(max_iter):
        new = gs + pm * (T @ xT)
        done = np.max(np.abs(new - xT)) < eps; xT = new
        if done: break
    return xT.reshape(w, l)

def cell(x, y, l=12, w=8):
    return min(int(x / PITCH_L * l), l - 1), min(int(y / PITCH_W * w), w - 1)

def xt_added(grid, start, end):                     # value of a successful pass/carry
    w, l = grid.shape; (c0, r0), (c1, r1) = cell(*start, l, w), cell(*end, l, w)
    return float(grid[r1, c1] - grid[r0, c0])
```

**socceraction**, if we convert synthetic events to SPADL:

```python
from socceraction import xthreat
m = xthreat.ExpectedThreat(l=16, w=12)          # defaults; eps=1e-5
m.fit(actions_ltr)                               # SPADL, all teams attacking left->right
moves = xthreat.get_successful_move_actions(actions_ltr)
moves["xT_value"] = m.rate(moves, use_interpolation=True)
```

Links: socceraction https://github.com/ML-KULeuven/socceraction · LaurieOnTracking (pitch control) https://github.com/Friends-of-Tracking-Data-FoTD/LaurieOnTracking · Soccermatics xT lesson https://soccermatics.readthedocs.io/en/latest/gallery/lesson4/plot_ExpectedThreat.html

## Sources

- Karun Singh, "Introducing Expected Threat (xT)" — https://karun.in/blog/expected-threat.html — accessed 20 Oct 2026
- Karun Singh, open xT 12×8 grid JSON — https://karun.in/blog/data/open_xt_12x8_v1.json — accessed 20 Oct 2026
- socceraction docs, Expected Threat — https://socceraction.readthedocs.io/en/latest/documentation/valuing_actions/xT.html — accessed 20 Oct 2026
- socceraction docs, Quickstart (12×8 grid, 2017-18 PL) — https://socceraction.readthedocs.io/en/latest/documentation/intro.html — accessed 20 Oct 2026
- socceraction docs, VAEP — https://socceraction.readthedocs.io/en/latest/documentation/valuing_actions/vaep.html — accessed 20 Oct 2026
- socceraction source `xthreat.py` — https://github.com/ML-KULeuven/socceraction/blob/master/socceraction/xthreat.py — accessed 20 Oct 2026
- socceraction repo (MIT licence, Python 3.9-3.12) — https://github.com/ML-KULeuven/socceraction — accessed 20 Oct 2026
- Spearman et al., "Physics-Based Modeling of Pass Probabilities in Soccer" (SSAC 2017; PDF returned 403, so details come from the summary below) — https://www.researchgate.net/publication/315166647_Physics-Based_Modeling_of_Pass_Probabilities_in_Soccer — accessed 20 Oct 2026
- The xG Football Club, summary of Spearman et al. 2017 (secondary) — https://thexgfootballclub.substack.com/p/the-perfect-pass-formula-can-physics — accessed 20 Oct 2026
- Laurie Shaw / Friends of Tracking, `Metrica_PitchControl.py` — https://github.com/Friends-of-Tracking-Data-FoTD/LaurieOnTracking/blob/master/Metrica_PitchControl.py — accessed 20 Oct 2026
- Power, Ruiz, Wei, Lucey, "Not All Passes Are Created Equal" (KDD 2017), DBLP entry — https://dblp.uni-trier.de/pid/01/10829.html — accessed 20 Oct 2026 (ACM page https://dl.acm.org/doi/10.1145/3097983.3098051 returned 403)
- Hudl StatsBomb, "xPass 360: upgrading expected pass models" — https://www.hudl.com/blog/xpass-360-upgrading-expected-pass-xpass-models — accessed 20 Oct 2026
- Hudl StatsBomb, "StatsBomb models: expected pass (xPass) and pass clustering" — https://www.hudl.com/blog/statsbomb-models-expected-pass-xpass-and-pass-clustering — accessed 20 Oct 2026
- The Analyst (Opta / Stats Perform), "Expected pass completion explained" (seen via search snippet only) — https://theanalyst.com/articles/expected-pass-completion-explained — accessed 20 Oct 2026
- AWS ML Blog, "The development of Bundesliga Match Fact Passing Profile" — https://aws.amazon.com/blogs/machine-learning/the-development-of-bundesliga-match-fact-passing-profile-a-deep-dive-into-passing-in-football — accessed 20 Oct 2026
- Bundesliga.com, Match Facts Shot Efficiency and Passing Profile (German; seen via search snippet only) — https://www.bundesliga.com/de/bundesliga/news/match-facts-dfl-aws-abschluss-effizienz-pass-profil-analyse-echtzeit-statistik-17236 — accessed 20 Oct 2026
- Soccermatics, Pass probability lesson — https://soccermatics.readthedocs.io/en/latest/lesson6/PassProbability.html — accessed 20 Oct 2026
