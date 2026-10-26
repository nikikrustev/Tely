// OWNER: A (potencialbg). Entry point for A's browser code: the Stage 4 commentary track and the Stage 7 live Ask.
import type { LaneAHandle, MountLaneA } from '../contracts/a-exports';
import { CommentaryTrackPlayer, parseCues } from './commentary-track';
import { browserIO, LiveAsk } from './live-ask';
import { bundleBase } from '../replay/base';

export const BUNDLE_BASE = bundleBase();   // the judge cut, or a dev-only soak bundle (replay/base.ts)

interface Manifest {
  tracks: Record<string, Record<string, string>>;
  ai_voice_notice: string;
}

async function getOk(url: string): Promise<Response> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  return r;
}

/** Static files only (BUILD_PLAN Stage 4: zero backend): the manifest names the cue file for English Radio. */
export async function loadRadioCues(base = BUNDLE_BASE) {
  const man = (await (await getOk(`${base}/manifest.json`)).json()) as Manifest;
  const file = man.tracks.en?.radio ?? 'cues.en.radio.jsonl';
  return parseCues(await (await getOk(`${base}/${file}`)).text());
}

/** ?names=<stem>: a local listening test's commentary (D21: real club and player names over the synthetic match).
 *  Only the dev server serves /replay/v1/local/ (web/.local/, git-ignored), so on the deployed site this 404s and the
 *  shipped track plays instead. */
export function localCommentaryBase(search: string): string | null {
  const stem = new URLSearchParams(search).get('names');
  return stem && /^[a-z0-9-]{1,40}$/.test(stem) ? `/replay/v1/local/${stem}` : null;
}

/** Browsers start audio only from a tap or key press. Create and resume the voice context in the first one, in the
 *  capture phase, so it happens inside the same gesture as B's Start button (iOS needs that; file 37). */
function unlockOnGesture(onContext: (ctx: AudioContext) => void): void {
  const Ctor = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!Ctor) return;
  let ctx: AudioContext | null = null;
  const events = ['pointerup', 'click', 'keydown', 'touchend'] as const;
  const unlock = () => {
    if (!ctx) {
      ctx = new Ctor({ latencyHint: 'balanced' }); // same hint as B's context, so both see the same output latency
      onContext(ctx);
    }
    const blip = ctx.createBufferSource(); // a 1-sample silent buffer, played inside the gesture, unlocks older iOS
    blip.buffer = ctx.createBuffer(1, 1, ctx.sampleRate);
    blip.connect(ctx.destination);
    blip.start();
    const c = ctx;
    c.resume().then(() => {
      if (c.state === 'running') events.forEach((e) => window.removeEventListener(e, unlock, true));
    }).catch(() => {}); // not allowed yet: the next gesture tries again
  };
  events.forEach((e) => window.addEventListener(e, unlock, true));
}

/** The relay's /voice URL: `relay` from /live.json (written at deploy by azure.yaml from the relay's azd output), or
 *  `?relay=` with `?debug=1` for local testing. None (no live Ask, presets only) if neither, or with `?live=0`. */
export async function liveRelayUrl(search: string, fetchJson: (u: string) => Promise<unknown>): Promise<string | null> {
  const q = new URLSearchParams(search);
  if (q.get('live') === '0') return null;
  let base = q.get('debug') === '1' ? q.get('relay') : null;
  if (!base) {
    try {
      base = ((await fetchJson('/live.json')) as { relay?: string } | null)?.relay ?? null;
    } catch {
      base = null;
    }
  }
  if (!base || !/^https?:\/\//.test(base)) return null;
  return `${base.replace(/\/$/, '').replace(/^http/, 'ws')}/voice`;
}

// SEAM(A->B): B's main.ts calls this once with LaneBContext (crowd bus, Ask, replay clock).
export const mountLaneA: MountLaneA = (ctx): LaneAHandle => {
  let audioBase = BUNDLE_BASE;
  const commentary = new CommentaryTrackPlayer({
    clock: ctx.clock,
    crowd: ctx.crowd,
    fetchAudio: async (url) => (await getOk(`${audioBase}/${url}`)).arrayBuffer(),
  });
  if (typeof window !== 'undefined') {
    const local = localCommentaryBase(location.search);
    const cues = local
      ? getOk(`${local}/cues.en.radio.jsonl`).then(async (r) => { const c = parseCues(await r.text()); audioBase = local; return c; })
        .catch(() => loadRadioCues())
      : loadRadioCues();
    cues.then((c) => commentary.load(c))
      .catch((err: unknown) => console.warn('[commentary] no commentary track; the match plays without it', err));
    unlockOnGesture((c) => commentary.attach(c));
    // The live Ask gets its own context: CommentaryTrack.pause() suspends the commentary's, and B pauses the
    // commentary before every answer. Created in the same Start tap, so it may play (file 37).
    let liveVoice: AudioContext | null = null;
    unlockOnGesture((c) => { liveVoice = c; });
    const debug = new URLSearchParams(location.search).get('debug') === '1';
    if (debug) {
      (window as unknown as { audioStandsCommentary?: CommentaryTrackPlayer }).audioStandsCommentary = commentary;
    }
    // Stage 7: "Ask out loud". B's Ask shows the button once this registers (b-exports.ts Ask.registerLiveMode).
    liveRelayUrl(location.search, async (u) => { const r = await fetch(u); return r.ok ? r.json() : null; })
      .then((url) => {
        if (!url) return;
        // WHY: the relay scales to zero (D6, no money), so wake it while the fan is still listening, not on the press.
        fetch(url.replace(/^ws/, 'http').replace(/\/voice$/, '/health'), { mode: 'no-cors' }).catch(() => {});
        const live = new LiveAsk(url, browserIO({ audio: () => liveVoice, base: BUNDLE_BASE, lane: ctx }));
        ctx.ask.registerLiveMode(live);   // SEAM(A->B): b-exports.ts Ask.registerLiveMode(handler)
        document.addEventListener('visibilitychange', () => { if (document.hidden) live.cancel(); });
        if (debug) (window as unknown as { audioStandsLive?: LiveAsk }).audioStandsLive = live;
      })
      .catch(() => {});
  }
  return { commentary };
};
