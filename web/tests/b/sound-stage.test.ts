// OWNER: B (Nikolay; A since the 24 Oct handover). Stage 2 tests (BUILD_PLAN): no ball loop, kicks panned by ball x,
// the mix levels, the crowd following the ball, the press-box commentator, excitement -> bus gain is monotonic,
// the refractory limit, the CrowdBus duck contract, and the scheduler over the real judge cut.
import { readFileSync } from 'node:fs';
import { gunzipSync } from 'node:zlib';
import { afterEach, describe, expect, it } from 'vitest';
import { AudioStands, EARCON_GAP_S, FIELD_LOWPASS_HZ, SEATS, stereoPan, toWorld } from '../../src/audio/audio-stands';
import { CrowdEngine, FOLLOW_PAN, levelFor, REFRACTORY_S, type CrowdBuffers } from '../../src/audio/crowd-engine';
import { DEFAULT_MIX, parseMix, setMix, VoiceStage } from '../../src/audio/mix';
import { ReplaySource, type SegmentsDoc } from '../../src/replay/replay-source';
import { wire } from '../../src/wire';
import { asCtx, FakeAudioContext, paramOf } from './fake-audio';

const JUDGE = new URL('../../public/replay/v1/judge/', import.meta.url);
const read = (f: string) => readFileSync(new URL(f, JUDGE), 'utf8');

afterEach(() => { setMix(DEFAULT_MIX); });   // the mix is one shared store

function engine(fake = new FakeAudioContext(), shots: Record<string, number> = { roar: 2, ooh_groan: 2 }) {
  const ctx = asCtx(fake);
  const buf = (s: number) => ctx.createBuffer(2, Math.floor(ctx.sampleRate * s), ctx.sampleRate);
  const buffers: CrowdBuffers = {
    beds: { murmur: buf(2), swell: buf(2), tense: buf(2), away: buf(2) },
    shots: Object.fromEntries(Object.entries(shots).map(([k, n]) => [k, Array.from({ length: n }, () => buf(1))])),
  };
  return { fake, ctx, crowd: new CrowdEngine(ctx, ctx.destination, buffers) };
}

/** Records every node of one kind the fake context makes, in order. */
function spy<T>(fake: FakeAudioContext, method: 'createStereoPanner' | 'createPanner' | 'createBiquadFilter'): T[] {
  const made: T[] = [];
  const f = (fake[method] as () => T).bind(fake);
  (fake as unknown as Record<string, () => T>)[method] = () => { const n = f(); made.push(n); return n; };
  return made;
}

describe('the pitch: no ball sound, kicks panned by ball x', () => {
  it('maps pitch x/y/z to Web Audio X/Y/Z (X = x, Y = z, Z = -y)', () => {
    expect(toWorld(30, -20, 1.5)).toEqual([30, 1.5, 20]);
    expect(toWorld(-52.5, 34)).toEqual([-52.5, 0, -34]);
  });

  it('plays no continuous ball sound: nothing starts on its own, and ball samples are silent', () => {
    const fake = new FakeAudioContext();
    const stands = new AudioStands(asCtx(fake));
    expect(fake.started).toBe(0);                                          // no looped noise, no rattle oscillator
    for (let k = 0; k < 50; k++) stands.ballAt({ x: k, y: 0, z: 0.11, speed: 15, alive: true }, k / 25);
    expect(fake.started).toBe(0);
    expect(stands).not.toHaveProperty('ballPanner');
    expect(stands).not.toHaveProperty('ballStereo');
  });

  it('the ping plays where the ball is as heard now, not where it is queued to be', () => {
    const fake = new FakeAudioContext();
    const stands = new AudioStands(asCtx(fake));
    stands.ballAt({ x: -30, y: 0, z: 0.11, speed: 5, alive: true }, 0);
    stands.ballAt({ x: 40, y: 0, z: 0.11, speed: 5, alive: true }, 3);    // queued 3 s ahead
    fake.currentTime = 1;
    expect(stands.last.x).toBe(-30);
    fake.currentTime = 3.5;
    expect(stands.last.x).toBe(40);
    stands.cancelFrom(3.5);
    stands.ballAt({ x: 10, y: 0, z: 0.11, speed: 5, alive: true }, 3.5);
    expect(stands.last.x).toBe(10);
  });

  it('the whistle is soft: peak at most -18 dBFS, and not a pure tone', () => {
    const fake = new FakeAudioContext();
    fake.sampleRate = 22050;
    const stands = new AudioStands(asCtx(fake));
    const buf = (stands as unknown as { icons: Map<string, AudioBuffer> }).icons.get('whistle') as AudioBuffer;
    const d = buf.getChannelData(0);
    const peak = d.reduce((m, v) => Math.max(m, Math.abs(v)), 0);
    expect(peak).toBeLessThanOrEqual(Math.pow(10, -18 / 20));
    expect(peak).toBeGreaterThan(0.02);
  });

  it("pans kicks clearly left/right: Reds' goal (Navy attack it) hard left, halfway centre, Navy's goal hard right", () => {
    expect(stereoPan(-52.5)).toBeLessThanOrEqual(-0.85);
    expect(stereoPan(0)).toBe(0);
    expect(stereoPan(52.5)).toBeGreaterThanOrEqual(0.85);
    for (let x = -52; x < 52; x += 4) expect(stereoPan(x + 4)).toBeGreaterThanOrEqual(stereoPan(x));
    const fake = new FakeAudioContext();
    const stands = new AudioStands(asCtx(fake));
    const pans = spy<StereoPannerNode>(fake, 'createStereoPanner'), hrtf = spy<PannerNode>(fake, 'createPanner');
    stands.earcon('pass', -45, 10, 0);
    stands.earcon('shot', 45, 10, 1);
    expect(paramOf(pans[0]!.pan).value).toBeLessThan(-0.8);
    expect(paramOf(pans[1]!.pan).value).toBeGreaterThan(0.8);
    expect(paramOf(hrtf[0]!.positionX).value).toBe(-45);
  });

  it('passes and shots sit under the crowd: well below 0 dB, low-passed, and set live from the mix', () => {
    expect(DEFAULT_MIX.pass).toBeLessThanOrEqual(-12);
    expect(DEFAULT_MIX.shot).toBeLessThanOrEqual(-6);
    expect(DEFAULT_MIX.pass).toBeLessThan(DEFAULT_MIX.shot);
    const fake = new FakeAudioContext();
    const filters = spy<BiquadFilterNode>(fake, 'createBiquadFilter');
    const stands = new AudioStands(asCtx(fake));
    fake.currentTime = 1;
    const gainOf = (k: 'pass' | 'shot' | 'whistle') => paramOf(stands.kindGain.get(k)!.gain).value;
    expect(gainOf('pass')).toBeCloseTo(Math.pow(10, DEFAULT_MIX.pass / 20), 3);
    expect(gainOf('shot')).toBeCloseTo(Math.pow(10, DEFAULT_MIX.shot / 20), 3);
    expect(gainOf('whistle')).toBeGreaterThan(gainOf('shot'));              // the referee stays clear
    expect(filters.some((f) => f.type === 'lowpass' && paramOf(f.frequency).value === FIELD_LOWPASS_HZ)).toBe(true);
    setMix({ pass: -40 });                                                 // the mixer: heard at once; -40 dB = off
    fake.currentTime = 2;
    expect(gainOf('pass')).toBeLessThan(0.001);
  });

  it('keeps earcons at least 300 ms apart', () => {
    const fake = new FakeAudioContext();
    const stands = new AudioStands(asCtx(fake));
    const a = stands.earcon('shot', 0, 0, 1), b = stands.earcon('whistle', 0, 0, 1.05);
    expect(a).toBe(1);
    expect((b ?? 0) - (a ?? 0)).toBeGreaterThanOrEqual(EARCON_GAP_S - 1e-9);
  });
});

describe('crowd follows the ball (left/right without a ball sound)', () => {
  const endsOf = (c: CrowdEngine) => (c as unknown as { ends: { gain: GainNode; side: number }[] }).ends;

  it('the end nearest the ball lifts and the far end drops; swell and tense pan toward the ball', () => {
    const { fake, crowd } = engine();
    expect(crowd.homePan).toBeLessThan(0);                                 // home end on the left, as before
    crowd.followBall(45, 0);                                               // ball at Navy's goal, on the right
    fake.currentTime = 5;
    const right = endsOf(crowd).filter((e) => e.side > 0), left = endsOf(crowd).filter((e) => e.side < 0);
    expect(right.length).toBeGreaterThan(0);
    expect(left.length).toBeGreaterThan(0);
    for (const e of right) expect(paramOf(e.gain.gain).value).toBeGreaterThan(1.3);   // about +3.5 dB at nearEnd 0.5
    for (const e of left) expect(paramOf(e.gain.gain).value).toBeLessThan(0.75);
    const beds = (crowd as unknown as { beds: Map<string, { pan: StereoPannerNode }> }).beds;
    expect(paramOf(beds.get('swell')!.pan.pan).value).toBeCloseTo(FOLLOW_PAN, 2);
    expect(paramOf(beds.get('murmur')!.pan.pan).value).toBe(crowd.homePan);  // the ends themselves stay put
    crowd.followBall(-45, 5);
    fake.currentTime = 10;
    for (const e of left) expect(paramOf(e.gain.gain).value).toBeGreaterThan(1.3);
  });

  it('nearEnd 0 turns the follow off', () => {
    setMix({ nearEnd: 0 });
    const { fake, crowd } = engine();
    crowd.followBall(45, 0);
    fake.currentTime = 5;
    for (const e of endsOf(crowd)) expect(paramOf(e.gain.gain).value).toBeCloseTo(1, 3);
  });
});

describe('the commentator: press box, behind and above, never left or right', () => {
  it('sits on the centre line behind and above the listener, and moves live', () => {
    const fake = new FakeAudioContext();
    const stands = new AudioStands(asCtx(fake));                            // listener on the halfway seat
    const seat = SEATS.halfway.pos, p = stands.voice.panner;
    const pos = () => { fake.currentTime += 1; return [p.positionX, p.positionY, p.positionZ].map((q) => paramOf(q).value); };
    expect(p.panningModel).toBe('HRTF');
    expect(p.rolloffFactor).toBe(0);                                       // close: no distance loss
    const behind = pos();
    expect(behind[0]).toBeCloseTo(seat[0], 3);                             // no left/right
    expect(behind[2]).toBeGreaterThan(seat[2] + 1);                        // behind (the seat faces -Z)
    expect(behind[1]).toBeGreaterThan(seat[1]);                            // and a little above
    setMix({ commentatorPos: 'overhead' });
    const over = pos();
    expect(over[0]).toBeCloseTo(seat[0], 3);
    expect(over[1]).toBeGreaterThan(seat[1] + 1.5);
    expect(over[2]).toBeCloseTo(seat[2], 3);
  });

  it('the voice chain is dry (no reverb) and has a booth-mic high-pass', () => {
    const fake = new FakeAudioContext();
    const filters = spy<BiquadFilterNode>(fake, 'createBiquadFilter');
    const convolvers: unknown[] = [];
    (fake as unknown as { createConvolver: () => unknown }).createConvolver = () => { const c = {}; convolvers.push(c); return c; };
    new VoiceStage(asCtx(fake), fake.destination as unknown as AudioNode);
    expect(convolvers).toHaveLength(0);
    expect(filters.some((f) => f.type === 'highpass')).toBe(true);
  });

  it('parseMix keeps known keys, clamps them, and accepts the mixer file ({version, mix})', () => {
    const m = parseMix({ version: 1, mix: { pass: -99, shot: 50, nearEnd: 3, commentatorPos: 'overhead', junk: 1 } });
    expect(m.pass).toBe(-40);
    expect(m.shot).toBe(12);
    expect(m.nearEnd).toBe(1);
    expect(m.commentatorPos).toBe('overhead');
    expect(m).not.toHaveProperty('junk');
    expect(parseMix({ commentatorPos: 'pitch' }).commentatorPos).toBe(DEFAULT_MIX.commentatorPos);
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
