// D36: low-data mode is picked from the browser's hint unless the fan chose.
import { describe, expect, it } from 'vitest';
import { autoLowData, lowDataOn, lowUrl } from '../src/lowdata';
import { sanitize } from '../src/settings';

describe('low-data mode', () => {
  it('turns itself on for Save-Data and slow connections, and the fan\'s choice wins', () => {
    expect(autoLowData({ saveData: true })).toBe(true);
    expect(autoLowData({ effectiveType: '3g' })).toBe(true);
    expect(autoLowData({ effectiveType: '4g' })).toBe(false);
    expect(autoLowData(undefined)).toBe(false);
    expect(lowDataOn(null, { saveData: true })).toBe(true);
    expect(lowDataOn(false, { saveData: true })).toBe(false);
    expect(lowDataOn(true, { effectiveType: '4g' })).toBe(true);
    expect(sanitize({}).lowData).toBeNull();
    expect(sanitize({ lowData: true }).lowData).toBe(true);
  });

  it('plays the same file name from the low-data folder', () => {
    expect(lowUrl('audio/en/radio/abc.mp3')).toBe('audio/en/radio-lo/abc.mp3');
    expect(lowUrl('audio/hi/radio/abc.mp3')).toBe('audio/hi/radio-lo/abc.mp3');
  });
});
