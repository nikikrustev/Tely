// D39: the match list's fixtures, picking one by what was said, and what the fan hears back.
import { describe, expect, it } from 'vitest';
import { findFixture, FIXTURES, heardLine, listenOnce, recognitionCtor, type Recognition } from '../src/matches';

describe('the fixtures', () => {
  it('have one playable match, Reds v Navy, and 3 to 5 that are not in the demo', () => {
    expect(FIXTURES.filter((f) => f.playable).map((f) => `${f.home} v ${f.away}`)).toEqual(['Reds v Navy']);
    const rest = FIXTURES.filter((f) => !f.playable).length;
    expect(rest).toBeGreaterThanOrEqual(3);
    expect(rest).toBeLessThanOrEqual(5);
    const clubs = FIXTURES.flatMap((f) => [f.home, f.away]);
    expect(new Set(clubs).size).toBe(clubs.length);                    // one club, one match: a name picks one card
  });
});

describe('findFixture', () => {
  it('finds a match by either club, in any case, with or without "play"', () => {
    expect(findFixture('Play Reds')?.id).toBe('demo');
    expect(findFixture('play navy')?.id).toBe('demo');
    expect(findFixture('NAVY!')?.id).toBe('demo');
    expect(findFixture('play red')?.id).toBe('demo');                  // a plural club heard singular
    expect(findFixture('Play Saltmere')?.id).toBe('saltmere');
    expect(findFixture('put on Quarrydale please')?.id).toBe('fernhallow');
  });

  it('takes the club said first, matches whole words only, and finds nothing in anything else', () => {
    expect(findFixture('play saltmere, no, reds')?.id).toBe('saltmere');
    expect(findFixture('play bredsfield')).toBeNull();
    expect(findFixture('play some football')).toBeNull();
    expect(findFixture('')).toBeNull();
  });
});

/** A recogniser that hears the given alternatives, an error, or nothing at all. */
function fake(heard: { alts?: string[]; error?: string; silent?: boolean; throws?: boolean }) {
  return class implements Recognition {
    lang = ''; interimResults = true; maxAlternatives = 1;
    onresult: Recognition['onresult'] = null;
    onerror: Recognition['onerror'] = null;
    onend: Recognition['onend'] = null;
    aborted = false;
    start() {
      if (heard.throws) throw new Error('busy');
      if (heard.silent) return;
      queueMicrotask(() => {
        if (heard.error) this.onerror?.({ error: heard.error });
        else this.onresult?.({ results: [(heard.alts ?? []).map((transcript) => ({ transcript }))] });
        this.onend?.();
      });
    }
    abort() { this.aborted = true; }
  };
}

describe('listenOnce', () => {
  it('uses the first alternative that names a club', async () => {
    const h = await listenOnce(fake({ alts: ['play beds', 'play reds'] })).heard;
    expect(h.fixture?.id).toBe('demo');
    expect(h.said).toBe('play reds');
  });

  it('returns what was heard when no alternative names a club, and the error when there is one', async () => {
    expect(await listenOnce(fake({ alts: ['play beds'] })).heard).toEqual({ fixture: null, said: 'play beds' });
    expect(await listenOnce(fake({ error: 'not-allowed' })).heard).toEqual({ fixture: null, said: '', error: 'not-allowed' });
    expect(await listenOnce(fake({ throws: true })).heard).toEqual({ fixture: null, said: '', error: 'start' });
  });

  it('gives up after the timeout, and stop() ends a listen at once', async () => {
    expect(await listenOnce(fake({ silent: true }), 10).heard).toEqual({ fixture: null, said: '' });
    const l = listenOnce(fake({ silent: true }));
    l.stop();
    expect((await l.heard).error).toBe('aborted');
  });

  it('finds the browser recogniser under either name, or none', () => {
    const R = fake({});
    expect(recognitionCtor({ webkitSpeechRecognition: R })).toBe(R);
    expect(recognitionCtor({ SpeechRecognition: R })).toBe(R);
    expect(recognitionCtor({})).toBeNull();
  });
});

describe('heardLine', () => {
  const demo = FIXTURES[0]!, salt = FIXTURES[1]!;
  it('says how to open a found match, in keys on Laptop and taps on Phone', () => {
    expect(heardLine({ fixture: demo, said: 'play reds' }, true)).toBe('Reds against Navy. Press Enter to open the match.');
    expect(heardLine({ fixture: demo, said: 'play reds' }, false)).toBe('Reds against Navy. Tap it to open the match.');
  });

  it('says why it fell back to the list', () => {
    expect(heardLine(null, false)).toMatch(/^Voice search isn't available/);
    expect(heardLine({ fixture: null, said: '', error: 'not-allowed' }, false)).toMatch(/^The microphone isn't allowed/);
    expect(heardLine({ fixture: salt, said: 'play saltmere' }, false)).toMatch(/^Saltmere against Brackenmoor isn't available in the demo/);
    expect(heardLine({ fixture: null, said: 'play beds' }, false)).toBe('I heard "play beds", but no match with that club. Pick a match from the list.');
    expect(heardLine({ fixture: null, said: '' }, false)).toMatch(/^I didn't hear a match/);
  });
});
