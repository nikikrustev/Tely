// OWNER: B (Nikolay). Connects the replay to the sound stage and haptics (file 43 §6 wire()). Sound is scheduled on
// the audio clock at the exact match time it belongs to, a few seconds ahead, so a busy main thread never makes it late.
// Vibration and per-second callbacks use timers aimed at the same moments. No cues here: A's commentary track loads
// cues.*.jsonl itself (TEAM_SPLIT.md).
import type { SoundStage } from './audio/sound-stage';
import type { CrowdEngine } from './audio/crowd-engine';
import type { Haptics, Tacton } from './haptics/haptics';
import type { ReplaySource, Segment } from './replay/replay-source';
import type { Club } from './settings';

export type { Club };
export type Second = Segment['seconds'][number];

export interface WireOptions {
  /** Which end the listener sits with; read at scheduling time, so a Settings change applies within ~3 s. */
  club?: () => Club;
  haptics?: Haptics | null;
  /** Called when each second is heard (score announcements, debug). */
  onSecond?: (s: Second) => void;
  /** Extra ms between the audio clock and the ear (Bluetooth etc.); haptics fire against it. */
  outputDelayMs?: () => number;
  timers?: { set: (f: () => void, ms: number) => number; clear: (id: number) => void };
}

export interface Wired {
  /** Release and schedule whatever is now within the lead window. Returns how many segments it scheduled. */
  pump(): number;
  /** Cancel every pending timer (pause, seek). Audio-clock events are cancelled by the engines' cancelFrom(). */
  cancel(): void;
}

export function wire(src: ReplaySource, stands: SoundStage | null, crowd: CrowdEngine, club: Club = 'H',
                     now: () => number = () => crowd.ctx.currentTime, opts: WireOptions = {}): Wired {
  const ours = opts.club ?? (() => club);
  const timers = opts.timers ?? { set: (f, ms) => setTimeout(f, ms) as unknown as number, clear: (id) => clearTimeout(id) };
  const pending = new Set<number>();
  const at = (t: number) => Math.max(now(), src.toCtx(t));
  /** Run f when match time t is heard (timer, not the audio clock). */
  const later = (t: number, f: () => void) => {
    const ms = Math.max(0, (at(t) - now()) * 1000);
    const id = timers.set(() => { pending.delete(id); f(); }, ms);
    pending.add(id);
  };
  const schedule = (s: Segment) => {
    const c = ours();
    const other: Club = c === 'H' ? 'A' : 'H';
    const from = src.now() - 0.05; // after a seek, skip what lies before the jump target
    for (const sec of s.seconds) {
      if (sec.t < Math.floor(from)) continue;
      crowd.setState(sec.crowd[c], at(sec.t));
      crowd.setOtherEnd(sec.crowd[other], at(sec.t));
      if (opts.haptics || opts.onSecond) later(sec.t, () => { opts.haptics?.setTension(sec.tension); opts.onSecond?.(sec); });
    }
    s.ball.forEach(([x, y, z, speed, alive], k) => {
      const t = s.t0 + k / src.doc.ball_hz;
      if (t < from) return;
      stands?.ballAt({ x, y, z, speed, alive: alive === 1 }, at(t));   // silent: where the ball is, for the ping
      crowd.followBall(x, at(t));                                       // the end nearest the ball reacts more
    });
    if (stands) {
      for (const e of s.earcons) if (e.t >= from) stands.earcon(e.kind, e.x, e.y, at(e.t));
    }
    for (const o of s.one_shots) if (o.t >= from) crowd.trigger(o.kind, at(o.t), o.end === c);
    const hap = opts.haptics;
    if (hap) {
      for (const h of s.haptics ?? []) {
        if (h.t < from) continue;
        const ms = (at(h.t) - now()) * 1000 + (opts.outputDelayMs?.() ?? 0);
        hap.event(h.tacton as Tacton, h.team, ms);
      }
    }
  };
  return {
    pump() {
      const due = src.due();
      due.forEach(schedule);
      return due.length;
    },
    cancel() {
      pending.forEach((id) => timers.clear(id));
      pending.clear();
    },
  };
}
