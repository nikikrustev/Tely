// OWNER: A (potencialbg). Stage 4 "Done when": commentary lines play at t_in ± 50 ms on the audio clock, and the
// crowd is ducked during every line. Runs the real judge-cut cue file through a simulated pair of audio clocks.
import { readFileSync } from 'node:fs';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { DEFAULT_MIX, setMix } from '../../src/audio/mix';
import type { CrowdBus } from '../../src/contracts/b-exports';
import { CommentaryTrackPlayer, DUCK_DB, parseCues, type Cue, type VoiceContext } from '../../src/lane-a/commentary-track';
// SEAM(A->B): B's real ReplaySource is the replay clock lane A follows (contracts/b-exports.ts ReplayClock). Using it,
// not a hand-made fake, means a change in its play()/now() behaviour shows up here as a failing seam test.
import { ReplaySource, type SegmentsDoc } from '../../src/replay/replay-source';

const BUNDLE = new URL('../../public/replay/v1/judge/', import.meta.url);
const CUES = parseCues(readFileSync(new URL('cues.en.radio.jsonl', BUNDLE), 'utf8'));
const MANIFEST = JSON.parse(readFileSync(new URL('manifest.json', BUNDLE), 'utf8')) as {
  t_start: number; t_end: number; ai_voice_notice: string;
};
const TOLERANCE_S = 0.05;
const STEP_S = 0.005;

/** An audio clock that only moves while running, read in render-quantum steps like a real AudioContext. */
class SimClock {
  t: number;
  running = true;
  constructor(start: number, private quantum: number) { this.t = start; }
  get currentTime() { return Math.floor(this.t / this.quantum) * this.quantum; }
}

interface FakeSource {
  buffer: { duration: number } | null;
  onended: (() => void) | null;
  at: number; into: number; started: boolean; stopped: boolean;
}

/** The voice AudioContext: its own clock (different start and quantum from B's), fake decode, recorded starts. */
class FakeVoice {
  readonly sources: FakeSource[] = [];
  readonly clock = new SimClock(0.0037, 512 / 48000);
  destination = {};
  get currentTime() { return this.clock.currentTime; }
  get state() { return this.clock.running ? 'running' : 'suspended'; }
  resume = async () => { this.clock.running = true; };
  suspend = async () => { this.clock.running = false; };
  /** A decoded line at 1 kHz: 60 ms of silence (the real MP3s have 46-72 ms), then speech. */
  decodeAudioData = async (ab: ArrayBuffer) => {
    const duration = new Float64Array(ab)[0] as number, sampleRate = 1000, length = Math.round(duration * sampleRate);
    return { duration, sampleRate, length, getChannelData: () => new Float32Array(length).fill(0.5, 60) };
  };
  /** Nodes record their last setTargetAtTime value (the press-box voice chain, audio/mix.ts VoiceStage). */
  readonly nodes: Record<string, unknown>[] = [];
  private param(v = 0) { return { value: v, setTargetAtTime(x: number) { this.value = x; } }; }
  private node(props: Record<string, unknown>) {
    const n = { connect: <T>(x: T) => x, disconnect() {}, ...props };
    this.nodes.push(n);
    return n;
  }
  createGain() { return this.node({ kind: 'gain', gain: this.param(1) }); }
  createBiquadFilter() { return this.node({ kind: 'biquad', type: 'lowpass', frequency: this.param(350), Q: this.param(1), gain: this.param() }); }
  createPanner() {
    return this.node({ kind: 'panner', panningModel: 'equalpower', distanceModel: 'inverse', rolloffFactor: 1,
      positionX: this.param(), positionY: this.param(), positionZ: this.param() });
  }
  createBufferSource() {
    const s: FakeSource & Record<string, unknown> = {
      buffer: null, onended: null, at: NaN, into: 0, started: false, stopped: false,
      connect: <T>(n: T) => n, disconnect() {},
      start(at: number, into = 0) { s.at = at; s.into = into; s.started = true; },
      stop() { s.stopped = true; },
    };
    this.sources.push(s);
    return s;
  }
  /** Fire onended for lines that have finished. */
  endFinished() {
    for (const s of this.sources) {
      if (s.started && !s.stopped && s.buffer && this.currentTime >= s.at + s.buffer.duration - s.into) {
        s.stopped = true;
        s.onended?.();
      }
    }
  }
}

/** Records duck/unduck against the voice clock, so we can ask "was the crowd ducked at voice time v?". */
class FakeCrowd implements CrowdBus {
  readonly log: { t: number; ducked: boolean; db?: number }[] = [];
  constructor(private now: () => number) {}
  duck(db: number) { this.log.push({ t: this.now(), ducked: true, db }); }
  unduck() { this.log.push({ t: this.now(), ducked: false }); }
  duckedAt(t: number): boolean {
    let d = false;
    for (const e of this.log) if (e.t <= t) d = e.ducked;
    return d;
  }
}

interface Heard { cue: Cue; at: number; end: number; error: number }

function world(cues: Cue[] = CUES, failUrls: string[] = []) {
  const voice = new FakeVoice();
  const b = new SimClock(123.456, 128 / 44100); // B's AudioContext: created earlier, different rate and quantum
  const doc = { t0: MANIFEST.t_start, t1: MANIFEST.t_end, segments: [] } as unknown as SegmentsDoc;
  const src = new ReplaySource(b, doc);
  const crowd = new FakeCrowd(() => voice.currentTime);
  const track = new CommentaryTrackPlayer({
    clock: src,
    crowd,
    fetchAudio: async (url) => {
      if (failUrls.includes(url)) throw new Error('404');
      const cue = cues.find((c) => c.utterance.audio_url === url) as Cue;
      return new Float64Array([cue.utterance.duration_ms / 1000]).buffer;
    },
  });
  const heard: Heard[] = [];
  const startOf = voice.createBufferSource.bind(voice);
  voice.createBufferSource = () => {
    const s = startOf();
    const start = s.start as (at: number, into?: number) => void;
    (s as unknown as { start: typeof start }).start = (at, into = 0) => {
      start(at, into);
      // Which match second is heard at voice time `at`? Map voice -> B's clock (both run at the same rate while
      // playing), then invert ReplaySource.toCtx (slope 1). The line's audio at `into` should be t_in + into.
      const bAt = at + (b.t - voice.clock.t);
      const matchAt = bAt - src.toCtx(0);
      const rec = track.starts.length; // track.starts gets this line right after start() returns
      queueMicrotask(() => {
        const r = track.starts[rec];
        const cue = cues.find((c) => c.cue_id === r?.cue_id) as Cue;
        heard.push({ cue, at, end: at + (s.buffer?.duration ?? 0) - into, error: matchAt - (cue.t_in + into) });
      });
    };
    return s;
  };
  track.load(cues);
  track.attach(voice as unknown as VoiceContext);

  const advance = async (seconds: number) => {
    for (let k = Math.round(seconds / STEP_S); k > 0; k--) {
      if (voice.clock.running) voice.clock.t += STEP_S;
      if (b.running) b.t += STEP_S;
      voice.endFinished();
      await vi.advanceTimersByTimeAsync(STEP_S * 1000);
    }
  };
  /** What B's main.ts does on Start (src.play() with its default 0.3 s head start). */
  const start = async () => { src.play(); await advance(0); };
  return { voice, b, src, crowd, track, heard, advance, start };
}

beforeEach(() => { vi.useFakeTimers(); });
afterEach(() => { vi.useRealTimers(); });

describe('commentary track on the judge cut', () => {
  it('starts every line at t_in ± 50 ms on the audio clock, and ducks the crowd ≥ 12 dB during every line', async () => {
    const w = world();
    await w.start();
    await w.advance(MANIFEST.t_end - MANIFEST.t_start + 2);

    expect(w.heard.map((h) => h.cue.cue_id)).toEqual(CUES.map((c) => c.cue_id)); // all 45, in order, none dropped
    for (const h of w.heard) {
      expect(Math.abs(h.error), `${h.cue.cue_id} at t_in ${h.cue.t_in}: off by ${(h.error * 1000).toFixed(1)} ms`)
        .toBeLessThanOrEqual(TOLERANCE_S);
      for (let t = h.at; t <= h.end; t += 0.05) expect(w.crowd.duckedAt(t), `${h.cue.cue_id} undocked at ${t}`).toBe(true);
    }
    expect(w.crowd.log.filter((e) => e.ducked).every((e) => (e.db as number) <= -12)).toBe(true);
    expect(DUCK_DB).toBeLessThanOrEqual(-12);
    expect(w.crowd.duckedAt(Infinity)).toBe(false); // the crowd comes back after the last line
  }, 60_000);

  it('ducks ahead of each scheduled line, so the first syllable is never masked', async () => {
    const w = world();
    await w.start();
    await w.advance(120);
    for (const h of w.heard.slice(1)) {
      const duckedFrom = [...w.crowd.log].reverse().find((e) => e.ducked && e.t <= h.at)?.t as number;
      expect(h.at - duckedFrom, h.cue.cue_id).toBeGreaterThanOrEqual(0.1);
    }
  }, 30_000);

  it('speaks the AI-voice and synthetic-data notice first, at Start', async () => {
    const [first] = CUES;
    expect(first?.kind).toBe('intro');
    expect(first?.t_in).toBe(MANIFEST.t_start);
    expect(first?.text.radio).toMatch(/\bAI\b/);
    expect(first?.text.radio).toMatch(/synthetic/i);
    expect(MANIFEST.ai_voice_notice).toMatch(/AI voices.*synthetic/is);
    const w = world();
    await w.start();
    await w.advance(1);
    expect(w.heard[0]?.cue.cue_id).toBe(first?.cue_id);
    // The playhead holds at t0 until B's replay starts, so the notice is found a few ms late; skipping that much of
    // its leading silence keeps the speech on t_in instead of late.
    expect(w.track.starts[0]?.into).toBeGreaterThan(0);
    expect(w.track.starts[0]?.into).toBeLessThan(0.055);
    expect(Math.abs(w.heard[0]?.error ?? 1)).toBeLessThanOrEqual(0.005);
  });

  it('pause stops the voice and lifts the duck; resume continues the same line, in sync', async () => {
    const w = world();
    const line = CUES.find((c) => c.utterance.duration_ms >= 4000 && c.t_in > MANIFEST.t_start + 1) as Cue;
    await w.start();
    await w.advance(line.t_in - MANIFEST.t_start + 1.5); // 1.5 s into the line
    expect(w.heard.at(-1)?.cue.cue_id).toBe(line.cue_id);

    // B's main.ts: src.pause(); commentary.pause(); ctx.suspend()
    w.src.pause();
    w.track.pause();
    w.b.running = false;
    await w.advance(0.05);
    const startedBefore = w.heard.length;
    expect(w.voice.sources.filter((s) => s.started && !s.stopped)).toEqual([]);
    expect(w.crowd.duckedAt(w.voice.currentTime)).toBe(false);
    await w.advance(5); // paused for 5 s of wall time
    expect(w.heard.length).toBe(startedBefore);

    // B's main.ts: ctx.resume(); src.play(0); commentary.resume()
    w.b.running = true;
    w.src.play(0);
    w.track.resume();
    await w.advance(0.5);
    const resumed = w.heard.at(-1) as Heard;
    expect(resumed.cue.cue_id).toBe(line.cue_id);
    expect(resumed.error).toBeGreaterThan(-TOLERANCE_S);
    expect(Math.abs(resumed.error)).toBeLessThanOrEqual(TOLERANCE_S);
    expect(w.track.starts.at(-1)?.into).toBeGreaterThan(1.0); // mid-line (1.5 s minus B's 0.3 s start delay), not from the top
    expect(w.crowd.duckedAt(w.voice.currentTime)).toBe(true);
  });

  it('skips a line whose MP3 fails to load and keeps the rest on time', async () => {
    const missing = CUES[3] as Cue;
    const w = world(CUES, [missing.utterance.audio_url]);
    await w.start();
    await w.advance(60);
    const ids = w.heard.map((h) => h.cue.cue_id);
    expect(ids).not.toContain(missing.cue_id);
    expect(ids).toEqual(CUES.filter((c) => c.t_in < MANIFEST.t_start + 58 && c !== missing).map((c) => c.cue_id));
    vi.spyOn(console, 'warn').mockImplementation(() => {});
  });

  it('nextCueWithin(s) looks ahead from the playhead', async () => {
    const w = world();
    const second = CUES[1] as Cue;
    expect(w.track.nextCueWithin(0.5)).toBe(true); // the AI notice at the very first second
    await w.start();
    await w.advance(1.5);
    const gap = second.t_in - w.src.now();
    expect(w.track.nextCueWithin(gap - 0.2)).toBe(false);
    expect(w.track.nextCueWithin(gap + 0.2)).toBe(true);
  });

  it('the voice comes from the press box: HRTF behind/above on the centre line, dry, no pitch panning', () => {
    const w = world();
    const panner = w.voice.nodes.find((n) => n.kind === 'panner') as Record<string, { value: number } | string | number>;
    expect(panner.panningModel).toBe('HRTF');
    expect(panner.rolloffFactor).toBe(0);
    const v = (k: string) => (panner[k] as { value: number }).value;
    expect(v('positionX')).toBe(0);                     // never left or right
    expect(v('positionZ')).toBeGreaterThan(1);          // behind (the voice context's listener faces -Z)
    expect(v('positionY')).toBeGreaterThan(0);          // and above
    expect(w.voice.nodes.some((n) => n.kind === 'biquad' && n.type === 'highpass')).toBe(true);
    expect(w.track.voice?.input).toBeDefined();
    setMix({ commentatorPos: 'overhead', commentator: -6 });
    expect(v('positionX')).toBe(0);
    expect(v('positionY')).toBeGreaterThan(1.5);
    expect(v('positionZ')).toBe(0);
    setMix(DEFAULT_MIX);
  });
});

// File 49 §4: after an Ask (the commentary pauses, the playhead keeps running) a line cut off mid-sentence is never
// picked up mid-sentence. It restarts from the top if still fresh, otherwise it is dropped (B's catch-up covers it).
describe('resume after an Ask: restart or drop, never mid-sentence', () => {
  const LINE = CUES.findIndex((c) => c.kind === 'describe' && c.utterance.duration_ms >= 5000);
  const withStale = (ms: Record<number, number>) =>
    CUES.map((c, i) => (i in ms ? { ...c, utterance: { ...c.utterance, stale_ms: ms[i] } } : c));
  /** Play to 1.5 s into `line`, pause the voice only (as Ask does), let the match run on, then resume. */
  async function askOver(cues: Cue[], line: Cue, pauseS: number) {
    const w = world(cues);
    await w.start();
    await w.advance(line.t_in - MANIFEST.t_start + 1.5);
    expect(w.track.starts.at(-1)?.cue_id).toBe(line.cue_id);
    w.track.pause();                     // B's ask.ts: commentary.pause(); the replay clock keeps going
    await w.advance(pauseS);
    const before = w.track.starts.length;
    w.track.resume();
    await w.advance(1);
    return w.track.starts.slice(before);
  }

  it('drops a stale line instead of resuming it mid-sentence', async () => {
    const line = CUES[LINE] as Cue;
    expect((line.utterance.stale_ms ?? 500)).toBeLessThan(3000);   // a normal describe line: fresh for ~1 s
    const after = await askOver(CUES, line, 3);
    expect(after.filter((s) => s.cue_id === line.cue_id)).toEqual([]);
  });

  it('restarts a still-fresh line from the top (only its leading silence skipped)', async () => {
    const cues = withStale({ [LINE]: 20_000 });
    const line = cues[LINE] as Cue;
    const after = await askOver(cues, line, 3);
    const again = after.filter((s) => s.cue_id === line.cue_id);
    expect(again).toHaveLength(1);
    expect(again[0]!.into).toBeLessThanOrEqual(0.07);
  });

  it('when a newer line is already due, only the newer one plays (never two voices at once)', async () => {
    // Cues never overlap, so the older line has ended by the time the newer one is due and reset() retires it.
    const cues = withStale({ [LINE]: 20_000, [LINE + 1]: 20_000 });
    const line = cues[LINE] as Cue, next = cues[LINE + 1] as Cue;
    const pause = next.t_in - (line.t_in + 1.5) + 0.5;            // resume 0.5 s after the next line was due
    const after = await askOver(cues, line, pause);
    expect(after.map((s) => s.cue_id)).toEqual([next.cue_id]);
  });
});

describe('screen-reader mode (D30)', () => {
  it('mutes the voice but still starts each line on time and reports it once, in order', async () => {
    const w = world();
    const said: string[] = [];
    w.track.setVoiceMuted(true);
    w.track.onLine = (c) => said.push(c.cue_id);
    await w.start();
    await w.advance(60);
    const gains = w.voice.nodes.filter((n) => n.kind === 'gain') as { gain: { value: number } }[];
    const mute = gains.find((g) => g.gain.value === 0);
    expect(mute).toBeDefined();                               // the one gain at 0: the voice is silent
    expect(said.length).toBeGreaterThan(3);
    expect(said).toEqual(w.heard.map((h) => h.cue.cue_id).slice(0, said.length));
    w.track.setVoiceMuted(false);
    expect(mute?.gain.value).toBe(1);
  }, 60_000);

  it('never reports a line that was stopped before it was heard', async () => {
    const w = world();
    const said: string[] = [];
    w.track.onLine = (c) => said.push(c.cue_id);
    await w.start();
    await w.advance(1);                                     // the AI notice is scheduled
    w.track.pause();                                        // an Ask, before the next line
    const n = said.length;
    await w.advance(30);
    expect(said.length).toBe(n);
  }, 60_000);
});
