// Tier 1 items 5 and 6 (D30): the detail level, screen-reader mode and one-ear mode.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { filterDetail, KEY_PRIORITY } from '../src/voice';
import { parseCues } from '../src/voice/commentary-track';
import { isMono, registerContext, setMono } from '../src/audio/mono';
import { POSITION_HZ, positionPitch } from '../src/audio/position-tone';
import { DEFAULTS, prefsPatch, sanitize } from '../src/settings';

const CUES = parseCues(readFileSync(new URL('../public/replay/v1/judge/cues.en.radio.jsonl', import.meta.url), 'utf8'));

describe('detail level', () => {
  it('"Key moments only" keeps the AI notice, the build-ups, the outcomes and the card, and drops the ball lines', () => {
    const key = filterDetail(CUES, 'key');
    expect(key.length).toBe(12);
    expect(key.every((c) => (c.priority ?? 0) >= KEY_PRIORITY)).toBe(true);
    expect(key[0]?.kind).toBe('intro');                                  // the AI-voice notice is never filtered out
    expect(new Set(key.map((c) => c.kind))).toEqual(new Set(['intro', 'build', 'call', 'var', 'react', 'detail', 'foul']));
    expect(filterDetail(CUES, 'full')).toBe(CUES);
  });

  it('is a saved setting, and the commentator can set it', () => {
    expect(DEFAULTS.detail).toBe('full');
    expect(sanitize({ detail: 'key' }).detail).toBe('key');
    expect(sanitize({ detail: 'describer' }).detail).toBe('full');
    expect(prefsPatch({ detail: 'key' })).toEqual({ detail: 'key' });
    expect(prefsPatch({ verbosity: 'calm' })).toEqual({});
  });
});

describe('listening modes', () => {
  it('are off by default and saved only as true/false', () => {
    expect([DEFAULTS.reader, DEFAULTS.mono]).toEqual([false, false]);
    expect(sanitize({ reader: true, mono: 'yes' })).toMatchObject({ reader: true, mono: false });
  });

  it('one-ear mode sums every registered context to one channel, and back to stereo', () => {
    const ctx = (n = 2) => ({ destination: { channelCount: n, maxChannelCount: 2, channelInterpretation: 'discrete' } }) as unknown as BaseAudioContext;
    const a = ctx(), b = ctx();
    registerContext(a);
    setMono(true);
    registerContext(b);                                    // a context made later (the voice, after Start) follows too
    expect([a.destination.channelCount, b.destination.channelCount, isMono()]).toEqual([1, 1, true]);
    expect(a.destination.channelInterpretation).toBe('speakers');
    setMono(false);
    expect([a.destination.channelCount, b.destination.channelCount]).toEqual([2, 2]);
  });

  it('the position tone is low in your own third and high in your attacking third, from your team\'s side', () => {
    expect(positionPitch('zone_H_attacking_third_far', 'H')).toBe(POSITION_HZ.attacking);
    expect(positionPitch('zone_H_attacking_third_far', 'A')).toBe(POSITION_HZ.defensive);   // their attack is our box
    expect(positionPitch('zone_A_middle_third_centre', 'H')).toBe(POSITION_HZ.middle);
    expect(positionPitch('zone_A_defensive_third_near', 'H')).toBe(POSITION_HZ.attacking);
    expect(positionPitch('ball_out', 'H')).toBeNull();
    expect(POSITION_HZ.defensive).toBeLessThan(POSITION_HZ.middle);
    expect(POSITION_HZ.middle).toBeLessThan(POSITION_HZ.attacking);
  });
});
