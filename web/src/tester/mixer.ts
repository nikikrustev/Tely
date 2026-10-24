// OWNER: A (potencialbg). The sound mixer (?mix=1, 24 Oct): a testing tool for setting the match mix by ear.
// main.ts imports this only with ?mix=1, so the judges' page never loads it. One slider per sound group from
// audio/mix.ts, heard live while the match plays; Reset; Submit copies the values as JSON and downloads
// audio-mix.json. Hand that file to Claude and the values become DEFAULT_MIX (the shipped defaults).
// The draft is kept in localStorage (try/catch) and read only here, so the judges always hear DEFAULT_MIX.
import {
  DEFAULT_MIX, getMix, MAX_DB, MIN_DB, MIX_GROUPS, onMix, parseMix, setMix, VOICE_POSITIONS,
  type AudioMix, type MixLevels, type VoicePos,
} from '../audio/mix';
import { browserStorage, type StorageLike } from '../settings';

export const DRAFT_KEY = 'audiostands.mixDraft.v1';
export const FILE_NAME = 'audio-mix.json';

export const LABELS: Record<keyof MixLevels, string> = {
  crowdBeds: 'Crowd beds (murmur, swell, tense, away end)',
  chants: 'Chants and claps',
  roars: 'Crowd reactions (roar, ooh, cheer, jeers, applause)',
  pass: 'Pass',
  shot: 'Shot',
  tackle: 'Tackle',
  save: 'Save',
  net: 'Ball in the net',
  whistle: "Referee's whistle",
  ping: 'Ball ping ("Where is the ball?")',
  commentator: 'Commentator (track, preset and live answers)',
};
const POS_LABEL: Record<VoicePos, string> = {
  behind: 'Behind me, a little above (press box)',
  above: 'Above me, a little behind',
  overhead: 'Straight overhead',
};

/** The file Submit writes: every value, with when it was made. */
export function mixFile(m: AudioMix, now = new Date()): { version: 1; saved: string; mix: AudioMix } {
  return { version: 1, saved: now.toISOString(), mix: { ...m } };
}

export const dbText = (db: number): string => (db <= MIN_DB ? 'off' : `${db > 0 ? '+' : ''}${db.toFixed(1)} dB`);

export function loadDraft(storage: StorageLike | null = browserStorage()): AudioMix | null {
  try {
    const raw = storage?.getItem(DRAFT_KEY);
    return raw ? parseMix(JSON.parse(raw)) : null;
  } catch {
    return null;
  }
}

export function saveDraft(m: AudioMix | null, storage: StorageLike | null = browserStorage()): void {
  try {
    if (m) storage?.setItem(DRAFT_KEY, JSON.stringify(m));
    else (storage as Storage | null)?.removeItem?.(DRAFT_KEY);
  } catch { /* storage blocked: the mix still works for this visit */ }
}

export interface MixerHooks {
  /** main.ts say(): the page's one polite status. */
  say(text: string): void;
}

const CSS = `
#mixer { background: var(--panel); border-radius: 0.75rem; padding: 1rem; margin: 1rem 0; }
#mixer .m-row { display: grid; grid-template-columns: 1fr auto; gap: 0 0.75rem; align-items: center; margin: 0 0 0.5rem; }
#mixer .m-row label { font-weight: 600; }
#mixer .m-row output { font-variant-numeric: tabular-nums; min-width: 5.5rem; text-align: right; }
#mixer .m-row input { grid-column: 1 / -1; }
#mixer textarea { display: block; width: 100%; box-sizing: border-box; min-height: 8rem; font: 0.9rem/1.4 ui-monospace, monospace;
  border: 2px solid var(--fg); border-radius: 0.5rem; background: var(--bg); color: var(--fg); padding: 0.5rem; }
#mixer .m-hint { color: var(--muted); margin: 0 0 1rem; }
`;

export function mountMixer(hooks: MixerHooks): HTMLElement {
  const draft = loadDraft();
  if (draft) setMix(draft);
  const style = document.createElement('style');
  style.textContent = CSS;
  document.head.append(style);

  const el = <K extends keyof HTMLElementTagNameMap>(tag: K, props: Record<string, string> = {}, text = '') => {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(props)) e.setAttribute(k, v);
    if (text) e.textContent = text;
    return e;
  };
  const section = el('section', { id: 'mixer', 'aria-labelledby': 'm-h' });
  section.append(el('h2', { id: 'm-h' }, 'Sound mixer (testing only)'),
    el('p', { class: 'm-hint' }, 'Press Start, then move the sliders: you hear each change at once. "Next big moment" jumps '
      + 'to a chance. Submit copies the values and downloads audio-mix.json; send that file to make them the defaults.'));

  const sliders = new Map<keyof AudioMix, { input: HTMLInputElement; out: HTMLOutputElement }>();
  const row = (key: keyof AudioMix, label: string, min: number, max: number, step: number) => {
    const id = `m-${key}`;
    const wrap = el('div', { class: 'm-row' });
    const input = el('input', { id, type: 'range', min: String(min), max: String(max), step: String(step) });
    const out = el('output', { for: id });
    wrap.append(el('label', { for: id }, label), out, input);
    input.addEventListener('input', () => { setMix({ [key]: Number(input.value) } as Partial<AudioMix>); saveDraft(getMix()); });
    sliders.set(key, { input, out });
    section.append(wrap);
  };
  for (const k of MIX_GROUPS) row(k, LABELS[k], MIN_DB, MAX_DB, 0.5);
  row('nearEnd', 'Crowd end nearest the ball reacts more', 0, 1, 0.05);

  const fs = el('fieldset');
  fs.append(el('legend', {}, 'Where the commentator sits'));
  const radios = VOICE_POSITIONS.map((p) => {
    const r = el('input', { type: 'radio', name: 'm-pos', value: p });
    r.addEventListener('change', () => { if (r.checked) { setMix({ commentatorPos: p }); saveDraft(getMix()); } });
    const l = el('label');
    l.append(r, ` ${POS_LABEL[p]}`);
    fs.append(l);
    return r;
  });
  section.append(fs);

  const buttons = el('div', { class: 'row' });
  const reset = el('button', { type: 'button', id: 'm-reset' }, 'Reset');
  const submit = el('button', { type: 'button', id: 'm-submit' }, 'Submit');
  buttons.append(reset, submit);
  const result = el('textarea', { id: 'm-json', readonly: '', 'aria-label': 'The submitted mix, as JSON', rows: '8' });
  result.hidden = true;
  section.append(buttons, result);

  // Every change, from a slider or Reset, shows here (aria-valuetext so a screen reader says "-14.0 dB", not "-14").
  onMix((m) => {
    for (const [k, { input, out }] of sliders) {
      const v = m[k] as number;
      input.value = String(v);
      const text = k === 'nearEnd' ? `${Math.round(v * 100)}%` : dbText(v);
      out.textContent = text;
      input.setAttribute('aria-valuetext', text);
    }
    for (const r of radios) r.checked = r.value === m.commentatorPos;
  });

  reset.addEventListener('click', () => {
    setMix(DEFAULT_MIX);
    saveDraft(null);
    hooks.say('Mix reset to the defaults.');
  });
  submit.addEventListener('click', async () => {
    const json = JSON.stringify(mixFile(getMix()), null, 2);
    result.value = json;
    result.hidden = false;
    let copied = false;
    try { await navigator.clipboard.writeText(json); copied = true; } catch { /* no clipboard permission */ }
    const a = el('a', { href: URL.createObjectURL(new Blob([json + '\n'], { type: 'application/json' })), download: FILE_NAME });
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    hooks.say(copied ? `Copied the mix and downloaded ${FILE_NAME}.` : `Downloaded ${FILE_NAME}. The JSON is also in the box below.`);
  });

  // After the Start / Next row, so the play controls sit right above the sliders.
  const anchor = document.querySelector('#app .row');
  if (anchor) anchor.after(section);
  else document.getElementById('app')?.append(section);
  return section;
}
