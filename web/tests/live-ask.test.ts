// The live Ask controller against a fake relay and fake browser IO (no mic, no network).
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { liveRelayUrl } from '../src/voice';
import {
  ANSWER_TIMEOUT_MS, BEEP_MS, browserIO, DOWN_FOR_MS, LiveAsk, type LiveIO, type RelaySocket, WAKE_TIMEOUT_MS,
} from '../src/voice/live-ask';
import { DEFAULT_MIX, levelFromDb, soundLevels } from '../src/audio/mix';
import { FakeAudioContext } from './fake-audio';

class FakeSocket implements RelaySocket {
  binaryType = 'blob';
  readyState = 1;
  sent: (string | ArrayBuffer)[] = [];
  closed = false;
  onopen: (() => void) | null = null;
  onmessage: ((ev: { data: unknown }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  send(d: string | ArrayBuffer) { this.sent.push(d); }
  close() { this.closed = true; this.readyState = 3; }
  server(m: object | ArrayBuffer) { this.onmessage?.({ data: m instanceof ArrayBuffer ? m : JSON.stringify(m) }); }
  json() { return this.sent.filter((s): s is string => typeof s === 'string').map((s) => JSON.parse(s)); }
}

function setup(over: Partial<LiveIO> = {}) {
  const sockets: FakeSocket[] = [];
  const log: string[] = [];
  let micChunk: ((b: ArrayBuffer) => void) | null = null;
  let t = 0;
  const io: LiveIO = {
    openSocket: () => { const s = new FakeSocket(); sockets.push(s); return s; },
    openMic: async (on) => { micChunk = on; log.push('mic:open'); return { stop: () => log.push('mic:stop') }; },
    play: () => log.push('play'),
    playbackDone: async () => { log.push('played'); },
    stopPlayback: () => log.push('stop'),
    earcon: (k) => log.push(`earcon:${k}`),
    clip: async (id) => { log.push(`clip:${id}`); },
    showPresets: () => log.push('presets'),
    now: () => t,
    wait: async () => {},
    ping: () => log.push('ping'),
    prefs: (p) => log.push(`prefs:${JSON.stringify(p)}`),
    phase: (p) => log.push(`phase:${p}`),
    ...over,
  };
  const live = new LiveAsk('wss://relay.test/voice', io);
  return { live, io, sockets, log, mic: () => micChunk, tick: (ms: number) => { t += ms; } };
}

const flush = () => vi.advanceTimersByTimeAsync(0);

beforeEach(() => { vi.useFakeTimers(); });
afterEach(() => { vi.useRealTimers(); });

describe('LiveAsk', () => {
  it('asks, streams the mic, plays the answer and resolves when it has played', async () => {
    const { live, sockets, log, mic, tick } = setup();
    const done = live.ask(742);
    const s = sockets[0] as FakeSocket;
    expect(s.binaryType).toBe('arraybuffer');
    s.server({ type: 'ready' });
    await flush();
    expect(s.json()[0]).toEqual({ type: 'ask', playhead_s: 742, levels: soundLevels(), lang: 'en' });
    expect((s.json()[0] as { levels: Record<string, number> }).levels.whistle).toBe(levelFromDb(DEFAULT_MIX.whistle));
    s.server({ type: 'listening', as_of_clock: '57:22' });
    await flush();
    expect(log).toContain('earcon:listen');
    expect(log).toContain('mic:open');
    mic()?.(new ArrayBuffer(960));                       // under the beep: not sent
    expect(s.sent.some((x) => x instanceof ArrayBuffer)).toBe(false);
    tick(BEEP_MS);
    mic()?.(new ArrayBuffer(960));
    expect(s.sent.some((x) => x instanceof ArrayBuffer)).toBe(true);
    s.server({ type: 'speech_started' });
    s.server({ type: 'speech_stopped' });
    expect(log).toContain('mic:stop');
    expect(log).toContain('earcon:sent');
    tick(640);
    s.server({ type: 'tool', name: 'get_ball_position', say: 'Navy have it', prefs: null });
    s.server(new ArrayBuffer(4800));
    expect(s.json().find((m) => m.type === 'metrics')).toEqual({ type: 'metrics', client_latency_ms: 640 });
    s.server({ type: 'answer_done', turn: { question: "Where's the ball?" } });
    await flush();
    await done;
    expect(log).toEqual(expect.arrayContaining(['ping', 'play', 'played']));
    expect(log).not.toContain('presets');
    expect(live.turns).toEqual([{ question: "Where's the ball?" }]);
  });

  it('reuses the socket for the next question', async () => {
    const { live, sockets } = setup();
    const a = live.ask(700);
    (sockets[0] as FakeSocket).server({ type: 'ready' });
    await flush();
    live.cancel();
    await a;
    void live.ask(710);
    await flush();
    expect(sockets).toHaveLength(1);
    expect((sockets[0] as FakeSocket).json().filter((m) => m.type === 'ask')).toHaveLength(2);
  });

  it('DEMO_MODE off: says so in the commentary voice, opens the presets, and skips the relay for a while', async () => {
    const { live, sockets, log, tick } = setup();
    const a = live.ask(700);
    (sockets[0] as FakeSocket).server({ type: 'refusal', reason: 'demo_off', clip: 'live_unavailable', say: 'x' });
    await a;
    expect(log).toEqual(['clip:live_unavailable', 'presets']);
    await live.ask(710);
    expect(sockets).toHaveLength(1);                     // no second connection while it's off
    tick(DOWN_FOR_MS + 1);
    void live.ask(720);
    expect(sockets).toHaveLength(2);
  });

  it('a relay that never answers: the waking line, one longer try, then presets', async () => {
    const { live, log, sockets } = setup();
    const a = live.ask(700);
    await vi.advanceTimersByTimeAsync(ANSWER_TIMEOUT_MS);
    expect(log).toEqual(['phase:waking', 'clip:live_waking']);
    expect(sockets).toHaveLength(2);                     // the first socket was dropped, then one retry
    expect(sockets[0]!.closed).toBe(true);
    await vi.advanceTimersByTimeAsync(WAKE_TIMEOUT_MS);
    await a;
    expect(log).toEqual(['phase:waking', 'clip:live_waking', 'clip:live_unavailable', 'presets']);
    expect(sockets).toHaveLength(2);                     // only one retry
  });

  it('a cold relay that wakes during the longer try answers the question (item 4: ~45 s wake)', async () => {
    const { live, log, sockets } = setup();
    const a = live.ask(700);
    await vi.advanceTimersByTimeAsync(ANSWER_TIMEOUT_MS);
    await vi.advanceTimersByTimeAsync(37_000);           // 45 s after the press
    const s = sockets[1] as FakeSocket;
    s.server({ type: 'ready' });
    await flush();
    expect(s.json()[0]).toMatchObject({ type: 'ask', playhead_s: 700 });
    s.server({ type: 'listening' });
    await flush();
    s.server({ type: 'speech_stopped' });
    s.server(new ArrayBuffer(48));
    s.server({ type: 'answer_done' });
    await flush();
    await a;
    expect(log).not.toContain('presets');
    expect(log).toContain('play');
  });

  it('cancel while the relay is connecting: done at once, no refusal line, no presets (item 3)', async () => {
    const { live, log, sockets } = setup();
    const a = live.ask(700);
    await vi.advanceTimersByTimeAsync(2000);
    live.cancel();
    await flush();
    await a;                                             // resolved without waiting for the 8 s connect timeout
    expect(log.filter((l) => l.startsWith('clip:') || l === 'presets')).toEqual([]);
    sockets[0]!.server({ type: 'ready' });               // the relay answers late: nothing is asked
    await flush();
    expect(sockets[0]!.json().filter((m) => m.type === 'ask')).toHaveLength(0);
    // and the next press asks normally on the same socket
    const b = live.ask(710);
    await flush();
    expect(sockets[0]!.json().filter((m) => m.type === 'ask')).toHaveLength(1);
    live.cancel();
    await b;
  });

  it('cancel during the waking line stops it and opens nothing (items 3 and 4)', async () => {
    let endClip: () => void = () => {};
    const { live, log } = setup({
      clip: (id) => { log.push(`clip:${id}`); return new Promise<void>((r) => { endClip = r; }); },
    });
    const a = live.ask(700);
    await vi.advanceTimersByTimeAsync(ANSWER_TIMEOUT_MS);
    expect(log).toContain('clip:live_waking');
    live.cancel();
    await flush();
    await a;
    expect(log).toContain('stop');                       // stopPlayback(): the line stops mid-word
    expect(log).not.toContain('presets');
    endClip();
  });

  it('cancel during a refusal line stops it and does not open the presets (item 3)', async () => {
    const { live, sockets, log } = setup({ clip: (id) => { log.push(`clip:${id}`); return new Promise<void>(() => {}); } });
    const a = live.ask(700);
    (sockets[0] as FakeSocket).server({ type: 'refusal', reason: 'rate_limit', clip: 'live_rate_limit', say: 'x' });
    await flush();
    expect(log).toContain('clip:live_rate_limit');
    live.cancel();
    await a;                                             // the never-ending clip does not hold the Ask
    expect(log).toContain('stop');
    expect(log).not.toContain('presets');
  });

  it('a slow mic permission prompt does not use up the 8 s timer, and the beep comes after the mic opens (item 2)', async () => {
    let grant: () => void = () => {};
    const { live, sockets, log } = setup({
      openMic: (on) => new Promise((res) => {
        grant = () => { log.push('mic:open'); res({ stop: () => log.push('mic:stop') }); };
        void on;
      }),
    });
    const a = live.ask(700);
    const s = sockets[0] as FakeSocket;
    s.server({ type: 'ready' });
    await flush();
    s.server({ type: 'listening' });
    await vi.advanceTimersByTimeAsync(20_000);           // the fan reads the permission prompt
    expect(log).not.toContain('earcon:listen');
    expect(log.some((l) => l.startsWith('clip:'))).toBe(false);
    grant();
    await flush();
    expect(log.indexOf('mic:open')).toBeLessThan(log.indexOf('earcon:listen'));
    await vi.advanceTimersByTimeAsync(ANSWER_TIMEOUT_MS - 1);
    expect(log).not.toContain('clip:live_not_heard');
    await vi.advanceTimersByTimeAsync(1);
    await a;
    expect(log).toEqual(expect.arrayContaining(['mic:stop', 'clip:live_not_heard', 'presets']));
  });

  it('nobody speaks: "I didn\'t catch a question", then presets', async () => {
    const { live, sockets, log } = setup();
    const a = live.ask(700);
    const s = sockets[0] as FakeSocket;
    s.server({ type: 'ready' });
    await flush();
    s.server({ type: 'listening' });
    await flush();
    await vi.advanceTimersByTimeAsync(ANSWER_TIMEOUT_MS);
    await a;
    expect(s.json().map((m) => m.type)).toContain('cancel');
    expect(log).toEqual(expect.arrayContaining(['mic:stop', 'clip:live_not_heard', 'presets']));
  });

  it('no answer audio within 8 s of the end of speech: presets', async () => {
    const { live, sockets, log } = setup();
    const a = live.ask(700);
    const s = sockets[0] as FakeSocket;
    s.server({ type: 'ready' });
    await flush();
    s.server({ type: 'listening' });
    await flush();
    s.server({ type: 'speech_started' });
    s.server({ type: 'speech_stopped' });
    await vi.advanceTimersByTimeAsync(ANSWER_TIMEOUT_MS - 1);
    expect(log).not.toContain('presets');
    await vi.advanceTimersByTimeAsync(1);
    await a;
    expect(log).toEqual(expect.arrayContaining(['clip:live_unavailable', 'presets']));
  });

  it('the relay drops mid-question: presets', async () => {
    const { live, sockets, log } = setup();
    const a = live.ask(700);
    const s = sockets[0] as FakeSocket;
    s.server({ type: 'ready' });
    await flush();
    s.server({ type: 'listening' });
    await flush();
    s.onclose?.();
    await a;
    expect(log).toEqual(expect.arrayContaining(['mic:stop', 'clip:live_unavailable', 'presets']));
  });

  it('a session cap is spoken and sends the fan to the presets', async () => {
    const { live, sockets, log } = setup();
    const a = live.ask(700);
    const s = sockets[0] as FakeSocket;
    s.server({ type: 'ready' });
    await flush();
    s.server({ type: 'refusal', reason: 'session_cap', clip: 'live_session_cap', say: 'x' });
    await a;
    expect(log.slice(-2)).toEqual(['clip:live_session_cap', 'presets']);
    expect(s.closed).toBe(true);
  });

  it('cancel() stops the answer at once and does not open the presets', async () => {
    const { live, sockets, log } = setup();
    const a = live.ask(700);
    const s = sockets[0] as FakeSocket;
    s.server({ type: 'ready' });
    await flush();
    s.server({ type: 'listening' });
    await flush();
    s.server({ type: 'speech_stopped' });
    s.server(new ArrayBuffer(48));
    live.cancel();
    await a;
    expect(s.json().map((m) => m.type)).toContain('cancel');
    expect(log).toContain('stop');
    expect(log).not.toContain('presets');
  });

  it('set_preferences reaches the page', async () => {
    const { live, sockets, log } = setup();
    void live.ask(700);
    const s = sockets[0] as FakeSocket;
    s.server({ type: 'ready' });
    await flush();
    s.server({ type: 'tool', name: 'set_preferences', say: 'Done.', prefs: { crowd_mix: 0.2 } });
    expect(log).toContain('prefs:{"crowd_mix":0.2}');
  });
});

describe("browserIO: B's services, not DOM clicks or window events", () => {
  it('opens the presets, pings the ball and applies prefs through LaneBContext (contracts/stage.ts)', () => {
    const calls: string[] = [];
    const io = browserIO({ audio: () => null, base: '/b', lane: {
      ask: { registerLiveMode() {}, showPresets: () => calls.push('presets') },
      pingBall: () => calls.push('ping'),
      applyPrefs: (p) => calls.push(`prefs:${JSON.stringify(p)}`),
    } });
    io.showPresets();
    io.ping?.();
    io.prefs?.({ haptics: 'events' });
    expect(calls).toEqual(['presets', 'ping', 'prefs:{"haptics":"events"}']);
  });
  it('is safe with an older context that lacks the optional members', () => {
    const io = browserIO({ audio: () => null, base: '/b', lane: { ask: { registerLiveMode() {} } } });
    expect(() => { io.showPresets(); io.ping?.(); io.prefs?.({}); }).not.toThrow();
  });
  it('a mic worklet that failed to load is tried again on the next question (item 7)', async () => {
    let loads = 0, trackStops = 0;
    const ctx = Object.assign(new FakeAudioContext(), {
      state: 'running', resume: async () => {},
      audioWorklet: { addModule: async () => { loads++; if (loads === 1) throw new Error('worklet blocked'); } },
      createMediaStreamSource: () => ({ connect: <T>(n: T) => n, disconnect() {} }),
    });
    vi.stubGlobal('navigator', { mediaDevices: { getUserMedia: async () => ({ getTracks: () => [{ stop: () => { trackStops++; } }] }) } });
    vi.stubGlobal('AudioWorkletNode', class { port = { onmessage: null }; connect(n: unknown) { return n; } disconnect() {} });
    const createObjectURL = URL.createObjectURL;
    URL.createObjectURL = () => 'blob:mic';
    try {
      const io = browserIO({ audio: () => ctx as unknown as AudioContext, base: '/b', lane: { ask: { registerLiveMode() {} } } });
      await expect(io.openMic(() => {})).rejects.toThrow('worklet blocked');
      expect(trackStops).toBe(1);                        // the mic does not stay on after the failure
      const mic = await io.openMic(() => {});
      expect(loads).toBe(2);
      mic.stop();
    } finally {
      URL.createObjectURL = createObjectURL;
      vi.unstubAllGlobals();
    }
  });
});

describe('liveRelayUrl', () => {
  const cfg = (relay: unknown) => async () => ({ relay });
  it('reads /live.json and turns it into the wss /voice URL', async () => {
    expect(await liveRelayUrl('', cfg('https://ca-relay.example.io/'))).toBe('wss://ca-relay.example.io/voice');
  });
  it('lets ?debug=1&relay= point at a local relay', async () => {
    expect(await liveRelayUrl('?debug=1&relay=http://localhost:8080', cfg(null))).toBe('ws://localhost:8080/voice');
    expect(await liveRelayUrl('?relay=http://localhost:8080', cfg(null))).toBeNull();   // only in debug
  });
  it('is off with ?live=0, without config, or with a bad URL', async () => {
    expect(await liveRelayUrl('?live=0', cfg('https://x.io'))).toBeNull();
    expect(await liveRelayUrl('', async () => { throw new Error('404'); })).toBeNull();
    expect(await liveRelayUrl('', cfg('javascript:alert(1)'))).toBeNull();
  });
});
