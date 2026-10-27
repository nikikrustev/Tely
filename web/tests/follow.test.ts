// D34: follow my player. Touches never run ahead of the playhead; the setting is checked.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { LocalTools, type QaBundle } from '../src/ask/local-tools';
import { prefsPatch, sanitize } from '../src/settings';

const J = new URL('../public/replay/v1/judge/', import.meta.url);
const read = (f: string) => readFileSync(new URL(f, J), 'utf8');
const bundle = {
  meta: JSON.parse(read('meta.json')),
  events: read('events.jsonl').trim().split('\n').map((l) => JSON.parse(l).event),
  signals: JSON.parse(read('signals.json')),
  ticks: { t0: 0, ball: { hz: 25, rows: [] } },
} as unknown as QaBundle;
const T = new LocalTools(bundle);

describe('follow my player', () => {
  it('finds each touch once, as actor or as receiver on arrival, and never one after the playhead', () => {
    const all = T.touches('n11', T.t0 - 1, T.t1 + 1);
    expect(all.length).toBeGreaterThanOrEqual(11);
    let seen: number[] = [];
    for (let p = T.t0; p <= T.t1; p += 0.25) {
      const got = T.touches('n11', p - 0.25, p);
      expect(got.every((t) => t <= p && t > p - 0.25)).toBe(true);
      seen = seen.concat(got);
    }
    expect(seen).toEqual(all.filter((t) => t > T.t0 - 0.25 && t <= T.t1));
  });

  it('is a saved setting and the commentator can set or clear it', () => {
    expect(sanitize({}).follow).toBeNull();
    expect(sanitize({ follow: 'n11' }).follow).toBe('n11');
    expect(sanitize({ follow: '<script>' }).follow).toBeNull();
    expect(prefsPatch({ follow: 'r4' })).toEqual({ follow: 'r4' });
    expect(prefsPatch({ follow: null })).toEqual({ follow: null });
    expect(prefsPatch({ haptics: 'off' })).toEqual({ haptics: 'off' });
  });
});
