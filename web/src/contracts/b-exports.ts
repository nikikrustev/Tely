// OWNER: B (Nikolay). Stub created by A in Stage 0 from TEAM_SPLIT.md "The seams" point 3.
// What B's code offers to A's lane. Append-only after Wed 21 Oct 18:00 Sofia.

/** The crowd mix bus. A's commentary and live Ask duck it while the commentator speaks. */
export interface CrowdBus {
  /** Lower the crowd by `db` (negative, e.g. -12) over `rampMs`. No abrupt gain jumps (setTargetAtTime). */
  duck(db: number, rampMs: number): void;
  /** Return the crowd to its normal level over `rampMs`. */
  unduck(rampMs: number): void;
}

/** A's live (Voice Live) question mode, as B's Ask button sees it. */
export interface LiveAskHandler {
  /** Start one spoken question at the listener's playhead. Resolves when the answer has finished playing. */
  ask(playheadS: number): Promise<void>;
  /** Stop listening or speaking now (the fan pressed Ask again, or the page is hidden). */
  cancel(): void;
}

/** B's Ask feature: offline presets by default; A registers the live mode when it is available. */
export interface Ask {
  registerLiveMode(handler: LiveAskHandler): void;
}

/** The replay clock: the one playhead everything follows (file 43 §2). Never ahead of what the listener hears. */
export interface ReplayClock {
  /** Playhead in match seconds. */
  now(): number;
  isPlaying(): boolean;
  /** Called on play, pause and seek. Returns an unsubscribe function. */
  onChange(listener: (playheadS: number, playing: boolean) => void): () => void;
}

/** Everything B's main.ts passes to mountLaneA(). */
export interface LaneBContext {
  crowd: CrowdBus;
  ask: Ask;
  clock: ReplayClock;
}
