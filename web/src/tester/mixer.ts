// OWNER: A (potencialbg). The sound desk on the Setup tab (D25, 27 Oct; the ?mix=1 mixer before that): one channel per
// sound group from audio/mix.ts, heard live while the match plays. main.ts imports this the first time Setup opens,
// so the Laptop and Phone views never load it.
// D24 (26 Oct): it is the listener's own mix, set once with a sighted helper and saved on this device (audio/mix.ts
// saveMix), so every later visit plays it. Reset goes back to our defaults. "Save a copy" downloads audio-mix.json:
// hand that file to Claude and the values can become DEFAULT_MIX (the shipped defaults).
// D25: every level is on the fan's 0..100 scale (audio/mix.ts levelFromDb), the same numbers the commentator's
// adjust_sound tool uses, so "whistle down by 5" out loud and the -5 button here do the same thing.
import {
  DEFAULT_MIX, dbFromLevel, getMix, levelFromDb, loadSavedMix, MAX_DB, MIN_DB, MIX_KEY, onMix, saveMix, setMix,
  VOICE_POSITIONS, type AudioMix, type MixLevels, type VoicePos,
} from '../audio/mix';

export const DRAFT_KEY = MIX_KEY;
export const FILE_NAME = 'audio-mix.json';

export const LABELS: Record<keyof MixLevels, string> = {
  commentator: 'Commentator',
  crowdBeds: 'Crowd murmur and swell',
  chants: 'Chants and claps',
  roars: 'Crowd reactions (roars, oohs, cheers)',
  pass: 'Passes',
  shot: 'Shots',
  tackle: 'Tackles',
  save: 'Saves',
  net: 'Ball in the net',
  whistle: "Referee's whistle",
  ping: 'Ball ping ("Where is the ball?")',
};
/** What the fan says for each channel (the adjust_sound names, pipeline/tely/qa/tools.py SOUNDS). */
export const SAY_AS: Record<keyof MixLevels, string> = {
  commentator: 'commentator', crowdBeds: 'crowd', chants: 'chants', roars: 'reactions', pass: 'passes', shot: 'shots',
  tackle: 'tackles', save: 'saves', net: 'net', whistle: 'whistle', ping: 'ball ping',
};
const POS_LABEL: Record<VoicePos, string> = {
  behind: 'Behind me, a little above (press box)',
  above: 'Above me, a little behind',
  overhead: 'Straight overhead',
};

/** Starting points for the helper, in dB on top of DEFAULT_MIX. */
export const PRESETS: { id: string; label: string; patch: Partial<MixLevels> }[] = [
  { id: 'default', label: 'Our default', patch: {} },
  { id: 'voice', label: 'Voice first', patch: { commentator: 6, crowdBeds: -6, chants: -6, roars: -3 } },
  { id: 'atmosphere', label: 'Big atmosphere', patch: { crowdBeds: 5, chants: 6, roars: 4, commentator: -2 } },
  { id: 'calm', label: 'Calm', patch: { crowdBeds: -10, chants: -14, roars: -10, whistle: -6 } },
];
export function presetMix(id: string): AudioMix {
  const p = PRESETS.find((x) => x.id === id)?.patch ?? {};
  const out = { ...DEFAULT_MIX };
  for (const [k, d] of Object.entries(p) as [keyof MixLevels, number][]) out[k] = Math.min(MAX_DB, Math.max(MIN_DB, DEFAULT_MIX[k] + d));
  return out;
}

/** The file Submit writes: every value, with when it was made. */
export function mixFile(m: AudioMix, now = new Date()): { version: 1; saved: string; mix: AudioMix } {
  return { version: 1, saved: now.toISOString(), mix: { ...m } };
}

export const dbText = (db: number): string => (db <= MIN_DB ? 'off' : `${db > 0 ? '+' : ''}${db.toFixed(1)} dB`);
/** A level as a screen reader says it: "35 out of 100", "0 out of 100, off". */
export const levelText = (level: number): string => `${level} out of 100${level === 0 ? ', off' : ''}`;

export const loadDraft = loadSavedMix;
export const saveDraft = saveMix;

export interface MixerHooks {
  /** main.ts say(): the page's one polite status. */
  say(text: string): void;
  /** The stage's output, for the live scope (null until Start). */
  analyser?(): AnalyserNode | null;
  /** Where the desk goes (Setup's #mixer-slot); the end of #app if missing. */
  host?: HTMLElement | null;
}

// A console look in both themes: its own dark surface. Contrast: #e8f3ee on #0d1513 is 16:1, #9fb8ad 8.6:1,
// #5fd3a3 10:1. The focus ring is light here, because the page's --fg is near black in light mode.
const CSS = `
#mixer { --d-bg: #0d1513; --d-panel: #13201c; --d-line: #284039; --d-fg: #e8f3ee; --d-muted: #9fb8ad; --d-accent: #5fd3a3;
  color-scheme: dark; background: var(--d-bg); color: var(--d-fg); border: 1px solid var(--d-line); border-radius: 1rem;
  padding: 1rem; margin: 1rem 0 0; box-shadow: inset 0 1px 0 rgb(255 255 255 / 0.04); }
#mixer :is(button, input, textarea):focus-visible { outline: 3px solid var(--d-fg); outline-offset: 2px; }
#mixer h2 { margin: 0; font-size: 1.3rem; letter-spacing: 0.01em; }
#mixer h3 { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.12em; color: var(--d-muted); margin: 1.25rem 0 0.5rem; }
#mixer .m-head { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 0.25rem 1rem; }
#mixer .m-hint { color: var(--d-muted); margin: 0; font-size: 0.95rem; }
#mixer .m-helper { margin: 0.75rem 0 0; color: var(--d-muted); font-size: 0.95rem; }
#mixer .m-helper p { margin: 0 0 0.35rem; }
#mixer .m-scope { margin: 0.75rem 0 0; background: #08100e; border: 1px solid var(--d-line); border-radius: 0.75rem; padding: 0.5rem; }
#mixer .m-scope canvas { display: block; width: 100%; height: 6rem; }
#mixer .m-scope p { margin: 0.35rem 0 0; font: 600 0.8rem/1.3 ui-monospace, "Cascadia Mono", monospace; color: var(--d-muted);
  letter-spacing: 0.06em; text-transform: uppercase; }
#mixer button { background: var(--d-panel); color: var(--d-fg); border: 1px solid var(--d-line); border-radius: 0.6rem; font-weight: 600; }
#mixer button:hover { border-color: var(--d-accent); }
#mixer .m-presets { display: grid; grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr)); gap: 0.5rem; }
#mixer .m-presets button { min-height: 44px; font-size: 1rem; }
#mixer .m-channels { display: grid; gap: 0.5rem; }
#mixer .m-row { display: grid; grid-template-columns: 44px minmax(0, 1fr) 44px 4.25rem; grid-template-areas: "name name name read" "minus slide plus read";
  align-items: center; gap: 0.15rem 0.6rem; padding: 0.55rem 0.75rem; background: var(--d-panel); border: 1px solid var(--d-line); border-radius: 0.75rem; }
#mixer .m-name { grid-area: name; display: flex; flex-wrap: wrap; align-items: baseline; gap: 0 0.6rem; }
#mixer .m-name label { font-weight: 600; }
#mixer .m-name .m-db, #mixer .m-name .m-say { font: 0.8rem/1.3 ui-monospace, "Cascadia Mono", monospace; color: var(--d-muted); }
#mixer .m-row output { grid-area: read; justify-self: end; font: 700 1.9rem/1 ui-monospace, "Cascadia Mono", monospace; color: var(--d-accent);
  font-variant-numeric: tabular-nums; text-shadow: 0 0 12px rgb(95 211 163 / 0.35); }
#mixer .m-row output.m-off { color: var(--d-muted); text-shadow: none; }
#mixer .m-row .m-minus { grid-area: minus; } #mixer .m-row .m-plus { grid-area: plus; }
#mixer .m-row .m-minus, #mixer .m-row .m-plus { min-width: 44px; padding: 0; font: 700 1rem ui-monospace, "Cascadia Mono", monospace; }
#mixer .m-row input { grid-area: slide; width: 100%; margin: 0; accent-color: var(--d-accent); }
#mixer fieldset { border: 1px solid var(--d-line); border-radius: 0.75rem; margin: 0.75rem 0 0; }
#mixer fieldset legend { color: var(--d-fg); font-weight: 600; }
#mixer input[type="radio"] { accent-color: var(--d-accent); }
#mixer .m-voice { margin: 0; padding: 0.75rem 1rem; border: 1px solid var(--d-line); border-left: 4px solid var(--d-accent);
  border-radius: 0.75rem; background: var(--d-panel); }
#mixer .m-voice p { margin: 0 0 0.5rem; }
#mixer .m-voice ul { margin: 0 0 0.5rem; padding-left: 1.25rem; }
#mixer .m-voice q { font-weight: 600; }
#mixer .m-actions { margin-top: 1rem; }
#mixer textarea { display: block; width: 100%; box-sizing: border-box; min-height: 8rem; margin-top: 0.75rem; font: 0.9rem/1.4 ui-monospace, monospace;
  border: 1px solid var(--d-line); border-radius: 0.5rem; background: #08100e; color: var(--d-fg); padding: 0.5rem; }
@media (max-width: 30rem) { #mixer .m-row output { font-size: 1.5rem; } #mixer .m-row { grid-template-columns: 44px minmax(0, 1fr) 44px 3.25rem; } }
`;

/** The order a helper meets the channels in: the voice and the crowd first, the small sounds after. */
export const ORDER: readonly (keyof MixLevels)[] = [
  'commentator', 'crowdBeds', 'chants', 'roars', 'whistle', 'pass', 'shot', 'tackle', 'save', 'net', 'ping',
];

/** The live scope: 40 log-spaced bands of the stadium's output. Decorative (aria-hidden): the helper listens. */
function startScope(canvas: HTMLCanvasElement, analyser: () => AnalyserNode | null): void {
  const g = canvas.getContext('2d');
  if (!g) return;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const BANDS = 40;
  let bins = new Uint8Array(0);
  const draw = () => {
    const dpr = Math.min(2, devicePixelRatio || 1);
    const w = Math.round(canvas.clientWidth * dpr), h = Math.round(canvas.clientHeight * dpr);
    if (!w || !h) return;
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
    g.clearRect(0, 0, w, h);
    g.strokeStyle = 'rgba(159,184,173,0.15)';
    g.lineWidth = 1;
    for (let i = 1; i < 4; i++) { g.beginPath(); g.moveTo(0, (h * i) / 4); g.lineTo(w, (h * i) / 4); g.stroke(); }
    const an = analyser();
    if (an && bins.length !== an.frequencyBinCount) bins = new Uint8Array(an.frequencyBinCount);
    if (an) an.getByteFrequencyData(bins);
    const gap = 2 * dpr, bw = (w - gap * (BANDS - 1)) / BANDS;
    for (let b = 0; b < BANDS; b++) {
      let v = 0;
      if (an && bins.length) {
        // 40 Hz .. 16 kHz, log spaced, so the voice and the crowd fill the middle rather than one corner.
        const nyq = an.context.sampleRate / 2, f0 = 40 * Math.pow(400, b / BANDS), f1 = 40 * Math.pow(400, (b + 1) / BANDS);
        const i0 = Math.max(0, Math.floor((f0 / nyq) * bins.length)), i1 = Math.min(bins.length, Math.max(i0 + 1, Math.ceil((f1 / nyq) * bins.length)));
        for (let i = i0; i < i1; i++) v = Math.max(v, bins[i] ?? 0);
      }
      const bh = Math.max(2 * dpr, (v / 255) * (h - 2 * dpr));
      g.fillStyle = v > 215 ? '#f2c14e' : `rgba(95,211,163,${0.35 + 0.65 * (v / 255)})`;
      g.fillRect(b * (bw + gap), h - bh, bw, bh);
    }
  };
  const tick = () => {
    if (!canvas.isConnected) return;
    if (canvas.offsetParent !== null && document.visibilityState === 'visible') draw();
    if (reduced) setTimeout(tick, 500); else requestAnimationFrame(tick);
  };
  tick();
}

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
  const saved = el('p', { class: 'm-hint', id: 'm-saved' }, loadDraft() ? 'Your own mix is saved on this device.'
    : 'Playing our default mix. Move a sound to make it yours.');
  const head = el('div', { class: 'm-head' });
  head.append(el('h2', { id: 'm-h' }, 'Sound desk'), saved);
  // D24: the helper explanation, read in order before the first channel.
  const helper = el('div', { class: 'm-helper', id: 'm-helper' });
  helper.append(
    el('p', {}, 'Set this up once with a sighted friend or carer: press Start, listen together, and move each sound '
      + 'until it feels right. You hear every change at once.'),
    el('p', {}, 'Every sound is on a scale from 0 (off) to 100. Your mix is saved on this device and plays on every visit.'));
  const scope = el('figure', { class: 'm-scope', 'aria-hidden': 'true' });
  const canvas = el('canvas');
  scope.append(canvas, el('p', {}, 'Live stadium sound'));
  section.append(head, helper, scope);

  const commit = (patch: Partial<AudioMix>) => {
    setMix(patch);
    saveDraft(getMix());
    saved.textContent = 'Saved on this device.';        // visual only: a live region would talk over every drag
  };

  section.append(el('h3', {}, 'Starting points'));
  const presets = el('div', { class: 'm-presets' });
  for (const p of PRESETS) {
    const b = el('button', { type: 'button', 'data-preset-mix': p.id }, p.label);
    b.addEventListener('click', () => { commit(presetMix(p.id)); hooks.say(`${p.label} mix.`); });
    presets.append(b);
  }
  section.append(presets, el('h3', { id: 'm-levels-h' }, 'Levels, 0 to 100'));

  const channels = el('div', { class: 'm-channels', role: 'group', 'aria-labelledby': 'm-levels-h' });
  const rows = new Map<keyof AudioMix, { input: HTMLInputElement; out: HTMLOutputElement; db: HTMLElement | null }>();
  const row = (key: keyof AudioMix, label: string, say: string | null, toLevel: (m: AudioMix) => number, fromLevel: (l: number) => number) => {
    const id = `m-${key}`;
    const wrap = el('div', { class: 'm-row' });
    const name = el('div', { class: 'm-name' });
    name.append(el('label', { for: id }, label));
    const db = say ? el('span', { class: 'm-db', 'aria-hidden': 'true' }) : null;
    if (db) name.append(db);
    if (say) name.append(el('span', { class: 'm-say' }, `say “${say}”`));
    const input = el('input', { id, type: 'range', min: '0', max: '100', step: '1' });
    const out = el('output', { for: id, 'aria-hidden': 'true' });
    const minus = el('button', { type: 'button', class: 'm-minus', 'aria-label': `${label} −5` }, '−5');
    const plus = el('button', { type: 'button', class: 'm-plus', 'aria-label': `${label} +5` }, '+5');
    const set = (l: number) => commit({ [key]: fromLevel(Math.min(100, Math.max(0, l))) } as Partial<AudioMix>);
    input.addEventListener('input', () => set(Number(input.value)));
    minus.addEventListener('click', () => set(toLevel(getMix()) - 5));
    plus.addEventListener('click', () => set(toLevel(getMix()) + 5));
    wrap.append(name, out, minus, input, plus);
    rows.set(key, { input, out, db });
    channels.append(wrap);
  };
  for (const k of ORDER) row(k, LABELS[k], SAY_AS[k], (m) => levelFromDb(m[k]), dbFromLevel);
  row('nearEnd', 'Crowd end nearest the ball reacts more', null, (m) => Math.round(m.nearEnd * 100), (l) => l / 100);
  section.append(channels);

  const fs = el('fieldset');
  fs.append(el('legend', {}, 'Where the commentator sits'));
  const radios = VOICE_POSITIONS.map((p) => {
    const r = el('input', { type: 'radio', name: 'm-pos', value: p });
    r.addEventListener('change', () => { if (r.checked) commit({ commentatorPos: p }); });
    const l = el('label');
    l.append(r, ` ${POS_LABEL[p]}`);
    fs.append(l);
    return r;
  });
  section.append(fs);

  // The same changes, out loud: what the fan can say to the commentator during the match (adjust_sound).
  section.append(el('h3', { id: 'm-voice-h' }, 'Or just ask the commentator'));
  const voice = el('div', { class: 'm-voice', role: 'note', 'aria-labelledby': 'm-voice-h' });
  const ul = el('ul');
  for (const q of ['Turn the whistle down by 5.', 'Set the chants to 40.', 'Crowd reactions up 10.', 'Turn the ball in the net off.']) {
    const li = el('li');
    li.append(el('q', {}, q));
    ul.append(li);
  }
  voice.append(
    el('p', {}, 'During the match, the fan presses Ask (Enter on a laptop) and says, for example:'), ul,
    el('p', {}, 'The commentator answers with the new level, and the channel here moves with it. Each channel shows the word to say.'));
  section.append(voice);

  const buttons = el('div', { class: 'row m-actions' });
  const reset = el('button', { type: 'button', id: 'm-reset' }, 'Reset');
  const submit = el('button', { type: 'button', id: 'm-submit' }, 'Save a copy (JSON)');
  buttons.append(reset, submit);
  const result = el('textarea', { id: 'm-json', readonly: '', 'aria-label': 'The submitted mix, as JSON', rows: '8' });
  result.hidden = true;
  section.append(buttons, result);

  // Every change, from a channel, a preset, Reset or the commentator, shows here (aria-valuetext: "35 out of 100").
  onMix((m) => {
    for (const [k, { input, out, db }] of rows) {
      const l = k === 'nearEnd' ? Math.round(m.nearEnd * 100) : levelFromDb(m[k] as number);
      input.value = String(l);
      out.textContent = String(l);
      out.classList.toggle('m-off', l === 0);
      input.setAttribute('aria-valuetext', levelText(l));
      if (db) db.textContent = dbText(m[k] as number);
    }
    for (const r of radios) r.checked = r.value === m.commentatorPos;
  });

  reset.addEventListener('click', () => {
    setMix(DEFAULT_MIX);
    saveDraft(null);
    saved.textContent = 'Playing our default mix. Move a sound to make it yours.';
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

  const host = hooks.host ?? document.getElementById('mixer-slot');
  if (host) host.append(section);
  else document.getElementById('app')?.append(section);
  startScope(canvas, hooks.analyser ?? (() => null));
  return section;
}
