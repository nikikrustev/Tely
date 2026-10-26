// OWNER: B (Nikolay). Judge mode: plays web/public/replay/v1/<cut>/segments.json from static files (file 43 §6).
// It is also the one replay clock (ReplayClock in contracts/b-exports.ts) that A's commentary track follows.
import type { ReplayClock } from '../contracts/b-exports';
import type { CrowdState } from '../audio/crowd-engine';
import type { Earcon } from '../audio/audio-stands';
import { bundleBase } from './base';

export interface CrowdEnds { H: CrowdState; A: CrowdState }
export interface Segment {
  t0: number;
  t1: number;
  /** 10 Hz: [x, y, z, speed m/s, alive 0/1] */
  ball: [number, number, number, number, number][];
  crowd: CrowdEnds;
  tension: number;
  seconds: { t: number; crowd: CrowdEnds; tension: number; score: { home: number; away: number } }[];
  one_shots: { t: number; end: 'H' | 'A'; kind: string }[];
  earcons: { t: number; kind: Earcon; x: number; y: number }[];
  haptics: { t: number; tacton: string; team: 'home' | 'away' | null }[];
}
export interface SegmentsDoc {
  format: string;
  version: string;
  match_id: string;
  t0: number;
  t1: number;
  seg_s: number;
  ball_hz: number;
  segments: Segment[];
}

/** Anything with an audio clock (an AudioContext, or a fake in tests). */
export interface Clocked { readonly currentTime: number }

export class ReplaySource implements ReplayClock {
  private anchorCtx = 0; // audio time when the playhead was at anchorMatch
  private anchorMatch: number;
  private playing = false;
  private next = 0;
  private listeners = new Set<(playheadS: number, playing: boolean) => void>();

  /** leadS: how far ahead of the playhead segments are released (file 43: 3 s audio prefetch). */
  constructor(private ctx: Clocked, readonly doc: SegmentsDoc, readonly leadS = 3) {
    this.anchorMatch = doc.t0;
  }

  // SEAM(B->A): ReplayClock (contracts/b-exports.ts). A's commentary schedules its lines against now().
  now(): number {
    const t = this.playing ? this.anchorMatch + (this.ctx.currentTime - this.anchorCtx) : this.anchorMatch;
    return Math.min(Math.max(t, this.doc.t0), this.doc.t1);
  }

  isPlaying(): boolean {
    return this.playing && this.now() < this.doc.t1;
  }

  onChange(listener: (playheadS: number, playing: boolean) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /** Start or resume. `delayS` gives the scheduler a head start so the first sounds are not late. */
  play(delayS = 0.3): void {
    if (this.playing) return;
    this.anchorCtx = this.ctx.currentTime + delayS;
    this.playing = true;
    this.emit();
  }

  pause(): void {
    if (!this.playing) return;
    this.anchorMatch = this.now();
    this.playing = false;
    this.emit();
  }

  /** Jump to match time `t` (e.g. "Next big moment"). Keeps playing if it was playing. Listeners (A's commentary
   *  track) re-anchor on the change; the caller must cancel sound already queued after now. */
  seek(t: number, delayS = 0.3): void {
    this.anchorMatch = Math.min(Math.max(t, this.doc.t0), this.doc.t1);
    this.anchorCtx = this.ctx.currentTime + (this.playing ? delayS : 0);
    const i = this.doc.segments.findIndex((s) => s.t1 > this.anchorMatch);
    this.next = i < 0 ? this.doc.segments.length : i;
    this.emit();
  }

  /** Audio-clock time at which match time `t` is heard. */
  toCtx(t: number): number {
    return this.anchorCtx + (t - this.anchorMatch);
  }

  /** Segments that are now within the lead window and were not released yet, in order. */
  due(): Segment[] {
    if (!this.playing) return [];
    const out: Segment[] = [];
    const horizon = this.now() + this.leadS;
    let s = this.doc.segments[this.next];
    while (s && s.t0 <= horizon) {
      out.push(s);
      this.next++;
      s = this.doc.segments[this.next];
    }
    return out;
  }

  private emit(): void {
    for (const l of this.listeners) l(this.now(), this.playing);
  }
}

export async function loadSegments(base = bundleBase()): Promise<SegmentsDoc> {
  return (await (await fetch(`${base}/segments.json`)).json()) as SegmentsDoc;
}
