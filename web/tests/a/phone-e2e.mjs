// OWNER: A (potencialbg). Manual end-to-end check on a phone-sized Chromium, against the LIVE relay (it costs a few
// Voice Live questions, so it is not in CI). A fake microphone "speaks" a WAV file, and an analyser on every
// AudioContext's output records how loud each context is, so "did the answer play / did it stop" is measured, not
// guessed. Run from web/:
//   node tests/a/phone-e2e.mjs --wav path/to/question.wav [--url http://localhost:5173] [--relay https://...]
//        [--out dir] [--only start,ask,barge,pause]
// Prints one JSON report; screenshots (1080x1920) go to --out.
import { chromium } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const arg = (k, d) => { const i = process.argv.indexOf(`--${k}`); return i > 0 ? process.argv[i + 1] : d; };
const URL_BASE = arg('url', 'http://localhost:5173');
const RELAY = arg('relay', 'https://ca-relay-calef3.icycliff-4b45d13b.swedencentral.azurecontainerapps.io');
const WAV = arg('wav');
const OUT = resolve(arg('out', 'test-results/phone-e2e'));
const ONLY = new Set((arg('only', 'start,ask,barge,pause')).split(','));
const QUERY = arg('query', '');
mkdirSync(OUT, { recursive: true });

// Labels every AudioContext by creation order and samples its output RMS every 100 ms (only while running).
const PROBE = () => {
  const ctxs = [];
  const taps = new WeakMap();
  window.__rms = [];
  const Orig = window.AudioContext;
  window.AudioContext = class extends Orig {
    constructor(...a) { super(...a); this.__id = ctxs.length; ctxs.push(this); window.__rms.push([]); }
  };
  const tap = (ctx) => {
    let an = taps.get(ctx);
    if (!an) {
      an = ctx.createAnalyser();
      an.fftSize = 2048;
      taps.set(ctx, an);
      const buf = new Float32Array(an.fftSize);
      setInterval(() => {
        if (ctx.state !== 'running') { window.__rms[ctx.__id]?.push([performance.now(), -1]); return; }
        an.getFloatTimeDomainData(buf);
        let s = 0; for (const v of buf) s += v * v;
        window.__rms[ctx.__id]?.push([performance.now(), Math.sqrt(s / buf.length)]);
      }, 100);
    }
    return an;
  };
  const connect = AudioNode.prototype.connect;
  AudioNode.prototype.connect = function (dest, ...rest) {
    if (dest instanceof AudioDestinationNode && this.context.__id !== undefined) connect.call(this, tap(this.context));
    return connect.call(this, dest, ...rest);
  };
  window.__ctxState = () => ctxs.map((c) => c.state);
};

const report = { url: URL_BASE, when: new Date().toISOString(), steps: [] };
const step = (name, pass, evidence) => { report.steps.push({ name, pass, ...evidence }); console.error(`${pass ? 'PASS' : 'FAIL'} ${name}`, JSON.stringify(evidence)); };

const browser = await chromium.launch({
  headless: true,
  args: ['--autoplay-policy=no-user-gesture-required', '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream',
    ...(WAV ? [`--use-file-for-fake-audio-capture=${resolve(WAV)}`] : [])],
});
const context = await browser.newContext({
  viewport: { width: 360, height: 640 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true,
  userAgent: 'Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36',
  permissions: ['microphone'],
});
await context.addInitScript(PROBE);
const page = await context.newPage();
const logs = [];
page.on('console', (m) => logs.push(`${m.type()}: ${m.text()}`));
page.on('pageerror', (e) => logs.push(`pageerror: ${e.message}`));

const wait = (ms) => page.waitForTimeout(ms);
const now = () => page.evaluate(() => performance.now());
/** Peak RMS of context i between t0 and t1 (performance.now ms). */
const peak = async (i, t0, t1 = Infinity) => page.evaluate(([i, t0, t1]) =>
  Math.max(0, ...(window.__rms[i] ?? []).filter(([t, v]) => t >= t0 && t <= t1 && v >= 0).map(([, v]) => v)), [i, t0, t1]);
/** First time after t0 that context i went quiet (RMS under thr) and stayed quiet for `hold` ms. */
const quietAt = async (i, t0, thr = 0.002, hold = 300) => page.evaluate(([i, t0, thr, hold]) => {
  const xs = (window.__rms[i] ?? []).filter(([t]) => t >= t0);
  for (let k = 0; k < xs.length; k++) {
    if (xs[k][1] < thr && xs.slice(k).filter(([t]) => t <= xs[k][0] + hold).every(([, v]) => v < thr)) return xs[k][0];
  }
  return null;
}, [i, t0, thr, hold]);
const text = (sel) => page.locator(sel).first().innerText().catch(() => null);
const playhead = () => page.evaluate(() => window.audioStandsCommentary?.['o']?.clock?.now?.() ?? null);
const live = () => page.evaluate(() => ({ events: window.audioStandsLive?.events ?? [], turns: window.audioStandsLive?.turns ?? [] }));
const shot = (name) => page.screenshot({ path: `${OUT}/${name}.png` });
const ASK = '#ask';
const askLabel = () => page.locator(ASK).getAttribute('aria-label').then((l) => l ?? page.locator(ASK).innerText());

await page.goto(`${URL_BASE}/?debug=1&relay=${encodeURIComponent(RELAY)}${QUERY}`);
await page.waitForFunction(() => document.getElementById('status')?.textContent?.startsWith('Ready'));
await shot('00-ready');

// ---- 1. Start: crowd + commentary
await page.tap('#start');
await page.waitForFunction(() => document.querySelector('[data-sb="state"]')?.textContent === 'Playing', null, { timeout: 30_000 });
const tStart = await now();
const clock0 = await text('[data-sb="clock"]');
await wait(25_000);
const ids = await page.evaluate(() => window.__rms.length);
const peaks = [];
for (let i = 0; i < ids; i++) peaks.push(await peak(i, tStart));
const clock1 = await text('[data-sb="clock"]');
step('start: match plays, crowd and commentary audible', peaks.filter((p) => p > 0.001).length >= 2, {
  contexts: ids, peakRmsPerContext: peaks.map((p) => +p.toFixed(4)), clockBefore: clock0, clockAfter25s: clock1,
  status: await text('#status'), ctxState: await page.evaluate(() => window.__ctxState()) });
await shot('01-playing');
// Which context is which: the stage (crowd) is the loudest steady one; the live voice one is silent until an answer.
const order = peaks.map((p, i) => [p, i]).sort((a, b) => b[0] - a[0]);
const liveVoiceGuess = peaks.findIndex((p) => p < 0.0005);
report.contexts = { peaks, liveVoiceGuess };

const liveCtx = () => page.evaluate(() => window.__rms.length);
const waitAskIdle = (ms) => page.waitForFunction((a) => !document.querySelector(a)?.textContent?.includes('Stop'), ASK, { timeout: ms });

// ---- 2. Ask out loud: question -> answer
if (ONLY.has('ask')) {
  const t0 = await now();
  await page.tap(ASK);
  const liveBtn = page.locator('#ask-live');
  if (await liveBtn.isVisible().catch(() => false)) await liveBtn.tap();
  await shot('02-ask-listening');
  let firstAudio = null;
  try {
    await page.waitForFunction(() => (window.audioStandsLive?.turns?.length ?? 0) > 0
      || (window.audioStandsLive?.events ?? []).some(([, e]) => e.startsWith('refusal')), null, { timeout: 30_000 });
  } catch { /* reported below */ }
  const l = await live();
  await shot('03-ask-answering');
  await waitAskIdle(60_000).catch(() => {});
  const t1 = await now();
  const n = await liveCtx();
  const answerPeaks = [];
  for (let i = 0; i < n; i++) answerPeaks.push(+(await peak(i, t0, t1)).toFixed(4));
  const turn = l.turns.at(-1);
  step('ask: spoken question answered out loud', !!turn && !l.events.some(([, e]) => e.startsWith('refusal')), {
    events: l.events, question: turn?.question ?? turn?.q, answer: turn?.answer ?? turn?.say, latency: turn?.latency_ms ?? turn?.latency,
    peakRmsPerContextDuringAsk: answerPeaks, statusAfter: await text('#status'), askLabelAfter: await text(ASK) });
  report.lastTurn = turn;
  await wait(8000);   // catch-up + resume
}

// ---- 3. Barge-in: press Ask while the answer plays
if (ONLY.has('barge')) {
  if (await page.locator('#ask-menu').isVisible()) { await page.keyboard.press('Escape'); await wait(6000); }
  await page.tap(ASK);
  const liveBtn = page.locator('#ask-live');
  if (await liveBtn.isVisible().catch(() => false)) await liveBtn.tap();
  const tAsk = await now();
  // wait for the answer audio to be playing on the live-voice context (index 1: lane A's second unlock)
  let tLoud = null;
  for (let k = 0; k < 300 && tLoud === null; k++) {
    await wait(100);
    tLoud = await page.evaluate(([t0]) => {
      for (const [i, xs] of window.__rms.entries()) {
        if (i !== 1) continue;                          // 0 commentary, 1 live voice, 2 stage (creation order)
        const hit = xs.find(([t, v]) => t > t0 && v > 0.01);
        if (hit) return [i, hit[0]];
      }
      return null;
    }, [tAsk + 3000]);
  }
  if (!tLoud) step('barge-in: Ask stops the answer', false, { reason: 'no answer audio within 30 s', events: (await live()).events });
  else {
    await wait(1200);                                   // let the answer run a little
    const labelDuring = await text(ASK);
    const tPress = await now();
    await page.tap(ASK);
    await wait(1500);
    const tq = await quietAt(tLoud[0], tPress, 0.002, 300);
    const menuOpen = await page.locator('#ask-menu').isVisible();
    const focused = await page.evaluate(() => document.activeElement?.textContent?.trim() ?? document.activeElement?.id);
    await shot('04-barge-in');
    step('barge-in: Ask stops the answer', tq !== null && tq - tPress < 400 && /stop/i.test(labelDuring ?? ''), {
      answerContext: tLoud[0], labelDuringAnswer: labelDuring, stopLatencyMs: tq === null ? null : Math.round(tq - tPress),
      menuOpenAfter: menuOpen, focusAfter: focused, events: (await live()).events.slice(-6) });
  }
  // Back to the action: Escape closes the held menu -> catch-up -> resume.
  await page.keyboard.press('Escape');
  await waitAskIdle(30_000).catch(() => {});
  await wait(6000);
}

// ---- 4. Pause / resume
if (ONLY.has('pause')) {
  const startBtn = '#start';
  await page.tap(startBtn);
  await page.waitForFunction(() => document.querySelector('[data-sb="state"]')?.textContent === 'Paused', null, { timeout: 10_000 });
  const tP = await now();
  const c0 = await text('[data-sb="clock"]');
  await wait(5000);
  const c1 = await text('[data-sb="clock"]');
  const ctxPaused = await page.evaluate(() => window.__ctxState());
  const n = await liveCtx();
  const pausedPeaks = [];
  for (let i = 0; i < n; i++) pausedPeaks.push(+(await peak(i, tP + 500)).toFixed(4));
  await shot('05-paused');
  await page.tap(startBtn);
  await page.waitForFunction(() => document.querySelector('[data-sb="state"]')?.textContent === 'Playing', null, { timeout: 10_000 });
  const tR = await now();
  await wait(8000);
  const c2 = await text('[data-sb="clock"]');
  const resumedPeaks = [];
  for (let i = 0; i < n; i++) resumedPeaks.push(+(await peak(i, tR)).toFixed(4));
  step('pause/resume: clock and sound stop, then carry on', c0 === c1 && c2 !== c1 && pausedPeaks.every((p) => p < 0.002)
    && resumedPeaks.some((p) => p > 0.005), {
    clockAtPause: c0, clockAfter5sPaused: c1, clockAfter8sResumed: c2, ctxStateWhilePaused: ctxPaused,
    peakRmsWhilePaused: pausedPeaks, peakRmsAfterResume: resumedPeaks, status: await text('#status') });
}

report.consoleErrors = logs.filter((l) => /error|warn/i.test(l)).slice(0, 30);
writeFileSync(`${OUT}/report.json`, JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
await browser.close();
