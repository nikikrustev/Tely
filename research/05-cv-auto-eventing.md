# 05 — Computer vision for football auto-eventing (detection, tracking, pitch mapping, event detection)

_Accessed/compiled: 20 Oct 2026 · Priority area: TwinCast CV loop (Ingest from video -> Interpret), grading vs ground truth_

## TL;DR

- **Use an Apache/MIT stack instead of Ultralytics.** Use RF-DETR (Apache-2.0 for the N/S/M/L sizes) or RT-DETR/YOLOX (Apache-2.0) for detection. Pair it with Roboflow `trackers` (Apache-2.0: ByteTrack, OC-SORT, BoT-SORT and others) and `supervision` (MIT) for annotators and utilities. Ultralytics YOLO is AGPL-3.0, and Ultralytics says that covers trained weights and SaaS/API use. A public hackathon repo can comply only if the whole project is AGPL-licensed.
- **Watch the ByteTrack breaking change.** `sv.ByteTrack` was removed in supervision 0.31.0 (released 16 Oct 2026). The Roboflow `sports` soccer example still calls `sv.ByteTrack(...).update_with_detections`. Either pin `supervision<0.31` or switch to `trackers.ByteTrackTracker().update()`.
- **Our renderer gives us exact labels.** We render the video ourselves, so we know each frame's camera matrix exactly. Projecting the simulator's 3D positions gives pixel-perfect boxes, IDs and a ground-plane homography for free. That covers training data, ground truth for grading, and an "oracle calibration" baseline to compare against keypoint-based homography.
- **Events come from ball + possession, not from video.** Use nearest-player possession (Vidal-Codina et al. use a 0.5–1 m possession radius) plus possession-loss/gain rules. Grade the result with SoccerNet-style matching: one-to-one, same class, within a time tolerance of δ = 1 s. For tracking, use HOTA, or GS-HOTA in pitch metres.
- **Azure GPU options.** Azure Container Apps serverless GPU offers T4 and A100 with per-second billing and scale-to-zero. T4 is available in West Europe, Sweden Central, France Central and Italy North, among others. Azure ML serverless jobs run when you leave out `compute`, and both services need GPU quota.

## Findings

### 1. Roboflow `sports` + `supervision` (what is reusable)

| Item | What it gives us | Licence / caveat |
|---|---|---|
| `github.com/roboflow/sports`, `examples/soccer/main.py` | Six modes: `PITCH_DETECTION`, `PLAYER_DETECTION`, `BALL_DETECTION`, `PLAYER_TRACKING`, `TEAM_CLASSIFICATION`, `RADAR` | Repo is MIT, but it uses `ultralytics` YOLOv8 and its downloaded `.pt` weights are YOLOv8, so treat them as AGPL |
| `sports/common/team.py` `TeamClassifier` | `google/siglip-base-patch16-224` embeddings (mean of the last hidden state), then `umap.UMAP(n_components=3)`, then `KMeans(n_clusters=2)`. Has `fit(crops)` and `predict(crops)` | Reusable as is. Crops are sampled every 60 frames. Goalkeepers are assigned to the nearer team centroid |
| `sports/common/view.py` `ViewTransformer` | `cv2.findHomography` from source to target points, plus `transform_points` and `transform_image` | Trivial to copy. Keypoints are filtered with `x>1 & y>1`, not by confidence |
| `sports/configs/soccer.py` `SoccerPitchConfiguration` | 32 pitch vertices in **cm** on a 12000×7000 (120×70 m) pitch | Scale it to our simulator's pitch size |
| `sports/common/ball.py` `BallTracker(buffer_size=20)` + `sv.InferenceSlicer(slice_wh=(640,640))` | Small-ball detection by tiling the frame, then NMS at threshold 0.1 | Good pattern for a small ball |
| Datasets (Roboflow Universe, built from the DFL Bundesliga Kaggle data) | player / ball / pitch-keypoint sets, each with a Colab notebook | Real footage. Useful for pretraining only, not as "data" in the demo (the challenge requires synthetic data) |

`supervision` (MIT, v0.31.0) still supplies `sv.Detections`, the annotators (Box, Ellipse, Label, Triangle), `get_video_frames_generator`, `VideoSink`, `InferenceSlicer` and `KeyPoints`. Tracking now lives in the separate **`trackers`** package (Apache-2.0, v2.6.1, Python 3.10+). Every tracker in it shares the same `update(detections)` interface, and it ships a `trackers eval` CLI that reports CLEAR, HOTA and Identity metrics.

### 2. Detectors (licence + speed only where the source states it)

| Model | Licence | COCO AP50:95 | T4 speed (source) |
|---|---|---|---|
| YOLO11n / s / m | AGPL-3.0 or Enterprise | 39.5 / 47.0 / 51.5 | 1.5 / 2.5 / 4.7 ms, TensorRT10 (Ultralytics docs) |
| RF-DETR Nano / Small / Medium / Large | **Apache-2.0** | 48.4 / 53.0 / 54.7 / 56.5 | 2.3 / 3.5 / 4.4 / 6.8 ms, T4 TensorRT FP16, batch size 1 (rf-detr README) |
| RF-DETR Atto/Femto/Pico/XL/2XL | PML 1.0 (not Apache) | – | – |
| RT-DETRv2-S / M / L | **Apache-2.0** | 48.1 / 51.9 / 53.4 | 217 / 145 / 108 FPS, T4 TensorRT FP16 |
| YOLOX-s / m | **Apache-2.0** | 40.5 / 46.9 | 9.8 / 12.3 ms on a **V100** (no T4 figure) |

RF-DETR fine-tunes with `model.train(dataset_dir=..., epochs=..., batch_size="auto", lr=1e-4, output_dir=...)`. It auto-detects COCO or YOLO dataset layout. All RF-DETR segmentation models and the keypoint preview are also Apache-2.0, which gives us a non-AGPL route to pitch-keypoint detection.

### 3. Trackers and ID switches

| Tracker | Idea | Licence | HOTA, `trackers` defaults (SportsMOT / SoccerNet\*) |
|---|---|---|---|
| ByteTrack (arXiv 2110.06864) | Associates low-score boxes too, to recover occluded objects | MIT | 73.0 / 84.0 |
| OC-SORT (arXiv 2203.14360) | Observation-centric re-update, for non-linear motion | MIT | 71.7 / 78.4 |
| BoT-SORT (arXiv 2206.14651) | Camera-motion compensation plus optional ReID | MIT | 73.8 / 84.5 |
| McByte | Needs SAM/Cutie (heavy) | – | 76.5 / 85.0 |

\*SoccerNet scores use oracle ground-truth boxes; SportsMOT scores use a YOLOX detector.

The broadcast camera pans, which favours BoT-SORT's camera-motion compensation. ID switches mostly happen in clusters (set pieces, duels) and when players re-enter the frame.

There are two fixes for ID switches:

- **Jersey OCR at tracklet level.** Koshkina & Elder (CVPRW 2024), `mkoshkina/jersey-number-pipeline`, chains re-ID outlier removal, a legibility classifier, ViTPose-guided crops, PARSeq text recognition and tracklet voting. Its licence is CC BY-NC 3.0, so it is non-commercial only. The best SoccerNet 2023 jersey-challenge entry reached 92.85% tracklet accuracy, against a random baseline of 3.93%.
- **Team + pitch-position consistency.** Re-link tracks that disappear and reappear within a few metres in pitch coordinates.

### 4. Homography and the known-camera trick

**Real-footage path.** Detect pitch keypoints, then `findHomography(image_pts, pitch_pts)`. Map each player's bottom-centre point to the pitch with `perspectiveTransform`. The SoccerNet GSR baseline uses TVCalib for this step.

**Our synthetic path.** Three.js `Vector3.project(camera)` is literally `applyMatrix4(camera.matrixWorldInverse).applyMatrix4(camera.projectionMatrix)`. That maps world points to NDC in [-1,1], and the pixel position is `px = (x+1)/2·W`, `py = (1−y)/2·H`. So per frame:

1. Export `projectionMatrix` and `matrixWorldInverse` per frame as JSON from the renderer.
2. **Auto-label boxes.** Project the 8 corners of each player's 3D bounding box (or a cylinder of 0.35 m radius × 1.85 m height). The 2D box is the min/max of the projected points. Drop points that fall behind the camera (w ≤ 0) and clip the box to the image. The ball becomes a box around its projected centre plus a projected radius. The player ID, team and jersey number come straight from the simulator, which gives perfect MOT ground truth.
3. **Pitch back-projection.** For the ground plane (y = 0 in Three.js), the 3×3 homography comes straight from `M = P·V`. Keep columns 0, 2 and 3 (x, z, translation) and rows 0, 1 and 3 (clip x, y, w), then left-multiply by the NDC→pixel matrix `[[W/2,0,W/2],[0,-H/2,H/2],[0,0,1]]`. Invert it to map pixels to pitch coordinates. An easier route is to project the 4 pitch corners and call `cv2.findHomography`.
4. **Grading CV calibration.** Compare the CV-estimated H with the true H by reprojecting a grid of pitch points and taking the mean error in metres.

### 5. Ball tracking and events

- **Small-object problem.** The ball covers a few pixels, blurs and gets occluded. Mitigations:
  - tile the frame with `InferenceSlicer` (the SAHI pattern);
  - use a dedicated ball class or model;
  - use temporal heatmap models such as TrackNet (arXiv 1907.03698), which was built for tiny, fast balls.
- **Filling gaps.** Linearly interpolate gaps of up to about 10 frames in pitch coordinates. Smooth with Savitzky-Golay: Vidal-Codina et al. use a 2nd-order, 7-frame window, about 0.25 s at 25 Hz.
- **Rule-based events** (Vidal-Codina et al., arXiv 2202.00804, MIT Sports Lab and FIFA):
  - Possession means the ball is inside a player's possession zone: 0.5 m or 1 m depending on the data provider.
  - A duel is two or more opponents within 1 m.
  - Possession gain requires a change in ball direction or speed.
  - A **shot** is a possession loss followed by a goal, corner, goal kick or save. A **pass** is any other possession loss.
  - The authors report detection rates above 90% for most event types.
  - A 2024 PLOS ONE follow-up (Bischofberger et al.) warns that F-scores drop to 0.71 for passes and 0.65 for shots when event and positional data are not linked. In other words, timing extraction is the hard part.
- **Learned spotting.** SoccerNet Ball Action Spotting has 12 ball event classes and is ranked by mAP@1 s. The 2025 edition, Team Ball Action Spotting, also requires the team and uses Team-mAP@1 s. Matching is unique, same class, within δ.

### 6. SoccerNet datasets and metrics we can borrow

| Benchmark | Data | Metric | Reuse for TwinCast |
|---|---|---|---|
| SoccerNet-Tracking | 200 × 30 s clips from 12 games; players, GKs, refs, ball; download via the `SoccerNet` pip package | HOTA = √(DetA·AssA), via TrackEval | Score our tracker in image space |
| SoccerNet-GSR (`sn-gamestate`, GPL-3.0) | 200 clips, 25 fps, 750 frames each, 2.36M athlete pitch positions with role, team and jersey | **GS-HOTA**: Sim = LocSim × IdSim, LocSim = exp(ln(0.05)·d²/τ²) with τ = 5 m; IdSim = 1 only if role, team and jersey all match | Grade our pitch-coordinate output plus identity. Baseline 22.26 on test; 2024 winner 63.81 |
| Jersey number (2023) | tracklets | accuracy over classes 0–99 plus −1 for not visible | Grade our OCR re-ID |
| Ball Action Spotting | 12 classes | mAP@δ = 1 s | Grade our events |

## So what for us

- **Pipeline stages:** Ingest (video -> tracks -> events), Interpret (possession, speeds), and Truth-check (the `truth_check` field in the cue JSON).
- **Ideas helped:**
  - **A TwinCast:** this is its core loop.
  - **B Speed Trap:** speeds come from pitch-coordinate tracks.
  - **D Chalk Talk:** the homography is needed to draw on the pitch.
  - **E Realism Bench:** CV-vs-truth scores become part of the realism report.
  - **05 Set-Piece X-Ray**, **04 Duel Card**: the duel zone comes from the same possession logic.

**Recommendations:**

1. **Stack:** RF-DETR-S or M (Apache-2.0) fine-tuned on frames rendered by our own simulator and auto-labelled from the camera matrices. Add `trackers` (ByteTrack first, then try BoT-SORT for camera pans) and `supervision>=0.31` annotators. Copy `TeamClassifier` and `ViewTransformer` from `sports` (MIT). Do not ship its YOLOv8 weights. If we use Ultralytics anyway, license the whole repo AGPL-3.0, link the source from the hosted demo, and say so in the README.
2. **Two calibration modes:** an "oracle" mode (true camera homography) and a "CV" mode (keypoint homography). Showing both scores is honest, and it is a strong demo beat.
3. **Grader metrics:**
   - event P/R/F1 per class at δ = 1 s (and 0.5 s);
   - HOTA and IDF1 via `trackers eval` (we write MOT-format ground truth from the projection);
   - a GS-HOTA-style pitch-metre similarity with τ = 5 m;
   - speed MAE (m/s) and distance error (%) per player;
   - ball and shot-speed absolute error;
   - jersey or ID accuracy per tracklet.
4. **Compute:** train on Azure ML serverless (Spot tier is fine for this). Run inference as an ACA job on a serverless T4. Create the workload-profiles environment in Sweden Central or West Europe first, then check its Quota page. Enterprise-agreement and pay-as-you-go subscriptions have T4/A100 quota by default. Others must request "Managed Environment Consumption T4 GPUs". Do this on day 1.
5. **Thresholds:** possession radius and speed-change thresholds are ours to tune. Start with 1.0–1.5 m because CV is noisy. Report the values used, because they are not sourced constants.

## Reuse: code & links

**Detector + ByteTrack + pitch mapping over a video** (`pip install rfdetr trackers "supervision>=0.31"`)

```python
import cv2, numpy as np, supervision as sv
from rfdetr import RFDETRMedium            # Apache-2.0 (N/S/M/L)
from trackers import ByteTrackTracker      # Apache-2.0; update() not update_with_detections()

model = RFDETRMedium()                     # fine-tuned: pass your checkpoint (arg name per rf-detr docs, unverified)
tracker = ByteTrackTracker()
ellipse, label = sv.EllipseAnnotator(), sv.LabelAnnotator()
H = np.load("frame_homography.npy")        # 3x3 image->pitch(m); per-frame if camera moves

info = sv.VideoInfo.from_video_path("in.mp4")
rows = []
with sv.VideoSink("out.mp4", info) as sink:
    for f, frame in enumerate(sv.get_video_frames_generator("in.mp4")):
        det = model.predict(frame[:, :, ::-1].copy(), threshold=0.4)   # returns sv.Detections (expects RGB)
        det = tracker.update(det)                                      # adds tracker_id (unverified attr for all trackers)
        feet = det.get_anchors_coordinates(sv.Position.BOTTOM_CENTER).reshape(-1, 1, 2).astype(np.float32)
        pitch = cv2.perspectiveTransform(feet, H).reshape(-1, 2) if len(det) else np.empty((0, 2))
        for tid, cls, (x, y) in zip(det.tracker_id, det.class_id, pitch):
            rows.append((f, f / info.fps, int(tid), int(cls), float(x), float(y)))
        frame = ellipse.annotate(frame.copy(), det)
        frame = label.annotate(frame, det, labels=[f"#{t}" for t in det.tracker_id])
        sink.write_frame(frame)
# rows -> pandas: interpolate ball gaps, Savitzky-Golay smooth, speeds = diff(xy)/dt
```

**Auto-label from a known Three.js camera** (camera JSON exported per frame, matrices column-major as in three.js `elements`)

```python
import numpy as np
def project(P_elems, Vinv_elems, pts_world, W, Hh):
    P  = np.array(P_elems).reshape(4, 4).T; V = np.array(Vinv_elems).reshape(4, 4).T
    X  = np.c_[pts_world, np.ones(len(pts_world))] @ (P @ V).T          # clip space
    ok = X[:, 3] > 0
    ndc = X[:, :3] / X[:, 3:4]
    px = np.c_[(ndc[:, 0] + 1) / 2 * W, (1 - ndc[:, 1]) / 2 * Hh]
    return px, ok
def bbox_for_player(P, Vinv, x, z, W, Hh, r=0.35, h=1.85):              # Three.js: y is up, pitch on x-z
    c = np.array([[x+dx, y, z+dz] for dx in (-r, r) for dz in (-r, r) for y in (0, h)])
    px, ok = project(P, Vinv, c, W, Hh)
    if not ok.all(): return None
    x0, y0 = px.min(0); x1, y1 = px.max(0)
    return [max(0, x0), max(0, y0), min(W, x1), min(Hh, y1)]
# Ground-truth image->pitch homography: project 4 pitch corners, then cv2.findHomography(px_corners, pitch_corners_m)
```

**Event matching F1 with a tolerance window** (one-to-one, same class, optimal assignment, SoccerNet-style)

```python
import numpy as np
from scipy.optimize import linear_sum_assignment

def event_f1(pred, gt, tol=1.0, keys=("type",)):
    """pred/gt: lists of dicts with 't' (seconds) and the fields in `keys` (e.g. type, team, player).
    A match needs equal keys and |dt| <= tol; each event is matched at most once."""
    tp, dts = 0, []
    groups = {tuple(e[k] for k in keys) for e in pred + gt}
    for g in groups:
        p = [e["t"] for e in pred if tuple(e[k] for k in keys) == g]
        q = [e["t"] for e in gt   if tuple(e[k] for k in keys) == g]
        if not p or not q: continue
        D = np.abs(np.subtract.outer(p, q))
        C = np.where(D <= tol, D, 1e6)                       # forbid out-of-window pairs
        r, c = linear_sum_assignment(C)
        hit = C[r, c] <= tol
        tp += int(hit.sum()); dts += list(D[r, c][hit])
    fp, fn = len(pred) - tp, len(gt) - tp
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec  = tp / (tp + fn) if tp + fn else 0.0
    f1   = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"precision": prec, "recall": rec, "f1": f1, "tp": tp, "fp": fp, "fn": fn,
            "mean_abs_dt": float(np.mean(dts)) if dts else None}

# event_f1(cv_events, sim_events, tol=1.0, keys=("type", "team"))  -> Team-mAP-like strictness
```

**Azure ML serverless GPU training job** (omit `compute` to get serverless)

```python
from azure.ai.ml import MLClient, command
from azure.ai.ml.entities import JobResourceConfiguration
from azure.identity import DefaultAzureCredential
ml = MLClient(DefaultAzureCredential(), "<sub>", "<rg>", "<workspace>")
job = command(code="./train", command="python train_rfdetr.py --data ${{inputs.data}}",
              inputs={"data": "azureml:twincast-frames:1"}, environment="<gpu-env>@latest",
              queue_settings={"job_tier": "Spot"})
job.resources = JobResourceConfiguration(instance_type="Standard_NC4as_T4_v3", instance_count=1)  # VM name unverified; must have quota
ml.create_or_update(job)
```

Links:
- roboflow/sports: https://github.com/roboflow/sports
- roboflow/trackers: https://github.com/roboflow/trackers
- roboflow/supervision: https://github.com/roboflow/supervision
- RF-DETR: https://github.com/roboflow/rf-detr
- SoccerNet game-state reconstruction (`sn-gamestate`): https://github.com/SoccerNet/sn-gamestate
- SoccerNet tracking (`sn-tracking`): https://github.com/SoccerNet/sn-tracking
- Jersey number pipeline: https://github.com/mkoshkina/jersey-number-pipeline

## Sources

- roboflow/sports README — https://github.com/roboflow/sports — accessed 20 Oct 2026
- sports soccer example README — https://github.com/roboflow/sports/tree/main/examples/soccer — accessed 20 Oct 2026
- sports `main.py`, `team.py`, `view.py`, `soccer.py` — https://raw.githubusercontent.com/roboflow/sports/main/examples/soccer/main.py (and `sports/common/team.py`, `sports/common/view.py`, `sports/configs/soccer.py`) — accessed 20 Oct 2026
- supervision repo — https://github.com/roboflow/supervision — accessed 20 Oct 2026
- supervision deprecations (sv.ByteTrack removed in 0.31.0) — https://supervision.roboflow.com/latest/deprecated/ — accessed 20 Oct 2026
- supervision on PyPI (0.31.0, 16 Oct 2026, MIT) — https://pypi.org/project/supervision/ — accessed 20 Oct 2026
- roboflow/trackers README + HOTA table — https://github.com/roboflow/trackers — accessed 20 Oct 2026
- trackers docs quickstart / eval — https://trackers.roboflow.com/latest/ — accessed 20 Oct 2026
- trackers on PyPI (2.6.1, Apache-2.0) — https://pypi.org/project/trackers/ — accessed 20 Oct 2026
- RF-DETR README (licences, T4 latency) — https://github.com/roboflow/rf-detr — accessed 20 Oct 2026
- RF-DETR training docs — https://rfdetr.roboflow.com/latest/learn/train/ — accessed 20 Oct 2026
- Ultralytics YOLO11 docs (T4 TensorRT10 latency, AGPL) — https://docs.ultralytics.com/models/yolo11/ — accessed 20 Oct 2026
- Ultralytics licensing page — https://www.ultralytics.com/license — accessed 20 Oct 2026
- RT-DETR / RT-DETRv2 (Apache-2.0, T4 FPS) — https://github.com/lyuwenyu/RT-DETR — accessed 20 Oct 2026
- YOLOX (Apache-2.0) — https://github.com/Megvii-BaseDetection/YOLOX — accessed 20 Oct 2026
- ByteTrack (MIT, arXiv 2110.06864) — https://github.com/ifzhang/ByteTrack — accessed 20 Oct 2026
- OC-SORT (MIT, arXiv 2203.14360) — https://github.com/noahcao/OC_SORT — accessed 20 Oct 2026
- BoT-SORT (MIT, arXiv 2206.14651) — https://github.com/NirAharon/BoT-SORT — accessed 20 Oct 2026
- Koshkina & Elder, jersey-number-pipeline (CC BY-NC 3.0) — https://github.com/mkoshkina/jersey-number-pipeline — accessed 20 Oct 2026
- SoccerNet 2023 Challenges Results (jersey accuracy) — https://arxiv.org/pdf/2309.06006 — accessed 20 Oct 2026
- SoccerNet 2024 Challenges Results (ball action spotting mAP@1) — https://arxiv.org/pdf/2409.10587 — accessed 20 Oct 2026
- Somers et al., SoccerNet Game State Reconstruction / GS-HOTA — https://arxiv.org/html/2404.11335v1 — accessed 20 Oct 2026
- From Broadcast to Minimap (GSR 2024 results) — https://arxiv.org/pdf/2504.06357 — accessed 20 Oct 2026
- SoccerNet/sn-gamestate (GPL-3.0) — https://github.com/SoccerNet/sn-gamestate — accessed 20 Oct 2026
- SoccerNet/sn-tracking — https://github.com/SoccerNet/sn-tracking — accessed 20 Oct 2026
- Vidal-Codina et al., Automatic event detection in football using tracking data — https://ar5iv.arxiv.org/html/2202.00804 — accessed 20 Oct 2026
- Bischofberger et al., Event detection in football (PLOS ONE 2024) — https://pmc.ncbi.nlm.nih.gov/articles/PMC11025972 — accessed 20 Oct 2026 (via search summary)
- TrackNet (arXiv 1907.03698) — https://arxiv.org/abs/1907.03698v1 — accessed 20 Oct 2026 (via search summary)
- three.js `Vector3.project/unproject` source — https://raw.githubusercontent.com/mrdoob/three.js/dev/src/math/Vector3.js — accessed 20 Oct 2026
- Azure Container Apps serverless GPUs — https://learn.microsoft.com/en-us/azure/container-apps/gpu-serverless-overview — accessed 20 Oct 2026
- Azure ML serverless compute — https://learn.microsoft.com/en-us/azure/machine-learning/how-to-use-serverless-compute — accessed 20 Oct 2026
