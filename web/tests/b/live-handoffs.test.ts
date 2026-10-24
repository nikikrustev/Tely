// OWNER: B (Nikolay). A7's HANDOFFs to B: the live commentator's set_preferences reaches the settings, and A can open
// the preset menu through Ask.showPresets() instead of clicking B's button.
import { describe, expect, it } from 'vitest';
import { prefsPatch } from '../../src/settings';
import { LazyAsk } from '../../src/ask/ask';
import type { Ask, LaneBContext } from '../../src/contracts/b-exports';

describe('set_preferences from the live commentator', () => {
  it('maps the tool result (relay `prefs`) to settings', () => {
    expect(prefsPatch({ haptics: 'events', crowd_mix: 0.3 })).toEqual({ haptics: 'events', crowdMix: 0.3 });
    expect(prefsPatch({ crowd_mix: 0 })).toEqual({ crowdMix: 0 });            // "turn the crowd off" is a real value
    expect(prefsPatch({ crowd_mix: 7 })).toEqual({ crowdMix: 1 });
  });

  it('drops anything else: unknown keys, bad values, verbosity (no setting yet), the match itself', () => {
    expect(prefsPatch({ haptics: 'max', crowd_mix: '0.3', verbosity: 'calm', playhead_s: 9999, score: '5-0' })).toEqual({});
    for (const junk of [null, undefined, 'events', 42, []]) expect(prefsPatch(junk)).toEqual({});
  });
});

describe('Ask.showPresets()', () => {
  it('forwards to the menu once main.ts sets it, and is safe before', () => {
    const ask = new LazyAsk();
    expect(() => ask.showPresets()).not.toThrow();
    let opened = 0;
    ask.onShowPresets = () => { opened++; };
    const forA: Ask = ask;                                 // what A's lane receives
    forA.showPresets?.();
    expect(opened).toBe(1);
  });

  it('keeps b-exports append-only: a context without the new members still type-checks', () => {
    const old: LaneBContext = { crowd: { duck() {}, unduck() {} }, ask: { registerLiveMode() {} },
      clock: { now: () => 0, isPlaying: () => false, onChange: () => () => {} } };
    expect(old.pingBall).toBeUndefined();
  });
});
