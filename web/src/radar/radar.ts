// The sound radar (; file 42): a visible top-down pitch for sighted
// friends and the muted demo video. Ball dot, crowd level per end, tension line, the haptic pulse and the current caption.
// Hidden from screen readers (aria-hidden: the listener hears all of this), and calm under reduced motion.
// Spoiler-safe: everything is read at the playhead (the sound engine queues ball moves ~3 s ahead, so it is not used).
import type { SegmentsDoc } from '../replay/replay-source';

export interface RadarModel {
  t: number;
  ball: { x: number; y: number; alive: boolean; poss: 'home' | 'away' | null } | null;
  crowd: { H: number; A: number };            // excitement 0..1 per end
  tension: number;
  history: number[];                         // tension for the last `historyS` seconds, oldest first
}

const HALF_L = 52.5, HALF_W = 34;

/** What the radar shows at playhead t, from data at or before t only. */
export function radarModel(doc: SegmentsDoc, t: number, historyS = 60): RadarModel {
  const p = Math.min(Math.max(t, doc.t0), doc.t1);
  const seconds = doc.segments.flatMap((s) => s.seconds);
  const known = seconds.filter((x) => x.t <= Math.floor(p));
  const cur = known[known.length - 1] ?? seconds[0];
  const seg = doc.segments.find((s) => s.t0 <= p && p < s.t1) ?? doc.segments[doc.segments.length - 1];
  let ball: RadarModel['ball'] = null;
  if (seg) {
    const k = Math.min(Math.floor((p - seg.t0) * doc.ball_hz), seg.ball.length - 1);
    const row = seg.ball[Math.max(0, k)];
    if (row) ball = { x: row[0], y: row[1], alive: row[4] === 1, poss: null };
  }
  return {
    t: p,
    ball,
    crowd: { H: cur?.crowd.H.excitement ?? 0, A: cur?.crowd.A.excitement ?? 0 },
    tension: cur?.tension ?? 0,
    history: known.filter((x) => x.t > p - historyS).map((x) => x.tension),
  };
}

/** Pitch metres -> canvas pixels. Main-stand view: +x to the right, the near touchline (y = -34) at the bottom. */
export function toCanvas(x: number, y: number, w: number, h: number, pad: number): [number, number] {
  return [pad + ((x + HALF_L) / (2 * HALF_L)) * (w - 2 * pad), pad + ((HALF_W - y) / (2 * HALF_W)) * (h - 2 * pad)];
}

/** One WebVTT cue lookup (A's captions_sdh.vtt uses the same seconds as the playhead). */
export interface Cue { start: number; end: number; text: string }
export function parseVtt(vtt: string): Cue[] {
  const toS = (s: string) => {
    const [h, m, rest] = s.trim().split(':');
    return Number(h) * 3600 + Number(m) * 60 + Number(rest);
  };
  const cues: Cue[] = [];
  for (const block of vtt.split(/\r?\n\r?\n/)) {
    const lines = block.split(/\r?\n/);
    const i = lines.findIndex((l) => l.includes('-->'));
    if (i < 0) continue;
    const [a, b] = (lines[i] as string).split('-->');
    cues.push({ start: toS(a as string), end: toS((b as string).split(' ').filter(Boolean)[0] as string), text: lines.slice(i + 1).join(' ') });
  }
  return cues;
}
export const captionAt = (cues: Cue[], t: number) => cues.find((c) => c.start <= t && t < c.end)?.text ?? '';

export interface RadarDeps {
  now: () => number;
  doc: SegmentsDoc;
  pulses: () => number;                 // count of vibration pulses sent so far
  cues: Cue[];
  reducedMotion: boolean;
}

/** Draw the radar into `host` until stop() is called. */
export function startRadar(host: HTMLElement, d: RadarDeps): { stop(): void } {
  host.hidden = false;
  host.setAttribute('aria-hidden', 'true');
  const canvas = document.createElement('canvas');
  const caption = document.createElement('p');
  caption.className = 'radar-caption';
  host.replaceChildren(canvas, caption);
  const g = canvas.getContext('2d');
  let raf = 0, last = 0, lastPulses = d.pulses(), pulseUntil = 0;
  const frameMs = d.reducedMotion ? 500 : 33;           // reduced motion: a calm 2 updates per second, no flashing
  const css = getComputedStyle(document.documentElement);
  const color = (v: string, f: string) => css.getPropertyValue(v).trim() || f;

  const draw = (ts: number) => {
    raf = requestAnimationFrame(draw);
    if (ts - last < frameMs || !g) return;
    last = ts;
    const w = (canvas.width = host.clientWidth || 320), h = (canvas.height = Math.round(w * 0.62)), pad = 22;
    const m = radarModel(d.doc, d.now());
    const fg = color('--fg', '#111'), muted = color('--muted', '#777'), accent = color('--accent', '#b00020');
    g.clearRect(0, 0, w, h);
    // pitch
    g.strokeStyle = muted; g.lineWidth = 2;
    const [x0, y0] = toCanvas(-HALF_L, HALF_W, w, h, pad), [x1, y1] = toCanvas(HALF_L, -HALF_W, w, h, pad);
    g.strokeRect(x0, y0, x1 - x0, y1 - y0);
    const [cx] = toCanvas(0, 0, w, h, pad);
    g.beginPath(); g.moveTo(cx, y0); g.lineTo(cx, y1); g.stroke();
    // crowd level per end: home end on the left (Reds defend -x), away end on the right
    for (const [end, xL] of [['H', 2], ['A', w - 14]] as const) {
      const lvl = Math.max(0, Math.min(1, m.crowd[end])), bh = (h - 2 * pad) * lvl;
      g.fillStyle = end === 'H' ? '#d0342c' : '#1f3a93';
      g.fillRect(xL, h - pad - bh, 12, bh);
    }
    // tension line along the bottom edge
    if (m.history.length > 1) {
      g.strokeStyle = accent; g.lineWidth = 2; g.beginPath();
      m.history.forEach((v, i) => {
        const px = pad + (i / 59) * (w - 2 * pad), py = h - 4 - v * (pad - 8);
        if (i) g.lineTo(px, py); else g.moveTo(px, py);
      });
      g.stroke();
    }
    // ball
    if (m.ball) {
      const [bx, by] = toCanvas(m.ball.x, m.ball.y, w, h, pad);
      g.fillStyle = m.ball.alive ? fg : muted;
      g.beginPath(); g.arc(bx, by, 7, 0, Math.PI * 2); g.fill();
    }
    // haptic pulse: a steady ring for half a second (never a strobe)
    const n = d.pulses();
    if (n > lastPulses) { lastPulses = n; pulseUntil = ts + 500; }
    if (ts < pulseUntil) {
      g.strokeStyle = accent; g.lineWidth = 4;
      g.beginPath(); g.arc(w - 30, 30, 12, 0, Math.PI * 2); g.stroke();
    }
    caption.textContent = captionAt(d.cues, m.t);
  };
  raf = requestAnimationFrame(draw);
  return { stop() { cancelAnimationFrame(raf); host.hidden = true; } };
}
