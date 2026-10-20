# 10 — Pitch control, space occupation and off-ball value (implementable)

_Accessed/compiled: 20 Oct 2026 · Priority area: Interpret-stage spatial metrics and Render-stage space overlays, for 02 Decoy Credit, 01 Ghost Team, A TwinCast, D Chalk Talk and C One Number_

## TL;DR

- There are three families of model. **Voronoi / dominant region** says the nearest player (or the one who arrives first) owns the cell. **Spearman** works from time to intercept: a logistic on arrival time, then a control-rate ODE integrated over time. **Fernández & Bornn (F&B)** gives each player a bivariate-normal "influence" stretched by speed, and takes a logistic of the team sums. Here (F&B) means Fernández & Bornn.
- **Our measurement, one laptop CPU, NumPy only, 22 players, 50×32 grid:** F&B took **1.3 ms** per frame. A "TTI-lite" logistic with no integration took **1.2 ms**. The full Spearman integration, vectorised over the grid, took **30 ms**. The same integration looped cell by cell took **~1.5 s**. TTI-lite matches the full Spearman surface closely: correlation 0.95, mean |diff| 0.07, and the same team wins 96% of cells. **Any of the three runs live at 25 fps in Python.**
- **"Space created by player i"** is a counterfactual difference. Compute pitch control with the real run, then again with the runner frozen (his own gain). Then compute it without him at t0 and t1, which shows space freed for teammates by defenders who moved (decoy gain). Optionally weight cells by a value surface. Code is below and runs in 3-5 ms (ours).
- **EPV × pitch control** (Shaw's `Metrica_EPV.py`) and **OBSO** (Spearman 2018) turn "space" into "value". The FoT `EPV_grid.csv` has no stated provenance, so **do not ship it.** Use the xT grid fitted on our synthetic matches (file 08) instead.
- **Licences:** LaurieOnTracking MIT, floodlight MIT, mplsoccer MIT, kloppy BSD-3, unravelsports MPL-2.0, anenglishgoat/Metrica-pitch-control **AGPL-3.0** (avoid copying from it), open-starlab/spaceEval MIT.

## Findings

### 1. The three model families

| Model | Formula (plain notation) | Pros | Cons | Cost (ours, 50×32) |
|---|---|---|---|---|
| **Voronoi / dominant region** (Taki & Hasegawa 1996-2000; floodlight `DiscreteVoronoiModel`) | Each cell goes to the nearest player (Euclidean). The `taki_hasegawa` variant uses the player who reaches it first given velocity and max acceleration (floodlight default 4.2 m/s²). `fujimura_sugihara` adds drag (vmax 7.8 m/s, α 1.3). | Easy to explain, binary, gives per-player areas | Euclidean version ignores speed and direction; hard edges | Euclidean: trivial. floodlight warns its motion models are "much more expensive" |
| **Spearman (2016-2018) / Shaw FoT** | `tti_j(r) = reaction + ‖r − (p_j + v_j·reaction)‖ / vmax`. Arrival prob `f_j(T) = 1/(1+exp(−π/√3/σ·(T − tti_j)))`. Control ODE `dPPCF_j/dT = (1 − Σ_k PPCF_k)·f_j(T)·λ_j`, integrated from ball arrival time. Shaw defaults: vmax 5, reaction 0.7 s, σ 0.45, λ 4.3, λ_GK 3×, ball speed 15 m/s, dt 0.04 s, max 10 s, tol 0.01, grid 50×32 on 106×68. | Physically meaningful (it is a probability of winning the ball), includes ball travel time, the basis of OBSO and EPV-added | The integral is slow if looped per cell; goalkeepers "own" a lot of space | Vectorised 30 ms; per-cell loop ~1.5 s |
| **TTI-lite** (ours; same TTI, no integral) | `PC_att(r) = 1/(1+exp(−π/√3/σ·(T_def(r) − T_att(r))))`, where `T_team` is a soft-min of `tti` over the team's players | 25× cheaper than the integral, 96% cell agreement with it | Drops λ and ball flight time, so not a true probability of control | 1.2 ms |
| **Fernández & Bornn 2018** | Per player: `μ = p + 0.5·v`; `Σ = R·S·S·R⁻¹`, with R the rotation to the velocity direction. `S = diag((1+Srat)·Rᵢ/2, (1−Srat)·Rᵢ/2)`, with `Srat = (speed/13)²`. Radius `Rᵢ = min(4 + d_ball³/(18³/6), 10)` m. Influence `Iᵢ(r) = N(r; μ, Σ)/N(pᵢ; μ, Σ)`. Team: `PC(r) = 1/(1+exp(−(Σ_att I − Σ_def I)))`. | Very cheap, smooth, players closer to the ball get tighter influence, intuitive "bubbles" | Not a probability of winning the ball. Far from players it sits at 0.5 ("nobody's"). The radius curve isn't printed in the paper. | 1.3 ms |

Notes on F&B:
- The numbers 13 m/s, 4-10 m and `18³/6` come from an implementation that follows the paper's appendix (Thomson, anenglishgoat). Its comment says the radius function "is not specified in the paper". Martens et al. (2021) confirm the radius range [4, 10] m and that the curve is only plotted. They also print Σ as R·V·V·R⁻¹ and normalise by the peak density, whereas Thomson normalises at the player's own position (small difference).
- Thomson's code computes the rotation with `arccos(vx/|v|)`. That loses the sign of vy, so players running "down" get rotated "up". We use `arctan2`.
- F&B also define a learned **pitch value** (defensive-influence network × distance-to-goal). Space quality = PC × PV. They measure space occupation and generation gains for players (the exact SOG/SGG definitions are unverified; the PDF timed out). Martens et al. (CC BY) reformulate space generation as Σ over the grid of max(SQᵢ − SQⱼ, 0).

**Compute cost in context.** Our timings (Intel Family 6 Model 170 laptop, Python 3.12.10, NumPy 2.4.1, random 11v11 frames, mean of 200 runs) are as follows. On a 50×32 grid: F&B 1.34 ms, TTI-lite 1.16 ms, Spearman vectorised 30.1 ms. On a 105×68 (1 m) grid: 4.85 ms, 5.95 ms and 208 ms. Our per-cell loop of the same Spearman integral took 1,482 ms, and the vectorised version stays within 0.008 of it. That loop mimics the structure of Shaw's reference, but it is **not** a timing of his code. A third party reports "about 30 seconds for a full game" on a Colab GPU with PyTorch (anenglishgoat README, unverified). Bekkers' Pressing Intensity (unravelsports) uses the same Spearman TTI plus logistic idea (σ 0.45, reaction 0.7 s) on player-to-player matrices. unravelsports has **no** pitch-control surface model; we checked the README.

### 2. From space to value: EPV-added and OBSO

- **EPV-added (Shaw, `Metrica_EPV.py`).** `EEPV = PC_att(r) × EPV(r)`. A pass adds `PC(end)·EPV(end) − PC(start)·EPV(start)`. `find_max_value_added_target` takes the argmax of `PC_surface × EPV_grid`, which is the best pass "on" right now. The grid is 32×50 and is flipped for direction of play. Its source is not documented in the repo, so its provenance is unclear (probably real-match derived; unverified).
- **OBSO (Spearman 2018, "Beyond Expected Goals", SSAC).** `P(goal) = Σ_r P(score|r) · P(control|r) · P(next ball event at r)`. The control term is the potential pitch control field above, which is zero before the ball can arrive. The transition term is a 2-D Gaussian around the ball, in some reimplementations modulated by PC^α with α = 0 in the original code. The score term is an xG-by-location grid. An attacker's off-ball value is the OBSO mass in cells he controls. We found this decomposition via open restatements (open-starlab/spaceEval paper, arXiv 2603.06585), because the primary PDF was not reachable. The exact σ and α values are unverified.
- **Timing counterfactuals (CRSV, Iwashita et al. 2025, reimplemented in spaceEval).** Shift only the start of a receiver's run by ±ξ frames, keep everyone else's real trajectory, and recompute the space metric. `V_timing = V(0) − max_{ξ≠0} V(ξ)`. This is the cleanest published recipe for "what if he'd gone earlier?", which is our Ghost Team idea.

### 3. "Space created" by a run (Decoy Credit, Ghost Team)

You need two counterfactuals (code below):
1. **Own gain**: PC at t1 with the real run, minus PC at t1 with runner i frozen at his t0 spot. This is the space he moved into.
2. **Decoy gain**: team PC **without player i** at t1, minus the same at t0. This is space that opened for teammates because defenders moved. Caveat: they may have moved for other reasons. Strengthen the attribution by also requiring that the defenders who moved were the ones nearest i's path.

Weight both by a value grid (synthetic xT/EPV) to get "valuable m²". In our toy run (attacker sprints 6 m and a defender follows 4 m), F&B gave 22 m² own and 21 m² decoy. TTI-lite gave 87 m² and 193 m². **Absolute m² depend heavily on the model, so only compare numbers from the same model.**

### 4. Visualisation and broadcast precedent

- **2-D pitch:** mplsoccer (MIT) `Pitch(pitch_type='custom', pitch_length=105, pitch_width=68)`, then `ax.pcolormesh` of the grid. Its own `bin_statistic`/`heatmap` is for binning events, not precomputed surfaces.
- **Browser:** send the 50×32 grid as 1,600 bytes (uint8) per update and draw it as a `THREE.DataTexture` with `LinearFilter` on a 105×68 plane. That gives free bilinear smoothing and costs about nothing on the GPU. In **A TwinCast** the 3-D camera is known, so no homography is needed: the plane sits on the pitch in the same scene.
- **Broadcast frame (real or rendered video):** use the CV calibration homography H (pitch m → pixels) and inverse-map each pixel to a grid cell. On a 1280×720 frame, a naive per-frame inverse warp took **91 ms** (ours). Precomputing the pixel→cell lookup table once per camera pose brings it to **15 ms** (ours). Fade contested cells (PC ≈ 0.5) to transparent so that only clear ownership shows, and use team colours.
- **Precedent:** GolStats' GVR tool ran **Laurie Shaw's pitch-control code** inside a 3-D replay. Pundits used it live on Univision during the 2018 World Cup, with plays rebuilt within about 2 minutes. Pundits could also **drag a player and recompute pitch control**, which is our Ghost Team idea on air. Spiideo sells automatic bird's-eye pitch-control views for coaches. We found **no** Bundesliga Match Fact for pitch or space control. The nearest are Match Momentum, Attacking Zones and Most Pressed Player. PL "Data Zone" (Second Spectrum / Genius) lists pitch maps and speeds, but we found no documented live space-control graphic (unverified either way).

## So what for us

- **Interpret stage, for 02 Decoy Credit:** per run (detected when speed exceeds a threshold for at least 1 s), compute `own_gain` and `decoy_gain` with **TTI-lite** (closest to Spearman, so "% chance we'd win the ball there" is honest wording), weighted by our synthetic xT. Emit a cue when `decoy_gain` exceeds a threshold, with `evidence_ids` = run id + the defender ids who moved. Casual text: "His run dragged 2 defenders and opened 140 m² for Saka."
- **01 Ghost Team:** use the CRSV-style counterfactual (shift the run ±0.5 s, or move the player to a "ghost" spot). Show real vs ghost PC side by side, plus `Δ value`.
- **A TwinCast:** compute PC from ground truth **and** from CV tracks. Mean |ΔPC| is another tracking-quality number for the realism report (pairs with xPass in file 08). Render the surface as a translucent texture on the Three.js pitch, then composite it.
- **D Chalk Talk / F Graphics Desk:** "show me the space" means a 2-3 s PC overlay on the paused frame. "Best option" means argmax(PC × xT), drawn as a target ring (Shaw's `find_max_value_added_target` idea).
- **C One Number:** "% of the final third controlled" (mean PC over x > 70 m) is a single, smooth, explainable number.
- **Budget:** compute PC at 5-10 Hz (not 25), smooth over 3 frames, and send uint8 grids over Web PubSub. Each update is 1.6 KB.

## Reuse: code & links

**Vectorised pitch control (F&B and TTI-lite).** Tested by us. Coordinates are in metres, origin bottom-left.

```python
import numpy as np
L, W = 105.0, 68.0

def make_grid(nx=50, ny=32):
    xs, ys = (np.arange(nx) + .5) * L / nx, (np.arange(ny) + .5) * W / ny
    gx, gy = np.meshgrid(xs, ys)                         # (ny, nx)
    return np.stack([gx.ravel(), gy.ravel()], 1), (ny, nx)

def fb_influence(grid, pos, vel, ball, vmax=13.0):
    """Fernandez & Bornn 2018 influence, (N players, G cells)."""
    pos, vel = np.asarray(pos, float), np.asarray(vel, float)
    th = np.arctan2(vel[:, 1], vel[:, 0])                 # arctan2, not arccos (keeps sign)
    d = np.linalg.norm(pos - np.asarray(ball, float), axis=1)
    R = np.minimum(4 + d**3 / (18**3 / 6), 10)            # radius 4..10 m vs distance to ball
    srat = np.minimum((np.linalg.norm(vel, axis=1) / vmax)**2, .95)
    s1, s2 = (1 + srat) * R / 2, (1 - srat) * R / 2      # along / across the run
    mu = pos + .5 * vel
    c, s = np.cos(th)[:, None], np.sin(th)[:, None]
    def maha(px, py):                                    # px,py broadcast against (N,1)
        dx, dy = px - mu[:, :1], py - mu[:, 1:]
        u, v = c * dx + s * dy, -s * dx + c * dy
        return (u / s1[:, None])**2 + (v / s2[:, None])**2
    m_grid = maha(grid[None, :, 0], grid[None, :, 1])
    m_self = maha(pos[:, :1], pos[:, 1:])                # density at the player's own spot
    return np.exp(-.5 * (m_grid - m_self))

def pitch_control_fb(grid, att_pos, att_vel, def_pos, def_vel, ball):
    z = fb_influence(grid, att_pos, att_vel, ball).sum(0) - fb_influence(grid, def_pos, def_vel, ball).sum(0)
    return 1 / (1 + np.exp(-z))                          # P(attacking team controls cell)

def time_to_intercept(grid, pos, vel, vmax=5.0, reaction=0.7):   # Shaw/FoT defaults
    r0 = np.asarray(pos, float) + np.asarray(vel, float) * reaction
    return reaction + np.linalg.norm(grid[None] - r0[:, None], axis=2) / vmax

def pitch_control_tti(grid, att_pos, att_vel, def_pos, def_vel, ball=None, sigma=.45, tau=.3):
    """TTI-lite: logistic on the difference of team soft-min arrival times (no integral)."""
    def team_t(t):
        m = t.min(0); return m - tau * np.log(np.exp(-(t - m) / tau).sum(0))
    k = np.pi / np.sqrt(3) / sigma
    dt = team_t(time_to_intercept(grid, def_pos, def_vel)) - team_t(time_to_intercept(grid, att_pos, att_vel))
    return 1 / (1 + np.exp(-k * dt))
```

**Space created by player i** (Decoy Credit / Ghost Team). Tested by us, 3-5 ms per call.

```python
def space_created(grid, f0, f1, i, value=None, model=pitch_control_tti):
    """f0, f1: dicts att_pos, att_vel, def_pos, def_vel, ball at t0 and t1 (1-2 s apart)."""
    area = L * W / len(grid)
    w = np.ones(len(grid)) if value is None else np.asarray(value, float)   # e.g. synthetic xT per cell
    pc = lambda f, ap=None, av=None: model(grid, f["att_pos"] if ap is None else ap,
                                           f["att_vel"] if av is None else av, f["def_pos"], f["def_vel"], f["ball"])
    ap = np.array(f1["att_pos"], float); ap[i] = f0["att_pos"][i]           # runner frozen at t0
    av = np.array(f1["att_vel"], float); av[i] = 0
    delta = pc(f1) - pc(f1, ap, av)                                         # his own gain
    keep = [j for j in range(len(f0["att_pos"])) if j != i]
    drop = lambda f: {**f, "att_pos": np.asarray(f["att_pos"])[keep], "att_vel": np.asarray(f["att_vel"])[keep]}
    freed = pc(drop(f1)) - pc(drop(f0))                                     # opened for teammates
    return {"own_gain": float((delta.clip(0) * w).sum() * area),
            "decoy_gain": float((freed.clip(0) * w).sum() * area),
            "delta_grid": delta}
```

For a full-fidelity Spearman surface, vectorise Shaw's loop over all cells at once. Loop `T = t_ball + n·dt`. Each step, `rem = 1 − Σpa − Σpd`, then `pa += rem·f_att(T)·λ·dt` (and the same for defenders), and stop when `rem.max() < 0.01`. That took 30 ms on our machine.

**mplsoccer plot.** Not run by us, because mplsoccer is not installed here. The identical `pcolormesh` call was run on plain matplotlib.

```python
from mplsoccer import Pitch
grid, shp = make_grid()
pc = pitch_control_tti(grid, att, att_v, dfn, dfn_v)
pitch = Pitch(pitch_type='custom', pitch_length=105, pitch_width=68, pitch_color='#1d6b35', line_color='white')
fig, ax = pitch.draw(figsize=(10, 6.6))
ax.pcolormesh(grid[:, 0].reshape(shp), grid[:, 1].reshape(shp), pc.reshape(shp),
              cmap='RdBu_r', vmin=0, vmax=1, alpha=.55, shading='auto', zorder=1)
pitch.arrows(att[:, 0], att[:, 1], att[:, 0] + att_v[:, 0], att[:, 1] + att_v[:, 1], ax=ax, color='red', width=1.5)
pitch.scatter(att[:, 0], att[:, 1], ax=ax, c='red', s=90, ec='white', zorder=3)
pitch.scatter(dfn[:, 0], dfn[:, 1], ax=ax, c='blue', s=90, ec='white', zorder=3)
```

**Broadcast overlay via homography.** Tested by us: 15 ms per 720p frame with the lookup table.

```python
def make_lut(H, h, w, shp):                 # once per camera pose; H maps pitch metres -> pixels
    ny, nx = shp
    uu, vv = np.meshgrid(np.arange(w) + .5, np.arange(h) + .5)
    p = np.linalg.inv(H) @ np.stack([uu.ravel(), vv.ravel(), np.ones(uu.size)])
    x, y = p[0] / p[2], p[1] / p[2]
    on = ((x >= 0) & (x < L) & (y >= 0) & (y < W)).reshape(h, w)
    idx = (np.clip((y / W * ny).astype(int), 0, ny - 1) * nx + np.clip((x / L * nx).astype(int), 0, nx - 1)).reshape(h, w)
    return idx, on

t = np.linspace(0, 1, 256); PAL = np.zeros((256, 4), np.uint8)          # defender red -> attacker blue
PAL[:, 0], PAL[:, 1], PAL[:, 2] = 220 - 190 * t, 30 + 60 * t, 40 + 180 * t
PAL[:, 3] = .45 * np.abs(t - .5) * 2 * 255                              # contested cells transparent

def overlay(pc, idx, on):                   # -> (h, w, 4) RGBA "fill"; alpha channel doubles as "key"
    out = PAL[(pc * 255).astype(np.uint8)[idx]]; out[~on, 3] = 0; return out
```

Browser (Three.js) sketch (not run by us): `tex = new THREE.DataTexture(u8rgba, 50, 32); tex.magFilter = THREE.LinearFilter;` on a `PlaneGeometry(105, 68)` rotated −90° about x, with `transparent: true`. Set `tex.needsUpdate = true` after each grid message. Check the row orientation against your pitch axes.

**Links**
- LaurieOnTracking (MIT): https://github.com/Friends-of-Tracking-Data-FoTD/LaurieOnTracking. Pitch-control video: https://www.youtube.com/watch?v=5X1cSehLg6s. EPV video: https://www.youtube.com/watch?v=KXSLKwADXKI
- floodlight `DiscreteVoronoiModel` (MIT): https://floodlight.readthedocs.io/en/latest/modules/models/space.html
- unravelsports PressingIntensity (MPL-2.0): https://unravelsports.readthedocs.io/en/latest/_modules/unravel/soccer/models/pressing_intensity.html
- kloppy (BSD-3, data loading only, no pitch control): https://github.com/PySport/kloppy
- open-starlab spaceEval (MIT; OBSO/CRSV paper): https://github.com/open-starlab/spaceEval

## Sources

- Laurie Shaw, `Metrica_PitchControl.py` — https://github.com/Friends-of-Tracking-Data-FoTD/LaurieOnTracking/blob/master/Metrica_PitchControl.py — accessed 20 Oct 2026
- Laurie Shaw, `Metrica_EPV.py` — https://github.com/Friends-of-Tracking-Data-FoTD/LaurieOnTracking/blob/master/Metrica_EPV.py — accessed 20 Oct 2026
- LaurieOnTracking README and LICENSE (MIT, 2021) — https://github.com/Friends-of-Tracking-Data-FoTD/LaurieOnTracking — accessed 20 Oct 2026
- Fernández & Bornn, "Wide Open Spaces" (SSAC 2018), PDF (timed out; details via the next three sources) — https://www.lukebornn.com/papers/fernandez_ssac_2018.pdf — accessed 20 Oct 2026
- Will Thomson (anenglishgoat), Metrica-pitch-control (AGPL-3.0; F&B appendix implementation) — https://github.com/anenglishgoat/Metrica-pitch-control — accessed 20 Oct 2026
- Martens, Dick & Brefeld, "Space and Control in Soccer", Frontiers 2021 (CC BY) — https://pmc.ncbi.nlm.nih.gov/articles/PMC8322620/ — accessed 20 Oct 2026
- Goalside Analytics, "A history of pitch control" (secondary) — https://www.getgoalsideanalytics.com/everything-you-need-to-know-about-pitch-control/ — accessed 20 Oct 2026
- Spearman, "Beyond Expected Goals" (SSAC 2018), primary PDF not reached; OBSO equations from: "Right Move, Right Time" (open-starlab spaceEval paper, CC BY 4.0) — https://arxiv.org/abs/2603.06585 — accessed 20 Oct 2026
- "Space evaluation at the starting point of soccer transitions" (OBSO Gaussian transition / α note, via search snippet) — https://arxiv.org/abs/2505.14711 — accessed 20 Oct 2026
- open-starlab/spaceEval (MIT) — https://github.com/open-starlab/spaceEval — accessed 20 Oct 2026
- floodlight space models docs — https://floodlight.readthedocs.io/en/latest/modules/models/space.html — accessed 20 Oct 2026; repo (MIT) — https://github.com/floodlight-sports/floodlight — accessed 20 Oct 2026
- Bekkers, "Pressing Intensity" (arXiv 2501.04712) — https://arxiv.org/abs/2501.04712 — accessed 20 Oct 2026
- unravelsports repo (MPL-2.0) — https://github.com/UnravelSports/unravelsports — accessed 20 Oct 2026
- kloppy repo (BSD-3) — https://github.com/PySport/kloppy — accessed 20 Oct 2026
- mplsoccer repo (MIT) — https://github.com/andrewRowlinson/mplsoccer — accessed 20 Oct 2026; pitch types — https://mplsoccer.readthedocs.io/en/latest/gallery/pitch_setup/plot_pitches.html — accessed 20 Oct 2026; heatmaps — https://mplsoccer.readthedocs.io/en/latest/gallery/pitch_plots/plot_heatmap.html — accessed 20 Oct 2026
- Sámano et al. (GolStats), "GVR: an intuitive tool for the visualization…" (Barça Sports Tomorrow 2020) — https://sportstomorrow.fcbarcelona.com/wp-content/uploads/2020/11/GVR_An_intuitive_tool_for_the_visualization_and_easy_interpretation_of_advanced_exploration_methods_for_the_analysis_of_soccer_matches.pdf — accessed 20 Oct 2026
- Spiideo, "Soccer pitch control" — https://www.spiideo.com/news/soccer-pitch-control/ — accessed 20 Oct 2026
- AWS, "Bundesliga Match Fact Match Momentum" (search result) — https://aws.amazon.com/blogs/media/bundesliga-match-fact-match-momentum-revealing-the-games-invisible-pulse — accessed 20 Oct 2026
- SVG Europe / Broadcast Now on PL Data Zone (search results) — https://www.sportsvideo.org/2023/10/05/premier-league-productions-partners-with-genius-sports-to-deliver-premier-league-data-zone/ — accessed 20 Oct 2026
