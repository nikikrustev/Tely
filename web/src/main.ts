// OWNER: B (Nikolay). Builds lane B's services, mounts lane A once, and runs the judge-cut sound stage on Start.
import type { LaneAHandle } from './contracts/a-exports';
import type { CrowdBus, LaneBContext, ReplayClock } from './contracts/b-exports';
import { mountLaneA } from './lane-a';
import { clipOver, listenClip } from './replay/listen';

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
    hap, settingsMod, { loadChapters, nextChapter }, askMod, { LocalTools, loadQaBundle }] = await Promise.all([
    import('./audio/audio-stands'), import('./audio/crowd-engine'), import('./replay/replay-source'), import('./wire'),
    import('./replay/debug'), import('./haptics/haptics'), import('./settings'), import('./replay/chapters'),
    import('./ask/ask'), import('./ask/local-tools')]);
  const { loadSettings, saveSettings, crowdGainFor, prefsPatch } = settingsMod;
  const clip = listenClip(location.search);              // listening-test clip (eval/listening_test.md), if any
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
  const lazyAsk = new askMod.LazyAsk();                 // A may register its live voice mode right at boot
  // The ball ping and settings exist only once Start / settings code below has run; until then they do nothing.
  const laneB = { pingBall: () => {}, applyPrefs: (_p: Record<string, unknown>) => {} };
  const lane = boot({ crowd: crowdBus, ask: lazyAsk, clock,
    pingBall: () => laneB.pingBall(), applyPrefs: (p) => laneB.applyPrefs(p) });

  // ---- settings (work without storage) ----
  let settings = loadSettings();
  const haptics = new hap.Haptics(hap.browserEnv());
  const applyHaptics = () => {
    haptics.s = { mode: clip.commentaryOnly ? 'off' : settings.haptics, strength: settings.hapticStrength, myTeam: settings.club === 'H' ? 'home' : 'away' };
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
  // The live commentator's set_preferences ("turn the crowd down", "only vibrate for big moments"): same path as the
  // controls, then the controls show it and the fan hears what changed.
  const HAPTIC_SAID = { off: 'Vibration off.', events: 'Vibration for key moments only.', full: 'Vibration for the heartbeat and key moments.' };
  laneB.applyPrefs = (p) => {
    const patch = prefsPatch(p);
    if (!Object.keys(patch).length) return;
    update(patch);
    for (const r of radios('haptics')) r.checked = r.value === settings.haptics;
    crowdSlider.value = String(Math.round(settings.crowdMix * 100));
    const said = [patch.haptics ? HAPTIC_SAID[patch.haptics] : '', patch.crowdMix !== undefined ? `Crowd level ${crowdSlider.value} percent.` : ''];
    say(said.filter(Boolean).join(' '));
  };
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
  laneB.pingBall = () => stands?.pingBall();
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

  // ---- Ask the commentator (Stage 6) ----
  const askBtn = $<HTMLButtonElement>('ask'), askMenu = $('ask-menu'), askLive = $<HTMLButtonElement>('ask-live');
  let askCtl: InstanceType<typeof askMod.AskController> | null = null;
  const openMenu = (open: boolean) => {
    askMenu.hidden = !open;
    askBtn.setAttribute('aria-expanded', String(open));
    if (open) askMenu.querySelector<HTMLButtonElement>('button:not([hidden])')?.focus();
  };
  askBtn.addEventListener('click', () => openMenu(askMenu.hidden !== false));
  let presetsAfter = false;                             // A's live mode asked for the menu while its answer finished
  const runAsk = async (fn: () => Promise<unknown>) => {
    openMenu(false);
    askBtn.disabled = true;
    say('Answering.');                                   // state change only; the answer itself is heard
    try { await fn(); } finally {
      askBtn.disabled = false;
      if (presetsAfter) { presetsAfter = false; openMenu(true); } else askBtn.focus();
    }
  };
  lazyAsk.onShowPresets = () => {
    if (askBtn.disabled) presetsAfter = !!askCtl;        // busy: open once it finishes (never before Ask is ready)
    else openMenu(true);
  };
  for (const b of askMenu.querySelectorAll<HTMLButtonElement>('button[data-preset]')) {
    b.addEventListener('click', () => { if (askCtl) void runAsk(() => askCtl!.ask(b.dataset.preset as 'ball')); });
  }
  askLive.addEventListener('click', () => { if (askCtl) void runAsk(() => askCtl!.askLive()); });
  document.addEventListener('keydown', (e) => {
    const typing = (e.target as HTMLElement | null)?.closest('input, select, textarea');
    if (typing || e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.key === 'a' || e.key === 'A') { if (!askBtn.disabled) { e.preventDefault(); openMenu(askMenu.hidden !== false); } }
    else if (e.key === 'Escape' && !askMenu.hidden) { openMenu(false); askBtn.focus(); }
  });
  const setupAsk = async (actx: AudioContext, st: InstanceType<typeof AudioStands>, c: InstanceType<typeof CrowdEngine>,
                          s: InstanceType<typeof ReplaySource>) => {
    try {
      const tools = new LocalTools(await loadQaBundle());
      const player = new askMod.FragmentPlayer(actx, st.commentaryIn);
      await player.load();
      askCtl = new askMod.AskController({
        tools, clock: s, crowd: c, commentary: lane.commentary,
        speak: (f, text) => player.speak(f, text),
        ping: () => st.pingBall(),
        show: (text) => { status.textContent = text; },
      });
      lazyAsk.attach(askCtl);
      const ctl = askCtl;
      lazyAsk.onRegister = () => { askLive.hidden = !ctl.hasLive; };   // A's live mode may register later
      askLive.hidden = !ctl.hasLive;
      askBtn.disabled = false;
    } catch {
      askBtn.disabled = true;                            // no data: the button stays off rather than failing mid-match
    }
  };

  // ---- one audio setup, shared by Start, "Learn the sounds" and Bluetooth calibration (each needs a tap first) ----
  let audio: { ctx: AudioContext; st: InstanceType<typeof AudioStands>; c: InstanceType<typeof CrowdEngine> } | null = null;
  const ensureAudio = async () => {
    if (audio) { await audio.ctx.resume(); return audio; }
    const actx = new AudioContext({ latencyHint: 'balanced' });
    const nav = navigator as Navigator & { audioSession?: { type: string } };
    if (nav.audioSession) nav.audioSession.type = 'playback'; // iOS: play even with the silent switch on (file 37)
    await actx.resume();
    const st = new AudioStands(actx);
    const c = new CrowdEngine(actx, st.crowdIn, await loadCrowdBuffers(actx));
    c.setOutputGain(crowdGainFor(settings.crowdMix));
    crowdBus.target = c;
    c.start();
    audio = { ctx: actx, st, c };
    stands = st;
    crowd = c;
    return audio;
  };

  // ---- "Learn the sounds" (Stage 8 item 2): skippable guided tour on the Start screen ----
  const learnBtn = $<HTMLButtonElement>('learn');
  let tour: { skip(): void } | null = null;
  const stopTour = () => {
    if (!tour) return;
    tour.skip();
    if (typeof speechSynthesis !== 'undefined') speechSynthesis.cancel();   // stop mid-sentence, not after it
  };
  learnBtn.addEventListener('click', async () => {
    if (tour) { stopTour(); return; }
    const [{ Tour }, { speakFallback }] = await Promise.all([import('./learn/learn'), import('./ask/ask')]);
    const a = await ensureAudio();
    const t = new Tour({
      stage: {
        ball: (x, y, speed, at) => a.st.ballAt({ x, y, z: 0.11, speed, alive: true }, at),
        ballOff: (at) => a.st.ballAt({ x: 0, y: 0, z: 0.11, speed: 0, alive: false }, at),
        earcon: (kind, x, y, at) => { a.st.earcon(kind, x, y, at); },
        crowd: (e, at) => a.c.setState({ excitement: e, valence: 0.2, danger: e > 0.5 ? 0.6 : 0 }, at),
        heartbeat: (x) => { if (x > 0) haptics.setTension(x); else haptics.stopAll(); },
        now: () => a.ctx.currentTime,
      },
      speak: (text) => speakFallback(text),                 // the browser's voice (no keys); fixed phrases only
      show: (text) => { status.textContent = text; },
    });
    tour = t;
    learnBtn.textContent = 'Skip the tour';
    say('Sound tour started. Press Escape to skip.');
    try { await t.run(); } finally {
      tour = null;
      learnBtn.textContent = 'Learn the sounds again';
      say(t.skipped ? 'Tour skipped. Press Start to hear the match.' : 'Tour finished. Press Start to hear the match.');
      start.focus();
    }
  });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && tour) stopTour(); });

  // ---- Bluetooth calibration (Stage 8 item 3) ----
  const calBtn = $<HTMLButtonElement>('calibrate'), tapBtn = $<HTMLButtonElement>('tap'), cstatus = $('cstatus');
  const showOffset = () => {
    cstatus.textContent = settings.audioOffsetMs === null ? 'Not calibrated: using what the browser reports.'
      : `Your headphones add about ${settings.audioOffsetMs} milliseconds. Vibrations are timed for that.`;
  };
  showOffset();
  calBtn.addEventListener('click', async () => {
    const { Calibration, perfMapper } = await import('./haptics/calibrate');
    const a = await ensureAudio();
    const cal = new Calibration({
      click: (at) => { a.st.earcon('ping', 0, 0, at); },
      ctxNow: () => a.ctx.currentTime,
      toPerf: perfMapper(a.ctx),
      perfNow: () => performance.now(),
      wait: (ms) => new Promise((r) => setTimeout(r, ms)),
    });
    const onTap = () => cal.tap();
    tapBtn.addEventListener('click', onTap);
    calBtn.disabled = true;
    tapBtn.hidden = false;
    tapBtn.focus();
    cstatus.textContent = 'Listen for 8 beats and tap on each one.';
    await cal.play();
    tapBtn.removeEventListener('click', onTap);
    tapBtn.hidden = true;
    calBtn.disabled = false;
    const ms = cal.finish();
    if (ms === null) {
      cstatus.textContent = 'Not enough taps on the beat. Please try again.';
    } else {
      update({ audioOffsetMs: ms });
      showOffset();
    }
    say(cstatus.textContent ?? '');
    calBtn.focus();
  });

  // ---- sound radar (Stage 8 item 1): ?radar=1 or Settings ----
  const radarToggle = $<HTMLInputElement>('radar-toggle');
  const radarWanted = () => settings.radar || new URLSearchParams(location.search).get('radar') === '1';
  radarToggle.checked = radarWanted();
  let radar: { stop(): void } | null = null;
  const syncRadar = async () => {
    if (!src || !radarWanted()) { radar?.stop(); radar = null; return; }
    if (radar) return;
    const { startRadar, parseVtt } = await import('./radar/radar');
    let cues: ReturnType<typeof parseVtt> = [];
    try { cues = parseVtt(await (await fetch('/replay/v1/judge/captions_sdh.vtt')).text()); } catch { cues = []; }
    const s = src;
    // SEAM(B->A): reads A's captions_sdh.vtt (same seconds as the playhead) for the radar's caption line
    radar = startRadar($('radar'), { now: () => s.now(), doc: s.doc, pulses: () => haptics.played.length, cues,
      reducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches });
  };
  radarToggle.addEventListener('change', () => { update({ radar: radarToggle.checked }); void syncRadar(); });

  const pause = async (said: string) => {
    if (!src || !ctx) return;
    src.pause();
    lane.commentary.pause(); // SEAM(B->A): CommentaryTrack.pause() (contracts/a-exports.ts)
    dropQueued();
    src.seek(src.now(), 0); // re-queue from the exact pause point on resume
    await ctx.suspend();
    start.textContent = 'Play';
    say(said);
  };

  start.addEventListener('click', async () => {
    if (!ctx) {
      start.disabled = true;
      stopTour();
      learnBtn.hidden = true;
      say('Loading the stadium…');
      const a = await ensureAudio();
      ctx = a.ctx;
      const st = a.st, c = a.c;
      const [doc, ch] = await Promise.all([loadSegments(), loadChapters()]);
      chapters = ch;
      const s = new ReplaySource(ctx, doc);
      src = s;
      clock.attach(s);
      if (clip.commentaryOnly) st.master.gain.value = 0;   // crowd, ball and earcons off; A's voice has its own context
      if (clip.from !== null) s.seek(clip.from);
      const wired = wire(s, st, c, settings.club, undefined, {
        club: () => settings.club,
        haptics,
        outputDelayMs: () => settings.audioOffsetMs ?? st.outputDelay * 1000,   // calibrated delay wins
        onSecond: (sec) => {
          const line = scoreLine(sec.score);
          if (lastScore && line !== lastScore) say(line);
          lastScore = line;
        },
      });
      w = wired;
      hap.keepAwake();
      s.play();
      wired.pump();
      let clipEnded = false;
      setInterval(() => {
        wired.pump();
        if (!clipEnded && clipOver(clip, s.now())) {   // once: pressing Play again carries on past the clip
          clipEnded = true;
          void pause('End of the clip.');
        }
      }, 250);
      void setupAsk(ctx, st, c, s);
      void syncRadar();
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
      await pause('Paused.');
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
