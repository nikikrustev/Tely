// OWNER: B (Nikolay). Stage 6 (B5 part 2): the TypeScript tools say exactly what the Python tools say (golden cases),
// never use the future (200 random playheads), and the catch-up covers exactly what was revealed during the Ask.
import { readFileSync } from 'node:fs';
import { gunzipSync } from 'node:zlib';
import { describe, expect, it } from 'vitest';
import { LocalTools, pyRound, type Answer, type QaBundle } from '../../src/ask/local-tools';

const J = new URL('../../public/replay/v1/judge/', import.meta.url);
const read = (f: string) => readFileSync(new URL(f, J), 'utf8');
const bundle: QaBundle = {
  meta: JSON.parse(read('meta.json')),
  events: read('events.jsonl').trim().split('\n').map((l: string) => JSON.parse(l).event),
  signals: JSON.parse(read('signals.json')),
  ticks: JSON.parse(gunzipSync(readFileSync(new URL('ticks.json.gz', J))).toString('utf8')),
};
const T = new LocalTools(bundle);
const CASES = readFileSync(new URL('../../../contracts/golden/b/qa_cases.jsonl', import.meta.url), 'utf8')
  .trim().split('\n').map((l: string) => JSON.parse(l));

function run(c: { tool: string; args: Record<string, unknown>; playhead_s: number }): Answer | boolean | { error: string } {
  const p = c.playhead_s;
  switch (c.tool) {
    case 'get_score_and_clock': return T.get_score_and_clock(p);
    case 'get_ball_position': return T.get_ball_position(p);
    case 'get_last_events': return T.get_last_events(p, c.args.n as number);
    case 'what_did_i_miss': return T.what_did_i_miss(p, c.args.since as string);
    case 'catch_up': return T.catch_up(c.args.since_s as number, p);
    case 'hold_that_thought': return T.hold_that_thought(p);
    default: throw new Error(c.tool);
  }
}

describe('golden cases (contracts/golden/b/qa_cases.jsonl)', () => {
  it('TypeScript says exactly what Python says, in every case', () => {
    expect(CASES.length).toBeGreaterThan(200);
    for (const c of CASES) {
      const r = run(c);
      if (c.tool === 'hold_that_thought') { expect(r, JSON.stringify(c)).toBe(c.expected); continue; }
      const a = r as Answer;
      expect([a.say, a.fragments, a.evidence_ids], JSON.stringify(c)).toEqual([c.expected_say, c.expected_fragments, c.expected_evidence]);
    }
  });

  it("rounds halves like Python's round()", () => {
    expect([pyRound(2.5), pyRound(3.5), pyRound(2.4), pyRound(2.6), pyRound(7.5)]).toEqual([2, 4, 2, 3, 8]);
  });
});

describe('spoiler firewall in the browser', () => {
  it('across 200 random playheads, no answer uses an event after the playhead', () => {
    let seed = 42;
    const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 2 ** 32; };
    for (let i = 0; i < 200; i++) {
      const p = T.t0 + rnd() * (T.t1 - T.t0);
      const answers = [T.get_score_and_clock(p), T.get_ball_position(p), T.get_last_events(p, 5),
        T.what_did_i_miss(p, T.clockStr(T.t0)), T.catch_up(T.t0, p)];
      for (const a of answers) {
        for (const id of (a as Answer).evidence_ids ?? []) {
          const s = T.sig(id);
          expect(s.t, `${id} at ${p}`).toBeLessThanOrEqual(p + 1e-9);
          expect(s.reveal_t, `${id} at ${p}`).toBeLessThanOrEqual(p + 1e-9);
        }
      }
    }
  });

  it('the catch-up covers exactly the big moments revealed between the start and end of the Ask', () => {
    // Asked during the VAR check: the goal was struck (t 679.4) before the Ask but confirmed (reveal 703.76) during it.
    const start = 690, end = 730;
    const a = T.catch_up(start, end);
    const revealed = bundle.events.filter((e) => {
      const s = T.sig(e.id);
      return start < s.reveal_t && s.reveal_t <= end && s.priority >= 2;
    }).map((e) => e.id);
    const goal = bundle.events.find((e) => e.type === 'shot' && e.outcome_type === 'successful')!;
    expect(revealed).toContain(goal.id);                 // the window really holds the goal (not a vacuous check)
    expect(a.evidence_ids.length).toBeGreaterThan(0);
    expect(revealed).toEqual(expect.arrayContaining(a.evidence_ids));
    expect(a.evidence_ids).toContain(goal.id);
    expect(a.say).toMatch(/^Back to the action\. While we talked, .*scored/);
    const before = T.catch_up(start, 700);              // the goal is not revealed yet at 700: not mentioned
    expect(before.say).toBe('Back to the action.');
  });
});

// ---- the Ask flow (ask.ts) ----------------------------------------------------------------------------------------
import { AskController, LazyAsk, PRESETS } from '../../src/ask/ask';

function harness(start: number) {
  const log: string[] = [];
  let now = start;
  const ctl = new AskController({
    tools: T,
    clock: { now: () => now },
    crowd: { duck: (db) => { log.push(`duck ${db}`); }, unduck: () => { log.push('unduck'); } },
    commentary: { pause: () => { log.push('pause'); }, resume: () => { log.push('resume'); }, nextCueWithin: () => false },
    speak: async (_f, text) => { log.push(`say: ${text}`); now += 3; },   // each answer takes 3 s of match time
    ping: () => { log.push('ping'); },
    wait: async (ms) => { now += ms / 1000; },
  });
  return { ctl, log };
}

describe('Ask flow', () => {
  it('ducks the crowd and pauses the commentary, answers, catches up, then restores both', async () => {
    const quiet = 940;                                  // no chance due within 8 s here
    expect(T.hold_that_thought(quiet)).toBe(false);
    const { ctl, log } = harness(quiet);
    await ctl.ask('ball');
    expect(log[0]).toBe('pause');                       // A's pause() unducks, so pause first...
    expect(log[1]).toBe('duck -12');                    // ...then duck: the answer sits over a lowered crowd
    expect(log).toContain('ping');
    expect(log.filter((l) => l.startsWith('say:'))).toHaveLength(2);
    expect(log.at(-3)).toMatch(/^say: Back to the action\./);
    expect(log.slice(-2)).toEqual(['unduck', 'resume']);
  });

  it('says "hold that thought" first when a chance is coming, and never what it is', async () => {
    const p = T.b.events.map((e) => T.sig(e.id)).find((s) => s.xg !== null && s.xg >= 0.08)!.t - 5;
    expect(T.hold_that_thought(p)).toBe(true);
    const { ctl, log } = harness(p);
    const said = await ctl.ask('score');
    expect(said[0]).toBe('Hold that thought, watch this!');
    expect(log[0]).toBe('say: Hold that thought, watch this!');
  });

  it('ignores a second press while answering, and LazyAsk hands A\'s live mode to the controller', async () => {
    const { ctl } = harness(940);
    const a = ctl.ask('score');
    expect(await ctl.ask('ball')).toEqual([]);
    await a;
    const lazy = new LazyAsk();
    let asked = -1;
    lazy.registerLiveMode({ ask: async (p) => { asked = p; }, cancel: () => {} });
    lazy.attach(ctl);
    expect(ctl.hasLive).toBe(true);
    await ctl.askLive();
    expect(asked).toBe(946);                            // the playhead kept running through the first answer (2 x 3 s)
  });

  it('every preset answers from the data at the playhead', () => {
    const { ctl } = harness(940);
    for (const pr of PRESETS) expect(ctl.answer(pr.id, 940).say.length).toBeGreaterThan(5);
  });
});

describe('Ask button (index.html)', () => {
  const html = readFileSync(new URL('../../index.html', import.meta.url), 'utf8');
  it('is a native button with an accessible name and the A shortcut, and every preset is a native button', () => {
    expect(html).toMatch(/<button id="ask" type="button"[^>]*aria-keyshortcuts="A"[^>]*>\s*Ask the commentator\s*<\/button>/);
    expect(html).toMatch(/aria-controls="ask-menu"/);
    for (const p of PRESETS) expect(html).toContain(`data-preset="${p.id}">${p.label.replace("'", "'")}</button>`);
  });
});
