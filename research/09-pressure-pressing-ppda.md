# 09 — Pressure, pressing intensity, PPDA, field tilt and "control vs chaos" metrics

_Accessed/compiled: 20 Oct 2026 · Priority area: Interpret stage (pressing and territory metrics, momentum and change detection) for C One Number, F Graphics Desk, A TwinCast, 13 Recap Dial, 17 Heartbeat_

## TL;DR

- **PPDA = opponent passes ÷ our defensive actions, counted only in the pressing zone.** Colin Trainor (StatsBomb blog, 30 Jul 2014) counted tackles, interceptions, challenges (failed tackles) and fouls at Opta x > 40, which is the 60% of the pitch nearest the opponent's goal. Lower values mean a more intense press. Providers define the zone and action set differently (see table), so we should always print which variant we use.
- **Pressure events are a StatsBomb invention.** One is triggered when a defender is within about 5 yards of the player on the ball (up to 10 yards, mostly for goalkeepers). "Counterpress" marks pressing actions within **5 s of an open-play turnover**. A "counterpressure regain" is the ball won back within 5 s of a counterpressure. Opta's tracking-era version is **"intense pressure": an opponent within 2 m**.
- **Two tracking-based pressure models can be implemented today.** The first is **Andrienko et al. 2017**: an oval zone, 9 m in front of the target and 3 m behind, with pressure `(1 − d/L)^1.75`, summed over defenders. The second is **Bekkers 2025 "Pressing Intensity"**: Spearman-style time-to-intercept, a logistic with σ = 0.45 and T = 1.5 s, combined as `1 − ∏(1 − p)`. It is open-source in `unravelsports`. Both are about 15 lines of NumPy (below).
- **"Momentum" on broadcasts is an Opta possession-value model summed per minute** (the Flashscore "Match Momentum" bars). No provider publishes a "control" or "chaos" index. The two formulas we give below are **our proposal**, built only from counts we can explain on screen.
- **To generate "pressure changed at 55'" cues,** run a two-sided CUSUM on per-minute bins with a baseline taken from reference synthetic matches. In our quick simulation, h = 6 gave about 6% false alarms per 90 minutes and about 5 minutes of delay for a 1.5σ shift. Use `ruptures` PELT offline for recaps.

## Findings

### 1. Event-based definitions

**PPDA variants**

| Source | Defensive actions counted | Zone | Notes |
|---|---|---|---|
| Trainor 2014 (StatsBomb blog) | tackles, interceptions, challenges (failed tackles), fouls | Opta x > 40, i.e. the attacking 60% (all of the opponent's half plus a fifth of our own) | Uses passes "made by attacking team" whether or not they were completed. Smoothed with 6-game rolling averages. |
| StatsBomb Bundesliga report (2022) | tackle, interception, foul | "40% of the length of the pitch away from a team's own goal and forwards" | The same zone as Trainor's. |
| Premier League explainer | tackles, interceptions, challenges, fouls | "three-fifths (or 60 per cent) of the pitch nearest the opposition's goal" | Example: Liverpool 8.62, the lowest in the PL in 2021/22 (Wyscout data). |
| Wyscout glossary | fouls, interceptions, **won** defensive duels, sliding tackles | "final 60%" | Example: Liverpool 5.2 vs Man Utd 17.6 (20 Oct 2019). Top-5 league average 11.01 (2018/19). |
| The Analyst (Opta) glossary | fouls, tackles, interceptions, challenges, **blocked passes** | **outside the pressing team's own defensive third** (about 67%) | This is a different zone from the 60% versions. |

Caveats from the PL explainer: a team that dominates possession can post a low PPDA without pressing hard. PPDA ignores shape and off-ball pressing, and because failed tackles count, a low PPDA does not mean the press was successful.

**Related StatsBomb/Opta metrics**

| Metric | Definition (source) |
|---|---|
| Pressure (StatsBomb) | "Applying pressure to an opposing player who's receiving, carrying or releasing the ball". It has a duration. Any on-ball event that overlaps that duration gets `under_pressure = true` (Open Data Events spec v4, Appendix 7). The original trigger is about a 5-yard radius, up to 10 yards (Morgan 2018). |
| Counterpress (StatsBomb) | A boolean on pressure, dribbled past, 50-50, duel, block, interception and foul events: "pressing actions within 5 seconds of an open play turnover". |
| Counterpressure regain | "Times a team won the ball back within 5 seconds of a player counterpressuring an opponent" (StatsBomb Bundesliga report). |
| Aggression % (StatsBomb) | The share of an opponent's pass receipts that are tackled, fouled or pressured within 2 s. |
| Defensive distance (StatsBomb) | The average distance from a team's own goal at which it makes its defensive actions. |
| Counter-pressing fraction | The share of open-play possessions, in zones outside a team's own defensive third, where pressure is applied within 5 s. The PL average in that sample was 0.47 (Morgan 2018). |
| Sequence (Opta) | A passage of play belonging to one team, ended by a defensive action, a stoppage or a shot. A **possession** is one or more consecutive sequences by the same team. |
| High turnover (Opta) | A sequence or possession that starts in open play "40 metres or less from the opponent's goal". |
| Passes per sequence (Opta) | The glossary only defines "passes within sequences", the number of passes in a sequence. Team PPS is that number averaged. Man City averaged about 3 more than West Brom in the 2020/21 article. |
| Direct speed (Opta) | Progress ÷ sequence time: the "average speed of ball movement towards the opponent goal line during a sequence". |
| Build-up attack / direct attack (Opta) | A build-up attack is an open-play sequence with 10 or more passes that ends in a shot or a box touch. A direct attack starts just inside the team's own half, has at least 50% of its movement towards goal, and ends in a shot or a box touch. |
| Pressed sequences (Opta) | Opponent open-play sequences starting in their defensive third in which they make three or fewer passes. |
| Start distance (Opta) | The average distance from a team's own goal at which its open-play sequences start. |
| Intense pressure (Opta Vision, tracking) | At least one opponent within **2 m** of the player on the ball. Opta Vision also defines compactness as a team area below 600 m² (high) or above 900 m² (low). |

**Field tilt** has no single owner. Driblab defines it as a team's share of passes and touches in the last 35 m, with Arsenal averaging 69.7% in its example. Other glossaries use the share of final-third touches or passes. We found no Opta or The Analyst page defining it, so its Opta definition is (unverified). The simplest form to explain on screen: `tilt_home = home final-third passes ÷ (home + away final-third passes)`.

**Tempo and directness.** Opta's measure is direct speed (m/s towards goal). A simple "tempo" figure is **passes per minute of own possession**. That is our proposal; we found no standard definition.

### 2. Tracking-based pressure on the ball carrier

**Andrienko et al. 2017** (Data Mining and Knowledge Discovery 31(6)). Each defender has an oval pressure zone around the target. Its limit is `L = Dback + (Dfront − Dback)(z³ + 0.3z)/1.3`, with `z = (1 − cos θ)/2`. Inside the zone, pressure is `Pr = (1 − d/L)^q`. The experts' parameters Dfront = 9 m, Dback = 3 m and q = 1.75 were checked against four Dortmund games. With several threat directions (towards goal, towards teammates), the maximum is taken. With several pressers, the values are **summed**, so totals can exceed 100%. The REF impact statement says this model feeds the Bundesliga database; that is self-reported. Orientation note: the paper says θ = 0 means "presser in front", but that would give L = Dback in the formula. Our code measures θ on the presser→target vector, so a goal-side presser gets Dfront, matching the paper's figure. This is our reading.

**Bekkers 2025, "Pressing Intensity"** (arXiv 2501.04712, single author, UnravelSports). Time-to-intercept is `T_ij = τ_r + ‖(r_j + v_j) − (r_i + v_i τ_r)‖ / v_max + τ_β`, where τ_β is a penalty for changing direction. The probability is `p_ij = 1 / (1 + exp(−π/(√3σ)·(T − T_ij)))` with σ = 0.45 and T = 1.5 s. Pressure on a player is `P_j = 1 − ∏_i(1 − p_ij)`. For the ball carrier, it is the maximum of pressure on the player and pressure on the ball. Only "active" pressers count, using a 2 m/s speed threshold. The paper reports no quantitative validation. In `unravelsports`, `PressingIntensity.fit(...)` defaults to `reaction_time=0.7, time_threshold=1.5, sigma=0.45, method="teams"` and returns per-frame 11×11 TTI/PTI matrices as Polars lists. The code docstring says `ball_method="max"` but the code applies `np.minimum`, so check before relying on it.

### 3. Momentum, control and chaos

- **Opta / Flashscore "Match Momentum".** An Opta model values every on-ball action by how much it raises or lowers the chance of scoring. The values are summed per minute and compared between the two teams. Each bar is one minute, the bar shows the team with the higher value, and it updates each minute live. The EPL was among the launch competitions. A Defector piece (Jun 2026) describes it as recency-weighted with no y-axis scale and criticises it as vague. That third-party description is (unverified).
- An **xT-based momentum chart** (a rolling sum of each team's xT added) is the open-data equivalent. xT is covered in file 08.
- We found no published "chaos" index or entropy-of-possession broadcast metric. The following are **our proposals**:
  - **Control (home), rolling 5 min:** `possession_share × field_tilt × pass_completion`. All three are in 0..1, so control is in 0..1 and each factor can be explained on screen.
  - **Chaos, rolling 5 min:** `(possession changes + duels + defensive actions) per minute`, z-scored against the match so far, so it can run live. Optional extra: the Shannon entropy of the possession-owner sequence in the window, where alternating ownership gives high entropy.
  - **Pressing intensity, rolling:** a rolling PPDA, plus the mean Andrienko/Bekkers pressure on the ball carrier per minute when we have positions.

### 4. Detecting change points ("the pressure changed at 55'")

- **CUSUM** (Page; NIST tabular form): `S_hi = max(0, S_hi + z − k)`, `S_lo = max(0, S_lo − z − k)`, alarm when either exceeds h. NIST's rule of thumb is k = δ/2 (0.5 for a 1σ shift) and h about 4-5. The change start is estimated as the last time the sum was zero.
- **Our simulation** (iid Gaussian per-minute bins, 90 bins, warm-up 15, 500 runs per cell; these are not published figures):

| h | baseline | false alarm (any) per match | detection of a 1.5σ shift at 55' | median delay |
|---|---|---|---|---|
| 5 | estimated from first 15 min | 42% | 99% | 4 min |
| 5 | known (from reference matches) | 14% | 99% | 4 min |
| 6 | known | 6% | 100% | 5 min |
| 8 | known | 0.2% | 100% | 7 min |

  Use non-overlapping bins, not overlapping rolling windows, because autocorrelation inflates false alarms.
- **ruptures** (v1.1.10 on PyPI) provides offline search with Pelt, Binseg, BottomUp, Window, Dynp and KernelCPD, and costs l1/l2/normal/rbf/rank/AR and others. It suits post-match recaps.
- **BOCPD** (Adams & MacKay 2007) gives an online posterior over "run length since the last change". It is a good fit if we want a calibrated "probability the game has changed" for 21 Called It, but CUSUM is enough for a demo.

### 5. How broadcasters and media show these

- **Momentum:** per-minute bars mirrored above and below a centre line in team colours (Flashscore/Opta), also on the BBC according to Defector.
- **PPDA:** league tables and bar charts on The Analyst, the PL site and Wyscout. We found no source for PPDA as a live TV graphic (unverified).
- **Opta Vision / The Analyst:** "passes under intense pressure" completion %, time spent in a low block, and compactness. These are tracking-based but presented as plain percentages.

## So what for us

- **Interpret stage (all ideas).** Our synthetic generator should emit `pressure` events with `duration`, an `under_pressure` flag, a `counterpress` flag (≤ 5 s after a turnover), `possession_change`, and x in metres from the acting team's goal. This lets us compute every metric above exactly, and match the "pressure" field the hackathon lists.
- **C One Number:** good single metrics are "Pressure on ball: 0.82" (Bekkers PTI, 0-1, easy to explain as "82% chance a defender gets there in time") and "Field tilt 68%". Avoid raw PPDA for casual viewers, since a lower value being better confuses them. Show "passes allowed before we win it back" instead.
- **F Graphics Desk / A TwinCast:** run CUSUM on per-minute chaos and control, plus pressure on the carrier. Every alarm becomes a proposed cue: `metric="chaos_index", text={casual:"The game has turned frantic since 55'", analyst:"Turnovers+duels/min up 1.8σ vs baseline (CUSUM, h=6)"}`, with evidence ids pointing to the events in the window. In TwinCast we can grade CV-derived pressure against ground-truth pressure from the simulator.
- **13 Recap Dial / 17 Heartbeat:** use the `ruptures` segments as recap chapters, and pressure on the carrier as the haptic intensity.
- **Recommendation.** Ship the Andrienko model first: it needs no learning, has 3 parameters and is easy to show on screen. Add Bekkers PTI if velocities are available. Label control and chaos as "Berbata indices (our definition)" in the UI, so the fact-checker never presents them as Opta stats.

## Reuse: code & links

All of the following ran on Python 3 / NumPy / pandas with synthetic test data, except the `ruptures` snippet, which was not executed (the library is not installed here).

```python
import numpy as np, pandas as pd
DEF_ACTIONS = {"tackle", "interception", "challenge", "foul"}   # Trainor 2014 / PL explainer

def ppda(events, team, pitch_len=105.0, zone_from_own_goal=0.40):
    """events: dicts team, type, x (m from ACTING team's own goal). 0.40 = Trainor/StatsBomb;
    use 1/3 for The Analyst 'outside own defensive third' variant."""
    cut = zone_from_own_goal * pitch_len
    opp_passes = sum(e["team"] != team and e["type"] == "pass" and pitch_len - e["x"] >= cut
                     for e in events)                         # flip opponent x into our frame
    def_actions = sum(e["team"] == team and e["type"] in DEF_ACTIONS and e["x"] >= cut
                      for e in events)
    return opp_passes / def_actions if def_actions else float("inf")

def rolling_indices(ev, home, win_s=300, step_s=60, L=105.0, min_ref=5):
    """ev: DataFrame t(s), team, type, x, outcome(1/0), poss_change(bool). Control/chaos = OUR proposal."""
    ev, rows = ev.sort_values("t"), []
    for t1 in np.arange(win_s, ev.t.max() + step_s, step_s):
        w = ev[(ev.t > t1 - win_s) & (ev.t <= t1)]
        p = w[w.type == "pass"]; mine = p[p.team == home]; f3 = p[p.x >= 2 * L / 3]
        tilt = (f3.team == home).mean() if len(f3) else 0.5      # share of final-third passes
        poss = len(mine) / len(p) if len(p) else 0.5             # pass share as possession proxy
        comp = mine.outcome.mean() if len(mine) else 0.0
        chaos = 60 / win_s * (w.poss_change.sum() + (w.type == "duel").sum()
                              + w.type.isin(DEF_ACTIONS).sum())
        rows.append(dict(t=t1, field_tilt=tilt, possession=poss, pass_comp=comp,
                         control=poss * tilt * comp, chaos_raw=chaos))
    out = pd.DataFrame(rows)
    ref = out.chaos_raw.expanding(min_periods=min_ref)           # baseline = match so far (live-safe)
    out["chaos_z"] = (out.chaos_raw - ref.mean().shift()) / ref.std().shift().clip(lower=0.5)
    return out
```

```python
def andrienko_pressure(target, threat_dir, defenders, d_front=9.0, d_back=3.0, q=1.75):
    """Andrienko et al. 2017 eqs (1)-(2). target (2,), threat_dir (2,) e.g. goal - target,
    defenders (n,2) in metres. Returns (total = sum, can exceed 1; per-defender array)."""
    u = threat_dir / np.linalg.norm(threat_dir)
    v = target - defenders                                       # presser -> target
    d = np.linalg.norm(v, axis=1)
    z = (1 - (v @ u) / np.maximum(d, 1e-9)) / 2                  # goal-side presser -> z=1 -> L=d_front
    L = d_back + (d_front - d_back) * (z**3 + 0.3 * z) / 1.3
    pr = np.clip(1 - d / L, 0, None) ** q
    return pr.sum(), pr

def pti_pressure(target, target_vel, defenders, def_vel, reaction=0.7, vmax=7.0,
                 T=1.5, sigma=0.45, active_speed=2.0):
    """Simplified Bekkers 2025: TTI -> logistic -> 1 - prod(1-p). Omits tau_beta; vmax is our guess."""
    tti = reaction + np.linalg.norm((target + target_vel) - (defenders + def_vel * reaction),
                                    axis=1) / vmax
    p = 1 / (1 + np.exp(-np.pi / (np.sqrt(3) * sigma) * (T - tti)))
    p[np.linalg.norm(def_vel, axis=1) < active_speed] = 0.0      # only active pressers
    return 1 - np.prod(1 - p), tti, p
# a defender 4 m goal-side scores (1-4/9)^1.75 = 0.357 on the Andrienko scale
```

```python
def cusum(x, k=0.5, h=6.0, warmup=15, cooldown=10, mu=None, sd=None):
    """Two-sided tabular CUSUM on per-minute bins. Pass mu/sd from reference synthetic matches.
    Returns [(alarm_idx, change_start_idx, 'up'|'down')]."""
    x = np.asarray(x, float)
    mu = x[:warmup].mean() if mu is None else mu
    sd = (x[:warmup].std(ddof=1) if sd is None else sd) or 1.0
    s_hi = s_lo = 0.0; z_hi = z_lo = 0; out = []; skip = warmup
    for i in range(warmup, len(x)):
        if i < skip: continue
        z = (x[i] - mu) / sd
        s_hi, s_lo = max(0.0, s_hi + z - k), max(0.0, s_lo - z - k)
        z_hi = i if s_hi == 0 else z_hi; z_lo = i if s_lo == 0 else z_lo
        if max(s_hi, s_lo) > h:
            up = s_hi > h; start = (z_hi if up else z_lo) + 1
            out.append((i, start, "up" if up else "down"))
            skip = i + cooldown                                  # let the new regime settle, then
            mu = x[start:skip].mean() if skip <= len(x) else mu  # re-baseline on it
            s_hi = s_lo = 0.0; z_hi = z_lo = skip
    return out
```

```python
# Offline recap segmentation (not executed here), per the ruptures docs:
import ruptures as rpt
bkps = rpt.Pelt(model="rbf").fit(per_minute_signal.reshape(-1, 1)).predict(pen=10)
```

- unravelsports PressingIntensity (API + source): https://unravelsports.readthedocs.io/en/latest/api/soccer/models.html
- ruptures docs: https://centre-borelli.github.io/ruptures-docs/
- StatsBomb open-data event spec (pressure/counterpress fields): https://github.com/statsbomb/open-data/tree/master/doc

## Sources

- Defensive Metrics: Measuring the Intensity of a High Press (Colin Trainor, 2014) — https://blogarchive.statsbomb.com/articles/soccer/defensive-metrics-measuring-the-intensity-of-a-high-press/ — accessed 20 Oct 2026
- How StatsBomb Data Helps Measure Counter-Pressing (Will Morgan, 2018) — https://blogarchive.statsbomb.com/articles/soccer/how-statsbomb-data-helps-measure-counter-pressing/ — accessed 20 Oct 2026
- StatsBomb Bundesliga Report 1 (metric definitions) — https://blogarchive.statsbomb.com/uploads/2022/05/StatsBomb-Bundesliga-Report-1.pdf — accessed 20 Oct 2026
- StatsBomb Open Data Events v4.0.0 spec — https://github.com/statsbomb/open-data/blob/master/doc/Open%20Data%20Events%20v4.0.0.pdf — accessed 20 Oct 2026
- Revisiting Pressure With StatsBomb 360 (Thom Lawrence, 2022) — https://blogarchive.statsbomb.com/articles/soccer/revisiting-pressure-with-statsbomb-360/ — accessed 20 Oct 2026
- Passes per defensive action: explained (Premier League) — https://www.premierleague.com/en/news/4250153 — accessed 20 Oct 2026
- Wyscout glossary: PPDA — https://dataglossary.wyscout.com/ppda/ — accessed 20 Oct 2026
- Opta football stats definitions (The Analyst) — https://theanalyst.com/articles/opta-football-stats-definitions — accessed 20 Oct 2026
- Possessions and sequences in football (The Analyst) — https://theanalyst.com/articles/possessions-and-sequences-in-football — accessed 20 Oct 2026
- Opta Vision stats / tracking data in the Premier League (The Analyst, Jul 2025) — https://theanalyst.com/articles/opta-vision-stats-tracking-data-premier-league — accessed 20 Oct 2026
- Field Tilt: percentage of passes and touches in the final third (Driblab, 2023) — https://www.driblab.com/blog/field-tilt-percentage-of-passes-and-touches-in-the-final-third — accessed 20 Oct 2026
- Andrienko et al., Visual analysis of pressure in football (DMKD 2017, accepted manuscript) — https://openaccess.city.ac.uk/id/eprint/17464/1/VAofPressing.pdf — accessed 20 Oct 2026
- REF 2021 output record for the Andrienko paper — https://results2021.ref.ac.uk/outputs/53a80cfc-447d-429f-9856-934155c87681?page=1 — accessed 20 Oct 2026
- Bekkers, Pressing Intensity (arXiv 2501.04712) — https://arxiv.org/html/2501.04712v1 — accessed 20 Oct 2026
- unravelsports pressing_intensity source — https://unravelsports.readthedocs.io/en/latest/_modules/unravel/soccer/models/pressing_intensity.html — accessed 20 Oct 2026
- Introducing Match Momentum (Flashscore / Opta) — https://www.flashscore.com/news/momentum/W82o7eCa/ — accessed 20 Oct 2026
- What on earth is match momentum (Defector, Jun 2026) — https://defector.com/what-on-earth-is-match-momentum — accessed 20 Oct 2026
- NIST/SEMATECH e-Handbook, CUSUM control charts — https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc323.htm — accessed 20 Oct 2026
- ruptures documentation — https://centre-borelli.github.io/ruptures-docs/ — accessed 20 Oct 2026
- Adams & MacKay, Bayesian Online Changepoint Detection (arXiv 0710.3742) — https://arxiv.org/abs/0710.3742 — accessed 20 Oct 2026
