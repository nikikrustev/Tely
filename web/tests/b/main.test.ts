// OWNER: B (Nikolay). Stub created by A in Stage 0.
import { describe, expect, it, vi } from 'vitest';

vi.mock('../../src/lane-a', () => ({
  mountLaneA: vi.fn(() => ({ commentary: { pause() {}, resume() {}, nextCueWithin: () => false } })),
}));

describe('boot', () => {
  it('mounts lane A exactly once with the lane-B context', async () => {
    const { mountLaneA } = await import('../../src/lane-a');
    const { boot, createStubContext } = await import('../../src/main');
    const ctx = createStubContext();
    boot(ctx);
    expect(mountLaneA).toHaveBeenCalledTimes(1);
    expect(mountLaneA).toHaveBeenCalledWith(ctx);
  });
});
