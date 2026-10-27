// The voice lane's entry point: mountLaneA, the local commentary base and the live relay URL.
import { describe, expect, it } from 'vitest';
import type { LaneBContext } from '../src/contracts/stage';
import { localCommentaryBase, mountLaneA } from '../src/voice';

// SEAM(A->B): a fake LaneBContext, so A's tests depend only on B's contract, not on B's main.ts.
const ctx: LaneBContext = {
  crowd: { duck() {}, unduck() {} },
  ask: { registerLiveMode() {} },
  clock: { now: () => 0, isPlaying: () => false, onChange: () => () => {} },
};

describe('mountLaneA', () => {
  it('returns a commentary track that is safe to call before Stage 4', () => {
    const { commentary } = mountLaneA(ctx);
    commentary.pause();
    commentary.resume();
    expect(commentary.nextCueWithin(3)).toBe(false);
  });
});

describe('local listening-test commentary (?names=, D21)', () => {
  it('maps a safe stem to the dev-only path, and ignores anything else', () => {
    expect(localCommentaryBase('?names=liverpool-arsenal')).toBe('/replay/v1/local/liverpool-arsenal');
    expect(localCommentaryBase('?mix=1&names=liverpool-arsenal')).toBe('/replay/v1/local/liverpool-arsenal');
    expect(localCommentaryBase('')).toBeNull();
    expect(localCommentaryBase('?names=../judge')).toBeNull();
    expect(localCommentaryBase('?names=https://evil.example')).toBeNull();
  });
});
