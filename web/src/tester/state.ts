// OWNER: A (potencialbg). Tester mode (?test=1, D19): the tester's anonymous ID, their group, the task list and
// everything they answered. Saved in localStorage inside try/catch, like settings.ts: a private window or blocked
// storage only means progress is kept in memory for this visit. No name, email or age is ever stored.
import type { ListenClip } from '../replay/listen';
import type { ClipNo, ProbeAnswers, ScaleId } from './questions';

export type Group = 'A' | 'B';
export type TaskKind = 'tour' | 'clip' | 'questions' | 'ask' | 'settings' | 'overall';
export type TaskStatus = 'todo' | 'done' | 'skip';

export interface Task { id: number; kind: TaskKind; clip?: ClipNo; title: string; minutes: number; what: string }

export const TASKS: readonly Task[] = [
  { id: 1, kind: 'tour', title: 'Learn the sounds', minutes: 2,
    what: 'A short guided tour of the sounds: the ball, a pass, a shot, the crowd. A voice explains each one.' },
  { id: 2, kind: 'clip', clip: 1, title: 'Clip 1, eyes closed', minutes: 3,
    what: 'Three minutes of the match. Close your eyes once it starts. It stops by itself.' },
  { id: 3, kind: 'questions', clip: 1, title: 'Questions about clip 1', minutes: 1,
    what: 'Seven quick questions about what you heard. "Don\'t know" is a fine answer.' },
  { id: 4, kind: 'clip', clip: 2, title: 'Clip 2, eyes closed', minutes: 3,
    what: 'Three more minutes, a little later in the same match. Eyes closed again. It stops by itself.' },
  { id: 5, kind: 'questions', clip: 2, title: 'Questions about clip 2', minutes: 1,
    what: 'The same seven questions, about clip 2.' },
  { id: 6, kind: 'ask', title: 'Try "Ask the commentator"', minutes: 2,
    what: 'Ask the commentator two questions from the list, then one out loud if your browser lets us use the microphone.' },
  { id: 7, kind: 'settings', title: 'Try Settings', minutes: 1,
    what: 'Choose your end of the stadium, change the crowd level and, on an Android phone, try the vibration.' },
  { id: 8, kind: 'overall', title: 'Overall feedback', minutes: 2,
    what: 'What confused you, what you liked, and a few questions about your device.' },
];

/** eval/listening_test.md section 1: Clip 1 is 670 -> 850, Clip 2 is 970 -> 1150 (playhead seconds). */
export const CLIP_WINDOWS: Record<ClipNo, { from: number; to: number }> = { 1: { from: 670, to: 850 }, 2: { from: 970, to: 1150 } };
/** Where tasks 6 and 7 start the match if nothing is playing: Clip 2's start, full sound, no end (section 4 step 8). */
export const OPEN_PLAY_FROM = 970;

/** Section 1 counterbalancing: group A hears Clip 1 with commentary only and Clip 2 full; group B the other way. */
export function commentaryOnly(group: Group, clip: ClipNo): boolean {
  return (group === 'A') === (clip === 1);
}

/** The clip a clip task plays. The condition stays inside the page: never in the URL, never on screen. */
export function clipFor(group: Group, clip: ClipNo): ListenClip {
  const w = CLIP_WINDOWS[clip];
  return { from: w.from, to: w.to, commentaryOnly: commentaryOnly(group, clip) };
}

/** "t-" and 8 random hex digits: anonymous, made on the first visit. */
export function newTesterId(random: (n: number) => Uint8Array = randomBytes): string {
  return `t-${hex(random(4))}`;
}

/** The group comes from the ID's last hex digit (even: A, odd: B), so a random ID gives a random, balanced group. */
export function groupFor(id: string): Group {
  const d = parseInt(id.slice(-1), 16);
  return Number.isFinite(d) && d % 2 === 1 ? 'B' : 'A';
}

export function newEventId(random: (n: number) => Uint8Array = randomBytes): string {
  return hex(random(4));
}

function randomBytes(n: number): Uint8Array {
  const b = new Uint8Array(n);
  globalThis.crypto.getRandomValues(b);
  return b;
}

function hex(b: Uint8Array): string {
  return [...b].map((x) => x.toString(16).padStart(2, '0')).join('');
}

export interface ClipAnswers { probes: ProbeAnswers; scale: Partial<Record<ScaleId, number>> }
export interface Answers {
  clips: Partial<Record<ClipNo, ClipAnswers>>;
  ask?: { presets: number; liveAvailable: boolean; liveTried: boolean; worked?: string };
  settings?: { changed: string[]; easy?: string };
  overall?: Partial<Record<'confusing' | 'liked' | 'would_use' | 'preferred' | 'device' | 'headphones' | 'screen_reader' | 'sight', string>>;
  problems: { kind: string; text: string }[];
}

export type Ev = Record<string, string | number | boolean>;
/** One feedback event and whether it reached the relay. "unsent" ones are retried on the next visit. */
export interface Outgoing { ev: Ev; status: 'pending' | 'sent' | 'unsent' }

export interface TesterState {
  v: 1;
  id: string;
  group: Group;
  consent: { takePart: boolean; quote: boolean } | null;   // null until the welcome screen is answered
  tasks: Record<number, TaskStatus>;
  answers: Answers;
  events: Outgoing[];
}

export const STORAGE_KEY = 'tely.tester.v1';
/** The key from before the rename to Tely (D26): read if the new key is empty, so a tester's answers carry over. */
export const LEGACY_STORAGE_KEY = 'audiostands.tester.v1';
export type StorageLike = Pick<Storage, 'getItem' | 'setItem'>;

export function freshState(id: string = newTesterId()): TesterState {
  return { v: 1, id, group: groupFor(id), consent: null, tasks: Object.fromEntries(TASKS.map((t) => [t.id, 'todo'])),
    answers: { clips: {}, problems: [] }, events: [] };
}

/** The saved state, or a fresh one if there is none, it is broken, or storage throws. */
export function loadState(storage: StorageLike | null): TesterState {
  try {
    const raw = storage?.getItem(STORAGE_KEY) ?? storage?.getItem(LEGACY_STORAGE_KEY);
    if (!raw) return freshState();
    const o = JSON.parse(raw) as Partial<TesterState>;
    if (o.v !== 1 || typeof o.id !== 'string' || !/^t-[0-9a-f]{8}$/.test(o.id)) return freshState();
    const base = freshState(o.id);
    const tasks = { ...base.tasks };
    for (const t of TASKS) {
      const s = o.tasks?.[t.id];
      if (s === 'done' || s === 'skip' || s === 'todo') tasks[t.id] = s;
    }
    return {
      ...base,
      consent: o.consent && typeof o.consent.takePart === 'boolean' ? { takePart: o.consent.takePart, quote: o.consent.quote === true } : null,
      tasks,
      answers: { ...base.answers, ...(o.answers ?? {}), clips: o.answers?.clips ?? {}, problems: o.answers?.problems ?? [] },
      events: Array.isArray(o.events) ? o.events.filter((e) => e && typeof e.ev === 'object') : [],
    };
  } catch {
    return freshState();
  }
}

/** False if it could not be saved (the page keeps going with the state in memory). */
export function saveState(s: TesterState, storage: StorageLike | null): boolean {
  try {
    if (!storage) return false;
    storage.setItem(STORAGE_KEY, JSON.stringify(s));
    return true;
  } catch {
    return false;
  }
}

export function setTask(s: TesterState, id: number, status: TaskStatus): TesterState {
  return { ...s, tasks: { ...s.tasks, [id]: status } };
}

/** The first task still to do after `after` (wrapping round), or null when every task is done or skipped. */
export function nextTask(s: TesterState, after = 0): Task | null {
  const order = [...TASKS.filter((t) => t.id > after), ...TASKS.filter((t) => t.id <= after)];
  return order.find((t) => s.tasks[t.id] === 'todo') ?? null;
}

export function progress(s: TesterState): { finished: number; total: number } {
  return { finished: TASKS.filter((t) => s.tasks[t.id] !== 'todo').length, total: TASKS.length };
}
