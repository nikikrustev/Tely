// OWNER: A (potencialbg). The ?mix=1 sound mixer: the Submit file, the draft in storage (and storage that throws),
// and dB labels. The page itself is covered by tests/a/mixer.spec.ts (Playwright + axe).
import { afterEach, describe, expect, it } from 'vitest';
import { DEFAULT_MIX, getMix, MIX_GROUPS, parseMix, setMix } from '../../src/audio/mix';
import { dbText, DRAFT_KEY, LABELS, loadDraft, mixFile, ORDER, saveDraft } from '../../src/tester/mixer';
import type { StorageLike } from '../../src/settings';

afterEach(() => { setMix(DEFAULT_MIX); });

const throwing: StorageLike = {
  getItem() { throw new DOMException('denied', 'SecurityError'); },
  setItem() { throw new DOMException('full', 'QuotaExceededError'); },
};
function memory() {
  const data = new Map<string, string>();
  return { data, getItem: (k: string) => data.get(k) ?? null, setItem: (k: string, v: string) => { data.set(k, v); },
    removeItem: (k: string) => { data.delete(k); } };
}

describe('sound mixer', () => {
  it('has a label for every sound group, and shows every group once', () => {
    for (const k of MIX_GROUPS) expect(LABELS[k]).toBeTruthy();
    expect([...ORDER].sort()).toEqual([...MIX_GROUPS].sort());
  });

  it('Submit writes every value, and the file reads back as the same mix', () => {
    setMix({ pass: -20, commentatorPos: 'above', nearEnd: 0.8 });
    const file = mixFile(getMix(), new Date('2026-10-24T18:00:00Z'));
    expect(file.version).toBe(1);
    expect(file.saved).toBe('2026-10-24T18:00:00.000Z');
    expect(Object.keys(file.mix).sort()).toEqual(Object.keys(DEFAULT_MIX).sort());
    expect(parseMix(JSON.parse(JSON.stringify(file)))).toEqual(getMix());
  });

  it('keeps a draft in storage, clears it on Reset, and survives storage that throws', () => {
    const s = memory();
    setMix({ shot: -3 });
    saveDraft(getMix(), s);
    expect(loadDraft(s)?.shot).toBe(-3);
    saveDraft(null, s);
    expect(s.data.has(DRAFT_KEY)).toBe(false);
    expect(() => saveDraft(getMix(), throwing)).not.toThrow();
    expect(loadDraft(throwing)).toBeNull();
    s.data.set(DRAFT_KEY, '{not json');
    expect(loadDraft(s)).toBeNull();
  });

  it('says levels in dB, and -40 dB as off', () => {
    expect(dbText(-14)).toBe('-14.0 dB');
    expect(dbText(3)).toBe('+3.0 dB');
    expect(dbText(0)).toBe('0.0 dB');
    expect(dbText(-40)).toBe('off');
  });
});
