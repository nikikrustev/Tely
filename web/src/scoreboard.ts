// The match-state card: score, match clock, current chapter.
// Visual for sighted judges; a screen-reader user can read it on demand, but it is NOT a live region: the clock ticks
// every second and would drown the match (file 32). Score changes are announced once by main.ts's say().
import type { Chapter } from './replay/chapters';
import { bundleBase } from './replay/base';

/** "56:10" -> 3370. Null for anything that isn't mm:ss. */
export function parseClock(s: string | undefined): number | null {
  const m = /^(\d+):(\d{2})(?:\.\d+)?$/.exec(s?.trim() ?? '');
  return m ? Number(m[1]) * 60 + Number(m[2]) : null;
}

/** Match clock for a playhead: offsetS is the clock at playhead 0 (45:00 for a second-half bundle). */
export function matchClock(playheadS: number, offsetS: number): string {
  const total = Math.max(0, Math.floor(offsetS + playheadS));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`;
}

/** The chapter the playhead is in (the last one at or before it), or null before the first. */
export function currentChapter(chapters: Chapter[], playheadS: number): { label: string; n: number; of: number } | null {
  const sorted = [...chapters].sort((a, b) => a.t - b.t);
  let n = 0;
  for (const c of sorted) if (c.t <= playheadS + 0.5) n++;
  return n ? { label: sorted[n - 1]!.label, n, of: sorted.length } : null;
}

export interface ScoreState { score?: { home: number; away: number }; playheadS?: number; state?: string }

/** Writes into the #match card in index.html. Only touches text that changed, so the card never re-renders. */
export class Scoreboard {
  private els: Record<'home' | 'away' | 'clock' | 'chapter' | 'state', HTMLElement>;
  chapters: Chapter[] = [];
  /** Clock at playhead 0; manifest.json's clock_start minus t_start once it loads. */
  offsetS = 45 * 60;

  constructor(root: ParentNode) {
    const q = (sel: string) => root.querySelector<HTMLElement>(sel)!;
    this.els = { home: q('[data-sb="home"]'), away: q('[data-sb="away"]'), clock: q('[data-sb="clock"]'),
      chapter: q('[data-sb="chapter"]'), state: q('[data-sb="state"]') };
  }

  update(s: ScoreState): void {
    if (s.score) { this.set('home', String(s.score.home)); this.set('away', String(s.score.away)); }
    if (s.playheadS !== undefined) {
      this.set('clock', matchClock(s.playheadS, this.offsetS));
      const ch = currentChapter(this.chapters, s.playheadS);
      if (ch) this.set('chapter', `${ch.label} of ${ch.of}`);
    }
    if (s.state) this.set('state', s.state);
  }

  private set(k: keyof Scoreboard['els'], text: string): void {
    if (this.els[k].textContent !== text) this.els[k].textContent = text;
  }
}

/** Clock at playhead 0 from manifest.json (clock_start is the clock at t_start). Null if it can't be read. */
export async function loadClockOffset(base = bundleBase()): Promise<number | null> {
  try {
    const m = (await (await fetch(`${base}/manifest.json`)).json()) as { clock_start?: string; t_start?: number };
    const c = parseClock(m.clock_start);
    return c !== null && typeof m.t_start === 'number' ? c - m.t_start : null;
  } catch {
    return null; // keep the 45:00 second-half default
  }
}
