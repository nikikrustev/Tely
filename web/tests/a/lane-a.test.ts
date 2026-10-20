// OWNER: A (potencialbg).
import { describe, expect, it } from 'vitest';
import type { LaneBContext } from '../../src/contracts/b-exports';
import { mountLaneA } from '../../src/lane-a';

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
