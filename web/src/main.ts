// OWNER: B (Nikolay). Builds lane B's services, mounts lane A once, and runs the judge-cut sound stage on Start.
import type { LaneAHandle } from './contracts/a-exports';
import type { CrowdBus, LaneBContext, ReplayClock } from './contracts/b-exports';
import { mountLaneA } from './lane-a';
import { clipOver, listenClip, type ListenClip } from './replay/listen';
import { loadClockOffset, Scoreboard } from './scoreboard';
import type { TesterHandle } from './tester';

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
  let clip = listenClip(location.search);                // listening-test clip (eval/listening_test.md), if any
  // Tester mode (?test=1, D19) only: web/src/tester/ drives the clips. Without it, `tester` stays null throughout.
  const testerMode = new URLSearchParams(location.search).get('test') === '1';
  let tester: TesterHandle | null = null;
  const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
  const start = $<HTMLButtonElement>('start'), next = $<HTMLButtonElement>('next'), toggle = $<HTMLButtonElement>('settings-toggle');
  const status = $('status'), polite = $('sr-polite'), panel = $('settings'), hstatus = $('hstatus');
  const say = (text: string) => {
    status.textContent = text;
    polite.textContent = ''; // clear first, so a repeated message is announced again
    setTimeout(() => { polite.textContent = text; }, 50);
  };
  // The match card (score, clock, chapter): for sighted viewers; the listener hears the same changes through say().
  const board = new Scoreboard($('match'));
  void loadClockOffset().then((o) => { if (o !== null) board.offsetS = o; });

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
  status.textContent = 'Ready. Press Start, the lower big button, to hear the match.';

  // ---- playback ----
  let ctx: AudioContext | null = null;
  let src: InstanceType<typeof ReplaySource> | null = null;
  let stands: InstanceType<typeof AudioStands> | null = null;
  laneB.pingBall = () => stands?.pingBall();
  let w: ReturnType<typeof wire> | null = null;
  let chapters: Awaited<ReturnType<typeof loadChapters>> = [];
  let lastScore = '';
  /** The second at or after playhead t (its score is the score there). */
  const secondAt = (t: number) => src?.doc.segments.flatMap((g) => g.seconds).find((x) => x.t >= Math.floor(t));
  /** Throw away everything queued ahead (pause, jump) so nothing stale plays; the pump re-queues from the playhead. */
  const dropQueued = () => {
    if (!ctx) return;
    crowd?.cancelFrom(ctx.currentTime);
    stands?.cancelFrom(ctx.currentTime);
    w?.cancel();
    haptics.stopAll();
  };

  // ---- press feedback (D24): every pad press is felt (Android) and heard, so nothing depends on seeing the screen ----
  const vibrate = hap.browserEnv().vibrate;
  type Press = 'ask' | 'stop' | 'pause' | 'resume' | 'start' | 'not-yet';
  const BUZZ: Record<Press, number[]> = { ask: [25], stop: [15, 40, 15], pause: [40], resume: [20, 30, 20], start: [40], 'not-yet': [60, 50, 60] };
  // [from Hz, to Hz]: rising for "go", falling for "stop"; a low double for "not yet". Quiet, under the match.
  const TONE: Partial<Record<Press, [number, number]>> = { ask: [520, 620], stop: [620, 440], pause: [560, 380], resume: [380, 560] };
  const feedback = (kind: Press) => {
    if (settings.haptics !== 'off') { try { vibrate?.(BUZZ[kind]); } catch { /* not allowed yet */ } }
    const c = audio?.ctx, tone = TONE[kind];
    if (!c || c.state !== 'running' || !tone) return;
    const osc = c.createOscillator(), g = c.createGain(), at = c.currentTime + 0.005;
    osc.frequency.setValueAtTime(tone[0], at);
    osc.frequency.linearRampToValueAtTime(tone[1], at + 0.09);
    g.gain.setValueAtTime(0, at);
    g.gain.linearRampToValueAtTime(0.08, at + 0.01);
    g.gain.linearRampToValueAtTime(0, at + 0.11);
    osc.connect(g).connect(c.destination);
    osc.start(at);
    osc.stop(at + 0.12);
  };
  /** A pad's visible words are its accessible name; the hint under it is its description. */
  const setPad = (b: HTMLButtonElement, label: string, state: string, hint: string) => {
    const l = b.querySelector('.pad-label');
    if (l) l.textContent = label; else b.textContent = label;
    b.dataset.state = state;
    const h = document.getElementById(b.getAttribute('aria-describedby') ?? '');
    if (h) h.textContent = hint;
  };

  // ---- Ask the commentator (Stage 6) ----
  const askBtn = $<HTMLButtonElement>('ask'), askMenu = $('ask-menu'), askLive = $<HTMLButtonElement>('ask-live');
  let askCtl: InstanceType<typeof askMod.AskController> | null = null;
  // aria-disabled, not disabled: before the match the fan can still find the pad by touch and hear why it waits.
  let askReady = false;
  const ASK_LABEL = 'Ask the commentator', STOP_LABEL = 'Stop the answer';
  const askHint = () => (askCtl?.hasLive ? 'Tap, wait for the beep, then speak' : 'Tap for quick questions');
  const setAskReady = (on: boolean) => {
    askReady = on;
    askBtn.setAttribute('aria-disabled', String(!on));
    setPad(askBtn, ASK_LABEL, 'ask', on ? askHint() : 'Works once the match starts');
    if (!askCtl?.hasLive) askBtn.setAttribute('aria-expanded', String(!askMenu.hidden));   // presets: it opens the menu
    else if (askMenu.hidden) askBtn.removeAttribute('aria-expanded');
  };
  const openMenu = (open: boolean) => {
    askMenu.hidden = !open;
    // With live Ask the pad asks straight away, so it only "expands" while the menu is actually open.
    if (open || !askCtl?.hasLive) askBtn.setAttribute('aria-expanded', String(open));
    else askBtn.removeAttribute('aria-expanded');
    if (open) askMenu.querySelector<HTMLButtonElement>('button:not([hidden])')?.focus();
  };
  // Press-to-interrupt (file 49): during an answer the same pad (or A) stops it at once, with the commentary still
  // paused for the next question; Escape stops it and goes straight back to the action.
  const HOLD_IDLE_MS = 10_000;                          // no next question after a stop: back to the match anyway
  let presetsAfter = false;                             // A's live mode asked for the menu while its answer finished
  let menuAfter = false;                                // the fan stopped an answer to pick another preset
  let holdTimer: ReturnType<typeof setTimeout> | null = null;
  const runAsk = async (fn: () => Promise<unknown>, live = false) => {
    openMenu(false);
    if (holdTimer) { clearTimeout(holdTimer); holdTimer = null; }
    setPad(askBtn, STOP_LABEL, 'stop', 'Tap to stop the answer');   // the pad stays live: pressing it interrupts
    askBtn.focus();
    // A live question opens the mic: a screen reader announcement now would be heard as the question, so the fan
    // gets the beep instead and the status line is visual only. Presets announce "Answering." (a state change).
    if (live) status.textContent = 'Listening. Speak after the beep.';
    else say('Answering.');
    try { await fn(); } finally {
      setPad(askBtn, ASK_LABEL, 'ask', askHint());
      if (presetsAfter || menuAfter) {
        presetsAfter = menuAfter = false;
        openMenu(true);
      } else askBtn.focus();
      if (askCtl?.isHolding) {
        if (askMenu.hidden) say('Stopped. Tap Ask to ask again, or wait to go back to the match.');
        holdTimer = setTimeout(() => { if (askCtl?.isHolding) closeMenu(); }, HOLD_IDLE_MS);
      }
    }
  };
  /** Close the menu. If the commentary is held after a stop, that means "back to the action". */
  const closeMenu = () => {
    openMenu(false);
    askBtn.focus();
    if (askCtl?.isHolding) void runAsk(() => askCtl!.release());
  };
  const notYet = () => { feedback('not-yet'); say('The match hasn\'t started. Start is the bottom half of the screen.'); };
  const pressAsk = () => {
    if (!askReady) { notYet(); return; }
    if (askCtl?.isBusy) {
      feedback('stop');
      const stopped = askCtl.interrupt('listen');
      menuAfter = stopped && !askCtl.hasLive;            // presets only: show them again for the next pick
      return;
    }
    if (!askMenu.hidden) { closeMenu(); return; }
    feedback('ask');
    // D24: one press, then speak. Without live Ask (no relay, or ?live=0) the pad opens the quick questions.
    if (askCtl?.hasLive) void runAsk(() => askCtl!.askLive(), true);
    else openMenu(true);
  };
  askBtn.addEventListener('click', pressAsk);
  $('presets-open').addEventListener('click', () => { if (!askReady) notYet(); else if (!askCtl?.isBusy) openMenu(true); });
  $('ask-close').addEventListener('click', closeMenu);
  lazyAsk.onShowPresets = () => {
    if (!askCtl) return;                                 // never before Ask is ready
    if (askCtl.isBusy) presetsAfter = true;              // busy: open once it finishes
    else openMenu(true);
  };
  for (const b of askMenu.querySelectorAll<HTMLButtonElement>('button[data-preset]')) {
    b.addEventListener('click', () => { if (askCtl) void runAsk(() => askCtl!.ask(b.dataset.preset as 'ball')); });
  }
  askLive.addEventListener('click', () => { if (askCtl) void runAsk(() => askCtl!.askLive(), true); });
  document.addEventListener('keydown', (e) => {
    const typing = (e.target as HTMLElement | null)?.closest('input, select, textarea');
    if (typing || e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.key === 'a' || e.key === 'A') { if (askReady) { e.preventDefault(); pressAsk(); } }
    else if (e.key === 'Escape') {
      if (askCtl?.isBusy) askCtl.interrupt('back');
      else if (!askMenu.hidden || askCtl?.isHolding) closeMenu();
    }
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
        stop: () => player.stop(),
        ping: () => st.pingBall(),
        show: (text) => { status.textContent = text; },
      });
      lazyAsk.attach(askCtl);
      const ctl = askCtl;
      lazyAsk.onRegister = () => { askLive.hidden = !ctl.hasLive; setAskReady(askReady); };   // live may register later
      askLive.hidden = !ctl.hasLive;
      setAskReady(true);
    } catch {
      setAskReady(false);                                // no data: the pad stays off rather than failing mid-match
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
        ball: (x, y, speed, at) => { a.st.ballAt({ x, y, z: 0.11, speed, alive: true }, at); a.c.followBall(x, at); },
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
      if (tester) tester.tourEnded(t.skipped);           // the tester's task panel says what comes next
      else {
        say(t.skipped ? 'Tour skipped. Press Start to hear the match.' : 'Tour finished. Press Start to hear the match.');
        start.focus();
      }
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
    setPad(start, 'Resume', 'resume', 'Carries on from where you paused');
    board.update({ state: 'Paused' });
    say(said);
  };

  let clipEnded = false;
  start.addEventListener('click', async () => {
    if (!ctx) {
      feedback('start');
      start.disabled = true;
      stopTour();
      learnBtn.hidden = true;
      board.update({ state: 'Loading' });
      say('Loading the stadium…');
      const a = await ensureAudio();
      ctx = a.ctx;
      const st = a.st, c = a.c;
      const [doc, ch] = await Promise.all([loadSegments(), loadChapters()]);
      chapters = ch;
      board.chapters = ch;
      const s = new ReplaySource(ctx, doc);
      src = s;
      clock.attach(s);
      if (clip.commentaryOnly) st.master.gain.value = 0;   // crowd, ball and earcons off; A's voice has its own context
      if (clip.from !== null) s.seek(clip.from);
      board.update({ score: secondAt(s.now())?.score, playheadS: s.now() });
      const wired = wire(s, st, c, settings.club, undefined, {
        club: () => settings.club,
        haptics,
        outputDelayMs: () => settings.audioOffsetMs ?? st.outputDelay * 1000,   // calibrated delay wins
        onSecond: (sec) => {
          const line = scoreLine(sec.score);
          board.update({ score: sec.score });
          if (lastScore && line !== lastScore) say(line);
          lastScore = line;
        },
      });
      w = wired;
      hap.keepAwake();
      s.play();
      wired.pump();
      setInterval(() => {
        wired.pump();
        board.update({ playheadS: s.now() });
        if (!clipEnded && clipOver(clip, s.now())) {   // once: pressing Play again carries on past the clip
          clipEnded = true;
          void pause('End of the clip.').then(() => tester?.clipEnded());
        }
      }, 250);
      void setupAsk(ctx, st, c, s);
      void syncRadar();
      if (new URLSearchParams(location.search).get('debug') === '1') {
        startDebugPanel($('debug'), { playhead: () => s.now(), crowdGain: () => c.level.gain.value, ballX: () => st.last.x });
      }
      start.disabled = false;
      start.focus();                                     // disabled while loading dropped focus; give it back
      next.disabled = chapters.length === 0;
      setPad(start, 'Pause', 'pause', 'Pauses the match');
      board.update({ state: 'Playing' });
      say('Playing. You are in the main stand, on the halfway line. Reds attack to your right.');
      return;
    }
    if (!src) return;
    if (src.isPlaying()) {
      feedback('pause');
      // An answer running, or the commentary held for a next question: stop it quietly first, so nothing resumes
      // the commentary behind the pause.
      if (askCtl?.isBusy) {
        askCtl.interrupt('back');
        for (let i = 0; i < 50 && askCtl.isBusy; i++) await new Promise((r) => setTimeout(r, 20));
      }
      if (holdTimer) { clearTimeout(holdTimer); holdTimer = null; }
      askCtl?.dropHold();
      openMenu(false);
      await new Promise((r) => setTimeout(r, 120));      // let the press tone finish before the context stops
      await pause('Paused.');
    } else {
      await ctx.resume();
      feedback('resume');
      src.play(0.1);
      lane.commentary.resume(); // SEAM(B->A): CommentaryTrack.resume()
      w?.pump();
      setPad(start, 'Pause', 'pause', 'Pauses the match');
      board.update({ state: 'Playing' });
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
    const sec = secondAt(ch.t);
    if (sec) lastScore = scoreLine(sec.score);
    board.update({ score: sec?.score, playheadS: ch.t });
    if (playing) {
      w?.pump();
      lane.commentary.resume();
    }
    say(sec ? `${ch.label}. ${lastScore}` : `${ch.label}.`);
  });

  // ---- sound mixer (?mix=1): a testing tool, never loaded on the judges' page ----
  if (new URLSearchParams(location.search).get('mix') === '1') {
    const { mountMixer } = await import('./tester/mixer');
    mountMixer({ say });
  }

  if (!testerMode) return;
  // ---- tester mode (?test=1, D19) ----
  /** Play a clip from the tester's task list. Call it inside a tap: the first time it presses Start itself. */
  const playClip = (c: ListenClip) => {
    clip = c;
    clipEnded = false;
    applyHaptics();
    if (!ctx) { start.click(); return; }                 // Start's own path seeks to clip.from and mutes if needed
    if (!src || !audio) return;
    const s = src, wasPlaying = s.isPlaying();
    void audio.ctx.resume();
    lane.commentary.pause();                             // SEAM(B->A): stop the current line, re-anchor on the seek
    dropQueued();
    audio.st.master.gain.value = c.commentaryOnly ? 0 : 1;
    if (c.from !== null) s.seek(c.from);
    const sec = secondAt(s.now());
    if (sec) lastScore = scoreLine(sec.score);           // a jump is not a score change
    board.update({ score: sec?.score, playheadS: s.now(), state: 'Playing' });
    if (!wasPlaying) s.play(0.1);
    w?.pump();
    lane.commentary.resume();
    setPad(start, 'Pause', 'pause', 'Pauses the match');
    say('Playing.');
  };
  const { mountTester } = await import('./tester');
  tester = mountTester({
    playClip,
    clip: () => clip,
    runTour: () => { if (src?.isPlaying()) void pause('Paused.'); if (!tour) learnBtn.click(); },
    pause: () => { if (src?.isPlaying()) void pause('Paused.'); },
    playhead: () => (src ? src.now() : null),
    playing: () => !!src?.isPlaying(),
    settings: () => settings,
    say,
  });
}

if (typeof document !== 'undefined') void startApp();
