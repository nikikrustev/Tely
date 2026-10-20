# 25 — Team shape and tactical metrics from tracking: compactness, block height, line breaks, phases of play, formations

_Accessed/compiled: 20 Oct 2026 · Priority area: Interpret stage (team-level tactical metrics) and Render stage (shape and line overlays), for A TwinCast, D Chalk Talk, F Graphics Desk, C One Number, E Realism Bench, 22 Half-Time Talk_

## TL;DR

- **FIFA's World Cup 2022 "Enhanced Football Intelligence" (EFI) is the primary vocabulary.** It defines line height as goal line to deepest outfielder, and team length as deepest to highest outfielder, goalkeeper excluded. A line is broken when the ball is played "beyond the deepest player in that line", going *through, around or over* a unit. Phases are computed per frame from tracking and kept only when they hold for enough consecutive frames. FIFA publishes no thresholds. Parlak's 2023 open-source re-implementation (UZH thesis, TRACAB at 25 Hz) gives tuned numbers we can start from, for example block-length limits of 37.7, 35.3 and 31.9 m.
- **Published reference ranges (professional men, systematic review of 13 studies):** team length **31–46 m**, width **35–48 m**, stretch index **7–16 m**, mean team area **~900 m²**. Every study found larger values in possession. Opta Vision (via The Analyst) buckets compactness as **< 600 m² = high** and **> 900 m² = low**.
- **Formation detection is template matching with the Hungarian algorithm.** Bialkowski et al. 2014 (EM + Hungarian per frame), Shaw & Glickman 2019 (2-minute possession windows, Kuhn-Munkres, 20 clusters, Bayesian classification) and Bekkers 2025 EFPI (scaled templates + linear sum assignment, in `unravelsports`) all build on it. SoccerCPD (KDD 2022) adds change-point detection with ≥5-minute segments and reports **72.4%** minute-level formation accuracy against expert labels.
- **SkillCorner's phases-of-play spec (Feb 2025) is the cleanest rule set for a broadcast.** It pairs build up/high block, create/medium block and finish/low block, plus direct (long ball 32+ m), quick break, transition, set play and chaotic.
- **Our NumPy/SciPy code (below) runs at about 0.7 ms per frame for all shape metrics and lines, and 0.26 ms for a 7-template formation match.** On toy data it labelled through/around/over correctly and recovered 140/140 noisy template windows.

## Findings

### 1. Definitions and how to compute them (x along the pitch, own goal at x = −52.5, 25 Hz)

| Metric | Definition (source) | Compute per frame |
|---|---|---|
| Defensive line height | "distance between a team's goal line and its deepest outfield player" (FIFA EFI) | `min(x_outfield) + 52.5`. FIFA reports averages split by in/out of possession × the ball's third (own, mid, final). |
| Team length | "distance between a team's deepest and highest players, excluding the goalkeeper" (FIFA EFI) | `max(x) − min(x)` over outfielders |
| Team width | Parlak: rightmost minus leftmost player | `max(y) − min(y)` |
| Surface area / compactness | Opta: "area of the pitch that the outfielders on the defending team are covering" | `scipy.spatial.ConvexHull(xy).volume`. In 2-D, `.volume` is the area and `.area` is the perimeter. |
| Centroid, stretch index | Centroid = mean position. Stretch index = mean player distance to the centroid (floodlight `CentroidModel`, citing Sampaio & Maçãs 2012 and Bourbousson et al. 2010) | `xy.mean(0)`; `norm(xy − c).mean()` |
| Units and lines | EFI groups outfielders into defensive, midfield and attacking units. The "line" is the deepest player of each unit. Parlak splits team length into equal thirds; an empty unit is invalid. | zonal thirds, or split at the 2 largest depth gaps |
| Line break | Completed pass, cross or carry that starts behind a line and ends beyond it. Direction is *over* if the ball goes above 1.67 m (Parlak, checked over 27 frames), *around* if it passes outside the unit's widest players, otherwise *through*. EFI also records attempted vs completed breaks, the deepest unit broken, units available, and whether the reception was inside or outside the shape. | see code |
| Receptions between and behind lines | Counts receptions between the midfield and defensive lines, and behind the defensive line (EFI). Parlak takes the lines 5 frames *before* the reception. | compare reception x with the line x |
| Forced turnover | Credited when a team "exert[s] pressure on the ball and then gains possession of the ball on the next touch". Several pressers count as one team turnover (EFI). | pressure flag (file 09) + possession change on the next touch |
| Offers to receive | A "clear and deliberate" signal or movement to receive the ball, counted whether or not the ball arrives. Located *in front*, *between units* or *in behind* the opposition shape (FIFA Football Language). | needs body orientation. Approximation: a run into a between-lines or behind zone at more than X m/s (ours, unverified) |

Opta's tracking-based line-breaking pass (Stats Perform analyst write-up) adds thresholds to filter trivial breaks. The pass must move the ball forward ≥ 10 m, start ≥ 5 m from the crossing point and end ≥ 2 m beyond the deepest player. Lines are found by clustering player positions along the length axis. _(These come from a search-result excerpt, because the page returned 403 to our fetcher, so treat them as unverified.)_

### 2. Typical reference values

| Quantity | Value | Source / status |
|---|---|---|
| Team length / width | 31–46 m / 35–48 m | Rico-González et al. 2022, *Biol Sport* 39(1) |
| Stretch index | 7–16 m | same |
| Team area (convex hull) | ~900 m² mean; 79±15 to 94±16 m² per outfield player | same |
| Compactness buckets | high < 600 m², low > 900 m² (defending outfielders) | Opta Vision via The Analyst. Example: Arsenal spent 47.0% of opponent build-up time in high compactness. |
| Attack vs defence | hull area when attacking about 2× the area when defending (one team, one match) | Shaw & Glickman 2019 |
| Block length limits | high 37.70, mid 35.31, low 31.85 m | Parlak 2023, tuned to reproduce FIFA reports. Not FIFA's own numbers. |
| Defensive line height | no fetched source gives typical metres | **(unverified)**: calibrate on our synthetic matches |

### 3. Formation detection and formation-change detection

- **Bialkowski et al. 2014 (ICDM):** "role representation" via EM. E-step: run the Hungarian algorithm on each frame to give each player a unique role, with cost = −log p(role generates location). M-step: re-fit each role's density. This is the summary given by the SoccerCPD paper; we did not read the original PDF.
- **Shaw & Glickman 2019 (Barça summit):** 180 matches at 25 Hz. The method aggregates each team's possessions into **2-minute** non-contiguous windows, drops possessions under 5 s, and ends a window at a substitution. That gives about 10 offensive and 10 defensive observations per team per match. Players are placed by averaging vectors between neighbours, anchored on the player in the densest part of the team. Observations are compared with a Wasserstein distance and Kuhn-Munkres pairing, with a scale factor k to ignore compactness. On 100 training matches (3,976 observations), hierarchical clustering gave **20** formation clusters. New windows are classified by Bayesian model selection.
- **EFPI (Bekkers 2025):** static templates and linear sum assignment. Positions are scaled to the template's length and width, and the lowest-cost template wins. It works per frame or per window, and a stability parameter blocks switches when costs differ only slightly. The code is in `unravelsports`.
- **SoccerCPD (Kim et al. KDD 2022):** applies Bialkowski roles, then builds a Delaunay role-adjacency matrix each frame, runs discrete g-segmentation, and drops frames with switch rate > 0.7 (set pieces). A change point is accepted only if p < 0.01, **both segments last ≥ 5 min**, and the mean adjacency matrices differ by Manhattan distance ≥ 7.0. On 10 Hz K League GPS data: formation accuracy 72.4% (1,941 of 2,680 minutes), position accuracy 86.5%. The main confusion is 4-4-2 vs 4-2-3-1.
- **FIFA EFI / Parlak:** a simple count of players in each unit per frame (4 levels if the two midfield units hold more than 4 players), with the majority vote per phase. Parlak's France result in the 2022 final sat between 4-3-3 and 4-2-4, which is a warning that unit counts drift with game state.

### 4. Phases of play: rule-based classification

FIFA's list has 9 out-of-possession phases (high/mid/low press or block, counter-press, recovery, defensive transition), 7 in possession (build up opposed/unopposed, progression, long ball, final third, counter-attack, attacking transition) and 4 set-play phases. The EFI document says build up, progression, final third, counter-attack, high press, mid block, low block, counter-press and recovery "are to be shown live on TV". Parlak's tuned rules:

| Phase | Rule (ball third from the attacker's view) |
|---|---|
| Build up opposed / unopposed | ball in own third. *Opposed* if any defender is < 5.36 m from the ball |
| Progression / final third | ball in middle / final third |
| High press / high block | ball in attacker's first third and a defender < 5.07 m (press), or defending attacking unit in that third and defending team length < 37.70 m (block) |
| Mid press / block | ball in middle third and defender < 2.28 m; or attacking unit in middle third and length < 35.31 m |
| Low press / block | ball in final third and closest defender < 1.23 m; or attacking unit in final third and length < 31.85 m |
| Counter-attack | after a turnover: ball path slope > 0.51 over 40 frames and > 2.11 m forward within 94 frames. That window is then reserved. |
| Counter-press | pressure within 21 frames of losing the ball. The next 49 frames are reserved. |
| Recovery | after a loss, defenders move faster than their match average toward their own goal, up to 139 frames |
| Long ball | ball higher than 3.24 m, window of 197 frames |

**SkillCorner (Phases of Play CSV spec, 16 Feb 2025)** pairs each in-possession phase with an out-of-possession one:

- **Build up / high block:** ball in own third and the carrier pressed, or opponents high.
- **Create / medium block:** the default.
- **Finish / low block:** the defensive line is near the box and possession has lasted ≥ 1 s.
- **Direct:** a long ball of 32+ m along x that is not a switch.
- **Quick break:** a regain in the opponent's half followed by rapid progression.
- **Transition:** the same, starting from a regain in our own half.
- **Set play:** corners, free kicks and long throws into the box, ending after at most 20 s.
- **Chaotic:** fewer than 3 passes (or more than one header) and less than 5 s of possession. A clearance under pressure is always chaotic.

The file also carries the team-in-possession width and length at the start and end of each phase. Their open data is MIT-licensed, at 10 fps.

### 5. On broadcasts

- **FIFA WC 2022:** FIFA promised "in-match and post-match enhanced football intelligence visuals" for every match, in AR and traditional graphics, with 11 metrics and explanation PDFs in 9 languages. The EFI document's presentation examples are a phases-of-play bar, a line-height and length side-on diagram, and a team-shape node map.
- **Opta Vision (The Analyst):** percentage of time in each compactness state during opponent build-up, line-breaking passes counted by number of lines broken (1/2/3), overloads, and intense pressure (within 2 m).
- **SkillCorner:** for each line-breaking pass it reports the phase, the defensive shape faced, the line broken and the number of players bypassed. That is a good template for the evidence fields on our cue.

## So what for us

- **Interpret stage, all ideas.** These metrics turn coordinates into tactical sentences: "France's block is 29 m long, the most compact all game", "Rice broke 2 lines". All of them are explainable, because each number is a distance between two named players. That is perfect `evidence_ids` material for the fact-checker.
- **A TwinCast:** our simulator knows true positions, so ground truth comes free. Grading the CV tracker on **line height, length and phase agreement** is more meaningful to a judge than raw tracking IoU. Add a "formation recovered" check.
- **D Chalk Talk:** draw the unit lines (the deepest player per unit), the hull and the break arrow coloured through, around or over. These are cheap and look like real telestration.
- **F Graphics Desk cues:** (1) defensive-line break → instant cue; (2) phase banner when a smoothed phase lasts ≥ 1 s; (3) formation change only after hysteresis plus at least a 5-minute segment (SoccerCPD); (4) compactness state flips that persist for 10 s or more (our guess).
- **E Realism Bench:** test the synthetic generator's distributions against the published ranges (length 31–46 m, width 35–48 m, stretch 7–16 m, area ~900 m², larger in possession). This gives a ready-made, cited realism check.
- **Caveat:** if the hackathon's synthetic feed contains only events, line breaks and blocks need defender positions. Either our simulator emits tracking, or we fall back to event-only proxies. Use SkillCorner's phase scheme for the UI because it has 8 short labels; keep FIFA's names for analyst mode.

## Reuse: code & links

Tested with NumPy 2.4 and SciPy 1.17 on toy data. Full runnable demo at `scratchpad/shape_metrics.py` (temporary). Toy output: Blue 4-4-2 units were [4, 4, 2] by both zonal and gap methods. The passes were labelled through (midfield line), around (wing), over (all 3 lines) and none (sideways). Formation matched 4-4-2 / 4-3-3. The timeline switched 4-4-2 → 3-5-2 one window after the true change, because patience = 2.

```python
import numpy as np
from scipy.spatial import ConvexHull
from scipy.optimize import linear_sum_assignment
HALF_LEN = 52.5   # x in [-52.5, 52.5], team attacks +x; y in [-34, 34]

def shape_metrics(xy):                      # xy (10,2) outfielders
    c = xy.mean(0); deepest = xy[:, 0].min()
    return dict(hull_area_m2=ConvexHull(xy).volume,       # 2-D: volume = area
                length_m=xy[:, 0].max() - deepest, width_m=np.ptp(xy[:, 1]),
                def_line_height_m=deepest + HALF_LEN,
                stretch_index_m=np.linalg.norm(xy - c, axis=1).mean())

def compactness_state(a): return "high" if a < 600 else ("low" if a > 900 else "medium")

def units_zonal(xy_def, attack_dir=+1):     # defending team; attacker plays towards attack_dir
    depth = xy_def[:, 0] * attack_dir; lo, hi = depth.min(), depth.max()
    e1, e2 = hi - (hi - lo) / 3, hi - 2 * (hi - lo) / 3
    out = []
    for name, m in [("defensive", depth >= e1), ("midfield", (depth < e1) & (depth >= e2)),
                    ("attacking", depth < e2)]:
        idx = np.flatnonzero(m)
        if idx.size: out.append((name, idx, depth[idx].max() * attack_dir))  # line = deepest
    return out

def detect_line_breaks(s, e, xy_def, ball_z_max=0.0, attack_dir=+1,
                       min_forward=0.0, min_beyond=0.0, over_height=1.67):
    s, e = np.asarray(s, float), np.asarray(e, float)
    if (e[0] - s[0]) * attack_dir < min_forward: return []      # Opta-style: 10.0
    out = []
    for name, idx, lx in units_zonal(xy_def, attack_dir):
        if (s[0] - lx) * attack_dir < 0 and (e[0] - lx) * attack_dir >= min_beyond:  # Opta: 2.0
            y = s[1] + (lx - s[0]) / (e[0] - s[0]) * (e[1] - s[1])   # crossing point
            how = ("over" if ball_z_max > over_height else
                   "around" if not (xy_def[idx, 1].min() <= y <= xy_def[idx, 1].max()) else "through")
            out.append({"unit": name, "line_x": float(lx), "direction": how})
    return out

P = dict(opposed=5.36, high_press=5.07, mid_press=2.28, low_press=1.23,
         high_len=37.70, mid_len=35.31, low_len=31.85)           # Parlak 2023 tuned values
third = lambda x: 1 if x < -HALF_LEN / 3 else (2 if x < HALF_LEN / 3 else 3)

def classify_frame(ball, def_xy, t_since_turnover, ball_dx_since_turnover,
                   pressed_after_loss=False, set_piece=False):
    """coords normalised so the team in possession attacks +x; defenders' own goal at +x."""
    if set_piece: return "set_piece", "defending_set_piece"
    if t_since_turnover <= 49 / 25 and pressed_after_loss: return "attacking_transition", "counter_press"
    if t_since_turnover <= 94 / 25 and ball_dx_since_turnover >= 10.0:   # 10 m is ours
        return "counter_attack", "recovery"
    near = np.linalg.norm(def_xy - ball, axis=1).min()
    L = np.ptp(def_xy[:, 0]); att_unit = third(np.sort(def_xy[:, 0])[:3].mean())
    z = third(ball[0])
    if z == 1:
        ip = "build_up_opposed" if near < P["opposed"] else "build_up_unopposed"
        return ip, ("high_press" if near < P["high_press"] else
                    "high_block" if att_unit == 1 and L < P["high_len"] else "mid_block")
    # mid/low: length checks (P["mid_len"], P["low_len"]) omitted here; add them to flag "stretched" blocks
    if z == 2:
        return "progression", "mid_press" if near < P["mid_press"] else "mid_block"
    return "final_third", "low_press" if near < P["low_press"] else "low_block"

def smooth_labels(lbl, min_len=25):         # drop runs < 1 s into the previous phase
    out, i = list(lbl), 0
    while i < len(out):
        j = i
        while j < len(out) and out[j] == out[i]: j += 1
        if j - i < min_len and i > 0: out[i:j] = [out[i - 1]] * (j - i)
        i = j
    return out

TEMPLATES = {  # (depth, width) units; add more as needed
 "4-4-2": [(0,-3),(0,-1),(0,1),(0,3),(1,-3),(1,-1),(1,1),(1,3),(2,-1),(2,1)],
 "4-3-3": [(0,-3),(0,-1),(0,1),(0,3),(1,-2),(1,0),(1,2),(2,-3),(2,0),(2,3)],
 "4-2-3-1": [(0,-3),(0,-1),(0,1),(0,3),(.8,-1),(.8,1),(1.5,-3),(1.5,0),(1.5,3),(2.2,0)],
 "3-5-2": [(0,-2),(0,0),(0,2),(1,-4),(.8,-1.5),(.8,1.5),(1.2,0),(1,4),(2,-1),(2,1)],
 "5-3-2": [(0,-4),(0,-2),(0,0),(0,2),(0,4),(1,-2),(1,0),(1,2),(2,-1),(2,1)]}

def _norm(p):
    p = np.asarray(p, float); p = p - p.mean(0); r = np.ptp(p, 0)
    return p / np.where(r == 0, 1, r)        # scale to template length/width (EFPI idea)

def match_formation(avg_xy):                 # window-averaged outfield positions
    obs, best = _norm(avg_xy), (None, np.inf, None)
    for name, tpl in TEMPLATES.items():
        C = ((obs[:, None] - _norm(tpl)[None]) ** 2).sum(-1)
        r, c = linear_sum_assignment(C)      # Hungarian / Kuhn-Munkres
        if C[r, c].mean() < best[1]: best = (name, C[r, c].mean(), c)   # c = role per player
    return best

def formation_timeline(windows, margin=0.15, patience=2):   # hysteresis change detector
    cur, streak, out = None, 0, []
    for w in windows:
        obs = _norm(w); cost = {}
        for n, t in TEMPLATES.items():
            C = ((obs[:, None] - _norm(t)[None]) ** 2).sum(-1); r, c = linear_sum_assignment(C)
            cost[n] = C[r, c].mean()
        b = min(cost, key=cost.get)
        if cur is None: cur = b
        elif b != cur and cost[b] < cost[cur] * (1 - margin):
            streak += 1
            if streak >= patience: cur, streak = b, 0
        else: streak = 0
        out.append(cur)
    return out
```

Links:
- Parlak EFI open-source implementation (repo; licence not checked): https://github.com/doganparlak/EFI
- floodlight `CentroidModel` / `ConvexHullModel` / `NearestMateModel` (MIT): https://floodlight.readthedocs.io/en/latest/modules/models/geometry.html
- SoccerCPD code: https://github.com/pientist/soccercpd
- EFPI formation matcher in `unravelsports` (MPL-2.0, see file 10): https://arxiv.org/abs/2506.23843
- SkillCorner open data incl. `*_phases_of_play.csv` (MIT, 10 fps): https://github.com/SkillCorner/opendata

## Sources

- FIFA, Enhanced Football Intelligence Explanation Document v1.0 (11 Oct 2022) — https://www.fifatrainingcentre.com/media/native/world-cup-2022/Enhanced%20Football%20Intelligence%20EN.pdf — accessed 20 Oct 2026
- FIFA Training Centre, EFI metric pages (line breaks; defensive line height and team length; receptions; forced turnovers; phases of play; PDFs index) — https://www.fifatrainingcentre.com/en/fwc2022/efi-metrics/efi-metric--line-breaks.php — accessed 20 Oct 2026
- FIFA Training Centre, The FIFA Football Language / Offering to receive — https://fifatrainingcentre.com/en/game/performance-analysis/football-language-analysis/the-fifa-football-language.php — accessed 20 Oct 2026
- FIFA, "FIFA to introduce enhanced football intelligence at FIFA World Cup 2022" — https://inside.fifa.com/innovation/media-releases/fifa-to-introduce-enhanced-football-intelligence-at-fifa-world-cup-2022-tm — accessed 20 Oct 2026
- D. Parlak, "An Open-Source Implementation of FIFA's Enhanced Football Intelligence", MSc thesis, Univ. Zurich, 2023 — https://capuana.ifi.uzh.ch/publications/PDFs/24098_An_Open_Source_Implementation_of_FIFA_s_Enhanced_Football_Intelligence.pdf — accessed 20 Oct 2026
- The Analyst, "Opta Vision stats: tracking data in the Premier League" — https://theanalyst.com/articles/opta-vision-stats-tracking-data-premier-league — accessed 20 Oct 2026
- Stats Perform, "How impactful are line-breaking passes?" (403 to our fetcher; thresholds seen via search excerpt only) — https://statsperform.com/resource/how-impactful-are-line-breaking-passes — accessed 20 Oct 2026
- SkillCorner, Phases of Play CSV Specifications (16 Feb 2025) — https://26560301.fs1.hubspotusercontent-eu1.net/hubfs/26560301/Guides/Phases%20of%20Play/20250216%20-%20Phases%20of%20Play%20CSV%20Specifications.pdf — accessed 20 Oct 2026
- SkillCorner, Game Intelligence line-breaking passes — https://skillcorner.com/blog/gi-line-breaking — accessed 20 Oct 2026
- L. Shaw & M. Glickman, "Dynamic analysis of team strategy in professional football", Barça Sports Analytics Summit 2019 — https://www.sportperformanceanalysis.com/s/Dynamic-analysis-of-team-strategy-in-professional-football-By-Laurie-Shaw-And-Mark-Glickman.pdf — accessed 20 Oct 2026
- H. Kim et al., "SoccerCPD: Formation and Role Change-Point Detection…", KDD 2022 — https://arxiv.org/abs/2206.10926 — accessed 20 Oct 2026
- A. Bialkowski et al., "Large-Scale Analysis of Soccer Matches using Spatiotemporal Tracking Data", IEEE ICDM 2014 (method as summarised by SoccerCPD) — https://authors.library.caltech.edu/records/4v1fx-ymm70 — accessed 20 Oct 2026
- J. Bekkers, "EFPI: Elastic Formation and Position Identification…", 2025 — https://arxiv.org/abs/2506.23843 — accessed 20 Oct 2026
- M. Rico-González et al., "Reference values for collective tactical behaviours based on positional data in professional football matches: a systematic review", Biology of Sport 39(1):101-114, 2022 — https://www.termedia.pl/Reference-values-for-collective-tactical-behaviours-based-on-positional-data-in-professional-football-matches-a-systematic-review,78,43095,0,1.html — accessed 20 Oct 2026
- floodlight geometry models docs — https://floodlight.readthedocs.io/en/latest/modules/models/geometry.html — accessed 20 Oct 2026
- SkillCorner open data README — https://github.com/SkillCorner/opendata — accessed 20 Oct 2026
