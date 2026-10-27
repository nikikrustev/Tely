// Tester mode (?test=1, D19): a guided test for friends who don't know the project.
// main.ts imports this only with ?test=1, so the judges' page never loads it. It clones #tester-tpl from
// index.html into the page, walks the tester through TASKS, and sends each answer to the relay (outbox.ts). The
// answers double as the self-run group of the eyes-closed listening test (eval/listening_test.md, mode=self).
// Accessibility as on the rest of the page (file 32): native controls, 44 px targets, focus moved to each new
// screen's heading, and the page's one polite status (#sr-polite, through main.ts say()) for state changes only.
import { liveRelayUrl } from '../voice';
import type { ListenClip } from '../replay/listen';
import { browserStorage, type Settings } from '../settings';
import { deliver, browserTransport, feedbackUrl } from './outbox';
import { answersText, baseEvent, fit, uaFamily, type Kind } from './payload';
import {
  ASK_WORKED, DEVICE, HEADPHONES, PREFERRED, PROBES, PROBLEM_KINDS, SCALE, SCREEN_READER, SETTINGS_EASY, SIGHT,
  scoreClip, type Choice, type ProbeId, type ScaleId,
} from './questions';
import {
  clipFor, loadState, nextTask, OPEN_PLAY_FROM, progress, saveState, setTask, TASKS, type Ev, type Task,
  type TaskStatus, type TesterState,
} from './state';

/** Where "Email my answers" goes. Empty: the link is not shown, and "Copy my answers" is the fallback. */
export const FEEDBACK_EMAIL = '';

export interface TesterHooks {
  /** Play a clip; call inside a tap (it may press Start). */
  playClip(c: ListenClip): void;
  clip(): ListenClip;
  runTour(): void;
  pause(): void;
  playhead(): number | null;
  playing(): boolean;
  settings(): Settings;
  /** main.ts say(): the page's one polite status. */
  say(text: string): void;
}

export interface TesterHandle {
  clipEnded(): void;
  tourEnded(skipped: boolean): void;
}

type Props = Record<string, string | boolean | number>;
function h<K extends keyof HTMLElementTagNameMap>(tag: K, props: Props = {}, ...kids: (Node | string)[]): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === 'text') e.textContent = String(v);
    else if (typeof v === 'boolean') { if (v) e.setAttribute(k, ''); }
    else e.setAttribute(k, String(v));
  }
  e.append(...kids);
  return e;
}

function radios(name: string, legend: string, choices: readonly Choice[], opts: { required?: boolean; value?: string; hint?: string } = {}): HTMLFieldSetElement {
  const fs = h('fieldset', {}, h('legend', { text: legend }));
  if (opts.hint) fs.append(h('p', { class: 't-hint', text: opts.hint }));
  choices.forEach(([id, label], i) => {
    const input = h('input', { type: 'radio', name, value: id, required: !!opts.required && i === 0 });
    input.checked = opts.value === id;
    fs.append(h('label', {}, input, ` ${label}`));
  });
  return fs;
}

function textarea(name: string, label: string, value = ''): HTMLDivElement {
  const id = `t-f-${name}`;
  const ta = h('textarea', { id, name, rows: 3, maxlength: 500 });
  ta.value = value;
  return h('div', { class: 't-field' }, h('label', { for: id, text: label }), ta);
}

const SCALE_CHOICES = (low: string, high: string): Choice[] =>
  [['1', `1, ${low}`], ['2', '2'], ['3', '3'], ['4', '4'], ['5', `5, ${high}`]];

export function mountTester(hooks: TesterHooks): TesterHandle {
  const storage = browserStorage();
  let st: TesterState = loadState(storage);
  const save = () => { saveState(st, storage); };
  save();                                                 // keeps the anonymous ID for the next visit, if storage works

  const tpl = document.getElementById('tester-tpl') as HTMLTemplateElement;
  const app = document.getElementById('app')!;
  const frag = tpl.content.cloneNode(true) as DocumentFragment;
  const bar = frag.getElementById('t-bar')!;
  const root = frag.getElementById('tester')!;
  const dialog = frag.getElementById('t-report') as HTMLDialogElement;
  const h1 = app.querySelector('h1')!;
  app.insertBefore(bar, h1);
  h1.after(root);
  document.body.append(dialog);
  document.documentElement.classList.add('t-mode');
  const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;

  // ---- relay: wake it now (cold start > 30 s, D17) and remember whether it answered, for problem reports ----
  let relayOk: boolean | null = null;
  let postUrl: string | null = null;
  const relayReady = liveRelayUrl(location.search, async (u) => { const r = await fetch(u); return r.ok ? r.json() : null; })
    .then((voice) => { postUrl = feedbackUrl(voice); return voice; })
    .catch(() => null);
  const checkRelay = async () => {
    const voice = await relayReady;
    if (!voice) { relayOk = false; return; }
    const ac = new AbortController();
    const timer = setTimeout(() => ac.abort(), 45_000);
    try {
      relayOk = (await fetch(voice.replace(/^ws/, 'http').replace(/\/voice$/, '/health'), { signal: ac.signal })).ok;
    } catch { relayOk = false; } finally { clearTimeout(timer); }
  };
  void checkRelay();

  // ---- sending: every event is saved first, then sent; failures stay "unsent" (outbox.ts) ----
  const flush = async (i: number) => {
    await relayReady;
    const out = st.events[i];
    if (!out) return;
    out.status = await deliver(postUrl, JSON.stringify(out.ev), browserTransport);
    save();
    renderThanks();
  };
  const emit = (kind: Kind, fields: Ev) => {
    const ev = fit({ ...baseEvent(st, kind), ...fields });
    st.events.push({ ev, status: 'pending' });
    save();
    void flush(st.events.length - 1);
  };
  st.events.forEach((e, i) => { if (e.status !== 'sent') void flush(i); });   // last visit's leftovers

  // ---- screens ----
  const screens = ['t-welcome', 't-tasks', 't-task', 't-thanks'] as const;
  const show = (id: (typeof screens)[number], focus = true) => {
    for (const s of screens) $(s).hidden = s !== id;
    app.classList.toggle('t-hide-app', id === 't-welcome' || id === 't-thanks');
    if (focus) $(`${id}-h`).focus();
  };

  // Welcome and consent (eval/listening_test.md section 3, questions 1 and 2)
  const takePart = $<HTMLInputElement>('t-take-part'), quote = $<HTMLInputElement>('t-quote'), err = $('t-consent-err');
  if (st.consent) { takePart.checked = st.consent.takePart; quote.checked = st.consent.quote; }
  $('t-consent').addEventListener('submit', (e) => {
    e.preventDefault();
    if (!takePart.checked) { err.hidden = false; takePart.focus(); return; }
    err.hidden = true;
    const first = !st.consent;
    st = { ...st, consent: { takePart: true, quote: quote.checked } };
    save();
    if (first) emit('consent', {});
    renderList();
    show('t-tasks');
  });
  $('t-welcome-again').addEventListener('click', () => show('t-welcome'));

  // Task list
  const list = $('t-list');
  const STATUS_TEXT: Record<TaskStatus, string> = { todo: 'To do', done: 'Done', skip: 'Skipped' };
  const renderList = () => {
    const { finished, total } = progress(st);
    $('t-progress').textContent = `${finished} of ${total} tasks finished. About ${TASKS.filter((t) => st.tasks[t.id] === 'todo').reduce((m, t) => m + t.minutes, 0)} minutes left.`;
    list.replaceChildren(...TASKS.map((t) => {
      const s = st.tasks[t.id] ?? 'todo';
      const startB = h('button', { type: 'button', 'aria-label': `${s === 'todo' ? 'Start this task' : 'Do it again'}: ${t.title}`,
        text: s === 'todo' ? 'Start this task' : 'Do it again', 'data-task': t.id });
      const skipB = h('button', { type: 'button', 'aria-label': `Skip: ${t.title}`, text: 'Skip', 'data-skip': t.id });
      startB.addEventListener('click', () => openTask(t));
      skipB.addEventListener('click', () => finishTask(t, 'skip'));
      return h('li', { class: `t-item t-${s}` },
        h('h3', { text: `${t.id}. ${t.title} (${t.minutes} min)` }),
        h('p', { text: t.what }),
        h('p', { class: 't-status-line', text: `Status: ${STATUS_TEXT[s]}` }),
        h('div', { class: 'row' }, startB, ...(s === 'todo' ? [skipB] : [])));
    }));
  };
  $('t-finish').addEventListener('click', () => { renderThanks(); show('t-thanks'); });

  // One task at a time
  let active: Task | null = null;
  let form: HTMLFormElement | null = null;
  const body = $('t-task-body'), doneB = $<HTMLButtonElement>('t-done'), skipB = $<HTMLButtonElement>('t-skip');
  let presets = 0, liveTried = false;
  const changed = new Set<string>();

  const playButton = (label: string, onPlay: () => void) => {
    const b = h('button', { type: 'button', class: 't-play', text: label });
    b.addEventListener('click', onPlay);
    return b;
  };
  /** Tasks 6 and 7 need the match running with full sound (the Ask button wakes up once it plays). */
  const playFull = () => {
    if (hooks.playing() && !hooks.clip().commentaryOnly) return;
    const p = hooks.playhead();
    hooks.playClip({ from: hooks.playing() && p !== null ? p : OPEN_PLAY_FROM, to: null, commentaryOnly: false });
  };

  const openTask = (t: Task) => {
    active = t;
    form = null;
    $('t-task-h').textContent = `Task ${t.id} of ${TASKS.length}: ${t.title}`;
    doneB.textContent = 'Done';
    const parts: Node[] = [];
    if (t.kind === 'tour') {
      parts.push(h('p', { text: 'Press "Play the tour". A voice explains each sound, then plays it. It takes about 2 minutes. You can keep your eyes open for this one.' }),
        playButton('Play the tour', () => hooks.runTour()));
    } else if (t.kind === 'clip') {
      const c = t.clip!;
      if (c === 2) parts.push(h('p', { text: 'We have skipped ahead two minutes. The score is still Reds nil, Navy one.' }));
      parts.push(
        h('p', { text: 'You are sitting on the halfway line. Reds attack to your right, Navy attack to your left.' }),
        h('p', { text: `Put your headphones on. Press "Play clip ${c}", then close your eyes. The clip lasts 3 minutes and stops by itself with "End of the clip". Please don't press anything until then.` }),
        h('p', { id: 't-clip-state', class: 't-hint', text: 'Not played yet.' }),
        playButton(`Play clip ${c}`, () => {
          hooks.playClip(clipFor(st.group, c));
          $('t-clip-state').textContent = 'Playing. Eyes closed, please.';
          (document.activeElement as HTMLElement | null)?.replaceChildren(`Play clip ${c} again from the start`);
        }));
      doneB.textContent = `Done: on to the questions`;
    } else if (t.kind === 'questions') {
      const c = t.clip!;
      const a = st.answers.clips[c];
      form = h('form', { id: 't-form', novalidate: false });
      form.append(h('p', { text: 'Answer from memory. There are no right or wrong answers, and "Don\'t know" is fine.' }));
      PROBES.forEach((p, i) => form!.append(radios(`p_${p.id}`, `${i + 1}. ${p.question}`, p.choices, { required: true, value: a?.probes[p.id] })));
      SCALE.forEach((q, i) => form!.append(radios(`s_${q.id}`, `${PROBES.length + i + 1}. ${q.question} From 1 to 5.`, SCALE_CHOICES(q.low, q.high),
        { required: true, value: a?.scale[q.id] !== undefined ? String(a.scale[q.id]) : undefined })));
      parts.push(form);
      doneB.textContent = 'Send my answers';
    } else if (t.kind === 'ask') {
      presets = 0; liveTried = false;
      form = h('form', { id: 't-form' });
      form.append(radios('ask_worked', 'Did the commentator answer you?', ASK_WORKED, { value: st.answers.ask?.worked }));
      parts.push(
        h('ol', {}, h('li', { text: 'Press "Play the match".' }),
          h('li', { text: 'Press "Quick questions" (under the two big buttons) and choose "Where\'s the ball?".' }),
          h('li', { text: 'Ask one more question from the list.' }),
          h('li', { text: 'Press the big "Ask the commentator" button, allow the microphone, wait for the beep and ask your own question, for example "Who has the ball?". The first one can take 30 seconds to wake up: if it says it isn\'t available, wait a moment and try again.' })),
        h('p', { class: 't-hint', text: 'If you ask out loud, your voice goes to Microsoft\'s Azure speech service so the commentator can answer. We keep the words of your question, not the recording.' }),
        playButton('Play the match', playFull), form);
      doneB.textContent = 'Send my answers';
    } else if (t.kind === 'settings') {
      changed.clear();
      form = h('form', { id: 't-form' });
      form.append(radios('settings_easy', 'Was Settings easy to use?', SETTINGS_EASY, { value: st.answers.settings?.easy }));
      parts.push(
        h('p', { text: 'Press "Play the match", then open the "Setup" tab at the top of the page. Try these:' }),
        h('ul', {}, h('li', { text: 'Choose your end of the stadium: Reds or Navy. Listen to how the crowd around you changes.' }),
          h('li', { text: 'Move the whole crowd level, or one sound on the sound desk, up or down.' }),
          h('li', { text: 'On an Android phone: choose a vibration setting, then press "Test vibration".' })),
        playButton('Play the match', playFull), form);
      doneB.textContent = 'Send my answers';
    } else {
      hooks.pause();
      const o = st.answers.overall ?? {};
      form = h('form', { id: 't-form' });
      form.append(
        h('p', { class: 't-hint', text: 'Everything here is optional. Please don\'t type your name or other personal details.' }),
        textarea('confusing', 'What was confusing?', o.confusing),
        textarea('liked', 'What did you like?', o.liked),
        textarea('would_use', 'What would make you use this?', o.would_use),
        radios('preferred', 'Which did you prefer: clip 1 or clip 2?', PREFERRED, { value: o.preferred }),
        radios('device', 'What did you use?', DEVICE, { value: o.device }),
        radios('headphones', 'Did you use headphones?', HEADPHONES, { value: o.headphones }),
        radios('screen_reader', 'Do you use a screen reader?', SCREEN_READER, { value: o.screen_reader }),
        radios('sight', 'Would you like to tell us about your sight?', SIGHT, { value: o.sight ?? 'not_said' }));
      parts.push(form);
      doneB.textContent = 'Send my answers';
    }
    if (form) {
      form.addEventListener('submit', (e) => { e.preventDefault(); doneB.click(); });
      form.addEventListener('change', () => { keepDraft(); save(); });
    }
    body.replaceChildren(...parts);
    show('t-task');
  };

  const val = (name: string) => {
    const v = form ? new FormData(form).get(name) : null;
    return typeof v === 'string' && v.trim() ? v.trim() : undefined;
  };
  /** Copy what the form says into the saved answers (on every change, so a reload keeps it). */
  const keepDraft = () => {
    const t = active;
    if (!t || !form) return;
    if (t.kind === 'questions') {
      const probes = Object.fromEntries(PROBES.map((p) => [p.id, val(`p_${p.id}`)]).filter(([, v]) => v)) as Partial<Record<ProbeId, string>>;
      const scale = Object.fromEntries(SCALE.map((q) => [q.id, Number(val(`s_${q.id}`))]).filter(([, v]) => v)) as Partial<Record<ScaleId, number>>;
      st.answers.clips[t.clip!] = { probes, scale };
    } else if (t.kind === 'ask') {
      const live = document.getElementById('ask-live');
      st.answers.ask = { presets, liveAvailable: !!live && !live.hidden, liveTried, worked: val('ask_worked') };
    } else if (t.kind === 'settings') {
      st.answers.settings = { changed: [...changed], easy: val('settings_easy') };
    } else if (t.kind === 'overall') {
      st.answers.overall = Object.fromEntries((['confusing', 'liked', 'would_use', 'preferred', 'device', 'headphones', 'screen_reader', 'sight'] as const)
        .map((k) => [k, val(k)]).filter(([, v]) => v));
    }
  };
  // Tasks 6-7 watch the real controls, so we know what was tried without asking.
  // D24: with live Ask on, the big Ask pad asks out loud straight away (main.ts sets data-state "stop" in the press).
  document.getElementById('ask')?.addEventListener('click', (e) => {
    const live = document.getElementById('ask-live');
    if (active?.kind !== 'ask' || !live || live.hidden || (e.currentTarget as HTMLElement).dataset.state !== 'stop') return;
    liveTried = true;
    keepDraft(); save();
  });
  document.getElementById('ask-menu')?.addEventListener('click', (e) => {
    const b = (e.target as HTMLElement).closest('button');
    if (!b || active?.kind !== 'ask') return;
    if (b.id === 'ask-live') liveTried = true; else if (b.dataset.preset) presets++;
    keepDraft(); save();
  });
  const watch: [string, string][] = [['input[name="club"]', 'club'], ['#crowd', 'crowd'], ['input[name="haptics"]', 'haptics'],
    ['#strength', 'strength'], ['#radar-toggle', 'radar']];
  for (const [sel, key] of watch) {
    document.querySelectorAll(sel).forEach((el) => el.addEventListener('change', () => {
      if (active?.kind === 'settings') { changed.add(key); keepDraft(); save(); }
    }));
  }
  document.getElementById('calibrate')?.addEventListener('click', () => { if (active?.kind === 'settings') { changed.add('calibrate'); keepDraft(); save(); } });

  doneB.addEventListener('click', () => {
    const t = active;
    if (!t) return;
    if (form && !form.reportValidity()) return;          // native messages; the first unanswered question gets focus
    keepDraft();
    const a = st.answers;
    if (t.kind === 'questions') {
      const ca = a.clips[t.clip!]!;
      emit('clip', { clip: t.clip!, ...ca.probes, ...scoreClip(t.clip!, ca.probes), ...ca.scale });
    } else if (t.kind === 'ask' && a.ask) {
      emit('ask', { ask_presets: a.ask.presets, ask_live_available: a.ask.liveAvailable, ask_live_tried: a.ask.liveTried,
        ...(a.ask.worked ? { ask_worked: a.ask.worked } : {}) });
    } else if (t.kind === 'settings' && a.settings) {
      emit('settings', { ...(a.settings.changed.length ? { settings_changed: a.settings.changed.join(',') } : {}),
        ...(a.settings.easy ? { settings_easy: a.settings.easy } : {}) });
    } else if (t.kind === 'overall' && a.overall) {
      emit('overall', { ...a.overall });
    }
    finishTask(t, 'done');
  });
  skipB.addEventListener('click', () => { if (active) finishTask(active, 'skip'); });

  const finishTask = (t: Task, result: 'done' | 'skip') => {
    if ((t.kind === 'clip' || t.kind === 'tour') && active?.id === t.id) hooks.pause();
    st = setTask(st, t.id, result);
    save();
    emit('task', { task: t.id, result });
    active = null;
    form = null;
    const next = nextTask(st, t.id);
    renderList();
    if (!next) { renderThanks(); show('t-thanks'); hooks.say('All tasks finished. Thank you!'); return; }
    show('t-tasks', false);
    list.querySelector<HTMLButtonElement>(`button[data-task="${next.id}"]`)?.focus();
    hooks.say(`Task ${t.id} ${result === 'done' ? 'done' : 'skipped'}. Next: ${next.title}.`);
  };

  // Thank you, with "Copy my answers" and the email fallback
  const copyBox = $<HTMLTextAreaElement>('t-copy-text');
  const renderThanks = () => {
    const unsent = st.events.filter((e) => e.status === 'unsent').length;
    const pending = st.events.filter((e) => e.status === 'pending').length;
    $('t-sent').textContent = unsent ? 'Some of your answers have not reached us yet. Please press "Copy my answers" and send them to the person who gave you the link.'
      : pending ? 'Still sending your answers…' : 'All your answers have reached us. You can close this page.';
    $('t-code').textContent = `Your tester code is ${st.id}. It is random and doesn't say who you are.`;
    const mail = $<HTMLAnchorElement>('t-mail');
    mail.hidden = !FEEDBACK_EMAIL;
    if (FEEDBACK_EMAIL) mail.href = `mailto:${FEEDBACK_EMAIL}?subject=${encodeURIComponent('Tely test answers')}&body=${encodeURIComponent(answersText(st))}`;
  };
  $('t-copy').addEventListener('click', async () => {
    const text = answersText(st);
    try {
      await navigator.clipboard.writeText(text);
      hooks.say('Your answers are copied. Paste them into a message to the person who gave you the link.');
    } catch {
      copyBox.value = text;
      $('t-copy-wrap').hidden = false;
      copyBox.focus();
      copyBox.select();
      hooks.say('Copying is blocked here. Your answers are in the text box: select all of it and copy it.');
    }
  });
  $('t-back').addEventListener('click', () => { renderList(); show('t-tasks'); });

  // Report a problem: always on screen, and the F key
  const reportOpen = $<HTMLButtonElement>('t-report-open');
  const reportKinds = $('t-report-kinds');
  reportKinds.replaceWith(radios('problem_kind', 'What went wrong?', PROBLEM_KINDS, { required: true }));
  const reportText = $<HTMLTextAreaElement>('t-report-text');
  const openReport = () => {
    if (dialog.open) return;
    void checkRelay();                                    // fresh answer for the next report; this one uses the last
    dialog.showModal();
  };
  reportOpen.addEventListener('click', openReport);
  $('t-report-cancel').addEventListener('click', () => dialog.close('cancel'));
  $('t-report-form').addEventListener('submit', (e) => {
    const f = e.currentTarget as HTMLFormElement;
    e.preventDefault();
    if (!f.reportValidity()) return;
    const kind = String(new FormData(f).get('problem_kind') ?? 'other');
    const text = reportText.value.trim();
    const s = hooks.settings(), p = hooks.playhead();
    const { browser, os } = uaFamily(navigator.userAgent, navigator.maxTouchPoints ?? 0);
    st.answers.problems.push({ kind, text });
    emit('problem', {
      problem_kind: kind, ...(text ? { problem_text: text } : {}),
      ctx_task: active?.id ?? 0, ...(p !== null ? { ctx_playhead: Math.round(p * 10) / 10 } : {}), ctx_playing: hooks.playing(),
      ctx_club: s.club, ctx_crowd: Math.round(s.crowdMix * 100), ctx_haptics: s.haptics, ctx_browser: browser, ctx_os: os,
      ctx_viewport: `${Math.round(innerWidth)}x${Math.round(innerHeight)}`, ...(relayOk !== null ? { ctx_relay: relayOk } : {}),
    });
    f.reset();
    dialog.close('send');
    hooks.say('Thank you. Your report is saved and on its way to us.');
  });
  document.addEventListener('keydown', (e) => {
    const typing = (e.target as HTMLElement | null)?.closest('input, select, textarea');
    if (typing || e.ctrlKey || e.metaKey || e.altKey || dialog.open) return;
    if (e.key === 'f' || e.key === 'F') { e.preventDefault(); openReport(); }
  });

  // First screen: welcome until they've said yes, then the task list (or thanks when all is finished)
  renderList();
  renderThanks();
  if (!st.consent?.takePart) show('t-welcome');
  else if (!nextTask(st)) show('t-thanks');
  else show('t-tasks');

  return {
    clipEnded() {
      if (active?.kind !== 'clip') return;
      const s = document.getElementById('t-clip-state');
      if (s) s.textContent = 'Clip finished. You can open your eyes.';
      doneB.focus();                                      // main.ts has said "End of the clip."
    },
    tourEnded(skipped) {
      if (active?.kind === 'tour') {
        doneB.focus();
        hooks.say(skipped ? 'Tour skipped. Press Done to go on.' : 'Tour finished. Press Done to go on.');
      } else {
        hooks.say(skipped ? 'Tour skipped.' : 'Tour finished.');
      }
    },
  };
}
