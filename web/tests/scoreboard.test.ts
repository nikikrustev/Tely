// The match card's clock, chapter and score text.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { currentChapter, matchClock, parseClock, Scoreboard } from '../src/scoreboard';

const J = new URL('../public/replay/v1/judge/', import.meta.url);
const MANIFEST = JSON.parse(readFileSync(new URL('manifest.json', J), 'utf8')) as {
  clock_start: string; t_start: number; chapters: { t: number; label: string }[];
};

describe('match clock', () => {
  it('parses mm:ss and rejects anything else', () => {
    expect(parseClock('56:10')).toBe(3370);
    expect(parseClock('45:00.00')).toBe(2700);
    expect(parseClock('5610')).toBeNull();
    expect(parseClock(undefined)).toBeNull();
  });

  it("reads the bundle's own clock at the start of the judge cut", () => {
    const offset = parseClock(MANIFEST.clock_start)! - MANIFEST.t_start;
    expect(matchClock(MANIFEST.t_start, offset)).toBe(MANIFEST.clock_start);
    expect(matchClock(MANIFEST.t_start + 59.9, offset)).toBe('57:09');
  });
});

describe('current chapter', () => {
  const ch = MANIFEST.chapters;
  const at = (i: number) => ch[i]!;
  it('is the last chapter at or before the playhead, counted against the total', () => {
    expect(currentChapter(ch, at(0).t - 5)).toBeNull();
    expect(currentChapter(ch, at(0).t)).toEqual({ label: at(0).label, n: 1, of: ch.length });
    expect(currentChapter(ch, at(1).t + 30)?.n).toBe(2);
  });

  it('never names a chapter ahead of the playhead (spoiler-safe, D11)', () => {
    for (let t = at(0).t; t < at(ch.length - 1).t + 60; t += 7) {
      const c = currentChapter(ch, t)!;
      expect(ch.find((x) => x.label === c.label)!.t).toBeLessThanOrEqual(t + 0.5);
    }
  });
});

describe('Scoreboard', () => {
  const fakeRoot = () => {
    const t = () => ({ textContent: '' });
    const els = { home: t(), away: t(), clock: t(), chapter: t(), state: t() };
    const root = { querySelector: (sel: string) => els[/data-sb="(\w+)"/.exec(sel)![1] as keyof typeof els] } as unknown as ParentNode;
    return { root, els };
  };

  it('writes the score, clock, chapter and state', () => {
    const { root, els } = fakeRoot();
    const b = new Scoreboard(root);
    b.chapters = MANIFEST.chapters;
    b.offsetS = 2700;
    const c1 = MANIFEST.chapters[1]!;
    b.update({ score: { home: 1, away: 0 }, playheadS: c1.t + 1, state: 'Playing' });
    expect(Object.fromEntries(Object.entries(els).map(([k, v]) => [k, v.textContent]))).toEqual({
      home: '1', away: '0', clock: matchClock(c1.t + 1, 2700),
      chapter: `${c1.label} of ${MANIFEST.chapters.length}`, state: 'Playing',
    });
  });

  it('leaves what it was not given alone', () => {
    const { root, els } = fakeRoot();
    els.chapter.textContent = 'Second half';
    new Scoreboard(root).update({ playheadS: 0 });   // no chapters yet
    expect(els.chapter.textContent).toBe('Second half');
    expect(els.home.textContent).toBe('');
  });
});
