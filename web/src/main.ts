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

/** "Reds 1, Navy 0." The score announcement (a state change, file 32): spoken only when it changes. */
export function scoreLine(score: { home: number; away: number }): string {
  return `Reds ${score.home}, Navy ${score.away}.`;
}

async function startApp(): Promise<void> {
  const [{ AudioStands }, { CrowdEngine, loadCrowdBuffers }, { ReplaySource, loadSegments }, { wire }, { startDebugPanel },
    hap, settingsMod, { loadChapters, nextChapter }] = await Promise.all([
    import('./audio/audio-stands'), import('./audio/crowd-engine'), import('./replay/replay-source'), import('./wire'),
    import('./replay/debug'), import('./haptics/haptics'), import('./settings'), import('./replay/chapters')]);
  const { loadSettings, saveSettings, crowdGainFor } = settingsMod;
  const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
  const start = $<HTMLButtonElement>('start'), next = $<HTMLButtonElement>('next'), toggle = $<HTMLButtonElement>('settings-toggle');
  const status = $('status'), polite = $('sr-polite'), panel = $('settings'), hstatus = $('hstatus');
  const say = (text: string) => {
    status.textContent = text;
    polite.textContent = ''; // clear first, so a repeated message is announced again
    setTimeout(() => { polite.textContent = text; }, 50);
  };

  // Lane A gets its services now; the audio ones forward once Start creates them.
  const crowdBus = new LazyCrowdBus(), clock = new LazyClock();
  let live: LiveAskHandler | null = null;
  const lane = boot({ crowd: crowdBus, ask: { registerLiveMode: (h) => { live = h; } }, clock });
  void live; // Stage 6/7: the Ask button uses it

  // ---- settings (work without storage) ----
  let settings = loadSettings();
  const haptics = new hap.Haptics(hap.browserEnv());
  const applyHaptics = () => {
    haptics.s = { mode: settings.haptics, strength: settings.hapticStrength, myTeam: settings.club === 'H' ? 'home' : 'away' };
  };
  applyHaptics();
  let crowd: InstanceType<typeof CrowdEngine> | null = null;
  const radios = (name: string) => [...document.querySelectorAll<HTMLInputElement>(`input[name="${name}"]`)];
  for (const r of radios('club')) r.checked = r.value === settings.club;
  for (const r of radios('haptics')) r.checked = r.value === settings.haptics;
  const crowdSlider = $<HTMLInputElement>('crowd'), strength = $<HTMLSelectElement>('strength');
  crowdSlider.value = String(Math.round(settings.crowdMix * 100));
  strength.value = String(settings.hapticStrength);
  const update = (patch: Partial<typeof settings>) => {
    settings = { ...settings, ...patch };
    saveSettings(settings);
    applyHaptics();
    crowd?.setOutputGain(crowdGainFor(settings.crowdMix));
  };
  for (const r of radios('club')) {
    r.addEventListener('change', () => {
      update({ club: r.value === 'A' ? 'A' : 'H' });
      say(r.value === 'A' ? 'You are now with the Navy fans.' : 'You are now with the Reds fans.');
    });
  }
  for (const r of radios('haptics')) r.addEventListener('change', () => update({ haptics: r.value as typeof settings.haptics }));
  crowdSlider.addEventListener('input', () => update({ crowdMix: Number(crowdSlider.value) / 100 }));
  strength.addEventListener('change', () => update({ hapticStrength: Number(strength.value) }));
  toggle.addEventListener('click', () => {
    const open = panel.hidden;
    panel.hidden = !open;
    toggle.setAttribute('aria-expanded', String(open));
    if (open) panel.querySelector<HTMLInputElement>('input:checked')?.focus();
  });
  $('htest').addEventListener('click', () => { // also the sticky-activation tap Android needs (file 41)
    if (!haptics.available) { hstatus.textContent = hap.NO_VIBRATION_MESSAGE; return; }
    const was = haptics.s;
    haptics.s = { ...was, mode: 'full' };
    haptics.event('goal', 'home', 0);
    haptics.s = was;
    hstatus.textContent = 'Playing the home goal pattern. Did you feel it?';
  });
  if (!haptics.available) hstatus.textContent = hap.NO_VIBRATION_MESSAGE;
  status.textContent = 'Ready. Press Start, or Enter, to hear the match.';

  // ---- playback ----
  let ctx: AudioContext | null = null;
  let src: InstanceType<typeof ReplaySource> | null = null;
  let stands: InstanceType<typeof AudioStands> | null = null;
  let w: ReturnType<typeof wire> | null = null;
  let chapters: Awaited<ReturnType<typeof loadChapters>> = [];
  let lastScore = '';
  /** Throw away everything queued ahead (pause, jump) so nothing stale plays; the pump re-queues from the playhead. */
  const dropQueued = () => {
    if (!ctx) return;
    crowd?.cancelFrom(ctx.currentTime);
    stands?.cancelFrom(ctx.currentTime);
    w?.cancel();
    haptics.stopAll();
  };

  start.addEventListener('click', async () => {
    if (!ctx) {
      start.disabled = true;
      say('Loading the stadium…');
      ctx = new AudioContext({ latencyHint: 'balanced' });
      const nav = navigator as Navigator & { audioSession?: { type: string } };
      if (nav.audioSession) nav.audioSession.type = 'playback'; // iOS: play even with the silent switch on (file 37)
      await ctx.resume();
      const st = new AudioStands(ctx);
      stands = st;
      const [buffers, doc, ch] = await Promise.all([loadCrowdBuffers(ctx), loadSegments(), loadChapters()]);
      chapters = ch;
      const c = new CrowdEngine(ctx, st.crowdIn, buffers);
      crowd = c;
      c.setOutputGain(crowdGainFor(settings.crowdMix));
      crowdBus.target = c;
      const s = new ReplaySource(ctx, doc);
      src = s;
      clock.attach(s);
      const wired = wire(s, st, c, settings.club, undefined, {
        club: () => settings.club,
        haptics,
        outputDelayMs: () => st.outputDelay * 1000,
        onSecond: (sec) => {
          const line = scoreLine(sec.score);
          if (lastScore && line !== lastScore) say(line);
          lastScore = line;
        },
      });
      w = wired;
      c.start();
      hap.keepAwake();
      s.play();
      wired.pump();
      setInterval(() => wired.pump(), 250);
      if (new URLSearchParams(location.search).get('debug') === '1') {
        startDebugPanel($('debug'), { playhead: () => s.now(), crowdGain: () => c.level.gain.value, ballX: () => st.last.x });
      }
      start.disabled = false;
      next.disabled = chapters.length === 0;
      start.textContent = 'Pause';
      say('Playing. You are in the main stand, on the halfway line. Reds attack to your right.');
      return;
    }
    if (!src) return;
    if (src.isPlaying()) {
      src.pause();
      lane.commentary.pause(); // SEAM(B->A): CommentaryTrack.pause() (contracts/a-exports.ts)
      dropQueued();
      src.seek(src.now(), 0); // re-queue from the exact pause point on resume
      await ctx.suspend();
      start.textContent = 'Play';
      say('Paused.');
    } else {
      await ctx.resume();
      src.play(0.1);
      lane.commentary.resume(); // SEAM(B->A): CommentaryTrack.resume()
      w?.pump();
      start.textContent = 'Pause';
      say('Playing.');
    }
  });

  next.addEventListener('click', () => {
    if (!src || !ctx) return;
    const ch = nextChapter(chapters, src.now());
    if (!ch) { say('No more big moments in this match.'); return; }
    const playing = src.isPlaying();
    lane.commentary.pause(); // SEAM(B->A): stop the current line; the clock change below re-anchors A's track
    dropQueued();
    src.seek(ch.t);
    // One announcement for the jump, with the score there (a jump may skip a goal); not repeated a second later.
    const sec = src.doc.segments.flatMap((g) => g.seconds).find((x) => x.t >= Math.floor(ch.t));
    if (sec) lastScore = scoreLine(sec.score);
    if (playing) {
      w?.pump();
      lane.commentary.resume();
    }
    say(sec ? `${ch.label}. ${lastScore}` : `${ch.label}.`);
  });
}

if (typeof document !== 'undefined') void startApp();
