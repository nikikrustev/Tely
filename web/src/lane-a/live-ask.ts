// OWNER: A (potencialbg). "Ask out loud": one spoken question to the commentator through the relay and Foundry Voice
// Live (BUILD_PLAN Stage 7). B's Ask button owns the duck, the commentary pause, "hold that thought" and the catch-up;
// this file opens the mic, streams it to the relay, plays the answer and resolves when it has finished playing.
// WHY a relay WebSocket and not browser WebRTC: docs/DECISIONS.md D17 (file 40 §2 routing is preview and ambiguous).
// On any error, or no answer within 8 s, the fan hears why (a pre-rendered line in the commentary voice) and B's
// preset menu opens.
import { soundLevels, VoiceStage } from '../audio/mix';
import type { LaneBContext, LiveAskHandler } from '../contracts/b-exports';

export const ANSWER_TIMEOUT_MS = 8000;  // BUILD_PLAN Stage 7: presets take over within 8 s
export const MIC_DELAY_MS = 250;        // file 40 §1: the screen reader's "pressed" stays out of the mic
export const MAX_LISTEN_MS = 12000;     // relay/caps.py max_listen_s: then the relay ends the turn itself
export const ANSWER_MAX_MS = 30_000;   // safety: no answer runs longer (300 output tokens is ~15 s)
export const DOWN_FOR_MS = 5 * 60_000;  // after "off" / a cap, skip the relay for 5 min and go straight to presets
export const RATE = 24000;              // PCM16 mono both ways (relay/voicelive.py)
export const STOP_FADE_S = 0.1;         // file 49: a stopped answer fades this fast (same as ask.ts), never clicks

/** A refusal from the relay (relay/clips.py), or one we make up when the relay can't be reached. */
export interface Refusal {
  reason: string;
  clip: string;
  say: string;
}
export const UNAVAILABLE: Refusal = {
  reason: 'unavailable',
  clip: 'live_unavailable',
  say: "Live questions aren't available right now, so here are the preset questions.",
};
export const NOT_HEARD: Refusal = {
  reason: 'not_heard',
  clip: 'live_not_heard',
  say: "I didn't catch a question, so here are the preset questions.",
};
const LASTING = new Set(['demo_off', 'daily_cap', 'session_cap']);

/** The parts of a WebSocket this file uses (tests pass a fake). */
export interface RelaySocket {
  binaryType: string;
  readyState: number;
  send(data: string | ArrayBuffer): void;
  close(): void;
  onopen: (() => void) | null;
  onmessage: ((ev: { data: unknown }) => void) | null;
  onclose: (() => void) | null;
  onerror: (() => void) | null;
}

/** Everything that touches the browser, so the controller runs under vitest in Node. */
export interface LiveIO {
  openSocket(url: string): RelaySocket;
  /** Open the mic; PCM16 24 kHz mono chunks go to onChunk until stop(). */
  openMic(onChunk: (pcm: ArrayBuffer) => void): Promise<{ stop(): void }>;
  play(pcm: ArrayBuffer): void;
  playbackDone(): Promise<void>;
  stopPlayback(): void;
  earcon(kind: 'listen' | 'sent'): void;
  /** Speak a fixed line: its pre-rendered clip, or the browser voice if the clip is missing. */
  clip(id: string, text: string): Promise<void>;
  /** Open B's preset menu (the fallback). */
  showPresets(): void;
  now(): number;
  wait(ms: number): Promise<void>;
  ping?(): void;
  prefs?(prefs: Record<string, unknown>): void;
  /** Where the question is (D24): the page shows it on screen. Never announced: the mic may still be open. */
  phase?(p: 'heard' | 'answering'): void;
}

type Msg = { type: string; [k: string]: unknown };

export class LiveAsk implements LiveAskHandler {
  /** Golden turns this page saw (relay records: question, tools, answer, latency). eval reads them in ?debug=1. */
  readonly turns: unknown[] = [];
  /** [ms, what] for each ask, refusal and fallback: how fast the presets took over (eval, ?debug=1). */
  readonly events: [number, string][] = [];
  private sock: RelaySocket | null = null;
  private ready: Promise<Refusal | null> | null = null;
  private listener: ((m: Msg | ArrayBuffer) => void) | null = null;
  private downUntil = 0;
  private stopCurrent: (() => void) | null = null;

  constructor(private url: string, private io: LiveIO) {}

  async ask(playheadS: number): Promise<void> {
    if (this.stopCurrent) return;
    this.events.push([this.io.now(), 'ask']);
    let r: Refusal | null;
    if (this.io.now() < this.downUntil) r = UNAVAILABLE;
    else {
      try {
        r = await this.question(playheadS);
      } catch {
        r = UNAVAILABLE;
      }
    }
    if (r) await this.refuse(r);
  }

  cancel(): void {
    this.stopCurrent?.();
  }

  private async refuse(r: Refusal): Promise<void> {
    this.events.push([this.io.now(), `refusal:${r.reason}`]);
    if (LASTING.has(r.reason)) {
      this.downUntil = this.io.now() + DOWN_FOR_MS;
      this.drop();
    }
    await this.io.clip(r.clip, r.say);    // the fan is told why, in the commentator's voice
    this.events.push([this.io.now(), 'presets']);
    this.io.showPresets();
  }

  /** One question. Resolves null once the answer has played, or the refusal to speak instead. */
  private async question(playheadS: number): Promise<Refusal | null> {
    const refused = await this.connect();
    if (refused) return refused;
    const sock = this.sock as RelaySocket;
    return new Promise<Refusal | null>((resolve) => {
      let mic: { stop(): void } | null = null;
      let timer: ReturnType<typeof setTimeout> | null = null;
      let listenCap: ReturnType<typeof setTimeout> | null = null;
      let stoppedAt: number | null = null;
      let heard = false, answering = false, done = false;
      const clear = () => {
        if (timer) clearTimeout(timer);
        timer = null;
      };
      const arm = (ms: number, r: Refusal | null) => {
        clear();
        timer = setTimeout(() => {
          this.send({ type: 'cancel' });
          finish(r);
        }, ms);
      };
      const closeMic = () => {
        mic?.stop();
        mic = null;
        if (listenCap) clearTimeout(listenCap);
        listenCap = null;
      };
      const finish = (r: Refusal | null) => {
        if (done) return;
        done = true;
        clear();
        closeMic();
        this.listener = null;
        this.stopCurrent = null;
        if (r) this.io.stopPlayback();
        resolve(r);
      };
      this.stopCurrent = () => {           // the fan pressed Ask again, or the page went away
        this.send({ type: 'cancel' });
        this.io.stopPlayback();
        finish(null);
      };
      this.listener = (m) => {
        if (m instanceof ArrayBuffer) {
          if (!answering) {
            answering = true;
            this.io.phase?.('answering');
            arm(ANSWER_MAX_MS, null);          // an answer that never says "done" can't hold the Ask forever
            if (stoppedAt !== null) this.send({ type: 'metrics', client_latency_ms: this.io.now() - stoppedAt });
          }
          this.io.play(m);
          return;
        }
        switch (m.type) {
          case 'listening':
            this.io.earcon('listen');
            arm(ANSWER_TIMEOUT_MS, NOT_HEARD);
            void this.io.wait(MIC_DELAY_MS).then(() => (done ? null : this.io.openMic((pcm) => this.send(pcm))))
              .then((m2) => { if (m2 && done) m2.stop(); else if (m2) mic = m2; })
              .catch(() => finish(UNAVAILABLE));      // no mic permission: presets
            break;
          case 'speech_started':
            heard = true;
            clear();
            listenCap = setTimeout(() => this.send({ type: 'commit' }), MAX_LISTEN_MS);
            break;
          case 'speech_stopped':
            closeMic();
            if (!heard) heard = true;
            stoppedAt = this.io.now();
            this.io.earcon('sent');
            this.io.phase?.('heard');
            arm(ANSWER_TIMEOUT_MS, UNAVAILABLE);
            break;
          case 'tool':
            if (m.name === 'get_ball_position') this.io.ping?.();
            if (m.prefs && typeof m.prefs === 'object') this.io.prefs?.(m.prefs as Record<string, unknown>);
            break;
          case 'answer_done':
            if (m.turn) this.turns.push(m.turn);
            clear();
            closeMic();
            if (!answering) {
              finish(UNAVAILABLE);
              break;
            }
            void this.io.playbackDone().then(() => finish(null));
            break;
          case 'refusal':
            finish(m as unknown as Refusal);
            break;
          case 'error':
          case 'closed':
            if (answering) void this.io.playbackDone().then(() => finish(null)); // keep what was already said
            else finish(UNAVAILABLE);
            break;
        }
      };
      arm(ANSWER_TIMEOUT_MS, UNAVAILABLE);
      // The fan's sound levels (0..100) ride along, so "whistle down by 5" is answered with the new level.
      sock.send(JSON.stringify({ type: 'ask', playhead_s: playheadS, levels: soundLevels() }));
    });
  }

  /** Open the relay socket once and reuse it until the relay closes it (90 s idle, file 40 §6). */
  private connect(): Promise<Refusal | null> {
    if (this.sock && this.ready) return this.ready;
    const sock = this.io.openSocket(this.url);
    sock.binaryType = 'arraybuffer';
    this.sock = sock;
    this.ready = new Promise<Refusal | null>((resolve) => {
      const t = setTimeout(() => { this.drop(); resolve(UNAVAILABLE); }, ANSWER_TIMEOUT_MS);
      let open = false;                    // the first ready/refusal is the handshake; later ones belong to a question
      sock.onmessage = (ev) => {
        const m = ev.data instanceof ArrayBuffer ? ev.data : (safeJson(ev.data) as Msg | null);
        if (!m) return;
        if (!open && !(m instanceof ArrayBuffer) && (m.type === 'ready' || m.type === 'refusal')) {
          open = true;
          clearTimeout(t);
          if (m.type === 'refusal') {
            this.drop();
            resolve(m as unknown as Refusal);
          } else resolve(null);
          return;
        }
        this.listener?.(m);
      };
      const lost = () => {
        clearTimeout(t);
        if (this.sock === sock) this.drop();
        this.listener?.({ type: 'closed' });
        resolve(UNAVAILABLE);
      };
      sock.onclose = lost;
      sock.onerror = lost;
    });
    return this.ready;
  }

  private send(o: object | ArrayBuffer): void {
    const s = this.sock;
    if (!s || s.readyState !== 1) return;
    s.send(o instanceof ArrayBuffer ? o : JSON.stringify(o));
  }

  private drop(): void {
    const s = this.sock;
    this.sock = null;
    this.ready = null;
    if (s) {
      s.onclose = s.onerror = s.onmessage = null;
      try { s.close(); } catch { /* already closed */ }
    }
  }
}

function safeJson(data: unknown): unknown {
  try {
    return typeof data === 'string' ? JSON.parse(data) : null;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------- the browser side of LiveIO
/** Mic worklet: resample the context rate to 24 kHz (linear) and post 20 ms PCM16 chunks. Inline, so no build step. */
const MIC_WORKLET = `
class AsMic extends AudioWorkletProcessor {
  constructor() { super(); this.step = sampleRate / ${RATE}; this.pos = 0; this.prev = 0; this.out = new Int16Array(${RATE / 50}); this.n = 0; }
  process(inputs) {
    const x = inputs[0] && inputs[0][0];
    if (!x) return true;
    let p = this.pos;
    while (p < x.length) {
      const i = Math.floor(p), f = p - i;
      const a = i === 0 ? this.prev : x[i - 1], b = x[i];
      const v = Math.max(-1, Math.min(1, a + (b - a) * f));
      this.out[this.n++] = v < 0 ? v * 0x8000 : v * 0x7fff;
      if (this.n === this.out.length) { this.port.postMessage(this.out.buffer, [this.out.buffer]); this.out = new Int16Array(${RATE / 50}); this.n = 0; }
      p += this.step;
    }
    this.pos = p - x.length; this.prev = x[x.length - 1];
    return true;
  }
}
registerProcessor('as-mic', AsMic);`;

export interface BrowserIOOptions {
  /** The live Ask's own AudioContext (created inside the Start tap, lane-a/index.ts). Not the commentary's: that one
   *  is suspended while the commentary is paused, which is exactly when an answer plays. */
  audio: () => AudioContext | null;
  /** Base URL of the bundle, for live/index.json and the clips. */
  base: string;
  /** B's services from mountLaneA(ctx): the preset menu, the ball ping and the settings (b-exports.ts). */
  lane: Pick<LaneBContext, 'ask' | 'pingBall' | 'applyPrefs'>;
}

export function browserIO(o: BrowserIOOptions): LiveIO {
  let workletReady: Promise<void> | null = null;
  let out: GainNode | null = null;
  let answerBus: GainNode | null = null;
  let voice: VoiceStage | null = null;
  let nextT = 0;
  const playing = new Set<AudioBufferSourceNode>();
  let clips: Promise<Record<string, { file: string }>> | null = null;
  const clipIndex = () => (clips ??= fetch(`${o.base}/live/index.json`).then((r) => r.json())
    .then((j: { clips: Record<string, { file: string }> }) => j.clips));
  // D24: the refusal clips are fetched while the page is online, so "Live questions aren't available" is still said in
  // the commentator's voice when the network has just dropped, which is exactly when it is needed.
  const bytes = new Map<string, Promise<ArrayBuffer | null>>();
  const clipBytes = (id: string): Promise<ArrayBuffer | null> => {
    let b = bytes.get(id);
    if (!b) {
      b = clipIndex().then((c) => (c[id]?.file ? fetch(`${o.base}/live/${c[id]!.file}`) : null))
        .then((r) => (r?.ok ? r.arrayBuffer() : null)).catch(() => null);
      bytes.set(id, b);
      void b.then((x) => { if (!x) { bytes.delete(id); clips = null; } });   // failed: try again next time
    }
    return b;
  };
  if (typeof fetch !== 'undefined') for (const id of [UNAVAILABLE.clip, NOT_HEARD.clip]) void clipBytes(id);
  const ctx = (): AudioContext => {
    const c = o.audio();
    if (!c) throw new Error('no audio context yet');
    if (c.state !== 'running') void c.resume().catch(() => {});
    if (!out || out.context !== c) {
      voice?.dispose();
      voice = new VoiceStage(c, c.destination);   // the same press-box voice as the commentary track (mix.ts)
      out = voice.input;
    }
    return c;
  };
  const tone = (c: AudioContext, f0: number, f1: number, at: number) => {
    const osc = c.createOscillator(), g = c.createGain();
    osc.frequency.setValueAtTime(f0, at);
    osc.frequency.linearRampToValueAtTime(f1, at + 0.12);
    g.gain.setValueAtTime(0, at);
    g.gain.linearRampToValueAtTime(0.15, at + 0.01);
    g.gain.linearRampToValueAtTime(0, at + 0.14);
    osc.connect(g).connect(out as GainNode);
    osc.start(at);
    osc.stop(at + 0.15);
  };
  const browserVoice = (text: string) => new Promise<void>((res) => {
    if (typeof speechSynthesis === 'undefined') return res();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = 'en-GB';
    const t = setTimeout(res, 2000 + text.length * 90);   // Chrome may never fire onend
    u.onend = u.onerror = () => { clearTimeout(t); res(); };
    speechSynthesis.speak(u);
  });
  return {
    openSocket: (url) => new WebSocket(url) as unknown as RelaySocket,
    async openMic(onChunk) {
      const c = ctx();
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
      });
      workletReady ??= c.audioWorklet.addModule(URL.createObjectURL(new Blob([MIC_WORKLET], { type: 'text/javascript' })));
      await workletReady;
      const src = c.createMediaStreamSource(stream);
      const node = new AudioWorkletNode(c, 'as-mic');
      const sink = c.createGain();
      sink.gain.value = 0;                 // the worklet must be pulled to run; the fan never hears their own mic
      node.port.onmessage = (e: MessageEvent<ArrayBuffer>) => onChunk(e.data);
      src.connect(node).connect(sink).connect(c.destination);
      return {
        stop() {
          node.port.onmessage = null;
          src.disconnect();
          node.disconnect();
          stream.getTracks().forEach((t) => t.stop());   // the browser's mic indicator goes off between questions
        },
      };
    },
    play(pcm) {
      const c = ctx();
      const s = new Int16Array(pcm);
      if (!s.length) return;
      const buf = c.createBuffer(1, s.length, RATE);
      const ch = buf.getChannelData(0);
      for (let i = 0; i < s.length; i++) ch[i] = (s[i] as number) / 0x8000;
      const src = c.createBufferSource();
      src.buffer = buf;
      if (!answerBus || answerBus.context !== c) {       // one gain per answer, so a stop can fade it (file 49)
        answerBus = c.createGain();
        answerBus.connect(out as GainNode);
      }
      src.connect(answerBus);
      const at = Math.max(c.currentTime + 0.06, nextT);
      src.start(at);
      nextT = at + buf.duration;
      playing.add(src);
      src.onended = () => playing.delete(src);
    },
    async playbackDone() {
      const c = o.audio();
      if (!c) return;
      const until = performance.now() + Math.max(0, nextT - c.currentTime) * 1000 + 2000;   // never wait forever
      while (c.currentTime < nextT && performance.now() < until) await new Promise((r) => setTimeout(r, 50));
    },
    stopPlayback() {
      const c = o.audio(), bus = answerBus;
      answerBus = null;                                   // the next answer gets a fresh bus at full level
      const at = c ? c.currentTime + STOP_FADE_S : 0;
      if (c && bus) {
        bus.gain.setTargetAtTime(0, c.currentTime, STOP_FADE_S / 3);   // a fast fade, not a click
        setTimeout(() => { try { bus.disconnect(); } catch { /* already gone */ } }, (STOP_FADE_S + 0.5) * 1000);
      }
      playing.forEach((s) => { try { s.stop(at); } catch { /* not started */ } });
      playing.clear();
      nextT = 0;
    },
    earcon(kind) {
      try {
        const c = ctx();
        const at = c.currentTime + 0.01;
        if (kind === 'listen') tone(c, 660, 880, at);       // rising: speak now
        else tone(c, 880, 660, at);                          // falling: got it
      } catch { /* no audio yet */ }
    },
    async clip(id, text) {
      try {
        const raw = await clipBytes(id);
        if (!raw) throw new Error('no clip');
        const c = ctx();
        const buf = await c.decodeAudioData(raw.slice(0));   // decodeAudioData detaches its buffer: keep ours
        const src = c.createBufferSource();
        src.buffer = buf;
        src.connect(out as GainNode);
        await new Promise<void>((res) => {
          const t = setTimeout(res, buf.duration * 1000 + 1500);   // onended never fires in a suspended context
          src.onended = () => { clearTimeout(t); res(); };
          src.start();
        });
      } catch {
        await browserVoice(text);
      }
    },
    // SEAM(A->B): b-exports.ts Ask.showPresets(). B opens the menu once its own Ask has finished, and focuses it.
    showPresets: () => o.lane.ask.showPresets?.(),
    now: () => performance.now(),
    wait: (ms) => new Promise((r) => setTimeout(r, ms)),
    // SEAM(A->B): b-exports.ts LaneBContext.pingBall() and applyPrefs() (a no-op before Start).
    ping: () => o.lane.pingBall?.(),
    prefs: (p) => o.lane.applyPrefs?.(p),
    // SEAM(A->B): a window event, so B's main.ts can show the phase without a contract change.
    phase: (p) => window.dispatchEvent(new CustomEvent('audiostands:live-phase', { detail: p })),
  };
}
