// Director's notes (Tier 1 item 9, D33): for sighted judges with the radar on (?radar=1),
// what the agents decided, shown only AFTER each moment has played. Every build-up's note waits until its shot's
// outcome is out (show_after = reveal_t, the spoiler clamp), so the panel can never hint that a chance is coming.
// Asks add a note when their answer is done: the Voice Live tools called and the time to the first answer audio.
// Not a live region: it would talk over the match; a screen-reader user can read it like any list.
import { bundleBase } from '../replay/base';

export interface Plan { build_up_level: number; lead_s: number; hold_ms: number; hint_type: string }
export interface Note {
  key: string; show_after: number; clock: string;
  plan: Plan | null; rules_plan: Plan; plan_check: string;
  latency_ms: number; tokens: number | null; xg: number; zone: string;
  line: { cue_id: string; text: string; truth_check: string; spoiler_check: string } | null;
}
export interface AskTrace { tools: string[]; latency_ms: number | null }

/** The notes whose moment is over at playhead p. Never one ahead of it. */
export const due = (notes: Note[], p: number): Note[] => notes.filter((n) => n.show_after <= p);

const plan = (p: Plan) => `level ${p.build_up_level.toFixed(2)}, lead ${p.lead_s.toFixed(1)} s, hold ${p.hold_ms} ms, hint ${p.hint_type}`;

export function noteText(n: Note, director: string): string {
  const head = `${n.clock} chance (xG ${n.xg.toFixed(2)}, ${n.zone}).`;
  const dir = n.plan
    ? `Director (${director}, ${(n.latency_ms / 1000).toFixed(1)} s${n.tokens ? `, ${n.tokens} tokens` : ''}): ${plan(n.plan)}.`
    : `Director reply ${n.plan_check}; the rules Director took over.`;
  const rules = `Rules Director would have said ${plan(n.rules_plan)}.`;
  const line = n.line
    ? `Build-up line "${n.line.text}": truth check ${n.line.truth_check}, spoiler check ${n.line.spoiler_check}.`
    : 'No build-up line: the level was under 0.3.';
  return `${head} ${dir} ${rules} ${line} Plan check: ${n.plan_check}.`;
}

export function askText(clock: string, t: AskTrace): string {
  const tools = t.tools.length ? t.tools.join(', ') : 'no tool';
  const ms = t.latency_ms === null ? '' : `; first answer audio ${(t.latency_ms / 1000).toFixed(2)} s after you stopped speaking`;
  return `${clock} Ask (Voice Live): ${tools}${ms}.`;
}

export function startNotes(el: HTMLElement, opts: { now(): number; clock(p: number): string; base?: string }) {
  el.hidden = false;
  el.replaceChildren();
  const h = document.createElement('h2');
  h.id = 'notes-h';
  h.textContent = "Director's notes";
  const hint = document.createElement('p');
  hint.className = 'hint';
  hint.textContent = 'What the agents decided, shown only after each moment has played.';
  const list = document.createElement('ol');
  list.id = 'notes-list';
  el.append(h, hint, list);
  el.setAttribute('aria-labelledby', 'notes-h');
  let notes: Note[] = [], director = 'Foundry';
  const shown = new Set<string>();
  const add = (text: string) => {
    const li = document.createElement('li');
    li.textContent = text;
    list.append(li);
  };
  void fetch(`${opts.base ?? bundleBase()}/director_notes.json`).then((r) => (r.ok ? r.json() : null))
    .then((d: { director?: string; notes?: Note[] } | null) => { notes = d?.notes ?? []; director = d?.director ?? director; })
    .catch(() => {});
  const timer = setInterval(() => {
    for (const n of due(notes, opts.now())) {
      if (shown.has(n.key)) continue;
      shown.add(n.key);
      add(noteText(n, director));
    }
  }, 500);
  const onAsk = (e: Event) => add(askText(opts.clock(opts.now()), (e as CustomEvent<AskTrace>).detail));
  window.addEventListener('tely:ask-trace', onAsk);
  return {
    stop() { clearInterval(timer); window.removeEventListener('tely:ask-trace', onAsk); el.hidden = true; el.replaceChildren(); },
  };
}
