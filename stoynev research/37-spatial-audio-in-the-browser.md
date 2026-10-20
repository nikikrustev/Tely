# 37 — Putting the listener in the stands: binaural/spatial audio and sonifying the pitch in the browser

_Accessed/compiled: 20 Oct 2026 · Priority area: Render (audio channel) + Personalise (seat choice), for Audio Stands (20 Home End + 17 Heartbeat)_

## TL;DR

- **Native Web Audio is enough. No library is needed.** Use `PannerNode` with `panningModel: "HRTF"` for the ball and earcons, `ConvolverNode` for stadium reverb, and `GainNode` buses for ducking. All are Baseline "widely available" (since July 2015). One quirk: **Firefox has no AudioParams on `AudioListener`** (`positionX`, `forwardX`…), so the seat must also be set with `setPosition()` / `setOrientation()`.
- **Default to the halfway seat.** From there the pitch length runs left to right. That is where human localisation is sharpest (minimum audible angle 1–2° near the front midline). Behind-goal seats ("Home End") put attacks on the front/back axis, which is where generic HRTFs cause front-back confusions. Add a brightness or distance cue there.
- **Make the ball a broadband rattling texture, not a tone.** This copies blind football's noisy ball. Narrowband sounds localise worse. Keep football actions as **auditory icons**: thud, whistle, net. They are understood without training, while earcons score about 10% before training. Keep earcon onsets **≥300 ms apart** and add **≥0.1 s gaps** (McGookin & Brewster).
- **Head tracking:** AirPods head tracking is **not exposed to the web**. It is native only (`CMHeadphoneMotionManager`), and the W3C issue has been open since 2020. Phone orientation works, but iOS needs `DeviceOrientationEvent.requestPermission()` from a tap. Use it as an optional "point your phone to listen" mode.
- **Bluetooth adds about 126–274 ms** (AirPods, end-to-end, measured by Coyle). Audio Stands has no video to sync, so this mostly matters for **haptics**: delay the Heartbeat pulses by `baseLatency + outputLatency`. **OpenAIR, the classic free IR library, currently shows a hosting "suspended" page**, so generate a synthetic stadium IR in code (licence-free). Voxengo's free IRs are the fallback.

## Findings

### 1. Web Audio building blocks (spec + MDN)

| Node / API | What matters for us | Support (MDN browser-compat-data) |
|---|---|---|
| `PannerNode` | `panningModel` is `"equalpower"` (default) or `"HRTF"`. HRTF "uses a convolution with measured impulse responses from human subjects". `distanceModel` is `linear`/`inverse` (default)/`exponential`. Defaults: `refDistance` 1, `maxDistance` 10000, `rolloffFactor` 1. Output is always stereo. Right-handed coordinates relative to `ctx.listener`. | `panningModel`: Chrome 14, Firefox 25, Safari 6. Constructor: Chrome 55, Firefox 53, Safari 14.1 |
| Inverse distance gain | `refDistance / (refDistance + rolloff * (max(d, ref) − ref))` | — |
| `AudioListener` | position + `forward` + `up` vectors. MDN suggests forward (0,0,−1), up (0,1,0) | `positionX`/`forwardX`: Chrome 52, Safari 14.1, **Firefox no** (use `setPosition`/`setOrientation`, supported everywhere) |
| `ConvolverNode` | `buffer` is an IR of 1, 2 or 4 channels; `normalize` applies equal-power scaling | Baseline since 2015 |
| `AudioWorklet` | Custom DSP off the main thread (e.g. a granular rolling-ball synth). Not needed for v1 | Chrome 66, Firefox 76, Safari 14.1 |
| `AudioContext({latencyHint})` | `"interactive"` (default, lowest latency, more power), `"balanced"`, `"playback"` (saves power). The real value is read from `baseLatency` | `baseLatency`: Chrome 58, Firefox 70, Safari 14.1 |
| `outputLatency` | "estimation… of audio output latency"; may change while running | Chrome 102, Firefox 70, **Safari 18.4** (Baseline 2025) |
| `navigator.audioSession.type` | `"playback"` keeps Web Audio playing when the iPhone silent switch is on. WebKit maps Web Audio to "ambient" by default | Safari 16.4; not Chrome; Firefox preview |

The spec is the W3C Working Draft of 22 Sep 2026 (Web Audio 1.1). Its default render quantum is 128 frames. Its example says double buffering at 44.1 kHz adds about 5.8 ms of `baseLatency`. Autoplay policy means the context starts suspended: call `ctx.resume()` from a tap (MDN).

### 2. Libraries: Resonance Audio and Omnitone

| | Licence | Status (GitHub API, 20 Oct 2026) | Use for us |
|---|---|---|---|
| **Resonance Audio Web SDK** | Apache-2.0 | **Archived.** Last commit 2018-04-26. npm `resonance-audio` 1.0.0 (Nov 2017). Docs moved to resonance-audio.github.io | First-order ambisonic scene with a shoebox room (`setRoomProperties` with dimensions in metres, materials per wall such as `grass`, `transparent`) and early reflections + late reverb. Nice, but the code is unmaintained. Skip |
| **Omnitone** | Apache-2.0 | **Active.** v2.0.0 released 30 Sep 2026 (ESM/UMD, CSP-safe, rotation setters before init). 914 stars | Ambisonic (FOA 4 ch, HOA 2nd/3rd order) → binaural decoding with SADIE HRIRs, built on `ConvolverNode`. Use it only if we produce an **ambisonic crowd bed** and want to rotate it with the seat or phone |

Resonance's own concepts page claims efficiency on mobile but gives no source counts. We found **no official numbers for how many HRTF panners a phone can run**. Budget about 6 at once (our guess). Earcon panners are short-lived. Measure on a mid-range Android.

### 3. What the hearing research says (Sonification Handbook, open access, 2011)

- **Localisation (ch. 3, Carlile).** Errors are a few degrees straight ahead and grow towards the back and with elevation. Front-back errors occur in 3–6% of trials even for broadband noise. "Narrowband stimuli… or reverberant listening conditions, can significantly degrade performance." Tones have much larger minimum audible angles. Generic (non-individual) HRTFs may fail to externalise sound. Distance cues are level and the **direct-to-reverberant ratio**. So use a stronger reverb send for far balls.
- **Earcons (ch. 14, McGookin & Brewster).**
  - Untrained earcons are recognised about 10% of the time; auditory icons are recognised well without training.
  - About 5 minutes of training gives about 80% identification.
  - Design rules:
    - Use musical timbres, not sine tones.
    - Use about 3 values per attribute.
    - Keep pitches between 125–150 Hz and 5 kHz.
    - Never use loudness alone to encode meaning.
    - Leave gaps of ≥0.1 s and stagger concurrent onsets by **≥300 ms**.
    - Spatial separation helps.
  - Avoid playing same-family earcons at the same time.
- **Spatial vs pitch for data (Liu et al., arXiv 2604.08979, IEEE CG&A 2026).** The study had 26 participants, 10 of them BLV. Mapping values to azimuth beat pitch for fine-grained values and signs, was similar for trends, and was worse for comparisons. This supports **position as space** and **intensity as pitch or tempo**.
- **Blind football (IBSA / Paralympics).** The ball is "hollow with a noisemaker inside". The stadium must be "completely silent until a goal is scored". Players shout "voy" when going for the ball, and a guide bangs on the goalpost to mark the goal. Lab work shows visually impaired players locate a rolling blind-football ball with fewer timing errors (PubMed 38562539). **Inspiration:** a rattle whose rate tracks speed, plus a "goal beacon" earcon.
- **Closest product precedent: Action Audio** (AKQA + Tennis Australia + Monash, Australian Open; trialled 2021, live 2022). It turns Hawk-Eye ball tracking into 3D sound cues for speed and trajectory, line proximity and forehand/backhand. It was delivered via AO radio and Google Assistant and co-designed for two years with blind and low-vision (BLV) fans. Its principles: co-watching with sighted fans, familiar sound languages, emphasis on dramatic moments, and **never override commentary** (the principles come from secondary press, unverified in a primary source). Tactile rivals: OneCourt, Touch2See, Field of Vision.

### 4. Listener model and mapping (design)

- **Coordinates.** CDF tracking uses metres with the origin at the centre spot: x ∈ ±52.5 along the length, y ∈ ±34, home attacks +x (research 02). Map to Web Audio world as **X = x, Y = height z, Z = −y**.
- **Seats.**
  - `halfway`: main stand, 15 m behind the near touchline, 12 m up, at (0, 12, 49), facing −Z (the default listener orientation).
  - `homeEnd`: (−64, 10, 0), facing +X.
  - `awayEnd`: mirrored.
- **Distance tuned for clarity, not realism.** Use `inverse` with `refDistance` 10 and `rolloff` 0.5. Our calculation: the ball at 15 m plays at 0.8, at 50 m at 0.33 (−9.6 dB), at 80 m at 0.22 (−13 dB). The far end is never inaudible. Add a reverb send that rises with distance as the depth cue.
- **Sound layers (priority high → low).**
  1. **Commentary**: dry, centre, "the friend in the next seat".
  2. **Earcons/icons**: kick thud at the passer (soft), shot whoosh + net/post/keeper icon, tackle thud, whistle, possession-change two-note earcon. Use timbre per team (≤3 values).
  3. **Ball rattle**: stops when `ball_status` is dead.
  4. **Crowd bed** (research 38).
  - Leave out footsteps. 22 sources break the ≤3-value and concurrency limits. Instead offer **player-focus mode**: one followed player gets a soft pulse.
- **Ducking.** While speech plays, drop the crowd bus to about 0.25 and the ball to about 0.5. Use a fast attack (≈80 ms time constant) and a slow release (≈600 ms) (our values). Earcons are not ducked, but the scheduler holds them until commentary pauses if they are not urgent.
- **"Where is the ball?"** On request (button or voice intent from research 40), play three pings at the ball position 300 ms apart. Then the commentator says it in words ("our half, left channel, 20 m from the touchline").

### 5. Phones, headphones, latency

- **Headphones are required for HRTF.** MDN's spatialisation guide says to use headphones or surround. On a phone speaker, fall back to `equalpower` and stronger level/pitch cues.
- **AirPods system settings.** iOS "Spatialize Stereo" or head tracking might re-spatialise our binaural mix (unverified). Tell users to switch it off.
- **iOS specifics.**
  - Set `navigator.audioSession.type = "playback"`, or the silent switch mutes everything (WebKit bug 237322).
  - Background suspension was reported even with that set; one commenter says iOS 17.5 fixed it (WebKit bug 261554).
  - `DeviceOrientationEvent.requestPermission()` is iOS Safari 14.5+ per BCD (Chrome 152 also lists it). It needs transient activation and HTTPS.
- **Head tracking.**
  - No web API exposes headphone head pose. Apple's route is native `CMHeadphoneMotionManager` (Apple dev forums). W3C orientation-sensor issue #68 "Head orientation tracking" has been **open since 2020-10-01**.
  - The phone can act as a pointer instead: rotate the listener with `alpha`.
  - Head movement normally resolves front/back ambiguity (general knowledge, unverified here).
- **Bluetooth latency.** Coyle's tap-to-sound measurements on iOS: AirPods 1st gen 274 ms, 2nd gen 178 ms, AirPods Pro 144 ms, AirPods Pro 2 126 ms average. The figures cover the whole chain. Our pipeline runs on a delay (research 24/39), so audio can be **scheduled ahead**. Only phone haptics and talk-back turn-taking feel the lag. Shift haptics by `ctx.baseLatency + ctx.outputLatency`; `outputLatency` needs Safari 18.4+.

### 6. Impulse responses (licences)

- **OpenAIR (University of York).** Historically "most content" was CC-licensed with per-item licences, in stereo, B-format and 5.1 formats. On 20 Oct 2026 both `openair.hosted.york.ac.uk` and `openairlib.net` **redirect to a cPanel "suspended page"**. York's research portal still lists the dataset (2010). Treat it as unavailable.
- **Voxengo free IRs.** Royalty-free for any use, including commercial. They may be redistributed only unaltered, with the notice and free of charge. They include large halls (e.g. "Large Wide Echo Hall") but **no stadium**.
- **EchoThief.** No licence is stated (copyright Chris Warren) and it has no stadium. Avoid.
- **Commercial stadium packs** (Wave Arts Arenas & Stadiums, Audio Ease) are paid. Not needed.
- **Recommendation.** Use a **synthetic stadium IR**: decorrelated stereo noise, 20 ms pre-delay, exponential decay to −60 dB over about 2.8 s (the length is our pick). It has no licence risk and is tunable. Apply it to the ball and earcons only, because a crowd bed already carries its own room sound.

## So what for us

- **Audio Stands. Stages: Render (spatial audio engine) + Personalise (seat, focus player, earcon set, speaker fallback).**
  - The module below is the "being in the stands" layer under the commentator (research 39/40) and crowd (38).
  - Seat choice is a real personalisation axis: "Home End" for your club's end, "halfway" for clarity. It also differentiates us from Audio Eyes / Blind-side (research 32, unverified).
  - The look-ahead delay lets us pre-schedule earcons and ducking around commentary lines.
  - Heartbeat haptics get latency-compensated timing.
  - Plan: about 1 day to build plus half a day of tuning with a 5-minute "learn the sounds" tutorial. The research says a short training session lifts earcon recognition to about 80%. Test with headphones on Chrome Android + iOS Safari.
- **Others, briefly.**
  - **19 Match Music**: same buses and mapping.
  - **A TwinCast**: spatial earcons over our rendered video (sync via the media clock, research 04).
  - **C One Number**: a single-metric sonification uses one panner.
  - **D Chalk Talk**: "where is X?" answered with a ping at X.
  - **10 Story Time**: auditory icons only.

## Reuse: code & links

**`audio-stands.ts`** (126 lines, no dependencies; passes `tsc --strict` with lib dom, TypeScript 5.6). It takes CDF frames at 25 Hz.

```ts
// audio-stands.ts — seat-in-the-stands spatial audio for synthetic CDF frames (metres, origin centre spot, 25 fps)
export type Seat = "halfway" | "homeEnd" | "awayEnd";
export type Earcon = "pass" | "shot" | "tackle" | "whistle" | "ping";
type V3 = [number, number, number];

// pitch (x length, y width, z up) -> Web Audio world (X = x, Y = z, Z = -y)
const toWorld = (x: number, y: number, z = 0): V3 => [x, z, -y];
const SEATS: Record<Seat, { pos: V3; fwd: V3 }> = {
  halfway: { pos: [0, 12, 49], fwd: [0, 0, -1] },  // main stand, 15 m behind near touchline, 12 m up
  homeEnd: { pos: [-64, 10, 0], fwd: [1, 0, 0] },  // behind the goal home defends (home attacks +x)
  awayEnd: { pos: [64, 10, 0], fwd: [-1, 0, 0] },
};

export class AudioStands {
  readonly ctx = new AudioContext({ latencyHint: "balanced" });
  private master = new GainNode(this.ctx);
  private reverb = new ConvolverNode(this.ctx);
  readonly crowdBus = this.bus(0.6);       // connect crowd bed (research 38) here
  readonly ballBus = this.bus(0.8);
  readonly earconBus = this.bus(0.9);
  readonly commentaryIn = this.bus(1.0);   // TTS / Voice Live output: dry, centre, top priority
  private ballPanner = this.panner();
  private ballGain = new GainNode(this.ctx, { gain: 0 });
  private ballSend = new GainNode(this.ctx, { gain: 0.2 });
  private rattle = new OscillatorNode(this.ctx, { type: "square", frequency: 6 });
  private buffers = new Map<Earcon, AudioBuffer>();
  private nextEarconAt = 0;
  private last = { x: 0, y: 0 };
  private seat: Seat = "halfway";

  constructor() {
    this.master.connect(this.ctx.destination);
    this.reverb.buffer = this.stadiumIR(2.8);
    this.reverb.connect(this.master);
    // Ball = looped noise -> band-pass (broadband localises better than tones) -> rattle AM -> HRTF
    const noise = new AudioBufferSourceNode(this.ctx, { buffer: this.noise(2), loop: true });
    const bp = new BiquadFilterNode(this.ctx, { type: "bandpass", frequency: 1800, Q: 0.6 });
    const am = new GainNode(this.ctx, { gain: 0.5 });
    this.rattle.connect(new GainNode(this.ctx, { gain: 0.5 })).connect(am.gain);
    noise.connect(bp).connect(am).connect(this.ballGain).connect(this.ballPanner).connect(this.ballBus);
    this.ballPanner.connect(this.ballSend).connect(this.reverb);   // distance-dependent wet send
    this.earconBus.connect(new GainNode(this.ctx, { gain: 0.15 })).connect(this.reverb);
    noise.start(); this.rattle.start();
    this.setSeat("halfway");
  }

  /** Call from a tap: contexts start suspended; on iOS also survive the silent switch. */
  async unlock() { const nav = navigator as any; if (nav.audioSession) nav.audioSession.type = "playback";
    await this.ctx.resume(); }

  setSeat(seat: Seat) { this.seat = seat; this.setListener(SEATS[seat].pos, SEATS[seat].fwd); }

  /** Optional phone-pointer mode: yaw in radians, positive = turn left. */
  turn(yaw: number) {
    const [fx, , fz] = SEATS[this.seat].fwd;
    this.setListener(SEATS[this.seat].pos,
      [fx * Math.cos(yaw) + fz * Math.sin(yaw), 0, -fx * Math.sin(yaw) + fz * Math.cos(yaw)]);
  }

  /** One tracking frame (25 Hz). setTargetAtTime (tau 40 ms) smooths the 40 ms steps (no zipper noise). */
  onFrame(ball: { x: number; y: number; z?: number; speed: number; alive: boolean }) {
    const t = this.ctx.currentTime, p = this.ballPanner;
    const w = toWorld(ball.x, ball.y, ball.z ?? 0);
    this.last = { x: ball.x, y: ball.y };
    [p.positionX, p.positionY, p.positionZ].forEach((a, i) => a.setTargetAtTime(w[i], t, 0.04));
    this.rattle.frequency.setTargetAtTime(4 + Math.min(ball.speed, 30) * 0.8, t, 0.1); // faster ball = faster rattle
    this.ballGain.gain.setTargetAtTime(ball.alive ? 0.35 : 0, t, ball.alive ? 0.05 : 0.3);
    const d = Math.hypot(...SEATS[this.seat].pos.map((s, i) => s - w[i]));
    this.ballSend.gain.setTargetAtTime(Math.min(0.6, d / 120), t, 0.2);              // far = wetter (DRR cue)
  }

  async loadEarcons(urls: Record<Earcon, string>) { await Promise.all(Object.entries(urls).map(async ([k, u]) =>
    this.buffers.set(k as Earcon, await this.ctx.decodeAudioData(await (await fetch(u)).arrayBuffer())))); }

  /** Spatial earcon at pitch (x, y). Onsets >= 300 ms apart (McGookin & Brewster). `at` = ctx time for look-ahead. */
  earcon(kind: Earcon, x: number, y: number, gain = 1, at = 0) {
    const buffer = this.buffers.get(kind); if (!buffer) return;
    const t = Math.max(this.ctx.currentTime, at, this.nextEarconAt);
    this.nextEarconAt = t + 0.3;
    const src = new AudioBufferSourceNode(this.ctx, { buffer });
    const p = this.panner(); const [X, Y, Z] = toWorld(x, y, 1);
    p.positionX.value = X; p.positionY.value = Y; p.positionZ.value = Z;
    src.connect(new GainNode(this.ctx, { gain })).connect(p).connect(this.earconBus);
    src.onended = () => p.disconnect();
    src.start(t);
  }

  /** "Where is the ball?" — three pings at its current position (commentator then says it in words). */
  pingBall() { for (let i = 0; i < 3; i++) this.earcon("ping", this.last.x, this.last.y, 0.8); }

  /** Priority ducking: commentary > earcons > ball > crowd. Fast attack, slow release. */
  duck(speaking: boolean) {
    const t = this.ctx.currentTime, tau = speaking ? 0.08 : 0.6;
    this.crowdBus.gain.setTargetAtTime(speaking ? 0.25 : 0.6, t, tau);
    this.ballBus.gain.setTargetAtTime(speaking ? 0.5 : 0.8, t, tau);
  }

  /** Seconds between scheduling and hearing (Bluetooth included where reported): delay haptics by this. */
  get outputDelay() { return (this.ctx.baseLatency ?? 0) + ((this.ctx as any).outputLatency ?? 0); }

  private setListener(pos: V3, fwd: V3) {
    const L = this.ctx.listener;
    if (L.positionX) {                      // Chrome / Safari 14.1+
      [L.positionX.value, L.positionY.value, L.positionZ.value] = pos;
      [L.forwardX.value, L.forwardY.value, L.forwardZ.value] = fwd;
      [L.upX.value, L.upY.value, L.upZ.value] = [0, 1, 0];
    } else {                                // Firefox: no AudioParams on AudioListener
      L.setPosition(...pos); L.setOrientation(...fwd, 0, 1, 0);
    }
  }
  private bus(gain: number) { const g = new GainNode(this.ctx, { gain }); g.connect(this.master); return g; }
  private panner() {                        // tuned for clarity: ~-13 dB from 15 m to 80 m
    return new PannerNode(this.ctx, { panningModel: "HRTF", distanceModel: "inverse",
      refDistance: 10, rolloffFactor: 0.5, maxDistance: 200 });
  }
  private noise(sec: number) { return this.decayNoise(1, sec, 0, 0); }
  /** Synthetic stadium IR: decorrelated stereo noise, 20 ms pre-delay, -60 dB at `sec` (RT60 ~ sec). */
  private stadiumIR(sec: number) { return this.decayNoise(2, sec, 0.02, 6.9); }
  private decayNoise(ch: number, sec: number, preSec: number, k: number) {
    const sr = this.ctx.sampleRate, n = Math.floor(sr * sec), pre = Math.floor(sr * preSec);
    const b = this.ctx.createBuffer(ch, n, sr);
    for (let c = 0; c < ch; c++) { const d = b.getChannelData(c);
      for (let i = pre; i < n; i++) d[i] = (Math.random() * 2 - 1) * Math.exp(-k * (i - pre) / (n - pre)); }
    return b;
  }
}
```

**Wiring sketch.**

```ts
const stands = new AudioStands();
startBtn.onclick = async () => { await stands.unlock(); await stands.loadEarcons(EARCON_URLS); };
pubsub.on("frame", (f) => stands.onFrame({ x: f.ball.x, y: f.ball.y, z: f.ball.z,
  speed: f.ball.speed, alive: f.ball_status === "alive" }));
pubsub.on("event", (e) => e.type === "shot" ? stands.earcon("shot", e.x, e.y)
  : e.type === "pass" ? stands.earcon("pass", e.x, e.y, 0.5) : undefined);
ttsAudio.onplay = () => stands.duck(true); ttsAudio.onended = () => stands.duck(false);
stands.ctx.createMediaElementSource(ttsAudio).connect(stands.commentaryIn);
// Heartbeat (research 41): navigator.vibrate after stands.outputDelay * 1000 ms, so the buzz lands with the sound
```

**Phone-pointer mode (iOS permission).** Turn the phone towards the action and that side gets louder and clearer.

```ts
async function pointToListen(stands: AudioStands) {          // call from a click handler
  const DOE = DeviceOrientationEvent as any;
  if (typeof DOE.requestPermission === "function" && (await DOE.requestPermission()) !== "granted") return;
  let zero: number | null = null;                              // calibrate: "facing the pitch" = first reading
  addEventListener("deviceorientation", (e) => {
    if (e.alpha == null) return; zero ??= e.alpha;
    stands.turn(((e.alpha - zero) * Math.PI) / 180);           // check sign on a real device
  });
}
```

**Links.**
- MDN spatialisation guide + boombox demo: https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API/Web_audio_spatialization_basics
- Omnitone v2 (FOA/HOA → binaural, Apache-2.0): https://github.com/GoogleChrome/omnitone
- Resonance Audio Web (archived, room model reference): https://github.com/resonance-audio/resonance-audio-web-sdk
- Voxengo IRs: https://www.voxengo.com/impulses/

## Sources

- Web Audio API 1.1, W3C Working Draft 22 Sep 2026 — https://www.w3.org/TR/webaudio/ — accessed 20 Oct 2026
- MDN PannerNode — https://developer.mozilla.org/en-US/docs/Web/API/PannerNode — accessed 20 Oct 2026
- MDN PannerNode.panningModel — https://developer.mozilla.org/en-US/docs/Web/API/PannerNode/panningModel — accessed 20 Oct 2026
- MDN PannerNode.distanceModel — https://developer.mozilla.org/en-US/docs/Web/API/PannerNode/distanceModel — accessed 20 Oct 2026
- MDN Web audio spatialization basics — https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API/Web_audio_spatialization_basics — accessed 20 Oct 2026
- MDN ConvolverNode — https://developer.mozilla.org/en-US/docs/Web/API/ConvolverNode — accessed 20 Oct 2026
- MDN AudioContext() constructor (latencyHint) — https://developer.mozilla.org/en-US/docs/Web/API/AudioContext/AudioContext — accessed 20 Oct 2026
- MDN AudioContext.outputLatency — https://developer.mozilla.org/en-US/docs/Web/API/AudioContext/outputLatency — accessed 20 Oct 2026
- MDN DeviceOrientationEvent.requestPermission() — https://developer.mozilla.org/en-US/docs/Web/API/DeviceOrientationEvent/requestPermission_static — accessed 20 Oct 2026
- MDN browser-compat-data (AudioListener, PannerNode, AudioContext, AudioSession, AudioWorkletNode, DeviceOrientationEvent JSON) — https://github.com/mdn/browser-compat-data/tree/main/api — accessed 20 Oct 2026
- W3C Audio Session, Editor's Draft 13 Nov 2024 — https://w3c.github.io/audio-session/ — accessed 20 Oct 2026
- WebKit bug 237322 (Web Audio muted by silent switch) — https://bugs.webkit.org/show_bug.cgi?id=237322 — accessed 20 Oct 2026
- WebKit bug 261554 (AudioContext suspended in background) — https://bugs.webkit.org/show_bug.cgi?id=261554 — accessed 20 Oct 2026
- Resonance Audio Web SDK repo (GitHub API: archived, Apache-2.0) — https://github.com/resonance-audio/resonance-audio-web-sdk — accessed 20 Oct 2026
- Resonance Audio Web getting started — https://resonance-audio.github.io/resonance-audio/develop/web/getting-started — accessed 20 Oct 2026
- Resonance Audio concepts — https://resonance-audio.github.io/resonance-audio/discover/concepts — accessed 20 Oct 2026
- Omnitone repo + v2.0.0 release notes — https://github.com/GoogleChrome/omnitone — accessed 20 Oct 2026
- W3C orientation-sensor issue #68 "Head orientation tracking" (open) — https://github.com/w3c/orientation-sensor/issues/68 — accessed 20 Oct 2026
- Apple Developer Forums, AirPods head-tracking API thread — https://developer.apple.com/forums/thread/661325 — accessed 20 Oct 2026
- Stephen Coyle, AirPods Pro latency — https://stephencoyle.net/airpods-pro — accessed 20 Oct 2026
- 9to5Mac, AirPods Pro 2 latency test — https://9to5mac.com/2022/11/15/airpods-pro-2-latency-test/ — accessed 20 Oct 2026
- Hermann, Hunt, Neuhoff (eds.), The Sonification Handbook (2011), ch. 3 Psychoacoustics (Carlile), ch. 14 Earcons (McGookin & Brewster) — https://sonification.de/handbook/chapters/ — accessed 20 Oct 2026
- Liu et al., Accessible Fine-grained Data Representation via Spatial Audio, arXiv 2604.08979 — https://arxiv.org/abs/2604.08979 — accessed 20 Oct 2026
- Aan et al., Remote Virtual Showdown (HRTF VR game for VI players), arXiv 2103.16153 — https://arxiv.org/abs/2103.16153 — accessed 20 Oct 2026
- Sound source localization in blind soccer (PubMed 38562539) — https://pubmed.ncbi.nlm.nih.gov/38562539/ — accessed 20 Oct 2026
- International Paralympic Committee, Blind Football — https://www.paralympic.org/blind-football — accessed 20 Oct 2026
- Action Audio — https://action-audio.com/ — accessed 20 Oct 2026
- Able Magazine, Australian Open Action Audio — https://ablemagazine.co.uk/australian-open-becomes-first-ever-major-sporting-event-to-offer-enhanced-audio-experience-for-blind-and-low-vision-fans/ — accessed 20 Oct 2026
- University of York, OpenAIR project page — https://www.york.ac.uk/physics-engineering-technology/research/communication-technologies/projects/open-acoustic-impulse-response-library/ — accessed 20 Oct 2026
- OpenAIR site (redirects to "suspended page" on 20 Oct 2026) — https://www.openair.hosted.york.ac.uk/ — accessed 20 Oct 2026
- Voxengo free impulse responses (licence) — https://www.voxengo.com/impulses/ — accessed 20 Oct 2026
- EchoThief IR library — http://www.echothief.com/ — accessed 20 Oct 2026
