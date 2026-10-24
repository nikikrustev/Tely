// OWNER: A (potencialbg). Stage 4: the pre-rendered commentary track, played on the audio clock (file 43 §6).
// It loads cues.en.radio.jsonl itself (segments.json carries no cues, TEAM_SPLIT.md), decodes each line ahead of
// time, starts it at its t_in with AudioBufferSourceNode.start(when), and ducks B's crowd bus around every line.
//
// Two clocks: the contract gives lane A the replay clock (match seconds) but not B's AudioContext, and B creates its
// context inside Start, after mountLaneA() has run. So the voice has its own AudioContext (unlocked in the same tap,
// see index.ts) and maps match time onto it by sampling clock.now() against ctx.currentTime. Both contexts run off
// the same output device, so the offset is constant while playing; we re-measure it after every play/pause/seek.
//
// The voice sits in the press box, behind and above the seat (mix.ts VoiceStage): HRTF straight behind/above (never
// left or right), a booth-mic high-pass and no stadium reverb, so it is clearly apart from the pitch.
import { VoiceStage } from '../audio/mix';
import type { CommentaryTrack } from '../contracts/a-exports';
import type { CrowdBus, ReplayClock } from '../contracts/b-exports';

/** One line of cues.<lang>.<level>.jsonl: the fields the player reads (cue contract, file 43 §3). */
export interface Cue {
  cue_id: string;
  t_in: number;
  kind: string;
  priority?: number;
  text: { radio: string };
  utterance: { audio_url: string; duration_ms: number; stale_ms?: number };
}

/** The subset of AudioContext the track uses, so tests can pass a fake. */
export type VoiceContext = Pick<AudioContext, 'currentTime' | 'state' | 'resume' | 'suspend' | 'decodeAudioData' |
  'createBufferSource' | 'createGain' | 'createBiquadFilter' | 'createPanner' | 'destination'>;

// Mix and timing constants. Duck depth: file 38 (a +12 dB dialogue-to-background ratio rated best) and BUILD_PLAN
// Stage 4 ("at least 12 dB under speech"); B's duck() adds a -6 dB speech-band dip on top.
export const DUCK_DB = -12;
export const DUCK_RAMP_MS = 150; // attack: soft, but fully down before the first syllable
export const DUCK_LEAD_S = 0.25; // start the duck this long before the line
export const UNDUCK_RAMP_MS = 600; // release: slow, so the crowd swells back rather than jumps (file 27 snippet)
export const UNDUCK_HOLD_S = 0.35; // keep ducked this long after the line; lines closer than this share one duck
export const LOOKAHEAD_S = 1.5; // schedule lines this far ahead on the audio clock (sample-accurate start)
export const DECODE_AHEAD_S = 30; // keep decoded PCM only for lines in the next 30 s (memory on phones)
const TICK_MS = 100;
const FAST_TICK_MS = 10; // while measuring the clock offset after play/seek
const OFFSET_SAMPLES = 15;
const DEFAULT_STALE_MS = 500;
/** If the playhead moved more than this while the voice was paused, the pause was an Ask (the match kept going). */
const RESUME_IN_SYNC_S = 0.25;

export interface TrackOptions {
  clock: ReplayClock;
  crowd: CrowdBus;
  /** Fetch one line's MP3 by its bundle-relative audio_url. */
  fetchAudio: (url: string) => Promise<ArrayBuffer>;
}

export interface StartRecord {
  cue_id: string;
  t_in: number;
  /** Audio-clock time passed to start(). */
  at: number;
  /** Seconds into the line it started from (non-zero only when resuming a paused line). */
  into: number;
}

type Status = 'pending' | 'scheduled' | 'done';

export function parseCues(jsonl: string): Cue[] {
  return jsonl.split('\n').filter((s) => s.trim()).map((s) => JSON.parse(s) as Cue)
    .filter((c) => c.utterance?.audio_url)
    .sort((a, b) => a.t_in - b.t_in);
}

/** Seconds before the first sample above -50 dBFS, minus 5 ms of margin. The Brian HD MP3s open with 67-88 ms of
 *  silence (measured in Chrome on all 45 judge-cut MP3s, 22 Oct 2026; Andrew HD was 46-72 ms). */
export function leadingSilence(buf: Pick<AudioBuffer, 'getChannelData' | 'sampleRate' | 'length'>): number {
  if (typeof buf.getChannelData !== 'function') return 0;
  const d = buf.getChannelData(0);
  let i = 0;
  while (i < d.length && Math.abs(d[i] as number) < 0.003) i++;
  return i >= d.length ? 0 : Math.max(0, i / buf.sampleRate - 0.005);
}

const median = (xs: number[]) => {
  const s = [...xs].sort((a, b) => a - b);
  return s[s.length >> 1] as number;
};

export class CommentaryTrackPlayer implements CommentaryTrack {
  readonly starts: StartRecord[] = [];
  private cues: Cue[] = [];
  private status: Status[] = [];
  private sources = new Map<number, AudioBufferSourceNode>();
  private bytes = new Map<string, Promise<ArrayBuffer | null>>();
  private decoded = new Map<string, AudioBuffer>();
  private decoding = new Map<string, Promise<void>>();
  private silence = new WeakMap<AudioBuffer, number>(); // seconds of leading silence we may skip when late
  private ctx: VoiceContext | null = null;
  private out: GainNode | null = null;
  voice: VoiceStage | null = null;
  private paused = false; // pause() from B, independent of the clock
  private playing = false; // what the replay clock last said
  private interrupted = -1; // the line that was speaking when the clock stopped: it resumes mid-line
  private pausedAt = NaN; // playhead at pause()
  private offsets: number[] = []; // samples of clock.now() - ctx.currentTime
  private lastRaw: [number, number] = [NaN, NaN];
  private timer: ReturnType<typeof setTimeout> | null = null;
  private duckTimers = new Set<ReturnType<typeof setTimeout>>();
  private ducks = 0; // lines currently holding the duck (overlapping holds merge into one duck)

  constructor(private opts: TrackOptions) {
    // SEAM(A->B): the replay clock (contracts/b-exports.ts ReplayClock). Every play, pause and seek re-anchors us.
    opts.clock.onChange((p, playing) => this.reset(p, playing));
  }

  /** Give the track its cue list and start fetching every MP3 (a few MB in total, file 43 §6). */
  load(cues: Cue[]): void {
    this.cues = cues;
    this.status = cues.map(() => 'pending');
    for (const c of cues) this.fetch(c.utterance.audio_url);
    this.reset(this.opts.clock.now(), this.opts.clock.isPlaying());
  }

  /** The voice AudioContext, created and resumed in a user gesture (index.ts). Decoding starts now. */
  attach(ctx: VoiceContext): void {
    this.ctx = ctx;
    // SEAM(A->B): mix.ts (B's folder) holds the shared mix, so the ?mix=1 mixer moves this voice live.
    this.voice = new VoiceStage(ctx as unknown as BaseAudioContext, ctx.destination);
    this.out = this.voice.input;
    this.reset(this.opts.clock.now(), this.opts.clock.isPlaying());
  }

  // --- CommentaryTrack (contracts/a-exports.ts) ---

  pause(): void {
    this.paused = true;
    this.pausedAt = this.opts.clock.now();
    this.stopAll(this.opts.clock.now());
    void this.ctx?.suspend().catch(() => {});
  }

  resume(): void {
    if (!this.paused) return;
    this.paused = false;
    const p = this.opts.clock.now();
    // The match moved on while the voice was paused (an Ask: the playhead keeps running). Never pick a line up
    // mid-sentence then (file 49 §4): it goes through the late rule below, so it restarts if still fresh, else it is
    // dropped and B's catch-up covers it. A replay pause keeps the playhead still, so that line resumes in sync.
    if (Math.abs(p - this.pausedAt) > RESUME_IN_SYNC_S) this.interrupted = -1;
    this.reset(p, this.opts.clock.isPlaying());
  }

  nextCueWithin(s: number): boolean {
    const p = this.opts.clock.now();
    return this.cues.some((c) => c.t_in >= p && c.t_in <= p + s);
  }

  // --- internals ---

  private reset(p: number, playing: boolean): void {
    this.playing = playing;
    this.stopAll(p);
    this.offsets = [];
    this.lastRaw = [p, this.ctx?.currentTime ?? NaN];
    this.cues.forEach((c, i) => {
      const end = c.t_in + this.durationOf(i);
      this.status[i] = end <= p && i !== this.interrupted ? 'done' : 'pending';
    });
    if (this.ctx && playing && !this.paused && this.ctx.state !== 'running') void this.ctx.resume().catch(() => {});
    this.kick(FAST_TICK_MS);
  }

  /** Stop every scheduled or speaking line, and drop the duck. Remembers a line cut off mid-sentence. */
  private stopAll(p: number): void {
    for (const [i, src] of this.sources) {
      const c = this.cues[i] as Cue;
      if (c.t_in < p && p < c.t_in + this.durationOf(i)) this.interrupted = i;
      src.onended = null;
      try { src.stop(); } catch { /* never started */ }
      try { src.disconnect(); } catch { /* already gone */ }
      if (this.status[i] === 'scheduled') this.status[i] = 'pending';
    }
    this.sources.clear();
    this.duckTimers.forEach((t) => clearTimeout(t));
    this.duckTimers.clear();
    if (this.ducks > 0) {
      this.ducks = 0;
      // SEAM(A->B): CrowdBus.unduck (contracts/b-exports.ts).
      this.opts.crowd.unduck(UNDUCK_RAMP_MS);
    }
  }

  private kick(ms: number): void {
    if (this.timer !== null) clearTimeout(this.timer);
    this.timer = setTimeout(() => {
      this.timer = null;
      this.tick();
    }, ms);
  }

  private durationOf(i: number): number {
    const c = this.cues[i] as Cue;
    return this.decoded.get(c.utterance.audio_url)?.duration ?? c.utterance.duration_ms / 1000;
  }

  /** Measure clock.now() - ctx.currentTime. Only counts when both clocks have moved since the last read, which skips
   *  B's start-up delay (the playhead holds at t0 until the replay really starts) and a voice context still waking. */
  private sampleOffset(): number | null {
    const ctx = this.ctx as VoiceContext;
    const p = this.opts.clock.now(), t = ctx.currentTime;
    const [p0, t0] = this.lastRaw;
    this.lastRaw = [p, t];
    if (ctx.state === 'running' && this.opts.clock.isPlaying() && p > p0 && t > t0) {
      this.offsets.push(p - t);
      if (this.offsets.length > OFFSET_SAMPLES) this.offsets.shift();
    }
    return this.offsets.length ? median(this.offsets) : null;
  }

  private tick(): void {
    const ctx = this.ctx;
    if (!ctx || !this.playing || this.paused || !this.cues.length) return;
    const offset = this.sampleOffset();
    if (offset === null) return this.kick(FAST_TICK_MS);
    const now = ctx.currentTime, p = now + offset;

    this.cues.forEach((c, i) => {
      if (this.status[i] !== 'pending') return;
      if (c.t_in <= p + DECODE_AHEAD_S) this.decode(c.utterance.audio_url);
      if (c.t_in <= p + LOOKAHEAD_S) this.schedule(i, offset, now);
    });
    this.release(p);
    this.kick(this.offsets.length < 3 ? FAST_TICK_MS : TICK_MS);
  }

  private schedule(i: number, offset: number, now: number): void {
    const ctx = this.ctx as VoiceContext, c = this.cues[i] as Cue;
    const buf = this.decoded.get(c.utterance.audio_url);
    const when = c.t_in - offset; // audio-clock time at which t_in is heard
    const lateS = now - when;
    const staleS = (c.utterance.stale_ms ?? DEFAULT_STALE_MS) / 1000;
    if (!buf) {
      // Not decoded yet: wait while the line is still fresh. The AI notice (kind "intro") is never dropped.
      if (lateS > staleS && c.kind !== 'intro' && i !== this.interrupted) this.status[i] = 'done';
      return;
    }
    let at = when, into = 0;
    if (i === this.interrupted) {
      // Resume mid-sentence, in sync with the match: start at the offset the playhead has reached.
      at = Math.max(when, now);
      into = at - when;
      this.interrupted = -1;
    } else if (lateS > 0) {
      // Late (start-up, where the playhead holds at t0 until B's replay really starts, after a seek, or after an Ask).
      // Skip into the line's leading silence by the lateness, so speech still lands on t_in; past that, say the whole
      // line now if it is still fresh, otherwise drop it.
      if (lateS > staleS && c.kind !== 'intro') {
        this.status[i] = 'done';
        return;
      }
      at = now;
      into = Math.min(lateS, this.silence.get(buf) ?? 0);
    }
    if (into >= buf.duration) {
      this.status[i] = 'done';
      return;
    }
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.connect(this.out as GainNode);
    src.onended = () => {
      if (this.sources.get(i) === src) this.sources.delete(i);
      if (this.status[i] === 'scheduled') this.status[i] = 'done';
    };
    src.start(at, into);
    this.sources.set(i, src);
    this.status[i] = 'scheduled';
    this.starts.push({ cue_id: c.cue_id, t_in: c.t_in, at, into });
    this.duckAround(at, at + buf.duration - into);
  }

  /** Duck the crowd from DUCK_LEAD_S before the line until UNDUCK_HOLD_S after it. Holds are counted, so lines
   *  closer together than the hold share one duck instead of pumping the crowd up and down between them. */
  private duckAround(start: number, end: number): void {
    const ctx = this.ctx as VoiceContext;
    const later = (atS: number, fn: () => void) => {
      const id = setTimeout(() => {
        this.duckTimers.delete(id);
        fn();
      }, Math.max(0, (atS - ctx.currentTime) * 1000));
      this.duckTimers.add(id);
    };
    later(start - DUCK_LEAD_S, () => {
      // SEAM(A->B): CrowdBus.duck (contracts/b-exports.ts); B's engine ramps with setTargetAtTime.
      if (this.ducks++ === 0) this.opts.crowd.duck(DUCK_DB, DUCK_RAMP_MS);
    });
    later(end + UNDUCK_HOLD_S, () => {
      if (this.ducks > 0 && --this.ducks === 0) this.opts.crowd.unduck(UNDUCK_RAMP_MS);
    });
  }

  private fetch(url: string): Promise<ArrayBuffer | null> {
    let f = this.bytes.get(url);
    if (!f) {
      f = this.opts.fetchAudio(url).catch((err: unknown) => {
        console.warn(`[commentary] could not fetch ${url}; that line will be skipped`, err);
        return null;
      });
      this.bytes.set(url, f);
    }
    return f;
  }

  private decode(url: string): void {
    const ctx = this.ctx;
    if (!ctx || this.decoded.has(url) || this.decoding.has(url)) return;
    const job = this.fetch(url)
      // decodeAudioData detaches its input, so decode a copy and keep the bytes for a re-decode after release().
      .then((ab) => (ab ? ctx.decodeAudioData(ab.slice(0)) : null))
      .then((buf) => {
        if (!buf) return;
        this.silence.set(buf, leadingSilence(buf));
        this.decoded.set(url, buf);
      })
      .catch((err: unknown) => console.warn(`[commentary] could not decode ${url}`, err))
      .finally(() => this.decoding.delete(url));
    this.decoding.set(url, job);
  }

  /** Free decoded PCM that no line still to come needs. */
  private release(p: number): void {
    const keep = new Set<string>();
    this.cues.forEach((c, i) => {
      if (this.status[i] !== 'done' || c.t_in + this.durationOf(i) > p) keep.add(c.utterance.audio_url);
    });
    for (const url of this.decoded.keys()) if (!keep.has(url)) this.decoded.delete(url);
  }
}
