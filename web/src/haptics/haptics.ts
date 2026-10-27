// Phone vibration (file 41 haptics.ts): heartbeat tempo from tension, event tactons with a
// home/away signature, fired at the moment the matching audio is heard (minus a 20 ms lead, never late).
// Adapted: the browser bits (vibrate, timers, clock) are passed in, so Node tests can check every pattern.
export type Team = 'home' | 'away';
export type Tacton = 'attack' | 'shot' | 'nearMiss' | 'goal' | 'yellow' | 'red' | 'whistle1' | 'whistle2' | 'whistle3';
export type HapticMode = 'off' | 'events' | 'full';
export const TACTONS: Tacton[] = ['attack', 'shot', 'nearMiss', 'goal', 'yellow', 'red', 'whistle1', 'whistle2', 'whistle3'];

/** The Vibration API caps a pattern at about 10 entries in practice (file 41 draft spec), so we never send more. */
export const MAX_ENTRIES = 10;
const MIN_ON = 30, MIN_OFF = 50;
const SIG: Record<Team, number[]> = { home: [140, 90], away: [40, 60, 40, 90] }; // home: one long; away: two short
const BODY: Record<Tacton, number[]> = {
  attack: [30, 120, 30, 80, 30], shot: [90], nearMiss: [90, 120, 60, 90, 30],
  goal: [60, 60, 60, 60, 60, 60, 400], yellow: [150, 100, 150], red: [150, 100, 150, 100, 150],
  whistle1: [350], whistle2: [350, 150, 350], whistle3: [350, 150, 350, 150, 600],
};
const clamp01 = (x: number) => Math.min(1, Math.max(0, x));

/** A tacton as a vibrate() pattern: [on, off, on, ...] ms. Opponent goals are muted; whistles carry no team. */
export function compose(t: Tacton, team: Team | null, strength = 1, isMine = true): number[] {
  const whistle = t.startsWith('whistle');
  const body = t === 'goal' && !isMine ? [60, 60, 200] : BODY[t];
  const p = [...(team && !whistle ? SIG[team] : []), ...body]
    .map((d, i) => (i % 2 === 0 ? Math.max(MIN_ON, Math.round(d * strength)) : Math.max(MIN_OFF, d)));
  return p.slice(0, MAX_ENTRIES);
}

/** tension 0..1 -> one lub-dub beat, and the time until the next one (55-140 bpm; our mapping, file 41). */
export function heartbeat(tension: number, strength = 1): { pattern: number[]; periodMs: number; bpm: number } {
  const t = clamp01(tension), bpm = 55 + 85 * t, periodMs = 60_000 / bpm;
  const lub = Math.max(MIN_ON, Math.round((40 + 40 * t) * strength));
  const dub = Math.max(MIN_ON, Math.round((30 + 25 * t) * strength));
  return { pattern: [lub, Math.max(MIN_OFF, Math.round(0.2 * periodMs)), dub], periodMs, bpm };
}

/** What the page needs from the browser. `vibrate` is null where the browser cannot vibrate. */
export interface HapticsEnv {
  vibrate: ((pattern: number[] | number) => boolean) | null;
  now: () => number;                                     // performance.now()
  setTimeout: (f: () => void, ms: number) => number;
  clearTimeout: (id: number) => void;
}

/** Firefox Android returns true from vibrate() but never vibrates (file 41, MDN BCD), so it counts as "cannot".
 *  iPhone browsers have no vibrate() at all. */
export function browserEnv(): HapticsEnv {
  const nav = typeof navigator !== 'undefined' ? navigator : undefined;
  const firefox = !!nav && /Firefox\//.test(nav.userAgent);
  const can = !!nav && 'vibrate' in nav && !firefox;
  return {
    vibrate: can ? (p) => (nav as Navigator).vibrate(p) : null,
    now: () => performance.now(),
    setTimeout: (f, ms) => window.setTimeout(f, ms),
    clearTimeout: (id) => window.clearTimeout(id),
  };
}

/** The honest line for the UI (file 41). */
export const NO_VIBRATION_MESSAGE =
  'This browser cannot vibrate (iPhone browsers and Firefox do not allow it). You get the full audio; vibration works on Android in Chrome or Samsung Internet.';

export interface HapticSettings { mode: HapticMode; strength: number; myTeam: Team | null }
const TENSION_FLOOR = 0.35, MAX_RUN_MS = 180_000, LEAD_MS = 20; // file 41 defaults (anti-fatigue, lead)

export class Haptics {
  private tension = 0;
  private beatTimer = 0;
  private runStart = 0;
  private restUntil = 0;
  private busyUntil = 0;
  private pending = new Set<number>();
  played: number[][] = []; // patterns actually sent (tests and the debug panel read it)

  constructor(private env: HapticsEnv, public s: HapticSettings = { mode: 'full', strength: 1, myTeam: null }) {}

  get available(): boolean {
    return this.env.vibrate !== null;
  }

  /** Vibrate tacton `t` with the matching sound: `delayToHearMs` = ms until that sound is heard (fired 20 ms early). */
  event(t: Tacton, team: Team | null, delayToHearMs = 0): void {
    if (!this.env.vibrate || this.s.mode === 'off') return;
    const p = compose(t, team, this.s.strength, !this.s.myTeam || !team || team === this.s.myTeam);
    const id = this.env.setTimeout(() => {
      this.pending.delete(id);
      this.play(p);
      this.busyUntil = this.env.now() + p.reduce((a, b) => a + b, 0) + 600; // event tactons pre-empt the heartbeat
    }, Math.max(0, delayToHearMs - LEAD_MS));
    this.pending.add(id);
  }

  /** Per-second tension drives the heartbeat (full mode only), with a 1-minute rest after a 3-minute run. */
  setTension(x: number): void {
    this.tension = clamp01(x);
    const now = this.env.now();
    if (!this.beatTimer && this.s.mode === 'full' && this.tension >= TENSION_FLOOR && now >= this.restUntil) {
      this.runStart = now;
      this.beat();
    }
  }

  /** Stop everything now, including tactons queued for later (pause, seek, hidden tab). */
  stopAll(): void {
    this.env.clearTimeout(this.beatTimer);
    this.beatTimer = 0;
    this.pending.forEach((id) => this.env.clearTimeout(id));
    this.pending.clear();
    this.env.vibrate?.(0);
  }

  private play(p: number[]): void {
    this.played.push(p);
    this.env.vibrate?.(p);
  }

  private beat = (): void => {
    const now = this.env.now();
    if (now - this.runStart > MAX_RUN_MS) this.restUntil = now + 60_000;
    if (this.s.mode !== 'full' || this.tension < TENSION_FLOOR || now < this.restUntil) {
      this.beatTimer = 0;
      return;
    }
    const hb = heartbeat(this.tension, this.s.strength);
    if (now >= this.busyUntil) this.play(hb.pattern);
    this.beatTimer = this.env.setTimeout(this.beat, hb.periodMs);
  };
}

/** Keep the screen on while playing: a hidden page cannot vibrate. The lock drops on tab switch, so re-request it. */
export function keepAwake(): void {
  const nav = navigator as Navigator & { wakeLock?: { request(type: 'screen'): Promise<unknown> } };
  const ask = () => nav.wakeLock?.request('screen').catch(() => {});
  ask();
  document.addEventListener('visibilitychange', () => { if (!document.hidden) ask(); });
}
