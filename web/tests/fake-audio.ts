// A small fake AudioContext for Node tests. AudioParam automation follows the Web Audio maths
// for setValueAtTime and setTargetAtTime (v -> target with exp(-dt / tau)), so tests can read a gain at any time.
// linearRampToValueAtTime is treated as a step at its end time (good enough for the checks here).

type Ev = { t: number; kind: 'set' | 'target'; value: number; tau?: number; seq: number };

export class FakeParam {
  private evs: Ev[] = [];
  private seq = 0;
  constructor(private ctx: { currentTime: number }, private initial = 0) {}
  get value(): number {
    return this.valueAt(this.ctx.currentTime);
  }
  set value(v: number) {
    if (this.evs.length === 0) this.initial = v;
    else this.push({ t: this.ctx.currentTime, kind: 'set', value: v });
  }
  setValueAtTime(value: number, t: number) { this.push({ t, kind: 'set', value }); return this; }
  linearRampToValueAtTime(value: number, t: number) { this.push({ t, kind: 'set', value }); return this; }
  exponentialRampToValueAtTime(value: number, t: number) { this.push({ t, kind: 'set', value }); return this; }
  setTargetAtTime(value: number, t: number, tau: number) { this.push({ t, kind: 'target', value, tau }); return this; }
  cancelScheduledValues(t: number) { this.evs = this.evs.filter((e) => e.t < t); return this; }
  cancelAndHoldAtTime(t: number) { return this.cancelScheduledValues(t); }
  private push(e: Omit<Ev, 'seq'>) {
    this.evs.push({ ...e, seq: this.seq++ });
    this.evs.sort((a, b) => a.t - b.t || a.seq - b.seq);
  }
  /** The value the param has at time t. */
  valueAt(t: number): number {
    let v = this.initial;
    let mode: { from: number; start: number; target: number; tau: number } | null = null;
    const at = (time: number) => (mode ? mode.target + (mode.from - mode.target) * Math.exp(-(time - mode.start) / mode.tau) : v);
    for (const e of this.evs) {
      if (e.t > t) break;
      v = at(e.t);
      if (e.kind === 'set') { v = e.value; mode = null; }
      else mode = { from: v, start: e.t, target: e.value, tau: e.tau ?? 0.1 };
    }
    return at(t);
  }
}

class FakeNode {
  constructor(protected ctx: FakeAudioContext) {}
  connect<T>(n: T): T { return n; }
  disconnect() {}
}

class FakeBuffer {
  private data: Float32Array[];
  constructor(readonly numberOfChannels: number, readonly length: number, readonly sampleRate: number) {
    this.data = Array.from({ length: numberOfChannels }, () => new Float32Array(length));
  }
  get duration() { return this.length / this.sampleRate; }
  getChannelData(c: number) { return this.data[c] as Float32Array; }
}

export class FakeAudioContext {
  currentTime = 0;
  sampleRate = 8000; // small, so generated buffers are cheap in tests
  started = 0;
  destination = new FakeNode(this);
  listener = Object.fromEntries(['positionX', 'positionY', 'positionZ', 'forwardX', 'forwardY', 'forwardZ', 'upX', 'upY', 'upZ']
    .map((k) => [k, new FakeParam(this)]));
  private p = (v = 0) => new FakeParam(this, v);
  createGain() { return Object.assign(new FakeNode(this), { gain: this.p(1) }); }
  createBiquadFilter() { return Object.assign(new FakeNode(this), { type: 'lowpass', frequency: this.p(350), Q: this.p(1), gain: this.p(0) }); }
  createStereoPanner() { return Object.assign(new FakeNode(this), { pan: this.p(0) }); }
  createPanner() {
    return Object.assign(new FakeNode(this), { positionX: this.p(), positionY: this.p(), positionZ: this.p(),
      panningModel: 'equalpower', distanceModel: 'inverse', refDistance: 1, rolloffFactor: 1, maxDistance: 10000 });
  }
  createDynamicsCompressor() {
    return Object.assign(new FakeNode(this), { threshold: this.p(), ratio: this.p(), attack: this.p(), release: this.p(), knee: this.p() });
  }
  createConvolver() { return Object.assign(new FakeNode(this), { buffer: null as unknown }); }
  createOscillator() { return Object.assign(new FakeNode(this), { type: 'sine', frequency: this.p(440), detune: this.p(), start() {}, stop() {} }); }
  createBufferSource() {
    const ctx = this;
    return Object.assign(new FakeNode(this), { buffer: null as unknown, loop: false, playbackRate: this.p(1), detune: this.p(),
      onended: null as unknown, start() { ctx.started++; }, stop() {} });
  }
  createBuffer(ch: number, n: number, sr: number) { return new FakeBuffer(ch, Math.max(1, n), sr); }
}

/** The fake, typed as the real thing for code under test. */
export const asCtx = (f: FakeAudioContext) => f as unknown as BaseAudioContext;
export const paramOf = (p: AudioParam) => p as unknown as FakeParam;
