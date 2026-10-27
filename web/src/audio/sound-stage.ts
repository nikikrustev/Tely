// Seat-in-the-stands spatial audio (file 37 sound-stage.ts), adapted:
// - the AudioContext is passed in (tests use a fake one; nodes come from its factory methods);
// - earcons are generated here (procedural thud / whistle / net / ping), nothing downloaded;
// - ball moves are scheduled at an exact audio time (`at`), so the replay can queue them ahead;
// - there is NO continuous ball sound (24 Oct): from the main stand nobody hears a ball roll on grass. Left/right
//   comes from the kicks (panned by ball x), the crowd end nearest the ball (CrowdEngine.followBall) and the commentary;
// - every sound group has its own level from the shared mix (mix.ts), so the ?mix=1 mixer is heard live.
import { dbToGain, onMix, VoiceStage, type AudioMix } from './mix';
import { prng, stadiumIR } from './stadium-ir';

export type Seat = 'halfway' | 'homeEnd' | 'awayEnd';
export type Earcon = 'pass' | 'shot' | 'tackle' | 'save' | 'whistle' | 'net' | 'ping';
export type V3 = [number, number, number];

/** Pitch (x along, y across, z up; metres, origin centre spot) -> Web Audio world (X = x, Y = z, Z = -y). */
export const toWorld = (x: number, y: number, z = 0): V3 => [x, z, -y];

export const SEATS: Record<Seat, { pos: V3; fwd: V3 }> = {
  halfway: { pos: [0, 12, 49], fwd: [0, 0, -1] }, // main stand, 15 m behind the near touchline, 12 m up (default)
  homeEnd: { pos: [-64, 10, 0], fwd: [1, 0, 0] },
  awayEnd: { pos: [64, 10, 0], fwd: [-1, 0, 0] },
};

/** Earcon onsets at least this far apart (McGookin & Brewster, via file 37). */
export const EARCON_GAP_S = 0.3;
/** A low-priority earcon that would be pushed later than this is dropped instead of piling up. */
const MAX_PUSH_S = 0.45;
const PRIORITY: Record<Earcon, number> = { net: 0, whistle: 0, shot: 0, save: 1, ping: 1, tackle: 2, pass: 3 };
/** The ball on the pitch: dulled and wetter, so these sit inside the crowd instead of popping out of it. */
export const FIELD: readonly Earcon[] = ['pass', 'shot', 'tackle', 'save'];
export const FIELD_LOWPASS_HZ = 2400; // a thud 30-60 m away has lost its click

export interface BallSample { x: number; y: number; z: number; speed: number; alive: boolean }

/** Plain left/right pan from pitch x: Reds' own goal (x -52.5, where Navy attack) hard left, halfway centre,
 *  Navy's goal (x 52.5, where Reds attack) hard right.
 *  HRTF alone was too subtle on laptops and earbuds (listening notes, 23 Oct), so this rides alongside it. */
export const stereoPan = (x: number): number => 0.9 * Math.min(1, Math.max(-1, x / 45));
const HRTF_MIX = 0.45, STEREO_MIX = 0.75;

export class SoundStage {
  readonly ctx: BaseAudioContext;
  readonly master: GainNode;
  readonly crowdIn: GainNode; // CrowdEngine output goes here (it has its own ducking)
  readonly earconBus: GainNode;
  /** Preset answers: the same press-box voice as A's commentary (mix.ts VoiceStage). Dry: no reverb send. */
  readonly commentaryIn: GainNode;
  readonly voice: VoiceStage;
  /** One level per earcon kind, from the mix (mix.ts), heard live. */
  readonly kindGain = new Map<Earcon, GainNode>();
  private reverb: ConvolverNode;
  private icons = new Map<Earcon, AudioBuffer>();
  private nextEarconAt = 0;
  private queued: { src: AudioScheduledSourceNode; when: number }[] = [];
  /** Ball positions queued ahead, by audio time, so "where is it now?" never reads the future. */
  private track: { at: number; x: number; y: number }[] = [];

  constructor(ctx: BaseAudioContext, destination: AudioNode = ctx.destination) {
    this.ctx = ctx;
    this.master = ctx.createGain();
    const limiter = ctx.createDynamicsCompressor(); // file 38 §7: limiter on the master, never full-scale jumps
    limiter.threshold.value = -3; // gentle: a hard ratio-20 limiter pumped on thuds and roars ("hoover", 23 Oct)
    limiter.ratio.value = 4;
    limiter.knee.value = 6;
    limiter.attack.value = 0.005;
    limiter.release.value = 0.3;
    this.master.connect(limiter).connect(destination);
    this.reverb = ctx.createConvolver();
    this.reverb.buffer = stadiumIR(ctx, 2.8);
    this.reverb.connect(this.master);
    this.crowdIn = this.bus(1.0);
    this.earconBus = this.bus(0.7);
    this.voice = new VoiceStage(ctx, this.master);
    this.commentaryIn = this.voice.input;
    const earconSend = ctx.createGain();
    earconSend.gain.value = 0.15;
    this.earconBus.connect(earconSend).connect(this.reverb);
    const fieldLp = ctx.createBiquadFilter();
    fieldLp.type = 'lowpass';
    fieldLp.frequency.value = FIELD_LOWPASS_HZ;
    fieldLp.Q.value = 0.5;
    fieldLp.connect(this.earconBus);
    const fieldSend = ctx.createGain();
    fieldSend.gain.value = 0.3; // twice the whistle's: further away, more of the bowl
    fieldLp.connect(fieldSend).connect(this.reverb);
    for (const k of Object.keys(PRIORITY) as Earcon[]) {
      this.icons.set(k, this.makeIcon(k));
      const g = ctx.createGain();
      g.connect(FIELD.includes(k) ? fieldLp : this.earconBus);
      this.kindGain.set(k, g);
    }
    onMix((m) => this.applyMix(m));
    this.setSeat('halfway');
  }

  applyMix(m: AudioMix): void {
    const t = this.ctx.currentTime;
    for (const [k, g] of this.kindGain) g.gain.setTargetAtTime(dbToGain(m[k]), t, 0.05);
  }

  setSeat(seat: Seat): void {
    setListener(this.ctx.listener, SEATS[seat].pos, SEATS[seat].fwd);
    this.voice.setListener(SEATS[seat].pos, SEATS[seat].fwd);
  }

  /** One ball sample, heard at audio time `at`. Makes no sound: it only records where the ball is (for the ping). */
  ballAt(b: BallSample, at = this.ctx.currentTime): void {
    const now = this.ctx.currentTime;
    while (this.track.length > 1 && (this.track[1] as { at: number }).at <= now) this.track.shift();
    this.track.push({ at, x: b.x, y: b.y });
  }

  /** Where the ball is as heard now: the latest sample at or before the audio clock. */
  get last(): { x: number; y: number } {
    const now = this.ctx.currentTime;
    let p = this.track[0] ?? { x: 0, y: 0 };
    for (const s of this.track) {
      if (s.at > now) break;
      p = s;
    }
    return { x: p.x, y: p.y };
  }

  /** A spatial earcon at pitch (x, y). Returns the start time, or null if it was dropped (too crowded). */
  earcon(kind: Earcon, x: number, y: number, at = this.ctx.currentTime, gain = 1): number | null {
    const buffer = this.icons.get(kind);
    if (!buffer) return null;
    const t = Math.max(this.ctx.currentTime, at, this.nextEarconAt);
    if (t - at > MAX_PUSH_S && PRIORITY[kind] >= 2) return null;
    this.nextEarconAt = t + EARCON_GAP_S;
    const src = this.ctx.createBufferSource();
    src.buffer = buffer;
    const g = this.ctx.createGain();
    g.gain.value = gain * (kind === 'pass' ? 0.5 : 1);
    const p = this.panner();
    const [X, Y, Z] = toWorld(x, y, 1);
    p.positionX.value = X;
    p.positionY.value = Y;
    p.positionZ.value = Z;
    const sp = this.ctx.createStereoPanner();
    sp.pan.value = stereoPan(x);
    src.connect(g);
    this.mix(g, p, sp, this.kindGain.get(kind) as GainNode);
    src.onended = () => { p.disconnect(); sp.disconnect(); };
    src.start(t);
    this.queued = this.queued.filter((q) => q.when > this.ctx.currentTime - 5);
    this.queued.push({ src, when: t });
    return t;
  }

  /** Drop ball positions and earcons scheduled from audio time `t` on (after a seek). */
  cancelFrom(t: number): void {
    this.track = this.track.filter((s) => s.at < t);
    for (const q of this.queued) if (q.when >= t) try { q.src.stop(); } catch { /* already stopped */ }
    this.queued = this.queued.filter((q) => q.when < t);
    this.nextEarconAt = 0;
  }

  /** "Where is the ball?": three pings where it is now. */
  pingBall(): void {
    const { x, y } = this.last;
    for (let i = 0; i < 3; i++) this.earcon('ping', x, y);
  }

  /** Seconds between scheduling and hearing (Bluetooth included where reported): haptics should lead by this. */
  get outputDelay(): number {
    const c = this.ctx as AudioContext;
    return (c.baseLatency ?? 0) + (c.outputLatency ?? 0);
  }

  /** Send `from` through both the 3D (HRTF) panner and the plain stereo panner into `to`. */
  private mix(from: AudioNode, hrtf: PannerNode, stereo: StereoPannerNode, to: AudioNode): void {
    const a = this.ctx.createGain(), b = this.ctx.createGain();
    a.gain.value = HRTF_MIX;
    b.gain.value = STEREO_MIX;
    from.connect(hrtf).connect(a).connect(to);
    from.connect(stereo).connect(b).connect(to);
  }

  private bus(gain: number): GainNode {
    const g = this.ctx.createGain();
    g.gain.value = gain;
    g.connect(this.master);
    return g;
  }

  private panner(): PannerNode {
    // Tuned for clarity: about -13 dB from 15 m to 80 m, so the far end is never inaudible (file 37 §4)
    const p = this.ctx.createPanner();
    p.panningModel = 'HRTF';
    p.distanceModel = 'inverse';
    p.refDistance = 10;
    p.rolloffFactor = 0.5;
    p.maxDistance = 200;
    return p;
  }

  /** Procedural auditory icons (no samples): short, distinct, and different in timbre. */
  private makeIcon(kind: Earcon): AudioBuffer {
    const sr = this.ctx.sampleRate;
    const len = { pass: 0.12, shot: 0.25, tackle: 0.18, save: 0.2, whistle: 0.45, net: 0.6, ping: 0.12 }[kind];
    const b = this.ctx.createBuffer(1, Math.floor(sr * len), sr);
    const d = b.getChannelData(0);
    const rnd = prng(kind.length * 97 + 11);
    let phase = 0, breath = 0;
    for (let i = 0; i < d.length; i++) {
      const t = i / sr;
      const u = t / len;
      let v = 0;
      if (kind === 'pass' || kind === 'shot' || kind === 'save') {
        const f = kind === 'pass' ? 180 : kind === 'shot' ? 140 : 210; // a "thud": falling sine + a click (less bass: 23 Oct)
        v = 0.6 * Math.sin(2 * Math.PI * f * t * (1 - 0.4 * u)) * Math.exp(-t * (kind === 'shot' ? 22 : 35));
        v += (rnd() * 2 - 1) * Math.exp(-t * 120) * (kind === 'shot' ? 0.6 : 0.3);
      } else if (kind === 'tackle') {
        v = (rnd() * 2 - 1) * Math.exp(-t * 25) * 0.7 + Math.sin(2 * Math.PI * 60 * t) * Math.exp(-t * 20) * 0.5;
      } else if (kind === 'whistle') {
        // A referee's pea whistle: ~2.2 kHz tone trilled ~27 times a second by the pea, plus breath noise.
        // About 10 dB quieter than the first version, which was a pure 2.8 kHz sine (piercing, team notes 22 Oct).
        const trill = Math.sin(2 * Math.PI * 27 * t);
        phase += (2 * Math.PI * (2200 + 70 * trill)) / sr;
        breath = 0.75 * breath + 0.25 * (rnd() * 2 - 1);
        const env = Math.min(1, 25 * t, 6 * (1 - u));
        v = (0.8 * Math.sin(phase) * (0.55 + 0.45 * (0.5 + 0.5 * trill)) + 0.3 * breath) * env * 0.11;
      } else if (kind === 'net') {
        v = (rnd() * 2 - 1) * Math.sin(Math.PI * u) * 0.5; // a soft swish
      } else {
        v = Math.sin(2 * Math.PI * 1200 * t) * Math.exp(-t * 25) * 0.6;
      }
      d[i] = v;
    }
    return b;
  }
}

/** Chrome / Safari 14.1+ have AudioParams on the listener; Firefox only has setPosition/setOrientation. */
export function setListener(L: AudioListener, pos: V3, fwd: V3): void {
  if (L.positionX) {
    L.positionX.value = pos[0];
    L.positionY.value = pos[1];
    L.positionZ.value = pos[2];
    L.forwardX.value = fwd[0];
    L.forwardY.value = fwd[1];
    L.forwardZ.value = fwd[2];
    L.upX.value = 0;
    L.upY.value = 1;
    L.upZ.value = 0;
  } else {
    L.setPosition(pos[0], pos[1], pos[2]);
    L.setOrientation(fwd[0], fwd[1], fwd[2], 0, 1, 0);
  }
}
