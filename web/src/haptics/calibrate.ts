// One-tap Bluetooth calibration (file 37 §5, file 41).
// Bluetooth earbuds add 126-274 ms (Coyle's tap-to-sound measurements, file 37), and the browser often doesn't report
// it. The fan taps along to a beat; the median gap between each beat being played and the tap is the delay their ears
// hear. Haptics then fire that much later, so the vibration lands with the sound (fire early, never late: file 41).

// One beat a second: slow enough that even 274 ms earbuds (file 37) plus a sloppy tap can't be paired with the
// wrong beat. Ours: 8 beats, at least 5 usable taps.
export const BEATS = 8, BEAT_S = 1.0;
export const MIN_TAPS = 5, MAX_OFFSET_MS = 500, EARLY_TAP_MS = 150;

/**
 * Median delay (ms) from each beat leaving the browser to the fan's tap. Each tap is paired with the latest beat at or
 * before it (a tap up to EARLY_TAP_MS early still counts, as people anticipate a steady beat); taps that fit no beat
 * are ignored, and a beat is used once. Returns null with fewer than MIN_TAPS taps; clamps to 0..MAX_OFFSET_MS.
 */
export function estimateOffsetMs(beatsMs: number[], tapsMs: number[]): number | null {
  const gaps: number[] = [];
  const used = new Set<number>();
  for (const tap of [...tapsMs].sort((a, b) => a - b)) {
    let best = -1;
    beatsMs.forEach((b, i) => { if (!used.has(i) && b <= tap + EARLY_TAP_MS) best = i; });   // latest such beat
    if (best < 0) continue;
    const gap = tap - (beatsMs[best] as number);
    if (gap < -EARLY_TAP_MS || gap > MAX_OFFSET_MS + EARLY_TAP_MS) continue;
    used.add(best);
    gaps.push(gap);
  }
  if (gaps.length < MIN_TAPS) return null;
  gaps.sort((a, b) => a - b);
  const mid = gaps.length >> 1;
  const median = gaps.length % 2 ? (gaps[mid] as number) : ((gaps[mid - 1] as number) + (gaps[mid] as number)) / 2;
  return Math.round(Math.min(MAX_OFFSET_MS, Math.max(0, median)));
}

export interface CalibrationDeps {
  /** Play a click at audio time `at`. */
  click(at: number): void;
  ctxNow(): number;
  /** Audio-clock time -> performance.now() time at which the browser outputs it (getOutputTimestamp, file 41). */
  toPerf(ctxTime: number): number;
  perfNow(): number;
  wait(ms: number): Promise<void>;
}

/** Plays BEATS clicks; collects taps via tap(); finish() returns the estimate (or null). */
export class Calibration {
  private beats: number[] = [];
  private taps: number[] = [];
  constructor(private d: CalibrationDeps) {}

  async play(): Promise<void> {
    const t0 = this.d.ctxNow() + 0.5;
    for (let i = 0; i < BEATS; i++) {
      this.d.click(t0 + i * BEAT_S);
      this.beats.push(this.d.toPerf(t0 + i * BEAT_S));
    }
    await this.d.wait((0.5 + BEATS * BEAT_S + 0.4) * 1000);
  }

  tap(): void {
    this.taps.push(this.d.perfNow());
  }

  finish(): number | null {
    return estimateOffsetMs(this.beats, this.taps);
  }
}

/** Audio time -> performance time, using the browser's output timestamp (no outputLatency: the taps measure that). */
export function perfMapper(ctx: AudioContext): (t: number) => number {
  return (t: number) => {
    const ts = ctx.getOutputTimestamp?.();
    const perf = ts?.performanceTime ?? performance.now(), at = ts?.contextTime ?? ctx.currentTime;
    return perf + (t - at) * 1000;
  };
}
