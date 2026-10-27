// OWNER: B (Nikolay). Listener settings (BUILD_PLAN Stage 4): club end, crowd level and vibration.
// Saved in localStorage inside try/catch: a private window, blocked storage or a broken value never stops the app.
import type { HapticMode } from './haptics/haptics';

export type Club = 'H' | 'A';
/** The commentator's languages (D27): the pre-recorded match and the live answers. */
export const LANGS = ['en', 'bg', 'es', 'ar', 'fr', 'de', 'hi'] as const;
export type Lang = (typeof LANGS)[number];
/** How much the commentator says: today's whole Radio track, or only the lines with priority KEY_PRIORITY and up. */
export type Detail = 'full' | 'key';
export interface Settings {
  /** Which end you sit with: "H" Reds (home) or "A" Navy (away). Flips whose goals the crowd around you cheers. */
  club: Club;
  /** Crowd level against the commentary, 0..1. 0.5 = default mix; 0 = crowd almost off. */
  crowdMix: number;
  haptics: HapticMode;
  /** Vibration strength: 0.7 low, 1 medium, 1.4 high (file 41). */
  hapticStrength: number;
  /** Show the visible sound radar (for sighted friends and the video). */
  radar: boolean;
  /** Measured headphone delay in ms (Bluetooth calibration), or null to use what the browser reports. */
  audioOffsetMs: number | null;
  /** The commentator's language (D27), set in Setup or by asking the commentator. */
  lang: Lang;
  /** "Key moments only" or "Full radio" (the default): a filter on the cues' priority, no other words. */
  detail: Detail;
  /** Screen-reader mode: the AI voice is quiet and each commentary line goes to a polite live region instead, read at
   *  the fan's own screen-reader speed. Crowd, sound icons and vibration stay. */
  reader: boolean;
  /** One-ear mode: every sound summed to mono (one earbud, or hearing in one ear), plus a soft position tone. */
  mono: boolean;
  /** Follow my player (D34): a player id ("n11"), or null. A soft cue and the name when they get the ball. */
  follow: string | null;
}

export const DEFAULTS: Settings = { club: 'H', crowdMix: 0.5, haptics: 'full', hapticStrength: 1, radar: false, audioOffsetMs: null, lang: 'en',
  detail: 'full', reader: false, mono: false, follow: null };
export const STORAGE_KEY = 'tely.settings.v1';
/** The key from before the rename to Tely (D26): read once if the new key is empty, so saved settings carry over. */
export const LEGACY_STORAGE_KEY = 'audiostands.settings.v1';

/** The parts of Storage we use, so tests can pass a fake (or one that throws). */
export type StorageLike = Pick<Storage, 'getItem' | 'setItem'>;

/** localStorage if the browser lets us touch it, else null (reading the property itself can throw). */
export function browserStorage(): StorageLike | null {
  try {
    return typeof localStorage === 'undefined' ? null : localStorage;
  } catch {
    return null;
  }
}

/** Keep only valid values; anything missing or wrong falls back to the default. */
export function sanitize(x: unknown): Settings {
  const o = (x && typeof x === 'object' ? x : {}) as Record<string, unknown>;
  const num = (v: unknown, d: number, lo: number, hi: number) =>
    typeof v === 'number' && Number.isFinite(v) ? Math.min(hi, Math.max(lo, v)) : d;
  return {
    club: o.club === 'A' ? 'A' : 'H',
    crowdMix: num(o.crowdMix, DEFAULTS.crowdMix, 0, 1),
    haptics: o.haptics === 'off' || o.haptics === 'events' || o.haptics === 'full' ? o.haptics : DEFAULTS.haptics,
    hapticStrength: num(o.hapticStrength, DEFAULTS.hapticStrength, 0.5, 1.5),
    radar: o.radar === true,
    audioOffsetMs: typeof o.audioOffsetMs === 'number' && Number.isFinite(o.audioOffsetMs) ? num(o.audioOffsetMs, 0, 0, 500) : null,
    lang: LANGS.includes(o.lang as Lang) ? (o.lang as Lang) : DEFAULTS.lang,
    detail: o.detail === 'key' ? 'key' : 'full',
    reader: o.reader === true,
    mono: o.mono === true,
    follow: typeof o.follow === 'string' && /^[A-Za-z0-9_-]{1,12}$/.test(o.follow) ? o.follow : null,
  };
}

export function loadSettings(storage: StorageLike | null = browserStorage()): Settings {
  try {
    const raw = storage?.getItem(STORAGE_KEY) ?? storage?.getItem(LEGACY_STORAGE_KEY);
    return raw ? sanitize(JSON.parse(raw)) : { ...DEFAULTS };
  } catch {
    return { ...DEFAULTS };
  }
}

/** Returns false if the value could not be stored (the app keeps working with it in memory). */
export function saveSettings(s: Settings, storage: StorageLike | null = browserStorage()): boolean {
  try {
    if (!storage) return false;
    storage.setItem(STORAGE_KEY, JSON.stringify(sanitize(s)));
    return true;
  } catch {
    return false;
  }
}

/** Crowd output gain for a mix value: -18 dB at 0, the engine's 0.8 at 0.5, +4 dB at 1 (ours, tune by ear). */
export function crowdGainFor(mix: number): number {
  const m = Math.min(1, Math.max(0, mix));
  const db = m <= 0.5 ? -18 + 18 * (m / 0.5) : 4 * ((m - 0.5) / 0.5);
  return 0.8 * Math.pow(10, db / 20);
}

/**
 * The live commentator's set_preferences result (A7: relay -> live-ask.ts) as a settings patch. Only what the fan
 * asked for out loud and the tool allowed (haptics, crowd_mix, detail); anything else, including the old verbosity,
 * is dropped. Empty when nothing applies.
 */
export function prefsPatch(p: unknown): Partial<Settings> {
  const o = (p && typeof p === 'object' ? p : {}) as Record<string, unknown>;
  const patch: Partial<Settings> = {};
  if (o.haptics === 'off' || o.haptics === 'events' || o.haptics === 'full') patch.haptics = o.haptics;
  if (typeof o.crowd_mix === 'number' && Number.isFinite(o.crowd_mix)) patch.crowdMix = Math.min(1, Math.max(0, o.crowd_mix));
  if (LANGS.includes(o.language as Lang)) patch.lang = o.language as Lang;   // set_language (D27)
  if (o.detail === 'key' || o.detail === 'full') patch.detail = o.detail;     // set_preferences detail
  if ('follow' in o && (o.follow === null || (typeof o.follow === 'string' && /^[A-Za-z0-9_-]{1,12}$/.test(o.follow)))) {
    patch.follow = o.follow as string | null;                                  // set_preferences follow (D34)
  }
  return patch;
}
