# 41 — Feeling the match: haptic patterns on phones, watches and controllers (idea 17 Heartbeat)

_Accessed/compiled: 20 Oct 2026 · Priority area: Render + Personalise (touch channel) for **Audio Stands** (20 Home End + 17 Heartbeat); also helps F Graphics Desk demo and 10 Story Time_

## TL;DR

- **Only Chromium browsers on Android can vibrate from the web.**
  - **iOS Safari:** no Vibration API in any version caniuse lists, up to 27.2. The current spec says "WebKit opposes" it.
  - **Firefox:** desktop Firefox removed it in 129. Firefox for Android is the trap: `navigator.vibrate()` **returns `true` but nothing vibrates** (MDN compat data). Feature detection alone cannot catch this.
- **The web API is on/off only.** `navigator.vibrate([on, off, on…])` takes durations in milliseconds and nothing else: no amplitude and no frequency.
  - It needs sticky user activation and a **visible** page.
  - Each call cancels the previous one.
  - The current W3C draft limits a pattern to **10 entries** and **10,000 ms per entry**. Chromium's code allows 99 entries.
  - So the haptic vocabulary has to be built on **rhythm**. That suits us: in Brown, Brewster & Purchase (2005), rhythm was recognised **93%** of the time, roughness 80%, and the full tacton 71%.
- **Commercial tactile football products always pair haptics with audio.** Touch2See, Field of Vision, OneCourt and Newcastle's "Unsilence the Crowd" shirts all do this. What fans praise is **feeling the moment at the same time as the crowd**. Haptics support the commentator; they do not replace him.
- **Sync:** I found **no published latency figure for `navigator.vibrate`**. The published numbers are perception windows:
  - Altinsoy (2003): sound-plus-vibration pairs felt synchronous from audio leading by 26 ms to audio lagging by 51 ms.
  - Kaaresoja's guideline for bimodal feedback: tactile within 25 ms, audio within 100 ms.
  - So schedule each pulse on the `AudioContext` output clock and fire the vibration **a little early, never late**. Then calibrate on the demo phone.
- **Hackathon plan:**
  - Android Chrome vibration plus desktop gamepad `dual-rumble`.
  - An honest "iPhone: audio only" message.
  - A native iOS wrapper is **not worth it** for the hackathon. Capacitor and Expo haptics have no custom patterns, so a heartbeat on iPhone needs Core Haptics (AHAP) in Swift. Ship the AHAP file as a roadmap item.

## Findings

### 1. Platform capabilities (what each API can really do)

| Platform / API | Control you get | Constraints | Reach for us |
|---|---|---|---|
| **Web Vibration API** `navigator.vibrate(pattern)` | Alternating on/off durations in ms. Passing `0` or `[]` cancels. | **Sticky activation** required. If the document is not visible it returns false, and a visibility change aborts a running pattern. Draft spec: max 10 entries, 10,000 ms each. Chromium: `kVibrationPatternLengthMax = 99`, `kVibrationDurationMsMax = 10000`. Since Chrome 60 it needs a user gesture. Blocked in cross-origin iframes. Some devices stay silent in Silent or Do Not Disturb mode (MDN). | Chrome, Edge, Samsung Internet and Opera on Android. **Not iOS** (any browser, since all use WebKit). Not Firefox. |
| **iOS "switch" trick** (`<input type=checkbox switch>`, used by the `ios-haptics` npm package) | One system tick when the user toggles the switch. | WebKit bug 285120 (fixed 3 Jan 2025) made the haptic **require user activation**, so it cannot follow match events. | Taps only, so useless for Heartbeat. |
| **Gamepad API** `vibrationActuator.playEffect("dual-rumble", {duration, startDelay, strongMagnitude, weakMagnitude})` | Two motors (strong = low frequency, weak = high frequency), each 0–1. | A new call preempts the old one. Rejects if the page is hidden. The spec says the UA MAY cap effect length and recommends 5 seconds. `trigger-rumble` is Chrome/Edge 126+ only. | Chrome/Edge 68+, Safari 16.4+ (desktop). Firefox has no `playEffect`. Not iOS Safari. |
| **Android native** `VibrationEffect.createWaveform(timings, amplitudes 0–255)` and `Composition` primitives (CLICK, TICK, LOW_TICK, THUD, SPIN, QUICK_RISE, SLOW_RISE, QUICK_FALL; Android 11+) | Amplitude, if `hasAmplitudeControl()`. Primitives with scale 0–1 and a delay that counts from the end of the previous primitive. | **No fallback inside a composition:** one unsupported primitive and the whole effect fails. Gaps of 5–10 ms are not detectable; use ~50 ms or more. Use at most 3 intensity levels (0.5, 0.7, 1.0), at least ×1.4 apart. Android 16 prefers `VibrationEffect.Builder`. | Wear OS apps use the same `android.os` vibrator classes (unverified which primitives watches support). |
| **iOS native Core Haptics** (AHAP JSON or `CHHapticPattern`) | Transient and continuous events, `HapticIntensity` and `HapticSharpness` 0–1, attack/decay/release, parameter curves, plus audio events in the same file. | Native app only. Haptics do nothing in Low Power Mode, with the Taptic Engine off in settings, or while the camera or dictation is active (Expo docs). | The only way to get a real heartbeat on iPhone. |
| **UIFeedbackGenerator** (impact / selection / notification / canvas) | Preset system feels; `prepare()` warms the engine up. | Native only, and no patterns. | Event ticks, not a heartbeat. |
| **Apple Watch** `WKInterfaceDevice.current().play(.directionUp)` | A **fixed set**: notification, directionUp, directionDown, success, failure, retry, start, stop, click, plus navigation cases. | No custom patterns. The HIG gives each type a fixed meaning and warns that overusing `click` "tends to diminish its utility". | watchOS app only. Out of hackathon scope. |
| **Wrappers:** `@capacitor/haptics`, `expo-haptics` | Capacitor: `impact(Light/Medium/Heavy)`, `notification`, `vibrate({duration})` (default 300 ms), selection hints. Expo: impact, notification, selection, and `performAndroidHapticsAsync`. | **Neither has custom patterns.** Expo sends you to the third-party Pulsar SDK for those. Expo on the web uses the Vibration API, so it has the same iOS gap. | A heartbeat needs a small custom Swift plugin that calls Core Haptics. |
| **Body-worn: Woojer Vest 3** | 6 transducers, 1–250 Hz haptic range. **Driven by audio** over 3.5 mm, USB audio or Bluetooth A2DP. | You need the vest. | Our crowd and heartbeat **audio** can drive it directly, with no API. |

### 2. What real tactile-football products learned

| Product | How it works | What worked / caveats |
|---|---|---|
| **Touch2See** (Toulouse; from search summaries, because the Orange pages were behind a cookie wall, unverified) | A tablet with a miniature pitch. A magnetic disk follows the ball, **vibration intensity signals how intense the action is**, and audio adds the clock, score and fouls. | Piloted by St. Louis CITY SC (MLS) on 15 Mar 2025 with about 10 blind fans. Also used by Cagliari, and at AFCON 2025 by CAF. Earlier trial at Orange Vélodrome. |
| **Field of Vision** (Dublin) | AI cameras track the play. A magnetic ball moves and vibrates for passes, tackles and goals. Claimed **under 0.5 s** latency. Has a headphone jack for the stadium commentary. | Used at FIFA Club World Cup 2025 (Man City v Wydad). One fan said she could "feel part of the crowd" and live the same moments at the same time. |
| **OneCourt** (Seattle) | Real-time league tracking data drives a surface with hundreds of motors. Different vibrations for different plays. Radio audio plus buttons to hear the score and clock. | Founders say radio is "often delayed by 10 to 30 seconds". Used in NBA and NFL pilots and at Super Bowl LX. Soccer tested. |
| **"Unsilence the Crowd"** (Sela, RNID, Newcastle; CuteCircuit shirts, 13 Apr 2024) | Pitch-side microphones drive motors in the shirt. **Distinct patterns for home goal, away goal, clapping and singing.** | Fans tuned it at a pre-match session. A fan said he felt "as one with the crowd". RNID: "not a solution for everyone". 30 shirts were made. |

**Lesson for us:**
- **Team identity plus event type**, with only a few distinct patterns, is what shipped.
- Every product **adds audio**.
- **Simultaneity** is the emotional payoff.

### 3. Perception and fatigue: design limits

- **Tacton parameters.** Brewster & Brown (2004) list frequency, amplitude, waveform, duration, rhythm and body location. The web only exposes **duration and rhythm**. A gamepad adds two "textures" (strong vs weak motor).
- **Recognition.** 3 rhythms × 3 roughness levels gave 71% overall recognition. Rhythm alone reached 93% (Brown et al. 2005). Keep the alphabet small: about 6–8 tactons, each with a clearly different rhythm.
- **Pulses and gaps.** Fingertip study: about 30 ms is the minimum for a pulse to read as vibration (Remache-Vinueza et al. 2025). Android: gaps need ~50 ms or more, and actuators keep ringing 20–50 ms after short inputs. Our floor is **30 ms on, 50 ms off**.
- **Sensitivity** peaks near 250 Hz (Pacinian channel). This is irrelevant on the web, but it matters for vest and AHAP sharpness choices.
- **Fatigue.**
  - Prolonged stimulation (for example 10 minutes) raises later detection thresholds, and the effect is channel-specific (Remache-Vinueza et al. 2025, citing the literature).
  - Android: "less is more". Too much vibration numbs hands and makes people switch haptics off.
  - Apple: frequent haptics "become tiresome"; let people "turn off or mute haptics".
  - So a **90-minute continuous heartbeat is a bad idea.** Beat only in high-tension windows, cap each run, then rest.

### 4. Sync with audio

- **Perception windows.**
  - Altinsoy (2003): with 25 ms stimuli, pairs were judged synchronous from audio leading by 26 ms to audio lagging by 51 ms. The point of subjective simultaneity was about 7 ms of audio delay.
  - Kaaresoja (thesis, Glasgow) recommends tactile within 25 ms and audio within 100 ms for bimodal feedback.
  - Either way, **vibration slightly before sound is fine; vibration after sound is noticed sooner.**
- **No sourced figure for vibration API latency.** Kaaresoja's measurement method (microphone and accelerometer recorded at once, read in an audio editor) is cheap to copy. Phone motors are audible, so a laptop mic recording the speaker click and the buzz gives an offset.
- **Clock.** Use `AudioContext.getOutputTimestamp()` to map the audio clock to `performance.now()`, and include `outputLatency` (Baseline 2025). Convert each cue's audio time to a performance time, then fire with `setTimeout` (minus a calibrated `leadMs`).
- **Audio Stands bonus.** The pipeline runs on a look-ahead delay, so the heartbeat can **start rising before the shot**, in step with the commentator's build-up.

## So what for us

**Audio Stands, Render stage (touch channel), driven by the tension signal from Interpret:**
- Use win-probability swing and momentum (research 23) plus pressure (research 09).
- Map tension 0–1 to heartbeat tempo, about 55 to 140 BPM. Our mapping is a design choice, not a sourced number.
- Event tactons ride on the same timed cue JSON as the commentary (research 24 scheduler). Add a `haptic` field: `{tacton, team, at_audio_time}`.

**Vocabulary** (rhythm-coded, ≤10 entries, home/away by a prefix "signature"):

| Tacton | Pattern idea | Why |
|---|---|---|
| Heartbeat | lub–dub (two pulses), tempo and pulse length scale with tension | Familiar metaphor, and stays readable at a glance |
| Attack building | 3 ticks with shrinking gaps, fired once when tension crosses 0.6 | The "rising" pattern; Android notes rises are noticed more |
| Shot | signature + one 90 ms thump | Short and sharp |
| Near miss | thump then shrinking pulses ("deflate") | Same opening as goal, opposite ending (Apple: don't reuse a pattern for opposite outcomes) |
| Goal | signature + 3 quick + one 400 ms long | Celebration; most distinct by length |
| Yellow / red card | 2 or 3 long pulses | Count = colour |
| Whistle (kick-off, half-time, full-time) | 1, 2 or 3 long pulses, no team signature | Mirrors the referee |
| **Home vs away** | Home signature = one long pulse; away = two short. On a gamepad, home = strong (low) motor, away = weak (high) motor | Rhythm is the most recognisable dimension |

**User control:**
- Modes: Off / Key moments / Heartbeat + key moments.
- Three strength levels (they scale pulse length on the web).
- A "my team" setting, so only *your* goals get the long celebration.
- A tension floor (no heartbeat below 0.35).
- Heartbeat runs auto-capped at 3 minutes.
- A **"Test pattern / did you feel it?" button**. It also gives the sticky activation, and it catches the Firefox-Android silent no-op.
- Status is announced through `aria-live` (research 32).
- Keep the screen awake with the Screen Wake Lock API. A hidden page cannot vibrate, and the lock is released on tab switch, so re-request it.

**Honest iOS line** (for the UI and the write-up): "iPhone browsers do not let websites vibrate the phone. On iPhone you get the full audio experience. Haptics work on Android (Chrome or Samsung Internet), with a game controller on a computer, or with an audio-driven haptic vest."

**Native wrapper verdict:** skip it for the hackathon. Capacitor or Expo alone would not give a heartbeat. It would need a custom Swift Core Haptics plugin, a Mac, device signing and test time. Put the AHAP file and the plan in the repo as "next step".

**Other ideas:**
- **20 Home End:** send the crowd-mix bus to a Woojer vest.
- **10 Story Time:** a gentle goal tacton for kids.
- **F Graphics Desk:** a producer can "feel" cues on a controller during the demo.
- **21 Called It:** a tick when a prediction resolves.

## Reuse: code & links

```ts
// haptics.ts — tension→heartbeat, tacton library, vibrate + gamepad backends, audio-clock scheduling
export type Team = "home" | "away";
export type Tacton = "attack" | "shot" | "nearMiss" | "goal" | "yellow" | "red" | "whistle1" | "whistle2" | "whistle3";
export type Mode = "off" | "events" | "full";
export interface Settings { mode: Mode; strength: 0.7 | 1 | 1.4; myTeam: Team | null; tensionFloor: number; maxRunMs: number; leadMs: number; }
export const defaults: Settings = { mode: "full", strength: 1, myTeam: null, tensionFloor: 0.35, maxRunMs: 180_000, leadMs: 20 };

const MIN_ON = 30, MIN_OFF = 50, MAX_ENTRIES = 10;           // draft spec: 10 entries max
const SIG: Record<Team, number[]> = { home: [140, 90], away: [40, 60, 40, 90] }; // on,off,... ends with off
const BODY: Record<Tacton, number[]> = {                     // starts with on
  attack: [30, 120, 30, 80, 30], shot: [90], nearMiss: [90, 120, 60, 90, 30],
  goal: [60, 60, 60, 60, 60, 60, 400], yellow: [150, 100, 150], red: [150, 100, 150, 100, 150],
  whistle1: [350], whistle2: [350, 150, 350], whistle3: [350, 150, 350, 150, 600],
};
const clamp01 = (x: number) => Math.min(1, Math.max(0, x));

export function compose(t: Tacton, team: Team | null, strength = 1, isMine = true): number[] {
  const whistle = t.startsWith("whistle");
  let body = BODY[t];
  if (t === "goal" && !isMine) body = [60, 60, 200];          // opponent goal: muted
  const p = [...(team && !whistle ? SIG[team] : []), ...body]
    .map((d, i) => (i % 2 === 0 ? Math.max(MIN_ON, Math.round(d * strength)) : Math.max(MIN_OFF, d)));
  return p.slice(0, MAX_ENTRIES);
}

/** tension 0..1 → one lub-dub beat and the period until the next beat. Mapping is our design choice. */
export function heartbeat(tension: number, strength = 1) {
  const t = clamp01(tension), bpm = 55 + 85 * t, periodMs = 60_000 / bpm;
  const lub = Math.max(MIN_ON, Math.round((40 + 40 * t) * strength));
  const dub = Math.max(MIN_ON, Math.round((30 + 25 * t) * strength));
  return { pattern: [lub, Math.max(MIN_OFF, Math.round(0.2 * periodMs)), dub], periodMs, bpm };
}

interface Backend { name: string; play(p: number[], team: Team | null): void; stop(): void; }
const vibrateBackend: Backend = { name: "vibrate", play: p => { navigator.vibrate(p); }, stop: () => { navigator.vibrate(0); } };
function gamepadBackend(): Backend | null {
  const pad = navigator.getGamepads?.().find(g => g?.vibrationActuator);
  if (!pad) return null;
  const act = pad.vibrationActuator as GamepadHapticActuator;
  let timers: number[] = [];
  return { name: "gamepad",
    play(p, team) {                                            // replay on/off list as timed effects (each call preempts)
      this.stop(); let t = 0;
      p.forEach((d, i) => { if (i % 2 === 0) timers.push(window.setTimeout(() => act.playEffect("dual-rumble",
        { duration: d, strongMagnitude: team === "away" ? 0.2 : 1, weakMagnitude: team === "away" ? 1 : 0.3 }).catch(() => {}), t)); t += d; });
    },
    stop() { timers.forEach(clearTimeout); timers = []; act.reset?.().catch(() => {}); } };
}

/** Feature detection. Firefox Android returns true from vibrate() but never vibrates (MDN BCD), so exclude it and ask the user. */
export function detectBackend(): Backend | null {
  const ua = navigator.userAgent, firefox = /Firefox\//.test(ua);
  if ("vibrate" in navigator && !firefox) return vibrateBackend;
  return gamepadBackend();
}

export class Haptics {
  private backend = detectBackend(); private tension = 0; private beatTimer = 0;
  private runStart = 0; private busyUntil = 0;
  constructor(private ctx: AudioContext, public s: Settings = defaults) {
    document.addEventListener("visibilitychange", () => { if (document.hidden) this.stopAll(); });
    window.addEventListener("gamepadconnected", () => { this.backend ??= gamepadBackend(); });
  }
  get available() { return this.backend?.name ?? "none"; }
  /** audio-context time → performance.now() time at which that sample is heard */
  private audibleAt(ctxTime: number) {
    const ts = this.ctx.getOutputTimestamp();
    return (ts.performanceTime ?? performance.now()) + (ctxTime - (ts.contextTime ?? this.ctx.currentTime)) * 1000
      + (this.ctx.outputLatency ?? 0) * 1000;
  }
  /** Schedule a tacton so it lands with the matching commentary/crowd audio (fires leadMs early, never late). */
  event(t: Tacton, team: Team | null, atCtxTime: number) {
    if (!this.backend || this.s.mode === "off") return;
    const p = compose(t, team, this.s.strength, !this.s.myTeam || team === this.s.myTeam);
    const delay = Math.max(0, this.audibleAt(atCtxTime) - this.s.leadMs - performance.now());
    window.setTimeout(() => { this.backend!.play(p, team); this.busyUntil = performance.now() + p.reduce((a, b) => a + b, 0) + 600; }, delay);
  }
  setTension(x: number) {
    const was = this.tension; this.tension = clamp01(x);
    if (was < 0.6 && this.tension >= 0.6) this.event("attack", null, this.ctx.currentTime);
    const now = performance.now();
    if (!this.beatTimer && this.s.mode === "full" && this.tension >= this.s.tensionFloor && now >= this.restUntil) { this.runStart = now; this.beat(); }
  }
  private restUntil = 0;
  private beat = () => {
    const now = performance.now();
    if (now - this.runStart > this.s.maxRunMs) this.restUntil = now + 60_000;   // anti-fatigue: 1 min rest after a capped run
    if (this.s.mode !== "full" || this.tension < this.s.tensionFloor || now < this.restUntil) { this.beatTimer = 0; return; }
    const hb = heartbeat(this.tension, this.s.strength);
    if (now >= this.busyUntil) this.backend?.play(hb.pattern, null);   // event tactons pre-empt the heartbeat
    this.beatTimer = window.setTimeout(this.beat, hb.periodMs);
  };
  stopAll() { clearTimeout(this.beatTimer); this.beatTimer = 0; this.backend?.stop(); }
}
```

Settings toggle. The test button doubles as the sticky-activation gesture and the "did you feel it?" check.

```html
<fieldset id="haptics"><legend>Vibration</legend>
  <label><input type="radio" name="hmode" value="off"> Off</label>
  <label><input type="radio" name="hmode" value="events"> Key moments</label>
  <label><input type="radio" name="hmode" value="full" checked> Heartbeat and key moments</label>
  <label>Strength <select id="hstr"><option value="0.7">Low</option><option value="1" selected>Medium</option><option value="1.4">High</option></select></label>
  <button id="htest" type="button">Test: home goal</button>
  <p id="hstatus" aria-live="polite"></p>
</fieldset>
<script type="module">
  // after the Haptics instance h exists and the AudioContext is resumed in this same click:
  htest.onclick = () => { h.event("goal", "home", ctx.currentTime);
    hstatus.textContent = h.available === "none"
      ? "This browser cannot vibrate (iPhone, Firefox). Audio continues as normal."
      : `Playing a home goal pattern via ${h.available}. Did you feel it?`; };
  navigator.wakeLock?.request("screen").catch(() => {});   // a hidden page cannot vibrate
</script>
```

iOS native roadmap: an example AHAP for one high-tension heartbeat (120 BPM) followed by a home-goal swell. Apple's AHAP article names the duration key `Duration`. The Swift API constant is `CHHapticPattern.Key.eventDuration`, and sample files are commonly written with `"EventDuration"`. Confirm the spelling by loading the file in Xcode (unverified).

```json
{
  "Version": 1.0,
  "Pattern": [
    { "Event": { "Time": 0.00, "EventType": "HapticTransient",
      "EventParameters": [ { "ParameterID": "HapticIntensity", "ParameterValue": 1.0 },
                           { "ParameterID": "HapticSharpness", "ParameterValue": 0.3 } ] } },
    { "Event": { "Time": 0.12, "EventType": "HapticTransient",
      "EventParameters": [ { "ParameterID": "HapticIntensity", "ParameterValue": 0.6 },
                           { "ParameterID": "HapticSharpness", "ParameterValue": 0.2 } ] } },
    { "Event": { "Time": 0.50, "EventType": "HapticTransient",
      "EventParameters": [ { "ParameterID": "HapticIntensity", "ParameterValue": 1.0 },
                           { "ParameterID": "HapticSharpness", "ParameterValue": 0.3 } ] } },
    { "Event": { "Time": 0.62, "EventType": "HapticTransient",
      "EventParameters": [ { "ParameterID": "HapticIntensity", "ParameterValue": 0.6 },
                           { "ParameterID": "HapticSharpness", "ParameterValue": 0.2 } ] } },
    { "Event": { "Time": 1.20, "EventType": "HapticContinuous", "EventDuration": 1.2,
      "EventParameters": [ { "ParameterID": "HapticIntensity", "ParameterValue": 1.0 },
                           { "ParameterID": "HapticSharpness", "ParameterValue": 0.5 },
                           { "ParameterID": "AttackTime", "ParameterValue": 0.2 },
                           { "ParameterID": "ReleaseTime", "ParameterValue": 0.5 } ] } },
    { "ParameterCurve": { "ParameterID": "HapticIntensityControl", "Time": 1.20,
      "ParameterCurveControlPoints": [ { "Time": 0.0, "ParameterValue": 0.3 },
                                       { "Time": 0.6, "ParameterValue": 1.0 },
                                       { "Time": 1.2, "ParameterValue": 0.0 } ] } }
  ]
}
```

For a live heartbeat on iOS, don't play static files. Build a looping `CHHapticAdvancedPatternPlayer` (`loopEnabled = true`, as in Apple's HapticSampler) and change `HapticIntensityControl` with `sendParameters` as tension moves.

Links:
- `ios-haptics` (tap-only switch trick): https://github.com/tijnjh/ios-haptics
- Apple HapticSampler sample: https://developer.apple.com/documentation/corehaptics/playing-a-custom-haptic-pattern-from-a-file
- Capacitor Haptics: https://capacitorjs.com/docs/apis/haptics

## Sources

- MDN, Navigator.vibrate() — https://developer.mozilla.org/en-US/docs/Web/API/Navigator/vibrate — accessed 20 Oct 2026
- Can I use, Vibration API — https://caniuse.com/vibration — accessed 20 Oct 2026
- MDN browser-compat-data, api/Navigator.json (vibrate) — https://github.com/mdn/browser-compat-data/blob/main/api/Navigator.json — accessed 20 Oct 2026
- W3C Vibration API (editor's draft) — https://w3c.github.io/vibration/ — accessed 20 Oct 2026
- Chromium vibration_controller.cc — https://chromium.googlesource.com/chromium/src/+/main/third_party/blink/renderer/modules/vibration/vibration_controller.cc — accessed 20 Oct 2026
- WebKit Bug 285120, switch haptics should require user activation — https://bugs.webkit.org/show_bug.cgi?id=285120 — accessed 20 Oct 2026
- tijnjh/ios-haptics README — https://github.com/tijnjh/ios-haptics — accessed 20 Oct 2026
- MDN, GamepadHapticActuator.playEffect() — https://developer.mozilla.org/en-US/docs/Web/API/GamepadHapticActuator/playEffect — accessed 20 Oct 2026
- MDN browser-compat-data, api/GamepadHapticActuator.json — https://github.com/mdn/browser-compat-data/blob/main/api/GamepadHapticActuator.json — accessed 20 Oct 2026
- W3C Gamepad (haptics section) — https://w3c.github.io/gamepad/ — accessed 20 Oct 2026
- Apple, Representing haptic patterns in AHAP files — https://developer.apple.com/documentation/corehaptics/representing-haptic-patterns-in-ahap-files — accessed 20 Oct 2026
- Apple, CHHapticPattern.Key.eventDuration — https://developer.apple.com/documentation/corehaptics/chhapticpattern/key/eventduration — accessed 20 Oct 2026
- Apple, Playing a custom haptic pattern from a file — https://developer.apple.com/documentation/corehaptics/playing-a-custom-haptic-pattern-from-a-file — accessed 20 Oct 2026
- Apple, UIFeedbackGenerator — https://developer.apple.com/documentation/uikit/uifeedbackgenerator — accessed 20 Oct 2026
- Apple, WKHapticType — https://developer.apple.com/documentation/watchkit/wkhaptictype — accessed 20 Oct 2026
- Apple HIG, Playing haptics — https://developer.apple.com/design/human-interface-guidelines/playing-haptics — accessed 20 Oct 2026
- Android, Create custom haptic effects — https://developer.android.com/develop/ui/views/haptics/custom-haptic-effects — accessed 20 Oct 2026
- Android, Haptics design principles — https://developer.android.com/develop/ui/views/haptics/haptics-principles — accessed 20 Oct 2026
- Capacitor Haptics API — https://capacitorjs.com/docs/apis/haptics — accessed 20 Oct 2026
- Expo Haptics — https://docs.expo.dev/versions/latest/sdk/haptics/ — accessed 20 Oct 2026
- MDN, AudioContext.outputLatency — https://developer.mozilla.org/en-US/docs/Web/API/AudioContext/outputLatency — accessed 20 Oct 2026
- MDN, Screen Wake Lock API — https://developer.mozilla.org/en-US/docs/Web/API/Screen_Wake_Lock_API — accessed 20 Oct 2026
- Brown, Brewster & Purchase, "A first investigation into the effectiveness of Tactons", Eurohaptics/WHC 2005 — https://eprints.gla.ac.uk/3209 — accessed 20 Oct 2026
- Brewster & Brown, "Tactons: structured tactile messages for non-visual information display", AUIC 2004 (abstract) — https://crpit.scem.westernsydney.edu.au/abstracts/CRPITV28Brewster.html — accessed 20 Oct 2026
- Remache-Vinueza et al., "Vibrotactile stimulus duration threshold for perception of pulse to vibration transition", Sci Rep 2025 — https://pmc.ncbi.nlm.nih.gov/articles/PMC11814341 — accessed 20 Oct 2026
- Altinsoy, "Perceptual aspects of auditory-tactile asynchrony" (2003) — https://tu-dresden.de/ing/elektrotechnik/ias/aha/ressourcen/dateien/professur/publikationen/Altinsoy2003_-_Perceptual_aspects_of_auditory-tactile_asynchrony.pdf — accessed 20 Oct 2026
- Kaaresoja, "Latency guidelines for touchscreen virtual button feedback" (PhD thesis, Glasgow) — https://theses.gla.ac.uk/7075 — accessed 20 Oct 2026
- TechInformed, Newcastle "Unsilence the Crowd" haptic shirts — https://techinformed.com/haptic-5g-football-for-deaf-fans/ — accessed 20 Oct 2026
- TechCrunch, OneCourt haptic mini-field (CES 2024) — https://techcrunch.com/2024/01/09/onecourts-haptic-mini-field-lets-blind-fans-follow-the-game-by-touch — accessed 20 Oct 2026
- Dezeen, OneCourt at Super Bowl LX (Feb 2026) — https://www.dezeen.com/2026/02/06/onecourt-tactile-device-super-bowl-blind-low-vision-fans/ — accessed 20 Oct 2026
- FIFA, haptic devices for blind fans at Club World Cup 2025 — https://inside.fifa.com/organisation/news/blind-fans-club-world-cup-2025-social-responsibility — accessed 20 Oct 2026
- St. Louis CITY SC, Touch2See pilot (search summary; page not fetched, unverified detail) — https://www.stlcitysc.com/news/st-louis-city-sc-expands-energizer-park-s-best-in-class-accessibility-programming-by-testing-touch2see-program-for-blind-and-visually-impaired-fans — accessed 20 Oct 2026
- Field of Vision coverage (search summaries; the "<0.5 s" figure is a company claim, unverified) — https://eyesmart.com.au/newsarticle/7105-startup-field-of-vision-revolutionises-live-sports-for-visually-impaired — accessed 20 Oct 2026
- Woojer Vest 3 manual — https://www.woojer.com/pages/vest-3-manual — accessed 20 Oct 2026
