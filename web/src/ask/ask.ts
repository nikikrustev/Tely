// OWNER: B (Nikolay). "Ask the commentator", offline presets (BUILD_PLAN Stage 6; file 40 §1).
// A question: hold that thought if a chance is coming (says THAT, never WHAT) -> duck the crowd and pause A's
// commentary (the playhead keeps running) -> the answer from A's pre-rendered clips -> "back to the action" with a
// catch-up of anything revealed meanwhile -> unduck and resume. A's live voice mode plugs in via registerLiveMode().
import type { CommentaryTrack } from '../contracts/a-exports';
import type { Ask, CrowdBus, LiveAskHandler } from '../contracts/b-exports';
import { HOLD_LOOKAHEAD_S, STATIC, type Answer, type LocalTools } from './local-tools';

export type Preset = 'score' | 'ball' | 'last' | 'missed';
export const PRESETS: { id: Preset; label: string }[] = [
  { id: 'ball', label: "Where's the ball?" },
  { id: 'score', label: "What's the score?" },
  { id: 'last', label: 'What just happened?' },
  { id: 'missed', label: 'What did I miss?' },
];
export const DUCK_DB = -12, DUCK_MS = 240, UNDUCK_MS = 1500;   // file 38: speech +12 dB over the crowd; fast down, slow up
export const HOLD_CUE_GAP_S = 2.5;                              // A's review: never say "hold" over a line due this soon

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
}

export class AskController implements Ask {
  private live: LiveAskHandler | null = null;
  private busy = false;
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

  private async run(body: () => Promise<string[]>): Promise<string[]> {
    if (this.busy) return [];
    this.busy = true;
    const said: string[] = [];
    try {
      if (this.d.tools.hold_that_thought(this.d.clock.now())) { // a chance is coming: never say what, just wait for it
        // Don't talk over A's build-up line: if one starts within 2.5 s, stay quiet and let it play.
        if (!this.d.commentary.nextCueWithin(HOLD_CUE_GAP_S)) {
          said.push(STATIC.hold as string);
          this.d.show?.(STATIC.hold as string);
          await this.d.speak(['hold'], STATIC.hold as string);
        }
        await (this.d.wait ?? sleep)(HOLD_LOOKAHEAD_S * 1000);
      }
      // SEAM(B->A): CommentaryTrack.pause() first (a-exports.ts; A's pause() also unducks), THEN duck the crowd,
      // so the answer always sits over a lowered crowd. The playhead keeps running.
      this.d.commentary.pause();
      this.d.crowd.duck(DUCK_DB, DUCK_MS);
      const paused = this.d.clock.now();                   // catch-up covers what was revealed from the pause on
      said.push(...(await body()));
      const back = this.d.tools.catch_up(paused, this.d.clock.now());
      said.push(back.say);
      this.d.show?.(back.say);
      await this.d.speak(back.fragments, back.say);
    } finally {
      this.d.crowd.unduck(UNDUCK_MS);
      this.d.commentary.resume();                         // SEAM(B->A): CommentaryTrack.resume()
      this.busy = false;
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
}

/**
 * Plays fragment clips from A's answers/index.json (fragment id -> mp3) on the audio clock, one after another.
 * If the index or a clip is missing (A hasn't rendered yet), it falls back to the browser's built-in voice
 * (speechSynthesis: on-device, no keys), so Ask still works.
 */
export class FragmentPlayer {
  private index: Record<string, string> = {};
  private cache = new Map<string, AudioBuffer>();
  constructor(private ctx: BaseAudioContext, private out: AudioNode, private base = '/replay/v1/judge/answers') {}

  async load(): Promise<number> {
    try {
      const raw = (await (await fetch(`${this.base}/index.json`)).json()) as Record<string, unknown>;
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
    let t = this.ctx.currentTime + 0.05;
    for (const f of files as string[]) {
      const buf = await this.buffer(f);
      if (!buf) return speakFallback(text);
      const src = this.ctx.createBufferSource();
      src.buffer = buf;
      src.connect(this.out);
      src.start(t);
      t += buf.duration + 0.12;                          // a breath between clips
    }
    await sleep(Math.max(0, (t - this.ctx.currentTime) * 1000));
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
      resolve();
    };
    const timer = setTimeout(() => { speechSynthesis.cancel(); finish(); }, 2000 + text.length * 90);
    u.onend = finish;
    u.onerror = finish;
    speechSynthesis.speak(u);
  });
}
