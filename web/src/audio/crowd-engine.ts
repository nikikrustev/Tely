// OWNER: B (Nikolay). The reactive crowd (file 38 CrowdEngine), adapted:
// - implements CrowdBus.duck(db, rampMs) / unduck(rampMs) from contracts/b-exports.ts (A's commentary ducks us);
// - state changes are scheduled at an exact audio time, so the replay can queue them ahead;
// - an explicit `level` gain follows excitement (the crowd "bus gain" the Stage 2 test checks);
// - our end and the other end: one-shots from the other end play distant (low-passed, opposite side);
// - "hush" / "stunned_hush" are dips of the whole crowd, not samples;
// - the chant vowel is generated (no sample), sung on our own seeded motif (no real songs, file 38 §5).
import type { CrowdBus } from '../contracts/b-exports';
import { prng } from './stadium-ir';

export interface CrowdState { excitement: number; valence: number; danger: number } // 0..1, -1..1, -1..1 (+ = we attack)
export type BedName = 'murmur' | 'swell' | 'tense' | 'away';
export interface CrowdBuffers { beds: Partial<Record<BedName, AudioBuffer>>; shots: Record<string, AudioBuffer[]> }

const clamp = (x: number, a = 0, b = 1) => Math.min(b, Math.max(a, x));

/** Crowd bus level from excitement: strictly increasing, 0.45 at a quiet moment, 1.0 at full roar (ours). */
export const levelFor = (excitement: number): number => 0.45 + 0.55 * clamp(excitement);

/** Default "don't repeat" time per one-shot (file 38 §7: 4 s default; longer for the big ones, ours). */
export const REFRACTORY_S: Record<string, number> = {
  roar: 20, stunned_hush: 20, ooh_groan: 6, relief_applause: 6, whistles_jeer: 8, cheer: 6, hush: 15,
};

interface Bed { gain: GainNode; lp: BiquadFilterNode; pan: StereoPannerNode }

export class CrowdEngine implements CrowdBus {
  readonly ctx: BaseAudioContext;
  readonly level: GainNode; // follows excitement
  readonly output: GainNode;
  private duckGain: GainNode;
  private speechDip: BiquadFilterNode;
  private hushGain: GainNode;
  private chantGain: GainNode;
  private beds = new Map<BedName, Bed>();
  private lastShot = new Map<string, number>();
  private targets = new Map<AudioParam, number>();
  private queued: { src: AudioScheduledSourceNode; when: number }[] = [];
  private state: CrowdState = { excitement: 0.2, valence: 0, danger: 0 };
  private rnd: () => number;
  private timer: ReturnType<typeof setInterval> | null = null;
  private nextGrain = 0;
  private nextBeat = 0;
  private beat = 0;
  private motif: number[];
  private vowel: AudioBuffer;
  private clapNoise: AudioBuffer;
  readonly homePan: number;
  started = 0; // one-shots actually started (tests read it)

  constructor(ctx: BaseAudioContext, destination: AudioNode, private buf: CrowdBuffers,
              opts: { homePan?: number; clubSeed?: number; seed?: number } = {}) {
    this.ctx = ctx;
    this.homePan = opts.homePan ?? -0.5; // halfway seat: the home end is on the left
    this.rnd = prng(opts.seed ?? 1);
    this.output = ctx.createGain();
    this.output.gain.value = 0.8;
    this.level = ctx.createGain();
    this.level.gain.value = levelFor(this.state.excitement);
    this.hushGain = ctx.createGain();
    this.duckGain = ctx.createGain();
    this.speechDip = ctx.createBiquadFilter();
    this.speechDip.type = 'peaking';
    this.speechDip.frequency.value = 2000;
    this.speechDip.Q.value = 0.8;
    this.speechDip.gain.value = 0;
    this.level.connect(this.hushGain).connect(this.duckGain).connect(this.speechDip).connect(this.output).connect(destination);
    this.chantGain = ctx.createGain();
    this.chantGain.gain.value = 0;
    this.chantGain.connect(this.level);
    const pans: Record<BedName, number> = { murmur: this.homePan, swell: this.homePan, tense: this.homePan, away: -this.homePan * 0.8 };
    for (const n of Object.keys(pans) as BedName[]) this.beds.set(n, this.makeBed(pans[n]));
    this.motif = CrowdEngine.makeMotif(opts.clubSeed ?? 7);
    this.vowel = this.makeVowel();
    this.clapNoise = this.makeNoise(0.2);
  }

  /** Our own 8-step pentatonic motif, seeded per synthetic club (no real songs). -1 = rest. */
  static makeMotif(seed: number): number[] {
    const scale = [0, 2, 4, 7, 9, 12];
    let s = seed >>> 0;
    const out: number[] = [];
    for (let i = 0; i < 8; i++) {
      s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
      out.push(i % 4 === 3 ? -1 : (scale[s % scale.length] ?? 0));
    }
    return out;
  }

  start(): void {
    const t = this.ctx.currentTime;
    for (const n of ['swell', 'tense', 'away'] as const) {
      const b = this.buf.beds[n];
      const bed = this.beds.get(n);
      if (!b || !bed) continue;
      const src = this.ctx.createBufferSource();
      src.buffer = b;
      src.loop = true;
      src.connect(bed.lp);
      src.start(t, this.rnd() * b.duration);
    }
    this.nextGrain = t;
    this.nextBeat = t;
    if (typeof setInterval !== 'undefined') this.timer = setInterval(() => this.schedule(), 25); // "two clocks"
    this.setState(this.state, t, 0.5);
  }

  stop(): void {
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
    this.output.gain.setTargetAtTime(0, this.ctx.currentTime, 0.3);
  }

  /** Move every layer toward `s` from audio time `at`. Rises faster than it falls. */
  setState(s: CrowdState, at = this.ctx.currentTime, tc = 0.6): void {
    const e = clamp(s.excitement), v = clamp(s.valence, -1, 1), d = clamp(s.danger, -1, 1);
    const ours = Math.max(d, 0), theirs = Math.max(-d, 0);
    const go = (p: AudioParam, target: number) => {
      const prev = this.targets.get(p) ?? p.value;
      this.targets.set(p, target);
      p.setTargetAtTime(target, at, target > prev ? tc * 0.5 : tc * 2);
    };
    const bed = (n: BedName) => this.beds.get(n) as Bed;
    go(this.level.gain, levelFor(e));
    go(bed('murmur').gain.gain, (0.25 + 0.35 * e) * (1 - 0.45 * theirs)); // home end goes quiet under pressure
    go(bed('murmur').lp.frequency, 2000 + 3500 * e);                        // bigger crowd = brighter (2 kHz floor: no rumble)
    go(bed('swell').gain.gain, Math.pow(ours, 1.5) * (0.3 + 0.7 * e));      // rising "ooh" on our attacks
    go(bed('swell').lp.frequency, 900 + 6000 * ours);
    go(bed('tense').gain.gain, 0.45 * theirs * (0.5 + 0.5 * e));
    go(bed('away').gain.gain, 0.08 + 0.35 * theirs * e);
    go(this.chantGain.gain, 0.4 * clamp((e - 0.3) / 0.5) * Math.max(v, 0) * (1 - theirs)); // sing when happy and safe
    this.state = { excitement: e, valence: v, danger: d };
  }

  /** The other end's mood drives the distant "away" bed (its excitement when they attack). */
  setOtherEnd(s: CrowdState, at = this.ctx.currentTime): void {
    const bed = this.beds.get('away') as Bed;
    bed.gain.gain.setTargetAtTime(0.08 + 0.3 * clamp(s.excitement) * Math.max(0, clamp(s.danger, -1, 1)), at, 0.8);
  }

  /** A one-shot at audio time `when`. `ours` = from our end (near, full) or the other end (far, muffled).
   *  Returns false when the refractory limit blocks it (anti-fatigue) or there is no clip. */
  trigger(name: string, when = this.ctx.currentTime, ours = true, intensity = 1, refractoryS = REFRACTORY_S[name] ?? 4): boolean {
    const key = `${name}:${ours ? 'us' : 'them'}`;
    if (when - (this.lastShot.get(key) ?? -Infinity) < refractoryS) return false;
    if (name === 'hush' || name === 'stunned_hush') {
      if (!ours) return false;
      this.lastShot.set(key, when);
      const [depth, hold] = name === 'hush' ? [0.55, 2] : [0.3, 6];
      this.hushGain.gain.setTargetAtTime(depth, when, 0.15);
      this.hushGain.gain.setTargetAtTime(1, when + hold, name === 'hush' ? 1 : 3);
      this.chantGain.gain.setTargetAtTime(0, when, 0.1);
      return true;
    }
    const variants = this.buf.shots[name];
    if (!variants?.length) return false;
    this.lastShot.set(key, when);
    const src = this.ctx.createBufferSource();
    src.buffer = variants[Math.floor(this.rnd() * variants.length)] ?? variants[0] ?? null;
    src.playbackRate.value = 0.94 + this.rnd() * 0.12; // variation, not identical repeats
    const g = this.ctx.createGain();
    const peak = clamp(intensity) * (ours ? 0.8 + this.rnd() * 0.2 : 0.35);
    g.gain.setValueAtTime(0, when);
    g.gain.linearRampToValueAtTime(peak, when + 0.08); // 80 ms attack: never a startling jump (file 38 §7)
    const p = this.ctx.createStereoPanner();
    p.pan.value = ours ? this.homePan : -this.homePan * 0.8;
    if (ours) {
      src.connect(g).connect(p).connect(this.level);
    } else {
      const lp = this.ctx.createBiquadFilter();
      lp.type = 'lowpass';
      lp.frequency.value = 900;
      src.connect(lp).connect(g).connect(p).connect(this.level);
    }
    src.start(when);
    this.started++;
    this.queued = this.queued.filter((q) => q.when > this.ctx.currentTime - 30);
    this.queued.push({ src, when });
    if (name === 'roar' && ours) this.chantGain.gain.setTargetAtTime(0, when, 0.2);
    return true;
  }

  /** Drop everything scheduled from audio time `t` on (after a seek): state moves and one-shots not yet started. */
  cancelFrom(t: number): void {
    const params = [this.level.gain, this.hushGain.gain, this.chantGain.gain];
    for (const b of this.beds.values()) params.push(b.gain.gain, b.lp.frequency);
    for (const p of params) p.cancelScheduledValues(t);
    this.hushGain.gain.setTargetAtTime(1, t, 0.2);
    for (const q of this.queued) if (q.when >= t) try { q.src.stop(); } catch { /* already stopped */ }
    this.queued = this.queued.filter((q) => q.when < t);
    this.lastShot.clear();
  }

  /** Overall crowd level (Settings: crowd mix). */
  setOutputGain(g: number): void {
    this.output.gain.setTargetAtTime(g, this.ctx.currentTime, 0.1);
  }

  // SEAM(B->A): CrowdBus contract (web/src/contracts/b-exports.ts). A's commentary track and live Ask call these.
  /** Lower the crowd by `db` (negative, e.g. -12) over `rampMs`, plus a -6 dB speech-band dip at 2 kHz. */
  duck(db: number, rampMs: number): void {
    const t = this.ctx.currentTime, tau = Math.max(0.001, rampMs / 3000); // ~95% of the way after 3 time constants
    this.duckGain.gain.setTargetAtTime(Math.pow(10, Math.min(0, db) / 20), t, tau);
    this.speechDip.gain.setTargetAtTime(-6, t, tau);
  }

  /** Return the crowd to its normal level over `rampMs`. */
  unduck(rampMs: number): void {
    const t = this.ctx.currentTime, tau = Math.max(0.001, rampMs / 3000);
    this.duckGain.gain.setTargetAtTime(1, t, tau);
    this.speechDip.gain.setTargetAtTime(0, t, tau);
  }

  /** "Two clocks" (file 38 §6): a 25 ms timer schedules grains and chant beats due in the next 100 ms. */
  schedule(): void {
    const now = this.ctx.currentTime, ahead = now + 0.1, e = this.state.excitement;
    if (this.nextGrain < now) this.nextGrain = now; // after a stalled tab: skip, never burst
    if (this.nextBeat < now) this.nextBeat = now;
    const murmur = this.buf.beds.murmur;
    const density = 6 + 30 * e;
    while (murmur && this.nextGrain < ahead) {
      this.grain(murmur, this.nextGrain, 0.18 + 0.22 * this.rnd()); // longer grains: smoother, less "chug"
      this.nextGrain += (0.5 + this.rnd()) / density;
    }
    const beatS = 60 / (96 + 20 * e) / 2;
    while (this.nextBeat < ahead) {
      const step = this.motif[this.beat % this.motif.length] ?? -1;
      if (step >= 0 && this.chantGain.gain.value > 0.02) this.chantNote(step, this.nextBeat, beatS * 0.9);
      if (this.beat % 2 === 0 && this.state.valence > 0.3 && e > 0.35) this.clap(this.nextBeat, 0.4 * e);
      this.beat++;
      this.nextBeat += beatS;
    }
  }

  private makeBed(panValue: number): Bed {
    const gain = this.ctx.createGain();
    gain.gain.value = 0;
    const lp = this.ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.value = 2000;
    const pan = this.ctx.createStereoPanner();
    pan.pan.value = panValue;
    lp.connect(gain).connect(pan).connect(this.level);
    return { gain, lp, pan };
  }

  private grain(b: AudioBuffer, when: number, len: number): void {
    const src = this.ctx.createBufferSource();
    src.buffer = b;
    src.playbackRate.value = 0.97 + 0.06 * this.state.excitement;
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(0, when);
    g.gain.linearRampToValueAtTime(0.35, when + len / 2); // longer grains overlap more: lower each one (~ -3 dB)
    g.gain.linearRampToValueAtTime(0, when + len);
    src.connect(g).connect((this.beds.get('murmur') as Bed).lp);
    src.start(when, this.rnd() * Math.max(0, b.duration - len), len);
  }

  private chantNote(semitones: number, when: number, dur: number): void {
    for (let voice = 0; voice < 3; voice++) { // 3 detuned copies = many voices
      const src = this.ctx.createBufferSource();
      src.buffer = this.vowel;
      src.playbackRate.value = Math.pow(2, semitones / 12);
      src.detune.value = (voice - 1) * 15 + (this.rnd() - 0.5) * 10;
      const g = this.ctx.createGain();
      g.gain.setValueAtTime(0, when);
      g.gain.linearRampToValueAtTime(0.25, when + 0.04);
      g.gain.setTargetAtTime(0, when + dur * 0.7, 0.05);
      src.connect(g).connect(this.chantGain);
      src.start(when + voice * 0.012, 0.05, dur + 0.2);
    }
  }

  /** Procedural clap ensemble: band-passed noise bursts with a fast decay (after Lee & Reiss 2020, file 38). */
  private clap(when: number, lvl: number): void {
    for (let k = 0; k < 12; k++) {
      const t = when + (this.rnd() - 0.5) * 0.04;
      const src = this.ctx.createBufferSource();
      src.buffer = this.clapNoise;
      const bp = this.ctx.createBiquadFilter();
      bp.type = 'bandpass';
      bp.frequency.value = 900 + this.rnd() * 1500;
      bp.Q.value = 1.2;
      const g = this.ctx.createGain();
      g.gain.setValueAtTime(lvl / 4, t);
      g.gain.setTargetAtTime(0, t + 0.002, 0.012);
      const p = this.ctx.createStereoPanner();
      p.pan.value = clamp(this.homePan + (this.rnd() - 0.5) * 0.6, -1, 1);
      src.connect(bp).connect(g).connect(p).connect(this.chantGain);
      src.start(t, this.rnd() * 0.1, 0.06);
    }
  }

  /** A generated "aah" vowel (a 196 Hz buzz with two formant peaks), so chants need no voice sample. */
  private makeVowel(): AudioBuffer {
    const sr = this.ctx.sampleRate, n = Math.floor(sr * 1.2);
    const b = this.ctx.createBuffer(1, n, sr);
    const d = b.getChannelData(0);
    const f0 = 196, formants = [[700, 130], [1220, 120]] as const;
    for (let i = 0; i < n; i++) {
      const t = i / sr;
      let v = 0;
      for (let h = 1; h * f0 < 4000; h++) {
        const f = h * f0;
        let amp = 0;
        for (const [fc, bw] of formants) amp += 1 / (1 + ((f - fc) / bw) ** 2);
        v += (amp / h) * Math.sin(2 * Math.PI * f * t + h);
      }
      d[i] = 0.3 * v * Math.min(1, t * 20, (1.2 - t) * 20);
    }
    return b;
  }

  private makeNoise(sec: number): AudioBuffer {
    const b = this.ctx.createBuffer(1, Math.floor(this.ctx.sampleRate * sec), this.ctx.sampleRate);
    const d = b.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = this.rnd() * 2 - 1;
    return b;
  }
}

/** Load web/public/crowd/manifest.json and decode every clip. Missing files are skipped, never fatal. */
export async function loadCrowdBuffers(ctx: BaseAudioContext, base = '/crowd'): Promise<CrowdBuffers> {
  const res = await fetch(`${base}/manifest.json`);
  const manifest = (await res.json()) as { roles: Record<string, string[]> };
  const decode = async (f: string) => {
    try {
      return await ctx.decodeAudioData(await (await fetch(`${base}/${f}`)).arrayBuffer());
    } catch {
      return null;
    }
  };
  const out: CrowdBuffers = { beds: {}, shots: {} };
  for (const [role, files] of Object.entries(manifest.roles)) {
    const bufs = (await Promise.all(files.map(decode))).filter((b): b is AudioBuffer => b !== null);
    if (role === 'murmur' || role === 'swell' || role === 'tense' || role === 'away') out.beds[role] = bufs[0];
    else out.shots[role] = bufs;
  }
  return out;
}
