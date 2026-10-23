// OWNER: B (Nikolay). Stage 4 (B4) tests: haptic patterns, settings without storage, "Next big moment".
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { compose, Haptics, heartbeat, MAX_ENTRIES, TACTONS, type HapticsEnv, type Team } from '../../src/haptics/haptics';
import { crowdGainFor, DEFAULTS, loadSettings, sanitize, saveSettings, STORAGE_KEY, type StorageLike } from '../../src/settings';
import { nextChapter } from '../../src/replay/chapters';
import { ReplaySource, type SegmentsDoc } from '../../src/replay/replay-source';
import { CrowdEngine } from '../../src/audio/crowd-engine';
import { scoreLine } from '../../src/main';
import { wire } from '../../src/wire';
import { asCtx, FakeAudioContext } from './fake-audio';

/** A fake browser for Haptics: timers run when we say so. */
function fakeEnv(canVibrate = true) {
  let t = 0, nextId = 1;
  const timers = new Map<number, { at: number; f: () => void }>();
  const sent: (number[] | number)[] = [];
  const env: HapticsEnv = {
    vibrate: canVibrate ? (p) => { sent.push(p); return true; } : null,
    now: () => t,
    setTimeout: (f, ms) => { const id = nextId++; timers.set(id, { at: t + ms, f }); return id; },
    clearTimeout: (id) => { timers.delete(id); },
  };
  const advance = (ms: number) => {
    t += ms;
    for (const [id, x] of [...timers].sort((a, b) => a[1].at - b[1].at)) {
      if (x.at <= t && timers.has(id)) { timers.delete(id); x.f(); }
    }
  };
  return { env, sent, advance, pending: () => timers.size };
}

describe('haptics', () => {
  it('every haptic pattern has at most 10 entries (all tactons, teams, strengths, mine or not)', () => {
    const teams: (Team | null)[] = ['home', 'away', null];
    for (const t of TACTONS) for (const team of teams) for (const s of [0.7, 1, 1.4]) for (const mine of [true, false]) {
      const p = compose(t, team, s, mine);
      expect(p.length, `${t}/${team}/${s}/${mine}`).toBeLessThanOrEqual(MAX_ENTRIES);
      expect(p.length).toBeGreaterThan(0);
      expect(p.every((d) => Number.isInteger(d) && d > 0)).toBe(true);
    }
    for (let x = 0; x <= 1; x += 0.1) expect(heartbeat(x).pattern.length).toBeLessThanOrEqual(MAX_ENTRIES);
  });

  it('heartbeat speeds up with tension (55 to 140 bpm)', () => {
    expect(heartbeat(0).bpm).toBeCloseTo(55);
    expect(heartbeat(1).bpm).toBeCloseTo(140);
    expect(heartbeat(0.8).periodMs).toBeLessThan(heartbeat(0.2).periodMs);
  });

  it('fires a tacton 20 ms before its sound, respects "off", and stopAll cancels what is queued', () => {
    const f = fakeEnv();
    const h = new Haptics(f.env, { mode: 'events', strength: 1, myTeam: 'home' });
    h.event('goal', 'home', 500);
    f.advance(479);
    expect(f.sent).toHaveLength(0);
    f.advance(1);
    expect(f.sent).toHaveLength(1);
    h.event('shot', 'away', 1000);
    h.stopAll();
    f.advance(2000);
    expect(f.sent.filter((p) => Array.isArray(p))).toHaveLength(1);
    h.s = { ...h.s, mode: 'off' };
    h.event('goal', 'home', 0);
    f.advance(10);
    expect(f.pending()).toBe(0);
  });

  it('a browser that cannot vibrate (iPhone, Firefox) is reported, and nothing throws', () => {
    const f = fakeEnv(false);
    const h = new Haptics(f.env);
    expect(h.available).toBe(false);
    h.event('goal', 'home', 0);
    h.setTension(0.9);
    h.stopAll();
    expect(f.pending()).toBe(0);
  });
});

describe('settings', () => {
  const throwing: StorageLike = {
    getItem: () => { throw new Error('SecurityError: storage blocked'); },
    setItem: () => { throw new Error('QuotaExceededError'); },
  };

  it('survive a localStorage that throws', () => {
    expect(loadSettings(throwing)).toEqual(DEFAULTS);
    expect(saveSettings({ ...DEFAULTS, club: 'A' }, throwing)).toBe(false);
    expect(loadSettings(null)).toEqual(DEFAULTS);
    expect(saveSettings(DEFAULTS, null)).toBe(false);
  });

  it('round-trip through storage, and bad stored values fall back to defaults', () => {
    const mem = new Map<string, string>();
    const store: StorageLike = { getItem: (k) => mem.get(k) ?? null, setItem: (k, v) => { mem.set(k, v); } };
    const mine = { ...DEFAULTS, club: 'A' as const, crowdMix: 0.2, haptics: 'events' as const, hapticStrength: 1.4, radar: true, audioOffsetMs: 180 };
    expect(saveSettings(mine, store)).toBe(true);
    expect(loadSettings(store)).toEqual(mine);
    mem.set(STORAGE_KEY, '{not json');
    expect(loadSettings(store)).toEqual(DEFAULTS);
    expect(sanitize({ club: 'X', crowdMix: 7, haptics: 'loud', hapticStrength: 'x' })).toEqual({ ...DEFAULTS, crowdMix: 1 });
  });

  it('the crowd slider changes crowd gain smoothly, never above +4 dB', () => {
    for (let m = 0; m < 1; m += 0.05) expect(crowdGainFor(m + 0.05)).toBeGreaterThan(crowdGainFor(m));
    expect(crowdGainFor(0.5)).toBeCloseTo(0.8);
    expect(crowdGainFor(1)).toBeLessThanOrEqual(0.8 * Math.pow(10, 4 / 20) + 1e-9);
  });
});

describe('next big moment', () => {
  const doc = JSON.parse(readFileSync(new URL('../../public/replay/v1/judge/segments.json', import.meta.url), 'utf8')) as SegmentsDoc;
  const chapters = [{ t: 670, label: 'Big moment 1' }, { t: 934, label: 'Big moment 2' }, { t: 1057.2, label: 'Big moment 3' }];

  it('picks the next chapter after the playhead, and none after the last', () => {
    expect(nextChapter(chapters, 670)?.t).toBe(934);
    expect(nextChapter(chapters, 900)?.t).toBe(934);
    expect(nextChapter(chapters, 1060)).toBeNull();
  });

  it('seeking moves the replay clock, tells listeners (A re-anchors), and releases segments from there', () => {
    const fake = new FakeAudioContext();
    const src = new ReplaySource(fake, doc);
    const heard: [number, boolean][] = [];
    src.onChange((p, playing) => heard.push([p, playing]));
    src.play(0);
    fake.currentTime = 5;
    src.due();
    src.seek(934, 0);
    expect(src.now()).toBeCloseTo(934);
    expect(heard.at(-1)).toEqual([934, true]);
    const first = src.due()[0];
    expect(first && first.t0 <= 934 && first.t1 > 934).toBe(true);
  });

  it('after a jump, nothing from before the target is scheduled, and queued one-shots are cancelled', () => {
    const fake = new FakeAudioContext();
    const ctx = asCtx(fake);
    const buf = () => ctx.createBuffer(2, 800, ctx.sampleRate);
    const crowd = new CrowdEngine(ctx, ctx.destination, { beds: {}, shots: { roar: [buf()], ooh_groan: [buf()] } });
    expect(crowd.trigger('roar', 3)).toBe(true);
    crowd.cancelFrom(1);                                    // the roar at 3 s was still queued: dropped
    expect(crowd.trigger('roar', 4)).toBe(true);            // and its refractory window is reset
    const src = new ReplaySource(fake, doc, 3);
    src.play(0);
    src.seek(934, 0);
    const before = fake.started;
    wire(src, null, crowd).pump();
    const triggered = fake.started - before;
    const ahead = doc.segments.flatMap((s) => s.one_shots).filter((o) => o.t >= 934 && o.t <= 937 && o.end === 'H');
    expect(triggered).toBeLessThanOrEqual(ahead.length);
  });

  it('announces the score in plain words', () => {
    expect(scoreLine({ home: 0, away: 1 })).toBe('Reds 0, Navy 1.');
  });
});
