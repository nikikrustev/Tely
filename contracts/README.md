# Contracts

Files that cross from one lane to the other. Each folder has one owner (TEAM_SPLIT.md "The seams").

| Folder | Owner | What it is |
|---|---|---|
| `b/` | B (Nikolay) | **The match format**: what happened (events), what it means (signals), where everyone is (ticks). Plus a hand-written 90 s sample, its generator and its test. |
| `golden/a/` | A (potencialbg) | Live Voice Live transcripts (later) |
| `golden/b/` | B | Q&A golden cases (later) |

The rest of this file documents `b/`: the **match format, version 0.2.0** (0.1.0 plus added fields only; see the Changelog).

**Where the real match is.** Stage 1 (`python -m audiostands.build_match --cut judge`, from `pipeline/`) writes the judge cut to `web/public/replay/v1/judge/`. It uses the same four files and the same fields as the sample, plus the 0.2.0 additions.

**Append-only from Wed 21 Oct, 18:00 Sofia.** Adding a field is fine. Renaming or removing a field needs A's approval in the PR (TEAM_SPLIT.md, cross-lane rules).

---

## The match format in one minute

A match is four files in one folder. The sample is in `contracts/b/sample/`. Stage 1 writes the same four files for the real judge cut to `web/public/replay/v1/judge/`.

| File | What it answers | Rate | Standard? |
|---|---|---|---|
| `meta.json` | Who is playing? Kits, names, shirt numbers, kick-off, which part of the match this is | once | Ours |
| `events.jsonl` | What happened, and when? Passes, shots, saves, interceptions | one line per event | **CDF v0.3.2** (passes the validator in `extreme` mode) |
| `signals.json` | What does it mean? Win probability, suspense, tension, danger, crowd mood (per second); xG, importance, zone and ready-to-speak text (per event) | 1 Hz + per event | Ours |
| `ticks.json.gz` | Where is everything? The ball at 25 Hz, all 22 players at 5 Hz | 25 Hz / 5 Hz | Ours |

Why the split: the CDF validator rejects any key it doesn't know (file 26, `extreme` mode), so everything that is not CDF lives in `signals.json`, keyed by the CDF `event.id` (file 26, "Final decision" 2).

### How A's code should use it

| A's piece | Reads | Fields |
|---|---|---|
| Commentary planner (Stage 3) | `events.jsonl` + `signals.json` | event `type`/`outcome_type`, `signals.events[id].xg`, `.priority`, `.zone.words`, per-second `tension` |
| Build-up lines (file 39 look-ahead) | `signals.json` | shot `t` and `xg` only. Never `outcome_type` before `reveal_t` (see "Spoiler rule") |
| Spatial voice | `ticks.json.gz` | ball `x` (pan) and `y` (near/far) at the line's time |
| Names, kits, kick-off line | `meta.json` | `teams.*.short_name`, `kit.words`, `players[].name` |
| Relay / Q&A (through B's `qa/` package) | all four | B's tools read them; A's relay never parses them itself |

Load a match in Python (stdlib only):

```python
import gzip, json
from pathlib import Path
d = Path("contracts/b/sample")
meta = json.loads((d / "meta.json").read_text())
events = [json.loads(s)["event"] for s in (d / "events.jsonl").read_text().splitlines()]
signals = json.loads((d / "signals.json").read_text())
ticks = json.loads(gzip.decompress((d / "ticks.json.gz").read_bytes()))

def ball_at(t):                       # t = seconds since kick-off
    return ticks["ball"]["rows"][round(t * ticks["ball"]["hz"])]      # [x, y, z, alive, poss]
```

---

## Shared rules (all four files)

### Time

- **`t`** is seconds since the start of the period (kick-off = 0.0), as a number. Our files use `t`. CDF files use ISO time.
- **CDF `time`** is UTC with milliseconds and a `Z`: `"2026-10-24T15:00:25.200Z"`. `time = meta.periods[i].start_time + t`.
- **CDF `match_clock`** is `"MM:SS.mm"` (minutes, seconds, hundredths): `"00:25.20"`.
- All event times fall on the 25 Hz grid (multiples of 0.04 s), so an event at `t` is exactly ball row `t × 25`.
- The sample is one period (`first_half`). For a second half, CDF restarts the clock at `"45:00.00"`, and `t` restarts at 0 for that period.

### Pitch and coordinates

Metres, origin at the centre spot (CDF, file 26 §4). The pitch is 105 × 68 m.

```
                         far touchline  (y = +34)
   +--------------------------------------------------------+
   |                           |                            |
 [ |  Reds' goal          (0,0)+ centre spot    Navy's goal  | ]
   |  x = -52.5                |                  x = +52.5 |
   |                           |                            |
   +--------------------------------------------------------+
                         near touchline (y = -34), main stand / "camera" side
        Reds (home) attack  ---->  +x   for the WHOLE match
        Navy (away) attack  <----  -x
```

- **x** runs along the touchline, from -52.5 to 52.5. **The home team attacks +x for the whole match.** CDF standardises this. Real sides only matter for video, which we don't have.
- **y** runs across the pitch, from -34 to 34, bottom to top. **-34 is the near touchline** (the main stand) and +34 is the far one (kloppy's CDF convention; the paper doesn't say, file 26 §4).
- **z** is height in metres. 0.11 = the ball rolling on the grass (its centre); about 1.0 = in a keeper's hands.
- The goal mouth is |y| ≤ 3.66. A ball behind the goal line inside the goal mouth (x up to ±54.5) is in the net.

### Teams

- In our files a team is `"home"` or `"away"`. In CDF lines it is the team id (`"syn_reds"`, `"syn_navy"`), and `meta.teams` maps one to the other.
- The crowd uses `"H"` and `"A"` (the home end and the away end), as in the file 43 cue contract.

### Spoiler rule (important for A and for Q&A)

An event starts at `t`, but its **outcome is only known at `reveal_t`**: when the pass arrives, the shot reaches the keeper, or the ball crosses the line. The listener's playhead must pass `reveal_t` before anything may say how it ended. That covers `spoken`, `spoken_past`, `outcome_type`, the score and the crowd reaction.
- The look-ahead for build-up lines may use a shot's `t`, its `xg` and its zone, never its outcome (files 38, 39, 43).
- The crowd's per-second values already follow this rule: their look-ahead uses xG only.
- **VAR-checked goals (0.2.0):** the final outcome is only known when the check ends. So for a reviewed shot, `reveal_t` is the VAR decision time, not the moment the ball crossed the line. The score changes then too.

---

## `meta.json`

Our format (not CDF). The match, the teams and the window.

| Field | Type | Meaning | Example |
|---|---|---|---|
| `format`, `version` | string | Always `"audiostands.meta"`, and the format version | `"0.1.0"` |
| `cdf_version` | string | CDF version the event lines follow | `"0.3.2"` |
| `synthetic`, `notice` | bool, string | Always `true`, plus a line the UI can show or speak | `"Synthetic match. Fictional clubs and players. No real match data."` |
| `match.id` | string | Same id as in every CDF line | `"syn_sample_0001"` |
| `match.competition`, `match.season` | string | Fictional | `"Berbata Synthetic League"`, `"2026-27"` |
| `match.kickoff_time` | ISO UTC | Kick-off | `"2026-10-24T15:00:00.000Z"` |
| `match.venue` | `{id, name}` | Fictional ground | `{"id":"syn_emberfield","name":"Emberfield"}` |
| `periods[]` | list | One entry per period in this file: `period` (CDF name), `start_time` (ISO, where `t` = 0), `start_t` (0.0), `clock_start` (`"00:00.00"` or `"45:00.00"`) | see sample |
| `pitch` | object | `length_m` 105.0, `width_m` 68.0, `origin` `"centre_spot"`, plus `x`/`y` explained in words | |
| `teams.home` / `teams.away` | object | One team each (below) | |
| `judge_cut` | object | The window this bundle covers: `t_start`, `t_end` (s), `seed` (generator seed; `null` for the hand-written sample), `source` (`"hand_written_sample"` or `"generator"`) | `{"t_start":0.0,"t_end":90.0,"seed":null,"source":"hand_written_sample"}` |
| `rates` | object | `ball_hz` 25, `player_hz` 5, `signals_hz` 1 | |
| `files` | object | The other three file names | |
| `judge_cut.period` *(0.2.0)* | string | The CDF period the window is in (the generator's cuts sit inside one half) | `"second_half"` |
| `judge_cut.score_at_start` *(0.2.0)* | `{home, away}` | Score when the window opens. Goals before the window are not in `events.jsonl`, so add this to any score you count from events. The judge cut is chosen to start at 0–0 | `{"home":0,"away":0}` |
| `officials` *(0.2.0)* | list | `{id, type}` of the officials that referee events name in `official_id` | `[{"id":"ref_1","type":"main_referee"},{"id":"var_1","type":"video_assistant_referee"}]` |
| `generator` *(0.2.0)* | object | `name` and `version` of the generator that made the bundle (absent in the hand-written sample) | `{"name":"audiostands.generator","version":"0.2.0"}` |

**A team:**

| Field | Meaning | Example |
|---|---|---|
| `id` | CDF `team_id` | `"syn_reds"` |
| `name` | Fictional club name | `"Ember Vale FC"` |
| `short_name` | **What the commentator says**: the kit name | `"Reds"` / `"Navy"` |
| `formation` | Starting shape | `"4-3-3"` |
| `attacks` | Direction for the whole match | `"+x"` (home) / `"-x"` (away) |
| `kit` | `shirt`, `sleeves`, `shorts`, `socks`, plus `words` for the kick-off line | `{"shirt":"navy","sleeves":"sky blue",...,"words":"navy shirts with sky-blue sleeves"}` |
| `players[]` | `id` (CDF `player_id`), `first_name`, `last_name`, `name` (full), `jersey_number`, `position` (GK, RB, CB, LB, DM, CM, AM, RW, LW, RM, LM, ST), `is_starter` | `{"id":"r9","first_name":"Caleb","last_name":"Ndiaye-Ross","name":"Caleb Ndiaye-Ross","jersey_number":9,"position":"ST","is_starter":true}` |

Player ids are `r1`…`r11` (Reds) and `n1`…`n11` (Navy), with the shirt number in the id. That is a sample convention: always look players up in `meta`, never parse the id.

---

## `events.jsonl`

**CDF v0.3.2 event lines**, one JSON object per line, LF line endings (the validator rejects CRLF). They are in time order. This is exactly the validated shape from file 26 §2: everything is nested under `"event"`, and a `"meta": {"is_synced": ...}` is required.

```json
{"match":{"id":"syn_sample_0001"},"meta":{"is_synced":true},"event":{"id":"e0011","time":"2026-10-24T15:00:25.200Z","period":"first_half","type":"shot","sub_type":null,"is_successful":false,"outcome_type":"saved","player_id":"r10","team_id":"syn_reds","receiver_id":null,"receiver_time":null,"receiver_team_id":null,"x":33.0,"y":2.0,"x_end":51.2,"y_end":-1.4,"body_part":"right_foot","related_event_ids":["e0012"],"match_clock":"00:25.20"}}
```

| Field | Meaning (units) |
|---|---|
| `match.id` | Same as `meta.match.id` |
| `meta.is_synced` | `true`: positions exist for this moment (in our `ticks.json.gz`) |
| `event.id` | `"e0001"`, `"e0002"`, … in time order. **The key into `signals.events`** |
| `event.time` | When it happened (ISO UTC, ms) |
| `event.period` | `"first_half"`, `"second_half"`, … |
| `event.type` / `sub_type` | What kind of event (table below). snake_case strings |
| `event.is_successful` | `true`/`false`. A goal is a successful shot |
| `event.outcome_type` | How it ended (table below). **Spoiler: only known at `reveal_t`** |
| `event.player_id`, `team_id` | Who did it (ids from `meta`) |
| `event.receiver_id`, `receiver_time`, `receiver_team_id` | Passes only: who got it and when. `null` if it was cut out |
| `event.x`, `y` | Where it started (m) |
| `event.x_end`, `y_end` | Where the ball ended (m). Passes and shots only, `null` otherwise. For a goal, the point where it crossed the line |
| `event.body_part` | `right_foot`, `left_foot`, `head`, `hands`, … (CDF list). Required for passes and shots |
| `event.related_event_ids` | Linked events: shot ↔ save, intercepted pass ↔ interception, goal → the pass that set it up. In the generated cut a shot lists the pass that set it up first (if any), then its save, block or VAR check |
| `event.match_clock` | `"MM:SS.mm"` |
| `event.official_id` *(0.2.0)* | Referee events only, instead of `player_id`/`team_id` (CDF forbids those on referee events). Look it up in `meta.officials` |
| `event.var` *(0.2.0)* | Shots a VAR check reviewed: `{"reviewed": true, "upheld": true/false}` (CDF field). `upheld` = the goal stood |

**Event types in v0.1.0.** CDF leaves `type` free; the names follow file 26 §3.

| What | `type` | `sub_type` | `outcome_type` |
|---|---|---|---|
| Kick-off | `pass` | `kick_off` | `successful` |
| Pass (incl. through balls, crosses, keeper throws with `body_part: "hands"`) | `pass` | `null` | `successful` / `intercepted` |
| Shot | `shot` | `null` | `successful` (= goal) / `saved` (later also `wide`, `blocked`, `woodwork`) |
| Keeper save | `goalkeeping` | `save` | `successful` |
| Interception | `defending` | `interception` | `successful` |
| *(0.2.0)* Free kick · goal kick | `pass` | `free_kick` · `goal_kick` | as a pass |
| *(0.2.0)* Shot that missed or was ruled out | `shot` | `null` | `wide`, `woodwork` (off the post, then a goal kick), `blocked`, `offside` (went in, but VAR ruled it out) |
| *(0.2.0)* Block | `defending` | `block` | `successful` |
| *(0.2.0)* Foul (with or without a card) | `misc` | `foul_committed` | `unsuccessful` (free kick only) / `yellow_card`. The player and team are the ones who committed it |
| *(0.2.0)* VAR-style check | `referee` | `var_check` | `goal_stands` / `goal_disallowed`. Has `official_id` and **no** `player_id`/`team_id`; `x`/`y` = the reviewed shot; `related_event_ids` = [that shot]; `reveal_t` = the decision, about 20 s later |

Rows marked 0.2.0 were added by Stage 1. Not generated yet: red cards (the generator never shows a second yellow, so it stays 11 v 11), penalties, corners and throw-ins. They would be added as new rows, and the fields stay the same.

**Code that reads every event must allow for `referee` events, which have no `team_id` or `player_id`.**

There are no `metrics` on purpose. xG lives in `signals.json` (TEAM_SPLIT.md). Copying it into CDF's `metrics.xg` later would be an additive change.

---

## `signals.json`

Our format. Two parts: `per_second` (one row per whole second) and `events` (one entry per CDF event).

```json
{"format":"audiostands.signals","version":"0.1.0","match_id":"syn_sample_0001","hz":1,
 "per_second":[ {...t=0...}, {...t=1...}, ... ],
 "events":{"e0001":{...}, ...},
 "crowd_one_shots":[ ... ]}
```

### `per_second[]`: row `i` is `t = i` seconds (from `judge_cut.t_start` to `t_end`, both ends included)

Example, two seconds before the goal (Reds are in the box, the cross is in the air):

```json
{"t":60,"win_prob":{"home":0.44,"draw":0.256,"away":0.303},"suspense":0.0315,"tension":0.92,
 "danger":{"home":0.47,"away":0.0},
 "crowd":{"H":{"excitement":0.54,"valence":0.21,"danger":0.5},"A":{"excitement":0.54,"valence":-0.21,"danger":-0.5}},
 "score":{"home":0,"away":0}}
```

| Field | Range | Meaning |
|---|---|---|
| `t` | s | Seconds since kick-off |
| `win_prob.home` / `draw` / `away` | 0–1, sum 1 | Chance of each final result, given the score and time left (file 23 Poisson model) |
| `suspense` | ≥ 0, in win-probability units | How much the win probability could move in the next second (file 39 suspense). Usually 0.005–0.035 |
| `tension` | 0–1 | **One number for "how tense is it now"**, for voice intensity and the haptic heartbeat. Suspense, normalised, plus a ramp over the 4 s before each shot, weighted by xG (file 39 `tension_curve`). It rises before a big chance whether or not it goes in |
| `danger.home` / `danger.away` | 0–1 | How close the team **with the ball** is to scoring (Berbata definition, below). The team without the ball has 0 |
| `crowd.H` / `crowd.A` | | The home end and the away end (file 38): `excitement` 0–1 (how loud and aroused), `valence` −1–1 (happy + / unhappy −, from that end's view), `danger` −1–1 (+ = we are attacking, − = they are) |
| `score.home` / `score.away` | goals | Score as the listener knows it at `t`. It changes at the goal's `reveal_t` |

**Danger, Berbata definition (v0):** `(1 − d / 40 m) ^ 1.5` where `d` is the distance from the ball to the goal the team attacks. It is 0 beyond 40 m and 0 when the ball is dead. Stage 1 may refine it with xT (file 33) but keeps the 0–1 range.

### `events{}`: one entry per CDF event, same ids, same order

Example (the shot above):

```json
"e0011":{"t":25.2,"reveal_t":25.88,"xg":0.09,"priority":2,
         "zone":{"third":"attacking_third","side":"centre","in_box":false,"words":"attacking third, centre"},
         "spoken":"Attacking third, centre, Reds. Ilievski shoots, saved by Solvang.",
         "spoken_past":"Ilievski had a shot saved by Solvang"}
```

| Field | Meaning |
|---|---|
| `t` | Event time in seconds (= CDF `time` − period start) |
| `reveal_t` | When the outcome is known, in seconds: pass arrival, shot reaching the keeper or crossing the line; otherwise `t`. **Nothing about the outcome may be said before this** |
| `xg` | Shots only: chance of a goal from that position and situation, 0–1 (file 07). `null` for every other event |
| `priority` | How important for commentary and catch-up: **0** routine, **1** notable (kick-off, interception, a pass into the final third or the box), **2** big (shot, save; later cards, VAR), **3** goal. Higher = more important. Catch-up uses `>= 2` (file 40) |
| `zone.third` | `defensive_third` / `middle_third` / `attacking_third`, **from the acting team's point of view** (file 36 ball-first grammar) |
| `zone.side` | `near` / `centre` / `far`, **absolute** (near = the main-stand touchline, y < −11.33) |
| `zone.in_box` | `true` if inside the box the acting team attacks |
| `zone.words` | The zone as spoken words: `"attacking third, near side"`. 3 thirds × 3 sides = 9 phrases per team, which matches file 43's 18 pre-rendered zone clips |
| `spoken` | One present-tense line, ball first: where, which team, then who. For "what just happened?" (`get_last_events`). Contains the outcome, so it is safe only after `reveal_t` |
| `spoken_past` | A past-tense fragment with no capital or full stop, for the catch-up "While we talked, A and B." (file 40 `catch_up_line`) |

These are B's plain-text drafts. A's commentator writes its own lines; these are the Q&A and fallback wording.

### `crowd_one_shots[]`

Crowd reactions to play once, at the moment the outcome is revealed: `{"t": 61.28, "end": "H", "kind": "roar"}`. The kinds in v0.1.0 are `roar`, `stunned_hush` (goal for / against), `ooh_groan` and `relief_applause` (our shot missed / theirs missed). 0.2.0 adds:
- `whistles_jeer`: the other team fouls us;
- `cheer`: the other team gets a card;
- `hush`: both ends, when a VAR check starts.

### `haptics[]` *(0.2.0)*

One-off vibration cues from file 41's vocabulary: `{"t": 703.76, "tacton": "goal", "team": "away"}`.
- `tacton` is one of `whistle1` (kick-off), `attack` (tension crosses 0.6), `shot`, `goal` or `nearMiss` (at `reveal_t`), `yellow` or `red`.
- `team` is `"home"`, `"away"` or `null`.
- The heartbeat is not listed: the browser drives it from per-second `tension`.

---

## `ticks.json.gz`

Our format, gzipped JSON. Where the ball and every player are, over the whole window. The sample is 49 KB on disk (175 KB unzipped).

```json
{"format":"audiostands.ticks","version":"0.1.0","match_id":"syn_sample_0001","t0":0.0,"duration_s":90.0,
 "ball":{"hz":25,"columns":["x","y","z","alive","poss"],
         "rows":[[0.0,0.0,0.11,1,"home"], ...]},
 "players":{"hz":5,"ids":["r1","r2","r5",...,"n10"],
            "rows":[[-45.33,0.0,-29.94,-17.6, ...], ...]}}
```

| Field | Meaning |
|---|---|
| `t0`, `duration_s` | The window, in s. It equals `meta.judge_cut` |
| `ball.rows[k]` | The ball at `t = t0 + k / 25`. There are `duration_s × 25 + 1` rows (both ends included). Columns: `x`, `y`, `z` (m, 2 decimals), `alive` (1 in play / 0 dead), `poss` (`"home"`, `"away"`, or `null` when dead) |
| `players.ids` | Column order: all home players, then all away players, as in `meta` |
| `players.rows[k]` | Everyone at `t = t0 + k / 5`, flattened: `[x_0, y_0, x_1, y_1, …]`, so player `ids[j]` is at `rows[k][2j]`, `rows[k][2j+1]` (m). There are `duration_s × 5 + 1` rows |

Example: ball row 1500 (t = 60.00 s), the cross in the air: `[41.82, -11.82, 3.73, 1, "home"]`.

**Why players at 5 Hz.**
- `where_is` needs only 1 Hz, but `get_player_stats` (distance, top speed) needs more. A sprint peak lasts about a second, so 1 Hz under-reads top speed, and 5 Hz catches it.
- The radar also redraws smoothly from 5 Hz with interpolation.
- 25 Hz for all 22 players would be 5× the size for no audible gain: an 8-minute cut is about 53,000 positions at 5 Hz against 264,000 at 25 Hz.
- The ball stays at 25 Hz because the stereo pan and ball sounds follow it closely (file 43 §6).

Player speed is not stored. Work it out from consecutive rows: `hypot(dx, dy) × 5` m/s.

This is not CDF tracking (CDF uses one JSON line per 40 ms frame with nested teams). Converting to it later is mechanical if we need it.

---

## The 90 s sample

`contracts/b/sample/`: Ember Vale FC (**Reds**: red shirts, white shorts) against Port Halden FC (**Navy**: navy shirts with sky-blue sleeves), the first 90 s of a fictional match.

| t (s) | What happens | Events |
|---|---|---|
| 0–24 | Kick-off, then a 10-pass Reds chain: back to the centre-backs, out to the left back, through midfield, and a wall pass with the striker | e0001–e0010 |
| 25.2 | Ilievski (Reds 10) shoots from 20 m, xG 0.09 | e0011 |
| 25.9 | Solvang (Navy 1) saves and holds | e0012 |
| 31–50 | Navy play out from the back down the far side | e0013–e0018 |
| 50.0–50.6 | Oduya's pass is cut out by Fenwick (Reds 5) | e0019, e0020 |
| 51.8–59.4 | Reds counter: a through ball to Wexford, then a cross from the near side | e0021–e0023 |
| 60.9 | Ndiaye-Ross heads it in, xG 0.31, **Reds 1, Navy 0** (`reveal_t` 61.28) | e0024 |
| 61–90 | Ball dead. Celebration in the corner, the keeper fetches the ball, back to the centre spot | (no events) |

What makes it believable:
- Average pass speeds are 10–19 m/s.
- The shot leaves the boot at about 35 m/s, and the ball slows a little on the grass.
- Players follow a team shape that shifts with the ball and possession. Top running speed is 9.0 m/s, against a fastest cited 37.1 km/h (10.3 m/s, file 19).
- Every passer is within 1.5 m of the ball when they touch it.

**Sample-only parts.** The formulas behind `win_prob`, `suspense`, `tension`, `danger` and `crowd` are simple versions of files 23, 38 and 39, with fixed constants. Stage 1's `interpret.py` and `crowd.py` replace the numbers, but not the format.

### Regenerate and test

```bash
pip install -e "pipeline[dev]"
python contracts/b/make_sample.py
cd pipeline && pytest tests/b
```

`make_sample.py` uses only the standard library and no randomness, so it writes identical files every time. The test (`pipeline/tests/b/test_contract.py`, run in CI) checks the sample **and** the real judge cut:
- CDF validity in `extreme` mode;
- ids agree across the four files;
- every event has matching signals;
- the per-second rows cover the window, with values in range;
- the ticks cover the full window at 25 Hz and 5 Hz;
- timestamps are in order and in UTC;
- positions stay on the pitch;
- speeds are realistic, and events line up with the ball and the players;
- the story is complete (pass chain, shot, save, goal, and no score leak before the goal);
- regenerating gives identical files. For `ticks.json.gz` it compares the unzipped content, because gzip bytes can differ between zlib builds.

On the judge cut, "events line up with the players" allows a median of 2 m and a 90th percentile of 4 m, because the players come from file 19's movement model rather than being placed by hand. `pipeline/tests/b/test_stage1.py` adds the Stage 1 checks:
- byte-identical rebuilds, and the committed bundle matches a fresh build;
- the two file 33 generator fixes;
- the crowd before a shot doesn't depend on its outcome;
- the look-ahead swell before a good chance;
- opposite valence at the two ends after a goal;
- the clock firewall;
- the judge-cut choice.

## Changelog

- **0.1.0** (20 Oct 2026): first version, with the hand-written 90 s sample.
- **0.2.0** (21 Oct 2026): Stage 1, the real judge cut. Added only, nothing renamed or removed:
  - `meta`: `judge_cut.period`, `judge_cut.score_at_start`, `officials`, `generator`;
  - `events`: event types `pass/free_kick`, `pass/goal_kick`, `shot` outcomes `wide`/`woodwork`/`blocked`/`offside`, `defending/block`, `misc/foul_committed`, `referee/var_check` (with `official_id`), and the CDF `var` field on reviewed shots;
  - `signals`: `haptics[]` and the one-shot kinds `whistles_jeer`, `cheer`, `hush`.
  - For VAR-reviewed shots, `reveal_t` is the decision time.
