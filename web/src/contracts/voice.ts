// What A's lane offers to B's code.
// Append-only after Wed 21 Oct 18:00 Sofia.
import type { LaneBContext } from './stage';

/** The pre-rendered commentary track (Stage 4). It loads cues.en.radio.jsonl itself; segments.json carries no cues. */
export interface CommentaryTrack {
  pause(): void;
  resume(): void;
  /** True if a commentary line starts within the next `s` seconds of the playhead (B's Ask uses it to wait). */
  nextCueWithin(s: number): boolean;
  /** Appended 27 Oct (D34): a line is playing or scheduled now. */
  isSpeaking?(): boolean;
}

/** What mountLaneA() hands back to B's main.ts. */
export interface LaneAHandle {
  commentary: CommentaryTrack;
  /** Appended 27 Oct (D27). Switch the commentary track and the live answers to a language ("bg"). Resolves false
   *  if the bundle has no track for it (the English track keeps playing). */
  setLanguage?(lang: string): Promise<boolean>;
  /** Appended 27 Oct (Tier 1): "key" plays only the lines with priority KEY_PRIORITY and up, "full" all of them. */
  setDetail?(detail: 'full' | 'key'): void;
  /** Appended 27 Oct (Tier 1): screen-reader mode. On: the AI voice is silent and onLine gets each line's text and
   *  language instead. Off (null): the voice speaks again. */
  setReader?(onLine: ((text: string, lang: string) => void) | null): void;
  /** Appended 27 Oct (D36): low-data mode, the 32 kbps commentary fetched just in time. Applies to lines not yet loaded. */
  setLowData?(on: boolean): void;
}

/** B's main.ts calls this once, and nothing else of A's. */
export type MountLaneA = (ctx: LaneBContext) => LaneAHandle;
