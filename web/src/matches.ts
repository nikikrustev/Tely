// The match list (27 Oct, D39): the one playable synthetic match and some fictional fixtures that are not in the demo.
// The fan picks a match by voice ("Play Reds") with the browser's own speech recognition, or from the list. Every
// result, and every reason to fall back to the list, is said aloud: the fan may not be looking at the screen.

export interface Fixture { id: string; home: string; away: string; when: string; playable: boolean }

/** Every club here is made up (D21). Only Reds v Navy has a match behind it. */
export const FIXTURES: readonly Fixture[] = [
  { id: 'demo', home: 'Reds', away: 'Navy', when: 'Demo', playable: true },
  { id: 'saltmere', home: 'Saltmere', away: 'Brackenmoor', when: '15:00', playable: false },
  { id: 'fernhallow', home: 'Fernhallow', away: 'Quarrydale', when: '17:30', playable: false },
  { id: 'ostwick', home: 'Ostwick', away: 'Duneholt', when: '20:00', playable: false },
  { id: 'glenvarra', home: 'Glenvarra', away: 'Velmora', when: 'Sun', playable: false },
];

/** "Reds against Navy": how a fixture is said (a voice reads "v" as "vee"). */
export const spoken = (f: Fixture) => `${f.home} against ${f.away}`;

/** The fixture a phrase names, by either club ("Play Reds", "navy", "the red one"); the club said first wins. */
export function findFixture(said: string, list: readonly Fixture[] = FIXTURES): Fixture | null {
  const words = ` ${said.toLowerCase().replace(/[^a-z]+/g, ' ').trim()} `;
  let best: Fixture | null = null, at = Infinity;
  for (const f of list) {
    for (const club of [f.home, f.away]) {
      const name = club.toLowerCase();
      // A plural club is often heard singular ("Play Red").
      for (const form of name.endsWith('s') ? [name, name.slice(0, -1)] : [name]) {
        const i = words.indexOf(` ${form} `);
        if (i >= 0 && i < at) { at = i; best = f; }
      }
    }
  }
  return best;
}

/** The parts of the Web Speech API's SpeechRecognition we use (Chrome, Edge and Safari; not Firefox). */
export interface Recognition {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
  start(): void;
  abort(): void;
}
export type RecognitionCtor = new () => Recognition;

export function recognitionCtor(w: object = globalThis): RecognitionCtor | null {
  const g = w as { SpeechRecognition?: RecognitionCtor; webkitSpeechRecognition?: RecognitionCtor };
  return g.SpeechRecognition ?? g.webkitSpeechRecognition ?? null;
}

/** What one listen heard: the fixture named, if any, what was said, and the recogniser's error, if any. */
export interface Heard { fixture: Fixture | null; said: string; error?: string }

/** Listen once. Resolves with the first alternative that names a club, else with what was heard (maybe nothing). */
export function listenOnce(Ctor: RecognitionCtor, timeoutMs = 8000): { heard: Promise<Heard>; stop(): void } {
  let settle: (h: Heard) => void = () => {};
  const heard = new Promise<Heard>((r) => { settle = r; });
  let done = false, timer: ReturnType<typeof setTimeout> | null = null;
  const finish = (h: Heard) => {
    if (done) return;
    done = true;
    if (timer) clearTimeout(timer);
    settle(h);
  };
  let rec: Recognition | null = null;
  const abort = () => { try { rec?.abort(); } catch { /* already stopped */ } };
  try {
    rec = new Ctor();
    rec.lang = 'en-GB';
    rec.interimResults = false;
    rec.maxAlternatives = 5;
    rec.onresult = (e) => {
      const alts = Array.from(e.results[0] ?? [], (a) => a.transcript);
      const hit = alts.map((said) => ({ said, fixture: findFixture(said) })).find((h) => h.fixture);
      finish(hit ?? { fixture: null, said: alts[0] ?? '' });
    };
    rec.onerror = (e) => finish({ fixture: null, said: '', error: e.error });
    rec.onend = () => finish({ fixture: null, said: '' });
    timer = setTimeout(() => { abort(); finish({ fixture: null, said: '' }); }, timeoutMs);
    rec.start();
  } catch {
    finish({ fixture: null, said: '', error: 'start' });
  }
  return { heard, stop: () => { abort(); finish({ fixture: null, said: '', error: 'aborted' }); } };
}

/** What the fan hears after a listen. `keys` says Enter (Laptop) rather than tap (Phone). */
export function heardLine(h: Heard | null, keys: boolean): string {
  if (!h) return 'Voice search isn\'t available in this browser. Pick a match from the list.';
  if (h.error === 'not-allowed' || h.error === 'service-not-allowed') return 'The microphone isn\'t allowed. Pick a match from the list.';
  if (h.fixture?.playable) return `${spoken(h.fixture)}. ${keys ? 'Press Enter' : 'Tap it'} to open the match.`;
  if (h.fixture) return `${spoken(h.fixture)} isn't available in the demo. Reds against Navy is. Pick it from the list.`;
  if (h.said) return `I heard "${h.said}", but no match with that club. Pick a match from the list.`;
  return 'I didn\'t hear a match. Pick one from the list, or press Say a match again.';
}

export interface ListHooks {
  /** Open the playable match. */
  open(): void;
  /** Say this aloud (or through the fan's screen reader) and show it. */
  tell(text: string): void;
  /** Laptop: talk about keys rather than taps. */
  keys(): boolean;
  /** Where focus goes when voice falls back to the list. */
  listTop: HTMLElement;
  recognition?: RecognitionCtor | null;
}

/** Fills #fixtures and wires the microphone button and the pop-up card. */
export function mountMatchList(hooks: ListHooks): { reset(): void } {
  const $ = (id: string) => document.getElementById(id)!;
  const list = $('fixtures'), mic = $('voice-pick') as HTMLButtonElement, micLabel = mic.querySelector('.vp-label')!;
  const status = $('voice-status'), picked = $('picked'), pickedOpen = $('picked-open') as HTMLButtonElement;
  const IDLE = status.textContent ?? '';
  const span = (cls: string, ...kids: (string | Node)[]) => {
    const s = document.createElement('span');
    s.className = cls;
    s.append(...kids);
    return s;
  };
  for (const f of FIXTURES) {
    const li = document.createElement('li');
    li.dataset.fixture = f.id;
    const card = document.createElement(f.playable ? 'button' : 'div');
    card.className = 'fx';
    if (card instanceof HTMLButtonElement) { card.type = 'button'; card.id = `card-${f.id}`; card.addEventListener('click', () => hooks.open()); }
    // Teams first, so a screen reader says "Reds v Navy" before the time; the commas are for its pauses only.
    const when = f.playable ? span('fx-when') : span('fx-when', span('sr-only', ', '), f.when);
    if (f.playable) when.insertAdjacentHTML('beforeend', '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M8 5.5v13a1 1 0 0 0 1.5.86l10.5-6.5a1 1 0 0 0 0-1.72L9.5 4.64A1 1 0 0 0 8 5.5z"/></svg>');
    card.append(
      span('fx-teams', span('fx-team', f.home), span('sr-only', ' v '), span('fx-team', f.away)),
      when,
      span('fx-note', span('sr-only', ', '), f.playable ? 'Synthetic match, ready to play' : 'Not available in the demo'));
    li.append(card);
    list.append(li);
  }

  let listening: ReturnType<typeof listenOnce> | null = null;
  const reset = () => {
    listening?.stop();
    picked.hidden = true;
    for (const li of list.querySelectorAll<HTMLElement>('li[data-picked]')) delete li.dataset.picked;
    status.textContent = IDLE;
  };
  const setMic = (on: boolean) => {
    mic.dataset.state = on ? 'listening' : 'idle';
    micLabel.textContent = on ? 'Stop listening' : 'Say a match';
  };
  /** Back to the list, with the reason said aloud. */
  const fallBack = (line: string, fixtureId?: string) => {
    if (fixtureId) list.querySelector<HTMLElement>(`li[data-fixture="${fixtureId}"]`)!.dataset.picked = '';
    status.textContent = line;
    hooks.listTop.focus();
    hooks.tell(line);
  };
  mic.addEventListener('click', async () => {
    if (listening) { listening.stop(); return; }
    reset();
    const Ctor = hooks.recognition === undefined ? recognitionCtor() : hooks.recognition;
    if (!Ctor) { fallBack(heardLine(null, hooks.keys())); return; }
    // Visual only, like live Ask: a screen-reader announcement now would be heard as the request.
    status.textContent = 'Listening. Say "Play" and a club, like "Play Reds".';
    setMic(true);
    const l = listenOnce(Ctor);
    listening = l;
    const h = await l.heard;
    listening = null;
    setMic(false);
    if (h.error === 'aborted') { status.textContent = 'Stopped listening.'; return; }
    const line = heardLine(h, hooks.keys());
    if (!h.fixture?.playable) { fallBack(line, h.fixture?.id); return; }
    // Found: the card pops up over the list, with focus on it, so Enter (or a tap) opens the match.
    picked.hidden = false;
    status.textContent = line;
    pickedOpen.focus();
    hooks.tell(line);
  });
  pickedOpen.addEventListener('click', () => hooks.open());
  // Enter opens the popped-up card even when focus has moved off it (a click on the page, say).
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter' || picked.hidden || picked.offsetParent === null) return;
    if ((e.target as HTMLElement | null)?.closest('button, a, input, select, textarea, [role="tab"]')) return;
    e.preventDefault();
    hooks.open();
  });
  return { reset };
}
