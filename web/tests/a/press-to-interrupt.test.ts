// OWNER: A (potencialbg). Press-to-interrupt (file 49): pressing Ask during an answer stops it at once, locally, and
// keeps the commentary paused for the next question; Escape stops it and goes back to the action; closing the menu
// after a stop catches up and resumes.
import { readFileSync } from 'node:fs';
import { gunzipSync } from 'node:zlib';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AskController, FragmentPlayer, speakFallback, stopFallback, STOP_FADE_S, type AskDeps } from '../../src/ask/ask';
import { LocalTools, type QaBundle } from '../../src/ask/local-tools';
import type { LiveAskHandler } from '../../src/contracts/b-exports';

const J = new URL('../../public/replay/v1/judge/', import.meta.url);
const read = (f: string) => readFileSync(new URL(f, J), 'utf8');
const T = new LocalTools({
  meta: JSON.parse(read('meta.json')),
  events: read('events.jsonl').trim().split('\n').map((l: string) => JSON.parse(l).event),
  signals: JSON.parse(read('signals.json')),
  ticks: JSON.parse(gunzipSync(readFileSync(new URL('ticks.json.gz', J))).toString('utf8')),
} as QaBundle);
const QUIET = 900;                                     // a playhead with no chance due (no "hold that thought")

afterEach(() => { vi.unstubAllGlobals(); });

/** An answer that only ends when stopped (or after `ms` of fake time), like a long clip. */
function rig(opts: { now?: number; hold?: boolean } = {}) {
  const log: string[] = [];
  let now = opts.now ?? QUIET;
  let release: (() => void) | null = null;
  const tools = Object.create(T) as LocalTools;
  if (opts.hold !== undefined) tools.hold_that_thought = () => opts.hold as boolean;
  const d: AskDeps = {
    tools, clock: { now: () => now },
    crowd: { duck: () => { log.push('duck'); }, unduck: () => { log.push('unduck'); } },
    commentary: { pause: () => { log.push('pause'); }, resume: () => { log.push('resume'); }, nextCueWithin: () => false },
    speak: (_f, text) => {
      log.push(`say: ${text}`);
      return new Promise<void>((r) => { release = () => { now += 2; r(); }; });
    },
    stop: () => { log.push('stop'); release?.(); },
    wait: () => new Promise<void>(() => {}),           // a hold that never ends on its own
  };
  const ctl = new AskController(d);
  const finishSpeaking = async () => { await Promise.resolve(); release?.(); await new Promise((r) => setTimeout(r, 0)); };
  return { ctl, log, finishSpeaking, setNow: (t: number) => { now = t; } };
}

const tick = () => new Promise((r) => setTimeout(r, 0));

describe('press-to-interrupt', () => {
  it('nothing to interrupt when no question runs', () => {
    const { ctl } = rig();
    expect(ctl.interrupt('listen')).toBe(false);
    expect(ctl.isHolding).toBe(false);
  });

  it("'listen': stops the answer at once, no catch-up, the commentary stays paused for the next question", async () => {
    const { ctl, log } = rig({ hold: false });
    const asked = ctl.ask('score');
    await tick();
    expect(ctl.isBusy).toBe(true);
    expect(ctl.interrupt('listen')).toBe(true);
    await asked;
    expect(log.filter((l) => l === 'stop')).toHaveLength(1);
    expect(log.some((l) => l.startsWith('say: Back to the action'))).toBe(false);
    expect(log).not.toContain('resume');
    expect(log).not.toContain('unduck');
    expect(ctl.isHolding).toBe(true);
  });

  it('the next question reuses the pause: no second pause, catch-up from the first pause, one resume', async () => {
    const { ctl, log, finishSpeaking, setNow } = rig({ hold: false });
    const calls: [number, number][] = [];
    const tools = (ctl as unknown as { d: AskDeps }).d.tools;
    const real = tools.catch_up.bind(tools);
    tools.catch_up = (s: number, e: number) => { calls.push([s, e]); return real(s, e); };
    const first = ctl.ask('score');
    await tick();
    ctl.interrupt('listen');
    await first;
    setNow(QUIET + 5);
    const second = ctl.ask('ball');
    await finishSpeaking();                             // the ball answer ends
    await finishSpeaking();                             // the catch-up ends
    await second;
    expect(log.filter((l) => l === 'pause')).toHaveLength(1);
    expect(log.filter((l) => l === 'resume')).toHaveLength(1);
    expect(log.filter((l) => l === 'unduck')).toHaveLength(1);
    expect(calls[0]![0]).toBe(QUIET);                   // covers everything since the commentary first stopped
    expect(ctl.isHolding).toBe(false);
  });

  it("'back' (Escape): stops the answer and resumes straight away, with no catch-up talk", async () => {
    const { ctl, log } = rig({ hold: false });
    const asked = ctl.ask('last');
    await tick();
    ctl.interrupt('back');
    await asked;
    expect(log.some((l) => l.startsWith('say: Back to the action'))).toBe(false);
    expect(log.slice(-2)).toEqual(['unduck', 'resume']);
    expect(ctl.isHolding).toBe(false);
  });

  it('release() after a stop: catch-up, then unduck and resume', async () => {
    const { ctl, log, finishSpeaking } = rig({ hold: false });
    const asked = ctl.ask('score');
    await tick();
    ctl.interrupt('listen');
    await asked;
    const back = ctl.release();
    await finishSpeaking();
    const said = await back;
    expect(said[0]).toMatch(/^Back to the action/);
    expect(log.slice(-2)).toEqual(['unduck', 'resume']);
    expect(ctl.isHolding).toBe(false);
  });

  it('a press during "hold that thought" cuts the 8 s wait short', async () => {
    const { ctl, log } = rig({ hold: true });
    const asked = ctl.ask('score');
    await tick();
    ctl.interrupt('back');                              // the wait never ends by itself in this rig
    await asked;
    expect(log.some((l) => l.startsWith('say: What'))).toBe(false);
    expect(log.at(-1)).toBe('resume');
  });

  it('a live answer is cancelled through the live mode', async () => {
    const { ctl } = rig({ hold: false });
    let end: () => void = () => {};
    const live: LiveAskHandler = { ask: () => new Promise<void>((r) => { end = r; }), cancel: vi.fn(() => end()) };
    ctl.registerLiveMode(live);
    const asked = ctl.askLive();
    await tick();
    ctl.interrupt('listen');
    await asked;
    expect(live.cancel).toHaveBeenCalledOnce();
    expect(ctl.isHolding).toBe(true);
  });
});

describe('stopping playback', () => {
  it('FragmentPlayer.stop fades its answer out (no click) and speak() resolves at once', async () => {
    const targets: [number, number, number][] = [], stops: number[] = [];
    const ctx = {
      currentTime: 10,
      createGain: () => ({ connect: () => {}, disconnect: () => {},
        gain: { setTargetAtTime: (v: number, t: number, k: number) => { targets.push([v, t, k]); } } }),
      createBufferSource: () => ({ buffer: null, connect: () => {}, start: () => {}, stop: (t: number) => { stops.push(t); } }),
      decodeAudioData: async () => ({ duration: 30 }),
    } as unknown as BaseAudioContext;
    vi.stubGlobal('fetch', async (u: string) => ({ json: async () => ({ a: 'a.mp3' }), arrayBuffer: async () => new ArrayBuffer(8), url: u }));
    const p = new FragmentPlayer(ctx, {} as AudioNode);
    await p.load();
    let done = false;
    const speaking = p.speak(['a'], 'text').then(() => { done = true; });
    await tick();
    p.stop();
    await speaking;
    expect(done).toBe(true);
    expect(targets).toEqual([[0, 10, STOP_FADE_S / 3]]);
    expect(stops).toEqual([10 + STOP_FADE_S]);
  });

  it('stopFallback ends the browser voice and resolves its promise', async () => {
    const cancel = vi.fn();
    vi.stubGlobal('SpeechSynthesisUtterance', class { lang = ''; onend: unknown = null; onerror: unknown = null; constructor(public text: string) {} });
    vi.stubGlobal('speechSynthesis', { speak: () => {}, cancel });   // never fires onend by itself
    const spoken = speakFallback('a long answer');
    stopFallback();
    await spoken;
    expect(cancel).toHaveBeenCalled();
  });
});
