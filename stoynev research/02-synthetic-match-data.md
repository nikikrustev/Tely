# 02 — Generating synthetic football match events and tracking data

_Accessed/compiled: 20 Oct 2026 · Priority area: Ingest (synthetic data source) + realism checks_

## TL;DR

- **Schema:** use the **Common Data Format (CDF)** (Anzer et al., arXiv 2505.15820) as our wire format. It covers both events and tracking, uses JSON Lines and metres with the origin at the centre spot, declares frame rate in metadata, and has an MIT-licensed validator on PyPI. Also provide a **SPADL** export (socceraction, MIT) so xT/VAEP-style models work without extra effort.
- **No off-the-shelf generator fits.** Google Research Football (Apache-2.0) is now **archived** (read-only since Aug 2026). rSoccer is robot soccer, not human football. SoccER (MIT) last changed in 2020. We should write our own: an **event-first possession chain**, then **derive 25 Hz tracking** from it.
- **Real samples are for calibration only.** SkillCorner opendata is MIT. Metrica has no licence file, only an "acknowledge the source" request. StatsBomb open data **forbids commercial exploitation and redistribution**. PFF FC WC2022 is behind a form and its terms are not stated. None of these can be shown as match data in the demo.
- **Realism targets (cited):** 2.93 goals/match (PL 2024/25), ~893 passes/match, ~26 shots/match, top speeds of 35–37.4 km/h, outfield distance of 8.5–12.9 km per 90, and a sprint threshold of 25 km/h.
- A seeded 53-line toy generator (below), averaged over 300 seeds, lands near these targets: ~880 passes, 84.7% completion, ~28 shots, ~3.2 goals per 90. The tracking it derives is still too static (~4 km per player per 90). That gap is exactly what the Realism Bench should report.

> **Correction (from [33](33-synthetic-possession-value.md)):** the toy generator below has two bugs. (1) After a missed shot the goal kick is placed at the shooter's end, so the opponent restarts 5.5 m from goal; this roughly doubles goals and explains the "~3.2 goals per 90". (2) Passes aimed off the pitch are clamped onto the goal line, and shots from there get xG ≈ 0.89. With both fixed, goals drop to ~1.58 per match, so xG and shot rate need re-tuning toward the cited 2.93. The fix is in file 33.

## Findings

### 1. Event/tracking schemas worth copying

| Schema | What it is | Coordinates | Licence / activity |
|---|---|---|---|
| **StatsBomb open data** (events v4.0.0 spec, 360 frames v1.0.0) | Rich JSON event arrays: `id`, `index`, `period`, `timestamp` (ms), `minute`, `second`, `type{id,name}`, `possession`, `possession_team`, `location`, plus type-specific objects (pass, shot with `freeze_frame`, carry `end_location`) | 120 × 80 yard pitch (unverified here: the spec's coordinate appendix is an image) | `LICENSE.pdf` user agreement: no redistribution, no commercial exploitation, logo attribution required. Repo pushed 2026-09-07. |
| **SPADL** (socceraction) | 12 columns: `game_id, period_id, seconds, player, team, start_x, start_y, end_x, end_y, action_type, result, bodypart`. 22 action types (pass, cross, shot, tackle, interception, take-on, dribble, keeper_save…). Results: success/fail/offside/owngoal/yellow/red | 105 × 68 m, origin bottom-left | MIT; pushed 2026-10-18 |
| **Atomic-SPADL** | Removes `result`. Uses `x, y, dx, dy`. Adds `receival`, `interception`, `out`, `goal`. A pass becomes two actions (give + receive) | same | MIT |
| **CDF** (Anzer et al. 2025; RB Leipzig, DFB, FIFA, KU Leuven…) | Five data types (match sheet, video, event, tracking, meta). JSONL. Tracking frame: `frame_id`, `timestamp` (UTC), `period`, `match.id`, team ids, players `id,x,y`, `ball x,y,z`, plus optional `ball_status`, `ball_poss_team_id`. Events: `type` ∈ {shot, pass, referee, misc}, with `sub_type`, `is_successful`, `outcome_type`, `player_id`, `receiver_id`, `x,y,x_end,y_end`, `body_part`, `related_event_ids` | Metres, origin at centre, ±L/2, ±W/2, 3 decimals. fps is declared in `meta/tracking/fps` (example: 25). Home plays left to right | Paper describes v1.0.0. The validator (`common-data-format-validator`, MIT, v0.1.1, Sep 2026) targets "CDF v0.3.2", so the two version numbers disagree. IEEE P3715 standard project is active. |
| **kloppy** data model | Vendor-neutral `EventDataset`/`TrackingDataset`/`Frame`, coordinate transforms. Loaders for StatsBomb, Metrica, SkillCorner, PFF, TRACAB, etc. | Any; can transform between systems | BSD-3-Clause, v3.19.1 (2026-10-03). A `to_cdf` exporter exists only as **open PRs** (#502, #519), not released. |

**Recommendation:** use **CDF-style JSONL** as the canonical format, with events and tracking sharing one clock and one coordinate system. Make it machine-checkable with the CDF validator. Add a trivial converter to SPADL (shift by +52.5/+34, map types) for analytics libraries. Copy StatsBomb only for *ideas* (its `possession` counter and pressure/counterpress flags are useful to emulate). Do not copy its data.

> **Correction (20 Oct 2026, from [26](26-cdf-spadl-data-tooling.md)):** the two JSON examples below do **not** pass the CDF v0.3.2 validator. Event fields must sit under `"event"`, `"meta": {"is_synced": ...}` is required, tracking uses `ball.status` (boolean) and `ball.poss_team_id`, `frame_id` starts at 0, and extra fields like `time_s` fail in `extreme` mode. Use the validated examples in file 26.

Minimal event (CDF-style; our extra fields such as `xg` and `time_s` are allowed because CDF permits optional fields):

```json
{"match":{"id":"syn-0001"},"event":{"id":"e00042"},"time":"2026-10-20T15:03:12.480Z","time_s":192.48,
 "period":"first_half","type":"pass","sub_type":"none","is_successful":true,"outcome_type":"successful",
 "team_id":"home","player_id":"h8","receiver_id":"h10","receiver_time":"2026-10-20T15:03:13.610Z",
 "x":-4.2,"y":11.0,"x_end":17.9,"y_end":5.3,"body_part":"right_foot","related_event_ids":[],"xg":null}
```

Minimal 25 Hz tracking frame (one JSONL line every 40 ms; field nesting should be checked against the validator, unverified):

```json
{"frame_id":4812,"timestamp":"2026-10-20T15:03:12.480Z","period":"first_half","match":{"id":"syn-0001"},
 "teams":{"home":{"id":"home","players":[{"id":"h1","x":-49.8,"y":0.6},{"id":"h8","x":-4.2,"y":11.0}]},
          "away":{"id":"away","players":[{"id":"a4","x":3.1,"y":9.7}]}},
 "ball":{"x":-4.0,"y":11.0,"z":0.11},"ball_status":"alive","ball_poss_team_id":"home"}
```

### 2. Existing simulators and generators

| Option | Events? | x/y tracking? | Verdict |
|---|---|---|---|
| **Google Research Football** (gfootball) | Derivable | Yes: raw obs gives `ball [x,y,z]`, `left_team`/`right_team` positions, x ∈ [-1,1], y ∈ [-0.42,0.42]. Replays via `--dump_full_episodes` | Apache-2.0, **archived 19 Aug 2026**. Heavy C++ engine with RL agents. Radke & Tilbury (arXiv 2503.19809, 2025) used it to produce "representative" tracking plus extracted events (code link not verified). Useful as an idea, risky as a dependency. |
| **SoccER** (Morra et al., SoftwareX 2020) | Yes: auto-labelled goals, passes, crosses, shots, fouls | Yes, from a modified Gameplay Football engine | MIT, last push 2020-10. Published dataset: 500 min, >1M events. Good proof that "engine → ground-truth events" works, but stale. |
| **rSoccer** | No | Robot positions | MIT, pushed 2026-02. Built for IEEE VSS / RoboCup SSL robot RL. **Not human football**, so skip it. |
| GitHub "football simulators" (e.g. AllenThomasDev/Football-Simulator, Apache-2.0, 2023; small random-event games) | Score/minute level | No | League/result simulators, not spatial. Skip. |
| **Markov / possession chain** (Rudd 2011 → Singh's xT grid; arXiv 2511.09457 studies grid-size trade-offs via simulation) | Yes, by construction | Only start/end zones | The right core for us: transparent, seedable, tunable to cited rates. Memoryless is a known simplification. |
| **Poisson / Dixon-Coles goal models** (penaltyblog, MIT, pushed 2026-10-19) | Scorelines and rates only | No | Use to set per-team goal/shot intensity for a "fixture", then let the chain produce the events. A Gillespie-style exponential gap between events gives a natural clock. |
| **Large Events Models / LLMs** (arXiv 2402.06815, 2402.06820; ScoutGPT 2603.15212) | Yes: next-event type, outcome, location, time | No | Transformers trained on real Wyscout/K League data. A general LLM prompted to "write a match" has **no physical consistency, is hard to seed reproducibly, and is slow and costly per event**. Use LLMs to *explain*, not to *generate* the ground truth. |

### 3. Public tracking samples (reference and parser testing only)

The hackathon requires synthetic data, so these are only for calibration (distributions, speeds) and for testing our parsers. We never ship them as the match feed or show them on screen.

| Dataset | Content | Licence / terms | OK for calibration? |
|---|---|---|---|
| **Metrica Sports sample-data** | 3 anonymised games, 25 fps (per databallpy docs and papers), CSV + EPTS/JSON, 0–1 coordinates on 105 × 68 m | No licence file. README asks to "acknowledge the source" for public use. Last push 2021 | Yes for internal calibration with attribution. Legally ambiguous for redistribution. |
| **SkillCorner opendata** | 10 A-League 2024/25 matches, broadcast tracking at 10 fps (body pose at 25 fps on Hugging Face), dynamic events, phases of play | MIT, credit requested. Pushed 2026-09-14 | Yes. The cleanest licence. |
| **StatsBomb open data** (events + 360) | Many competitions | User agreement: **no commercial exploitation, no redistribution**, logo attribution | Only to read the schema and look at distributions privately. **Flag: do not embed or redistribute.** |
| **PFF FC 2022 World Cup** | 64 matches, broadcast tracking (`.jsonl.bz2`) + events + grades | Access via form. **No licence stated on the page (unverified)** | Only after reading the terms in the download. |

### 4. Realism ranges (citable)

| Metric | Value | Source |
|---|---|---|
| Goals per match | 2.93 (1,115 in 380, PL 2024/25) | Wikipedia season page |
| Passes per match (both teams) | 893.4 (2024/25), 941.0 (2023/24) | Opta Analyst, 16 Jan 2026 |
| Shots per 90 (both teams) | 25.3–27.6 over 2021/22–2024/25; 26.1 in 2024/25 (289 games) | premierleague.com "Talking Tactics", 24 Mar 2025 |
| Shot conversion | ~11–11.9% | same |
| Pass completion | ~84% (unverified: not found on a page we could fetch; FBref returned 403) | — |
| Top speed | PL record since 2020/21: 37.38 km/h (Van de Ven). Top-10 list from 36.70 km/h | premierleague.com news 4138354 |
| Distance per 90 (outfield, ≥1,500 min) | 8.5–12.3 km; up to 12.9 km (≥600 min) | Opta via premierleague.com, 25 Mar 2025 |
| Sprint threshold / season sprints | >25 km/h; leaders ~640–700 sprints in 29 matchweeks | same |

## So what for us

- **Stage: Ingest.** This is the data source for every idea. It matters most for **A TwinCast** (the simulator *is* the ground truth that our CV is graded against), **E Realism Bench** (generator + realism report against the table above), and **B Speed Trap** (speed and distance tags need believable 25 Hz kinematics capped near 37 km/h, plus sprint events at 25 km/h).
- **Design (event-first):**
  1. Fixture intensities (Poisson-style per-team attack strength).
  2. A possession chain emits passes, carries, shots and tackles with x/y, an exponential "touch time" and a ball flight time. This sets the match clock.
  3. Tracking is derived at 25 Hz. Ball position is interpolated along event segments. Players steer toward formation anchors shifted toward the ball, with speed cap 10.3 m/s and an acceleration cap (our 4 m/s² is a tuning guess, unverified). Add per-player noise and off-ball runs.
  4. Everything is driven by one `seed`, so any moment can be replayed exactly, which is useful for the fact-checker and the cue `evidence ids`.
  5. A streamer yields events and frames at match clock × speed-up into Event Hubs.
- **Known gap from our test:** anchor-following gives only ~2 km per half per player, about half the cited 8.5–12.9 km per 90, and all outfielders move almost identically. Add Ornstein-Uhlenbeck jitter, pressing runs toward the ball carrier and overlapping runs. Then report the before/after numbers in Realism Bench.
- **Avoid:** LLM-generated ground truth, gfootball as a hard dependency, and putting StatsBomb or Metrica data anywhere in the product.

## Reuse: code & links

**Seeded possession-chain event generator** (53 lines, tested; CDF-style coordinates in metres with the origin at the centre). Averaged over 300 seeds and scaled ×2 from one half, it gives ≈880 passes, 84.7% completion, ≈28 shots and ≈3.2 goals per 90. Tune the shot rate, the xG intercept and the touch time to hit the targets above.

```python
import json, math, random

L, W = 105.0, 68.0                      # metres, CDF-style: origin at centre spot
TEAMS = {"home": [f"h{i}" for i in range(1, 12)], "away": [f"a{i}" for i in range(1, 12)]}

def xg(x, y, attack_dir):               # toy xG: distance + angle to goal centre
    gx = attack_dir * L / 2
    d = math.hypot(gx - x, y)
    ang = math.atan2(7.32 * abs(gx - x), (gx - x) ** 2 + y ** 2 - (7.32 / 2) ** 2)
    return 1 / (1 + math.exp(-(-1.6 - 0.11 * d + 1.2 * ang)))

def generate(seed=42, period_s=45 * 60):
    rng = random.Random(seed)
    n, t, team, x, y = 0, 0.0, "home", 0.0, 0.0
    score = {"home": 0, "away": 0}
    def ev(**kw):
        nonlocal n
        n += 1
        return {"event_id": f"e{n:05d}", "period": "first_half", "time_s": round(t, 2),
                "team_id": team, "body_part": "right_foot", "related_event_ids": [], **kw}
    while t < period_s:
        d = 1 if team == "home" else -1           # home attacks +x in this half
        player = rng.choice(TEAMS[team][1:])      # skip GK for simplicity
        dist_to_goal = abs(d * L / 2 - x)
        if dist_to_goal < 30 and rng.random() < 0.03 + (30 - dist_to_goal) / 400:
            p = xg(x, y, d); goal = rng.random() < p
            yield ev(type="shot", sub_type="none", player_id=player, receiver_id=None,
                     x=x, y=y, x_end=d * L / 2, y_end=rng.uniform(-3, 3), xg=round(p, 3),
                     is_successful=goal, outcome_type="successful" if goal else rng.choice(["saved", "wide", "blocked"]))
            other = "away" if team == "home" else "home"
            if goal:
                score[team] += 1; x, y = 0.0, 0.0     # kick-off to the other team
            else:
                x, y = -d * (L / 2 - 5.5), 0.0        # goal kick for the other team
            team = other; t += rng.uniform(20, 60); continue
        length = abs(rng.gauss(14, 8))                 # pass length in metres
        ang = rng.gauss(0, 0.9)                        # forward-biased direction
        xe = max(-L / 2, min(L / 2, x + d * length * math.cos(ang)))
        ye = max(-W / 2, min(W / 2, y + length * math.sin(ang)))
        p_ok = 0.98 - 0.006 * length - 0.12 * (abs(d * L / 2 - xe) < 25)
        ok = rng.random() < p_ok
        receiver = rng.choice([p for p in TEAMS[team] if p != player])
        yield ev(type="pass", sub_type="none", player_id=player, receiver_id=receiver if ok else None,
                 x=round(x, 2), y=round(y, 2), x_end=round(xe, 2), y_end=round(ye, 2),
                 is_successful=ok, outcome_type="successful" if ok else "intercepted")
        t += length / rng.uniform(12, 18) + rng.expovariate(1 / 3.9)   # flight + touch time
        x, y = xe, ye
        if not ok:                                     # turnover: defender wins it
            team = "away" if team == "home" else "home"
            yield ev(type="misc", sub_type="tackle", player_id=rng.choice(TEAMS[team][1:]),
                     receiver_id=None, x=x, y=y, x_end=x, y_end=y, is_successful=True,
                     outcome_type="successful")
```

**Deriving 25 Hz tracking** (tested: speeds stay ≤10.3 m/s and players stay inside the pitch; still needs noise and runs):

```python
import math

FPS, VMAX, AMAX = 25, 10.3, 4.0          # 10.3 m/s ~ 37 km/h (PL record); AMAX is a tuning guess
ANCHORS_442 = [(-50, 0), (-35, -25), (-38, -8), (-38, 8), (-35, 25),
               (-10, -25), (-14, -7), (-14, 7), (-10, 25), (8, -6), (8, 6)]  # home, attacking +x

def target(anchor, ball, side):           # formation anchor shifted toward the ball
    ax, ay = anchor[0] * side, anchor[1]
    tx, ty = ax + 0.35 * (ball[0] - ax * 0.3), ay + 0.25 * (ball[1] - ay)
    return max(-52, min(52, tx)), max(-33, min(33, ty))   # keep inside 105 x 68

def step(pos, vel, tgt, dt=1 / FPS):      # damped steering with speed + accel caps
    dvx, dvy = 1.5 * (tgt[0] - pos[0]) - 2.5 * vel[0], 1.5 * (tgt[1] - pos[1]) - 2.5 * vel[1]
    a = math.hypot(dvx, dvy)
    if a > AMAX: dvx, dvy = dvx * AMAX / a, dvy * AMAX / a
    vx, vy = vel[0] + dvx * dt, vel[1] + dvy * dt
    v = math.hypot(vx, vy)
    if v > VMAX: vx, vy = vx * VMAX / v, vy * VMAX / v
    return (pos[0] + vx * dt, pos[1] + vy * dt), (vx, vy)

def ball_at(ev, t, speed=15.0):           # ball moves linearly from (x,y) to (x_end,y_end)
    d = math.hypot(ev["x_end"] - ev["x"], ev["y_end"] - ev["y"]) or 1e-6
    f = min(1.0, max(0.0, (t - ev["time_s"]) * speed / d))
    return ev["x"] + f * (ev["x_end"] - ev["x"]), ev["y"] + f * (ev["y_end"] - ev["y"])
```

**SPADL export:** `start_x = x + 52.5`, `start_y = y + 34` (SPADL uses origin bottom-left on 105 × 68). Map `pass` → `pass`, `shot` → `shot`, `misc/tackle` → `tackle`; `result = "success" if is_successful else "fail"`.

**Validate:** `pip install common-data-format-validator` (MIT). It has soft, strict and extreme modes and works on JSONL samples. See the README for the exact API.

Links: socceraction https://github.com/ML-KULeuven/socceraction · kloppy https://github.com/PySport/kloppy · CDF validator https://github.com/unravelsports/common-data-format-validator · penaltyblog https://github.com/martineastwood/penaltyblog · LaurieOnTracking (MIT, Metrica parsing and pitch control) https://github.com/Friends-of-Tracking-Data-FoTD/LaurieOnTracking

## Sources

- StatsBomb open-data repo + LICENSE.pdf + Open Data Events v4.0.0 spec — https://github.com/statsbomb/open-data — accessed 20 Oct 2026
- SPADL docs — https://socceraction.readthedocs.io/en/latest/documentation/spadl/spadl.html — accessed 20 Oct 2026
- Atomic-SPADL docs — https://socceraction.readthedocs.io/en/latest/documentation/spadl/atomic_spadl.html — accessed 20 Oct 2026
- socceraction repo (MIT) — https://github.com/ML-KULeuven/socceraction — accessed 20 Oct 2026
- Anzer et al., The Common Data Format (CDF) — https://arxiv.org/abs/2505.15820 (HTML v4: https://arxiv.org/html/2505.15820v4) — accessed 20 Oct 2026
- IEEE P3715 project — https://standards.ieee.org/ieee/3715/12303/ — accessed 20 Oct 2026
- CDF validator (PyPI / GitHub) — https://pypi.org/project/common-data-format-validator/ ; https://github.com/unravelsports/common-data-format-validator — accessed 20 Oct 2026
- kloppy docs / repo / to_cdf PRs — https://kloppy.pysport.org/ ; https://github.com/PySport/kloppy/pull/519 — accessed 20 Oct 2026
- Google Research Football repo + observation doc — https://github.com/google-research/football ; https://github.com/google-research/football/blob/master/gfootball/doc/observation.md — accessed 20 Oct 2026
- Radke & Tilbury, Simulating Tracking Data to Advance Sports Analytics Research — https://arxiv.org/abs/2503.19809 — accessed 20 Oct 2026
- rSoccer — https://github.com/robocin/rSoccer — accessed 20 Oct 2026
- SoccER (Morra et al.) — https://github.com/ElsevierSoftwareX/SOFTX-D-20-00016 — accessed 20 Oct 2026
- Expected Threat flexibility vs accuracy — https://arxiv.org/abs/2511.09457 — accessed 20 Oct 2026
- penaltyblog — https://github.com/martineastwood/penaltyblog — accessed 20 Oct 2026
- Large Events Models — https://arxiv.org/abs/2402.06815 ; https://arxiv.org/abs/2402.06820 ; https://arxiv.org/abs/2603.15212 — accessed 20 Oct 2026
- Metrica Sports sample data — https://github.com/metrica-sports/sample-data — accessed 20 Oct 2026
- databallpy docs (Metrica 25 fps) — https://databallpy.readthedocs.io/en/main/getting_started/loading_in_a_game_page.html — accessed 20 Oct 2026
- SkillCorner opendata — https://github.com/SkillCorner/opendata — accessed 20 Oct 2026
- PFF FC enhanced 2022 World Cup dataset — https://www.blog.fc.pff.com/blog/enhanced-2022-world-cup-dataset — accessed 20 Oct 2026
- 2024–25 Premier League (goals) — https://en.wikipedia.org/wiki/2024%E2%80%9325_Premier_League — accessed 20 Oct 2026
- Opta Analyst, PL teams still more direct 2025-26 (passes per game) — https://theanalyst.com/articles/premier-league-teams-still-more-direct-2025-26 — accessed 20 Oct 2026
- premierleague.com, Six key tactical trends of 2024/25 (shots, conversion) — https://premierleague.com/news/4271974 — accessed 20 Oct 2026
- premierleague.com, Van de Ven sets fastest speed of season — https://www.premierleague.com/en/news/4138354 — accessed 20 Oct 2026
- premierleague.com, Who tops the 2024/25 running charts? — https://www.premierleague.com/news/4272290 — accessed 20 Oct 2026
