// OWNER: B (Nikolay). Connects the replay to the sound stage (file 43 §6 wire()). Everything is scheduled on the
// audio clock at the exact match time it belongs to, a few seconds ahead, so a busy main thread never makes it late.
// No cues here: A's commentary track loads cues.*.jsonl itself (TEAM_SPLIT.md).
import type { AudioStands } from './audio/audio-stands';
import type { CrowdEngine } from './audio/crowd-engine';
import type { ReplaySource, Segment } from './replay/replay-source';

export type Club = 'H' | 'A';

export interface Wired {
  /** Release and schedule whatever is now within the lead window. Returns how many segments it scheduled. */
  pump(): number;
}

export function wire(src: ReplaySource, stands: AudioStands | null, crowd: CrowdEngine, club: Club = 'H',
                     now: () => number = () => crowd.ctx.currentTime): Wired {
  const other: Club = club === 'H' ? 'A' : 'H';
  const at = (t: number) => Math.max(now(), src.toCtx(t));
  const schedule = (s: Segment) => {
    for (const sec of s.seconds) {
      crowd.setState(sec.crowd[club], at(sec.t));
      crowd.setOtherEnd(sec.crowd[other], at(sec.t));
    }
    if (stands) {
      s.ball.forEach(([x, y, z, speed, alive], k) =>
        stands.ballAt({ x, y, z, speed, alive: alive === 1 }, at(s.t0 + k / src.doc.ball_hz)));
      for (const e of s.earcons) stands.earcon(e.kind, e.x, e.y, at(e.t));
    }
    for (const o of s.one_shots) crowd.trigger(o.kind, at(o.t), o.end === club);
  };
  return {
    pump() {
      const due = src.due();
      due.forEach(schedule);
      return due.length;
    },
  };
}
