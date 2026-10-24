// OWNER: B (Nikolay). Stage 8 items 1-3 (B6): sound radar, "Learn the sounds" tour, Bluetooth calibration.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { captionAt, parseVtt, radarModel, toCanvas } from '../../src/radar/radar';
import { STEPS, Tour, type LearnStage } from '../../src/learn/learn';
import { BEAT_S, BEATS, Calibration, estimateOffsetMs, MAX_OFFSET_MS } from '../../src/haptics/calibrate';
import type { SegmentsDoc } from '../../src/replay/replay-source';

const J = new URL('../../public/replay/v1/judge/', import.meta.url);
const doc = JSON.parse(readFileSync(new URL('segments.json', J), 'utf8')) as SegmentsDoc;

describe('sound radar', () => {
  it('shows only what is known at the playhead (ball, crowd, tension history)', () => {
    let seed = 7;
    const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 2 ** 32; };
    for (let i = 0; i < 100; i++) {
      const t = doc.t0 + rnd() * (doc.t1 - doc.t0);
      const m = radarModel(doc, t);
      const seconds = doc.segments.flatMap((s) => s.seconds).filter((x) => x.t <= Math.floor(t));
      expect(m.history).toEqual(seconds.filter((x) => x.t > t - 60).map((x) => x.tension));
      expect(m.tension).toBe(seconds[seconds.length - 1]!.tension);
      const seg = doc.segments.find((s) => s.t0 <= t && t < s.t1)!;
      expect(m.ball!.x).toBe(seg.ball[Math.floor((t - seg.t0) * doc.ball_hz)]![0]);   // the row at t, not ahead
    }
  });

  it('maps the pitch like the main-stand view: Reds goal left, Navy goal right, near touchline at the bottom', () => {
    const [lx] = toCanvas(-52.5, 0, 400, 250, 20), [rx] = toCanvas(52.5, 0, 400, 250, 20);
    const [, nearY] = toCanvas(0, -34, 400, 250, 20), [, farY] = toCanvas(0, 34, 400, 250, 20);
    expect([lx, rx]).toEqual([20, 380]);
    expect(nearY).toBeGreaterThan(farY);
  });

  it("reads A's captions_sdh.vtt and finds the caption at a playhead", () => {
    const cues = parseVtt(readFileSync(new URL('captions_sdh.vtt', J), 'utf8'));
    expect(cues.length).toBeGreaterThan(10);
    const c = cues[1]!;
    expect(captionAt(cues, (c.start + c.end) / 2)).toBe(c.text);
    expect(captionAt(cues, c.start - 0.001)).not.toBe(c.text);
  });
});

describe('learn the sounds', () => {
  const fakeStage = (log: string[]) => {
    let now = 0;
    const stage: LearnStage = {
      ball: () => {}, ballOff: () => { log.push('ballOff'); },
      earcon: (k) => { log.push(`earcon:${k}`); }, crowd: (e) => { log.push(`crowd:${e}`); },
      heartbeat: (x) => { log.push(`heartbeat:${x}`); }, now: () => now,
    };
    return { stage, tick: (s: number) => { now += s; } };
  };

  it('covers the ball, pass/shot/whistle/net icons, the crowd swell and the heartbeat in about 2 minutes', async () => {
    const ids = STEPS.map((s) => s.id);
    for (const need of ['ball', 'pass', 'shot', 'whistle', 'net', 'crowd', 'heartbeat']) expect(ids).toContain(need);
    const log: string[] = [];
    const { stage, tick } = fakeStage(log);
    let total = 0;
    const tour = new Tour({ stage, speak: async (t) => { total += t.split(' ').length / 2.6; tick(1); },   // ~2.6 words/s
      wait: async (ms) => { total += ms / 1000; tick(ms / 1000); } });
    expect(await tour.run()).toEqual(ids);
    expect(total).toBeGreaterThan(60);
    expect(total).toBeLessThan(150);                       // "a skippable 2-minute intro"
    expect(log).toContain('earcon:whistle');
  });

  it('says what each sound is before playing it, and skip stops it', async () => {
    const order: string[] = [];
    const { stage } = fakeStage(order);
    const tour = new Tour({ stage, speak: async (t) => { order.push(`say:${t.slice(0, 12)}`); if (t.startsWith('A shot')) tour.skip(); },
      wait: async () => {} });
    const played = await tour.run();
    expect(played).not.toContain('shot');                    // skipped right after the "A shot..." sentence
    expect(played.at(-1)).toBe('pass');
    const passSaid = order.findIndex((x) => x.startsWith('say:A pass'));
    expect(order.indexOf('earcon:pass', passSaid)).toBeGreaterThan(passSaid);   // the ball step's kicks come earlier
    const ballSaid = order.findIndex((x) => x.startsWith('say:Like in a'));
    expect(order.indexOf('earcon:pass')).toBeGreaterThan(ballSaid);             // and those are after its sentence
  });
});

describe('bluetooth calibration', () => {
  const beats = Array.from({ length: BEATS }, (_, i) => 1000 + i * BEAT_S * 1000);

  it('finds the headphone delay from taps, ignoring a stray tap', () => {
    const jitter = [12, -20, 8, 30, -5, 0, 15, -10];
    const taps = beats.map((b, i) => b + 180 + (jitter[i] as number));     // 180 ms earbuds (file 37: 126-274 ms)
    taps.push(1000 + 3.5 * BEAT_S * 1000);                                   // a stray tap between beats
    expect(Math.abs(estimateOffsetMs(beats, taps)! - 180)).toBeLessThanOrEqual(15);
  });

  it('copes with slow earbuds and slightly early taps, needs 5 taps, and clamps', () => {
    expect(estimateOffsetMs(beats, beats.map((b) => b + 274))).toBe(274);   // slowest AirPods figure in file 37
    expect(estimateOffsetMs(beats, beats.map((b) => b - 40))).toBe(0);      // tapping ahead of the beat: clamp to 0
    expect(estimateOffsetMs(beats, beats.slice(0, 4).map((b) => b + 150))).toBeNull();
    expect(estimateOffsetMs(beats, beats.map((b) => b + 600))).toBe(MAX_OFFSET_MS); // capped at 500 ms
  });

  it('plays 8 clicks on the audio clock and estimates from real tap times', async () => {
    const clicks: number[] = [];
    let perf = 5000;
    const cal = new Calibration({ click: (at) => { clicks.push(at); }, ctxNow: () => 2, toPerf: (t) => 5000 + (t - 2) * 1000,
      perfNow: () => perf, wait: async () => {} });
    await cal.play();
    expect(clicks).toHaveLength(BEATS);
    for (const c of clicks) { perf = 5000 + (c - 2) * 1000 + 200; cal.tap(); }
    expect(cal.finish()).toBe(200);
  });
});
