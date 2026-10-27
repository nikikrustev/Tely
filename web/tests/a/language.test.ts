// OWNER: A (potencialbg). D27: the commentator's language, saved in settings, set by the commentator's set_language,
// and the manifest's per-language tracks.
import { afterEach, describe, expect, it, vi } from 'vitest';
import { DEFAULTS, LANGS, prefsPatch, sanitize } from '../../src/settings';
import { loadRadioCues } from '../../src/lane-a';
import { liveLanguage, setLiveLanguage } from '../../src/lane-a/language';

afterEach(() => { vi.unstubAllGlobals(); setLiveLanguage('en'); });

describe('the language setting', () => {
  it('defaults to English and keeps only the languages we recorded', () => {
    expect(DEFAULTS.lang).toBe('en');
    expect([...LANGS]).toEqual(['en', 'bg', 'es', 'ar', 'fr', 'de', 'hi']);
    expect(sanitize({ lang: 'bg' }).lang).toBe('bg');
    expect(sanitize({ lang: 'it' }).lang).toBe('en');
  });

  it('takes set_language from the live commentator, and nothing it does not know', () => {
    expect(prefsPatch({ language: 'ar' })).toEqual({ lang: 'ar' });
    expect(prefsPatch({ language: 'klingon' })).toEqual({});
  });

  it('is what the live Ask sends', () => {
    setLiveLanguage('fr');
    expect(liveLanguage()).toBe('fr');
  });
});

describe('loadRadioCues', () => {
  const cue = '{"cue_id":"c_0001","t_in":1,"utterance":{"audio_url":"audio/bg/radio/x.mp3","duration_ms":900}}';
  const stub = (tracks: Record<string, { radio: string }>) => {
    const seen: string[] = [];
    vi.stubGlobal('fetch', async (u: string) => {
      seen.push(u);
      return new Response(u.endsWith('manifest.json') ? JSON.stringify({ tracks }) : cue);
    });
    return seen;
  };

  it('loads the cue file the manifest names for the language', async () => {
    const seen = stub({ en: { radio: 'cues.en.radio.jsonl' }, bg: { radio: 'cues.bg.radio.jsonl' } });
    expect(await loadRadioCues('/b', 'bg')).toHaveLength(1);
    expect(seen).toEqual(['/b/manifest.json', '/b/cues.bg.radio.jsonl']);
  });

  it('refuses a language the bundle has no track for, so the player keeps what it has', async () => {
    stub({ en: { radio: 'cues.en.radio.jsonl' } });
    await expect(loadRadioCues('/b', 'de')).rejects.toThrow(/no de commentary/);
  });
});

describe('the quick questions in the chosen language', () => {
  it('reads answers/<lang>/, and keeps the current answers when a language has none', async () => {
    const { FragmentPlayer } = await import('../../src/ask/ask');
    const seen: string[] = [];
    vi.stubGlobal('fetch', async (u: string) => {
      seen.push(u);
      if (u.includes('/answers/xx/')) return new Response('missing', { status: 404 });
      return new Response(JSON.stringify({ fragments: { done: { file: u.includes('/es/') ? 'es.mp3' : 'en.mp3' } } }));
    });
    const p = new FragmentPlayer({} as BaseAudioContext, {} as AudioNode, '/r/answers');
    expect(await p.load()).toBe(1);
    expect(await p.setLanguage('es')).toBe(true);
    expect(await p.setLanguage('xx')).toBe(false);          // stays Spanish
    expect(await p.setLanguage('es')).toBe(true);           // already loaded: no fetch
    expect(await p.setLanguage('en')).toBe(true);
    expect(seen).toEqual(['/r/answers/index.json', '/r/answers/es/index.json', '/r/answers/xx/index.json', '/r/answers/index.json']);
  });
});
