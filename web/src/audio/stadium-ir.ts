// A generated stadium impulse response (file 37 §6): no downloaded IRs, so no licence risk.
// Decorrelated stereo noise, 20 ms pre-delay, exponential decay to -60 dB over `seconds` (RT60 ~ seconds).

/** Small seeded PRNG (mulberry32), so the same seed gives the same IR and tests are repeatable. */
export function prng(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Fill `channels` arrays with decaying noise. k = 6.9 gives -60 dB at the end (e^-6.9 ~ 0.001). */
export function decayNoise(channels: Float32Array[], sampleRate: number, preSec: number, k: number, seed = 1): void {
  const rnd = prng(seed);
  for (const d of channels) {
    const pre = Math.floor(sampleRate * preSec);
    const n = d.length;
    for (let i = 0; i < n; i++) d[i] = i < pre ? 0 : (rnd() * 2 - 1) * Math.exp((-k * (i - pre)) / Math.max(1, n - pre));
  }
}

export function stadiumIR(ctx: BaseAudioContext, seconds = 2.8, seed = 7): AudioBuffer {
  const b = ctx.createBuffer(2, Math.floor(ctx.sampleRate * seconds), ctx.sampleRate);
  decayNoise([b.getChannelData(0), b.getChannelData(1)], ctx.sampleRate, 0.02, 6.9, seed);
  return b;
}
