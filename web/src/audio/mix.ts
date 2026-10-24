// OWNER: A (potencialbg; B's lane since the 24 Oct handover). The match mix: one level per sound group, in dB on
// top of each engine's built-in level, plus where the commentator sits. One shared store, so the ?mix=1 mixer
// (web/src/tester/mixer.ts) is heard live in all three audio contexts (B's stage, A's commentary, A's live Ask).
// No Microsoft here: plain Web Audio.

export type VoicePos = 'behind' | 'above' | 'overhead';
export const VOICE_POSITIONS: readonly VoicePos[] = ['behind', 'above', 'overhead'];

/** Every sound group, in dB. -40 dB or lower = off. */
export interface MixLevels {
  crowdBeds: number;   // the murmur grains and the swell / tense / away beds
  chants: number;      // the chant and the claps
  roars: number;       // crowd one-shots: roar, ooh, cheer, jeers, applause
  pass: number;
  shot: number;
  tackle: number;
  save: number;
  net: number;
  whistle: number;
  ping: number;        // "Where is the ball?" and the Bluetooth calibration beat
  commentator: number; // the commentary track, preset answers and live answers
}

export interface AudioMix extends MixLevels {
  /** How much the crowd end nearest the ball lifts (and the far end drops), 0..1. 0.5 = about +-3.5 dB. */
  nearEnd: number;
  commentatorPos: VoicePos;
}

export const MIX_GROUPS: readonly (keyof MixLevels)[] = [
  'crowdBeds', 'chants', 'roars', 'pass', 'shot', 'tackle', 'save', 'net', 'whistle', 'ping', 'commentator',
];
export const MIN_DB = -40;
export const MAX_DB = 12;

// Set by ear in the ?mix=1 mixer (potencialbg, audio-mix.json saved 24 Oct 2026 20:30 UTC). Kicks and saves sit well
// under the crowd bed, like thuds heard from the main stand; the net and whistle are nearly off; reactions over the bed.
export const DEFAULT_MIX: AudioMix = {
  crowdBeds: -14, chants: -20, roars: -7,
  pass: -29.5, shot: -20, tackle: -20, save: -20, net: -39, whistle: -28, ping: -0.5,
  commentator: -23.5,
  nearEnd: 0.55,
  commentatorPos: 'behind',
};

export const dbToGain = (db: number): number => (db <= MIN_DB ? 0 : Math.pow(10, db / 20));

/** Keep only known keys with valid values; anything else falls back to `base`. Accepts {mix: {...}} too. */
export function parseMix(x: unknown, base: AudioMix = DEFAULT_MIX): AudioMix {
  let o = (x && typeof x === 'object' ? x : {}) as Record<string, unknown>;
  if (o.mix && typeof o.mix === 'object') o = o.mix as Record<string, unknown>;
  const out: AudioMix = { ...base };
  for (const k of MIX_GROUPS) {
    const v = o[k];
    if (typeof v === 'number' && Number.isFinite(v)) out[k] = Math.min(MAX_DB, Math.max(MIN_DB, v));
  }
  if (typeof o.nearEnd === 'number' && Number.isFinite(o.nearEnd)) out.nearEnd = Math.min(1, Math.max(0, o.nearEnd));
  if (VOICE_POSITIONS.includes(o.commentatorPos as VoicePos)) out.commentatorPos = o.commentatorPos as VoicePos;
  return out;
}

let current: AudioMix = { ...DEFAULT_MIX };
const listeners = new Set<(m: AudioMix) => void>();

export const getMix = (): AudioMix => current;

export function setMix(patch: Partial<AudioMix>): AudioMix {
  current = parseMix(patch, current);
  listeners.forEach((f) => f(current));
  return current;
}

/** Call `f` now and on every change. Returns an unsubscribe function. */
export function onMix(f: (m: AudioMix) => void): () => void {
  listeners.add(f);
  f(current);
  return () => listeners.delete(f);
}

/** The commentator, as heard from the press box (seat at the origin, facing -Z, up +Y). HRTF gives the direction;
 *  the EQ adds Blauert's directional bands (more ~1 kHz and less ~4 kHz reads "behind", more ~8 kHz reads "above"),
 *  because HRTF elevation and front/back are weak on most headphones. Never left or right: X is always 0. */
export const VOICE_PLACES: Record<VoicePos, { pos: [number, number, number]; eq: [number, number, number] }> = {
  behind: { pos: [0, 0.8, 2], eq: [3, -3, 0] },    // [dB at 1 kHz, dB at 4 kHz, dB at 8 kHz]
  above: { pos: [0, 2, 0.8], eq: [1.5, -3, 3] },
  overhead: { pos: [0, 2, 0], eq: [0, -2, 4] },
};

/** The commentator's chain, the same in every context it plays in: high-pass (a close, dry booth mic, no rumble),
 *  directional EQ, HRTF panner with no distance loss, and the commentator level. No reverb send, so the voice is
 *  clearly outside the stadium's space. Connect speech to `input`. */
export class VoiceStage {
  readonly input: GainNode;
  readonly panner: PannerNode;
  private level: GainNode;
  private bands: BiquadFilterNode[];
  private off: () => void;
  private mix: AudioMix = current;
  private frame: { pos: [number, number, number]; fwd: [number, number, number] } = { pos: [0, 0, 0], fwd: [0, 0, -1] };

  constructor(private ctx: BaseAudioContext, destination: AudioNode) {
    this.input = ctx.createGain();
    const hp = ctx.createBiquadFilter();
    hp.type = 'highpass';
    hp.frequency.value = 110;
    this.bands = [1000, 4000, 8000].map((f) => {
      const b = ctx.createBiquadFilter();
      b.type = 'peaking';
      b.frequency.value = f;
      b.Q.value = 1;
      return b;
    });
    this.panner = ctx.createPanner();
    this.panner.panningModel = 'HRTF';
    this.panner.distanceModel = 'linear';
    this.panner.rolloffFactor = 0; // a voice right behind you: no distance loss
    this.level = ctx.createGain();
    let n: AudioNode = this.input.connect(hp);
    for (const b of this.bands) n = n.connect(b);
    n.connect(this.panner).connect(this.level).connect(destination);
    this.off = onMix((m) => this.apply(m));
  }

  /** Where this context's listener is (B's stage puts it on the seat; A's voice contexts leave it at the origin). */
  setListener(pos: [number, number, number], fwd: [number, number, number]): void {
    this.frame = { pos, fwd };
    this.apply(this.mix);
  }

  apply(m: AudioMix): void {
    this.mix = m;
    const t = this.ctx.currentTime, place = VOICE_PLACES[m.commentatorPos];
    this.level.gain.setTargetAtTime(dbToGain(m.commentator), t, 0.05);
    this.bands.forEach((b, i) => b.gain.setTargetAtTime(place.eq[i] ?? 0, t, 0.05));
    // Local (right, up, back) -> world, for a listener facing `fwd` with up = +Y: right = fwd x up = (-fz, 0, fx).
    const [x, y, z] = place.pos, [px, py, pz] = this.frame.pos, [fx, , fz] = this.frame.fwd;
    this.panner.positionX.setTargetAtTime(px - x * fz - z * fx, t, 0.05);
    this.panner.positionY.setTargetAtTime(py + y, t, 0.05);
    this.panner.positionZ.setTargetAtTime(pz + x * fx - z * fz, t, 0.05);
  }

  dispose(): void {
    this.off();
  }
}
