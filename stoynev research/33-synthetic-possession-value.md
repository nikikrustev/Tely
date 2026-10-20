# 33 — Synthetic possession value (xT + VAEP): the value layer for momentum, Ghost Team and Relay Credit

_Accessed/compiled: 20 Oct 2026 · Priority area: Interpret (value per action) → Explain; feeds file 23 momentum, 06 Relay Credit, 01 Ghost Team, 21 Called It, 22 explanations_

## TL;DR

- **The pipeline works end to end with no real data.** The steps are: file 02 generator (seeded) → CDF lines → file 26 CDF→SPADL converter → socceraction xT and VAEP (xgboost) → a value for every action. **Our run:** 200 matches, 218,180 actions, a 150/50 train/test split by match, **34 s total on one laptop CPU**. The xT fit takes 0.9 s, VAEP features 15 s, the xgboost fit 2 s, and rating takes 0.11 s per match. That means we can refit at deploy time and, if needed, live.
- **Our metrics (synthetic test matches, not comparable to real football).** VAEP *scores* beats the base rate: log loss 0.0649 vs 0.0755, Brier 0.0125 vs 0.0142 (**Brier skill 12%**), AUC 0.75, ECE 0.0025. VAEP *concedes* has the right ranking (AUC 0.73) but no Brier skill: 0.00202 vs 0.00202. The VAEP paper reports the same pattern on real data, with concedes models barely beating "no features". The xT grid is sane: it peaks in front of goal at 0.067, the column means rise in 15 of 15 steps, and the Spearman correlation of xT with x is 0.95.
- **We found two bugs in the file 02 generator that distort every value model.** (1) After a missed shot, the goal kick is placed at the *shooter's* end. That gives the opponent the ball 5.5 m from the goal it attacks, and it doubles goals to 3.18 per match. (2) Passes aimed off the pitch are clamped onto the goal line. Shots from that line get a toy xG of about 0.89 (the angle term becomes π). In the run with only the goal-kick fix, **47% of shots and 71% of goals came from the byline**. A two-line fix is given below. File 02's "≈3.2 goals per 90" came from bug 1.
- **Uses.** (1) **Momentum:** feed file 23's `momentum_series` with build-up VAEP plus shot xG. The goal outcome itself makes a spike, so leave it out. (2) **Relay Credit:** VAEP summed per player is exactly the Shapley value of the additive game. We verified this in code. It gives the scorer **94%** of positive credit on average, so show "chance creation" (build-up only) as a separate split. (3) **Ghost Team:** value above the average action from the same zone. In our generator, players have *no* skill, and half-to-half correlation is 0.02, so any "best player" story is noise until we give players latent skill. (4) **Called It:** P(score in next 10 actions ≈ 44 s) is well calibrated, which makes it a usable house baseline.
- **We explain value changes with xgboost TreeSHAP (`pred_contribs`), which takes 2.4 ms per action.** Then we wordalize a whitelist of features, following the file 22 pattern. Example (ours): *"Chance of scoring in the next 10 actions: 2% → 9%, mainly because it ended 8 m from goal (was 13 m)…"* Time-of-match features also showed up as top contributors, which is spurious, so keep them out of the text.

## Findings

### 1. What we ran (our run)

Setup: Windows laptop CPU, Python 3.12, socceraction 1.5.3 (`multimethod<2` pin, see file 26), xgboost 3.4.1, scikit-learn 1.9.1. Each match is two seeded halves from file 02's `generate()` (seeds 2s and 2s+1). CDF already fixes home to attack +x, so no flip is needed. Matches are wrapped as CDF event lines and converted with the file 26 `cdf_to_spadl`, and all pass `SPADLSchema`.

| Stage | Result (ours, both generator fixes) | Time |
|---|---|---|
| Generate + SPADL | 200 matches, 218,180 actions (pass 181,504 · tackle 26,128 · cross 5,827 · shot 4,721). 23.6 shots, 1.58 goals per match, 86.1% pass completion | 11.7 s |
| xT fit (16×12, eps 1e-5) on 150 train matches | Converged in 29 iterations | 0.9 s |
| VAEP features + labels (3 previous actions, k = 10) | 154 features (we dropped `actiontype_result_onehot`, which is noise with only 4 action types) | 14.6 s |
| VAEP fit, socceraction default xgboost (100 trees, depth 3, early stop on AUC) | 163,379 train / 54,801 test states | 2.0 s |
| Rate a match (VAEP + xT) | `offensive_value`, `defensive_value`, `vaep_value`, `xt_value` per action | 0.11 s |

For comparison, the VAEP paper's XGBoost took 16-22 minutes to train on 8.5-11.4 M real actions (Decroos et al., Table 5).

### 2. The generator bugs matter more than the model choice (ours)

| Generator variant (200 matches) | Shots/match | Goals/match | Shots from byline | Concede label rate | xT peak | Spearman(x, xT) | VAEP scores AUC / Brier skill |
|---|---|---|---|---|---|---|---|
| File 02 as published | 28.1 | 3.18 | 50% | 1.20% | 0.092 | 0.83 | 0.776 / 17.7% |
| + goal-kick fix | 23.1 | 1.62 | 47% | 0.21% | 0.104 | 0.85 | 0.806 / 13.1% |
| + byline fix (main run) | 23.6 | 1.58 | 2% | 0.20% | 0.067 | 0.95 | 0.746 / 12.1% |

The buggy versions *look* better: more goals and a higher AUC. That is because the model learns the bugs, which are easy to predict. Under bug 1, the concede rate is 6× higher, because every missed shot hands the opponent a chance. Under bug 2, the xG on the goal line is about 0.89. After the fixes, conversion is 7.5% and goals are 1.58 per match. The cited Premier League reference is 2.93 goals per match and ~11-11.9% conversion (file 02 table). So **re-tune the 02 xG intercept and shot rate next**, then refit. This is a 30-second job.

### 3. xT grid sanity (ours)

Chart (ours): a heat map of the 16×12 grid with cell values ×100 is saved to the session scratchpad as `pv33/xt_grid_33.png`. It is not in the repo, and `plot_xt.py` regenerates it.

- The peak is **0.067 in the two central cells of the last column (98-105 m)**. Next to it are 0.041 (penalty spot) and 0.028-0.033 at the box corners. The own-half mean is 0.0088, and the minimum is 0.0065.
- Monotonic and symmetric: the column means rise in 15 of 15 steps. Spearman(x, xT) is 0.95, and the left-right mirror correlation is 0.97. In the final column, the centre is 4.9× the wings.
- **Compared with published patterns (qualitative only):** Singh's real-data xT also starts as "effectively an xG model" at iteration 1 and spreads value away from goal as iterations add moves. His worked example moves a pass from xT 0.077 to 0.158. Every one of our cells is below 0.158, so our surface is flatter and lower. That fits the toy xG being weak: mean shot xG is 0.074. socceraction's docs say xT should only value moves that keep possession, so `xt_value` is NaN for shots, tackles and failed passes. Use VAEP for those.

### 4. VAEP models vs base rate (ours) and the paper's real-data pattern

| Model (test = 50 synthetic matches) | Positive rate | Log loss (base) | Brier (base) | Brier skill | AUC | ECE |
|---|---|---|---|---|---|---|
| scores, xgboost | 1.44% | 0.0649 (0.0755) | 0.0125 (0.0142) | 12.1% | 0.746 | 0.0025 |
| scores, logistic (sklearn fallback, scaled) | 1.44% | 0.0647 | 0.0125 | 12.1% | 0.767 | 0.0021 |
| concedes, xgboost | 0.20% | 0.0139 (0.0146) | 0.00202 (0.00202) | −0.2% | 0.727 | 0.0006 |
| concedes, logistic | 0.20% | 0.0137 | 0.00201 | 0.4% | 0.757 | 0.0004 |
| *Paper, real data, CatBoost: scores / concedes* | *1.5% / 0.5%* | — | *0.01376 (0.01632) / 0.00547 (0.00564)* | *15.7% / 3.0%* | *0.769 / 0.731* | — |

- The pattern matches the paper. Scores gets a modest Brier gain. Concedes barely beats "always predict the mean", and AUC is 0.73-0.77 for both. In the paper, XGBoost came "a close second" to CatBoost. Here a scaled logistic regression is as good as xgboost, because the generator's rules are simple. **The sklearn fallback is fine for the hackathon.**
- **Ground-truth check (only possible on synthetic data):** P_scores in the state *just before* each shot has Spearman 0.73 with the generator's hidden xG (0.88 in the goal-kick-only run). Mean shot xG is 0.074 against a goal rate of 0.075. VAEP features include the action's own result, so P_scores is 1.000 at goals and 0.006 at misses. A goal's VAEP averages 0.957 and a miss −0.016.
- **Circularity caveat:** the model learns our generator, not football. The numbers prove the plumbing and calibration, not football truth. That is still the right claim for a contest that bans real data.

### 5. Uses of the value layer (ours, on the 50 test matches)

**Momentum (file 23).** We fed file 23's `momentum_series` with three variants: (a) all-action positive offensive VAEP, (b) shot xG only, and (c) build-up VAEP plus shot xG instead of the shot's VAEP. In (a), each goal adds about 0.95 in one minute and dominates the 5-minute window. In (b), the line is flat between shots. In our test match, variant (c) moved almost every minute and peaked around the chances, not the outcomes. **Use (c).** Scale against the 98th percentile of a reference set of synthetic matches, not per match.

**Relay Credit.** There were 90 goals in the test set. The scoring possession had a median of 10 actions and 6 players.

| Scheme | What the scorer gets | Note |
|---|---|---|
| VAEP sum per player (positive part normalised) | 94% on average | Additive, so it *is* the Shapley value of the game "v(S) = sum of S's action values". We checked this numerically (`shapley == vaep sum: True`). |
| Chance-creation split: build-up `offensive_value` only, excluding the shot | 0% unless they also built up | Build-up adds a mean ΔP of only 0.053 in total, so show it as its own "who made the chance" card |
| xGChain / xGBuildup (StatsBomb, Lawrence 2018) | Equal xG to everyone involved / excludes shot and assist | Easy for fans to read, but ignores who added value |
| Restricted Shapley (Cefis, Metulini, Carpita 2026) | Coalitions limited to observed passing links, worth from xGA | Use only if we need interaction effects; the publication's main application is shot-ending actions in Serie A |

Recommendation: the card shows "Finish 94% · Creation 6%", and the creation part is split by build-up VAEP. Within one possession, offensive values telescope: they sum to P_score(end) − P_score(start), except where socceraction resets after a long gap between actions. So the split adds up and is easy to explain.

**Ghost Team.** The ghost is the mean VAEP of the same action type from the same 8×6 zone, fitted on the train matches. A player's value above the ghost per half has SD 0.205, or 0.065 without shots. The correlation between first-half and second-half value across player-matches is **0.02 (−0.01 without shots)**. That is the correct answer, because the 02 generator picks players uniformly at random and gives them no skill. A 0.9 "top player" in one match is just the scorer. Before we narrate Ghost Team or player rankings, give the generator players latent skills (pass accuracy, finishing). Then E Realism Bench can report the correlation of recovered skill with true skill.

**Called It baseline.** Ten actions last a median of 44 s here. Reliability of P_scores on the test set (bins → mean p / observed): 0-0.5% → 0.20%/0.40%. 0.5-1% → 0.74%/1.05%. 1-2% → 1.44%/1.71%. 2-5% → 2.92%/2.94%. 5-10% → 6.2%/4.5%. 10-20% → 12.2%/12.1%. This is good enough to serve as the "house" probability in a fan's Brier skill score (file 23 functions). For calls framed by time ("goal in the next 5 minutes"), use the file 23 Poisson model instead. The VAEP horizon is about 44 s, not minutes.

**Explaining a value change (file 22).** Take the TreeSHAP log-odds contributions for the state after the action and subtract those for the state before it. Example pass (ours): P_scores went from 0.021 to 0.094. The top contributors were `end_dist_to_goal_a0` +0.68, `end_y_a2` +0.45 and `time_seconds_overall_a2` +0.38. The third is spurious, because time carries no signal in our generator. So **wordalize only a whitelist of the current action's features** and lump the rest into "the build-up before it". The output then reads: *"Chance of scoring in the next 10 actions: 2% → 9%, mainly because it ended 8 m from goal (was 13 m)."* Numbers go through file 22's locked placeholders.

## So what for us

- **Stage: Interpret, which feeds Explain and Render.** Run the pipeline as an ACA job at deploy time. Store `xt_grid.json` and `vaep.pkl` with the model version and generator seed range in the cue's `source`. Rate actions live: 0.11 s per match, so well under 1 ms per action.
- **Fix file 02 first** (two lines, below), then re-tune toward 2.9 goals per match and ~11% conversion, then refit. The same table becomes an **E Realism Bench** exhibit: "bugs we caught because the value model looked too good".
- **06 Relay Credit:** ship the Finish/Creation card from VAEP sums. Cite Shapley equivalence on the judge page. Fall back to xGChain wording for the casual audience.
- **01 Ghost Team:** don't claim player quality until the generator has skill parameters. Until then, use the ghost only per action ("this pass was +0.04 above an average pass from here").
- **21 Called It:** use P_scores as the house baseline for 10-action calls, and file 23's Poisson model for minute calls.
- **C One Number / 23 momentum:** use build-up VAEP plus shot xG as the feed.
- **Rule risk:** we fit only on synthetic data. Do not load Singh's published grid or StatsBomb data, as file 08 also warns.

## Reuse: code & links

**Fixes to file 02 `generate()`** (tested):
```python
# 1) goal kick after a missed shot belongs at the *defending* (shot-target) end
x, y = d * (L / 2 - 5.5), 0.0                      # was: -d * (L / 2 - 5.5)
# 2) re-draw passes aimed off the pitch instead of clamping them onto the line (insert after `ang = ...`)
for _ in range(20):
    if abs(x + d * length * math.cos(ang)) < L / 2 - 0.5 and abs(y + length * math.sin(ang)) < W / 2 - 0.5: break
    length, ang = abs(rng.gauss(14, 8)), rng.gauss(0, 0.9)
```

**Pipeline: generate → SPADL → fit → evaluate → rate → save** (tested, 34 s for 200 matches; reproduces the table in §4 exactly):
```python
# pv_pipeline.py  -- python pv_pipeline.py out/ 200
# needs: gen02.py (file 02 generator + the 2 fixes), cdf_spadl.py (file 26 converter)
import sys, time, json, pickle, pathlib, warnings
from datetime import datetime, timedelta, timezone
import numpy as np, pandas as pd
from sklearn.metrics import log_loss, brier_score_loss, roc_auc_score
from socceraction import xthreat
from socceraction.spadl import play_left_to_right
from socceraction.vaep import VAEP, features as fs
import gen02; from cdf_spadl import cdf_to_spadl
warnings.filterwarnings("ignore")
OUT = pathlib.Path(sys.argv[1]); OUT.mkdir(exist_ok=True); N = int(sys.argv[2]); N_TEST = N // 4
KO = {"first_half": datetime(2026, 10, 20, 15, tzinfo=timezone.utc), "second_half": datetime(2026, 10, 20, 16, tzinfo=timezone.utc)}
iso = lambda d: d.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
META = {"match": {"periods": [{"period": p, "start_time": iso(t)} for p, t in KO.items()]},
        "teams": {"home": {"id": "home"}, "away": {"id": "away"}}, "venue": {"pitch_length": 105.0, "pitch_width": 68.0}}

def match(seed, mid):                       # two seeded halves; CDF: home attacks +x all match
    lines = []
    for k, per in enumerate(KO):
        for e in gen02.generate(seed=2 * seed + k):
            lines.append({"match": {"id": mid}, "meta": {"is_synced": False}, "event": {
                **{f: e[f] for f in ("type", "sub_type", "is_successful", "outcome_type", "team_id", "player_id",
                                     "x", "y", "x_end", "y_end", "body_part")},
                "id": per[0] + e["event_id"], "period": per, "time": iso(KO[per] + timedelta(seconds=e["time_s"]))}})
    return cdf_to_spadl(META, lines, game_id=mid)

t0 = time.perf_counter()
games = {f"syn_{s:04d}": match(s, f"syn_{s:04d}") for s in range(N)}
ids = list(games); test, train = ids[:N_TEST], ids[N_TEST:]
gs = lambda g: pd.Series({"game_id": g, "home_team_id": "home"})

xT = xthreat.ExpectedThreat(l=16, w=12).fit(pd.concat([play_left_to_right(games[g], "home") for g in train]))
xT.save_model(str(OUT / "xt_grid.json"))                       # row 0 = top touchline (socceraction convention)

XF = [fs.actiontype_onehot, fs.result_onehot, fs.bodypart_onehot, fs.time, fs.startlocation, fs.endlocation,
      fs.startpolar, fs.endpolar, fs.movement, fs.team, fs.time_delta, fs.space_delta, fs.goalscore]
v = VAEP(xfns=XF, nb_prev_actions=3)
X = {g: v.compute_features(gs(g), games[g]) for g in ids}; Y = {g: v.compute_labels(gs(g), games[g]) for g in ids}
cat = lambda D, k: pd.concat([D[g] for g in k])
np.random.seed(33); v.fit(cat(X, train), cat(Y, train), learner="xgboost", fit_params={"verbose": False})
cols = fs.feature_column_names(XF, 3); M = v._VAEP__models          # private attr: the two XGBClassifiers

metrics = {}
for c in ("scores", "concedes"):
    y = cat(Y, test)[c].astype(int).values; p = M[c].predict_proba(cat(X, test)[cols])[:, 1]
    base = np.full(len(y), cat(Y, train)[c].mean())
    metrics[c] = dict(pos_rate=y.mean(), logloss=log_loss(y, p), logloss_base=log_loss(y, base),
                      brier=brier_score_loss(y, p), brier_base=brier_score_loss(y, base), auc=roc_auc_score(y, p))

def rate(g):                                 # per-action values for overlays / momentum / credit
    a = games[g].copy()
    a[["offensive_value", "defensive_value", "vaep_value"]] = v.rate(gs(g), a, X[g]).values
    a["xt_value"] = xT.rate(play_left_to_right(a, "home"))     # NaN for non-moves and failed moves
    return a
pd.concat([rate(g) for g in test]).to_csv(OUT / "rated_test.csv", index=False)
pickle.dump(v, open(OUT / "vaep.pkl", "wb"))
json.dump({"metrics": metrics, "runtime_s": time.perf_counter() - t0}, open(OUT / "metrics.json", "w"), indent=1, default=float)
```
No xgboost? Fit `make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000))` per label on `X[cols]`. It scored the same in §4. To plot the grid, use `np.array(json.load(open("xt_grid.json")))[::-1]` with `imshow(origin="lower", extent=(0,105,0,68))`.

**Value consumers** (tested on the output above: Shapley equals the VAEP sum, and the credit table is as in §5):
```python
import itertools, math, numpy as np, pandas as pd, xgboost as xgb

def add_possessions(R):                      # new possession whenever the acting team / period / game changes
    R = R.reset_index(drop=True)
    R["poss"] = ((R.team_id != R.team_id.shift()) | (R.period_id != R.period_id.shift())
                 | (R.game_id != R.game_id.shift())).cumsum()
    R["minute"] = R.time_seconds / 60 + 45 * (R.period_id - 1)
    R["is_goal"] = (R.type_name == "shot") & (R.result_name == "success")
    return R

def momentum_feed(m, shot_xg=None):          # -> (minute, 'H'|'A', value) for file 23 momentum_series()
    val = m.offensive_value.clip(lower=0).copy()
    if shot_xg is not None:                  # replace the shot's outcome jump by its pre-shot xG
        val[m.type_name == "shot"] = shot_xg[m.type_name == "shot"]
    return list(zip(m.minute, np.where(m.team_id == "home", "H", "A"), val))

def relay_credit(R, goal_idx):               # Finish vs Creation split for one goal
    a = R[(R.poss == R.at[goal_idx, "poss"]) & (R.index <= goal_idx)]
    per = a.groupby("player_id").vaep_value.sum(); pos = per.clip(lower=0)
    build = a.iloc[:-1].groupby("player_id").offensive_value.sum().clip(lower=0)
    return pd.DataFrame({"vaep": per, "share": pos / pos.sum(),
                         "creation_share": (build / build.sum()).reindex(per.index).fillna(0)})

def shapley(players, v):                     # exact; fine for <= 10 players
    k, out = len(players), {}
    for i in players:
        rest = [p for p in players if p != i]
        out[i] = sum(math.factorial(r) * math.factorial(k - r - 1) / math.factorial(k)
                     * (v(frozenset(C) | {i}) - v(frozenset(C)))
                     for r in range(k) for C in itertools.combinations(rest, r))
    return out   # with v = lambda C: a[a.player_id.isin(C)].vaep_value.sum() this equals the per-player VAEP sum

zone = lambda x, y: (x // (105 / 8)).astype(int).clip(0, 7) * 10 + (y // (68 / 6)).astype(int).clip(0, 5)
def ghost_table(train):                      # average action of the same type from the same zone
    return train.assign(z=zone(train.start_x, train.start_y)).groupby(["type_name", "z"]).vaep_value.mean()
def value_above_ghost(R, ghost):
    g = R.assign(z=zone(R.start_x, R.start_y)).join(ghost.rename("ghost"), on=["type_name", "z"])
    return g.vaep_value - g.ghost.fillna(0)

def explain_change(model, X_before_after, top=6):    # model = M["scores"]; rows = states i-1 and i
    C = model.get_booster().predict(xgb.DMatrix(X_before_after), pred_contribs=True)   # last col = bias
    d = pd.Series(C[1, :-1] - C[0, :-1], index=X_before_after.columns)
    return d.reindex(d.abs().sort_values(ascending=False).index)[:top]
# wordalize only whitelisted current-action features, e.g.
# {"end_dist_to_goal_a0": "it ended {a:.0f} m from goal (was {b:.0f} m)", "dx_a0": "it moved the ball {a:+.0f} m upfield"}
```

Links: socceraction (MIT) https://github.com/ML-KULeuven/socceraction · VAEP docs https://socceraction.readthedocs.io/en/latest/documentation/valuing_actions/vaep.html · xT docs https://socceraction.readthedocs.io/en/latest/documentation/valuing_actions/xT.html · xgboost `pred_contribs` https://xgboost.readthedocs.io/en/stable/python/python_api.html

## Sources

- Decroos, Bransen, Van Haaren, Davis, "Actions Speak Louder than Goals: Valuing Player Actions in Soccer", KDD 2019. k = 10, 3-action game state, CatBoost, Table 3 Brier/AUC, Table 5 runtimes — https://arxiv.org/abs/1802.07127 (PDF https://arxiv.org/pdf/1802.07127) — accessed 20 Oct 2026
- socceraction VAEP documentation (formulas, features, labels) — https://socceraction.readthedocs.io/en/latest/documentation/valuing_actions/vaep.html — accessed 20 Oct 2026
- socceraction xT documentation ("only … actions that move the ball and … keep … possession") — https://socceraction.readthedocs.io/en/latest/documentation/valuing_actions/xT.html — accessed 20 Oct 2026
- socceraction repository (v1.5.3 source read locally: `VAEP.fit` defaults, labels, `ExpectedThreat`) — https://github.com/ML-KULeuven/socceraction — accessed 20 Oct 2026
- Karun Singh, "Introducing Expected Threat (xT)" (16×12 grid, 2017-18 PL data, worked example 0.077→0.158) — https://karun.in/blog/expected-threat.html — accessed 20 Oct 2026
- Thom Lawrence, "Introducing xGChain and xGBuildup" (30 Sep 2018; now on hudl.com) — https://www.hudl.com/blog/introducing-xgchain-and-xgbuildup — accessed 20 Oct 2026
- Cefis, Metulini, Carpita, "A model-based restricted Shapley value to measure the players' contribution to shot actions in football", Computational Statistics 2026 — https://arxiv.org/abs/2603.11016 — accessed 20 Oct 2026
- Lundberg & Lee, "A Unified Approach to Interpreting Model Predictions" (SHAP), NIPS 2017 — https://arxiv.org/abs/1705.07874 — accessed 20 Oct 2026
- L. S. Shapley, "A Value for n-Person Games" (RAND P-295, 1952/1953) — https://www.rand.org/pubs/papers/P295.html — accessed 20 Oct 2026 (unverified: page returned 403)
- xgboost Python API, `Booster.predict(pred_contribs=True)` returns SHAP values with a final bias column — https://xgboost.readthedocs.io/en/stable/python/python_api.html — accessed 20 Oct 2026
- Internal: files 02 (generator, PL realism ranges), 08 (xT, rule risk), 22 (wordalization), 23 (momentum, scoring functions), 26 (CDF→SPADL converter)
