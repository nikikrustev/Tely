# 06 — Rendering synthetic match video from tracking data (broadcast camera, capture to MP4, auto-labels)
_Accessed/compiled: 20 Oct 2026 · Priority area: Render stage (synthetic video) + Ingest/auto-eventing ground truth for TwinCast_

## TL;DR
- **Use Three.js in Chromium, driven by Playwright (Python) in lockstep.** The page exposes `window.renderFrame(i)`. Python calls it, saves the canvas as PNG and pipes the frames into ffmpeg for H.264. Frame `i` always shows time `i/fps`, so the output does not depend on wall-clock speed. Labels come out exactly aligned with frames.
- **Broadcast camera prior from the literature:** the main camera sits at roughly halfway, about 45 m behind the near touchline and about 17 m up. Pan is about ±35°, tilt is -5° to -15°, and focal length is 1000-6000 px at 1280x720. That works out to a vertical FOV of about 7°-40° (Chen & Little 2018, fit to World Cup 2014 frames). Build a pan/tilt/zoom follow-cam that aims at an exponentially smoothed ball position.
- **Auto-labels are nearly free.** Project the 8 corners of each player's 3D box with `Vector3.project(camera)`, take the min/max in pixels and write YOLO `class cx cy w h` (normalised). Also export `projectionMatrix x matrixWorldInverse` for each frame. The pitch-to-image homography is three of its columns.
- **Prior art says this works.** SoccerSynth-Detection (Unreal Engine, YOLO labels) trained YOLOv8n to scores comparable with real datasets. On SoccerNet-Tracking it scored 89.4 AP50, against 82.8 for a model trained on SportsMOT. Randomised lighting, grass and kits plus motion blur were the key additions. Unity Perception is discontinued, and Google Research Football was archived on 19 Aug 2026.
- **Realism is cheap to add:** sub-frame motion blur (render at 100 fps, `tmix` down to 25), ffmpeg `noise`, low-CRF-then-high-CRF re-encode, plus per-seed kits and lighting. Albumentations `MotionBlur` / `GaussNoise` can go on top at training time.

## Findings

### 1. Rendering options (for a 2-person, 2-week build)

| Option | Realism | Speed / determinism | Labels | Verdict |
|---|---|---|---|---|
| **Three.js (WebGL) + Playwright** | Low-medium (stylised capsules, can add GLTF players later) | Fast on GPU. Deterministic if you step time yourself | You compute them (projection), exact | **Pick this.** Same TypeScript stack as overlays; runs in ACA job with Chromium |
| Babylon.js | Similar to Three.js | Built-in `VideoRecorder` uses MediaRecorder + `canvas.captureStream()`, records **webm only**, default 7 s, real-time capture | Manual | Fine, but no advantage. Its recorder is not frame-exact |
| Blender (bpy, `blender -b file.blend -P script.py -a`) | High (EEVEE/Cycles, real lighting) | Slow per frame. Fully deterministic CLI: `-b` background, `-P` script, `-s/-e` frame range, `-o` output, `-E` engine, `-f` single frame | Manual via bpy camera matrices | Stretch goal for a "hero" clip, not the main pipeline |
| Unreal Engine (as SoccerSynth) | High | Heavy toolchain, Windows generator | Marketplace 2D-bbox plugin | Too heavy for 2 weeks |
| Unity Perception | High | — | Had labelers built in | **Discontinued:** "This project has been discontinued and is no longer supported by Unity." |
| Google Research Football renderer | Game-like 3D | Renders its own simulator episodes (`--render`, dump replays). Replaying *external* tracking is not documented (unverified) | No CV labels | Repo **archived 19 Aug 2026**. Skip |
| 2D animators: LaurieOnTracking `save_match_clip`, mplsoccer `FuncAnimation` | Top-down tactical only | matplotlib `FFMpegWriter(fps=25)` grabs frames, deterministic | n/a | Reuse for a "tactical cam" insert, not broadcast |
| immament/football-match-viewer (Three.js + R3F, TypeScript, CC-BY stadium model) | Medium | Real-time viewer | None | Good code reference for player rigs and the stadium |

### 2. Broadcast main-camera model
- Chen & Little ("Sports Camera Calibration via Synthetic Data", 2018) observe that broadcast cameras are "roughly located near and above the middle line". Pan has a large range and tilt a small range. Their fitted prior (origin at the bottom-left pitch corner) is a camera centre of about N([52, -45, 17], ±[2, 9, 3]) m, pan [-35°, 35°], tilt [-15°, -5°] and focal length [1000, 6000] px at 1280x720. They assume a PTZ camera on a fixed base with roll of ±0.1°.
- The model is PTZ: position fixed per match, only pan, tilt and zoom move. Three.js `PerspectiveCamera(fov, aspect, near, far)` takes a **vertical** FOV in degrees. Call `updateProjectionMatrix()` after changing FOV. `setFocalLength()` uses a 35 mm film gauge by default.
- Converting the focal-length range to FOV: vertical FOV = 2·atan(360/f). That gives about 39.6° at f=1000 (wide) and about 6.9° at f=6000 (tight). A sensible default for a "wide following" shot is around 20-25° (our choice, not from a source).
- **Follow logic** (our design): aim point = exponentially smoothed ball ground position (time constant about 0.6 s). Clamp pan to ±35°, add a small dead-zone so the camera does not jitter, and widen the FOV when the ball moves fast or players are spread out. Use a fixed `dt` so the result is deterministic.

### 3. Deterministic frame capture

| Method | Deterministic? | Notes |
|---|---|---|
| **Playwright loop: `evaluate(renderFrame(i))` + canvas PNG** | Yes (you step time) | Simplest. `page.screenshot()` / `locator.screenshot()` return bytes. Alternatively `canvas.toDataURL()` with `preserveDrawingBuffer: true` |
| Playwright `page.clock` (install / run_for) | Yes | Overrides `requestAnimationFrame`, `performance` and timers. Useful if you keep a rAF loop |
| CCapture.js | Yes | "TimeWarp" hooks `performance.now`, rAF and `setTimeout`, plus `Date.now` by default. Now outputs mp4/webm via WebCodecs, or PNG/JPG tar. Does not cover CSS/Web Animations |
| WebCodecs `VideoEncoder` + Mediabunny | Yes if you pass timestamps (`videoSource.add(frame/30, 1/30)`) | In-browser encode, no PNG round-trip. MDN marks it "Limited availability", secure context only. `mp4-muxer` is **deprecated** in favour of Mediabunny. Playwright's bundled Chromium lacks some licensed codecs, so H.264 may need `channel="chrome"` (check `isConfigSupported`) |
| MediaRecorder / screencast recorders (Babylon VideoRecorder, puppeteer-screen-recorder) | No (real-time) | Drops or duplicates frames under load. Avoid for ground truth |

**Headless WebGL caveat:** without a GPU, Chromium falls back to SwiftShader (software). One vendor measured about 24 s per 3D page on SwiftShader versus about 6 s with `--use-angle=gl` on Mesa llvmpipe. That mode needs an X display (Xvfb). Without one, WebGL "silently" falls back to 2D. **Log the `WEBGL_debug_renderer_info` string on every run.** On a dev laptop with a GPU, run Playwright headed. In Azure, use ACA serverless GPU or accept slow CPU renders for short clips.

### 4. Auto-labels and camera ground truth
- `Vector3.project(camera)` = `applyMatrix4(camera.matrixWorldInverse).applyMatrix4(camera.projectionMatrix)` → NDC in [-1, 1]. Pixel u = (x+1)/2·W, v = (1−y)/2·H. Points behind the camera project mirrored, so reject boxes whose camera-space z ≥ 0.
- YOLO (Ultralytics): one `.txt` per image, one row per object, `class cx cy w h` normalised to 0-1, zero-indexed classes. Images with no objects need no file. SoccerSynth used class 0 = player, 1 = ball.
- Occlusion: projected boxes ignore occlusion. For the hackathon, compute a cheap visibility ratio by rendering an ID-colour pass to a `WebGLRenderTarget` and counting pixels with `readRenderTargetPixelsAsync` (optional). Drop boxes under about 20% visible (our threshold).
- Homography ground truth: for ground points (X, 0, Z), the 3x3 H = Viewport · [columns 0, 2, 3 of rows 0, 1, 3 of P], where P = projectionMatrix·matrixWorldInverse. Export P, H, pan/tilt/FOV and the camera position for every frame in `cam.jsonl`. This lets us grade our own pitch-keypoint and homography model as well as the detector.
- Also export MOT-style tracking ground truth (`frame,id,x,y,w,h,1,-1,-1,-1`) so ByteTrack can be scored with IDF1/HOTA (format per MOTChallenge, not re-checked here).

### 5. Domain randomisation and degradations
- SoccerSynth randomised: sun gradient (brightness, colour temperature), 10 grass colours × 5 grass textures, random kits/hair/shoes, and camera-shake motion blur. They report that the synthetic-trained detector "clearly" did better on motion-blurred images.
- In the Three.js scene, per seed: kit colour pairs (keep the two teams' colours far apart), grass stripe width and tint, HemisphereLight/DirectionalLight intensity and angle (shadows), FOV jitter, small camera shake (±0.1° roll, which matches the PTZ prior).
- In ffmpeg post: `noise=alls=20:allf=t+u` (temporal uniform noise, documented example). `tmix` frame averaging for motion blur. `eq` for grade, `gblur` for softness. `minterpolate` (mi_mode `blend`/`mci`) can change the frame rate. Option names for tmix, eq and gblur were not re-checked in the docs; run `ffmpeg -h filter=tmix` to confirm. Compression: encode once at high CRF (for example 30-35) to imitate stream artefacts. libx264 exposes `crf`, `preset` and `tune`.
- At training time: Albumentations `MotionBlur(blur_range=(3,7), angle_range=(0,360), p=0.5)`, `GaussNoise`, `RandomBrightnessContrast`, with `BboxParams(... 'yolo' ...)`. Newer versions call the argument `coord_format`, older ones `format`.

### 6. Prior art
- **SoccerSynth-Detection** (Qin, Yeung, Umemoto, Fujii, arXiv 2501.09281). Built in Unreal Engine with behaviour-tree players and a 2D-bbox plugin. 37,621 clear images (1920x1080) plus 17,052 motion-blurred images (800x600), YOLO labels. YOLOv8n transfer scores: on SportsMOT, 88.1 AP50 (vs 90.3 for SoccerNet-trained). On SoccerNet-Tracking, 89.4 AP50 (vs 82.8 for SportsMOT-trained). Pretraining on 1/8-subsampled SportsMOT raised AP50 from 92.6 to 95.3. Repo: Apache-2.0, dataset and Windows generator on Google Drive.
- **SoccerSynth-Field** (arXiv 2503.13969). Synthetic pitch data for field detection. Pretraining beat real-only training (no numbers in the abstract).
- **Chen & Little 2018.** Synthetic camera poses (100k sampled) for broadcast calibration: 89.4 mean IoU_whole on World Cup 2014. This is the source of the camera prior above.
- **SoccER (Morra et al., SoftwareX 2020).** A synthetic soccer *event* generator on an open-source game engine (from search snippet, unverified detail).
- **Spiideo SoccerNet SynLoc (2025).** Synthetic athletes composited onto real static-camera images (search snippet, unverified detail).

## So what for us
- **Stages:** this is the core of **Render** (synthetic broadcast video), and it supplies the ground truth for **Ingest/Interpret** in **A TwinCast**. The simulator writes tracking JSON, Three.js renders broadcast video plus labels, our YOLO+ByteTrack auto-events the video, and we grade against the labels. It directly serves the "auto-eventing from video" and "synthetic dataset innovation" suggestions. It also feeds **E Realism Bench**, since the degradations and labels make up a publishable generator. **B Speed Trap** and **D Chalk Talk** need per-frame homography to pin name tags and drawings to the pitch, and `cam.jsonl` provides it. **F Graphics Desk** composites cues over this MP4 by timecode (frame `i` ↔ `tc_in`).
- **Recommendation:** Three.js + Playwright lockstep capture → PNG pipe → ffmpeg H.264 (CRF 18 master plus a CRF 32 "broadcast-degraded" copy). Labels and `cam.jsonl` are written by the same `renderFrame(i)` call so they cannot drift. Clips of 25 fps × 60-90 s per seed. Keep Blender for one optional hero clip. Use YOLO classes 0 = player, 1 = ball, 2 = referee (optional). Day 1-2: scene + follow-cam. Day 3: capture + labels. Day 4: degradations. Then hand off to the CV stage.
- **Risk:** GPU-less containers render slowly (SwiftShader). Render on a dev laptop or ACA serverless GPU, and assert that the renderer string is not SwiftShader.

## Reuse: code & links

**`scene.js`** (Three.js, ES module; tracking JSON assumed `{fps, frames:[{ball:[x,y,z], players:[{id,team,num,x,z}]}]}` in metres, pitch centred, x along length, y up)
```js
import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js';
const W = 1280, H = 720;
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1); renderer.setSize(W, H); document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene(); scene.background = new THREE.Color(0x87a96b);
scene.add(new THREE.HemisphereLight(0xffffff, 0x335533, 1.0));
const sun = new THREE.DirectionalLight(0xffffff, 1.5); sun.position.set(-40, 80, 30); scene.add(sun);
// pitch 105x68 with mowing stripes (add white line meshes the same way)
const stripes = document.createElement('canvas'); stripes.width = 1050; stripes.height = 8;
const g = stripes.getContext('2d');
for (let i = 0; i < 20; i++) { g.fillStyle = i % 2 ? '#3f8f3f' : '#358535'; g.fillRect(i * 52.5, 0, 52.5, 8); }
const pitch = new THREE.Mesh(new THREE.PlaneGeometry(105, 68),
  new THREE.MeshLambertMaterial({ map: new THREE.CanvasTexture(stripes) }));
pitch.rotation.x = -Math.PI / 2; scene.add(pitch);
const numberTex = n => { const c = document.createElement('canvas'); c.width = c.height = 64;
  const x = c.getContext('2d'); x.fillStyle = '#fff'; x.font = 'bold 44px sans-serif';
  x.textAlign = 'center'; x.fillText(String(n), 32, 48); return new THREE.CanvasTexture(c); };
const PLAYER_H = 1.85, PLAYER_R = 0.35, BALL_R = 0.11, players = new Map();
function getPlayer(p, kits) {
  if (players.has(p.id)) return players.get(p.id);
  const grp = new THREE.Group();
  const body = new THREE.Mesh(new THREE.CapsuleGeometry(PLAYER_R, PLAYER_H - 2 * PLAYER_R, 4, 8),
    new THREE.MeshLambertMaterial({ color: kits[p.team] ?? 0x111111 }));
  body.position.y = PLAYER_H / 2; grp.add(body);
  const num = new THREE.Sprite(new THREE.SpriteMaterial({ map: numberTex(p.num) }));
  num.position.y = PLAYER_H * 0.65; num.scale.set(0.6, 0.6, 1); grp.add(num);
  scene.add(grp); players.set(p.id, grp); return grp;
}
const ball = new THREE.Mesh(new THREE.SphereGeometry(BALL_R, 16, 12), new THREE.MeshLambertMaterial({ color: 0xffffff }));
scene.add(ball);

// Broadcast PTZ camera: fixed base (Chen & Little prior), pan/tilt follow, fixed zoom here
const camera = new THREE.PerspectiveCamera(22, W / H, 0.5, 400);
camera.position.set(0, 17, 34 + 45);                   // halfway, 45 m behind near touchline, 17 m up
const aim = new THREE.Vector3(0, 0, 0), TAU = 0.6, MAX_PAN = THREE.MathUtils.degToRad(35);
function updateCamera(ballPos, dt) {
  const k = 1 - Math.exp(-dt / TAU);                    // frame-rate independent smoothing
  const target = new THREE.Vector3(ballPos[0], 0, ballPos[2]);
  if (target.distanceTo(aim) > 1.0) aim.lerp(target, k); // 1 m dead-zone
  const dx = aim.x - camera.position.x, dz = aim.z - camera.position.z;
  const pan = THREE.MathUtils.clamp(Math.atan2(dx, -dz), -MAX_PAN, MAX_PAN);
  const dist = Math.hypot(dx, dz);
  camera.lookAt(camera.position.x + Math.sin(pan) * dist, 0, camera.position.z - Math.cos(pan) * dist);
  camera.updateProjectionMatrix(); camera.updateMatrixWorld();
}

// Projection -> YOLO label line ("cls cx cy w h", normalised) or null
const boxCorners = (x, y, z, r, h) =>
  [[-r,0,-r],[r,0,-r],[-r,0,r],[r,0,r],[-r,h,-r],[r,h,-r],[-r,h,r],[r,h,r]]
    .map(([a, b, c]) => new THREE.Vector3(x + a, y + b, z + c));
function yoloBox(pts, cls) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const p of pts) {
    if (p.clone().applyMatrix4(camera.matrixWorldInverse).z >= 0) return null; // behind camera
    const n = p.clone().project(camera);
    const u = (n.x + 1) / 2 * W, v = (1 - n.y) / 2 * H;
    x0 = Math.min(x0, u); x1 = Math.max(x1, u); y0 = Math.min(y0, v); y1 = Math.max(y1, v);
  }
  x0 = Math.max(0, x0); y0 = Math.max(0, y0); x1 = Math.min(W, x1); y1 = Math.min(H, y1);
  if (x1 - x0 < 2 || y1 - y0 < 2) return null;           // off-screen or too small
  const f = v => v.toFixed(6);
  return `${cls} ${f((x0 + x1) / 2 / W)} ${f((y0 + y1) / 2 / H)} ${f((x1 - x0) / W)} ${f((y1 - y0) / H)}`;
}
// Per-frame camera ground truth incl. pitch-plane (y=0) -> pixel homography
function cameraRecord(i) {
  const P = new THREE.Matrix4().multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
  const e = P.elements, m = (r, c) => e[c * 4 + r];      // three.js is column-major
  const M = [0, 1, 3].map(r => [0, 2, 3].map(c => m(r, c)));  // (X,Z,1) -> clip (x,y,w)
  const V = [[W / 2, 0, W / 2], [0, -H / 2, H / 2], [0, 0, 1]];  // clip -> pixels
  const Hm = V.map(row => [0, 1, 2].map(c => row.reduce((s, v, k) => s + v * M[k][c], 0)));
  return { frame: i, P: Array.from(e), H_pitch_to_img: Hm, fov: camera.fov, pos: camera.position.toArray() };
}

// Lockstep hooks for Playwright: no wall-clock time anywhere
let DATA, KITS = { home: 0xd00000, away: 0x1040ff, ref: 0x111111 };
window.loadMatch = async (url, kits) => {
  DATA = await (await fetch(url)).json(); if (kits) KITS = kits; window.ready = true; return DATA.frames.length;
};
window.renderFrame = (i) => {
  const f = DATA.frames[i], dt = 1 / DATA.fps;
  for (const p of f.players) getPlayer(p, KITS).position.set(p.x, 0, p.z);
  ball.position.set(...f.ball);
  updateCamera(f.ball, dt);                               // camera first, then project
  renderer.render(scene, camera);
  const labels = [];
  for (const p of f.players) {
    const b = yoloBox(boxCorners(p.x, 0, p.z, PLAYER_R, PLAYER_H), p.team === 'ref' ? 2 : 0);
    if (b) labels.push(b);
  }
  const bb = yoloBox(boxCorners(f.ball[0], f.ball[1] - BALL_R, f.ball[2], BALL_R, 2 * BALL_R), 1);
  if (bb) labels.push(bb);
  return { png: renderer.domElement.toDataURL('image/png'), labels, cam: cameraRecord(i) };
};
```
Note: `updateCamera` must run for every frame in order (0, 1, 2, ...) because the smoothing is stateful. To restart mid-clip, replay the camera updates from frame 0 without rendering.

**`capture.py`** (Playwright sync API → PNG pipe into ffmpeg; also writes YOLO txt and `cam.jsonl`)
```python
import base64, json, subprocess, pathlib
from playwright.sync_api import sync_playwright

OUT = pathlib.Path("out"); (OUT / "labels").mkdir(parents=True, exist_ok=True)
ff = subprocess.Popen(["ffmpeg", "-y", "-f", "image2pipe", "-framerate", "25", "-c:v", "png", "-i", "-",
                       "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                       "-movflags", "+faststart", str(OUT / "match_master.mp4")], stdin=subprocess.PIPE)
with sync_playwright() as p, open(OUT / "cam.jsonl", "w") as cam:
    browser = p.chromium.launch(headless=False)          # headed = real GPU on a laptop
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    page.goto("http://localhost:8080/render.html")      # serve scene.js + data with any static server
    gpu = page.evaluate("""() => { const gl = document.createElement('canvas').getContext('webgl');
        const d = gl.getExtension('WEBGL_debug_renderer_info');
        return d ? gl.getParameter(d.UNMASKED_RENDERER_WEBGL) : 'unknown'; }""")
    print("WebGL renderer:", gpu)                        # warn if it says SwiftShader
    n = page.evaluate("u => window.loadMatch(u)", "/data/seed42.json")
    for i in range(n):
        r = page.evaluate("i => window.renderFrame(i)", i)
        ff.stdin.write(base64.b64decode(r["png"].split(",", 1)[1]))
        (OUT / "labels" / f"{i:06d}.txt").write_text("\n".join(r["labels"]))
        cam.write(json.dumps(r["cam"]) + "\n")
    browser.close()
ff.stdin.close(); ff.wait()
```

**ffmpeg commands** (image2 options verified in the docs. The `image2pipe` flags and the tmix/eq/gblur option names are standard usage but were not re-checked in the docs.)
```bash
# PNG folder -> H.264 master (frames/000000.png ...)
ffmpeg -framerate 25 -i frames/%06d.png -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -movflags +faststart master.mp4
# Sub-frame motion blur: render at 100 fps, average 4, keep 25 fps (labels: keep every 4th frame's)
ffmpeg -framerate 100 -i frames100/%06d.png -vf "tmix=frames=4,fps=25" -c:v libx264 -crf 18 -pix_fmt yuv420p blur.mp4
# "Broadcast-degraded" copy: grain + grade + softness + heavy compression
ffmpeg -i master.mp4 -vf "noise=alls=12:allf=t+u,eq=contrast=1.05:saturation=1.1,gblur=sigma=0.5" -c:v libx264 -crf 32 -preset veryfast -pix_fmt yuv420p degraded.mp4
# Extract training images from the degraded MP4 (frame index matches labels/000000.txt ...)
ffmpeg -i degraded.mp4 -start_number 0 images/%06d.jpg
```

**Ultralytics dataset YAML**
```yaml
path: out
train: images/train
val: images/val
names: {0: player, 1: ball, 2: referee}
```

Links: SoccerSynth-Detection generator https://github.com/open-starlab/SoccerSynth-Detection · Three.js football viewer https://github.com/immament/football-match-viewer · LaurieOnTracking `Metrica_Viz.save_match_clip` https://github.com/Friends-of-Tracking-Data-FoTD/LaurieOnTracking · mplsoccer animation https://mplsoccer.readthedocs.io/en/latest/gallery/pitch_plots/plot_animation.html · CCapture.js https://github.com/spite/ccapture.js · Mediabunny https://mediabunny.dev/guide/quick-start

## Sources
- Vector3.js source (project/unproject) — https://github.com/mrdoob/three.js/blob/dev/src/math/Vector3.js — accessed 20 Oct 2026
- Three.js PerspectiveCamera docs — https://threejs.org/docs/pages/PerspectiveCamera.html — accessed 20 Oct 2026
- Three.js WebGLRenderer docs — https://threejs.org/docs/pages/WebGLRenderer.html — accessed 20 Oct 2026
- Playwright Python screenshots — https://playwright.dev/python/docs/screenshots — accessed 20 Oct 2026
- Playwright Python Clock — https://playwright.dev/python/docs/clock — accessed 20 Oct 2026
- Playwright Python Page API (evaluate, add_init_script) — https://playwright.dev/python/docs/api/class-page — accessed 20 Oct 2026
- Playwright browsers (Chromium codecs, headless shell) — https://playwright.dev/python/docs/browsers — accessed 20 Oct 2026
- MDN VideoEncoder — https://developer.mozilla.org/en-US/docs/Web/API/VideoEncoder — accessed 20 Oct 2026
- mp4-muxer (deprecated in favour of Mediabunny) — https://github.com/Vanilagy/mp4-muxer — accessed 20 Oct 2026
- Mediabunny quick start — https://mediabunny.dev/guide/quick-start — accessed 20 Oct 2026
- CCapture.js — https://github.com/spite/ccapture.js — accessed 20 Oct 2026
- FFmpeg formats (image2 demuxer) — https://ffmpeg.org/ffmpeg-formats.html — accessed 20 Oct 2026
- FFmpeg filters (noise, minterpolate) — https://ffmpeg.org/ffmpeg-filters.html — accessed 20 Oct 2026
- FFmpeg codecs (libx264 crf/preset/tune) — https://ffmpeg.org/ffmpeg-codecs.html — accessed 20 Oct 2026
- Microlink, "WebGL without a GPU" (vendor benchmark) — https://microlink.io/blog/webgl-without-a-gpu — accessed 20 Oct 2026
- Blender CLI arguments — https://docs.blender.org/manual/en/latest/advanced/command_line/arguments.html — accessed 20 Oct 2026
- Babylon.js render to video — https://doc.babylonjs.com/features/featuresDeepDive/scene/renderToVideo — accessed 20 Oct 2026
- Unity Perception (discontinued) — https://github.com/Unity-Technologies/com.unity.perception — accessed 20 Oct 2026
- Google Research Football (archived) — https://github.com/google-research/football — accessed 20 Oct 2026
- Chen & Little, Sports Camera Calibration via Synthetic Data — https://arxiv.org/abs/1810.10658 — accessed 20 Oct 2026
- Qin et al., SoccerSynth-Detection — https://arxiv.org/html/2501.09281v1 — accessed 20 Oct 2026
- SoccerSynth-Detection repo — https://github.com/open-starlab/SoccerSynth-Detection — accessed 20 Oct 2026
- Qin et al., SoccerSynth Field — https://arxiv.org/abs/2503.13969 — accessed 20 Oct 2026
- Morra et al., SoccER (SoftwareX 2020) — https://iris.polito.it/retrieve/e384c432-cbfb-d4b2-e053-9f05fe0a1d67/2020_Morra_SoftwareX.pdf — accessed 20 Oct 2026 (search result only)
- Spiideo SoccerNet SynLoc — https://www.scitepress.org/Papers/2025/131082 — accessed 20 Oct 2026 (search result only)
- Ultralytics detection dataset format — https://docs.ultralytics.com/datasets/detect/ — accessed 20 Oct 2026
- Albumentations blur transforms (MotionBlur) — https://albumentations.ai/docs/api-reference/albumentations/augmentations/blur/transforms/ — accessed 20 Oct 2026
- Albumentations bbox utils (yolo format, coord_format) — https://albumentations.ai/docs/api-reference/core/bbox_utils — accessed 20 Oct 2026 (search result only)
- LaurieOnTracking / Metrica_Viz.py — https://github.com/Friends-of-Tracking-Data-FoTD/LaurieOnTracking — accessed 20 Oct 2026
- mplsoccer animation example — https://mplsoccer.readthedocs.io/en/latest/gallery/pitch_plots/plot_animation.html — accessed 20 Oct 2026
- immament/football-match-viewer — https://github.com/immament/football-match-viewer — accessed 20 Oct 2026
