// TypeScript copies of the offline Q&A tools (pipeline/tely/qa/tools.py), so presets work
// with no backend. Every tool reads the match only up to the local playhead: an event counts once
// its outcome is revealed (reveal_t), and the ball is read at the playhead. pipeline/tests/golden/qa_cases.jsonl holds
// the Python answers; vitest checks these give exactly the same `say`, fragments and evidence.
import { bundleBase } from '../replay/base';

export interface QaEvent {
  id: string;
  type: string;
  sub_type: string | null;
  outcome_type: string;
  related_event_ids: string[] | null;
  [k: string]: unknown;
}
export interface EventSignal {
  t: number; reveal_t: number; xg: number | null; priority: number; spoken: string; spoken_past: string;
}
export interface QaBundle {
  meta: { judge_cut: { t_start: number; t_end: number }; periods: { clock_start: string }[];
          teams: Record<'home' | 'away', { short_name: string; attacks: string }> };
  events: QaEvent[];
  signals: { per_second: { t: number; score: { home: number; away: number } }[]; events: Record<string, EventSignal> };
  ticks: { t0: number; ball: { hz: number; rows: [number, number, number, number, string | null][] } };
}
export interface Answer { say: string; evidence_ids: string[]; as_of_clock: string; fragments: string[] | null; x?: number; y?: number }

const HALF_L = 52.5;
export const RECAP_MAX = 6;   // tools.py RECAP_MAX: the latest six big moments, so a recap stays under about 20 s
const NUM = ['nil', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'];
const THIRD_WORDS: Record<string, string> = { defensive_third: 'defensive third', middle_third: 'midfield', attacking_third: 'attacking third' };
const SIDE_WORDS: Record<string, string> = { near: 'near side', centre: 'centre', far: 'far side' };
// Same texts as STATIC in pipeline/tely/qa/fragments.py (the golden cases catch any drift).
export const STATIC: Record<string, string> = {
  hold: 'Hold that thought, watch this!',
  back: 'Back to the action.',
  while_we_talked: 'While we talked,',
  while_away: 'While you were away,',
  and: 'and',
  then: 'Before that:',
  ball_out: 'The ball is out of play.',
  nothing_yet: 'Nothing big has happened yet.',
  recap: "Here's the story so far.",
  recap_ht: "That's half-time. Here's the story of the half.",
  recap_end: "That's the end of this part of the match. Here's how it went.",
  nothing_missed: 'Nothing big happened.',
  no_spoilers: "I can't tell you what happens next. That's for the match to decide.",
  no_betting: "I can't help with betting or odds. Ask me about the match instead.",
  off_topic: "I'm just here for the match. Ask me about the score, the ball, or what just happened.",
  not_sure: "Sorry, I didn't catch that. Try: what's the score, or where's the ball.",
  done: 'Done.',
};
export const HOLD_LOOKAHEAD_S = 8, HOLD_MIN_XG = 0.08;

type Part = [string, string];

/** Python's round(): halves go to the even neighbour (2.5 -> 2), unlike Math.round. */
export function pyRound(x: number): number {
  const f = Math.floor(x), d = x - f;
  if (d > 0.5) return f + 1;
  if (d < 0.5) return f;
  return f % 2 === 0 ? f : f + 1;
}

export class LocalTools {
  constructor(readonly b: QaBundle) {}

  get t0(): number { return this.b.meta.judge_cut.t_start; }
  get t1(): number { return this.b.meta.judge_cut.t_end; }
  clamp(p: number): number { return Math.min(Math.max(p, this.t0), this.t1); }
  private get offset(): number {
    const [mm, ss] = (this.b.meta.periods[0]?.clock_start ?? '00:00').split(':');
    return Number(mm) * 60 + Math.trunc(Number(ss));
  }
  clockS(p: number): number { return this.offset + p; }
  clockStr(p: number): string {
    const c = Math.trunc(this.clockS(this.clamp(p)));
    return `${String(Math.floor(c / 60)).padStart(2, '0')}:${String(c % 60).padStart(2, '0')}`;
  }
  parseClock(mmss: string): number | null {
    const m = /^\s*(\d+):(\d+(?:\.\d+)?)\s*$/.exec(mmss);
    return m ? Number(m[1]) * 60 + Number(m[2]) - this.offset : null;
  }
  sig(id: string): EventSignal { return this.b.signals.events[id] as EventSignal; }
  /** D34: the times in (from, to] when player pid gets the ball: as the actor of an event at its time, or as the
   *  receiver of a pass when it arrives (reveal_t). Never ahead of `to`, so a follow cue can't give anything away. */
  touches(pid: string, from: number, to: number): number[] {
    const out: number[] = [];
    for (const e of this.b.events) {
      const s = this.sig(e.id);
      if (e.player_id === pid && s.t > from && s.t <= to) out.push(s.t);
      if (e.receiver_id === pid && e.outcome_type === 'successful' && s.reveal_t > from && s.reveal_t <= to) out.push(s.reveal_t);
    }
    return out.sort((a, b) => a - b);
  }
  team(side: 'home' | 'away'): string { return this.b.meta.teams[side].short_name; }
  private attacks(side: 'home' | 'away'): number { return this.b.meta.teams[side].attacks === '+x' ? 1 : -1; }
  known(p: number): QaEvent[] { return this.b.events.filter((e) => this.sig(e.id).reveal_t <= p); }
  private score(p: number) {
    const rows = this.b.signals.per_second;
    const i = Math.min(Math.max(Math.floor(this.clamp(p) - (rows[0]?.t ?? 0)), 0), rows.length - 1);
    return (rows[i] as (typeof rows)[number]).score;
  }
  ball(p: number) {
    const b = this.b.ticks.ball;
    const k = Math.min(Math.max(Math.floor((this.clamp(p) - this.b.ticks.t0) * b.hz), 0), b.rows.length - 1);
    const [x, y, z, alive, poss] = b.rows[k] as QaBundle['ticks']['ball']['rows'][number];
    return { x, y, z, alive: alive === 1, poss: poss as 'home' | 'away' | null };
  }

  private ok(p: number, parts: Part[], say?: string, evidence: string[] = [], extra: Partial<Answer> = {}): Answer {
    return { say: say ?? parts.map(([, t]) => t).join(' '), evidence_ids: evidence, as_of_clock: this.clockStr(p),
             fragments: parts.map(([i]) => i), ...extra };
  }
  private st(key: string): Part { return [key, STATIC[key] as string]; }

  // ---- the offline tools (same names and answers as tools.py) ---------------------------------------------
  get_score_and_clock(playhead: number): Answer {
    const p = this.clamp(playhead), sc = this.score(p);
    const minute = Math.floor(this.clockS(p) / 60);
    const num = (n: number) => NUM[n] ?? String(n);
    // Same second as the score row: a goal revealed at 703.76 counts from 704 (never contradicts "nil").
    const goals = this.known(Math.floor(p)).filter((e) => e.type === 'shot' && e.outcome_type === 'successful').map((e) => e.id);
    return this.ok(p, [[`score_m${minute}_${sc.home}_${sc.away}`,
      `${this.team('home')} ${num(sc.home)}, ${this.team('away')} ${num(sc.away)}, ${minute} minutes played.`]], undefined, goals);
  }

  get_ball_position(playhead: number): Answer {
    const p = this.clamp(playhead), ball = this.ball(p), known = this.known(p);
    const ev = known.length ? [(known[known.length - 1] as QaEvent).id] : [];
    if (!ball.alive || !ball.poss) return this.ok(p, [this.st('ball_out')], undefined, ev, { x: ball.x, y: ball.y });
    const side = ball.poss, ax = ball.x * this.attacks(side);
    const third = ax < -17.5 ? 'defensive_third' : ax < 17.5 ? 'middle_third' : 'attacking_third';
    const s = ball.y < -11.33 ? 'near' : ball.y > 11.33 ? 'far' : 'centre';
    const d = Math.hypot(HALF_L * this.attacks(side) - ball.x, ball.y);
    const m = Math.trunc(Math.min(100, Math.max(0, 5 * pyRound(d / 5))));
    const key = side === 'home' ? 'H' : 'A';
    return this.ok(p, [
      [`zone_${key}_${third}_${s}`, `${this.team(side)} have it, ${THIRD_WORDS[third]}, ${SIDE_WORDS[s]}.`],
      [`dist_${String(m).padStart(3, '0')}`, m === 0 ? 'On the goal line.' : `${m} metres from goal.`],
    ], undefined, ev, { x: ball.x, y: ball.y });
  }

  /** Half-time, the end, or "so far": the score, then each big moment revealed by the playhead, in time order (a shot
   *  and its save once, the latest RECAP_MAX). Same fragments and words as tools.py get_recap. */
  get_recap(playhead: number, moment: 'so_far' | 'half_time' | 'end' = 'so_far'): Answer {
    const p = this.clamp(playhead);
    const lead = moment === 'half_time' ? 'recap_ht' : moment === 'end' ? 'recap_end' : 'recap';
    const big = this.b.events.filter((e) => this.sig(e.id).reveal_t <= p && this.sig(e.id).priority >= 2)
      .sort((a, b) => this.sig(a.id).t - this.sig(b.id).t);
    let keep: QaEvent[] = [];
    for (const e of big) {
      if (e.type === 'goalkeeping' && keep.some((k) => (e.related_event_ids ?? []).includes(k.id))) continue;
      keep.push(e);
    }
    keep = keep.slice(-RECAP_MAX);
    const score = this.get_score_and_clock(p);
    const scorePart: Part = [score.fragments?.[0] as string, score.say];
    const events: Part[] = keep.map((e) => [`past_${e.id}`, this.sig(e.id).spoken_past]);
    const parts: Part[] = [this.st(lead), scorePart, ...(events.length ? events : [this.st('nothing_yet')])];
    const say = `${parts[0]?.[1]} ${scorePart[1]} ${parts.slice(2).map(([, t]) => t.replace(/\.$/, '')).join('. ')}.`;
    return this.ok(p, parts, say, keep.map((e) => e.id));
  }

  get_last_events(playhead: number, n = 3): Answer {
    const p = this.clamp(playhead);
    const k = Math.max(1, Math.min(Math.trunc(n), 5));
    const ev = this.known(p).filter((e) => this.sig(e.id).priority >= 1).slice(-k).reverse();
    if (!ev.length) return this.ok(p, [this.st('nothing_yet')]);
    const parts: Part[] = [];
    ev.forEach((e, i) => { if (i) parts.push(this.st('then')); parts.push([`ev_${e.id}`, this.sig(e.id).spoken]); });
    return this.ok(p, parts, undefined, ev.map((e) => e.id));
  }

  /** Big moments whose outcome was revealed in (since, until]; top 2, a shot and its save said once.
   *  Filter on reveal_t, not the start: a goal confirmed by VAR during the Ask is news. */
  missed(since: number, until: number): QaEvent[] {
    const m = this.b.events.filter((e) => {
      const s = this.sig(e.id);
      return since < s.reveal_t && s.reveal_t <= until && s.priority >= 2;
    });
    const order = [...m].sort((a, b) => this.sig(b.id).priority - this.sig(a.id).priority || this.sig(a.id).t - this.sig(b.id).t);
    const top: QaEvent[] = [];
    for (const e of order) {
      if (e.type === 'goalkeeping' && top.some((t) => (e.related_event_ids ?? []).includes(t.id))) continue;
      top.push(e);
      if (top.length === 2) break;
    }
    return top.sort((a, b) => this.sig(a.id).t - this.sig(b.id).t);
  }

  private missedParts(lead: string, ev: QaEvent[]): Part[] {
    const parts: Part[] = [this.st(lead)];
    ev.forEach((e, i) => { if (i) parts.push(this.st('and')); parts.push([`past_${e.id}`, this.sig(e.id).spoken_past]); });
    return parts;
  }

  what_did_i_miss(playhead: number, since: string): Answer | { error: string; candidates: string[] } {
    const p = this.clamp(playhead), s = this.parseClock(since);
    if (s === null) return { error: 'bad_time', candidates: [this.clockStr(Math.max(this.t0, p - 60))] };
    const ev = this.missed(s, p);
    if (!ev.length) return this.ok(p, [this.st('nothing_missed')]);
    const parts = this.missedParts('while_away', ev);
    return this.ok(p, parts, parts.map(([, t]) => t).join(' ') + '.', ev.map((e) => e.id));
  }

  /** "Back to the action" + what was revealed while the fan was asking (file 40 catch_up_line). */
  catch_up(sinceS: number, untilS: number): Answer {
    const until = this.clamp(untilS), ev = this.missed(sinceS, until);
    if (!ev.length) return this.ok(until, [this.st('back')]);
    const parts = [this.st('back'), ...this.missedParts('while_we_talked', ev)];
    return this.ok(until, parts, parts.map(([, t]) => t).join(' ') + '.', ev.map((e) => e.id));
  }

  /** True if a chance is about to come (a build-up is due within ~4 s). Says THAT, never WHAT. */
  hold_that_thought(playhead: number): boolean {
    const p = this.clamp(playhead);
    return this.b.events.some((e) => {
      const s = this.sig(e.id);
      return e.type === 'shot' && p < s.t && s.t <= p + HOLD_LOOKAHEAD_S && (s.xg ?? 0) >= HOLD_MIN_XG;
    });
  }
}

/** Load the judge-cut bundle in the browser (static files only; ticks are gzip, decompressed natively). */
export async function loadQaBundle(base = bundleBase()): Promise<QaBundle> {
  const get = async (f: string) => {
    const r = await fetch(`${base}/${f}`);
    if (!r.ok) throw new Error(`${f}: HTTP ${r.status}`);
    return r;
  };
  const [meta, eventsTxt, signals, ticksRes] = await Promise.all([
    get('meta.json').then((r) => r.json()), get('events.jsonl').then((r) => r.text()), get('signals.json').then((r) => r.json()),
    get('ticks.json.gz')]);
  // Static Web Apps serves .gz as raw application/gzip bytes (A's D11); a dev server may already have unzipped it
  // (Content-Encoding: gzip). Unzip only if the bytes really start with the gzip magic number 1f 8b.
  const bytes = new Uint8Array(await ticksRes.arrayBuffer());
  const ticksText = bytes[0] === 0x1f && bytes[1] === 0x8b
    ? await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).text()
    : new TextDecoder().decode(bytes);
  const events = eventsTxt.split('\n').filter((l: string) => l.trim()).map((l: string) => JSON.parse(l).event as QaEvent);
  return { meta, events, signals, ticks: JSON.parse(ticksText) } as QaBundle;
}
