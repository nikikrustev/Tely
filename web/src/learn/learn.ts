// OWNER: B (Nikolay). "Learn the sounds" (BUILD_PLAN Stage 8 item 2; file 37: a short training session lifts
// earcon recognition to about 80%). A skippable ~2-minute guided tour, offered on the Start screen: each step says
// what a sound means, then plays it. Nothing here comes from the match, so nothing can spoil it.

/** What the tour can play. Times are audio-clock seconds. */
export interface LearnStage {
  ball(x: number, y: number, speed: number, at: number): void;
  ballOff(at: number): void;
  earcon(kind: 'pass' | 'shot' | 'tackle' | 'save' | 'whistle' | 'net' | 'ping', x: number, y: number, at: number): void;
  crowd(excitement: number, at: number): void;
  heartbeat?(tension: number): void;
  now(): number;
}

export interface Step {
  id: string;
  say: string;
  /** What the voice says, when it differs from the text shown (D26: the browser voice reads "Tely" as "tee-lee"). */
  speech?: string;
  /** Play the demo starting at audio time `at`; returns how long it lasts (s). */
  play(s: LearnStage, at: number): number;
}

/** The ball moves across, from `from` to `to`, with a soft pass every second. The ball itself is silent (no grass
 *  hiss, 24 Oct); you hear where it is from the kicks and from the crowd end nearest it. */
function sweep(s: LearnStage, at: number, from: number, to: number, secs: number): number {
  for (let k = 0; k <= secs * 10; k++) {
    const u = k / (secs * 10), x = from + (to - from) * u;
    s.ball(x, 0, 14, at + k / 10);
    if (k % 10 === 0) s.earcon('pass', x, 0, at + k / 10);
  }
  return secs;
}

export const STEPS: Step[] = [
  { id: 'intro', say: 'Welcome to Tely. Here are the sounds, one by one. Use headphones if you can. Press Escape to skip.',
    speech: 'Welcome to Telly. Here are the sounds, one by one. Use headphones if you can. Press Escape to skip.',
    play: () => 0 },
  { id: 'ball', say: 'Like in a real stadium, you cannot hear the ball itself. Follow the kicks, and the crowd: the end nearest the ball gets louder. Here it travels from your left to your right.',
    play: (s, at) => { const d = sweep(s, at, -45, 45, 5); s.ballOff(at + d); return d + 0.5; } },
  { id: 'sides', say: 'Reds attack to your right. Navy attack to your left. Here is the ball near Navy\'s goal, on your right.',
    play: (s, at) => { const d = sweep(s, at, 30, 45, 2); s.ballOff(at + d + 1); return d + 1.5; } },
  { id: 'pass', say: 'A pass sounds like a soft thud, from where the pass is played.',
    play: (s, at) => { s.earcon('pass', -30, 0, at); s.earcon('pass', 0, 0, at + 0.8); s.earcon('pass', 30, 0, at + 1.6); return 2.5; } },
  { id: 'shot', say: 'A shot is a harder thud.', play: (s, at) => { s.earcon('shot', 35, 0, at); return 1.5; } },
  { id: 'save', say: 'When the keeper catches it, you hear this.', play: (s, at) => { s.earcon('save', 50, 0, at); return 1.5; } },
  { id: 'net', say: 'And this is the ball hitting the net.', play: (s, at) => { s.earcon('net', 52, 0, at); return 1.5; } },
  { id: 'whistle', say: 'The referee\'s whistle, for a foul or a kick-off.', play: (s, at) => { s.earcon('whistle', 0, 0, at); return 1.5; } },
  { id: 'crowd', say: 'The crowd around you grows when an attack builds, before a chance. Listen to it rise, then settle.',
    play: (s, at) => { s.crowd(0.2, at); s.crowd(0.95, at + 1); s.crowd(0.3, at + 6); return 9; } },
  { id: 'heartbeat', say: 'On an Android phone, a heartbeat vibration speeds up with the tension. Hold your phone to feel it.',
    play: (s) => { s.heartbeat?.(0.8); return 5; } },
  { id: 'ask', say: 'Any time, press A, or the Ask button, to ask the commentator where the ball is, or the score.',
    play: () => 0 },
  { id: 'done', say: 'That\'s all. Press Start to hear the match.', play: (s) => { s.heartbeat?.(0); return 0; } },
];

export interface TourDeps {
  stage: LearnStage;
  speak: (text: string) => Promise<void>;
  show?: (text: string) => void;
  wait?: (ms: number) => Promise<void>;
}

/** Runs the tour; skip() stops it after the current sentence (and silences the demo). */
export class Tour {
  private stopped = false;
  constructor(private d: TourDeps) {}

  skip(): void {
    this.stopped = true;
  }

  get skipped(): boolean {
    return this.stopped;
  }

  /** Plays every step; returns the ids that were played (for tests and the transcript). */
  async run(steps: Step[] = STEPS): Promise<string[]> {
    const played: string[] = [];
    const wait = this.d.wait ?? ((ms: number) => new Promise<void>((r) => setTimeout(r, ms)));
    for (const step of steps) {
      if (this.stopped) break;
      this.d.show?.(step.say);
      await this.d.speak(step.speech ?? step.say);
      if (this.stopped) break;
      const dur = step.play(this.d.stage, this.d.stage.now() + 0.2);
      played.push(step.id);
      if (dur > 0) await wait((dur + 0.4) * 1000);
    }
    this.d.stage.ballOff(this.d.stage.now());
    this.d.stage.crowd(0.2, this.d.stage.now());
    this.d.stage.heartbeat?.(0);
    return played;
  }
}
