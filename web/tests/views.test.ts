// D25 (27 Oct): the three views of one match, the fan's 0..100 sound scale, and the
// commentator's adjust_sound result reaching the mix. The page itself is covered by tests/a11y.spec.ts.
import { afterEach, describe, expect, it } from 'vitest';
import { adjustSound, dbFromLevel, DEFAULT_MIX, getMix, levelFromDb, MAX_DB, MIN_DB, MIX_KEY, setMix, SOUNDS, soundLevels } from '../src/audio/mix';
import { HINTS, initialView } from '../src/main';
import { presetMix, PRESETS, SAY_AS } from '../src/tester/mixer';

afterEach(() => { setMix(DEFAULT_MIX); });

function memory() {
  const data = new Map<string, string>();
  return { data, getItem: (k: string) => data.get(k) ?? null, setItem: (k: string, v: string) => { data.set(k, v); } };
}

describe('views', () => {
  it('opens ?view= when valid, Setup for the old ?mix=1 link, else Phone on a narrow screen and Laptop otherwise', () => {
    expect(initialView('?view=setup', true)).toBe('setup');
    expect(initialView('?view=phone', false)).toBe('phone');
    expect(initialView('?view=tv', false)).toBe('laptop');
    expect(initialView('?mix=1', true)).toBe('setup');
    expect(initialView('', true)).toBe('phone');
    expect(initialView('', false)).toBe('laptop');
  });

  it('says keys on Laptop and taps on Phone, for every pad state', () => {
    expect(Object.keys(HINTS.keys).sort()).toEqual(Object.keys(HINTS.touch).sort());
    expect(HINTS.keys.pause).toBe('Press Space to pause');
    expect(HINTS.keys.askLive).toMatch(/^Press Enter/);
    expect(HINTS.touch.askLive).toMatch(/^Tap/);
  });
});

describe('the 0..100 sound scale', () => {
  it('maps the dB range end to end: 0 is off, 100 is the loudest, and round-trips', () => {
    expect(levelFromDb(MIN_DB)).toBe(0);
    expect(levelFromDb(MAX_DB)).toBe(100);
    expect(dbFromLevel(0)).toBe(MIN_DB);
    for (let l = 0; l <= 100; l += 5) expect(levelFromDb(dbFromLevel(l))).toBe(l);
  });

  it('names the same sounds as the commentator tool and the desk', () => {
    expect(Object.keys(soundLevels()).sort()).toEqual(Object.keys(SOUNDS).sort());
    for (const [name, key] of Object.entries(SOUNDS)) expect(SAY_AS[key].replace(' ', '_')).toBe(name);
  });
});

describe('adjust_sound from the live commentator', () => {
  it('applies a level from the relay and keeps it on this device', () => {
    const s = memory();
    expect(adjustSound({ sound: 'whistle', level: 25 }, s)).toEqual({ key: 'whistle', level: 25 });
    expect(levelFromDb(getMix().whistle)).toBe(25);
    expect(JSON.parse(s.data.get(MIX_KEY)!).whistle).toBe(getMix().whistle);
  });

  it('applies a change when the relay did not know the level, clamped to 0..100', () => {
    const was = levelFromDb(getMix().roars);
    expect(adjustSound({ sound: 'reactions', change: -5 }, memory())?.level).toBe(was - 5);
    expect(adjustSound({ sound: 'reactions', change: 500 }, memory())?.level).toBe(100);
    expect(adjustSound({ sound: 'net', level: -3 }, memory())?.level).toBe(0);
  });

  it('ignores anything that is not a sound change (set_preferences still goes to the settings)', () => {
    for (const junk of [null, 'whistle', { haptics: 'off' }, { sound: 'music', level: 3 }, { sound: 'whistle' }]) {
      expect(adjustSound(junk, memory())).toBeNull();
    }
    expect(getMix()).toEqual(DEFAULT_MIX);
  });
});

describe('desk presets', () => {
  it('are DEFAULT_MIX plus their patch, inside the dB range', () => {
    expect(presetMix('default')).toEqual(DEFAULT_MIX);
    for (const p of PRESETS) {
      const m = presetMix(p.id);
      for (const v of Object.values(m)) if (typeof v === 'number' && v < 0) expect(v).toBeGreaterThanOrEqual(MIN_DB);
    }
    expect(presetMix('voice').commentator).toBe(DEFAULT_MIX.commentator + 6);
  });
});
