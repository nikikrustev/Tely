// The live-readiness soak (D24): one full-length half (48 min, real time) on a phone-sized
// headless Chromium. Needs the dev server (the soak bundles live in git-ignored web/.local/, built by
// `python -m tely.eval.soak_bundle`) and a relay. Not in CI: it runs for the whole half.
//   node tests/soak.mjs --bundle soak2 --wav question.wav [--relay http://localhost:8080] [--minutes 48]
//        [--ask-every 10] [--offline-at 20] [--pause-at 35] [--out dir]
// Every second it records the playhead, both audio contexts' clocks and wall time; every 100 ms each context's output
// RMS (same probe as phone-e2e.mjs); every 30 s the JS heap and DOM size. At the end it measures:
// - clock drift: playhead against wall time while playing, and the commentary context against the stage context;
// - commentary sync: each cue's first audible output against the wall time its t_in was due;
// - silent gaps: stretches over 1 s with no crowd output while the match plays;
// - memory growth, live Ask results (incl. the relay's 90 s idle close between questions), offline recovery.
import { chromium } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const arg = (k, d) => { const i = process.argv.indexOf(`--${k}`); return i > 0 ? process.argv[i + 1] : d; };
const URL_BASE = arg('url', 'http://localhost:5173');
const BUNDLE = arg('bundle', 'soak2');
const RELAY = arg('relay', 'http://localhost:8080');
const WAV = arg('wav');
const MINUTES = Number(arg('minutes', '49'));
const ASK_EVERY = Number(arg('ask-every', '10'));
const OFFLINE_AT = Number(arg('offline-at', '20'));
const PAUSE_AT = Number(arg('pause-at', '35'));
const OUT = resolve(arg('out', `test-results/soak-${BUNDLE}`));
mkdirSync(OUT, { recursive: true });

const PROBE = () => {
  const ctxs = [];
  window.__rms = [];
  window.__ctxs = ctxs;
  const Orig = window.AudioContext;
  window.AudioContext = class extends Orig {
    constructor(...a) { super(...a); this.__id = ctxs.length; ctxs.push(this); window.__rms.push([]); }
  };
  const taps = new WeakMap();
  const tap = (ctx) => {
    let an = taps.get(ctx);
    if (!an) {
      an = ctx.createAnalyser();
      an.fftSize = 1024;
      taps.set(ctx, an);
      const buf = new Float32Array(an.fftSize);
      setInterval(() => {
        const xs = window.__rms[ctx.__id];
        if (ctx.state !== 'running') { xs.push([performance.now(), -1]); return; }
        an.getFloatTimeDomainData(buf);
        let s = 0; for (const v of buf) s += v * v;
        xs.push([Math.round(performance.now()), +Math.sqrt(s / buf.length).toFixed(5)]);
      }, 100);
    }
    return an;
  };
  const connect = AudioNode.prototype.connect;
  AudioNode.prototype.connect = function (dest, ...rest) {
    if (dest instanceof AudioDestinationNode && this.context.__id !== undefined) connect.call(this, tap(this.context));
    return connect.call(this, dest, ...rest);
  };
  // 1 Hz: wall, playhead, playing, each context's currentTime
  window.__ticks = [];
  setInterval(() => {
    const c = window.telyCommentary?.opts?.clock;
    window.__ticks.push([Math.round(performance.now()), c ? +c.now().toFixed(3) : null, c ? c.isPlaying() : null,
      ...ctxs.map((x) => +x.currentTime.toFixed(4))]);
  }, 1000);
};

const t0Wall = Date.now();
const log = (...a) => console.error(`[${((Date.now() - t0Wall) / 60000).toFixed(1)} min]`, ...a);
const browser = await chromium.launch({
  headless: true,
  args: ['--autoplay-policy=no-user-gesture-required', '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream',
    ...(WAV ? [`--use-file-for-fake-audio-capture=${resolve(WAV)}`] : [])],
});
const context = await browser.newContext({
  viewport: { width: 360, height: 640 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, permissions: ['microphone'],
  userAgent: 'Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36',
});
await context.addInitScript(PROBE);
const page = await context.newPage();
const errors = [];
page.on('console', (m) => { if (['error', 'warning'].includes(m.type())) errors.push([Date.now() - t0Wall, m.type(), m.text().slice(0, 300)]); });
page.on('pageerror', (e) => errors.push([Date.now() - t0Wall, 'pageerror', e.message.slice(0, 300)]));
const cdp = await context.newCDPSession(page);
await cdp.send('Performance.enable');

await page.goto(`${URL_BASE}/?debug=1&bundle=${BUNDLE}&relay=${encodeURIComponent(RELAY)}`);
await page.waitForFunction(() => document.getElementById('status')?.textContent?.startsWith('Ready'));
await page.tap('#start');
await page.waitForFunction(() => document.querySelector('[data-sb="state"]')?.textContent === 'Playing', null, { timeout: 60_000 });
const playStartPerf = await page.evaluate(() => performance.now());
log('playing', BUNDLE);

const mem = [], asks = [], marks = [];
const metric = async () => {
  const m = Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.map((x) => [x.name, x.value]));
  return { t: Date.now() - t0Wall, heapMB: +(m.JSHeapUsedSize / 1e6).toFixed(1), nodes: m.Nodes, listeners: m.JSEventListeners,
    clock: await page.locator('[data-sb="clock"]').innerText(), state: await page.locator('[data-sb="state"]').innerText() };
};
const now = () => page.evaluate(() => performance.now());
const liveState = () => page.evaluate(() => ({ events: window.telyLive?.events?.length ?? 0, turns: window.telyLive?.turns ?? [],
  last: (window.telyLive?.events ?? []).slice(-3) }));

const ask = async (why) => {
  const before = await liveState();
  const tAsk = await now();
  marks.push(['ask', tAsk]);
  if (await page.locator('#ask-menu').isVisible()) await page.keyboard.press('Escape');
  await page.tap('#ask');
  const ok = await page.waitForFunction(([n, k]) => (window.telyLive?.events ?? []).slice(n)
    .some(([, e]) => e.startsWith('refusal')) || (window.telyLive?.turns?.length ?? 0) > k,
  [before.events, before.turns.length], { timeout: 40_000 }).then(() => true).catch(() => false);
  await page.waitForFunction(() => document.getElementById('ask')?.dataset.state !== 'stop', null, { timeout: 60_000 }).catch(() => {});
  const after = await liveState();
  const turn = after.turns.length > before.turns.length ? after.turns.at(-1) : null;
  const r = { why, atMin: +((Date.now() - t0Wall) / 60000).toFixed(1), answered: !!turn && turn.outcome === 'answered',
    refusal: (await page.evaluate((n) => (window.telyLive?.events ?? []).slice(n).map(([, e]) => e)
      .filter((e) => e.startsWith('refusal')), before.events)).at(-1) ?? null,
    question: turn?.question ?? null, answer: turn?.answer?.slice(0, 160) ?? null, latency_ms: turn?.latency_ms ?? null,
    usage: turn?.usage ?? null, waitedMs: Math.round((await now()) - tAsk), settled: ok };
  asks.push(r);
  marks.push(['ask-end', await now() + 12_000]);   // + the catch-up and the crowd's slow unduck
  log('ask', JSON.stringify(r).slice(0, 300));
  if (await page.locator('#ask-menu').isVisible()) await page.keyboard.press('Escape');   // refusal opened the presets
};

const endAt = Date.now() + MINUTES * 60_000;
let nextMem = 0, nextAsk = ASK_EVERY, offlineDone = false, pauseDone = false;
while (Date.now() < endAt) {
  const min = (Date.now() - t0Wall) / 60000;
  if (Date.now() >= nextMem) { mem.push(await metric()); nextMem = Date.now() + 30_000; }
  if (min >= nextAsk) { await ask(`every ${ASK_EVERY} min`); nextAsk += ASK_EVERY; }
  if (!offlineDone && min >= OFFLINE_AT) {
    offlineDone = true;
    marks.push(['offline', await now()]);
    log('network offline for 45 s');
    await context.setOffline(true);
    await page.waitForTimeout(10_000);
    await ask('while offline');
    await page.waitForTimeout(Math.max(0, 45_000 - 10_000));
    await context.setOffline(false);
    marks.push(['online', await now()]);
    log('network back');
    await page.waitForTimeout(15_000);
    await ask('after the network came back');
  }
  if (!pauseDone && min >= PAUSE_AT) {
    pauseDone = true;
    await page.tap('#start');
    marks.push(['pause', await now()]);
    log('paused 60 s');
    await page.waitForTimeout(60_000);
    await page.tap('#start');
    marks.push(['resume', await now()]);
  }
  const state = await page.locator('[data-sb="state"]').innerText();
  if (min > 5 && state !== 'Playing' && state !== 'Paused') { log('state', state); }
  if (await page.evaluate(() => !window.telyCommentary?.opts?.clock?.isPlaying()) && pauseDone && min > PAUSE_AT + 2) {
    log('replay finished');
    break;
  }
  await page.waitForTimeout(5_000);
}
mem.push(await metric());

// ---------------------------------------------------------------- analysis
const data = await page.evaluate(() => ({ ticks: window.__ticks, rms: window.__rms, playout: window.__ctxs.map((c) => {
  const s = c.playoutStats; return s ? { fallbackFramesEvents: s.fallbackFramesEvents, fallbackDuration: s.fallbackDuration,
    totalDuration: s.totalDuration, averageLatency: s.averageLatency } : null; }) }));
writeFileSync(`${OUT}/raw.json`, JSON.stringify({ data, mem, asks, marks, errors }));
const cues = (await (await fetch(`${URL_BASE}/replay/v1/local/${BUNDLE}/cues.en.radio.jsonl`)).text())
  .split('\n').filter(Boolean).map((l) => JSON.parse(l));
const [COMM, STAGE] = [0, 2];   // creation order: lane A's commentary, lane A's live voice, B's stage
const playing = data.ticks.filter((t) => t[2] && t[1] !== null);
// Playhead vs wall: over each uninterrupted playing stretch, playhead advance / wall advance.
const stretches = [];
let cur = [];
for (const t of data.ticks) {
  if (t[2] && t[1] !== null && (!cur.length || Math.abs((t[1] - cur.at(-1)[1]) - (t[0] - cur.at(-1)[0]) / 1000) < 0.5)) cur.push(t);
  else { if (cur.length > 60) stretches.push(cur); cur = t[2] ? [t] : []; }
}
if (cur.length > 60) stretches.push(cur);
const driftRows = stretches.map((s) => {
  const a = s[0], b = s.at(-1);
  const wall = (b[0] - a[0]) / 1000, ph = b[1] - a[1];
  const ctxStage = b[3 + STAGE] - a[3 + STAGE];
  // The commentary context is suspended during every Ask, so its own clock is not compared here; the cue onset lags
  // below are the commentary's drift measure.
  return { fromPlayhead: a[1], toPlayhead: b[1], wallS: +wall.toFixed(1), playheadMinusWallMs: Math.round((ph - wall) * 1000),
    stageCtxMinusWallMs: Math.round((ctxStage - wall) * 1000) };
});
// Map a playhead time to the wall (perf ms) when it was due, from the 1 Hz ticks.
const wallAt = (p) => {
  for (let i = 1; i < playing.length; i++) {
    const a = playing[i - 1], b = playing[i];
    if (a[1] <= p && p <= b[1] && b[1] - a[1] < 2) return a[0] + (p - a[1]) / Math.max(1e-6, b[1] - a[1]) * (b[0] - a[0]);
  }
  return null;
};
const commRms = data.rms[COMM] ?? [];
const onset = (from, to, thr = 0.003) => commRms.find(([t, v]) => t >= from && t <= to && v > thr)?.[0] ?? null;
const sync = [];
for (const c of cues) {
  const due = wallAt(c.t_in);
  if (due === null) continue;
  const prevEnd = sync.at(-1)?.endDue ?? -Infinity;
  if (due - prevEnd < 1500) { sync.push({ t_in: c.t_in, endDue: due + (c.utterance?.duration_ms ?? 2000), skipped: 'overlaps previous' }); continue; }
  const o = onset(due - 1500, due + 4000);
  sync.push({ t_in: c.t_in, kind: c.kind, endDue: due + (c.utterance?.duration_ms ?? 2000), lagMs: o === null ? null : Math.round(o - due) });
}
const lags = sync.filter((s) => typeof s.lagMs === 'number').map((s) => s.lagMs);
const third = Math.floor(lags.length / 3);
const med = (xs) => { const s = [...xs].sort((a, b) => a - b); return s.length ? s[Math.floor(s.length / 2)] : null; };
// Silent gaps in the crowd (stage) while playing, outside the pause and offline marks.
// Windows where quiet is expected: the pause, the offline minute, and every Ask (the crowd is ducked 12 dB).
const quiet = [];
for (const [a, b] of [['pause', 'resume'], ['offline', 'online'], ['ask', 'ask-end']]) {
  const as = marks.filter(([k]) => k === a).map(([, t]) => t), bs = marks.filter(([k]) => k === b).map(([, t]) => t);
  as.forEach((t, i) => quiet.push([t - 500, (bs[i] ?? t) + 1500]));
}
const gaps = [];
let gapStart = null;
for (const [t, v] of data.rms[STAGE] ?? []) {
  if (t < playStartPerf + 15_000 || quiet.some(([a, b]) => t > a && t < b)) { gapStart = null; continue; }
  // A dropout is real silence (under -94 dBFS). The quiet murmur at low tension sits around -68 dBFS (26 Oct soak),
  // which is the D20 mix, not a glitch.
  if (v >= 0 && v < 0.00002) { gapStart ??= t; }
  else { if (gapStart !== null && t - gapStart > 1000) gaps.push({ atPerfMs: Math.round(gapStart), ms: Math.round(t - gapStart) }); gapStart = null; }
}
const report = {
  bundle: BUNDLE, when: new Date(t0Wall).toISOString(), minutes: +((Date.now() - t0Wall) / 60000).toFixed(1),
  playheadRange: [playing[0]?.[1], playing.at(-1)?.[1]],
  drift: driftRows,
  commentarySync: { cuesChecked: lags.length, cuesNotHeard: sync.filter((s) => s.lagMs === null).length,
    medianLagMs: med(lags), firstThirdMedianMs: med(lags.slice(0, third)), lastThirdMedianMs: med(lags.slice(-third)),
    p90AbsLagMs: (() => { const a = lags.map(Math.abs).sort((x, y) => x - y); return a.length ? a[Math.floor(a.length * 0.9)] : null; })(),
    maxLagMs: lags.length ? Math.max(...lags) : null, minLagMs: lags.length ? Math.min(...lags) : null },
  crowdDropoutsOver1s: gaps, playoutStats: data.playout,
  memory: { first: mem[0], last: mem.at(-1), maxHeapMB: Math.max(...mem.map((m) => m.heapMB)) },
  asks, marks: marks.map(([k, t]) => [k, Math.round(t)]), consoleErrors: errors.slice(0, 40), consoleErrorCount: errors.length,
};
writeFileSync(`${OUT}/report.json`, JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
await browser.close();
