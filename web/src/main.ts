// OWNER: B (Nikolay). Stub created by A in Stage 0: builds no-op lane-B services and mounts lane A once.
import type { LaneAHandle } from './contracts/a-exports';
import type { LaneBContext } from './contracts/b-exports';
import { mountLaneA } from './lane-a';

/** Placeholder services until B's audio/, ask/ and replay/ modules exist. */
export function createStubContext(): LaneBContext {
  return {
    crowd: { duck() {}, unduck() {} },
    ask: { registerLiveMode() {} },
    clock: { now: () => 0, isPlaying: () => false, onChange: () => () => {} },
  };
}

export function boot(ctx: LaneBContext = createStubContext()): LaneAHandle {
  // SEAM(B->A): the only call into A's lane (TEAM_SPLIT.md "The seams" point 3).
  return mountLaneA(ctx);
}

if (typeof document !== 'undefined') {
  boot();
  const status = document.getElementById('status');
  if (status) status.textContent = 'Ready. Audio starts when you press Play.';
}
