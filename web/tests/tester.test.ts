// Tester mode (?test=1, D19): task flow, group assignment, probe scoring against
// eval/listening_test.md section 5, storage that throws, and the outbox's one retry. Pure logic; the DOM is covered
// by tests/tester.spec.ts (Playwright + axe).
import { describe, expect, it } from 'vitest';
import { deliver, feedbackUrl, RETRY_AFTER_MS, type Transport } from '../src/tester/outbox';
import { answersText, baseEvent, codeLine, fit, MAX_BYTES, uaFamily } from '../src/tester/payload';
import { KEY, PROBES, scoreClip } from '../src/tester/questions';
import {
  clipFor, commentaryOnly, freshState, groupFor, loadState, newTesterId, nextTask, progress, saveState, setTask,
  STORAGE_KEY, TASKS, type StorageLike, type TesterState,
} from '../src/tester/state';

const throwing: StorageLike = {
  getItem() { throw new DOMException('denied', 'SecurityError'); },
  setItem() { throw new DOMException('full', 'QuotaExceededError'); },
};
function memory(): StorageLike & { data: Map<string, string> } {
  const data = new Map<string, string>();
  return { data, getItem: (k) => data.get(k) ?? null, setItem: (k, v) => { data.set(k, v); } };
}

describe('task flow', () => {
  it('has the eight tasks in order, with the clips and their questions paired', () => {
    expect(TASKS.map((t) => t.kind)).toEqual(['tour', 'clip', 'questions', 'clip', 'questions', 'ask', 'settings', 'overall']);
    expect(TASKS.filter((t) => t.clip).map((t) => [t.id, t.clip])).toEqual([[2, 1], [3, 1], [4, 2], [5, 2]]);
    expect(TASKS.reduce((m, t) => m + t.minutes, 0)).toBe(15);   // the welcome screen promises about 15 minutes
  });

  it('moves to the next task still to do, wraps round, and ends when all are done or skipped', () => {
    let s = freshState('t-00000000');
    expect(nextTask(s)?.id).toBe(1);
    s = setTask(s, 1, 'done');
    s = setTask(s, 2, 'skip');
    expect(nextTask(s, 2)?.id).toBe(3);
    expect(nextTask(s, 8)?.id).toBe(3);                         // wraps to the first one left
    expect(progress(s)).toEqual({ finished: 2, total: 8 });
    for (const t of TASKS) s = setTask(s, t.id, 'done');
    expect(nextTask(s)).toBeNull();
  });
});

describe('group assignment (section 1 counterbalancing)', () => {
  it('comes from the random ID: even last digit A, odd B', () => {
    expect(groupFor('t-0000000a')).toBe('A');
    expect(groupFor('t-0000000b')).toBe('B');
    expect(freshState('t-12345671').group).toBe('B');
  });

  it('is roughly balanced over many random IDs, and IDs are anonymous hex', () => {
    const ids = Array.from({ length: 2000 }, () => newTesterId());
    expect(ids.every((id) => /^t-[0-9a-f]{8}$/.test(id))).toBe(true);
    const b = ids.filter((id) => groupFor(id) === 'B').length;
    expect(b).toBeGreaterThan(850);
    expect(b).toBeLessThan(1150);
  });

  it('gives group A commentary-only Clip 1 and full Clip 2, and group B the reverse, at the kit times', () => {
    expect(clipFor('A', 1)).toEqual({ from: 670, to: 850, commentaryOnly: true });
    expect(clipFor('A', 2)).toEqual({ from: 970, to: 1150, commentaryOnly: false });
    expect(clipFor('B', 1)).toEqual({ from: 670, to: 850, commentaryOnly: false });
    expect(clipFor('B', 2)).toEqual({ from: 970, to: 1150, commentaryOnly: true });
    expect([commentaryOnly('A', 1), commentaryOnly('B', 1)]).toEqual([true, false]);
  });
});

describe('probe scoring against the answer key (section 5)', () => {
  it('scores the key answers 1', () => {
    expect(scoreClip(1, { where: 'left_close', side: 'far', danger: 'navy', scored: 'navy' }))
      .toEqual({ where_ok: 1, side_ok: 1, danger_ok: 1, scored_ok: 1 });
    expect(scoreClip(2, { where: 'right_close', side: 'middle', danger: 'reds', scored: 'nobody' }))
      .toEqual({ where_ok: 1, side_ok: 1, danger_ok: 1, scored_ok: 1 });
  });

  it('accepts the Navy shot in Clip 2 as the alternative the key allows', () => {
    expect(scoreClip(2, { where: 'left_far', side: 'far', danger: 'both', scored: 'nobody' }))
      .toEqual({ where_ok: 1, side_ok: 1, danger_ok: 1, scored_ok: 1 });
  });

  it("scores wrong, missing and \"don't know\" as 0", () => {
    expect(scoreClip(1, { where: 'right_close', side: 'dont_know', danger: 'both' }))
      .toEqual({ where_ok: 0, side_ok: 0, danger_ok: 0, scored_ok: 0 });
    expect(scoreClip(2, { scored: 'navy', danger: 'no' })).toEqual({ where_ok: 0, side_ok: 0, danger_ok: 0, scored_ok: 0 });
  });

  it('only keys choices that exist, and every probe offers "Don\'t know"', () => {
    for (const p of PROBES) {
      const ids = p.choices.map(([id]) => id);
      expect(ids).toContain('dont_know');
      for (const clip of [1, 2] as const) for (const k of KEY[clip][p.id]) expect(ids).toContain(k);
      for (const clip of [1, 2] as const) expect(KEY[clip][p.id]).not.toContain('dont_know');
    }
  });
});

describe('storage', () => {
  it('works when storage throws: a fresh state in memory, and save reports false', () => {
    const s = loadState(throwing);
    expect(s.id).toMatch(/^t-[0-9a-f]{8}$/);
    expect(saveState(s, throwing)).toBe(false);
    expect(saveState(s, null)).toBe(false);
    expect(loadState(null).consent).toBeNull();
  });

  it('keeps the ID, group, progress and answers across visits', () => {
    const mem = memory();
    let s = freshState('t-abcdef01');
    s = { ...setTask(s, 1, 'done'), consent: { takePart: true, quote: true } };
    s.answers.clips[1] = { probes: { where: 'left_close' }, scale: { enjoy: 4 } };
    s.events.push({ ev: baseEvent(s, 'task', '00000001'), status: 'unsent' });
    expect(saveState(s, mem)).toBe(true);
    const back = loadState(mem);
    expect([back.id, back.group, back.tasks[1], back.consent]).toEqual(['t-abcdef01', 'B', 'done', { takePart: true, quote: true }]);
    expect(back.answers.clips[1]?.scale.enjoy).toBe(4);
    expect(back.events[0]?.status).toBe('unsent');
  });

  it('starts fresh on broken or foreign data instead of failing', () => {
    const mem = memory();
    mem.data.set(STORAGE_KEY, '{not json');
    expect(loadState(mem).consent).toBeNull();
    mem.data.set(STORAGE_KEY, JSON.stringify({ v: 1, id: 'Nikolay', tasks: {} }));
    expect(loadState(mem).id).toMatch(/^t-[0-9a-f]{8}$/);
    mem.data.set(STORAGE_KEY, JSON.stringify({ v: 1, id: 't-00000002', tasks: { 1: 'hacked', 2: 'done' } }));
    expect(loadState(mem).tasks).toMatchObject({ 1: 'todo', 2: 'done' });
  });
});

describe('payload', () => {
  it('fits three long Cyrillic answers into the relay limit, trimming text only', () => {
    const s = { ...freshState('t-00000003'), consent: { takePart: true, quote: false } };
    const long = 'Ж'.repeat(800);
    const ev = fit({ ...baseEvent(s, 'overall', '0000000f'), confusing: long, liked: `  ${long}  `, would_use: '😀'.repeat(500), device: 'iphone' });
    expect(new TextEncoder().encode(JSON.stringify(ev)).length).toBeLessThanOrEqual(MAX_BYTES);
    expect(ev).toMatchObject({ v: 1, kind: 'overall', tester: 't-00000003', device: 'iphone', consent_take_part: true });
    expect((ev.confusing as string).length).toBeLessThanOrEqual(500);
  });

  it('reads only the browser and OS family from the user agent', () => {
    expect(uaFamily('Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/25.0 Chrome/121.0 Mobile Safari/537.36'))
      .toEqual({ browser: 'samsung', os: 'android' });
    expect(uaFamily('Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1'))
      .toEqual({ browser: 'safari', os: 'ios' });
    expect(uaFamily('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36 Edg/141.0'))
      .toEqual({ browser: 'edge', os: 'windows' });
    expect(uaFamily('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15', 5).os).toBe('ios');
  });

  it('never shows the score or the group in "Copy my answers", but keeps them in the code line', () => {
    let s: TesterState = { ...freshState('t-0000000b'), consent: { takePart: true, quote: false } };
    s.answers.clips[1] = { probes: { where: 'left_close', side: 'far' }, scale: { enjoy: 5 } };
    s.events.push({ ev: { ...baseEvent(s, 'clip', '00000010'), clip: 1, where: 'left_close', where_ok: 1 }, status: 'unsent' });
    s = setTask(s, 2, 'done');
    const text = answersText(s);
    expect(text).toContain('Close to the goal at the left end');
    const code = codeLine(s);
    const readable = text.replace(code, '');
    expect(readable).not.toMatch(/_ok|group|commentary only|full sound|right|wrong|correct/i);
    expect(text).toContain(code);
    const json = new TextDecoder().decode(Uint8Array.from(atob(code.slice(4)), (c) => c.charCodeAt(0)));
    expect(JSON.parse(json)[0]).toMatchObject({ where_ok: 1, group: 'B' });
  });
});

describe('outbox: keepalive POST, one retry after 30 s, never lost', () => {
  function transport(results: (number | Error)[]): Transport & { calls: number; waits: number[] } {
    const t = {
      calls: 0, waits: [] as number[],
      async post() { const r = results[t.calls++]; if (r instanceof Error) throw r; return r ?? 500; },
      async wait(ms: number) { t.waits.push(ms); },
    };
    return t;
  }

  it('sends once when the relay answers', async () => {
    const t = transport([202]);
    expect(await deliver('https://relay/feedback', '{}', t)).toBe('sent');
    expect([t.calls, t.waits]).toEqual([1, []]);
  });

  it('retries once after 30 s on a network error or a cold relay', async () => {
    const t = transport([new TypeError('Failed to fetch'), 202]);
    expect(await deliver('https://relay/feedback', '{}', t)).toBe('sent');
    expect(t.waits).toEqual([RETRY_AFTER_MS]);
    expect(RETRY_AFTER_MS).toBe(30_000);
  });

  it('keeps the event as unsent after two failures, and does not retry what the relay refused', async () => {
    const twice = transport([503, new TypeError('offline')]);
    expect(await deliver('https://relay/feedback', '{}', twice)).toBe('unsent');
    expect(twice.calls).toBe(2);
    const refused = transport([400]);
    expect(await deliver('https://relay/feedback', '{}', refused)).toBe('unsent');
    expect(refused.calls).toBe(1);
    expect(await deliver(null, '{}', transport([]))).toBe('unsent');   // no relay (local preview, ?live=0)
  });

  it("derives /feedback from lane A's /voice URL", () => {
    expect(feedbackUrl('wss://ca-relay.example.io/voice')).toBe('https://ca-relay.example.io/feedback');
    expect(feedbackUrl('ws://localhost:8080/voice')).toBe('http://localhost:8080/feedback');
    expect(feedbackUrl(null)).toBeNull();
  });
});
