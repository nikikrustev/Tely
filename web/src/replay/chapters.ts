// OWNER: B (Nikolay). "Next big moment": the chapter stops A's build_bundle writes into manifest.json (file 43 §6).
// Spoiler-safe by design (A's D11): every stop sits before a build-up or a card, named alike for a goal or a miss.
export interface Chapter { t: number; label: string }

/** The first chapter strictly after the playhead (with a small margin, so pressing twice moves on). */
export function nextChapter(chapters: Chapter[], playhead: number, marginS = 1): Chapter | null {
  return [...chapters].sort((a, b) => a.t - b.t).find((c) => c.t > playhead + marginS) ?? null;
}

// SEAM(B->A): reads manifest.json's `chapters`, written by A's build_bundle (contracts: replay bundle manifest)
export async function loadChapters(base = '/replay/v1/judge'): Promise<Chapter[]> {
  try {
    const m = (await (await fetch(`${base}/manifest.json`)).json()) as { chapters?: Chapter[] };
    return Array.isArray(m.chapters) ? m.chapters.filter((c) => typeof c.t === 'number') : [];
  } catch {
    return []; // no manifest: the button says there are no more big moments
  }
}
