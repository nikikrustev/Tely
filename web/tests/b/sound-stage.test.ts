// OWNER: B (Nikolay). Stage 2 tests (BUILD_PLAN): ball -> panner mapping, excitement -> bus gain is monotonic,
// the refractory limit, the CrowdBus duck contract, and the scheduler over the real judge cut.
import { readFileSync } from 'node:fs';
import { gunzipSync } from 'node:zlib';
import { describe, expect, it } from 'vitest';
import { AudioStands, EARCON_GAP_S, SEATS, toWorld } from '../../src/audio/audio-stands';
import { CrowdEngine, levelFor, REFRACTORY_S, type CrowdBuffers } from '../../src/audio/crowd-engine';
import { ReplaySource, type SegmentsDoc } from '../../src/replay/replay-source';
import { wire } from '../../src/wire';
import { asCtx, FakeAudioContext, paramOf } from './fake-audio';

const JUDGE = new URL('../../public/replay/v1/judge/', import.meta.url);
const read = (f: string) => readFileSync(new URL(f, JUDGE), 'utf8');

function engine(fake = new FakeAudioContext(), shots: Record<string, number> = { roar: 2, ooh_groan: 2 }) {
  const ctx = asCtx(fake);
  const buf = (s: number) => ctx.createBuffer(2, Math.floor(ctx.sampleRate * s), ctx.sampleRate);
  const buffers: CrowdBuffers = {
    beds: { murmur: buf(2), swell: buf(2), tense: buf(2), away: buf(2) },
    shots: Object.fromEntries(Object.entries(shots).map(([k, n]) => [k, Array.from({ length: n }, () => buf(1))])),
  };
  return { fake, ctx, crowd: new CrowdEngine(ctx, ctx.destination, buffers) };
}

describe('ball -> panner position', () => {
  it('maps pitch x/y/z to Web Audio X/Y/Z (X = x, Y = z, Z = -y)', () => {
    expect(toWorld(30, -20, 1.5)).toEqual([30, 1.5, 20]);
    expect(toWorld(-52.5, 34)).toEqual([-52.5, 0, -34]);
  });

  it('puts the ball on the panner, so the home goal is to the left and the near touchline closest', () => {
    const fake = new FakeAudioContext();
    const stands = new AudioStands(asCtx(fake));
    stands.ballAt({ x: -40, y: -30, z: 0.11, speed: 10, alive: true }, 0, 0.01);
    fake.currentTime = 1;
    const p = stands.ballPanner;
    expect(paramOf(p.positionX).value).toBeCloseTo(-40, 3);
    expect(paramOf(p.positionZ).value).toBeCloseTo(30, 3);
    const seat = SEATS.halfway.pos;                         // listener faces -Z: smaller world X = further left
    expect(paramOf(p.positionX).value).toBeLessThan(seat[0]);
  });

  it('keeps earcons at least 300 ms apart', () => {
    const fake = new FakeAudioContext();
    const stands = new AudioStands(asCtx(fake));
    const a = stands.earcon('shot', 0, 0, 1), b = stands.earcon('whistle', 0, 0, 1.05);
    expect(a).toBe(1);
    expect((b ?? 0) - (a ?? 0)).toBeGreaterThanOrEqual(EARCON_GAP_S - 1e-9);
  });
});

describe('crowd engine', () => {
  it('bus gain rises strictly with excitement', () => {
    const xs = Array.from({ length: 21 }, (_, i) => i / 20);
    for (let i = 1; i < xs.length; i++) expect(levelFor(xs[i] as number)).toBeGreaterThan(levelFor(xs[i - 1] as number));
    const { fake, crowd } = engine();
    crowd.setState({ excitement: 0.1, valence: 0, danger: 0 }, 0);
    fake.currentTime = 10;
    const low = crowd.level.gain.value;
    crowd.setState({ excitement: 0.9, valence: 0, danger: 0 }, 10);
    fake.currentTime = 20;
    expect(crowd.level.gain.value).toBeGreaterThan(low);
  });

  it('the refractory limit blocks a repeated one-shot', () => {
    const { fake, crowd } = engine();
    expect(crowd.trigger('roar', 1)).toBe(true);
    expect(crowd.trigger('roar', 1 + 1)).toBe(false);                       // 1 s later: blocked
    expect(crowd.trigger('roar', 1 + (REFRACTORY_S.roar ?? 4) + 0.1)).toBe(true);
    expect(fake.started).toBe(2);
    expect(crowd.trigger('ooh_groan', 30, false)).toBe(true);               // the other end has its own limit
  });

  it('implements CrowdBus.duck(db, rampMs) / unduck(rampMs) with smooth ramps', () => {
    const { fake, crowd } = engine();
    fake.currentTime = 5;
    crowd.duck(-12, 300);
    fake.currentTime = 5.3;                                                 // 3 time constants: ~95% of the way
    const duckStage = (crowd as unknown as { duckGain: GainNode }).duckGain;
    expect(paramOf(duckStage.gain).value).toBeLessThan(0.3);
    expect(paramOf(duckStage.gain).value).toBeGreaterThan(Math.pow(10, -12 / 20) - 0.01);
    crowd.unduck(600);
    fake.currentTime = 6;
    expect(paramOf(duckStage.gain).value).toBeGreaterThan(0.9);
  });
});

describe('scheduler over the real judge cut', () => {
  it('by 1 s after every shot, the crowd bus gain is above its level 8 s before the shot', () => {
    const doc = JSON.parse(read('segments.json')) as SegmentsDoc;
    const signals = JSON.parse(read('signals.json')) as { events: Record<string, { t: number }> };
    const shots = read('events.jsonl').trim().split('\n').map((l: string) => JSON.parse(l).event)
      .filter((e: { type: string }) => e.type === 'shot').map((e: { id: string }) => signals.events[e.id]?.t as number);
    expect(shots.length).toBeGreaterThanOrEqual(4);
    const { fake, crowd } = engine(new FakeAudioContext(), { roar: 1, ooh_groan: 1, relief_applause: 1, cheer: 1, whistles_jeer: 1 });
    const src = new ReplaySource(fake, doc, Infinity);                      // release everything at once
    src.play(0);
    expect(wire(src, null, crowd, 'H').pump()).toBe(doc.segments.length);
    const gainAt = (t: number) => paramOf(crowd.level.gain).valueAt(src.toCtx(t));
    for (const t of shots) {
      if (t - 8 < doc.t0) continue;
      expect(gainAt(t + 1), `shot at ${t}`).toBeGreaterThan(gainAt(t - 8));
    }
  });

  it('segments carry no cues and cover the cut', () => {
    const doc = JSON.parse(read('segments.json')) as SegmentsDoc & { segments: Record<string, unknown>[] };
    expect(doc.segments.every((s) => !('cues' in s))).toBe(true);
    expect(doc.segments[0]?.t0).toBe(doc.t0);
    expect(doc.segments.at(-1)?.t1).toBe(doc.t1);
    const ticks = JSON.parse(gunzipSync(readFileSync(new URL('ticks.json.gz', JUDGE))).toString('utf8'));
    expect(doc.t1 - doc.t0).toBe(ticks.duration_s);
  });
});
