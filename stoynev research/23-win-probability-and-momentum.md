# 23 — Live win probability, possession value and momentum (implementable on synthetic data)

_Accessed/compiled: 20 Oct 2026 · Priority area: Interpret + Render stages (live probability, momentum bar, prediction scoring) for 21 Called It, C One Number, F Graphics Desk, 17 Heartbeat, 13 Recap Dial_

## TL;DR

- **The standard explainable live model is "remaining-time Poisson".** For each team, remaining goals ~ Poisson(rate × minutes left). Add the current score and read off P(home/draw/away) from a goal grid or from the closed-form Skellam. Robberechts, Van Haaren & Davis (KDD 2021) use exactly this structure. They model independent Poisson goals in the remaining time, with Bayesian, time-varying feature weights. Their ECE in the last 10% of the match is 0.002, against 0.10-0.17 for baselines borrowed from other sports.
- **Opta's live model simulates the rest of the match "thousands of times".** Its inputs are 4-year team quality, 1-year form, home advantage, live chance quality, red cards, score and time left, including estimated added time. Bundesliga/AWS Win Probability uses goal margin, time left, xG, Skill and Set Piece Threat. It is shown only on big swings after goals, red cards or substitutions. Neither provider publishes formulas.
- **Our implementable version (run below on 3,000 synthetic matches).** Per-minute rates are Gamma-Poisson shrinkage of pre-match strength toward live xG, plus red-card factors (10 men ×2/3, opponent ×5/4, from Vecer et al. 2009) and a score-state "chase" term, then a Poisson grid. Reliability is close to diagonal: home-win ECE 0.006, multiclass ECE 0.008, RPS 0.140. The prior weight matters. Weighting live xG too early (k = 30 min) made Brier *worse* than ignoring xG, so tune k on the generator.
- **Momentum = rolling, recency-weighted possession value per team, home minus away.** Bundesliga computes it every minute over the last 5 minutes, scales each team to 0-10 and resets each half. Feed it xT/PV for *every* action, not just shots. A shot-only feed is spiky and mostly zero, as our toy run shows.
- **For 21 Called It, score each timestamped call with Brier (plus a Brier skill score against a base rate), log loss and RPS for 1X2.** Add a reliability diagram plus ECE once there are 50+ calls. All of these functions are below, roughly 60 lines of NumPy.

## Findings

### 1. Published live win-probability models

| Model | Structure | Inputs | Evaluation / numbers |
|---|---|---|---|
| Robberechts, Van Haaren, Davis, KDD 2021 | The game is split into T = 100 frames (half-time = 50). `y_>t,home ~ Pois((T−t)·θ_t,home)`, `θ_t,home = invlogit(α_t·x_t,home + β + Ha)`. Weights follow a random walk, `α_t ~ N(α_{t−1}, 2)`. Goals are treated as independent (the small correlation is ignored). Fitted with PyMC3 ADVI. | Time, score difference, Elo difference, goals so far, red-card difference, opponent yellows, chances, rolling attacking passes, rolling **xT**, rolling duel success. **No xG.** Stoppage time comes from a separate random forest (MAE 46 s first half, 59 s second half). | 12,758 training and 1,826 test games, top-5 leagues. RPS 0.134 offline and 0.138 for the simplified real-time model. ECE (5 bins) 0.011 overall and **0.002 in the final 10%**, against LR 0.174 and RF 0.101. Baselines from other sports fail on the draw: RF "never predicts a high probability of a tie". |
| Opta / The Analyst LWP | Monte Carlo simulation of the remaining match, "thousands of times", from time-varying scoring likelihoods | Team quality (4 yrs), form (1 yr), home advantage, live chance quality for and against, red cards, score, time left including added time | No accuracy published. Examples: Burnley 17 / draw 26 / Man City 57 at 7'. Palace 38%→59% after a City red card. Used by Amazon Prime Video and Canal+. |
| Bundesliga Match Facts (DFL + AWS), since 2022-23 | Not published | Goal margin, time left, live xG, Skill, Set Piece Threat, previous-game stats | Graphic shown only on "significant change" after goals, sending-offs or substitutions |
| Dixon & Coles 1997 (pre-match) | Independent Poisson with a correction τ on low scores: 0-0 ×(1−λμρ), 0-1 ×(1+λρ), 1-0 ×(1+μρ), 1-1 ×(1−ρ) | Team attack and defence, home advantage | Basis of `penaltyblog`. Sources disagree on whether 1-1 is adjusted. Use our pre-match λ from the generator. |

**Red cards.** Vecer, Kopriva & Ichiba (2009) inferred scoring rates from live betting odds at WC 2006 and Euro 2008. As quoted by Greenberg (2015), the 10-man team's rate falls "to about 2/3 of the original intensity" and the opponent's rises "by a factor of about 5/4". An older Dutch study (Ridder et al. 1994, cited in Červený et al. 2016) found the 11-man side's rate rose 88% and the 10-man side's was unchanged. The effects are real but the size depends on the study. Use 2/3 and 5/4 as defaults and print them as assumptions.

### 2. Formulas for our live model

Let `m` be the current minute, `M` the expected end (90 + added time, taken from generator metadata), `λ_H, λ_A` the pre-match expected goals, and `xG_H, xG_A` the live xG so far.

1. **Live rate (Gamma-Poisson shrinkage).** Treat the pre-match rate as `k` minutes of pseudo-play: `r_H = (λ_H/90·k + xG_H) / (k + m)`. Using xG as pseudo-goals is an approximation, but it has lower variance than actual goals.
2. **Red cards.** If home has `d` more reds than away, `r_H ×= (2/3)^d` and `r_A ×= (5/4)^d`.
3. **Score state (our assumption, not from a fetched source).** The trailing side's rate is ×(1+s) and the leader's ×(1−s), with s ≈ 0.1. Calibrate s on the generator.
4. **Remaining goals.** `μ_H = r_H·(M−m)` and `μ_A = r_A·(M−m)`, with `X ~ Pois(μ_H)` and `Y ~ Pois(μ_A)`.
5. **Outcome.** With current difference `D = g_H − g_A`:
   `P(home) = Σ_{x,y: D+x−y>0} Pois(x;μ_H)·Pois(y;μ_A)`, and similarly for draw (=0) and away (<0).
   In closed form, `X − Y ~ Skellam(μ_H, μ_A)`, so `P(draw) = Skellam.pmf(−D)`, `P(away) = Skellam.cdf(−D−1)` and `P(home) = 1 − both`. Our run shows the grid and Skellam versions agree to 3 decimals. The grid is needed only if you add a Dixon-Coles ρ.

Worked outputs (pre-match λ 1.5 v 1.1, M = 95, k = 90): 0-0 at 0' gives **47/25/28**. 1-0 at 60' with xG 0.9-0.7 gives **75/20/5**, and **66/26/9** if home has a red card. 0-0 at 80' with xG 0.4-1.6 gives **12/69/18**.

### 3. Toy validation on our own synthetic league

We simulated 3,000 matches. The generator has hidden per-match form (rate × lognormal noise, sd 0.25), shots with Beta xG (mean 0.11), red cards and a 0.15 chase effect. We predicted at 0/15/30/45/60/75/85', giving 21,000 predictions.

| Model | Brier (3-class) | RPS | Log loss | ECE (mc, 5 bins) |
|---|---|---|---|---|
| Score + time + pre-match only (k = ∞) | 0.4439 | 0.1407 | 0.7556 | 0.0092 |
| + live xG (k = 90), reds, chase | **0.4426** | **0.1403** | **0.7539** | **0.0077** |

The prior sweep (separate seed) shows the size of k matters. With hidden-form sd 0.25, Brier was 0.4557 at k = 30, 0.4507 at k = 180 and 0.4521 with no xG. With sd 0.5, the best was 0.4352 at k = 30-90, against 0.4441 with no xG. **Live xG helps only as much as matches really deviate from pre-match strength, so k is a property of the generator.** These numbers are synthetic and not comparable to the paper's RPS. The model also matches the generator's assumptions closely (same red-card factors), so expect calibration to look better than it would on real data.

### 4. Possession value (OBV / PV / EPV / VAEP) in brief

| Model | Value of an action | Notes |
|---|---|---|
| xT (Singh) | `xT(end) − xT(start)` on a grid | Covered in file 08 |
| VAEP (Decroos et al., KDD 2019) | Δ P(score soon) − Δ P(concede soon), from two classifiers over game-state features | "Soon" = within the next 10 actions (from memory of the paper, unverified here). Implemented in `socceraction`. |
| OBV (Hudl StatsBomb, 2021) | Change in P(score) and P(concede) caused by the event | Two separate models (goals for and against), **trained on xG, not goals**, to cut variance. Features are location, distance and angle, set or open play, pressure and body part. **Possession history is deliberately excluded**, and receivers get no direct credit. |
| Stats Perform PV | Trained on goals, "time-based" | Per Hudl, does not model conceding |
| EPV (Fernández, Bornn, Cervone, *Machine Learning* 2021) | Expected outcome of the possession at each instant, split into pass, drive and shot sub-models | Tracking-based deep surfaces. Too heavy for us. |

**On synthetic data**, the cheapest honest option is OBV-style. Label every action with the xG of shots by the same team minus shots by the opponent within the next N actions or S seconds. Then fit a small model (a zone × action-type table, or logistic/GBM) on a few hundred generated matches. If the generator has an internal threat function, the ground-truth PV is simply that function. We can then *grade* a learned PV against it, which feeds E Realism Bench.

### 5. Momentum

- **Bundesliga Match Momentum.** Every minute, using the last 5 minutes, each team gets a 0 ("no own offensive threat") to 10 score. The displayed value is the difference between the two, and both teams restart at zero each half. Inputs per bundesliga.com are goals, shots with xG/xSave, entries into the attacking zone, crosses, corners, box receptions, attacking-third free kicks, possession in the opponent's half and red cards. AWS's write-up adds that weights come from "extensive historical analysis" and that recent actions count more and decay. Indicators are normalised by season. It also defines "heat" as the sum of both threats (0-20). Weights are not published. File 11 has a simple weighted-count version.
- **Opta/Flashscore** sum a possession-value model per minute (see file 09).
- **Our version (code below):** per-minute sum of positive PV/xT added per team, a 5-minute window with linearly increasing weights, reset at 45', and scaling to 0-10 against the 98th percentile of reference synthetic matches, giving momentum from −10 to +10. Fed with shots only, our toy series is mostly 0 with spikes such as −2.8 and +6.3. Feed it all actions.

### 6. Calibration and the "Called It" scorecard

- **Brier (binary)** `= mean((p − o)²)`. Multiclass uses a sum over classes (range 0-2). **Brier skill score** `BSS = 1 − BS/BS_ref`, where the reference is the base rate or the pre-match model.
- **Log loss** punishes confident misses hard, which makes it good for exposing an overconfident model.
- **RPS** respects the H > D > A order (Constantinou & Fenton 2012). Wheatcroft (2019) argues against it, so report it alongside Brier rather than instead of it. `penaltyblog.metrics.rps_average` gives 0.15625 for [0.5, 0.25, 0.25] when the home team wins, which is a useful unit test.
- **Reliability diagram + ECE.** Bin predictions, then plot the mean prediction against the observed frequency. `ECE = Σ_b |B_b|/N · |ō_b − p̄_b|` (Guo et al. 2017, from Naeini et al. 2015). Diagrams hide bin counts, so add a count histogram. `sklearn.calibration.calibration_curve(y, p, n_bins=5, strategy='uniform'|'quantile')` drops empty bins. With few calls, use quantile bins and 5 bins.
- **Scorecard per call.** Store `call_id, match_clock, tc_issued, claim, p, horizon, resolved_at, outcome`, and score only after resolution. Each call is locked at issue (hash it, see 18 Signed Recap). Report Brier, BSS, log loss, hit rate at 0.5, and *sharpness* (mean |p − 0.5|). A model that always says 50% is calibrated but useless. On a toy set of 6 calls: Brier 0.157 against a base-rate 0.250, so BSS = 0.37.

### 7. Broadcast presentation

- **Win probability** is a three-segment bar (H/D/A) or a line chart over time. Show it **on swings**: Bundesliga after goals, reds and substitutions, and Opta notes jumps after goals, reds, penalties and unexpected added time. File 11 proposes ≥10 pp at stoppages for 5-6 s. Persistent display belongs on an alt or analyst feed.
- **Momentum** goes full-screen at half-time and full-time, and live on a full reversal or after a key event (Bundesliga). Mirrored per-minute bars in team colours (Opta/Flashscore).
- **Swing graphic.** "Win chance 38% → 59% (red card)" is the format Opta uses in prose. Pair it with the one driver behind the change, from our model terms: score change, red factor, or xG update.

## So what for us

- **Interpret + Render, 21 Called It.** The live model gives Called It calibrated, explainable probabilities. Every number decomposes into "pre-match strength + live xG + red card + time left". The scorecard shows our predictions **graded against the generator's ground truth**: a reliability diagram over 1,000+ seeded matches is a strong slide for a "trustworthy AI" judging angle.
- **C One Number / F Graphics Desk.** Use a `prob` cue with `trigger: threshold` when |ΔP(home)| ≥ 0.10 or the favourite changes, and a `bar` cue for momentum. Put the driver text (one sentence) in the cue's `text` per audience. The analyst view also shows μ_H, μ_A and k.
- **A TwinCast / E Realism Bench.** Compare WP calibration when the inputs are ground-truth events versus CV-detected events. The difference in ECE and Brier measures how much CV errors hurt downstream insight.
- **Recommendation.** Ship the Poisson grid + Skellam model with k tuned on 500 generated matches (k is the only parameter we must fit; reds and chase are printed assumptions). Use `penaltyblog` only for the pre-match Dixon-Coles λ (MIT licence), and do not fit it on any real PL data.

## Reuse: code & links

The code was tested: Python 3.12, NumPy 2.4, SciPy 1.17, matplotlib 3.10, 3,000 matches in about 10 s.

```python
import numpy as np
from scipy.stats import poisson, skellam
RED_SELF, RED_OPP = 2/3, 5/4          # Vecer et al. 2009 (via Greenberg 2015)

def live_rates(minute, lam_h, lam_a, xg_h=0., xg_a=0., prior_minutes=90.,
               reds_h=0, reds_a=0, goal_diff=0, chase=0.10):
    k = prior_minutes                                   # Gamma-Poisson shrinkage
    r_h = (lam_h/90*k + xg_h) / (k + minute); r_a = (lam_a/90*k + xg_a) / (k + minute)
    d = reds_h - reds_a
    if d > 0: r_h *= RED_SELF**d;  r_a *= RED_OPP**d
    if d < 0: r_a *= RED_SELF**-d; r_h *= RED_OPP**-d
    s = np.sign(goal_diff) * chase; r_h *= 1 - s; r_a *= 1 + s   # our assumption
    return r_h, r_a

def win_prob(g_h, g_a, minute, r_h, r_a, total_minutes=95, max_goals=10, rho=0.0):
    t = max(total_minutes - minute, 0.); mu_h, mu_a = r_h*t, r_a*t
    k = np.arange(max_goals + 1)
    G = np.outer(poisson.pmf(k, mu_h), poisson.pmf(k, mu_a))
    if rho:  # Dixon-Coles low-score correction
        G[0,0] *= 1-mu_h*mu_a*rho; G[0,1] *= 1+mu_h*rho; G[1,0] *= 1+mu_a*rho; G[1,1] *= 1-rho
    G /= G.sum(); D = (g_h - g_a) + k[:, None] - k[None, :]
    return G[D > 0].sum(), G[D == 0].sum(), G[D < 0].sum()

def win_prob_skellam(g_h, g_a, minute, r_h, r_a, total_minutes=95):
    t = max(total_minutes - minute, 1e-9); mu_h, mu_a, d = r_h*t, r_a*t, g_h - g_a
    p_d = skellam.pmf(-d, mu_h, mu_a); p_a = skellam.cdf(-d-1, mu_h, mu_a)
    return 1 - p_d - p_a, p_d, p_a
```

```python
def momentum_series(events, n_minutes=95, window=5, half_break=45, scale=10., ref=None):
    """events: (minute, 'H'|'A', value) with value = PV/xT added or xG. Returns home, away, home-away."""
    h, a = np.zeros(n_minutes), np.zeros(n_minutes)
    for m, team, v in events:
        if 0 <= m < n_minutes: (h if team == 'H' else a)[int(m)] += max(v, 0.)
    w = np.arange(1, window + 1, dtype=float); w /= w.sum()      # recent minutes weigh more
    def roll(x):
        out = np.zeros_like(x)
        for t in range(len(x)):
            seg = x[max(half_break if t >= half_break else 0, t - window + 1): t + 1]
            out[t] = (seg * w[-len(seg):]).sum()
        return out
    th, ta = roll(h), roll(a)
    ref = ref or np.percentile(np.r_[th, ta], 98) or 1.   # pass ref from reference matches in prod
    th, ta = np.clip(th/ref*scale, 0, scale), np.clip(ta/ref*scale, 0, scale)
    return th, ta, th - ta
```

```python
def brier_multi(P, y):   # P (n,3) [H,D,A], y in {0,1,2}
    P = np.asarray(P, float); Y = np.eye(P.shape[1])[np.asarray(y)]
    return float(np.mean(((P - Y)**2).sum(1)))
def brier_binary(p, o): return float(np.mean((np.asarray(p, float) - np.asarray(o, float))**2))
def log_loss(P, y, eps=1e-12):
    P = np.clip(np.asarray(P, float), eps, 1); return float(-np.mean(np.log(P[np.arange(len(P)), y])))
def rps(P, y):
    P = np.asarray(P, float); Y = np.eye(P.shape[1])[np.asarray(y)]
    return float(np.mean(((np.cumsum(P,1)[:, :-1] - np.cumsum(Y,1)[:, :-1])**2).sum(1) / (P.shape[1]-1)))
def ece_binary(p, o, n_bins=10):
    p, o = np.asarray(p, float), np.asarray(o, float); idx = np.minimum((p*n_bins).astype(int), n_bins-1)
    return float(sum((idx == b).mean() * abs(o[idx == b].mean() - p[idx == b].mean())
                     for b in range(n_bins) if (idx == b).any()))
def ece_multiclass(P, y, n_bins=5):
    P = np.asarray(P, float); Y = np.eye(P.shape[1])[np.asarray(y)]
    return float(np.mean([ece_binary(P[:, c], Y[:, c], n_bins) for c in range(P.shape[1])]))
```

```python
import matplotlib.pyplot as plt
def plot_reliability(p, o, n_bins=10, ax=None, label="model"):
    p, o = np.asarray(p, float), np.asarray(o, float)
    edges = np.linspace(0, 1, n_bins + 1); idx = np.minimum(np.digitize(p, edges) - 1, n_bins - 1)
    bins = [b for b in range(n_bins) if (idx == b).any()]
    ax = ax or plt.gca(); ax.plot([0, 1], [0, 1], "--", c="grey", lw=1, label="perfect")
    ax.plot([p[idx == b].mean() for b in bins], [o[idx == b].mean() for b in bins], "o-",
            label=f"{label} (ECE {ece_binary(p, o, n_bins):.3f})")
    ax2 = ax.twinx(); ax2.bar(edges[:-1] + .5/n_bins, np.bincount(idx, minlength=n_bins),
                              width=.9/n_bins, alpha=.15, color="grey"); ax2.set_yticks([])
    ax.set(xlim=(0, 1), ylim=(0, 1), xlabel="predicted probability", ylabel="observed frequency")
    ax.legend(loc="upper left"); return ax
# usage: plot_reliability(P[:, 0], y == 0, label="P(home win)"); plt.savefig("reliability.png")
```

**Pre-match λ with penaltyblog (MIT):** `from penaltyblog.models import create_dixon_coles_grid; g = create_dixon_coles_grid(home_lambda=1.5, away_lambda=1.2, rho=0.01); g.home_draw_away`. A fitted model's `.predict(home, away)` returns a `FootballProbabilityGrid` with `.home_win/.draw/.away_win/.grid`, and `pb.metrics.rps_average(preds, observed)`.

Links: `penaltyblog` https://github.com/martineastwood/penaltyblog · `socceraction` (VAEP, xT) https://github.com/ML-KULeuven/socceraction · Robberechts paper HTML https://arxiv.org/html/1906.05029v2

## Sources

- Robberechts, Van Haaren, Davis, "A Bayesian Approach to In-Game Win Probability in Soccer" (KDD 2021) — https://arxiv.org/html/1906.05029v2 — accessed 20 Oct 2026
- The Analyst, "Live Win Probability" — https://theanalyst.com/articles/live-win-probability — accessed 20 Oct 2026
- Bundesliga, "Pressure Handling and Win Probability join Bundesliga Match Facts powered by AWS" — https://bundesliga.com/en/bundesliga/news/pressure-handling-win-probability-join-bundesliga-match-facts-powered-by-aws-21390 — accessed 20 Oct 2026
- Bundesliga, "Match Momentum" (16th BMF) — https://www.bundesliga.com/en/bundesliga/news/bundesliga-match-facts-aws-match-momentum-34052 — accessed 20 Oct 2026
- AWS Media blog, "Bundesliga Match Fact Match Momentum: revealing the game's invisible pulse" — https://aws.amazon.com/blogs/media/bundesliga-match-fact-match-momentum-revealing-the-games-invisible-pulse — accessed 20 Oct 2026
- Hudl StatsBomb, "Introducing On-Ball Value (OBV)" — https://www.hudl.com/blog/introducing-on-ball-value-obv — accessed 20 Oct 2026
- Decroos et al., "Actions Speak Louder than Goals: Valuing Player Actions in Soccer" (KDD 2019) — https://arxiv.org/abs/1802.07127 — accessed 20 Oct 2026
- Fernández, Bornn, Cervone, "A framework for the fine-grained evaluation of the instantaneous expected value of soccer possessions" (Machine Learning 2021) — https://arxiv.org/abs/2011.09426 — accessed 20 Oct 2026
- Dixon & Coles 1997 (JRSS C 46(2):265-280), repository record — https://eprints.lancs.ac.uk/id/eprint/19492 — accessed 20 Oct 2026; τ restated in https://arxiv.org/pdf/2508.20075 — accessed 20 Oct 2026
- Greenberg, "The red card cliché", Significance (Aug 2015), quoting Vecer, Kopriva & Ichiba 2009 — https://www.nottingham.ac.uk/economics/documents/news/greenberg-2015-significance.pdf — accessed 20 Oct 2026
- Červený, van Ours, van Tuijl, "Effects of a Red Card on Goal-Scoring in World Cup Football Matches", IZA DP 10174 (2016) — https://docs.iza.org/dp10174.pdf — accessed 20 Oct 2026
- penaltyblog docs: FootballProbabilityGrid — https://penaltyblog.readthedocs.io/en/latest/models/football_prob_grid.html ; RPS — https://penaltyblog.readthedocs.io/en/latest/metrics/rps.html — accessed 20 Oct 2026
- Guo, Pleiss, Sun, Weinberger, "On Calibration of Modern Neural Networks" (ICML 2017) — https://arxiv.org/abs/1706.04599 — accessed 20 Oct 2026
- scikit-learn `calibration_curve` — https://scikit-learn.org/stable/modules/generated/sklearn.calibration.calibration_curve.html — accessed 20 Oct 2026
- Constantinou & Fenton (2012), JQAS 8(1) — https://ideas.repec.org/a/bpj/jqsprt/v8y2012i1n12.html ; Wheatcroft, "The case against the RPS" — https://arxiv.org/abs/1908.08980 — accessed 20 Oct 2026
