# 20 — Building the ground-truth grader: tracking metrics tooling and camera calibration from frames

_Accessed/compiled: 20 Oct 2026 · Priority area: CV grading (A TwinCast), speed truth (B Speed Trap), calibration (D Chalk Talk), realism report (E Realism Bench)_

## TL;DR

- **Write MOTChallenge text files and score them with `trackers eval`.** Each line is `frame,id,bb_left,bb_top,bb_width,bb_height,conf,x,y,z`, with 1-based frames. For ground truth, column 7 must be 1 (rows with 0 are dropped) and column 8 must be class 1 ("pedestrian"). `trackers eval --gt_dir ... --predictions_dir ... --metrics '[CLEAR,HOTA,Identity]'` returns MOTA, HOTA and IDF1. Keep TrackEval (MIT) as the reference implementation. Use `--DO_PREPROC False` on our data.
- **Grade in pitch metres, not only in pixels.** GS-HOTA scores matches with `LocSim = exp(ln(0.05)·d²/τ²)`, where τ = 5 m, times an all-attributes-match IdSim. A metre-based grader we fully understand is simple to build: Hungarian matching per frame with a 5 m gate, then mean and p95 position error, plus ID accuracy per tracklet. The SoccerNet GSR baseline scored only 22.26% GS-HOTA, so a low number is normal.
- **Process speed the way FIFA's EPTS test does.** The test computes speed from x/y by three-point central difference, then applies a 2nd-order 1 Hz low-pass Butterworth filter. Data is resampled to 50 Hz and aligned by cross-correlation plus a ±50-sample RMSD search. Results are rated on a five-level scale within velocity bands (0-5, 5-10, ... 25+ km/h). Smoothing lowers top speed, while raw differentiation raises it. Measure that bias against our own truth rather than guessing it.
- **Calibration from frames:** No Bells Just Whistles (NBJW) and PnLCalib each run as a single `inference.py` with release weights. Both are GPL-2.0. TVCalib is MIT but runs from a notebook. NBJW (single view) reports Acc@5 75.3% at 97.8% completeness on SoccerNet 2022, and a mean projection error of 1.23 m (median 0.58 m) on WorldCup 2014 without fine-tuning. Compare against our true camera by reprojecting a 1 m pitch grid and reporting the error in metres.
- **Demo experiment:** a degradation sweep (blur × compression × occlusion) plotted as small multiples of event F1, HOTA, position error and top-speed error. Each panel has two lines, one for oracle calibration and one for CV calibration.

## Findings

### 1. MOTChallenge format and how to run the evaluators

| col | field | GT (what TrackEval reads) | predictions |
|---|---|---|---|
| 1 | frame | 1-based | 1-based |
| 2 | id | track id | track id |
| 3-6 | bb_left, bb_top, bb_width, bb_height | pixels | pixels |
| 7 | conf | **"consider" flag**: rows with 0 are dropped | detector score, or 1 |
| 8 | x / class | **class, which must be 1 = pedestrian**; an error is raised if the column is missing | -1 |
| 9 | y / visibility | visibility (not read by the 2D-box loader) | -1 |
| 10 | z | -1 | -1 |

- TrackEval reads GT from `GT_FOLDER/<BENCHMARK>-<split>/<seq>/gt/gt.txt` and predictions from `TRACKERS_FOLDER/<BENCHMARK>-<split>/<tracker>/data/<seq>.txt`. It needs `seqinfo.ini`, but uses only `[Sequence] seqLength`. Any frame beyond `seqLength` raises an error.
- Only the class `pedestrian` can be evaluated, and a tracker file with a class greater than 1 errors in preprocessing. Evaluate players and the ball as **separate sequences**, each written with class 1.
- The README advises `--DO_PREPROC False` unless you want distractor removal.
- Run it with `python scripts/run_mot_challenge.py --BENCHMARK MOT17 --SPLIT_TO_EVAL train --TRACKERS_TO_EVAL ours --METRICS HOTA CLEAR Identity --USE_PARALLEL False`.
- It was tested on Python 3.7. Old NumPy aliases such as `np.float` may break it on NumPy 1.24 and later (unverified for the current master). That is one more reason to use `trackers eval` day to day.
- Roboflow `trackers eval` takes either a single sequence (`--gt`, `--predictions`) or folders (`--gt_dir <root>/<seq>/gt/gt.txt` plus `--predictions_dir results/<seq>.txt`).
  - It offers `--metrics` CLEAR/HOTA/Identity, `--threshold` (IoU, default 0.5, used for CLEAR and Identity), `--class_config mot17` and `--output results.json`.
- py-motmetrics (MIT, `pip install motmetrics`) is an alternative: `python -m motmetrics.apps.eval_motchallenge gt_root preds_root`. Its accumulator also accepts arbitrary distance matrices, so it works in pitch space too.

### 2. Pitch-space metrics

- **GS-HOTA** (SoccerNet Game State Reconstruction) computes `Sim = LocSim × IdSim`, where `LocSim = e^{ln(0.05)·‖P−G‖²/τ²}` and τ = 5 m.
  - HOTA is integrated over α ∈ [0.05, 0.95] in steps of 0.05, so pairs more than 5 m apart never match.
  - IdSim is 1 only if role, team and jersey all match. Attributes missing from the GT are ignored.
  - GT and predictions store `bbox_pitch.{x,y}_bottom_middle` in metres, with the origin at the centre spot.
  - Evaluate with `python3 ./scripts/run_soccernet_gs.py --GT_FOLDER ... --TRACKERS_FOLDER ... --TRACKER_SUB_FOLDER "" --SPLIT_TO_EVAL test` from sn-trackeval (MIT). The full pipeline repo sn-gamestate is GPL-3.0.
  - The paper's ablation shows that turning off the pitch term falls back to plain image-IoU HOTA.
  - Its failure example is a calibration failure that put athletes in the wrong place: GS-HOTA 0.23% on that frame, against 49.69% on a good one.
- **Our own simpler metrics** (code below):
  - (a) Per frame, run Hungarian matching on Euclidean pitch distance with a 5 m gate. Report precision, recall and F1, plus mean, median and p95 position error in metres over the matches.
  - (b) **ID accuracy per tracklet**: map each predicted track to its majority GT id, then compute the share of the tracklet's frames whose matched GT equals that id.
  - (c) Speed and distance errors per GT player, computed through the same matches.

### 3. Speed and distance from noisy tracks

- **How FIFA EPTS validates** (Test Manual, Aug 2025 version):
  - **Reference systems:** a 40-camera Vicon system at 100 Hz over a capture area of at least 35 × 25 m, using a 6-marker centre of mass, plus a full-pitch stationary-position test.
  - **Processing of provider data:**
    - Resample to 50 Hz by linear interpolation.
    - Rotate into Vicon axes by brute force: 1° steps, then 0.01° refinement.
    - Recompute speed from x/y with a **three-point central difference plus a 2nd-order low-pass Butterworth at 1 Hz**, to cancel filter phase effects.
    - Synchronise by cross-correlation, then shift ±50 samples and keep the shift with the lowest RMSD.
  - **Metrics:** position error is the straight-line x/y distance, and agreement is reported as RMSD and mean difference.
  - **Ratings:** five levels (well-above to well-below), applied **per velocity band** (0-5, 5-10, 10-15, 15-20, 20-25, 25+ km/h). The thresholds are box-plot cut-offs drawn from more than 1,000,000 data points across more than 30 systems and are reviewed every year. The manual deliberately does not publish fixed tolerances (its threshold table is a figure, not text).
  - **Ball data** is smoothed with a 5 Hz Butterworth filter.
- **Smoothing choices for us:**
  - Savitzky-Golay (`scipy.signal.savgol_filter(..., deriv=1, delta=1/fps)`) gives position and speed in one pass with low peak distortion.
  - A constant-velocity Kalman filter plus an RTS smoother handles gaps and ID switches better.
  - A Butterworth `filtfilt` matches the EPTS method.
  - **Bias:** differentiating noisy positions inflates the *maximum* speed, because the noise peaks get picked. Low-pass filtering flattens real sprint peaks and lowers it. The net sign depends on the noise level and the cut-off. Because we have truth, run all three filters and pick the one whose top-speed error is closest to zero on clean renders. Report **top-speed error** and **distance error %** per band, the way EPTS does.
  - **Fairness rule:** apply the same filter to truth and estimate before comparing, or compare against raw simulator speed and say which one you used.

### 4. Camera calibration from frames

| repo | licence | how it runs | output | reported accuracy |
|---|---|---|---|---|
| NBJW (mguti97/No-Bells-Just-Whistles) | GPL-2.0 | `python inference.py --weights_kp SV_kp --weights_line SV_lines --input_path x.mp4 --input_type video`; CUDA default, `--device cpu` works; resizes to 960×540 | full camera (focal length, principal point, position, rotation) → 3×4 P | SN22-test-center: Acc@5 75.3, Acc@10 89.4, completeness 97.8, final score 73.7. WC14 (trained on SN): IoU_whole 89.4, projection error 1.23 m mean / 0.58 m median. TS-WorldCup: 0.30 / 0.24 m |
| PnLCalib (mguti97/PnLCalib) | GPL-2.0 | same CLI plus `--pnl_refine` (line-based non-linear refinement, optional lens distortion) | same | no figures in README; journal version in CVIU 2026 |
| TVCalib (mm4spa/tvcalib) | MIT | conda env, segmentation weights, `inference.ipynb` | camera params | SN22-test-center (from the NBJW paper): Acc@5 54.8, completeness 100 |

- **SoccerNet calibration metric** (sn-calibration `evaluate_camera.py`):
  - Pitch-line points are reprojected at 960×540.
  - A line class counts as correct only if *all* its GT points lie within t px (5 by default) of the predicted polyline.
  - Final score = completeness × accuracy (JaC@t).
- **Easiest to run:** NBJW, a single script plus weights.
  - Because it is GPL-2.0, keep it as a separate tool or container invoked as a process, not vendored into our code (we have not had legal advice on this).
  - Get the homography from its output as `H = P[:, [0,1,3]]`. Check the SoccerNet world-axis convention (origin at the centre, z sign) by projecting the four corners (unverified).
- **What to expect on our frames:** the 0.5-1.2 m projection errors above were measured on real broadcast footage. Our renders have clean lines but a domain gap. Measure the error rather than assume it, and expect failures on tight zooms with few lines (the GS-HOTA paper's 0.23% case).
- **Comparing with our true camera:**
  - Sample a 1 m grid over the pitch and keep the points inside the true frame.
  - Project the points to pixels with H_true, then back to the pitch with H_est⁻¹.
  - Report the mean and p95 error **in metres**, plus the share of frames under 1 m.
  - This is exactly the error our name tags and Chalk Talk drawings will inherit.

### 5. Degradation sweep (the demo experiment)

- **Factors:** apply one at a time from a clean baseline, then add one combined "bad broadcast" preset.
  - Blur: ffmpeg `gblur=sigma` 0/1/2/3/4.
  - Compression: CRF 18/23/28/33/38.
  - Occlusion: render-time density, i.e. a set-piece cluster, or 0/10/20/30% of players with random occluder patches.
  - Optionally zoom level.
- **Seeds and cost:** 3 match seeds × 60 s per level. Render each master once. Degrading with ffmpeg is cheap, and only the CV pass re-runs.
- **Outputs per run:**
  - event F1 at δ = 1 s;
  - HOTA and IDF1;
  - pitch-space position error (p50/p95);
  - top-speed error and distance error %;
  - calibration reprojection error in metres.
  - Each output is computed twice, once with oracle calibration and once with CV calibration.
- **Plot:** one row per factor and one column per metric, as small multiples sharing the y axis per column.
  - x = level, y = metric, two lines (oracle and CV) with min-max bands across seeds.
  - Draw a horizontal reference line for any threshold we use on screen, for example "speed tag shown if error < x".

## So what for us

- **Stages:** this is the **Interpret** truth layer and the `truth_check` field of the shared cue JSON. A cue only gets `truth_check: pass` if the metric's measured error at the current degradation level is under its threshold.
- **A TwinCast:** this grader is the proof that the CV works. Write MOT GT from the same `renderFrame(i)` projection that produces the labels (see 06). Score with `trackers eval`, plus our own pitch-metre grader, plus event F1 (05).
- **B Speed Trap:** adopt the EPTS speed chain (central difference plus a 1 Hz Butterworth) so we can say "processed like FIFA's EPTS test". Show error per velocity band.
- **D Chalk Talk:** use the grid reprojection error to decide when to hide drawings, for example when the CV camera error is above 1 m (our threshold, to tune).
- **E Realism Bench:** the degradation-sweep figure is the headline chart of the realism report.

**Recommendation:**

1. Day 1: build the MOT writer, `trackers eval`, and the pitch grader against oracle tracks. A perfect score is the sanity check.
2. Day 2: NBJW in its own container, emitting per-frame H.
3. Day 3-4: run the sweep and produce the figure.

Keep TrackEval and GS-HOTA as "official-metric" cross-checks, not as day-to-day tools.

## Reuse: code & links

```python
# grader.py  (numpy, scipy, opencv-python)
import numpy as np, os, cv2
from scipy.optimize import linear_sum_assignment
from scipy.signal import butter, filtfilt, savgol_filter

def write_mot(rows, seq_dir, seq_len, gt=True):
    """rows: iterable of (frame0, track_id, x1, y1, x2, y2, score, vis) from the projection/tracker."""
    path = os.path.join(seq_dir, "gt", "gt.txt") if gt else seq_dir + ".txt"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        for fr, tid, x1, y1, x2, y2, s, vis in rows:
            w, h = x2 - x1, y2 - y1
            if w <= 1 or h <= 1: continue                     # off-screen / degenerate
            if gt:   # consider-flag=1, class=1 (pedestrian), visibility
                f.write(f"{fr+1},{tid},{x1:.2f},{y1:.2f},{w:.2f},{h:.2f},1,1,{vis:.2f}\n")
            else:
                f.write(f"{fr+1},{tid},{x1:.2f},{y1:.2f},{w:.2f},{h:.2f},{s:.3f},-1,-1,-1\n")
    if gt:
        with open(os.path.join(seq_dir, "seqinfo.ini"), "w") as f:
            f.write(f"[Sequence]\nname={os.path.basename(seq_dir)}\nseqLength={seq_len}\n"
                    "frameRate=25\nimWidth=1280\nimHeight=720\nimExt=.jpg\n")
# then: trackers eval --gt_dir out/gt --predictions_dir out/pred --metrics '[CLEAR,HOTA,Identity]' --output res.json

def pitch_match(gt, pr, gate_m=5.0):
    """gt, pr: dict frame -> (ids[N], xy[N,2] metres). Returns P/R/F1, errors, ID accuracy per tracklet."""
    errs, tp, fp, fn, pairs = [], 0, 0, 0, []
    for fr in sorted(set(gt) | set(pr)):
        gi, gxy = gt.get(fr, ([], np.zeros((0, 2)))); pi, pxy = pr.get(fr, ([], np.zeros((0, 2))))
        if len(gi) and len(pi):
            D = np.linalg.norm(gxy[:, None] - pxy[None], axis=2)
            r, c = linear_sum_assignment(np.where(D > gate_m, 1e6, D))
            ok = D[r, c] <= gate_m; r, c = r[ok], c[ok]
        else:
            r = c = np.array([], int)
        tp += len(r); fn += len(gi) - len(r); fp += len(pi) - len(r)
        errs += list(np.linalg.norm(gxy[r] - pxy[c], axis=1))
        pairs += [(pi[j], gi[i]) for i, j in zip(r, c)]
    # ID accuracy per tracklet: majority GT id per predicted track
    from collections import Counter, defaultdict
    by_trk = defaultdict(Counter)
    for p, g in pairs: by_trk[p][g] += 1
    id_acc = {p: cnt.most_common(1)[0][1] / sum(cnt.values()) for p, cnt in by_trk.items()}
    P, R = tp / max(tp + fp, 1), tp / max(tp + fn, 1); e = np.array(errs) if errs else np.array([np.nan])
    return dict(precision=P, recall=R, f1=2*P*R/max(P+R, 1e-9), err_mean=e.mean(),
                err_p50=np.median(e), err_p95=np.percentile(e, 95),
                id_acc_mean=np.mean(list(id_acc.values())) if id_acc else np.nan)

def speed_epts(xy, fps):
    """EPTS-style: 3-point central difference then 2nd-order 1 Hz low-pass Butterworth (zero-phase)."""
    v = np.gradient(xy, 1 / fps, axis=0)                      # central difference inside
    s = np.linalg.norm(v, axis=1)
    b, a = butter(2, 1.0, fs=fps); return filtfilt(b, a, s)

def speed_savgol(xy, fps, win=13, poly=2):
    v = savgol_filter(xy, win, poly, deriv=1, delta=1 / fps, axis=0); return np.linalg.norm(v, axis=1)

def speed_errors(true_xy, est_xy, fps, f=speed_epts):
    st, se = f(true_xy, fps), f(est_xy, fps)
    dist_t = np.linalg.norm(np.diff(true_xy, axis=0), axis=1).sum()
    dist_e = np.linalg.norm(np.diff(est_xy, axis=0), axis=1).sum()
    return dict(top_speed_err=se.max() - st.max(), speed_rmsd=np.sqrt(np.mean((se - st) ** 2)),
                dist_err_pct=100 * (dist_e - dist_t) / dist_t)

def H_from_P(P):              # 3x4 camera matrix, pitch plane z=0 -> image homography
    return P[:, [0, 1, 3]] / P[2, 3]

def reproj_error_m(H_true, H_est, w=1280, h=720, L=105, W=68, step=1.0):
    """H_*: pitch(m, origin centre) -> image px. Grid points visible in the true view,
    projected with H_true, back-projected with H_est^-1; error in metres."""
    xs, ys = np.meshgrid(np.arange(-L/2, L/2 + 1e-6, step), np.arange(-W/2, W/2 + 1e-6, step))
    g = np.stack([xs.ravel(), ys.ravel()], 1).astype(np.float64)[:, None]
    px = cv2.perspectiveTransform(g, H_true)[:, 0]
    vis = (px[:, 0] >= 0) & (px[:, 0] < w) & (px[:, 1] >= 0) & (px[:, 1] < h)
    if not vis.any(): return dict(mean=np.nan, p95=np.nan, n=0)
    back = cv2.perspectiveTransform(px[vis][:, None], np.linalg.inv(H_est))[:, 0]
    e = np.linalg.norm(back - g[vis, 0], axis=1)
    return dict(mean=e.mean(), p95=np.percentile(e, 95), n=int(vis.sum()))
```

```python
# sweep.py — skeleton: render once, degrade with ffmpeg, re-run CV, grade, collect a tidy table
import itertools, subprocess, pandas as pd
LEVELS = {"blur": [0, 1, 2, 3, 4], "crf": [18, 23, 28, 33, 38]}
def degrade(src, dst, blur=0, crf=18):
    vf = f"gblur=sigma={blur}" if blur else "null"
    subprocess.run(["ffmpeg", "-y", "-i", src, "-vf", vf, "-c:v", "libx264", "-crf", str(crf), dst], check=True)
rows = []
for seed in [1, 2, 3]:
    master = f"renders/seed{seed}.mp4"                     # occlusion levels = separate renders
    for factor, levels in LEVELS.items():
        for lv in levels:
            out = f"work/s{seed}_{factor}{lv}.mp4"; degrade(master, out, **{factor: lv})
            for calib in ["oracle", "cv"]:
                m = run_cv_and_grade(out, seed, calib)    # ours: detect+track -> events -> grader.py
                rows.append(dict(seed=seed, factor=factor, level=lv, calib=calib, **m))
pd.DataFrame(rows).to_csv("sweep.csv", index=False)
# plot: small multiples, rows=factor, cols=[event_f1, hota, err_p95, top_speed_err];
#       x=level, one line per calib (median over seeds), band = min-max across seeds.
```

**Links:**

- Evaluators:
  - TrackEval: https://github.com/JonathonLuiten/TrackEval
  - trackers eval: https://trackers.roboflow.com/develop/evaluations/evaluate/
  - sn-trackeval: https://github.com/SoccerNet/sn-trackeval
  - py-motmetrics: https://github.com/cheind/py-motmetrics
- Calibration tools:
  - NBJW: https://github.com/mguti97/No-Bells-Just-Whistles
  - PnLCalib: https://github.com/mguti97/PnLCalib
  - TVCalib: https://github.com/mm4spa/tvcalib
  - SoccerNet calibration devkit: https://github.com/SoccerNet/sn-calibration

## Sources

- TrackEval README (MIT; metrics; `--DO_PREPROC False` advice) — https://github.com/JonathonLuiten/TrackEval — accessed 20 Oct 2026
- TrackEval MOTChallenge format docs — https://github.com/JonathonLuiten/TrackEval/blob/master/docs/MOTChallenge-Official/Readme.md — accessed 20 Oct 2026
- TrackEval `mot_challenge_2d_box.py` (column use, folder layout, seqinfo) — https://raw.githubusercontent.com/JonathonLuiten/TrackEval/master/trackeval/datasets/mot_challenge_2d_box.py — accessed 20 Oct 2026
- Roboflow trackers, Evaluate docs — https://trackers.roboflow.com/develop/evaluations/evaluate/ — accessed 20 Oct 2026
- py-motmetrics README — https://github.com/cheind/py-motmetrics — accessed 20 Oct 2026
- SoccerNet sn-gamestate README (GS-HOTA, calibration options, GPL-3.0) — https://github.com/SoccerNet/sn-gamestate — accessed 20 Oct 2026
- SoccerNet sn-trackeval README — https://github.com/SoccerNet/sn-trackeval — accessed 20 Oct 2026
- Somers et al., "SoccerNet Game State Reconstruction" (LocSim formula, τ = 5 m, 22.26% baseline, JSON example) — https://arxiv.org/pdf/2404.11335 — accessed 20 Oct 2026
- SoccerNet sn-calibration README and `src/evaluate_camera.py` — https://github.com/SoccerNet/sn-calibration — accessed 20 Oct 2026
- SoccerNet camera calibration task page — https://www.soccer-net.org/tasks/camera-calibration — accessed 20 Oct 2026
- NBJW repo, `inference.py`, LICENSE (GPL-2.0) — https://github.com/mguti97/No-Bells-Just-Whistles — accessed 20 Oct 2026
- Gutiérrez-Pérez & Agudo, "No Bells, Just Whistles" (results tables, v1 HTML) — https://arxiv.org/html/2404.08401v1 — accessed 20 Oct 2026
- PnLCalib repo — https://github.com/mguti97/PnLCalib — accessed 20 Oct 2026
- TVCalib repo — https://github.com/mm4spa/tvcalib — accessed 20 Oct 2026
- FIFA, EPTS testing process — https://inside.fifa.com/technical/football-technology/standards/epts/epts-testing-process — accessed 20 Oct 2026
- FIFA Quality Programme for EPTS, Test Manual (Aug 2025 version) — https://digitalhub.fifa.com/m/6ae31e7e4962aa3f/original/Handbook-of-Test-Methods-for-EPTS-devices.pdf — accessed 20 Oct 2026
- SciPy `savgol_filter` docs — https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.savgol_filter.html — accessed 20 Oct 2026
