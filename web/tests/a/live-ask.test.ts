// OWNER: A (potencialbg). The live Ask controller against a fake relay and fake browser IO (no mic, no network).
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { liveRelayUrl } from '../../src/lane-a';
import { ANSWER_TIMEOUT_MS, browserIO, DOWN_FOR_MS, LiveAsk, type LiveIO, type RelaySocket } from '../../src/lane-a/live-ask';
import { DEFAULT_MIX, levelFromDb, soundLevels } from '../../src/audio/mix';

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

function setup() {
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

  it('a relay that never answers: presets within 8 s', async () => {
    const { live, log } = setup();
    const a = live.ask(700);
    await vi.advanceTimersByTimeAsync(ANSWER_TIMEOUT_MS);
    await a;
    expect(log).toEqual(['clip:live_unavailable', 'presets']);
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
  it('opens the presets, pings the ball and applies prefs through LaneBContext (b-exports.ts)', () => {
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
