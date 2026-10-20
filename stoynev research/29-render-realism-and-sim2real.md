# 29 — Making rendered matches look real enough: animated players, kits, lighting, and the sim-to-real gap
_Accessed/compiled: 20 Oct 2026 · Priority area: Render (synthetic broadcast video) → CV Ingest (detector transfer)_

## TL;DR
- **Use CC0 assets only, and keep Mixamo out of the repo.** Quaternius (Universal Animation Library + Universal Base Characters), Kenney Animated Characters, Poly Haven HDRIs/textures and ambientCG textures are all CC0. They are fine for a public GitHub repo, a demo video and ML training. Mixamo forbids redistributing the raw files. A 2022 FAQ copy on Adobe's forum also says Mixamo content can't be used to train ML models, which is exactly what TwinCast does. The three.js `Soldier.glb` sample is credited to mixamo.com, so it is out too. Ready Player Me's public services shut down on 31 Jan 2026 after Netflix bought it.
- **Animated players are a one-day job in Three.js.** Load one glTF, make 22 copies with `SkeletonUtils.clone`, and give each one its own `AnimationMixer`. Blend idle/walk/jog/sprint by the tracked speed. Drive a shared gait phase from speed so the feet don't slide, and point each body along its smoothed velocity. Three.js core has no instanced skinning (PR #22667 was closed unmerged), but 22–25 ordinary `SkinnedMesh` players are cheap anyway.
- **Appearance variety matters most, then distractors, then camera.** In Tobin et al. 2017, transfer got clearly worse below about 1,000 unique textures. Removing distractors raised error from 1.8 to 7.2 cm on cluttered real scenes. Removing camera randomisation raised it from 1.3 to 2.0 cm. Image noise had almost no effect. SoccerSynth-Field's cumulative table shows gains from grass colour/texture (finetuned 97.5 → 98.4) and from lighting (pretrain-only 94.2 → 95.4). SoccerSynth-Detection credits its win on blurry frames to motion-blur variety, and blames its shortfall on SportsMOT on too little head/hair variety.
- **Realism ladder:** capsules (0.5 day) → low-poly animated CC0 players with team colours (+2 days) → numbers, hair/skin variety, real grass, HDRI and shadows (+1.5 days) → motion blur, grade, grain and compression (+1 day) → crowd, ad boards and floodlit night (+1–2 days). Stop at level 3 for the hackathon. These are our effort estimates.

## Findings

### 1. Licences: what we can commit and show

| Source | Licence | Public repo + demo video? | ML training? | Notes |
|---|---|---|---|---|
| **Quaternius Universal Animation Library** | CC0 | Yes | Yes (CC0 sets no limits) | 120+ animations on one humanoid rig, including jog, sprint and 8-direction locomotion. The free Standard tier comes in OBJ/FBX/glTF and holds "60-70%" of the pack. One review says Standard has 45 animations (unverified). |
| **Quaternius Universal Base Characters** | CC0 | Yes | Yes | 6 bodies (male/female × 3 builds) and 20 hairstyles, about 13k triangles each, stated to be "Compatible with the Universal Animation Library". |
| **Kenney Animated Characters 1–3** | CC0 | Yes | Yes | One rig, 4 skins, but only Idle, Run and a Jump pose. There is no walk or sprint. The zip is 689 kB, and the file format isn't shown on the page (unverified). |
| **Poly Haven** (HDRIs, textures) | CC0 | Yes, no credit needed | Yes | Bulk scraping without permission is prohibited, so download by hand or through their API. |
| **ambientCG** (PBR textures) | CC0 | Yes. "You can include the raw files in your project" | Yes | Grass001–008 come at 1K–8K in JPG/PNG. |
| **Mixamo** | Royalty-free inside your project | **No.** "the only thing you can't do is distribute the raw character and animation files" | **No** per the 2022 FAQ copy. The live helpx page returned 403 to us (unverified there). | Even a baked glTF in a public repo is arguably raw redistribution. |
| **three.js example `Soldier.glb`** | Credited "(model from mixamo.com)" | Same issue as Mixamo | Same issue as Mixamo | Use it only to prototype locally. |
| **Ready Player Me** | n/a | **Dead** | n/a | Netflix acquisition announced 22 Dec 2025. The avatar creator and public API went offline on 31 Jan 2026 (secondary sources). |
| **three.js** | MIT | Yes | Yes | |

**Recommended set:** Universal Base Characters as the body, Universal Animation Library for the clips (the two share a rig), ambientCG `Grass004` for the pitch, and Poly Haven HDRIs. Searching the 997 Poly Haven HDRIs by tag found `stadium_01` (sunrise/sunset, clear), `orlando_stadium` (midday, clear, high contrast), `suburban_football_field` (overcast) and `suburban_soccer_park` (overcast). None of them is a **floodlit night stadium**, so night scenes need our own lights over a dark sky.

### 2. Animated players: GLTF → 22 clones → speed-driven blending
- **Cloning.** `SkeletonUtils.clone` "ensur[es] that any SkinnedMesh instances are correctly associated with their bones". It clones the bones, but "geometries and materials are reused by reference". So clone the **materials** yourself, once per team, or every player ends up in the same colour.
- **Mixers.** "When multiple objects in the scene are animated independently, one AnimationMixer may be used for each object." That means 22 mixers that all share the same `AnimationClip`s. Action `weight` is "in the interval [0, 1] … used to blend between several actions."
- **Speed bands (our values):** idle below 0.5 m/s, walk around 1.5, jog around 3.5, sprint from 6.94 m/s (25 km/h). The 25 km/h sprint threshold is the PL one from research 02. Use piecewise-linear weights between those knots so every frame blends at most two clips.
- **Foot sliding.** The three.js blending example keeps walk and run in step with `crossFadeTo(..., warp=true)` and waits for loop boundaries. That suits a game, but our players change speed every frame. A better way: keep one **normalised gait phase φ** per player and advance it by `dt × speed / strideLength(speed)`. Set every locomotion action's `time = φ × clip.duration` and leave its `timeScale` at 0, so the playback rate follows speed. Measure each clip's reference speed once, as stride length ÷ cycle duration in metres per cycle. This is our design, so test it on the chosen clips.
- **Orientation.** Use yaw = `atan2(vx, vz)`, smoothed with a slerp (about 0.2 per frame at 25 fps). Below about 0.4 m/s, turn the player to face the ball instead, otherwise jitter makes the body spin. Map simulator (x, y) metres to three.js (x, z).
- **Determinism.** In lockstep capture (research 06), call `mixer.update(1/fps)` exactly once per `renderFrame(i)` and take each player's gait-phase offset from the seed. The same seed then gives identical frames.
- **Tight boxes come free.** `SkinnedMesh.computeBoundingBox()` "should be recomputed per frame in order to reflect the current animation state". That gives tighter YOLO boxes than a fixed capsule box. Engine-computed bounding spheres go stale under animation, so set `frustumCulled = false` on players. Otherwise players near the edge of the frame can vanish.

### 3. Kits and numbers
- **Shirts.** Two cloned shirt materials (home and away), plus keeper colours and a referee material. Randomise the hue per seed inside a palette, and keep the two teams at least about 60° apart in hue. That is our rule, so that team classification (research 05) stays possible.
- **Numbers.** Draw each number on a 256×256 canvas and turn it into a `CanvasTexture`. The constructor sets `needsUpdate` for you. Set `colorSpace = SRGBColorSpace` and put it on a small plane parented to the upper spine bone. That is far easier than editing the character's UVs. Use one material per player for the number only, and keep the bodies on the shared team materials.
- **Head/hair variety.** Use the 20 Quaternius hairstyles and a range of skin tones. SoccerSynth-Detection names missing head-texture variety as the reason for its AP50 shortfall on SportsMOT (88.1 against 90.3).

### 4. Lighting, shadows, camera effects
- **Day.** Use a `DirectionalLight` sun with `castShadow`. The default orthographic shadow frustum is only ±5 units, so widen it to about ±60 m to cover 105×68 m and raise `mapSize` (default 512) to 4096. Image-based lighting comes from a Poly Haven `.hdr` via `HDRLoader`, which replaced `RGBELoader` in current docs, then PMREM into `scene.environment`. Randomise sun elevation and azimuth, colour temperature (warm at sunrise, neutral at midday) and HDRI choice per seed. SoccerSynth-Detection used a sunlight gradient across brightness, colour temperature, sunrise and sunset.
- **Night.** Use 4 corner floodlights. Every shadow-casting light adds a depth pass over every caster, so only 2 should cast shadows. Real floodlit matches show 4 faint shadows per player, which is a nice detail but optional.
- **Post stack.** The three.js addons (r186, 24 Sep 2026) ship `EffectComposer`, `RenderPass`, `BokehPass` (depth of field), `FilmPass` (grain), `LUTPass` (colour grade), `SMAAPass`/`TAARenderPass`, `UnrealBloomPass` and `OutputPass`. The shaders folder adds `VignetteShader` and `ColorCorrectionShader`. There is **no built-in lens-distortion pass**, so write a small `ShaderPass` for barrel distortion (k1 around -0.02 to -0.08, our range). In that case, distort the labels too, or keep k1 at 0 for the label-exact clips. Do **motion blur** by sub-frame accumulation, as in research 06: render at 100 fps, then `tmix` down to 25. Keep depth of field off or weak, because wide broadcast shots are mostly in focus (our judgement). Use it only on tight zoom shots.

### 5. Which randomisations matter for detector transfer

| Factor | Evidence | Priority for us |
|---|---|---|
| Appearance/texture variety (kits, grass, skin, hair) | Tobin: performance "degrades significantly when fewer than 1,000 textures are used". With little data, texture randomisation mattered more than object positions. SoccerSynth-Field: JA → JA+G took finetuned accuracy from 97.5 to 98.4. | **1** |
| Distractors (crowd, ad boards, officials, staff, fake lines) | Tobin: removing distractors moved error from 1.8 to 7.2 cm on real scenes with distractors. SoccerSynth-Field kept random "fake lines" in its best set (+0.1, not isolated). | **2** |
| Lighting | SoccerSynth-Field: +L moved pretrain-only accuracy from 94.2 to 95.4, the largest single step in pretraining. | **2** |
| Camera pose/FOV | Tobin: no camera randomisation moved error from 1.3 to 2.0 cm. SoccerSynth-Detection used camera ranges taken from real footage. | **3**, using research 06's broadcast prior |
| Motion blur | SoccerSynth-Detection: clearly better than real-trained models on blurred images. The evidence is qualitative and has no ablation. | **3** |
| Pixel noise | Tobin: "negligible effect", but it helps convergence. | 4 (cheap, so keep it) |

**Caveats.** Neither SoccerSynth paper ablates single factors for player detection. The Field paper's table is cumulative and is about pitch keypoints, not players. Synthetic-only pretraining stayed below the real baseline (about 92–96% against 98.3%) until it was fine-tuned on real data. We cannot use real PL data, so we report transfer honestly on our own held-out seeds plus one public non-PL set, if its licence allows.

## So what for us
- **Stages:** **Render** (realistic broadcast video) and **Ingest** (the detector trained on it). Main beneficiaries: **A TwinCast**, then **E Realism Bench** (the randomisation config *is* the generator spec), plus **B Speed Trap**, whose name tags on visibly sprinting players sell the speed. Better-looking video also lifts **F Graphics Desk** and **D Chalk Talk** demos.
- **Recommendation:** go up to **realism level 3** (CC0 Quaternius players + speed blending + kits/numbers + ambientCG grass with mow stripes + Poly Haven HDRI + sun shadows + sub-frame blur, grade, grain and CRF re-encode). Put every random choice in one seeded `render_config.json` and log it next to `labels/` and `cam.jsonl`, so the realism report can list exactly what varied. Hold out 2 seeds with **unseen** kit colours and HDRIs as the "sim-to-sim gap" test.
- **Do not** commit Mixamo or `Soldier.glb`. Add a `LICENSES-ASSETS.md` table with the source URL and CC0 for every file. Judges and reviewers can then check it in seconds.
- **Plan (our estimate):** day 1 load, clone and blend. Day 2 kits, numbers, grass and HDRI. Day 3 post stack and config. Level 4 (crowd cards, ad boards, night) only if the CV stage is waiting on nothing else.

## Reuse: code & links

```js
// players.js — three r186. CC0 body+clips from Quaternius (check clip names after export).
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';

const gltf = await new GLTFLoader().loadAsync('assets/ubc_male_regular.glb');
const clipsGltf = await new GLTFLoader().loadAsync('assets/ual_locomotion.glb');
const CLIP = n => THREE.AnimationClip.findByName(clipsGltf.animations, n);
const GAIT = [ // name, knot speed m/s, metres per cycle (measure once per clip)
  { clip: CLIP('Idle'),   v: 0.0, stride: 1.0 },
  { clip: CLIP('Walk'),   v: 1.5, stride: 1.5 },
  { clip: CLIP('Jog'),    v: 3.5, stride: 2.4 },
  { clip: CLIP('Sprint'), v: 6.94, stride: 4.0 }];

function numberTexture(n, fg = '#fff') {
  const c = Object.assign(document.createElement('canvas'), { width: 256, height: 256 });
  const g = c.getContext('2d');
  g.fillStyle = fg; g.font = 'bold 180px sans-serif';
  g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(String(n), 128, 140);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

export function makePlayer(teamMat, shirtNo, rng) {
  const root = SkeletonUtils.clone(gltf.scene);           // bones cloned, geometry shared
  root.traverse(o => { if (o.isSkinnedMesh) {
    o.frustumCulled = false; o.castShadow = true;
    if (/shirt|body/i.test(o.material.name)) o.material = teamMat; // shared per team
  }});
  const spine = root.getObjectByName('spine_03') ?? root;  // bone name: inspect the rig
  const num = new THREE.Mesh(new THREE.PlaneGeometry(0.22, 0.22),
    new THREE.MeshStandardMaterial({ map: numberTexture(shirtNo), transparent: true }));
  num.position.set(0, 0.05, -0.16); num.rotation.y = Math.PI; spine.add(num); // tune offsets
  const mixer = new THREE.AnimationMixer(root);
  const actions = GAIT.map(g => { const a = mixer.clipAction(g.clip); a.timeScale = 0; a.play(); return a; });
  return { root, mixer, actions, phase: rng(), yaw: 0 };
}

export function stepPlayer(p, vx, vz, dt, ballDir) {
  const s = Math.hypot(vx, vz);
  // piecewise-linear weights between neighbouring knots
  let k = GAIT.findIndex(g => g.v > s); if (k === -1) k = GAIT.length - 1;
  const lo = Math.max(0, k - 1), t = THREE.MathUtils.clamp((s - GAIT[lo].v) / (GAIT[k].v - GAIT[lo].v || 1), 0, 1);
  p.actions.forEach((a, i) => a.setEffectiveWeight(i === lo ? 1 - t : i === k ? t : 0));
  // shared gait phase: cadence = speed / stride, so feet don't slide
  const stride = THREE.MathUtils.lerp(GAIT[lo].stride, GAIT[k].stride, t);
  p.phase = (p.phase + dt * Math.max(s, 0.3) / stride) % 1;
  p.actions.forEach((a, i) => { a.time = p.phase * GAIT[i].clip.duration; });
  p.mixer.update(dt);                                       // timeScale 0: applies weights at set time
  // face velocity, or the ball when nearly still
  const target = s > 0.4 ? Math.atan2(vx, vz) : Math.atan2(ballDir.x, ballDir.z);
  const d = Math.atan2(Math.sin(target - p.yaw), Math.cos(target - p.yaw));
  p.yaw += d * 0.2; p.root.rotation.y = p.yaw;
}
```

```js
// seeded randomisation — mulberry32 so Python can reproduce the same draws if needed
export const mulberry32 = a => () => { a |= 0; a = a + 0x6D2B79F5 | 0;
  let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
  return ((t ^ t >>> 14) >>> 0) / 4294967296; };
```

```json
{ "seed": 4217,
  "kits":     { "home_hue": [0, 360], "min_hue_gap_deg": 60, "sat": [0.5, 0.95], "shorts": ["white","black","match"] },
  "players":  { "skin_tones": 6, "hairstyles": 20, "body": ["regular","superhero"], "gait_phase": "uniform" },
  "pitch":    { "texture": ["Grass001","Grass004","Grass006"], "mow_stripes": [8, 12], "hue_shift": [-10, 10], "fake_lines": [0, 3] },
  "lighting": { "mode": ["day","day","night"], "hdri": ["stadium_01","orlando_stadium","suburban_football_field"],
                "sun_elev_deg": [10, 65], "sun_azim_deg": [0, 360], "colour_temp_k": [3500, 6500], "floodlights_shadowed": 2 },
  "distractors": { "crowd_density": [0.3, 1.0], "ad_boards": true, "officials": 3, "staff_on_touchline": [0, 6] },
  "camera":   { "use_prior": "research-06", "lens_k1": [0.0, -0.06], "dof": false },
  "post":     { "subframes": 4, "grain": [0.0, 0.35], "lut": ["neutral","warm_broadcast","cool_broadcast"], "crf_degrade": [28, 34] } }
```

```js
// post stack (OutputPass last: tone mapping + sRGB)
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { FilmPass } from 'three/addons/postprocessing/FilmPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
composer.addPass(new FilmPass(cfg.post.grain));   // add LUTPass / custom barrel ShaderPass here
composer.addPass(new OutputPass());
```

Links:
- three.js skinning blending example (pattern to copy, but its model is from Mixamo): https://github.com/mrdoob/three.js/blob/dev/examples/webgl_animation_skinning_blending.html
- three.js postprocessing passes: https://github.com/mrdoob/three.js/tree/dev/examples/jsm/postprocessing
- Poly Haven API (list HDRIs by tag): https://api.polyhaven.com/assets?t=hdris
- ambientCG API: https://ambientcg.com/api/v2/full_json?q=grass&type=Material
- Community instanced skinning (only if we ever need 100+ animated people, e.g. a moving crowd): https://github.com/mrdoob/three.js/pull/22667 (closed, unmerged)

## Sources
- Tobin et al., "Domain Randomization for Transferring Deep Neural Networks from Simulation to the Real World" (arXiv 1703.06907; ablation in Sec. IV-C, Table II) — https://arxiv.org/abs/1703.06907 — accessed 20 Oct 2026
- Qin, Yeung, Umemoto, Fujii, "SoccerSynth-Detection" (arXiv 2501.09281) — https://arxiv.org/html/2501.09281 — accessed 20 Oct 2026
- Qin, Fang, Fujii, "SoccerSynth Field" (arXiv 2503.13969) — https://arxiv.org/html/2503.13969 — accessed 20 Oct 2026
- three.js docs: AnimationMixer — https://threejs.org/docs/pages/AnimationMixer.html — accessed 20 Oct 2026
- three.js docs: AnimationAction — https://threejs.org/docs/pages/AnimationAction.html — accessed 20 Oct 2026
- three.js docs: SkeletonUtils — https://threejs.org/docs/pages/module-SkeletonUtils.html — accessed 20 Oct 2026
- three.js docs: SkinnedMesh — https://threejs.org/docs/pages/SkinnedMesh.html — accessed 20 Oct 2026
- three.js docs: CanvasTexture — https://threejs.org/docs/pages/CanvasTexture.html — accessed 20 Oct 2026
- three.js docs: HDRLoader — https://threejs.org/docs/pages/HDRLoader.html — accessed 20 Oct 2026
- three.js docs: DirectionalLightShadow / LightShadow — https://threejs.org/docs/pages/DirectionalLightShadow.html — accessed 20 Oct 2026
- three.js releases (r186, 24 Sep 2026) — https://github.com/mrdoob/three.js/releases — accessed 20 Oct 2026
- three.js PR #22667 InstancedSkinnedMesh (closed 18 Oct 2021, unmerged) — https://github.com/mrdoob/three.js/pull/22667 — accessed 20 Oct 2026
- three.js forum: Animated instanced skinned meshes — https://discourse.threejs.org/t/animated-instanced-skinned-meshes-gltf/41958?page=2 — accessed 20 Oct 2026
- Quaternius, Universal Animation Library — https://quaternius.com/packs/universalanimationlibrary.html — accessed 20 Oct 2026
- Quaternius, Universal Base Characters — https://quaternius.com/packs/universalbasecharacters.html — accessed 20 Oct 2026
- 80.lv, Universal Animation Library article (Standard = 45 animations, unverified) — https://80.lv/articles/get-your-hands-on-over-120-ready-to-use-game-animations — accessed 20 Oct 2026
- Kenney, Animated Characters 3 — https://kenney-assets.itch.io/animated-characters-3 — accessed 20 Oct 2026
- OpenGameArt, Kenney Animated Characters 2 (CC0) — https://opengameart.org/content/animated-characters-2 — accessed 20 Oct 2026
- Poly Haven licence — https://polyhaven.com/license — accessed 20 Oct 2026
- Poly Haven public API (HDRI and texture catalogue queried) — https://api.polyhaven.com/assets?t=hdris — accessed 20 Oct 2026
- ambientCG licence — https://docs.ambientcg.com/license/ — accessed 20 Oct 2026
- Adobe Community, "Mixamo FAQ: licensing, royalties, ownership, EULA and TOS" (29 Sep 2022, community post) — https://community.adobe.com/questions-696/mixamo-faq-licensing-royalties-ownership-eula-and-tos-589400 — accessed 20 Oct 2026
- Adobe, Mixamo common questions (returned 403 to our fetcher; seen in search snippet only) — https://helpx.adobe.com/en/creative-cloud/faq/mixamo-faq.html — accessed 20 Oct 2026
- PocketGamer.biz, Netflix acquires Ready Player Me — https://www.pocketgamer.biz/netflix-acquires-avatar-creation-platform-ready-player-me — accessed 20 Oct 2026
- Avatar SDK, Ready Player Me migration guide (shutdown 31 Jan 2026) — https://avatarsdk.com/blog/2026/07/07/ready-player-me-migration-guide/ — accessed 20 Oct 2026
- Research 02 (PL 25 km/h sprint threshold) and 06 (broadcast camera prior, lockstep capture, sub-frame blur) in this library
