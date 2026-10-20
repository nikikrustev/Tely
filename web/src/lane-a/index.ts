// OWNER: A (potencialbg). Entry point for A's browser code. A no-op until Stage 4 (commentary-track.ts)
// and Stage 7 (live-ask.ts) land here.
import type { CommentaryTrack, LaneAHandle, MountLaneA } from '../contracts/a-exports';

const silentTrack: CommentaryTrack = {
  pause() {},
  resume() {},
  nextCueWithin: () => false,
};

// SEAM(A->B): B's main.ts calls this once with LaneBContext (crowd bus, Ask, replay clock).
export const mountLaneA: MountLaneA = (_ctx): LaneAHandle => ({ commentary: silentTrack });
