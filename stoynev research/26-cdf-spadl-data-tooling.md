# 26 — Settling our data format: CDF compliance, SPADL conversion and kloppy interop

_Accessed/compiled: 20 Oct 2026 · Priority area: Ingest (wire format) → Interpret (analytics models) · Builds on 02_

## TL;DR

- **Target CDF v0.3.2, the version the validator checks.** The paper (arXiv 2505.15820 v4, 20 Aug 2025) calls itself "Version 1.0.0". The validator's v0.3.2 changelog (9 Sep 2026) says it "aligned the schemas with the paper's tables", field by field, and it is the only machine-checkable spec. Pin `common-data-format-validator==0.1.1`, write `meta.cdf.version = "0.3.2"` in our meta file, and validate in `extreme` mode.
- **Our run:** minimal meta, match sheet, event and tracking files for a synthetic match **pass in both `strict` and `extreme` modes**. So does a 1,058-event generated match. The two examples in doc 02 **fail**. Events must be nested under `"event"` with a required `"meta": {"is_synced": ...}`. In tracking, `ball_status`/`ball_poss_team_id` must become `ball.status` (bool) and `ball.poss_team_id`. A full-file check also needs `frame_id` to start at 0.
- **Coordinates:** CDF and SPADL both use the convention that the home team attacks to the right for the whole match. So CDF → SPADL is **a shift (and a rescale if the pitch is not 105×68), with no flip**: `sx = (x + L/2)·105/L`, `sy = (y + W/2)·68/W`. The per-period `play_direction` / `left_team_id` fields record the *real* sides. Use them only to draw overlays on video.
- **Converter works (our run):** the ~80-line CDF → SPADL converter below passes `socceraction.spadl.SPADLSchema` validation. On 30 seeded matches (32,485 actions) it fits socceraction's **xT** and computes **VAEP** features and labels.
- **kloppy cannot load CDF today.** Released kloppy 3.19.1 has no CDF code. PR #519 (tracking-only `load_tracking` + `to_cdf`) is still **open with merge conflicts**, last updated 8 Jan 2026. PR #502 is a draft. A 45-line in-memory adapter (below, tested) already gives us kloppy's `to_df()`/`transform()` on our CDF tracking.

## Findings

### 1. Which version: paper vs validator vs IEEE

| Item | What we found |
|---|---|
| Paper | Anzer et al., v1 6 Feb 2025 → v4 20 Aug 2025. It describes "Version 1.0.0". Internal inconsistencies: event/skeletal tables spell periods `first_half_extra`, while tracking/meta use `first_half_extratime`. |
| Validator | `common-data-format-validator` 0.1.1 (PyPI, 9 Sep 2026, MIT). `cdf.VERSION = "0.3.2"` ("alpha"). Bundles schemas v0.2.0 to v0.3.2. Modes: `soft` (warn only), `strict` (raise on schema errors, warn on unknown keys), `extreme` (unknown keys also raise). The README says it does *not* check cross-file IDs or UTF-8. Python ≥3.11. No CLI. |
| v0.3.2 breaking changes | `final_winning_team_id` → `result.final.winning_team_id`. Goal `assist_id` is now mandatory (nullable). Team name/colour/formation and `vendor` are removed from tracking frames. `percipitation` → `precipitation` (int). |
| IEEE P3715 | "Standard for a Common Exchange Format for Match-Data in Football (Soccer)". Active PAR, approved 2025-11-04. Working group: "WG for Common Data Format in Football (Soccer)", chaired by Jesse Davis (a CDF co-author). Sponsor: IEEE EMB. No draft is public, so v0.3.2 is what exists to target. |

### 2. Exact shapes (all four validated in our run: PASS in `strict` and `extreme`)

**Meta** (`meta.json`). Required: competition, season, match (id, kickoff_time, periods, whistles), teams, venue, meta. The keys `meta.video/landmarks/ball` are required but may be `null`.
```json
{"competition":{"id":"syn_league"},"season":{"id":"syn_2026"},
 "match":{"id":"syn_0001","kickoff_time":"2026-10-20T15:00:00Z",
  "periods":[{"period":"first_half","play_direction":"left_right","start_time":"2026-10-20T15:00:00Z","end_time":"2026-10-20T15:47:00Z","frame_id_start":0,"frame_id_end":70499,"left_team_id":"syn_home","right_team_id":"syn_away"},
             {"period":"second_half","play_direction":"right_left","start_time":"2026-10-20T16:02:00Z","end_time":"2026-10-20T16:50:00Z","frame_id_start":70500,"frame_id_end":142499,"left_team_id":"syn_away","right_team_id":"syn_home"}],
  "whistles":[{"type":"first_half","sub_type":"start","time":"2026-10-20T15:00:00Z"},{"type":"first_half","sub_type":"end","time":"2026-10-20T15:47:00Z"},
              {"type":"second_half","sub_type":"start","time":"2026-10-20T16:02:00Z"},{"type":"second_half","sub_type":"end","time":"2026-10-20T16:50:00Z"}]},
 "teams":{"home":{"id":"syn_home","name":"Synthetic Home","players":[{"id":"h1","team_id":"syn_home","jersey_number":1,"is_starter":true},{"id":"h8","team_id":"syn_home","jersey_number":8,"is_starter":true},{"id":"h10","team_id":"syn_home","jersey_number":10,"is_starter":true}]},
          "away":{"id":"syn_away","name":"Synthetic Away","players":[{"id":"a1","team_id":"syn_away","jersey_number":1,"is_starter":true},{"id":"a4","team_id":"syn_away","jersey_number":4,"is_starter":true}]}},
 "venue":{"id":"syn_stadium","pitch_length":105.0,"pitch_width":68.0},
 "meta":{"video":null,"landmarks":null,"ball":null,
  "tracking":{"version":"0.1.0","name":"berbata_sim","fps":25,"collection_timing":"live"},
  "event":{"version":"0.1.0","name":"berbata_sim","collection_timing":"live"},
  "meta":{"version":"0.1.0","name":"berbata_sim"},"cdf":{"version":"0.3.2"}}}
```
**Match sheet** (`match.json`). The validator checks that `winning_team_id` agrees with the score.
```json
{"match":{"id":"syn_0001","status":{"is_neutral":false,"has_extratime":false,"has_shootout":false},
  "result":{"final":{"home":1,"away":0,"winning_team_id":"syn_home"},"first_half":{"home":1,"away":0},"second_half":{"home":0,"away":0}}},
 "teams":{"home":{"id":"syn_home","formation":"4-4-2","players":[{"id":"h10","first_name":"Sim","last_name":"Ten","team_id":"syn_home","jersey_number":10,"is_starter":true,"has_played":true,"position":"CAM"}]},
          "away":{"id":"syn_away","players":[{"id":"a4","first_name":"Sim","last_name":"Four","team_id":"syn_away","jersey_number":4,"is_starter":true,"has_played":true}]}},
 "officials":[{"id":"ref_1","type":"main_referee"}],
 "events":{"goals":[{"time":"2026-10-20T15:03:15.900Z","period":"first_half","team_id":"syn_home","player_id":"h10","assist_id":"h8","is_own_goal":false,"is_penalty":false,"score":{"home":1,"away":0}}],
           "substitutions":null,"cards":null},
 "meta":{"vendor":"berbata_sim"}}
```
**Event** (one JSONL line). All 16 keys under `event` are required, even when `null`. Passes and shots must have numeric `x_end`/`y_end` and a string `body_part`.
```json
{"match":{"id":"syn_0001"},"meta":{"is_synced":true},"event":{"id":"e00042","time":"2026-10-20T15:03:12.480Z","period":"first_half","type":"pass","sub_type":null,"is_successful":true,"outcome_type":"successful","player_id":"h8","team_id":"syn_home","receiver_id":"h10","receiver_time":"2026-10-20T15:03:13.610Z","receiver_team_id":"syn_home","x":-4.2,"y":11.0,"x_end":17.9,"y_end":5.3,"body_part":"right_foot","related_event_ids":null,"match_clock":"03:12.48","metrics":{"xpass":0.81}}}
```
**Tracking frame** (one JSONL line every 40 ms). Optional per-player fields are `vel`, `acc`, `dist` and `is_visible`. Ball fields are `status` (bool), `poss_team_id` and `poss_status`.
```json
{"frame_id":0,"timestamp":"2026-10-20T15:00:00.000Z","period":"first_half","match":{"id":"syn_0001"},"teams":{"home":{"id":"syn_home","players":[{"id":"h1","x":-49.8,"y":0.6},{"id":"h8","x":-0.4,"y":0.5,"vel":5.0}]},"away":{"id":"syn_away","players":[{"id":"a4","x":9.15,"y":0.0}]}},"ball":{"x":0.0,"y":0.0,"z":0.11,"status":true,"poss_team_id":"syn_home"}}
```

**Negative tests (our run, so we know what CI will catch):**

| Input | Mode | Result |
|---|---|---|
| doc 02 flat event (fields at top level) | strict | FAIL: `'meta' is a required property` |
| doc 02 frame, `frame_id` 4812, full-file check | strict | FAIL: `frame_id must start at 0` |
| doc 02 frame with `ball_status`, `ball_poss_team_id` at top level | strict / extreme | PASS with warnings / FAIL `unknown field 'ball_status'` |
| our extra `event.time_s` | strict / extreme | warning / FAIL `unknown field 'time_s' - did you mean 'time'?` |
| `time` with `+01:00` offset | strict | FAIL (must be UTC `Z` or `+00:00`) |
| pass with `body_part: null` | strict | FAIL |
| `sub_type: "CornerKick"` | strict | FAIL (values must be snake_case) |
| `referee` event with `player_id` and no `official_id` | strict | FAIL |
| `x: 70.0` (SPADL coordinates leaking into CDF) | strict | FAIL (bounds are ±65 / ±42.5; only keys named `x`/`y` are checked, not `x_end`) |
| `type: "carry"` (not in the paper) | extreme | **PASS**: `type` and `sub_type` are free snake_case strings |

Gotchas: the `frame_id`-starts-at-0 and monotonic checks run only with `limit=None`. To validate a mid-match stream slice, use a numeric `limit`, or pass each record as a dict. Values that look like identifiers must be snake_case, except id-type keys (`id`, `player_id`, `team_id`, `receiver_id`...).

### 3. Field mapping: our synthetic events → CDF → SPADL

SPADL vocabulary in socceraction 1.5.3 (`spadl/config.py`): 23 action types (including `non_action` and `goalkick`), 6 results (`fail, success, offside, owngoal, yellow_card, red_card`) and 6 bodyparts (`foot, head, other, head/other, foot_left, foot_right`). Rows marked *ours* are conventions we choose where CDF is silent. They still validate because types are free strings.

| Our event | CDF `type` / `sub_type` / `outcome_type` | SPADL `type` / `result` / `bodypart` |
|---|---|---|
| Open-play pass | pass / null / successful, intercepted, out_of_play | pass (or **cross** if it starts wide in the final third and ends in the box: *our rule*, since CDF has no cross flag) / success or fail |
| Offside pass | pass / null / offside (*ours*) | pass / offside |
| Corner | pass / corner_kick | corner_crossed if it ends in the box, else corner_short |
| Free-kick pass | pass / free_kick | freekick_crossed / freekick_short (same rule) |
| Throw-in | pass / throw_in (body_part hands) | throw_in / – / other |
| Goal kick · kick-off | pass / goal_kick · kick_off | goalkick · pass |
| Shot | shot / null / successful, saved, blocked, wide, woodwork | shot / success or fail |
| Penalty · direct free kick | shot / penalty_kick · free_kick | shot_penalty · shot_freekick |
| Own goal | shot / … / own_goal | shot / owngoal |
| Tackle | misc / tackle (paper) | tackle |
| Interception · clearance | defending / interception · clearance | interception · clearance |
| Pressure | defending / pressing / pressure | **dropped**: SPADL has no pressure. Keep it in CDF for "pressure changes" explanations |
| Block | defending / block | dropped (non_action) |
| Carry · take-on · bad touch | misc / carry · take_on · bad_touch (*ours*) | dribble · take_on · bad_touch |
| Foul (+ card) | misc / foul_committed, with outcome yellow_card or red_card (*ours*, player side), **plus** referee / foul with `official_id`. Referee events may not carry `player_id` | foul / fail, yellow_card or red_card |
| Keeper actions | goalkeeping / save, claim, punch, pick_up | keeper_save, keeper_claim, keeper_punch, keeper_pick_up |
| Possession change | no event. Carried in tracking as `ball.poss_team_id` | derived, not an action |

Body part: `left_foot`→`foot_left`, `right_foot`→`foot_right`, `feet`→`foot`, `head`→`head`, any other value →`other`, `null`→`foot` (socceraction's StatsBomb converter also defaults to foot).

### 4. Coordinates and direction of play

- **CDF:** metres, origin at the centre spot, x along the touchline. Per the meta-schema description, "The CDF requires a standardized playing direction": the paper says the home team "always plays from left to right for the entire match". `left_team_id`/`right_team_id` "should be the actual, non-standardized sides". The paper does not state which way +y points. kloppy PR #519's `CDFCoordinateSystem` uses **y bottom-to-top** (same as Second Spectrum). We adopt that (paper unverified).
- **SPADL:** 105 × 68 m, origin bottom-left, home team attacks to the right (socceraction docs). So: `sx = (x + L/2)·105/L`, `sy = (y + W/2)·68/W`, clipped to the pitch, **no flip**. (socceraction's StatsBomb converter has to flip away actions with `_fix_direction_of_play` because StatsBomb is per-team. CDF already is not.)
- **Per-actor normalisation:** `socceraction.spadl.play_left_to_right(actions, home_team_id)` mirrors away rows (`x→105−x`, `y→68−y`), so every action attacks right. Call it before `ExpectedThreat.fit`. **Don't** call it before VAEP: `VAEP.compute_features` already does this internally with `game.home_team_id`.
- **kloppy terms:** CDF = `Orientation.STATIC_HOME_AWAY`. Per-actor = `ACTION_EXECUTING_TEAM` (events) or `BALL_OWNING_TEAM` (tracking).
- **Real-world sides (for video):** when the home team is really on the right (`left_team_id != home`), rotate by 180°: `(x, y) → (−x, −y)`. The paper describes custom normalisation as multiplying by −1.

## So what for us

- **Stages: Ingest (canonical format, CI gate) → Interpret (xT/VAEP via SPADL) → Render (real-side flip for overlays).**
- **A TwinCast:** emit simulator ground truth *and* our YOLO+ByteTrack output as CDF tracking. Then one validator, one kloppy adapter and one grader handle both. The overlay compositor must apply the real-side rotation in the second half. The CDF data itself never flips.
- **E Realism Bench:** put a "valid CDF v0.3.2 (extreme)" badge and the validator log in the realism report. This is a cheap, objective claim that the 40-50 crew-style projects won't have. xT fitted on our SPADL export gives a realism check against public xT grids.
- **B Speed Trap:** speed and distance fit in CDF optional fields (`vel`, `acc`, `dist` per player), so there is no need for a custom schema.
- **03 Dive Judges / 06 Relay Credit / 02 Decoy Credit:** VAEP and xT values come for free from the SPADL export.
- **Final decision:**
  1. CDF v0.3.2 JSONL is the only wire format on Event Hubs and on disk.
  2. Non-CDF fields (`time_s`, seed, evidence ids) go in a sidecar `berbata.jsonl` keyed by `event.id`, or into the cue JSON, never inside CDF records. Use `match_clock` and `metrics.xg/xpass/epv` where CDF already has a slot.
  3. SPADL is a derived artefact for analytics only.
  4. CI validates every generated fixture in `extreme` mode and also checks cross-file IDs, which the validator skips.

## Reuse: code & links

**CDF → SPADL converter** (tested: our 3 examples, 9 toy edge cases and 30 seeded matches all pass `SPADLSchema.validate`. `xthreat.ExpectedThreat(l=16, w=12).fit()` converged in 28 iterations. `VAEP.compute_features` gave 1,058 × 568 for one match.)
```python
import json; from datetime import datetime; import pandas as pd
from socceraction.spadl import config as sc, SPADLSchema, add_names
PERIOD_ID = {"first_half":1,"second_half":2,"first_half_extratime":3,"second_half_extratime":4,"shootout":5}
BODYPART = {"left_foot":"foot_left","right_foot":"foot_right","feet":"foot","head":"head"}
TYPE_MAP = {("pass",None):"pass",("pass","kick_off"):"pass",("pass","throw_in"):"throw_in",("pass","goal_kick"):"goalkick",
  ("shot",None):"shot",("shot","corner_kick"):"shot",("shot","penalty_kick"):"shot_penalty",("shot","free_kick"):"shot_freekick",
  ("misc","tackle"):"tackle",("misc","take_on"):"take_on",("misc","carry"):"dribble",("misc","bad_touch"):"bad_touch",
  ("misc","foul_committed"):"foul",("defending","interception"):"interception",("defending","clearance"):"clearance",
  ("goalkeeping","save"):"keeper_save",("goalkeeping","claim"):"keeper_claim",("goalkeeping","punch"):"keeper_punch",
  ("goalkeeping","pick_up"):"keeper_pick_up"}          # anything else (pressing, block, referee...) is dropped
_ts = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))
in_box = lambda x, y: x >= 88.5 and abs(y - 34) <= 20.16      # attacking penalty area, SPADL coords

def _type(t, st, sx, sy, ex, ey, home):
    st = None if st in (None, "none") else st
    fx = (lambda v: v) if home else (lambda v: 105 - v); fy = (lambda v: v) if home else (lambda v: 68 - v)
    if t == "pass" and st in ("corner_kick", "free_kick"):
        kind = "corner" if st == "corner_kick" else "freekick"
        return f"{kind}_crossed" if in_box(fx(ex), fy(ey)) else f"{kind}_short"
    a = TYPE_MAP.get((t, st))
    if a == "pass" and in_box(fx(ex), fy(ey)) and abs(fy(sy) - 34) > 20.16 and fx(sx) > 70:
        return "cross"                                       # our geometric cross rule
    return a

def _result(e):
    out = e.get("outcome_type")
    if e["type"] == "misc" and e.get("sub_type") == "foul_committed":
        return {"yellow_card":"yellow_card","second_yellow_card":"yellow_card","red_card":"red_card"}.get(out, "fail")
    return {"own_goal":"owngoal","offside":"offside"}.get(out, "success" if e.get("is_successful") else "fail")

def cdf_to_spadl(meta: dict, lines: list[dict], game_id=None) -> pd.DataFrame:
    L, W = meta["venue"].get("pitch_length", 105.0), meta["venue"].get("pitch_width", 68.0)
    home = meta["teams"]["home"]["id"]; t0 = {p["period"]: _ts(p["start_time"]) for p in meta["match"]["periods"]}
    X = lambda x: min(max((x + L/2) * 105 / L, 0), 105); Y = lambda y: min(max((y + W/2) * 68 / W, 0), 68)
    rows = []
    for ln in lines:
        e = ln["event"]
        if e["type"] == "referee": continue
        sx, sy = X(e["x"]), Y(e["y"])
        ex = X(e["x_end"]) if e.get("x_end") is not None else sx
        ey = Y(e["y_end"]) if e.get("y_end") is not None else sy
        a = _type(e["type"], e.get("sub_type"), sx, sy, ex, ey, e["team_id"] == home)
        if a is None: continue
        bp = "other" if a == "throw_in" else BODYPART.get(e.get("body_part"), "other" if e.get("body_part") else "foot")
        rows.append(dict(game_id=game_id or ln["match"]["id"], original_event_id=e["id"], period_id=PERIOD_ID[e["period"]],
            time_seconds=(_ts(e["time"]) - t0[e["period"]]).total_seconds(), team_id=e["team_id"], player_id=e["player_id"],
            start_x=sx, start_y=sy, end_x=ex, end_y=ey, type_id=sc.actiontypes.index(a),
            result_id=sc.results.index(_result(e)), bodypart_id=sc.bodyparts.index(bp)))
    df = pd.DataFrame(rows).sort_values(["period_id", "time_seconds"], kind="mergesort").reset_index(drop=True)
    df.insert(2, "action_id", range(len(df)))
    return SPADLSchema.validate(add_names(df))
```
Usage: `ltr = play_left_to_right(actions, "syn_home"); xT = xthreat.ExpectedThreat().fit(ltr); ltr["xt"] = xT.rate(ltr)`. Only successful move actions get a value; others are NaN. For VAEP: `VAEP().compute_features(pd.Series({"game_id": gid, "home_team_id": "syn_home"}), actions)`. If our simulator does not emit carries, add socceraction's (private) `spadl.base._add_dribbles` after the conversion.

**Install gotcha (our run):** `pip install socceraction` gives 1.5.3, the latest on PyPI (Aug 2024). It pulls `multimethod` 2.1, which breaks `import pandera` 0.17.2 (`cannot import name 'overload'`). Pin `multimethod<2`.

**CDF tracking → kloppy adapter** (tested on kloppy 3.19.1: `to_df()`, `transform(to_coordinate_system="kloppy", to_orientation="BALL_OWNING_TEAM")` and `transform(to_coordinate_system="metrica")` all work):
```python
from kloppy.domain import (BallState, CustomCoordinateSystem, DatasetFlag, Dimension, Ground, Metadata, MetricPitchDimensions,
    Orientation, Origin, Period, Player, PlayerData, Point, Point3D, Provider, Team, TrackingDataset, VerticalOrientation)
from kloppy.domain.services.frame_factory import create_frame
PID = {"first_half":1,"second_half":2,"first_half_extratime":3,"second_half_extratime":4,"shootout":5}

def load_cdf_tracking(meta_path, tracking_path) -> TrackingDataset:
    meta = json.load(open(meta_path)); L, W = meta["venue"]["pitch_length"], meta["venue"]["pitch_width"]
    teams, players = [], {}
    for side, g in (("home", Ground.HOME), ("away", Ground.AWAY)):
        t = meta["teams"][side]; team = Team(team_id=t["id"], name=t.get("name", t["id"]), ground=g)
        for p in t["players"]:
            pl = Player(player_id=p["id"], team=team, jersey_no=p["jersey_number"], starting=p["is_starter"])
            team.players.append(pl); players[p["id"]] = pl
        teams.append(team)
    by_id = {t.team_id: t for t in teams}; start = {p["period"]: _ts(p["start_time"]) for p in meta["match"]["periods"]}
    periods = {PID[p["period"]]: Period(id=PID[p["period"]], start_timestamp=timedelta(0),
               end_timestamp=_ts(p["end_time"]) - _ts(p["start_time"])) for p in meta["match"]["periods"]}
    cs = CustomCoordinateSystem(origin=Origin.CENTER, vertical_orientation=VerticalOrientation.BOTTOM_TO_TOP,
        pitch_dimensions=MetricPitchDimensions(x_dim=Dimension(-L/2, L/2), y_dim=Dimension(-W/2, W/2),
                                               pitch_length=L, pitch_width=W, standardized=False))
    frames = []
    for line in open(tracking_path):
        fr = json.loads(line); b = fr["ball"]
        pdata = {players[p["id"]]: PlayerData(coordinates=Point(p["x"], p["y"]), speed=p.get("vel"))
                 for s in ("home", "away") for p in fr["teams"][s]["players"] if p["x"] is not None}
        frames.append(create_frame(frame_id=fr["frame_id"], timestamp=_ts(fr["timestamp"]) - start[fr["period"]],
            period=periods[PID[fr["period"]]], ball_coordinates=Point3D(b["x"], b["y"], b["z"]),
            ball_state=BallState.ALIVE if b.get("status", True) else BallState.DEAD,
            ball_owning_team=by_id.get(b.get("poss_team_id")), players_data=pdata, other_data={}))
    md = Metadata(teams=teams, periods=list(periods.values()), pitch_dimensions=cs.pitch_dimensions, coordinate_system=cs,
                  orientation=Orientation.STATIC_HOME_AWAY, flags=DatasetFlag.BALL_OWNING_TEAM | DatasetFlag.BALL_STATE,
                  provider=Provider.OTHER, frame_rate=meta["meta"]["tracking"]["fps"], score=None, game_id=meta["match"]["id"])
    return TrackingDataset(records=frames, metadata=md)          # (imports json, timedelta, _ts as above)
```
For events we skip kloppy. socceraction's own kloppy → SPADL path officially supports only the StatsBomb provider (`_SUPPORTED_PROVIDERS` in `spadl/kloppy.py`) and warns on any other, so going CDF → SPADL directly is simpler. When PR #519 merges, replace the adapter with `kloppy.cdf.load_tracking(meta_data, raw_data)`. That PR also validates input with the CDF validator in soft mode.

**CI step** (`.github/workflows/data.yml`, run on every PR):
```yaml
- run: pip install "common-data-format-validator==0.1.1" "socceraction==1.5.3" "multimethod<2" pytest
- run: python -m sim.generate --seeds 0 1 2 --out fixtures/   # writes meta.json, match.json, event.jsonl, tracking.jsonl
- run: pytest tests/test_data_contract.py
```
```python
# tests/test_data_contract.py
import cdf, json, glob, pytest
from sim.cdf_spadl import cdf_to_spadl
V = {"meta.json": cdf.MetaSchemaValidator, "match.json": cdf.MatchSchemaValidator,
     "event.jsonl": cdf.EventSchemaValidator, "tracking.jsonl": cdf.TrackingSchemaValidator}
@pytest.mark.parametrize("path", sorted(glob.glob("fixtures/*/*.json*")))
def test_cdf_extreme(path):
    V[path.split("/")[-1]]().validate_schema(sample=path, mode="extreme", limit=None)   # raises on any finding
def test_ids_and_spadl():
    for d in glob.glob("fixtures/*/"):
        meta = json.load(open(d + "meta.json")); ev = [json.loads(l) for l in open(d + "event.jsonl")]
        roster = {p["id"] for s in ("home", "away") for p in meta["teams"][s]["players"]}
        assert {e["event"]["player_id"] for e in ev if "player_id" in e["event"]} <= roster   # validator skips this
        cdf_to_spadl(meta, ev)                                                             # SPADLSchema.validate inside
```
For live Event Hubs messages, call `validate_schema(sample=record_dict, mode="strict")` on a sampled 1% of messages. Don't run the full-file frame check on slices.

Links: validator https://github.com/UnravelSports/common-data-format-validator · docs https://www.cdf.football · socceraction https://github.com/ML-KULeuven/socceraction · kloppy https://github.com/PySport/kloppy · kloppy PR #519 https://github.com/PySport/kloppy/pull/519

## Sources

- common-data-format-validator on PyPI (0.1.1; release history) — https://pypi.org/project/common-data-format-validator/ — accessed 20 Oct 2026
- CDF validator repo, README, schemas `cdf/files/v0.3.2/`, commits (last 9 Sep 2026) — https://github.com/UnravelSports/common-data-format-validator — accessed 20 Oct 2026
- CDF validator CHANGELOG (v0.3.2, 9 Sep 2026) — https://github.com/UnravelSports/common-data-format-validator/blob/main/CHANGELOG.md — accessed 20 Oct 2026
- CDF documentation site (states Version 0.3.2) — https://www.cdf.football — accessed 20 Oct 2026
- Anzer et al., Common Data Format (CDF), arXiv 2505.15820 (abstract + v4 HTML) — https://arxiv.org/abs/2505.15820 ; https://arxiv.org/html/2505.15820v4 — accessed 20 Oct 2026
- IEEE P3715 project page — https://standards.ieee.org/ieee/3715/12303/ — accessed 20 Oct 2026
- socceraction SPADL docs — https://socceraction.readthedocs.io/en/latest/documentation/spadl/spadl.html — accessed 20 Oct 2026
- socceraction 1.5.3 source (`spadl/config.py`, `schema.py`, `utils.py`, `base.py`, `statsbomb.py`, `kloppy.py`, `xthreat.py`, `vaep/base.py`), installed from PyPI — https://pypi.org/project/socceraction/ — accessed 20 Oct 2026
- kloppy docs (loading data, coordinates/transformations, dataframes) — https://kloppy.pysport.org/user-guide/transformations/coordinates/ ; https://kloppy.pysport.org/user-guide/exporting-data/dataframes/ — accessed 20 Oct 2026
- kloppy 3.19.1 source (`domain/models/common.py`: Orientation, SecondSpectrumCoordinateSystem, CustomCoordinateSystem) — https://github.com/PySport/kloppy — accessed 20 Oct 2026
- kloppy PR #519 "[CDF] to_cdf" (open, mergeable_state dirty, updated 8 Jan 2026) and file list incl. `CDFCoordinateSystem` — https://github.com/PySport/kloppy/pull/519 — accessed 20 Oct 2026
- kloppy PR #502 "Feat/to cdf" (open draft, updated 24 Oct 2025) — https://github.com/PySport/kloppy/pull/502 — accessed 20 Oct 2026
- Our run: Python 3.12.10 scratch venv, common-data-format-validator 0.1.1, socceraction 1.5.3, kloppy 3.19.1, pandas 2.3.3, pandera 0.17.2 — 20 Oct 2026
