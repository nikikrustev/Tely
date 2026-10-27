// OWNER: B (Nikolay). "Ask the commentator", offline presets (BUILD_PLAN Stage 6; file 40 §1).
// A question: hold that thought if a chance is coming (says THAT, never WHAT) -> duck the crowd and pause A's
// commentary (the playhead keeps running) -> the answer from A's pre-rendered clips -> "back to the action" with a
// catch-up of anything revealed meanwhile -> unduck and resume. A's live voice mode plugs in via registerLiveMode().
// Press-to-interrupt (file 49): pressing Ask during an answer stops it at once and keeps the commentary paused while
// the fan picks the next question; closing the menu instead goes back to the action (catch-up, then resume).
import type { CommentaryTrack } from '../contracts/a-exports';
import type { Ask, CrowdBus, LiveAskHandler } from '../contracts/b-exports';
import { HOLD_LOOKAHEAD_S, STATIC, type Answer, type LocalTools } from './local-tools';
import { bundleBase } from '../replay/base';

export type Preset = 'score' | 'ball' | 'last' | 'missed';
export const PRESETS: { id: Preset; label: string }[] = [
  { id: 'ball', label: "Where's the ball?" },
  { id: 'score', label: "What's the score?" },
  { id: 'last', label: 'What just happened?' },
  { id: 'missed', label: 'What did I miss?' },
];
export const DUCK_DB = -12, DUCK_MS = 240, UNDUCK_MS = 1500;   // file 38: speech +12 dB over the crowd; fast down, slow up
export const HOLD_CUE_GAP_S = 2.5;                              // A's review: never say "hold" over a line due this soon
export const STOP_FADE_S = 0.1;                                 // file 49: a stop is a fast fade, never a click

export interface AskDeps {
  tools: LocalTools;
  clock: { now(): number };
  crowd: CrowdBus;
  commentary: CommentaryTrack;
  /** Speak one answer: play these fragment clips in order (or fall back to `text`). Resolves when done. */
  speak: (fragments: string[] | null, text: string) => Promise<void>;
  ping?: () => void;
  show?: (text: string) => void;                 // visible text (not a live region: the fan already hears it)
  wait?: (ms: number) => Promise<void>;
  /** Stop whatever `speak` is playing now; its promise then resolves. */
  stop?: () => void;
}

/** After an interrupt: 'listen' keeps the commentary paused for the next question, 'back' returns to the action. */
export type AfterStop = 'listen' | 'back';

export class AskController implements Ask {
  private live: LiveAskHandler | null = null;
  private busy = false;
  private pausedAt: number | null = null;          // the commentary is paused (and the crowd ducked) since this playhead
  private stopped: AfterStop | null = null;        // set by interrupt() while a question runs
  private wake: (() => void) | null = null;        // ends the current wait early
  constructor(private d: AskDeps) {}

  // SEAM(B->A): b-exports.ts Ask.registerLiveMode. A's lane-a/live-ask.ts registers the Voice Live handler here.
  registerLiveMode(handler: LiveAskHandler): void {
    this.live = handler;
  }

  get hasLive(): boolean {
    return this.live !== null;
  }

  get isBusy(): boolean {
    return this.busy;
  }

  /** The commentary is paused waiting for the fan's next question (after an interrupt). */
  get isHolding(): boolean {
    return !this.busy && this.pausedAt !== null;
  }

  /** Answer for a preset at playhead p (pure; the Stage 6 tests call it). */
  answer(preset: Preset, p: number): Answer {
    const t = this.d.tools;
    if (preset === 'score') return t.get_score_and_clock(p);
    if (preset === 'ball') return t.get_ball_position(p);
    if (preset === 'last') return t.get_last_events(p, 2);
    const r = t.what_did_i_miss(p, t.clockStr(Math.max(t.t0, p - 120)));
    return 'error' in r ? t.get_last_events(p, 2) : r;
  }

  /** Ask one preset question. Returns what was said (for tests and the visible transcript). */
  async ask(preset: Preset): Promise<string[]> {
    return this.run(async () => {
      const p = this.d.clock.now();
      const a = this.answer(preset, p);
      if (preset === 'ball') this.d.ping?.();
      this.d.show?.(a.say);
      await this.d.speak(a.fragments, a.say);
      return [a.say];
    });
  }

  /** A's live voice mode (Voice Live), with the same duck / pause / catch-up around it. */
  async askLive(): Promise<string[]> {
    const live = this.live;
    if (!live) return [];
    return this.run(async () => {
      await live.ask(this.d.clock.now());
      return [];
    });
  }

  cancel(): void {
    this.live?.cancel();
  }

  /** The fan pressed Ask (or a key) while a question runs: stop speaking now, locally, without waiting for any
   *  network. Returns false if nothing was running. */
  interrupt(then: AfterStop): boolean {
    if (!this.busy) return false;
    this.stopped = then;
    this.live?.cancel();
    this.d.stop?.();
    this.wake?.();
    return true;
  }

  /** The fan closed the question menu after an interrupt without asking again: catch up, then resume. */
  async release(): Promise<string[]> {
    if (this.busy || this.pausedAt === null) return [];
    this.busy = true;
    const said: string[] = [];
    try {
      await this.backToAction(said);
    } finally {
      this.finish(this.stopped === 'listen');            // stopped mid catch-up to ask again: stay paused
    }
    return said;
  }

  /** The fan paused the match while the commentary was held for a next question (D24): forget the hold, with no
   *  catch-up talk. The commentary resumes here and the pause that follows stops it again. */
  dropHold(): void {
    if (!this.busy && this.pausedAt !== null) this.finish(false);
  }

  /** A wait that interrupt() can cut short. */
  private async hold(ms: number): Promise<void> {
    await Promise.race([(this.d.wait ?? sleep)(ms), new Promise<void>((r) => { this.wake = r; })]);
    this.wake = null;
  }

  private async backToAction(said: string[]): Promise<void> {
    const back = this.d.tools.catch_up(this.pausedAt as number, this.d.clock.now());
    said.push(back.say);
    this.d.show?.(back.say);
    await this.d.speak(back.fragments, back.say);
  }

  /** Unduck and resume, unless the fan is about to ask again. Always clears the busy flag. */
  private finish(keepPaused: boolean): void {
    if (!keepPaused && this.pausedAt !== null) {
      this.d.crowd.unduck(UNDUCK_MS);
      this.d.commentary.resume();                         // SEAM(B->A): CommentaryTrack.resume()
      this.pausedAt = null;
    }
    this.stopped = null;
    this.busy = false;
  }

  private async run(body: () => Promise<string[]>): Promise<string[]> {
    if (this.busy) return [];
    this.busy = true;
    this.stopped = null;
    const said: string[] = [];
    let keepPaused = false;
    try {
      // A chance is coming: never say what, just wait for it. Not when the commentary is already paused for this
      // question (after an interrupt): the build-up would be paused too.
      if (this.pausedAt === null && this.d.tools.hold_that_thought(this.d.clock.now())) {
        // Don't talk over A's build-up line: if one starts within 2.5 s, stay quiet and let it play.
        if (!this.d.commentary.nextCueWithin(HOLD_CUE_GAP_S)) {
          said.push(STATIC.hold as string);
          this.d.show?.(STATIC.hold as string);
          await this.d.speak(['hold'], STATIC.hold as string);
        }
        if (!this.stopped) await this.hold(HOLD_LOOKAHEAD_S * 1000);
      }
      if (this.pausedAt === null) {
        // SEAM(B->A): CommentaryTrack.pause() first (a-exports.ts; A's pause() also unducks), THEN duck the crowd,
        // so the answer always sits over a lowered crowd. The playhead keeps running.
        this.d.commentary.pause();
        this.d.crowd.duck(DUCK_DB, DUCK_MS);
        this.pausedAt = this.d.clock.now();               // catch-up covers what was revealed from the pause on
      }
      if (!this.stopped) said.push(...(await body()));
      if (this.stopped === 'listen') keepPaused = true;   // the fan asks again: no catch-up yet, stay paused
      else if (!this.stopped) await this.backToAction(said);
      // 'back' (Escape): straight back to the action, with no catch-up talk after the fan asked for quiet.
    } finally {
      this.finish(keepPaused);
    }
    return said;
  }
}

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

/** The Ask button exists before Start; A may register the live mode at boot. This forwards once the controller exists. */
export class LazyAsk implements Ask {
  private handler: LiveAskHandler | null = null;
  target: AskController | null = null;
  /** Called whenever the live mode is registered (A's live mode may register after Start). */
  onRegister: (() => void) | null = null;
  registerLiveMode(handler: LiveAskHandler): void {
    this.handler = handler;
    this.target?.registerLiveMode(handler);
    this.onRegister?.();
  }
  attach(c: AskController): void {
    this.target = c;
    if (this.handler) c.registerLiveMode(this.handler);
  }
  /** Opens the preset menu; main.ts sets this (the menu is DOM). Before that it does nothing. */
  onShowPresets: (() => void) | null = null;
  // SEAM(B->A): b-exports.ts Ask.showPresets. A's live-ask.ts calls it after a refusal instead of clicking #ask.
  showPresets(): void {
    this.onShowPresets?.();
  }
}

/**
 * Plays fragment clips from A's answers/index.json (fragment id -> mp3) on the audio clock, one after another.
 * If the index or a clip is missing (A hasn't rendered yet), it falls back to the browser's built-in voice
 * (speechSynthesis: on-device, no keys), so Ask still works.
 */
export class FragmentPlayer {
  private index: Record<string, string> = {};
  private cache = new Map<string, AudioBuffer>();
  private current: { gain: GainNode; sources: AudioBufferSourceNode[]; done: () => void } | null = null;
  private base: string;
  constructor(private ctx: BaseAudioContext, private out: AudioNode, private root = `${bundleBase()}/answers`) {
    this.base = root;
  }

  /** D27: the same fragments in another language, from answers/<lang>/ (English stays in answers/). A language
   *  the bundle has no answers for keeps the current ones and returns false. */
  async setLanguage(lang: string): Promise<boolean> {
    const base = lang === 'en' ? this.root : `${this.root}/${lang}`;
    if (base === this.base && Object.keys(this.index).length) return true;
    const prev = { base: this.base, index: this.index };
    this.base = base;
    this.index = {};
    if (await this.load()) return true;
    this.base = prev.base;
    this.index = prev.index;
    return false;
  }

  /** Stop the answer now: a STOP_FADE_S fade (no click), and speak() resolves at once. */
  stop(): void {
    stopFallback();
    const c = this.current;
    if (!c) return;
    this.current = null;
    const t = this.ctx.currentTime;
    c.gain.gain.setTargetAtTime(0, t, STOP_FADE_S / 3);  // ~95% down after three time constants
    for (const s of c.sources) { try { s.stop(t + STOP_FADE_S); } catch { /* not started */ } }
    c.done();
  }

  async load(): Promise<number> {
    try {
      const res = await fetch(`${this.base}/index.json`);
      if (res.ok === false) throw new Error(String(res.status));   // a missing language folder: keep what we have
      const raw = (await res.json()) as Record<string, unknown>;
      const map = (raw.fragments && typeof raw.fragments === 'object' ? raw.fragments : raw) as Record<string, unknown>;
      // SEAM(B->A): answers/index.json from A's answers.py: { id: "file.mp3" } or { id: { file / audio_url } }
      for (const [id, v] of Object.entries(map)) {
        const f = typeof v === 'string' ? v : (v as { file?: string; audio_url?: string })?.file ?? (v as { audio_url?: string })?.audio_url;
        if (typeof f === 'string') this.index[id] = f;
      }
    } catch {
      this.index = {};
    }
    return Object.keys(this.index).length;
  }

  async speak(fragments: string[] | null, text: string): Promise<void> {
    const files = (fragments ?? []).map((id) => this.index[id]);
    if (!fragments?.length || files.some((f) => !f)) return speakFallback(text);
    const bufs: AudioBuffer[] = [];
    for (const f of files as string[]) {
      const buf = await this.buffer(f);
      if (!buf) return speakFallback(text);
      bufs.push(buf);
    }
    const gain = this.ctx.createGain();                  // one gain per answer, so stop() can fade it out
    gain.connect(this.out);
    let done = () => {};
    const stopped = new Promise<void>((r) => { done = r; });
    const me = { gain, sources: [] as AudioBufferSourceNode[], done };
    this.current = me;
    let t = this.ctx.currentTime + 0.05;
    for (const buf of bufs) {
      const src = this.ctx.createBufferSource();
      src.buffer = buf;
      src.connect(gain);
      src.start(t);
      me.sources.push(src);
      t += buf.duration + 0.12;                          // a breath between clips
    }
    await Promise.race([sleep(Math.max(0, (t - this.ctx.currentTime) * 1000)), stopped]);
    if (this.current === me) this.current = null;
    setTimeout(() => { try { gain.disconnect(); } catch { /* already gone */ } }, (STOP_FADE_S + 0.5) * 1000);
  }

  private async buffer(f: string): Promise<AudioBuffer | null> {
    const url = f.startsWith('/') || f.startsWith('http') ? f : `${this.base}/${f}`;
    if (!this.cache.has(url)) {
      try {
        this.cache.set(url, await this.ctx.decodeAudioData(await (await fetch(url)).arrayBuffer()));
      } catch {
        return null;
      }
    }
    return this.cache.get(url) ?? null;
  }
}

const speaking = new Set<SpeechSynthesisUtterance>(); // keep a reference: Chrome can drop a collected utterance's events
const finishers = new Set<() => void>();              // pending speakFallback() promises, so a stop resolves them

/** Stop the browser voice now and resolve its pending speakFallback() promises. */
export function stopFallback(): void {
  if (!finishers.size) return;
  if (typeof speechSynthesis !== 'undefined') speechSynthesis.cancel();
  [...finishers].forEach((f) => f());
}

/** Browser voice fallback. Chrome sometimes never fires onend/onerror, so a timeout (2 s + 90 ms per character)
 *  cancels the speech and resolves anyway: the Ask can never get stuck (A's review). */
export function speakFallback(text: string): Promise<void> {
  if (typeof speechSynthesis === 'undefined') return Promise.resolve();
  return new Promise((resolve) => {
    const u = new SpeechSynthesisUtterance(text);
    u.lang = 'en-GB';
    speaking.add(u);
    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      speaking.delete(u);
      finishers.delete(finish);
      resolve();
    };
    finishers.add(finish);
    const timer = setTimeout(() => { speechSynthesis.cancel(); finish(); }, 2000 + text.length * 90);
    u.onend = finish;
    u.onerror = finish;
    speechSynthesis.speak(u);
  });
}
