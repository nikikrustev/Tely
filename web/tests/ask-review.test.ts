// Regression tests for A's review of PR #15 (hold vs build-up line, catch-up from the pause,
// speech fallback timeout, late live-mode registration, score evidence timing).
import { readFileSync } from 'node:fs';
import { gunzipSync } from 'node:zlib';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AskController, LazyAsk, speakFallback } from '../src/ask/ask';
import { LocalTools, type QaBundle } from '../src/ask/local-tools';

const J = new URL('../public/replay/v1/judge/', import.meta.url);
const read = (f: string) => readFileSync(new URL(f, J), 'utf8');
const T = new LocalTools({
  meta: JSON.parse(read('meta.json')),
  events: read('events.jsonl').trim().split('\n').map((l: string) => JSON.parse(l).event),
  signals: JSON.parse(read('signals.json')),
  ticks: JSON.parse(gunzipSync(readFileSync(new URL('ticks.json.gz', J))).toString('utf8')),
} as QaBundle);
const chanceAt = () => T.b.events.map((e) => T.sig(e.id)).find((s) => s.xg !== null && s.xg >= 0.08)!.t - 5;

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("A's review fixes", () => {
  it("stays quiet (no 'hold') when A's build-up line starts within 2.5 s, but still waits for the moment", async () => {
    const log: string[] = [];
    let now = chanceAt();
    const ctl = new AskController({
      tools: T, clock: { now: () => now },
      crowd: { duck: () => { log.push('duck'); }, unduck: () => { log.push('unduck'); } },
      commentary: { pause: () => { log.push('pause'); }, resume: () => { log.push('resume'); }, nextCueWithin: (s) => s >= 2.5 },
      speak: async (_f, text) => { log.push(`say: ${text}`); now += 3; },
      wait: async (ms) => { log.push(`wait ${ms}`); now += ms / 1000; },
    });
    await ctl.ask('score');
    expect(log).not.toContain('say: Hold that thought, watch this!');
    expect(log[0]).toBe('wait 8000');
    expect(log.slice(1, 3)).toEqual(['pause', 'duck']);
  });

  it('the catch-up starts from the moment the commentary paused, not from before the hold', async () => {
    const calls: [number, number][] = [];
    const tools = Object.create(T) as LocalTools;
    tools.hold_that_thought = () => true;
    tools.catch_up = (s: number, e: number) => { calls.push([s, e]); return T.catch_up(s, e); };
    let now = 900;
    const ctl = new AskController({
      tools, clock: { now: () => now }, crowd: { duck: () => {}, unduck: () => {} },
      commentary: { pause: () => {}, resume: () => {}, nextCueWithin: () => false },
      speak: async () => { now += 2; }, wait: async (ms) => { now += ms / 1000; },
    });
    await ctl.ask('score');
    expect(calls[0]![0]).toBe(900 + 2 + 8);              // after the hold line (2 s) and the wait (8 s)
  });

  it('the browser voice fallback can never get stuck: a timeout cancels it and resolves', async () => {
    vi.useFakeTimers();
    const cancel = vi.fn();
    vi.stubGlobal('SpeechSynthesisUtterance', class { lang = ''; onend: unknown = null; onerror: unknown = null; constructor(public text: string) {} });
    vi.stubGlobal('speechSynthesis', { speak: () => {}, cancel });   // never fires onend / onerror
    const text = 'Reds nil, Navy one.';
    let resolved = false;
    void speakFallback(text).then(() => { resolved = true; });
    await vi.advanceTimersByTimeAsync(2000 + text.length * 90 - 10);
    expect(resolved).toBe(false);
    await vi.advanceTimersByTimeAsync(20);
    expect(resolved).toBe(true);
    expect(cancel).toHaveBeenCalledTimes(1);
  });

  it('LazyAsk tells the page when A registers the live mode after Start', () => {
    const lazy = new LazyAsk();
    let seen = 0;
    lazy.onRegister = () => { seen++; };
    lazy.registerLiveMode({ ask: async () => {}, cancel: () => {} });
    expect(seen).toBe(1);
  });

  it('the score counts a goal from the moment it is revealed, and lists it (27 Oct review, item 9)', () => {
    const goal = T.b.events.find((e) => e.type === 'shot' && e.outcome_type === 'successful')!;
    const r = T.sig(goal.id).reveal_t;                   // 703.76
    const before = T.get_score_and_clock(r - 0.1);
    expect(before.say).toMatch(/Navy nil/);
    expect(before.evidence_ids).not.toContain(goal.id);
    const just = T.get_score_and_clock(r + 0.1);         // the per-second row still said nil-nil here until 704
    expect(just.say).toMatch(/Navy one/);
    expect(just.evidence_ids).toContain(goal.id);
  });
  it('a NaN playhead is the cut start, and the ball says nothing while a shot is unrevealed (items 11, 12)', () => {
    expect(T.clamp(Number.NaN)).toBe(T.t0);
    expect(T.clamp(Number.POSITIVE_INFINITY)).toBe(T.t0);
    expect(T.get_last_events(800, Number.NaN).say).toBe(T.get_last_events(800, 3).say);
    const shot = T.b.events.find((e) => e.type === 'shot')!;
    const s = T.sig(shot.id);
    const during = T.get_ball_position((s.t + s.reveal_t) / 2);
    expect(during.fragments).toEqual(['hold']);
    expect(during.x).toBeUndefined();
    expect(during.y).toBeUndefined();
  });
});
