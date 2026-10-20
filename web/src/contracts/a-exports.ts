// OWNER: A (potencialbg). What A's lane offers to B's code (TEAM_SPLIT.md "The seams" point 3).
// Append-only after Wed 21 Oct 18:00 Sofia.
import type { LaneBContext } from './b-exports';

/** The pre-rendered commentary track (Stage 4). It loads cues.en.radio.jsonl itself; segments.json carries no cues. */
export interface CommentaryTrack {
  pause(): void;
  resume(): void;
  /** True if a commentary line starts within the next `s` seconds of the playhead (B's Ask uses it to wait). */
  nextCueWithin(s: number): boolean;
}

/** What mountLaneA() hands back to B's main.ts. */
export interface LaneAHandle {
  commentary: CommentaryTrack;
}

/** B's main.ts calls this once, and nothing else of A's. */
export type MountLaneA = (ctx: LaneBContext) => LaneAHandle;
