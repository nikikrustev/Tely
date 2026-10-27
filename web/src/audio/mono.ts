// One-ear mode (Tier 1 item 5b): every AudioContext the page plays through, summed to mono, so a fan with one earbud
// or hearing in one ear misses nothing panned to the other side. Each context registers itself once it exists.
// WHY the destination's channelCount: Web Audio down-mixes any input to it with the "speakers" rules (L and R summed,
// half each), so the HRTF and stereo panners need no change, and turning it off restores stereo at once.
const contexts = new Set<BaseAudioContext>();
let mono = false;

function apply(ctx: BaseAudioContext): void {
  const d = ctx.destination;
  try {
    d.channelCount = mono ? 1 : Math.min(2, d.maxChannelCount || 2);
    d.channelInterpretation = 'speakers';
  } catch { /* a context that won't take it plays as it was */ }
}

export function registerContext(ctx: BaseAudioContext): void {
  contexts.add(ctx);
  apply(ctx);
}

export function setMono(on: boolean): void {
  mono = on;
  contexts.forEach(apply);
}

export const isMono = (): boolean => mono;
