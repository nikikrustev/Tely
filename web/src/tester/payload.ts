// OWNER: A (potencialbg). Tester mode (?test=1, D19): the events sent to the relay's POST /feedback, and the text
// behind "Copy my answers". Every key here is in relay/feedback.py SCHEMA; the relay refuses anything else.
import {
  ASK_WORKED, DEVICE, HEADPHONES, labelOf, PREFERRED, PROBES, SCALE, SCREEN_READER, SETTINGS_EASY, SIGHT, type ClipNo,
} from './questions';
import { newEventId, TASKS, type Ev, type TesterState } from './state';

export const MAX_BYTES = 4000;          // the relay allows 4096; leave room for nothing to go wrong
export const TEXT_MAX = 500;            // the relay's cap per text field
const TEXT_KEYS = ['confusing', 'liked', 'would_use', 'problem_text'];

export type Kind = 'consent' | 'task' | 'clip' | 'ask' | 'settings' | 'overall' | 'problem';

export function baseEvent(s: TesterState, kind: Kind, eid = newEventId()): Ev {
  const ev: Ev = { v: 1, kind, tester: s.id, eid, group: s.group };
  if (s.consent) {
    ev.consent_take_part = s.consent.takePart;
    ev.consent_quote = s.consent.quote;
  }
  return ev;
}

const bytes = (ev: Ev) => new TextEncoder().encode(JSON.stringify(ev)).length;

/** Text trimmed to TEXT_MAX, then the longest text shortened until the whole event fits in MAX_BYTES
 *  (Cyrillic is 2 bytes a character and emoji 4, so 3 x 500 characters can be too big). */
export function fit(ev: Ev, max = MAX_BYTES): Ev {
  const out: Ev = { ...ev };
  for (const k of TEXT_KEYS) {
    if (typeof out[k] === 'string') {
      const t = (out[k] as string).trim().slice(0, TEXT_MAX);
      if (t) out[k] = t; else delete out[k];
    }
  }
  while (bytes(out) > max) {
    const k = TEXT_KEYS.filter((x) => typeof out[x] === 'string').sort((a, b) => (out[b] as string).length - (out[a] as string).length)[0];
    if (!k) break;
    const t = out[k] as string;
    out[k] = t.slice(0, Math.max(0, Math.floor(t.length * 0.8)));
  }
  return out;
}

/** Browser and OS family from the user agent; the full string is never sent. iPadOS says "Macintosh", so the
 *  page passes touch points too. */
export function uaFamily(ua: string, touchPoints = 0): { browser: string; os: string } {
  let os = /Android/i.test(ua) ? 'android' : /iPhone|iPad|iPod/i.test(ua) ? 'ios' : /CrOS/.test(ua) ? 'chromeos'
    : /Windows/i.test(ua) ? 'windows' : /Macintosh|Mac OS X/i.test(ua) ? 'macos' : /Linux/i.test(ua) ? 'linux' : 'other';
  if (os === 'macos' && touchPoints > 1) os = 'ios';
  const browser = /SamsungBrowser/i.test(ua) ? 'samsung' : /Edg(e|A|iOS)?\//.test(ua) ? 'edge'
    : /OPR\/|Opera/.test(ua) ? 'opera' : /Firefox|FxiOS/.test(ua) ? 'firefox' : /Chrome|CriOS|Chromium/.test(ua) ? 'chrome'
      : /Safari/.test(ua) ? 'safari' : 'other';
  return { browser, os };
}

/** The tester's own answers in plain words, for "Copy my answers". No score, no group, no condition: those stay in
 *  the code line at the end, which only our eval/pull_feedback.py --paste reads. */
export function answersText(s: TesterState): string {
  const a = s.answers;
  const lines = ['Tely: my test answers', `Tester code: ${s.id}`, ''];
  for (const t of TASKS) lines.push(`Task ${t.id}, ${t.title}: ${s.tasks[t.id] === 'done' ? 'done' : s.tasks[t.id] === 'skip' ? 'skipped' : 'not done'}`);
  for (const c of [1, 2] as ClipNo[]) {
    const ca = a.clips[c];
    if (!ca) continue;
    lines.push('', `Questions about clip ${c}`);
    for (const p of PROBES) lines.push(`- ${p.question} ${labelOf(p.choices, ca.probes[p.id]) || '(no answer)'}`);
    for (const q of SCALE) lines.push(`- ${q.question} ${ca.scale[q.id] ?? '(no answer)'} out of 5`);
  }
  if (a.ask) {
    lines.push('', 'Ask the commentator', `- Questions from the list: ${a.ask.presets}`,
      `- Asked out loud: ${a.ask.liveTried ? 'yes' : a.ask.liveAvailable ? 'no' : 'not offered'}`,
      `- Did it answer you? ${labelOf(ASK_WORKED, a.ask.worked) || '(no answer)'}`);
  }
  if (a.settings) {
    lines.push('', 'Settings', `- Changed: ${a.settings.changed.join(', ') || 'nothing'}`,
      `- Easy to use? ${labelOf(SETTINGS_EASY, a.settings.easy) || '(no answer)'}`);
  }
  const o = a.overall;
  if (o) {
    lines.push('', 'Overall',
      `- What was confusing? ${o.confusing || '(blank)'}`, `- What did you like? ${o.liked || '(blank)'}`,
      `- What would make you use this? ${o.would_use || '(blank)'}`,
      `- Preferred clip: ${labelOf(PREFERRED, o.preferred) || '(no answer)'}`,
      `- Device: ${labelOf(DEVICE, o.device) || '(no answer)'}`, `- Headphones: ${labelOf(HEADPHONES, o.headphones) || '(no answer)'}`,
      `- Screen reader: ${labelOf(SCREEN_READER, o.screen_reader) || '(no answer)'}`, `- Sight: ${labelOf(SIGHT, o.sight) || '(no answer)'}`);
  }
  for (const p of a.problems) lines.push('', `Problem reported (${p.kind}): ${p.text || '(no text)'}`);
  lines.push('', 'Code for the team (please keep this line as it is):', codeLine(s));
  return lines.join('\n');
}

/** "AS1." + base64 of the events as UTF-8 JSON: every answer, with the scores, in one line. */
export function codeLine(s: TesterState): string {
  const b = new TextEncoder().encode(JSON.stringify(s.events.map((e) => e.ev)));
  let bin = '';
  for (const x of b) bin += String.fromCharCode(x);
  return `AS1.${btoa(bin)}`;
}
