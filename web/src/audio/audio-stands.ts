// OWNER: B (Nikolay). Seat-in-the-stands spatial audio (file 37 audio-stands.ts), adapted:
// - the AudioContext is passed in (tests use a fake one; nodes come from its factory methods);
// - earcons are generated here (procedural thud / whistle / net / ping), nothing downloaded;
// - ball moves are scheduled at an exact audio time (`at`), so the replay can queue them ahead.
import { decayNoise, prng, stadiumIR } from './stadium-ir';

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

export interface BallSample { x: number; y: number; z: number; speed: number; alive: boolean }

export class AudioStands {
  readonly ctx: BaseAudioContext;
  readonly master: GainNode;
  readonly crowdIn: GainNode; // CrowdEngine output goes here (it has its own ducking)
  readonly ballBus: GainNode;
  readonly earconBus: GainNode;
  readonly commentaryIn: GainNode; // A's commentary: dry, centre, top priority
  readonly ballPanner: PannerNode;
  private ballGain: GainNode;
  private ballSend: GainNode;
  private rattle: OscillatorNode;
  private reverb: ConvolverNode;
  private icons = new Map<Earcon, AudioBuffer>();
  private nextEarconAt = 0;
  private seat: Seat = 'halfway';
  last = { x: 0, y: 0 };

  constructor(ctx: BaseAudioContext, destination: AudioNode = ctx.destination) {
    this.ctx = ctx;
    this.master = ctx.createGain();
    const limiter = ctx.createDynamicsCompressor(); // file 38 §7: limiter on the master, never full-scale jumps
    limiter.threshold.value = -6;
    limiter.ratio.value = 20;
    this.master.connect(limiter).connect(destination);
    this.reverb = ctx.createConvolver();
    this.reverb.buffer = stadiumIR(ctx, 2.8);
    this.reverb.connect(this.master);
    this.crowdIn = this.bus(1.0);
    this.ballBus = this.bus(0.8);
    this.earconBus = this.bus(0.9);
    this.commentaryIn = this.bus(1.0);
    // Ball = looped noise -> band-pass (broadband localises better than tones) -> rattle AM -> HRTF panner
    const noise = ctx.createBufferSource();
    noise.buffer = this.noiseBuffer(2);
    noise.loop = true;
    const bp = ctx.createBiquadFilter();
    bp.type = 'bandpass';
    bp.frequency.value = 1800;
    bp.Q.value = 0.6;
    const am = ctx.createGain();
    am.gain.value = 0.5;
    this.rattle = ctx.createOscillator();
    this.rattle.type = 'square';
    this.rattle.frequency.value = 6;
    const depth = ctx.createGain();
    depth.gain.value = 0.5;
    this.rattle.connect(depth).connect(am.gain);
    this.ballGain = ctx.createGain();
    this.ballGain.gain.value = 0;
    this.ballPanner = this.panner();
    noise.connect(bp).connect(am).connect(this.ballGain).connect(this.ballPanner).connect(this.ballBus);
    this.ballSend = ctx.createGain();
    this.ballSend.gain.value = 0.2;
    this.ballPanner.connect(this.ballSend).connect(this.reverb); // far = wetter (distance cue)
    const earconSend = ctx.createGain();
    earconSend.gain.value = 0.15;
    this.earconBus.connect(earconSend).connect(this.reverb);
    for (const k of Object.keys(PRIORITY) as Earcon[]) this.icons.set(k, this.makeIcon(k));
    noise.start();
    this.rattle.start();
    this.setSeat('halfway');
  }

  setSeat(seat: Seat): void {
    this.seat = seat;
    setListener(this.ctx.listener, SEATS[seat].pos, SEATS[seat].fwd);
  }

  /** One ball sample, heard at audio time `at`. setTargetAtTime smooths the steps (no zipper noise). */
  ballAt(b: BallSample, at = this.ctx.currentTime, tau = 0.04): void {
    const p = this.ballPanner;
    const w = toWorld(b.x, b.y, b.z);
    p.positionX.setTargetAtTime(w[0], at, tau);
    p.positionY.setTargetAtTime(w[1], at, tau);
    p.positionZ.setTargetAtTime(w[2], at, tau);
    this.rattle.frequency.setTargetAtTime(4 + Math.min(b.speed, 30) * 0.8, at, 0.1); // faster ball, faster rattle
    this.ballGain.gain.setTargetAtTime(b.alive ? 0.35 : 0, at, b.alive ? 0.05 : 0.3); // silent when the ball is dead
    const s = SEATS[this.seat].pos;
    const d = Math.hypot(s[0] - w[0], s[1] - w[1], s[2] - w[2]);
    this.ballSend.gain.setTargetAtTime(Math.min(0.6, d / 120), at, 0.2);
    this.last = { x: b.x, y: b.y };
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
    src.connect(g).connect(p).connect(this.earconBus);
    src.onended = () => p.disconnect();
    src.start(t);
    return t;
  }

  /** "Where is the ball?": three pings at its last position. */
  pingBall(): void {
    for (let i = 0; i < 3; i++) this.earcon('ping', this.last.x, this.last.y);
  }

  /** Seconds between scheduling and hearing (Bluetooth included where reported): haptics should lead by this. */
  get outputDelay(): number {
    const c = this.ctx as AudioContext;
    return (c.baseLatency ?? 0) + (c.outputLatency ?? 0);
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

  private noiseBuffer(sec: number): AudioBuffer {
    const b = this.ctx.createBuffer(1, Math.floor(this.ctx.sampleRate * sec), this.ctx.sampleRate);
    decayNoise([b.getChannelData(0)], this.ctx.sampleRate, 0, 0, 3);
    return b;
  }

  /** Procedural auditory icons (no samples): short, distinct, and different in timbre. */
  private makeIcon(kind: Earcon): AudioBuffer {
    const sr = this.ctx.sampleRate;
    const len = { pass: 0.12, shot: 0.25, tackle: 0.18, save: 0.2, whistle: 0.45, net: 0.6, ping: 0.12 }[kind];
    const b = this.ctx.createBuffer(1, Math.floor(sr * len), sr);
    const d = b.getChannelData(0);
    const rnd = prng(kind.length * 97 + 11);
    for (let i = 0; i < d.length; i++) {
      const t = i / sr;
      const u = t / len;
      let v = 0;
      if (kind === 'pass' || kind === 'shot' || kind === 'save') {
        const f = kind === 'pass' ? 110 : kind === 'shot' ? 80 : 140; // a "thud": falling sine + a click of noise
        v = Math.sin(2 * Math.PI * f * t * (1 - 0.4 * u)) * Math.exp(-t * (kind === 'shot' ? 18 : 30));
        v += (rnd() * 2 - 1) * Math.exp(-t * 120) * (kind === 'shot' ? 0.6 : 0.3);
      } else if (kind === 'tackle') {
        v = (rnd() * 2 - 1) * Math.exp(-t * 25) * 0.7 + Math.sin(2 * Math.PI * 60 * t) * Math.exp(-t * 20) * 0.5;
      } else if (kind === 'whistle') {
        v = Math.sin(2 * Math.PI * (2800 + 120 * Math.sin(2 * Math.PI * 28 * t)) * t) * 0.35 * Math.min(1, 40 * t, 8 * (1 - u));
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
