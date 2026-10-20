# 32 — An accessible, phone-friendly viewer: WCAG, colour-blind-safe team colours, captions, reduced motion and audio description

_Accessed/compiled: 20 Oct 2026 · Priority area: Render + Personalise (viewer UX, accessibility, judge-on-a-phone)_

## TL;DR

- **WCAG 2.2 AA can be met by a broadcast-style overlay if three things hold.** First, text sits on a plate, not straight on video: a black plate at **≥ 54% opacity** keeps white text at 4.5:1 even over a pure-white frame (66% gives 7:1; our own maths from the WCAG formula). Second, there is a **"Hide overlays / Freeze stats" control**, because overlays that move or auto-update for more than 5 s beside other content fall under SC 2.2.2 (Level A). Third, there is **no flashing more than 3 times a second** (2.3.1).
- **Team colours: simulate, then measure.** Simulate both kits for protan, deutan and tritan vision. Use Brettel 1997 matrices (public domain, from libDaltonLens) plus Machado 2009 as a cross-check, in linear RGB. Then require a CIEDE2000 ΔE **and** a lightness gap. The FA/UEFA advice already gives the rule of thumb: "imagine both kits in greyscale" and "one dark kit, one light kit". With **ΔE ≥ 30 and ΔL ≥ 30** (our thresholds), the checker below fails all 8 problem pairs we built from the FA list and passes all 5 of its good pairs. Whatever the result, never use colour alone (SC 1.4.1): always show the team abbreviation plus a shape or pattern.
- **We already have the text, so captions and audio description are almost free.** Our commentary is generated from cue text, so the **captions track is exact** (no speech-to-text). The same verified cues become a WebVTT `kind="descriptions"` track. Our demo is prerecorded, so **SC 1.2.5 (audio description, AA) applies to it**. Screen-reader users get cues through two live regions that exist from page load (polite and assertive), with throttling, de-duplication and a verbosity setting.
- **Phone first.** Fill the player with `aspect-ratio: 16/9` and `container-type: size`. Size overlay text in `cqh` units, inset it by `max(5%, env(safe-area-inset-*))`, and do not lock orientation (SC 1.3.4). In portrait, the video is only about 220 px tall, so cue text moves into a "cue rail" below the video. Tap targets are at least 24×24 CSS px (SC 2.5.8 AA); we aim for 44.
- **CI gate:** Playwright + `@axe-core/playwright` with tags `wcag2a, wcag2aa, wcag21a, wcag21aa, wcag22aa`, run at 3 viewports and under `emulateMedia({reducedMotion, contrast})`. Axe cannot judge text over video or the 2.2.2 and 2.3.1 timing rules, so add our own assertions for those.

## Findings

### 1. The WCAG 2.2 criteria that bite a live overlay

| SC (level) | What it says (short) | What it means for our overlay |
|---|---|---|
| 1.4.3 Contrast (AA) | Text needs 4.5:1, large text 3:1. Logotypes are exempt | Video behind text changes every frame, so the ratio can't be guaranteed without a plate. With white text on `rgb(0 0 0 / .54)` or darker, the worst case (white video) is 4.59:1. At `.66` it is 7.26:1 (our calculation, sRGB-space blending) |
| 1.4.11 Non-text contrast (AA) | Graphics needed for understanding: 3:1 against adjacent colours | Team chips, the possession bar and pitch-map dots each need 3:1 against the plate |
| 1.4.1 Use of colour (A) | Colour must not be the only visual means | Always add team abbreviation + shape/pattern; a "Reds" chip is never just red |
| 2.2.2 Pause, Stop, Hide (A) | Moving, blinking or scrolling content that starts automatically, lasts more than 5 s and runs beside other content needs pause/stop/hide. Auto-updating info needs pause/stop/hide or control of update frequency | A stats ticker, live win-probability bar or rolling name tags all qualify. Provide **Hide overlays** (key `H`) and **Freeze stats** |
| 2.3.1 Three flashes (A) | Nothing flashes more than 3 times in any 1 s (or stays below the flash thresholds) | No strobe "GOAL" bursts. A goal sting is a single fade |
| 2.3.3 Animation from interactions (AAA) | Motion triggered by interaction can be disabled | Chalk Talk zoom/pan, card flips. Honour `prefers-reduced-motion` plus an in-page toggle |
| 1.2.4 Captions, live (AA) / 1.2.2 prerecorded (A) | Captions for audio in synchronized media | Our TTS commentary → captions from the same text |
| 1.2.5 Audio description, prerecorded (AA) | AD for prerecorded video | The seeded demo video counts as prerecorded → ship a description track |
| 4.1.3 Status messages (AA) | Status messages are announced without moving focus (role/properties) | Use `role="status"` / `aria-live` for cue announcements, never `focus()` |
| 1.3.4 Orientation (AA), 1.4.10 Reflow (AA) | No orientation lock. Works at 320 CSS px wide with no 2-D scrolling | Portrait layout with a cue rail; no horizontal scroll |
| 2.5.8 Target size minimum (AA, new in 2.2) | Targets at least 24×24 CSS px, or spacing/equivalent exceptions | Player controls, mode chips, "?" explain buttons |

### 2. Broadcast-like *and* WCAG: design rules

- **Plates, not outlines.** Use a semi-opaque plate (≥ 0.54 black for white text). Under `prefers-contrast: more` it becomes solid black with a 2 px white outline. Under `forced-colors: active`, use the system colours `Canvas`/`CanvasText`. Both media queries are Baseline "widely available" (MDN: reduced motion since Jan 2020, `prefers-contrast` since May 2022). Under `forced-colors`, `prefers-contrast: custom` also matches.
- **Safe areas.** Keep the 5% graphics-safe margin from EBU R 95 (research 04). On phones, take `max(5%, env(safe-area-inset-*))`. `env()` is Baseline widely available. The insets only matter with `viewport-fit=cover`, and MDN says to use the inset variables when you set it. **Never** set `user-scalable=no`: MDN warns that it blocks low-vision zoom, and axe flags it (`meta-viewport`).
- **Subtitle conventions (BBC Subtitle Guidelines).**
  - Colours: white on black. Speaker colours in priority order are white, yellow `#FFFF00`, cyan `#00FFFF`, green `#00FF00`.
  - Lines: at most 2 for 16:9 and 3 for 9:16.
  - Size: online line width is at most 68% of a 16:9 frame and 90% of a 9:16 frame. Authored line height is 7–8% of video height (3.9–4.5% for 9:16). A 4-inch phone shows the authored size unscaled; larger screens scale it by 0.6–0.8.
  - Timing: live rate is 160–180 wpm, so about 0.3 s per word minimum.
  - Position: subtitles must avoid obscuring on-screen captions, and the guidelines name football as a case that needs extra reading time.

  **Rule for us:** subtitles and our overlays must never collide. When captions are on, reserve the bottom band for them and move lower-third cues up.
- **Pause/hide.** Use one `Hide overlays` toggle button (`aria-pressed`) and a `Freeze stats` button. While paused, live regions also stop announcing (the `paused` flag in the announcer). The video itself stays playable, because the live feed is arguably "essential" (unverified interpretation). Our *overlays* are not essential, so they must be hideable.
- **Reduced motion.** MDN names "scaling or panning large objects" as vestibular triggers. Variants:
  - slide-in → 150 ms opacity fade
  - count-up numbers → jump to the final value
  - Chalk Talk zoom/pan → static annotated frame
  - TwinCast orbiting camera → fixed tactical camera

  Also add an in-page "Motion: on/reduced" toggle that sets `data-motion`, so users who never changed their OS setting can still opt in. On iOS the OS setting is under Settings > Accessibility > Motion; on Android 9+ it is "Remove animations" (MDN).

### 3. Colour-blind-safe team colours

- **Prevalence and football problem pairs.** The kit advice PDF from Colour Blind Awareness / FA / UEFA says colour blindness affects 1 in 12 men and 1 in 200 women.
  - Problem combinations: red–green–orange, red–black, yellow–light green, blue–deep blue/pink, and all-red/orange/green kits against the pitch. TV wide shots and small screens make it worse.
  - Good pairs: blue–white, black–white, yellow–red, black–yellow, blue–yellow.
  - The test: imagine how both kits look "in greyscale". The ideal is one dark kit and one light kit.
  - The Premier League rulebook only advises "sufficient contrast" (press report, unverified).
- **Which simulation.** DaltonLens's review finds Brettel 1997 and Viénot 1999 "the clear winners (once adapted to sRGB)". For tritanopia, it says Brettel is still "basically only valid choice". Machado 2009 (IEEE TVCG 15(6); severity table on the authors' page) is useful for *anomalous* trichromacy. However, DaltonLens notes that its sRGB decoding was not clearly handled. DaltonLens applies Machado in linear RGB, and so do we.
- **Algorithm (code below, tested in Node 24):**
  1. Convert sRGB to linear.
  2. Simulate {normal, protan, deutan, tritan}. For protan/deutan, keep the worse of Brettel and Machado.
  3. Convert to CIELAB and compute **CIEDE2000**. Our implementation matches 5 Sharma et al. reference pairs to 4 decimals.
  4. Take the min ΔE over all visions, and the min ΔL\* over all visions (the "greyscale test").
  5. Pass if ΔE ≥ 30 and ΔL ≥ 30.
  6. `assignKits` tries every home × away kit pair and prefers the home team's earliest kit. If no pair passes, it returns the least-bad pair plus a forced fallback: stripes vs solid, circle vs triangle markers, and abbreviations always on.
  7. Chip text is black or white, whichever gives the higher WCAG ratio.
- **Calibration (our run, our hex picks; the PDF shows swatches, not hex values).**
  - FA "problem" pairs scored ΔE 4.6–24.9 and ΔL 0.5–27.3.
  - "Good" pairs scored ΔE 33.3–93.2 and ΔL 35.8–94.9.
  - Red vs green collapses to ΔE 6.4 under deutan.
  - Red vs black passes for normal vision (ΔE 38.9) but drops to 21.6 under protan, which is exactly the FA's warning.

  The thresholds are a design choice. Tune them with real colour-blind viewers.
- **Synthetic upside.** Our teams are fictional, so we *choose* the palettes. Run `assignKits` in the generator (E Realism Bench) and in the renderer (A TwinCast). Distinct light/dark kits should also make CV team classification by jersey colour easier (inference, untested).

### 4. Screen-reader mode, captions and audio description

- **Live regions (MDN).**
  - `polite` waits for "the next graceful opportunity".
  - `assertive` interrupts. MDN says not to use it unless the interruption is imperative. For tickers whose updates are not the widget's main purpose, MDN even suggests `off`.
  - The region must already be in the DOM, empty, before you write to it.
  - `role="status"` is the WCAG 4.1.3 technique (ARIA22).

  **Our design:**
  - Routine cues go to the polite region, at most one every 4 s (our default). Items older than 8 s are dropped, and a newer value of the same metric replaces the queued one.
  - Goals and red cards go to the assertive region and jump the queue.
  - Verbosity has three levels: goals only, normal, everything.
  - Announcing pauses when the video pauses.
  - The text is the cue's `describe` or `casual` string, and only cues with `truth_check == "pass"` are voiced.
- **Audio description track.** MDN says `kind="descriptions"` cues are "intended to be synthesized as audio". We found no statement that browsers voice them natively, so we treat it as **not supported** (unverified) and voice them ourselves on `cuechange`. Use `speechSynthesis` as a zero-cost fallback, or pre-rendered Azure TTS clips (research 27). The generator below lets a more important cue (a goal) cut the previous description short, and drops low-priority cues that would overlap.
- **Captions.** Put the commentary TTS text, plus sound labels such as `CROWD ROARS`, into a `kind="captions"` track. Turn it on by default in the judge demo.
- **How we differ from the blind-fan entries.**
  - **Competitors in the field.** Our intel lists **Audio Eyes (126311)** and **Blind-side (126432)** as "spatial audio for blind fans", and **VYBE (126450)** as accessibility-first with browser TTS (research 16). Their project pages returned 404 when we fetched them, so the details are unverified.
  - **Real-world equivalents.** Human audio-descriptive commentary (the FIFA Audio Description app, ITV at Women's Euro 2025) and haptics (OneCourt, Touch2See, FIFA haptic boards at the 2026 World Cup).
  - **Our angle.** Not "another blind-fan app" but **the same overlay stream, conformant by default**. Every cue carries text for each audience, captions, a description track and a live-region announcement, all generated from *verified* cues. Colour-blind-safe kits come from a tested algorithm, and an axe CI gate proves it.

  The blind-fan entries serve one audience. We show that accessibility falls out of the shared cue contract.

### 5. Phone layout (a judge opens the link on a phone)

- **Portrait (≈390×844).** The video is full width, so at 16:9 it is about 220 px tall.
  - Small in-video items (name tags, scorebug) stay inside the video.
  - Cue *text* moves into a cue rail below the video, on a solid background. That also solves contrast and reflow. The rail fits the BBC's 3-line maximum for 9:16.
  - Controls go in a bottom bar padded by `env(safe-area-inset-bottom)`.
- **Landscape/fullscreen.** Overlays sit inside the video, sized in `cqh` units and kept within the safe area. The captions band is reserved.
- **First-open checklist.**
  - No sign-in, and captions on by default.
  - A visible "Accessibility" sheet: Motion, Contrast, Captions, Audio description, Announce verbosity, Hide overlays.
  - Nothing autoplays with sound (our choice).
  - Settings saved in `localStorage`.
  - Targets at least 24 px, checked by axe (`target-size`, tagged `wcag22aa`). We aim for 44 px, a common platform guideline (unverified; not fetched).

### 6. Automated checks

- **What axe gives us.** `@axe-core/playwright` exposes `new AxeBuilder({ page }).include().exclude().withTags().analyze()`. Axe-core's tag list includes `wcag22aa`. Relevant rules: `color-contrast` (wcag143), `target-size` (wcag258), `meta-viewport` (wcag144), `video-caption` (wcag122), and `blink`/`marquee` (wcag222). These two are the only automated checks for 2.2.2.
- **Emulating user settings.** Playwright `page.emulateMedia` supports `reducedMotion` (v1.12), `forcedColors` (v1.15) and `contrast` (v1.51), so each variant can be scanned.
- **Limits of automation.** Playwright's docs say automated scans catch only some issues, so manual and user testing is still needed. Lighthouse's accessibility score is a weighted pass/fail average, weighted by axe user-impact levels.
- **What axe can't see:** text over moving video, 2.2.2 durations, 2.3.1 flash rate and live-region pacing. We cover these with our own assertions:
  - the plate's computed background alpha
  - `document.getAnimations()` under reduced motion
  - live regions present at load
  - the hide toggle working

## So what for us

- **Stages:** Render (overlay CSS, captions, description track) and Personalise (an accessibility profile as one more audience mode). Interpret also gains a kit-assignment step in the synthetic generator.
- **Ideas helped:**
  - **A TwinCast:** kit palettes that pass the checker, a reduced-motion camera, and a description track for the prerecorded demo (1.2.5 requires it).
  - **F Graphics Desk:** a "CVD preview" toggle that applies the Machado matrices as an SVG `feColorMatrix` filter on the program monitor, plus contrast lint on proposed cues.
  - **B Speed Trap:** name tags on plates, with abbreviation + shape.
  - **C One Number:** a single metric is ideal for screen readers.
  - **16 Vertical Match:** the portrait cue rail is the same layout.
  - **12 Jargon Buster** and **10 Story Time:** plain-language audience strings double as audio description.
  - **17 Heartbeat:** haptics complement audio description.
- **Recommendation (about 1.5 days for 2 people):**
  1. Adopt the CSS skeleton, `Announcer` and `assignKits` below as they are.
  2. Add `text.describe` to the cue contract.
  3. Have the render job emit `captions.vtt` and `descriptions.vtt`.
  4. Add the Playwright + axe job to CI, then show its green badge and a 20 s "accessibility mode" clip in the demo video.

  With 40–50 near-identical entries, a *verifiable* WCAG 2.2 AA claim is a cheap differentiator. It also aligns with Microsoft's accessibility emphasis (research 28).

## Reuse: code & links

### a) Player markup (live regions exist at load; tracks from our cue stream)

```html
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><!-- never user-scalable=no -->
<div class="player" data-motion="auto">
  <video id="v" playsinline controls muted>
    <source src="match.mp4" type="video/mp4">
    <track kind="captions" src="captions.vtt" srclang="en" label="English" default>
    <track kind="descriptions" src="descriptions.vtt" srclang="en" label="Audio description">
  </video>
  <div class="overlay-layer" aria-hidden="true"><!-- visual cues; announced separately --></div>
</div>
<section class="cue-rail" aria-label="Match insights"></section>
<div class="controls">
  <button class="ctrl" aria-pressed="false" id="hide">Hide overlays</button>
  <button class="ctrl" aria-pressed="false" id="freeze">Freeze stats</button>
  <button class="ctrl" aria-pressed="false" id="ad">Audio description</button>
</div>
<div id="sr-polite" class="sr-only" role="status" aria-live="polite"></div>
<div id="sr-assertive" class="sr-only" aria-live="assertive"></div>
<script type="module">
  const t = [...v.textTracks].find(t => t.kind === "descriptions");
  t.mode = "hidden";                                   // fire cuechange without rendering
  t.addEventListener("cuechange", () => {
    if (ad.getAttribute("aria-pressed") !== "true") return;
    for (const c of t.activeCues) speechSynthesis.speak(new SpeechSynthesisUtterance(c.text)); // or Azure TTS clip
  });
</script>
```

### b) Scalable overlay CSS (container queries, safe areas, reduced motion, contrast)

```css
.player { position: relative; width: 100%; aspect-ratio: 16 / 9; container: player / size; background: #000; }
.player video { position: absolute; inset: 0; width: 100%; height: 100%; }
.overlay-layer {
  position: absolute; inset: 0; pointer-events: none;
  /* EBU R95 graphics-safe 5% (research 04), or the device notch if larger */
  padding: max(5cqh, env(safe-area-inset-top, 0px)) max(5cqw, env(safe-area-inset-right, 0px))
           max(5cqh, env(safe-area-inset-bottom, 0px)) max(5cqw, env(safe-area-inset-left, 0px));
}
.cue {
  font: 600 clamp(12px, 4.2cqh, 44px)/1.25 system-ui, sans-serif;   /* sizes are our choice */
  color: #fff; background: rgb(0 0 0 / .72);                         /* >= .54 keeps 4.5:1 over white video */
  padding: .3em .6em; border-radius: .25em; max-width: 68cqw;        /* BBC 68% line width */
  animation: cue-in 300ms ease-out both;
}
.team-chip { display: inline-flex; gap: .3em; align-items: center; }
.team-chip::before { content: ""; width: .8em; height: .8em; background: var(--kit); outline: 1px solid #fff; }
.team-chip[data-shape="triangle"]::before { clip-path: polygon(50% 0, 100% 100%, 0 100%); }
.team-chip[data-pattern="stripes"]::before {
  background: repeating-linear-gradient(90deg, var(--kit) 0 2px, var(--kit2, #fff) 2px 4px); }
.captions-on .cue--lower { translate: 0 -18cqh; }                    /* keep clear of captions band */
.overlays-hidden .overlay-layer, .overlays-hidden .cue-rail { visibility: hidden; }
.ctrl { min-width: 44px; min-height: 44px; }                         /* WCAG 2.5.8 floor is 24px */

/* Portrait phone: video ~220px tall -> move text out of the picture into the rail */
@container player (height < 300px) { .cue--text { display: none; } }
.cue-rail { display: none; }
@media (orientation: portrait) and (max-width: 600px) {
  .cue-rail { display: block; background: #111; color: #fff; padding: 12px 16px;
              font-size: 1rem; max-height: calc(4.2em * 3); overflow-y: auto; }  /* BBC: 3 lines for 9:16 */
  .controls { position: sticky; bottom: 0; padding-bottom: calc(8px + env(safe-area-inset-bottom, 0px)); }
}

@keyframes cue-in   { from { opacity: 0; transform: translateY(20%); } }
@keyframes cue-fade { from { opacity: 0; } }
@media (prefers-reduced-motion: reduce) {
  .player[data-motion="auto"] .cue { animation: cue-fade 150ms linear both; }
  .player[data-motion="auto"] .ticker, .player[data-motion="auto"] .countup { animation: none; }
}
.player[data-motion="reduce"] .cue { animation: cue-fade 150ms linear both; }  /* in-page override */
@media (prefers-contrast: more) { .cue { background: #000; outline: 2px solid #fff; } }
@media (forced-colors: active)  { .cue { background: Canvas; color: CanvasText; border: 1px solid CanvasText; } }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
```

### c) Colour-blind clash checker (TypeScript, tested with Node 24; matrices: Brettel 1997 via public-domain libDaltonLens, Machado et al. 2009 severity 1.0)

```ts
// teamColours.ts — colour-blind-safe team colour checker (TypeScript, no deps)
// Simulation: Brettel 1997 (via libDaltonLens, public domain, precomputed for sRGB)
// and Machado 2009 severity 1.0 matrices; both applied in LINEAR RGB.
type RGB = [number, number, number];
type M3 = number[]; // row-major 3x3
export type Vision = "normal" | "protan" | "deutan" | "tritan";

const toLin = (c: number) => { const v = c / 255; return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
const hexToLin = (hex: string): RGB => {
  const n = parseInt(hex.replace("#", ""), 16);
  return [toLin((n >> 16) & 255), toLin((n >> 8) & 255), toLin(n & 255)];
};
const mul = (m: M3, c: RGB): RGB => [
  m[0]*c[0] + m[1]*c[1] + m[2]*c[2], m[3]*c[0] + m[4]*c[1] + m[5]*c[2], m[6]*c[0] + m[7]*c[1] + m[8]*c[2]];
const clamp = (c: RGB): RGB => c.map(v => Math.min(1, Math.max(0, v))) as RGB;

// Brettel 1997: two half-plane matrices + separation normal (libDaltonLens.c)
const BRETTEL: Record<Exclude<Vision, "normal">, { a: M3; b: M3; n: RGB }> = {
  protan: { a: [0.14980,1.19548,-0.34528, 0.10764,0.84864,0.04372, 0.00384,-0.00540,1.00156],
            b: [0.14570,1.16172,-0.30742, 0.10816,0.85291,0.03892, 0.00386,-0.00524,1.00139],
            n: [0.00048,0.00393,-0.00441] },
  deutan: { a: [0.36477,0.86381,-0.22858, 0.26294,0.64245,0.09462, -0.02006,0.02728,0.99278],
            b: [0.37298,0.88166,-0.25464, 0.25954,0.63506,0.10540, -0.01980,0.02784,0.99196],
            n: [-0.00281,-0.00611,0.00892] },
  tritan: { a: [1.01277,0.13548,-0.14826, -0.01243,0.86812,0.14431, 0.07589,0.80500,0.11911],
            b: [0.93678,0.18979,-0.12657, 0.06154,0.81526,0.12320, -0.37562,1.12767,0.24796],
            n: [0.03901,-0.02788,-0.01113] },
};
// Machado, Oliveira & Fernandes 2009, severity 1.0 (tritan not modelled well; use Brettel)
const MACHADO: Record<"protan" | "deutan", M3> = {
  protan: [0.152286,1.052583,-0.204868, 0.114503,0.786281,0.099216, -0.003882,-0.048116,1.051998],
  deutan: [0.367322,0.860646,-0.227968, 0.280085,0.672501,0.047413, -0.011820,0.042940,0.968881],
};

export function simulate(lin: RGB, v: Vision, model: "brettel" | "machado" = "brettel"): RGB {
  if (v === "normal") return lin;
  if (model === "machado" && v !== "tritan") return clamp(mul(MACHADO[v], lin));
  const p = BRETTEL[v];
  const side = lin[0]*p.n[0] + lin[1]*p.n[1] + lin[2]*p.n[2];
  return clamp(mul(side >= 0 ? p.a : p.b, lin));
}

// linear sRGB -> CIELAB (D65)
function lab(c: RGB): RGB {
  const X = (0.4124564*c[0] + 0.3575761*c[1] + 0.1804375*c[2]) / 0.95047;
  const Y =  0.2126729*c[0] + 0.7151522*c[1] + 0.0721750*c[2];
  const Z = (0.0193339*c[0] + 0.1191920*c[1] + 0.9503041*c[2]) / 1.08883;
  const f = (t: number) => t > 216/24389 ? Math.cbrt(t) : (24389/27*t + 16) / 116;
  return [116*f(Y) - 16, 500*(f(X) - f(Y)), 200*(f(Y) - f(Z))];
}

// CIEDE2000 (Sharma, Wu & Dalal 2005)
export function deltaE2000([L1, a1, b1]: RGB, [L2, a2, b2]: RGB): number {
  const rad = Math.PI / 180, C1 = Math.hypot(a1, b1), C2 = Math.hypot(a2, b2);
  const Cb7 = ((C1 + C2) / 2) ** 7, G = 0.5 * (1 - Math.sqrt(Cb7 / (Cb7 + 25 ** 7)));
  const ap1 = a1 * (1 + G), ap2 = a2 * (1 + G);
  const Cp1 = Math.hypot(ap1, b1), Cp2 = Math.hypot(ap2, b2);
  const hue = (b: number, a: number) => (b === 0 && a === 0) ? 0 : (Math.atan2(b, a) / rad + 360) % 360;
  const hp1 = hue(b1, ap1), hp2 = hue(b2, ap2);
  const dL = L2 - L1, dC = Cp2 - Cp1;
  let dh = 0;
  if (Cp1 * Cp2 !== 0) { dh = hp2 - hp1; if (dh > 180) dh -= 360; else if (dh < -180) dh += 360; }
  const dH = 2 * Math.sqrt(Cp1 * Cp2) * Math.sin((dh / 2) * rad);
  const Lb = (L1 + L2) / 2, Cb = (Cp1 + Cp2) / 2;
  let hb = hp1 + hp2;
  if (Cp1 * Cp2 !== 0) { hb = Math.abs(hp1 - hp2) > 180 ? (hp1 + hp2 + (hp1 + hp2 < 360 ? 360 : -360)) / 2 : (hp1 + hp2) / 2; }
  const T = 1 - 0.17*Math.cos((hb - 30)*rad) + 0.24*Math.cos(2*hb*rad) + 0.32*Math.cos((3*hb + 6)*rad) - 0.20*Math.cos((4*hb - 63)*rad);
  const SL = 1 + 0.015 * (Lb - 50) ** 2 / Math.sqrt(20 + (Lb - 50) ** 2), SC = 1 + 0.045 * Cb, SH = 1 + 0.015 * Cb * T;
  const Cb7p = Cb ** 7, RT = -2 * Math.sqrt(Cb7p / (Cb7p + 25 ** 7)) * Math.sin(60 * Math.exp(-(((hb - 275) / 25) ** 2)) * rad);
  return Math.sqrt((dL/SL) ** 2 + (dC/SC) ** 2 + (dH/SH) ** 2 + RT * (dC/SC) * (dH/SH));
}

const relLum = (c: RGB) => 0.2126*c[0] + 0.7152*c[1] + 0.0722*c[2];
export const contrastRatio = (a: string, b: string) => {
  const [x, y] = [relLum(hexToLin(a)), relLum(hexToLin(b))].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
};
/** Text colour for a team chip: whichever of black/white has the higher WCAG ratio. */
export const chipText = (bg: string) => contrastRatio(bg, "#FFFFFF") >= contrastRatio(bg, "#000000") ? "#FFFFFF" : "#000000";

export interface ClashReport { worstVision: Vision; minDeltaE: number; deltaL: number; perVision: Record<Vision, number>; ok: boolean; }
// Thresholds are OUR choice, not a standard: set so all 8 FA/UEFA "problem" pairs fail and
// all 5 "good" pairs pass with our hex picks (bad max dE 24.9 / dL 27.3; good min 33.3 / 35.8).
export const MIN_DE = 30, MIN_DL = 30;

export function checkPair(hexA: string, hexB: string): ClashReport {
  const A = hexToLin(hexA), B = hexToLin(hexB);
  const per = {} as Record<Vision, number>;
  for (const v of ["normal", "protan", "deutan", "tritan"] as Vision[]) {
    const models = v === "protan" || v === "deutan" ? (["brettel", "machado"] as const) : (["brettel"] as const);
    per[v] = Math.min(...models.map(m => deltaE2000(lab(simulate(A, v, m)), lab(simulate(B, v, m)))));
  }
  const worst = (Object.keys(per) as Vision[]).reduce((w, v) => (per[v] < per[w] ? v : w), "normal");
  // "Greyscale test" from the FA/UEFA kit advice, applied under every simulated vision.
  const deltaL = Math.min(...(["normal", "protan", "deutan", "tritan"] as Vision[])
    .map(v => Math.abs(lab(simulate(A, v))[0] - lab(simulate(B, v))[0])));
  return { worstVision: worst, minDeltaE: per[worst], deltaL, perVision: per, ok: per[worst] >= MIN_DE && deltaL >= MIN_DL };
}

/** Pick a passing kit pair, preferring the home team's earliest kit; else the least-bad pair + fallback. */
export function assignKits(home: string[], away: string[]) {
  const all = home.flatMap((h, i) => away.map((a, j) => ({ h, a, i, j, r: checkPair(h, a) })));
  const passing = all.filter(x => x.r.ok).sort((x, y) => x.i - y.i || y.r.minDeltaE - x.r.minDeltaE);
  const best = passing[0] ?? all.sort((x, y) => y.r.minDeltaE - x.r.minDeltaE)[0];
  return {
    home: best.h, away: best.a, report: best.r,
    // Fallback when nothing passes: never rely on colour alone (WCAG 1.4.1).
    fallback: best.r.ok ? null : { homePattern: "solid", awayPattern: "stripes", homeShape: "circle", awayShape: "triangle", forceAbbrev: true },
    chipText: { home: chipText(best.h), away: chipText(best.a) },
  };
}
```

Usage: `assignKits(["#C8102E","#FFFFFF"], ["#00843D","#111111"])` → home `#FFFFFF`, away `#111111` (red v green and red v black both fail). `assignKits(["#C8102E"],["#00843D"])` → returns the fallback (stripes/triangle/abbrev). For the Graphics Desk preview, a single-matrix model (Machado, or Viénot) drops into an SVG `<feColorMatrix type="matrix">` with `color-interpolation-filters="linearRGB"`. Brettel's two half-planes need two matrices plus a mask, which the DaltonLens SVG-filter article covers (not fetched).

### d) Throttled aria-live announcer (TypeScript, tested with fake regions)

```ts
// announcer.ts — throttled screen-reader announcer for overlay cues
type Prio = "urgent" | "normal" | "low";
interface Item { text: string; prio: Prio; at: number; key?: string }
interface Region { textContent: string | null }

export class Announcer {
  private queue: Item[] = [];
  private last = -Infinity;
  private timer: ReturnType<typeof setTimeout> | null = null;
  paused = false;            // tie to video.paused and to a "Quiet" toggle
  verbosity: Prio = "normal"; // "urgent" = goals/cards only, "low" = everything

  private polite: Region; private assertive: Region;
  private minGapMs: number; private maxAgeMs: number; private now: () => number;
  // Gap and max age are OUR defaults, not from a standard; tune with screen-reader users.
  constructor(polite: Region, assertive: Region, minGapMs = 4000, maxAgeMs = 8000, now = () => Date.now()) {
    this.polite = polite; this.assertive = assertive;
    this.minGapMs = minGapMs; this.maxAgeMs = maxAgeMs; this.now = now;
  }

  say(text: string, prio: Prio = "normal", key?: string) {
    const rank = { urgent: 0, normal: 1, low: 2 };
    if (rank[prio] > rank[this.verbosity]) return;
    if (key) this.queue = this.queue.filter(i => i.key !== key); // newest value of a metric wins
    this.queue.push({ text, prio, at: this.now(), key });
    if (prio === "urgent" && this.timer) { clearTimeout(this.timer); this.timer = null; } // goals jump the queue
    this.pump();
  }

  private pump() {
    if (this.timer || this.paused) return;
    const t = this.now();
    this.queue = this.queue.filter(i => i.prio === "urgent" || t - i.at <= this.maxAgeMs); // stale = drop
    if (!this.queue.length) return;
    this.queue.sort((a, b) => (a.prio === "urgent" ? 0 : 1) - (b.prio === "urgent" ? 0 : 1) || a.at - b.at);
    const wait = this.queue[0].prio === "urgent" ? 0 : Math.max(0, this.last + this.minGapMs - t);
    this.timer = setTimeout(() => {
      this.timer = null;
      const item = this.queue.shift();
      if (!item || this.paused) return;
      if (item.prio !== "urgent" && this.now() - item.at > this.maxAgeMs) return this.pump(); // went stale while waiting
      const region = item.prio === "urgent" ? this.assertive : this.polite;
      region.textContent = "";                                  // clear so repeats re-announce
      setTimeout(() => { region.textContent = item.text; }, 50);
      this.last = this.now();
      this.pump();
    }, wait);
  }

  resume() { this.paused = false; this.pump(); }
}
```

Wire-up: `const an = new Announcer(srPolite, srAssertive); onCue(c => c.truth_check === "pass" && an.say(c.text.describe ?? c.text.casual, c.metric_kind === "goal" ? "urgent" : "normal", c.metric));` and `video.onpause = () => an.paused = true; video.onplay = () => an.resume();`.

### e) Cue stream → `descriptions.vtt` (Python, tested)

```python
"""cues.jsonl -> descriptions.vtt (kind="descriptions"). Speech rate is OUR assumption."""
import json, sys
WPM = 170  # assumption: mid of the 160-180 wpm live rate BBC/Ofcom use for subtitles
PRIORITY = {"goal": 0, "card": 1, "shot": 1, "big_chance": 1, "sub": 3, "pass": 4}  # lower = more important

def ts(sec: float) -> str:
    h, rem = divmod(sec, 3600); m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"

def tc_to_sec(tc: str, fps: int = 25) -> float:  # "HH:MM:SS:FF"
    h, m, s, f = map(int, tc.split(":")); return h * 3600 + m * 60 + s + f / fps

def build(cues, audience="describe"):
    kept = []  # [start, end, prio, cue_id, text]
    for c in sorted(cues, key=lambda c: tc_to_sec(c["tc_in"])):
        text = c["text"].get(audience) or c["text"].get("casual")
        if not text or c.get("truth_check") != "pass":
            continue                                   # never voice an unverified claim
        start, prio = tc_to_sec(c["tc_in"]), PRIORITY.get(c.get("metric_kind"), 9)
        end = start + max(1.2, len(text.split()) * 60 / WPM)
        if kept and start < kept[-1][1]:               # overlaps the line being spoken
            if prio < kept[-1][2]: kept[-1][1] = start # more important: cut the old line short
            else: continue                             # less/equally important: drop it
        kept.append([start, end, prio, c["cue_id"], text])
    lines = ["WEBVTT", ""]
    for s, e, _, cid, text in kept:
        lines += [cid, f"{ts(s)} --> {ts(e)}", text, ""]
    return "\n".join(lines)

if __name__ == "__main__":
    print(build(json.loads(l) for l in open(sys.argv[1], encoding="utf-8")))
```

### f) Playwright + axe CI test (not run here; APIs per Playwright and axe docs)

```ts
// tests/a11y.spec.ts   npm i -D @playwright/test @axe-core/playwright
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const VIEWPORTS = { desktop: { width: 1280, height: 720 }, portrait: { width: 390, height: 844 }, landscape: { width: 844, height: 390 } };

for (const [name, viewport] of Object.entries(VIEWPORTS)) {
  test(`axe WCAG 2.2 AA – ${name}`, async ({ page }, testInfo) => {
    await page.setViewportSize(viewport);
    await page.goto("/?seed=42&demo=1");
    await page.waitForSelector(".cue");                    // at least one overlay rendered
    for (const media of [{}, { reducedMotion: "reduce" as const }, { contrast: "more" as const }]) {
      await page.emulateMedia(media);
      const r = await new AxeBuilder({ page }).withTags(TAGS).analyze();
      await testInfo.attach(`axe-${name}-${JSON.stringify(media)}`, { body: JSON.stringify(r, null, 2), contentType: "application/json" });
      expect(r.violations).toEqual([]);
    }
  });
}

test("things axe cannot see", async ({ page }) => {
  await page.goto("/?seed=42&demo=1");
  // live regions exist and are empty at load (MDN: region must pre-exist)
  await expect(page.locator('[aria-live="polite"]')).toHaveText("");
  await expect(page.locator('[aria-live="assertive"]')).toHaveCount(1);
  // plate alpha keeps 4.5:1 over any video frame
  const alpha = await page.locator(".cue").first().evaluate(el => {
    const p = getComputedStyle(el).backgroundColor.match(/\(([^)]+)\)/)![1].split(/[\s,\/]+/);
    return p.length === 4 ? Number(p[3]) : 1;               // "rgb(0, 0, 0)" = opaque
  });
  expect(alpha).toBeGreaterThanOrEqual(0.54);
  // 2.2.2: overlays can be hidden
  await page.getByRole("button", { name: /hide overlays/i }).click();
  await expect(page.locator(".overlay-layer")).toBeHidden();
  // reduced motion: no transform animations on cues
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.reload(); await page.waitForSelector(".cue");
  const moving = await page.evaluate(() => document.getAnimations()
    .filter(a => (a.effect as KeyframeEffect).getKeyframes().some(k => "transform" in k)).length);
  expect(moving).toBe(0);
  // 2.5.8: every control >= 24x24 CSS px
  for (const b of await page.getByRole("button").all()) {
    const box = await b.boundingBox();
    if (box) expect(Math.min(box.width, box.height)).toBeGreaterThanOrEqual(24);
  }
});
```

CI: `npx playwright install --with-deps chromium webkit && npx playwright test` in a GitHub Actions job, with `use.baseURL` pointing at the Static Web Apps preview URL.

### Links

- DaltonLens-Python (Brettel/Viénot/Machado simulators; check repo licence) — https://github.com/DaltonLens/DaltonLens-Python
- libDaltonLens (single-file C, public domain; source of our Brettel matrices) — https://github.com/DaltonLens/libDaltonLens
- axe-core Playwright package — https://github.com/dequelabs/axe-core-npm/tree/develop/packages/playwright
- axe-core rule list with WCAG tags — https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md

## Sources

- W3C, Web Content Accessibility Guidelines (WCAG) 2.2 — https://www.w3.org/TR/WCAG22/ — accessed 20 Oct 2026
- W3C, Understanding SC 2.5.8 Target Size (Minimum) — https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html — accessed 20 Oct 2026
- W3C, Understanding SC 4.1.3 Status Messages — https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html — accessed 20 Oct 2026
- MDN, prefers-reduced-motion — https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion — accessed 20 Oct 2026
- MDN, prefers-contrast — https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-contrast — accessed 20 Oct 2026
- MDN, aria-live — https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Attributes/aria-live — accessed 20 Oct 2026
- MDN, &lt;track&gt; element (kind values) — https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/track — accessed 20 Oct 2026
- MDN, env() / safe-area-inset — https://developer.mozilla.org/en-US/docs/Web/CSS/env — accessed 20 Oct 2026
- MDN, Container queries — https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_containment/Container_queries — accessed 20 Oct 2026
- MDN, viewport meta (viewport-fit, user-scalable) — https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/meta/name/viewport — accessed 20 Oct 2026
- Machado, Oliveira, Fernandes, "A Physiologically-based Model for Simulation of Color Vision Deficiency", IEEE TVCG 15(6) 2009 — https://www.inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/CVD_Simulation.html — accessed 20 Oct 2026
- DaltonLens, "Review of open source color blindness simulations" — https://daltonlens.org/opensource-cvd-simulation/ — accessed 20 Oct 2026
- libDaltonLens source (Brettel 1997 precomputed sRGB matrices, public domain) — https://github.com/DaltonLens/libDaltonLens/blob/master/libDaltonLens.c — accessed 20 Oct 2026
- DaltonLens-Python simulate.py (Machado severity tables applied in linear RGB) — https://github.com/DaltonLens/DaltonLens-Python/blob/master/daltonlens/simulate.py — accessed 20 Oct 2026
- Colour Blind Awareness / UEFA, "Advice when selecting kit colours" (PDF) — https://www.colourblindawareness.org/wp-content/uploads/2020/07/Kit-Selection-Advice-FINAL.pdf — accessed 20 Oct 2026
- The FA, colour blindness guidance (2017) — https://www.thefa.com/news/2017/jun/19/colour-blindness-guidance-190617 — accessed 20 Oct 2026
- Footy Headlines, PL rulebook "sufficient contrast" (secondary, unverified) — https://amp.footyheadlines.com/1207285759246537869 — accessed 20 Oct 2026
- BBC Subtitle Guidelines — https://www.bbc.co.uk/accessibility/forproducts/guides/subtitles/ — accessed 20 Oct 2026
- Playwright, Accessibility testing — https://playwright.dev/docs/accessibility-testing — accessed 20 Oct 2026
- Playwright, page.emulateMedia — https://playwright.dev/docs/api/class-page#page-emulate-media — accessed 20 Oct 2026
- Deque, @axe-core/playwright README — https://github.com/dequelabs/axe-core-npm/blob/develop/packages/playwright/README.md — accessed 20 Oct 2026
- Deque, axe-core API (tags incl. wcag22aa) — https://github.com/dequelabs/axe-core/blob/develop/doc/API.md — accessed 20 Oct 2026
- Chrome for Developers, Lighthouse accessibility scoring — https://developer.chrome.com/docs/lighthouse/accessibility/scoring — accessed 20 Oct 2026
- FIFA, Audio-descriptive commentary and haptic boards — https://inside.fifa.com/organisation/news/audio-desctiptive-commentary-haptic-boards-jillian-sloane-canada — accessed 20 Oct 2026
- European Blind Union, Lionesses get audio description (ITV, Euro 2025) — https://www.euroblind.org/newsletter/2025/august/en/football-lionesses-get-audio-description — accessed 20 Oct 2026
- Microsoft Accessibility Blog, OneCourt — https://blogs.microsoft.com/accessibility/onecourt-revolutionizing-accessibility-in-live-sports/ — accessed 20 Oct 2026
- Embedded.com, Touch2See — https://www.embedded.com/?p=4492907 — accessed 20 Oct 2026
- Innovation Studio project pages Audio Eyes (126311) and Blind-side (126432) — https://innovationstudio.microsoft.com/hackathons/insidethegamedeveloperhackathon/project/126311 , .../126432 — accessed 20 Oct 2026 (both returned 404; descriptions from local `Berbata_Hackathon_Intel.md`)
