// OWNER: B (Nikolay). Builds lane B's services, mounts lane A once, and runs the judge-cut sound stage on Start.
import type { LaneAHandle } from './contracts/a-exports';
import type { CrowdBus, LaneBContext, LiveAskHandler, ReplayClock } from './contracts/b-exports';
import { mountLaneA } from './lane-a';

/** Placeholder services (tests, and before Start). */
export function createStubContext(): LaneBContext {
  return {
    crowd: { duck() {}, unduck() {} },
    ask: { registerLiveMode() {} },
    clock: { now: () => 0, isPlaying: () => false, onChange: () => () => {} },
  };
}

export function boot(ctx: LaneBContext = createStubContext()): LaneAHandle {
  // SEAM(B->A): the only call into A's lane (TEAM_SPLIT.md "The seams" point 3).
  return mountLaneA(ctx);
}

/** The crowd bus A gets at boot. Audio can only start on a tap, so it forwards to the engine once Start creates it. */
export class LazyCrowdBus implements CrowdBus {
  target: CrowdBus | null = null;
  duck(db: number, rampMs: number): void {
    this.target?.duck(db, rampMs);
  }
  unduck(rampMs: number): void {
    this.target?.unduck(rampMs);
  }
}

/** The replay clock A gets at boot; it follows the ReplaySource once Start creates it. */
export class LazyClock implements ReplayClock {
  private src: ReplayClock | null = null;
  private listeners = new Set<(playheadS: number, playing: boolean) => void>();
  attach(src: ReplayClock): void {
    this.src = src;
    src.onChange((p, playing) => this.listeners.forEach((l) => l(p, playing)));
  }
  now(): number {
    return this.src?.now() ?? 0;
  }
  isPlaying(): boolean {
    return this.src?.isPlaying() ?? false;
  }
  onChange(listener: (playheadS: number, playing: boolean) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }
}

async function startApp(): Promise<void> {
  const [{ AudioStands }, { CrowdEngine, loadCrowdBuffers }, { ReplaySource, loadSegments }, { wire }, { startDebugPanel }] =
    await Promise.all([import('./audio/audio-stands'), import('./audio/crowd-engine'), import('./replay/replay-source'),
      import('./wire'), import('./replay/debug')]);
  const $ = (id: string) => document.getElementById(id) as HTMLElement;
  const button = $('start') as HTMLButtonElement, status = $('status'), polite = $('sr-polite');
  const say = (text: string) => { status.textContent = text; polite.textContent = text; }; // state changes only
  const crowdBus = new LazyCrowdBus(), clock = new LazyClock();
  let live: LiveAskHandler | null = null;
  const lane = boot({ crowd: crowdBus, ask: { registerLiveMode: (h) => { live = h; } }, clock });
  void live;
  status.textContent = 'Ready. Press Start, or Enter, to hear the match.';

  let ctx: AudioContext | null = null;
  let src: InstanceType<typeof ReplaySource> | null = null;
  button.addEventListener('click', async () => {
    if (!ctx) {
      button.disabled = true;
      say('Loading the stadium…');
      ctx = new AudioContext({ latencyHint: 'balanced' });
      const nav = navigator as Navigator & { audioSession?: { type: string } };
      if (nav.audioSession) nav.audioSession.type = 'playback'; // iOS: play even with the silent switch on (file 37)
      await ctx.resume();
      const stands = new AudioStands(ctx);
      const [buffers, doc] = await Promise.all([loadCrowdBuffers(ctx), loadSegments()]);
      const crowd = new CrowdEngine(ctx, stands.crowdIn, buffers);
      crowdBus.target = crowd;
      src = new ReplaySource(ctx, doc);
      clock.attach(src);
      const w = wire(src, stands, crowd, 'H');
      crowd.start();
      src.play();
      w.pump();
      setInterval(() => w.pump(), 250);
      if (new URLSearchParams(location.search).get('debug') === '1') {
        const s = src;
        startDebugPanel($('debug'), { playhead: () => s.now(), crowdGain: () => crowd.level.gain.value, ballX: () => stands.last.x });
      }
      button.disabled = false;
      button.textContent = 'Pause';
      say('Playing. You are in the main stand, halfway line. Reds attack to your right.');
      return;
    }
    if (src?.isPlaying()) {
      src.pause();
      lane.commentary.pause();
      await ctx.suspend();
      button.textContent = 'Play';
      say('Paused.');
    } else if (src) {
      await ctx.resume();
      src.play(0);
      lane.commentary.resume();
      button.textContent = 'Pause';
      say('Playing.');
    }
  });
}

if (typeof document !== 'undefined') void startApp();
