// OWNER: A (potencialbg). Entry point for A's browser code: the Stage 4 commentary track; Stage 7 (live-ask.ts)
// lands here too.
import type { LaneAHandle, MountLaneA } from '../contracts/a-exports';
import { CommentaryTrackPlayer, parseCues, type VoiceContext } from './commentary-track';

export const BUNDLE_BASE = '/replay/v1/judge';

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

/** Browsers start audio only from a tap or key press. Create and resume the voice context in the first one, in the
 *  capture phase, so it happens inside the same gesture as B's Start button (iOS needs that; file 37). */
function unlockOnGesture(onContext: (ctx: VoiceContext) => void): void {
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

// SEAM(A->B): B's main.ts calls this once with LaneBContext (crowd bus, Ask, replay clock).
export const mountLaneA: MountLaneA = (ctx): LaneAHandle => {
  const commentary = new CommentaryTrackPlayer({
    clock: ctx.clock,
    crowd: ctx.crowd,
    fetchAudio: async (url) => (await getOk(`${BUNDLE_BASE}/${url}`)).arrayBuffer(),
  });
  if (typeof window !== 'undefined') {
    loadRadioCues().then((cues) => commentary.load(cues))
      .catch((err: unknown) => console.warn('[commentary] no commentary track; the match plays without it', err));
    unlockOnGesture((voice) => commentary.attach(voice));
    if (new URLSearchParams(location.search).get('debug') === '1') {
      (window as unknown as { audioStandsCommentary?: CommentaryTrackPlayer }).audioStandsCommentary = commentary;
    }
  }
  return { commentary };
};
