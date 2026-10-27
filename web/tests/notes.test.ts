// D33: the Director's notes never run ahead of the playhead, and carry no outcome.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { askText, due, noteText, type Note } from '../src/notes/notes';

const FILE = JSON.parse(readFileSync(new URL('../public/replay/v1/judge/director_notes.json', import.meta.url), 'utf8')) as {
  director: string; notes: Note[];
};
const OUTCOME = /\b(goal|scores?|scored|saved?|saves|wide|miss(ed)?|blocked|post|denied|woodwork|nets|stands)\b/i;

describe("Director's notes", () => {
  it('one note per Director window, each due only once its shot is revealed', () => {
    expect(FILE.notes.length).toBe(4);
    const first = FILE.notes[0] as Note;
    expect(due(FILE.notes, first.show_after - 0.01)).toEqual([]);
    expect(due(FILE.notes, first.show_after)).toEqual([first]);
    for (let p = 670; p <= 1150; p += 0.5) expect(due(FILE.notes, p).every((n) => n.show_after <= p)).toBe(true);
  });

  it('say the plan, the rules plan, the latency and the Verifier, and no outcome', () => {
    for (const n of FILE.notes) {
      const t = noteText(n, FILE.director);
      expect(t).toContain('Rules Director would have said');
      expect(t).toMatch(/truth check pass|No build-up line/);
      expect(t, t).not.toMatch(OUTCOME);
    }
    expect(noteText(FILE.notes[0] as Note, FILE.director)).toContain('level 0.62, lead 4.0 s, hold 300 ms, hint danger');
  });

  it('an Ask note names the tools and the time to the first answer audio', () => {
    expect(askText('57:02', { tools: ['get_score_and_clock'], latency_ms: 950 }))
      .toBe('57:02 Ask (Voice Live): get_score_and_clock; first answer audio 0.95 s after you stopped speaking.');
    expect(askText('57:02', { tools: [], latency_ms: null })).toBe('57:02 Ask (Voice Live): no tool.');
  });
});
