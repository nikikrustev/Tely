// One-ear mode (Tier 1 item 5b): with no left and right, where the ball is comes from two cues that survive mono:
// the end nearest the ball lifts (CrowdEngine.followBall), and this soft tone every few seconds, pitched by the third
// the ball is in, seen from the fan's own team: low = our defensive third, middle = midfield, high = our attacking third.
import type { Club } from '../settings';

export const POSITION_TONE_EVERY_S = 5;
export const POSITION_HZ = { defensive: 262, middle: 330, attacking: 440 } as const;   // C4, E4, A4: a major chord, calm

/** The tone for a get_ball_position fragment id ("zone_A_attacking_third_far"), or null when the ball is out. */
export function positionPitch(fragment: string | null | undefined, club: Club): number | null {
  const m = /^zone_([HA])_(defensive|middle|attacking)_third_/.exec(fragment ?? '');
  if (!m) return null;
  const third = m[2] as keyof typeof POSITION_HZ;
  if (m[1] === club) return POSITION_HZ[third];
  return POSITION_HZ[third === 'attacking' ? 'defensive' : third === 'defensive' ? 'attacking' : 'middle'];
}

/** 150 ms of sine, faded in and out (no click), well under the commentary. */
export function playPositionTone(c: BaseAudioContext, hz: number, out: AudioNode = c.destination): void {
  const osc = c.createOscillator(), g = c.createGain(), at = c.currentTime + 0.01;
  osc.frequency.setValueAtTime(hz, at);
  g.gain.setValueAtTime(0, at);
  g.gain.linearRampToValueAtTime(0.05, at + 0.03);
  g.gain.linearRampToValueAtTime(0, at + 0.15);
  osc.connect(g).connect(out);
  osc.start(at);
  osc.stop(at + 0.16);
}
