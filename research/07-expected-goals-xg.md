# 07 — Expected goals (xG): how it's calculated and an implementable model

_Accessed/compiled: 20 Oct 2026 · Priority area: football domain (Interpret + Explain stages)_

## TL;DR

- **What xG is:** the probability (0 to 1) that a shot becomes a goal, learned from many past shots that looked like it. The core inputs everywhere are **distance**, **angle to goal**, **body part**, **assist type / previous action**, and **situation** (open play, set piece, fast break). The best models also use **goalkeeper and defender positions** taken from a snapshot at the moment of the shot (StatsBomb "freeze frames"). Penalties get a **fixed value**: Opta uses **0.79** and Hudl StatsBomb **0.78**. Every penalty in the StatsBomb open data we checked carries 0.783.
- **A logistic regression on distance and angle** (the soccermatics tutorial) is the standard starter model. Its published coefficients are below. We wrote a plain-NumPy version and fitted it.
- **For our synthetic world, use option (a):** we define our own xG function and draw each shot's outcome from it. Then sum of xG ≈ goals is true by construction, and the reasons behind every number are known exactly. Fit on real StatsBomb open data only offline, as a sanity check. Its licence forbids commercial use, and it contains Premier League seasons, which the hackathon bans.
- **Explainability comes free with a logistic model.** Each feature's push on the log-odds is coefficient × (value − typical value). That is exactly linear SHAP. These pushes turn into a sentence like "xG 0.20 because only 9 m out, a wide view of goal, but under pressure."
- **Related metrics:** xGOT / post-shot xG (adds where the shot was placed), xA (how likely a pass is to become an assist), and possession-value models (xT, VAEP) for non-shot actions. Broadcasters show xG per chance, as a match total, and as a "momentum" graphic (Amazon Prime Vision, 2025).

## Findings

### Definition and features (primary explainers)

| Source | Definition / model | Features named | Penalty |
|---|---|---|---|
| Opta / Stats Perform (The Analyst, Aug 2023) | "measures the quality of a chance". XGBoost model, "over 20 variables", trained on "nearly one million shots" from 40 competitions, 2018-19 to 2021-22 | distance and angle; GK position; how clearly the shooter can see goal; defender pressure; shot type (foot, header, volley, one-on-one); pattern of play (open play, fast break, set piece); assist type | **0.79**, a fixed constant equal to the historical conversion rate |
| Hudl StatsBomb (xG explained) | probability of a shot resulting in a goal | distance, angle, body part, assist or previous action; **plus** GK position and status, attacker and defender positions in the freeze frame, shot impact height | "most models" use 0.76. The 2022 Hudl StatsBomb update moved it to **0.78** |
| Hudl StatsBomb (Upgrading xG, May 2022) | the existing model counts blockers in the shooter–posts triangle and the share of the goal face that defenders block | new version: each defender is a 2D Gaussian "blocking surface", so blocking is continuous; models with and without the GK show how much keeper positioning lowers xG | — |

Hudl's explainer shows why the freeze frame matters. A model that only knows distance, angle, body part and assist might value a chance at 0.30. Hudl StatsBomb values the same chance at **0.65** because it knows the goalkeeper was out of position.

**Our check on the data:** across 44 FIFA World Cup 2022 matches in StatsBomb open data, all 17 non-shootout penalties have `statsbomb_xg = 0.783`. Across the 1,001 non-penalty shots, mean StatsBomb xG is **0.098** per shot and the goal rate is **11.6%** (116 goals). This is our own computation on a small sample. Use it only as a rough sanity range.

**Goal-mouth angle.** This is the angle at the shooter between the lines to the two posts. Put the goal line at x = 0, take X as the distance from the goal line and C as the distance from the centre line, and let w = 7.32 m be the goal width. Then

`angle = arctan( w·X / (X² + C² − (w/2)²) )`, adding π if the result is negative.

That is the soccermatics formula. Using `atan2` to the near post and the far post and taking the difference gives the same value with no special case (see code). Distance is `sqrt(X² + C²)` to the goal centre.

**Gradient-boosted model with tracking data (paper):** Anzer & Bauer (2021) trained on 105,627 Bundesliga shots using synchronised positional and event data. Their best model was gradient boosting (XGBoost).

### Simple logistic xG (soccermatics, David Sumpter)

Lesson 2 of the soccermatics course fits `Goal ~ Angle` and similar formulas with a statsmodels Binomial GLM. The data is Wyscout events for the 2017/18 Premier League, converted to a 105×68 pitch, with penalties excluded (n = 8,451 shots). Predicted xG = `1/(1+exp(-(b0 + b1·x)))`. Coefficients as printed on the page (angle in radians, distance in metres):

| Model | Intercept | Angle | Distance | Distance² | Log-likelihood |
|---|---|---|---|---|---|
| Angle only | −3.5248 | 2.8436 | — | — | −2561.2 |
| Distance only | 0.1555 | — | −0.1496 | — | −2524.4 |
| Distance + D² | 0.8705 | — | −0.2591 | 0.0034 | −2505.6 |

The page also fits a 7-variable model, which reaches McFadden R² ≈ 0.137. The Friends of Tracking repo `SoccermaticsForPython` has the matching scripts (`3xGModel.py`, `5xGModelFit.py`).

**Our own fit (reproducible, research use only).** We ran a NumPy logistic regression on the same 44 WC2022 matches (1,001 non-penalty shots, coordinates scaled to 105×68):
- Distance + angle: intercept −1.359, angle +1.233, distance −0.103. Brier score 0.090, against 0.081 for StatsBomb's own xG on the same shots.
- Adding header (−1.04), under_pressure (−0.55) and defenders in the shooter–posts triangle (−0.38 each) lowers the Brier score to 0.085. Correlation with StatsBomb xG rises to 0.86.

The sample is small. Use these values to check that a model has the right signs and size, not as a model to ship.

**Sanity checklist for any xG model we build:** penalty ≈ 0.78–0.79; mean non-penalty xG per shot ≈ 0.10 (our WC2022 check: 0.098); sum of xG within a few percent of goals over many shots; xG falls as distance grows and rises as the angle opens; headers below foot shots from the same spot.

### Using xG in a synthetic world: three options

**(a) Analytic xG plus sampled outcomes (recommended core).** We choose coefficients for a logistic function. The geometry terms follow the shape of the published fits. Header, pressure, defenders and fast break are our own design choices, and we tune them until the sanity checklist passes. Each synthetic shot's goal flag is drawn as `rng.random() < xg`. The simulator then agrees with its own xG by construction. In our test on 50,000 synthetic shots, sum of xG was 5,680 against 5,625 goals, and refitting recovered the coefficients we put in (code below). This gives the fact-checker a ground truth: "true xG" is known for every shot.

**(b) Fit on StatsBomb open data offline.** This is technically easy, and gives sensible numbers (above). The licence is a real risk:
- The StatsBomb Public Data User Agreement (updated 8 Sep 2023) says the user may not "commercially exploit the data or any analysis derived from the use of the Service" (1.2.2). It also bans passing the data to third parties (1.2.1) and requires the StatsBomb logo on any publication (1.4). The data is "aimed to be a research tool".
- The open data also includes **Premier League 2015/16 and 2003/04**, and the hackathon bans real PL data.

A prize-bearing hackathon entry may count as commercial (unverified, so check the hackathon terms). If we use (b) at all: exclude PL competitions, keep it offline, don't ship any data, credit StatsBomb, and ideally replace the fitted numbers with our own hand-set ones in (a). The soccermatics coefficients come from a publicly taught tutorial. They are a lower-risk seed, but they were fitted on 2017/18 PL Wyscout data. The Wyscout dataset's licence is unverified (one catalogue lists it as "non-commercial only").

**(c) Explainable xG.** For a logistic model, each feature's contribution in log-odds is `w_i·(x_i − E[x_i])`. This is the "Linear SHAP" result in Lundberg & Lee (2017), so no SHAP library is needed. For a gradient-boosted model, use `shap.TreeExplainer`. Research on this:
- Cavus, Stando & Biecek (2023) aggregate SHAP values for xG per player and per team ("glocal" explanations).
- Rahimian, Flisar & Sumpter (2025) turn logistic-regression xG contributions into sentences, then have an LLM rewrite them. They call these "wordalizations".

That second paper is almost exactly our Explain stage.

### Related metrics (brief)

- **xGOT / post-shot xG:** Opta xGOT covers on-target shots only and rewards placement. One Sterling free kick was 0.1 xG but 0.81 xGOT. Hudl StatsBomb post-shot xG uses shot placement and GK position, and since 2022 shot velocity. Used for keeper "goals prevented" and finishing skill.
- **xA (Opta):** the likelihood that a pass becomes an assist. Logistic regression on pass type, pattern of play, start and end location, and distance. It is given to every completed pass, whether or not a shot follows.
- **Non-shot value:** xT (Karun Singh) values pitch zones on a 16×12 grid by the chance of scoring within the next few actions. VAEP (KU Leuven) values every action, including defensive ones. See file on xT, queued.

### How xG appears on broadcasts

- BBC *Match of the Day* began showing xG in 2017. StatsBomb's 10 Aug 2017 post welcomed it and warned against over-reading single-shot values. Opta says xG is now a regular feature on Sky Sports and Match of the Day. An Opta article shows a Sky xG graphic on a single chance (date of first use unverified).
- Amazon Prime Video's **Prime Vision** alternate feed (UEFA Champions League, launched 16 Sep 2025, UK first) shows xG, shot speed and a **momentum bar** driven by statistical models. Reports disagree on the bar's time window: "next 10 seconds" or "last five minutes" (unverified).
- Common formats: a per-chance xG lower-third, team xG totals beside the score, and a cumulative xG "flow" line that steps up at each shot (common practice; no single source).

## So what for us

- **Interpret + Explain (all ideas; core to A TwinCast, C One Number, 21 Called It, 05 Set-Piece X-Ray, 09 Keeper Brain):**
  - Ship option (a). The simulator calls `xg(shot)` and `sample_outcome()`, and stores `true_xg` with each shot event.
  - The Interpret agent recomputes xG from the event fields. The fact-checker asserts that the recomputed xG matches the stored value, and that sum of xG ≈ goals over the match. This gives our cue a `truth_check` that is mathematically true, not LLM-asserted.
- **Explain:** use `explain()` to build each cue's `text` per audience:
  - Analyst: numbers plus the log-odds contributions.
  - Casual: the sentence only.
  - Kids (10 Story Time): "a hard chance, like scoring from the corner of the box".
  
  Put the contribution dict in the cue's evidence so an LLM rewrite cannot invent reasons. This is the "wordalization" pattern.
- **Render:** a cumulative xG flow line, plus a per-shot xG lower-third with a ttl of about 6 s, fits the cue JSON. A "momentum" bar can be xG summed over a rolling 5-minute window. Label it as such, since Amazon's own definition is unclear.
- **E Realism Bench:** report our synthetic mean xG per shot, penalty share and xG-to-goals calibration against the sanity ranges above.
- **Rule hygiene:** do not bundle StatsBomb data or a model fitted on it. If we mention it, say "coefficients hand-set; magnitudes sanity-checked against public literature".

## Reuse: code & links

Tested with Python 3.12 + NumPy. Pitch is 105×68 and the team attacks toward x = 105.

```python
import math, numpy as np
PITCH_L, PITCH_W, GOAL_W = 105.0, 68.0, 7.32
GOAL_X, GOAL_Y = PITCH_L, PITCH_W / 2

def shot_geometry(x, y):
    """Distance (m) to goal centre and goal-mouth angle (rad) from (x, y)."""
    dx = GOAL_X - x
    dist = math.hypot(dx, GOAL_Y - y)
    angle = abs(math.atan2(GOAL_Y + GOAL_W/2 - y, dx) - math.atan2(GOAL_Y - GOAL_W/2 - y, dx))
    return dist, angle          # equals soccermatics arctan formula (with +pi fix)

# Synthetic-world "true" model in log-odds. Hand-set design values (not a published fit);
# magnitudes sanity-checked against soccermatics and our offline WC2022 check.
COEF = {"intercept": -1.0, "angle": 1.6, "distance": -0.10, "header": -1.0,
        "under_pressure": -0.4, "defenders_in_cone": -0.3, "fast_break": 0.4}
REF  = {"angle": 0.35, "distance": 17.0, "header": 0, "under_pressure": 0,
        "defenders_in_cone": 1, "fast_break": 0}        # "typical shot" baseline
PENALTY_XG = 0.78                                        # Hudl StatsBomb; Opta 0.79

def features(s):
    d, a = shot_geometry(s["x"], s["y"])
    return {"angle": a, "distance": d, "header": float(s.get("body_part") == "head"),
            "under_pressure": float(s.get("under_pressure", False)),
            "defenders_in_cone": float(s.get("defenders_in_cone", 0)),
            "fast_break": float(s.get("situation") == "fast_break")}

def xg(s, coef=COEF):
    if s.get("situation") == "penalty":
        return PENALTY_XG
    z = coef["intercept"] + sum(coef[k] * v for k, v in features(s).items())
    return 1 / (1 + math.exp(-z))

def sample_outcome(s, rng):               # consistent by construction
    p = xg(s)
    return {"xg": round(p, 3), "goal": bool(rng.random() < p)}

def contributions(s, coef=COEF, ref=REF):  # = linear SHAP in log-odds, baseline REF
    f = features(s)
    return {k: coef[k] * (f[k] - ref[k]) for k in f}

PHRASES = {"distance": ("only {d:.0f} m out", "{d:.0f} m out"),
           "angle": ("a wide view of goal", "a tight angle"),
           "header": ("", "a header"), "under_pressure": ("", "under pressure"),
           "defenders_in_cone": ("a clear sight of goal", "{n:.0f} defender(s) in the way"),
           "fast_break": ("on the counter", "")}

def explain(s, top=3):
    if s.get("situation") == "penalty":
        return f"xG {PENALTY_XG:.2f}: a penalty, valued at its usual conversion rate."
    f, c = features(s), contributions(s)
    ranked = sorted(((k, v) for k, v in c.items() if abs(v) > 0.05), key=lambda kv: -abs(kv[1]))[:top]
    fmt = lambda t: t.format(d=f["distance"], n=f["defenders_in_cone"])
    plus = [fmt(PHRASES[k][0]) for k, v in ranked if v > 0 and PHRASES[k][0]]
    minus = [fmt(PHRASES[k][1]) for k, v in ranked if v < 0 and PHRASES[k][1]]
    out = f"xG {xg(s):.2f}"
    if plus:  out += " because " + ", ".join(plus)
    if minus: out += (", but " if plus else " because ") + ", ".join(minus)
    return out + "."

def fit_logistic(X, y, iters=30):          # NumPy Newton/IRLS; returns [b0, w1, ...]
    X = np.column_stack([np.ones(len(X)), X]); b = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-X @ b))
        b += np.linalg.solve(X.T @ (X * (p * (1 - p))[:, None]), X.T @ (y - p))
    return b

rng = np.random.default_rng(7)
shot = {"x": 96.0, "y": 34.5, "under_pressure": True, "defenders_in_cone": 1}
print(sample_outcome(shot, rng))   # {'xg': 0.203, 'goal': False}
print(explain(shot))               # xG 0.20 because only 9 m out, a wide view of goal, but under pressure.
print(explain({"x": 84, "y": 50, "defenders_in_cone": 0, "situation": "fast_break"}))
# xG 0.05 because on the counter, a clear sight of goal, but 26 m out.
```

**Consistency test we ran:**
- Setup: 50,000 synthetic shots, with x = 105 − |N(0,10)| − 5, y ~ N(34, 9), 15% headers, 40% under pressure, and defenders ~ Poisson(1).
- Result: mean xG 0.114, goal rate 0.113, sum of xG 5,680 vs 5,625 goals.
- Refitting gave `[-1.11, 1.69, -0.097, -1.09, -0.37, -0.29]`, close to the true `[-1.0, 1.6, -0.10, -1.0, -0.4, -0.3]`.

Links:
- soccermatics xG fit lesson (code + coefficients): https://soccermatics.readthedocs.io/en/latest/gallery/lesson2/plot_xGModelFit.html
- Friends of Tracking `SoccermaticsForPython` (`3xGModel.py`, `5xGModelFit.py`): https://github.com/Friends-of-Tracking-Data-FoTD/SoccermaticsForPython
- StatsBomb open data (read LICENSE.pdf first): https://github.com/statsbomb/open-data
- socceraction xT/VAEP implementations: https://socceraction.readthedocs.io/en/latest/documentation/valuing_actions/xT.html

## Sources

- What Is Expected Goals (xG)? (Opta Analyst, Aug 2023) — https://theanalyst.com/2023/08/what-is-expected-goals-xg — accessed 20 Oct 2026
- What Are Expected Goals on Target (xGOT)? (Opta Analyst) — https://theanalyst.com/2021/06/what-are-expected-goals-on-target-xgot — accessed 20 Oct 2026
- What Are Expected Assists (xA)? (Opta Analyst, 24 Mar 2021) — https://theanalyst.com/2021/03/what-are-expected-assists-xa — accessed 20 Oct 2026
- What are Expected Goals (xG)? (Opta Analyst, 2021; mentions Sky/MOTD) — https://theanalyst.com/eu/2021/06/what-are-expected-goals-xg/ — accessed 20 Oct 2026
- Expected Goals (xG) explained (Hudl StatsBomb) — https://www.hudl.com/blog/expected-goals-xg-explained — accessed 20 Oct 2026
- Upgrading Expected Goals (Hudl StatsBomb, 16 May 2022) — https://www.hudl.com/blog/upgrading-expected-goals — accessed 20 Oct 2026
- StatsBomb open data repo and Public Data User Agreement (updated 8 Sep 2023) — https://github.com/statsbomb/open-data , https://github.com/hudl/open-data/blob/master/LICENSE.pdf — accessed 20 Oct 2026
- soccermatics, "Fitting the xG model" (D. Sumpter) — https://soccermatics.readthedocs.io/en/latest/gallery/lesson2/plot_xGModelFit.html — accessed 20 Oct 2026
- Friends of Tracking, SoccermaticsForPython — https://github.com/Friends-of-Tracking-Data-FoTD/SoccermaticsForPython — accessed 20 Oct 2026
- Anzer & Bauer, A Goal Scoring Probability Model for Shots Based on Synchronized Positional and Event Data (Frontiers, 2021) — https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8056301/ — accessed 20 Oct 2026
- Lundberg & Lee, A Unified Approach to Interpreting Model Predictions (SHAP, 2017) — https://arxiv.org/abs/1705.07874 — accessed 20 Oct 2026
- Cavus, Stando & Biecek, Glocal Explanations of Expected Goal Models in Soccer (2023) — https://arxiv.org/abs/2308.15559 — accessed 20 Oct 2026
- Rahimian, Flisar & Sumpter, Automated Explanation of Machine Learning Models of Footballing Actions in Words (2025) — https://arxiv.org/abs/2504.00767 — accessed 20 Oct 2026
- Karun Singh, Introducing Expected Threat (xT) — https://karun.in/blog/expected-threat.html — accessed 20 Oct 2026
- KU Leuven DTAI, Valuing On-the-Ball Actions: A Critical Comparison of xT and VAEP — https://dtai.cs.kuleuven.be/sports/blog/valuing-on-the-ball-actions-in-soccer-a-critical-comparison-of-xt-and-vaep — accessed 20 Oct 2026
- StatsBomb, xG is on TV. Now What? (10 Aug 2017) — https://blogarchive.statsbomb.com/articles/soccer/xg-is-on-tv-now-what/ — accessed 20 Oct 2026
- The Conversation, A brief history of statistics in football — https://theconversation.com/a-brief-history-of-statistics-in-football-why-actual-goals-remain-king-in-predicting-who-will-win-194314 — accessed 20 Oct 2026
- SVG Europe, Amazon launches Prime Vision for Champions League coverage (16 Sep 2025) — https://www.svgeurope.org/blog/headlines/amazon-launches-prime-vision-for-champions-league-coverage/ — accessed 20 Oct 2026
- Broadcast, Prime Video adds layers of graphical insights for Champions League — https://www.broadcastnow.co.uk/broadcasting/prime-video-adds-layers-of-graphical-insights-for-champions-league/5208911.article — accessed 20 Oct 2026 (seen via search excerpt only; unverified)
- Pappalardo et al., Soccer match event dataset (Wyscout, figshare; licence unverified) — https://figshare.com/collections/_/4415000 — accessed 20 Oct 2026
