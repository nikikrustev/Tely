# 38 — A crowd that reacts like a real home end: generating stadium atmosphere from match state

_Accessed/compiled: 20 Oct 2026 · Priority area: Render + Personalise (audio channel) for Audio Stands (20 Home End + 17 Heartbeat); also 19 Match Music, F Graphics Desk, A TwinCast_

## TL;DR

- **Broadcasters in 2020 used human-triggered sample libraries, not automation.**
  - Sky Sports and NBC got 800+ club-specific clips per league from EA's FIFA library. A sound operator "like a DJ" fired them live.
  - EA's sound designer says the setup was a looping bed, randomised home and away chant clips, and operator one-shots. Applause ducked the chants and the chants ducked the bed.
  - Sky Deutschland built its own samples, layered on audio from the two teams' previous meeting.
  - We can automate exactly what those operators did, because we know the match state.
- **Use three control numbers: `excitement` (arousal 0..1), `valence` (-1..1, from our club's point of view) and `danger` (-1..1, + = we attack).**
  - The first two are Russell's circumplex axes. The third tells the mix which end is in trouble.
  - The engine turns them into 4 looped or granular beds, a synthetic chant, a procedural clap ensemble, and one-shots with refractory limits.
- **Look-ahead must be spoiler-safe.** The anticipation swell uses only the chance quality (xT/xG) of the upcoming shot, never its outcome. A big chance gets the same swell whether it goes in or not, which is what a real crowd knows.
  - On our toy match, an 8 s look-ahead raised excitement 1 s before the goal from 0.61 to 0.94.
  - Excitement crossed 0.6 two seconds earlier than without look-ahead.
- **Legal:** use only CC0 crowd recordings and our own generated chant motifs. Never use real chants or club names.
  - Lawyers note that copying a melody "could infringe", even an excerpt of about 5 seconds.
  - BBC Sound Effects (RemArc licence) is reported to cover personal, educational and research use only, so leave it out.
  - Freesound has usable CC0 football material, including a whole CC0 stadium-reaction pack (list in §4).
- **Mix for a blind listener on headphones.** Keep commentary at least ~12 dB above the crowd: a 2026 study found every listener group rated speech better at a +12 dB dialogue-to-background ratio than at +7. Add a speech-band dip, a safety limiter and soft attacks on one-shots. Rate-limit reactions so 90 minutes does not become fatiguing.

## Findings

### 1. How the 2020 "fake crowd" broadcasts actually worked

| Who | What they did | Source |
|---|---|---|
| EA SPORTS FIFA → Sky Sports, NBC (PL), LaLiga | More than 800 crowd clips per league, gathered over years for FIFA. EA: "There is nothing simulated or generic. It is all club-specific content." A broadcaster's sound operator triggers clips in real time, e.g. for an away tackle or a home shot. The crowd feed also went into the NBC commentator's headset. Viewers could choose the augmented feed or the stadium-only feed. | AP, 11 Jun 2020; Deseret News, 8 Jun 2020 |
| EA (Paul Boechler interview) | Live operation ran in **Ableton Live**, because a fully automated system "wasn't feasible" in the time available. It used a looping background bed, randomised home and away chant clips played in sequence, and operator one-shots. **Applause ducks chants, chants duck the bed.** The team avoids heavy limiting and downward compression, which raise the din. It uses upward expansion, dynamic EQ and manual automation instead. Loops are avoided where possible because listeners notice them. There are crowd-size variants (7k/15k/20k/40k) and context variants of the goal cheer (blowout, consolation, cup-clinching). Context matters: ball position alone can't tell an own goal from a VAR-overturned goal. | Sound Particles blog |
| Sky Deutschland (Bundesliga) | The base layer is audio from the teams' previous meeting, mixed in the OB van. A sound producer in Unterföhring triggers samples for fouls, penalties, VAR decisions and fan reactions from a sample board. Up to 10 people worked across a weekend. FIFA 20 was the tonal benchmark, but Sky used its own samples. | ESPN, 29 May 2020 |

**Lesson for us.** The craft is the *mix rules* (bed, chants, one-shots, ducking order) plus *timing*. Human operators react after the fact. Our pipeline knows the state, and with a delay it knows the next 8 s as well.

### 2. Research we can quote for the narrative (crowd noise matters)

- **Nevill, Balmer & Williams (2002).** 40 qualified referees judged 47 challenges from a video. Those who heard crowd noise were less certain and gave **15.5% fewer fouls against the home team** than those watching in silence.
- **Ghost games (2019/20).**
  - **Leitner & Richlan (2021)** studied 1,286 matches in 8 leagues. The home-win share fell from 48.1% to 39.8%. Home points per game fell from 1.69 to 1.44 and away rose from 1.07 to 1.32. Home teams got +26.2% foul-play yellow cards.
  - **Dilger & Vischer** compared 83 Bundesliga ghost games with the same 83 pairings played with fans. Home wins fell from 48.2% to 32.5%.
  - An *Economics Letters* (Dec 2020) paper found that the home team's foul and card advantage reversed without fans.
- **Use in the demo.** One honest line: "Crowd noise is part of the game. Studies of empty-stadium matches found the home advantage shrank." This is narrative only. Our generator must not change referee behaviour because of our synthetic crowd unless we label it.

### 3. Emotion model: why excitement, valence and danger

- **Russell's circumplex (1980)** places affect on a circle: pleasure at 0°, arousal at 90°, displeasure at 180°, sleepiness at 270°. Two axes cover almost every crowd mood we need:

| Mood | Excitement | Valence | Layers |
|---|---|---|---|
| Euphoria | high | + | roar, chant, claps |
| Anxiety | high | − | tense murmur |
| Content | low | + | soft murmur, polite applause |
| Gloom | low | − | thin murmur |

- **We add `danger`**, the signed threat of the current possession (xT/PV, files 07/08), because the same excitement sounds different when *we* attack (rising "ooh") and when *they* do. With danger, our end goes quiet and the away end becomes audible.
- **Validation dataset.** Franzoni et al. (2020) released an "Emotional Crowd Sound" set on IEEE DataPort: 39 approval, 14 disapproval and 15 neutral clips, segmented into 1 s blocks. A 2025 follow-up reports roughly 97–99% accuracy for a CNN on those blocks. Optional QA: run that kind of classifier on our rendered mix and check that approval tracks valence > 0. Licence not checked (unverified).

### 4. Free-licence crowd material (checked on Freesound, 20 Oct 2026)

Freesound pages show the licence per sound. Downloads need a free Freesound login, which the user creates; we do not.

| Use as | Sound / pack | Licence (verified on page unless noted) |
|---|---|---|
| Bed, swell, goal, miss | **"Sound Of Sankt Pauli"** pack (itmightgetloud). Millerntor recordings at ~29.5k fans: *General Ambience 01, Excited 01, Chance Missed 01, Goal 01, Mood Waves 01* (4:03, 48 kHz). Pack https://freesound.org/people/itmightgetloud/packs/44412/ | CC0 (checked on Mood Waves 01; other items via the CC0 search filter) |
| Big "huuuu" groan/ooh | felix.blume, *Crowd yelling huuuuu (60k persons)*, Mineirão, binaural, 96 kHz/24-bit, 54 s. https://freesound.org/people/felix.blume/sounds/612131/ | CC0 |
| Cheers | Krizin pack *Crowd Cheer Sports Game*, 7 sounds, 96 kHz. https://freesound.org/people/Krizin/packs/36296/ | CC0 (checked on Crowd Cheer 5) |
| Groan / sigh, crowd whistling, **sung "ooh" vowel for chants** | ShangusBurger, GameSoundCon 2024 walla session. Recorded "for the sole purpose of being published online for free under CC0". Each take is in several mic formats, **including binaural (BIN-AmbeoVR)**. e.g. https://freesound.org/people/ShangusBurger/sounds/764324/ and pack https://freesound.org/people/ShangusBurger/packs/42102/ | CC0 |
| Short ooh / groan | CHallSmith *GroupReactions* (Group Ooh 2, 2.9 s; Group Groan 2). https://freesound.org/people/CHallSmith/packs/46348/ | CC0 (checked on Group Ooh 2) |
| Ambience alternatives | Vogyik *Norwegian football match ambience* (XY/ORTF/AB/binaural) 868982; FlatHill *Sports Crowd Various Sounds* 324756; kyles applause/cheer 455659 | CC0 per search filter (pages not opened) |
| Not CC0 | Gregor Quendel free crowd cheering (itch.io) | CC BY 4.0 per search summary (unverified). Needs attribution. |
| **Avoid** | BBC Sound Effects (RemArc) | Coverage says personal, educational or research use only, with no commercial use. The BBC licence page could not be fetched (unverified). A hackathon entry for a commercial sponsor is not clearly "research", so skip it. |

**Audit rule.** Real stadium recordings (St Pauli, San Siro, Mexico) can contain **identifiable chants, club names or abuse**. Listen to every clip, cut sung passages, and keep only wordless reactions. Never label a clip with the real club. Keep a `licences.json` manifest (sound id, author, URL, licence).

### 5. Legal: chants and trademarks

- **Song lyrics as a whole are protected.** A three-word phrase is "probably not sufficient to be an original literary work" (Bird & Bird). But copying a substantial part of a **melody** could infringe, "even if the excerpt is only about five seconds long" (Managing IP, 2021).
- **Fan-altered chants have unclear ownership** (the team, the ultras or the original writers), and "everybody else is doing it" is no defence (GGI, 2024). I found no case law clearing chant use (unverified gap).
- **Our rule.** No real chants, songs or melodies, and no real club names or crests in audio or text.
  - Chants are **procedurally generated 8-step pentatonic motifs, seeded per synthetic club**, sung with a CC0 vowel sample. Each fictional club gets its "own" song.
  - This also fits the hackathon's synthetic-only rule.
  - EA's 2020 selling point was "club-specific" content. We can't copy that, and we don't need to.

### 6. Procedural and granular building blocks

- **Granular bed.** A grain is roughly 10–200 ms of sample (Roads, via the audience-feedback review). Scheduling many short random-offset grains from a 30–60 s CC0 bed gives a texture that never audibly loops. Density and pitch follow excitement. Use `AudioBufferSourceNode.start(when, offset, duration)`. Each source can be started only once, so make one node per grain.
- **Applause synthesis.** Lee & Reiss (AES 2020) model each clap as filtered noise with an exponential-decay envelope, and an ensemble of spatially spread clappers as the crowd. The model has an "enthusiasm" parameter, and listeners rated it more realistic than four other methods (abstract only; full text paywalled).
- **Scheduling.** Use Chris Wilson's "two clocks" pattern: a ~25 ms JS timer schedules everything due in the next ~100 ms on the audio clock.
- **ML generation exists but is overkill.** Shah et al. (LIQUE 2021) generated crowd noise from commentary audio with CycleGAN and MelGAN. Patents describe ML-driven synthetic crowd responses. For a 2-person team, samples plus rules are more controllable and explainable.

### 7. Mixing for headphones and a blind listener

- **Speech first.** A JSLHR (2026) study compared dialogue-to-background ratios of about +7 and +12 dB. All groups, including listeners with hearing loss, rated understanding better at +12 dB (from the abstract snippet; page 403). Recommendations:
  - default duck depth of −9 dB (gain 0.35) **plus** a −6 dB peaking cut at 2 kHz on the crowd bus while the commentator speaks
  - a "Clarity" preset at −14 dB
  - a user crowd-level slider.
- **Ducking dynamics** (file 27). Use `setTargetAtTime`, which is ~95% of the way after 3 time constants: fast down (τ 0.08 s) and slow up (τ 0.5 s). Use the EA hierarchy too: applause > chants > bed.
- **Loudness.** AES TD1008 is reported to target about −18 LUFS for speech/mixed streams and −17 for sports (secondary sources; unverified against the PDF). Put a limiter (`DynamicsCompressorNode`, ratio 20) on the master. Avoid broadband compression of the crowd, per EA's advice.
- **Hearing safety.** WHO-ITU H.870 sets an adult reference dose of 80 dBA for 40 h/week. Default the master to a moderate level, and never let a goal roar jump to full scale. One-shots get an 80 ms attack ramp so they don't startle.
- **Fatigue.**
  - Per-sound refractory times (4 s default) and random variants with ±6% playback rate.
  - Reactions decay (τ 3–30 s), so the crowd falls back to murmur.
  - Quiet stretches are realistic: the home end *should* go quiet under pressure.
  - Planet Coaster's audio team limited how often reactions fire with a probability setting (Audiokinetic blog; page 403, from a search summary, unverified).
- **Space.** Pan our end to one side (`homePan`) and the away end, dull and low-passed, to the other. A binaural CC0 bed (GSC24 BIN or felix.blume) gives the "I'm in the stand" feeling on headphones. Check that the mix still works in mono for single-earbud users.

### 8. The state machine (signals → state → layers)

| Signal (file) | Effect |
|---|---|
| Possession side + threat xT/PV (07/08) | `danger` = ± threat. Our attack → swell; their attack → our murmur −45%, tense layer, away end up |
| Upcoming shot within the look-ahead window (xG only) | Anticipation ramp over the last 5 s before the shot → excitement and danger up. **Same for goal and miss.** |
| Leverage / win-prob swing (23) | Raises baseline excitement late in close games (nervous murmur) |
| Pressure/chaos index (09) | Small excitement boost (scrappy, loud) |
| Events after they happen | Goal for: roar, chant. Goal against: stunned hush. Our miss: ooh→groan. Their miss: relief applause. Foul on us: whistles/jeers. Card for them: short cheer. Our sub: applause. VAR-like pause: hushed hold for 20 s. |
| Score diff | Valence offset (`tanh`) |

Output: one state per second as a timed cue (`metric:"crowd"`, payload `{excitement, valence, danger}`), plus one-shot cues with exact `tc_in`. These go through the file-24 scheduler, so the crowd, commentator and haptics share one clock.

## So what for us

- **Audio Stands, Interpret → Render (audio) → Personalise (club end).**
  - Build `crowd_states()` as a tiny Interpret-side function that emits crowd cues on the shared cue bus.
  - Build `CrowdEngine` as the client-side Render. It needs no Azure service.
  - Personalise = the listener's club. The same match renders mirrored for the other end (see the toy output: valence flips, and our goal becomes their "stunned hush").
  - The commentator (file 27) knows the outcome and builds the drama. The crowd only knows "big chance coming", so the two never contradict each other. A blind listener gets build-up without spoilers from the crowd.
  - Duck under the commentator and under the fan's own spoken questions. Use Live-Reference AEC from file 27, because the crowd plays from the same speakers.
- **17 Heartbeat.** Drive the haptics from the same `excitement` and `danger` (pulse rate ∝ excitement, a strong buzz on one-shots). One signal, two senses.
- **19 Match Music.** Use the same state for tempo and mode. **A TwinCast** gets a soundtrack for rendered video at no extra cost. **F Graphics Desk** gets a "crowd" fader the producer can hold or ride.
- **Recommendation.** Day 1: download about 15 CC0 clips (§4), cut them, and write the manifest. Day 2: CrowdEngine plus mapping on the seeded match. Tune the weights by ear with the commentary on. Pitch line: "an automated version of what Sky's sound operators did by hand in 2020, tuned to your club, without a single real chant."

## Reuse: code & links

**Python: signals → crowd state with spoiler-safe look-ahead** (core function. The toy-match generator lived in a session scratch script, not the repo; it ran on Python 3 on 20 Oct 2026.)

```python
import math
REACT = {  # (d_excitement, d_valence, tau_s) from the listener club's view
    ("goal", True): (1.00, 1.00, 25), ("goal", False): (0.30, -0.90, 30),
    ("shot", True): (0.55, -0.35, 5), ("shot", False): (0.25, 0.35, 4),   # our miss = groan, theirs = relief
    ("foul", True): (0.15, 0.10, 3),  ("foul", False): (0.30, -0.30, 4),
    ("card", True): (0.20, -0.30, 5), ("card", False): (0.25, 0.25, 5),
    ("sub", True): (0.10, 0.20, 6),   ("sub", False): (0.05, 0.00, 4)}
def smoothstep(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)

def crowd_states(ticks, events, club="H", lookahead_s=8.0, lead_s=5.0):
    """ticks: per-second rows (t, poss, threat, chaos, leverage, score_h, score_a).
    events: (t, kind, team, xg). Uses only events up to t+lookahead_s (our broadcast delay).
    Anticipation uses xg only, never the outcome: identical swell for goal and miss."""
    out, exc_s, val_s, dang_s, hold_until = [], 0.15, 0.0, 0.0, -1.0
    for k in ticks:
        t = k.t
        mine = 1.0 if k.poss == club else (-1.0 if k.poss else 0.0)
        danger = mine * k.threat
        antic = sum((1 if e.team == club else -1) * min(1.0, 2 * e.xg) * smoothstep(1 - (e.t - t) / lead_s)
                    for e in events if e.kind in ("shot", "goal") and t < e.t <= t + lookahead_s)
        de = dv = 0.0
        for e in events:
            if e.t <= t:
                r = REACT.get((e.kind, e.team == club))
                if r: w = math.exp(-(t - e.t) / r[2]); de += r[0] * w; dv += r[1] * w
                if e.kind == "var" and t - e.t < 20: hold_until = e.t + 20
        diff = (k.score_h - k.score_a) * (1 if club == "H" else -1)
        exc = 0.15 + 0.25 * k.leverage + 0.35 * abs(danger) + 0.15 * k.chaos + 0.5 * abs(antic) + de
        val = 0.5 * math.tanh(0.5 * diff) + 0.4 * danger + 0.3 * antic + dv
        if t < hold_until: exc, val = 0.35 + 0.3 * k.leverage, 0.0          # VAR-like hush
        exc, val = max(0, min(1, exc)), max(-1, min(1, val))
        up, dn = 1 - math.exp(-1 / 0.8), 1 - math.exp(-1 / 4.0)              # rise fast, settle slow
        exc_s += (up if exc > exc_s else dn) * (exc - exc_s)
        val_s += (1 - math.exp(-1 / 2.0)) * (val - val_s)
        dang_s += (1 - math.exp(-1 / 1.5)) * (danger + 0.5 * antic - dang_s)
        out.append(dict(t=t, excitement=round(exc_s, 2), valence=round(val_s, 2), danger=round(max(-1, min(1, dang_s)), 2)))
    return out
```

Toy run. The match is 180 s: H attack with a saved shot at 28 s, A pressure with a foul at 60 s, an A shot wide at 84 s, a VAR check at 100 s, an H goal at 150 s and an H sub at 170 s.

| t (s) | H end: exc / val / danger | A end: exc / val / danger |
|---|---|---|
| 26 (H build-up) | 0.67 / 0.30 / 0.74 | 0.67 / −0.30 / −0.74 |
| 31 (after H save) | 0.81 / −0.15 / 0.05 (groan) | 0.64 / 0.13 / −0.05 (relief) |
| 80 (A pressure) | 0.57 / −0.26 / −0.65 | 0.57 / 0.26 / 0.65 |
| 148 (pre-goal) | 0.82 / 0.39 / 0.95 | 0.82 / −0.39 / −0.95 |
| 153 (after goal) | 1.00 / 0.93 / 0.13 | 0.76 / −0.93 / −0.13 |
| 175 | 0.82 / 0.76 / 0.08 | 0.52 / −0.68 / −0.08 |

Look-ahead check (H end): with look-ahead 0 s, excitement first reached 0.6 at 148 s and was 0.61 at 149 s. With 8 s, it reached 0.6 at 146 s and was **0.94 at 149 s**. Cues for H: `ooh_groan@28, whistles_jeer@60, relief_applause@84, hush@100, roar@150, applause@170`. The weights are our starting guesses: tune them by ear.

**TypeScript: `CrowdEngine` (Web Audio).** Smoke-tested in Node 24 with a mock AudioContext:

- "our attack" → swell 0.73, chant 0.20
- "under pressure" → murmur 0.29, tense 0.29, away 0.25, chant 0
- the roar refractory rejected a repeat 1 s later
- duck → 0.35 gain and −6 dB at 2 kHz.

This first test caught a scheduler catch-up burst after a stall, which is now fixed. Not yet heard in a browser.

```ts
export interface CrowdState { excitement: number; valence: number; danger: number } // 0..1, -1..1, -1..1 (+ = we attack)
export interface CrowdBuffers { murmur: AudioBuffer; swell: AudioBuffer; tense: AudioBuffer; away: AudioBuffer;
  vowel: AudioBuffer; shots: Record<string, AudioBuffer[]> }  // shots: roar, ooh_groan, whistles_jeer, applause, ...
interface Bed { gain: GainNode; lp: BiquadFilterNode; pan: StereoPannerNode }
const clamp = (x: number, a = 0, b = 1) => Math.min(b, Math.max(a, x));

export class CrowdEngine {
  readonly ctx: AudioContext; private buf: CrowdBuffers; private beds = new Map<string, Bed>();
  private crowdBus: GainNode; private duckGain: GainNode; private speechDip: BiquadFilterNode;
  private master: GainNode; private chantGain: GainNode; private lastShot = new Map<string, number>();
  private state: CrowdState = { excitement: 0.2, valence: 0, danger: 0 };
  private timer: ReturnType<typeof setInterval> | null = null;
  private nextGrain = 0; private nextBeat = 0; private beat = 0; private motif: number[]; private noise?: AudioBuffer;
  homePan: number;

  constructor(ctx: AudioContext, buffers: CrowdBuffers, opts: { homePan?: number; clubSeed?: number } = {}) {
    this.ctx = ctx; this.buf = buffers; this.homePan = opts.homePan ?? 0;
    this.master = ctx.createGain(); this.master.gain.value = 0.8;
    const limiter = ctx.createDynamicsCompressor();                     // headphone safety limiter
    limiter.threshold.value = -6; limiter.ratio.value = 20; limiter.attack.value = 0.003; limiter.release.value = 0.25;
    this.speechDip = ctx.createBiquadFilter(); this.speechDip.type = "peaking";
    this.speechDip.frequency.value = 2000; this.speechDip.Q.value = 0.8; this.speechDip.gain.value = 0;
    this.duckGain = ctx.createGain(); this.crowdBus = ctx.createGain();
    this.crowdBus.connect(this.duckGain).connect(this.speechDip).connect(this.master).connect(limiter).connect(ctx.destination);
    this.chantGain = ctx.createGain(); this.chantGain.gain.value = 0; this.chantGain.connect(this.crowdBus);
    for (const [n, p] of [["murmur", this.homePan], ["swell", this.homePan], ["tense", this.homePan], ["away", -this.homePan * 0.8]] as const)
      this.beds.set(n, this.makeBed(p));
    this.motif = CrowdEngine.makeMotif(opts.clubSeed ?? 7);
  }

  /** Our own 8-step pentatonic motif, seeded per synthetic club (no real songs). -1 = rest. */
  static makeMotif(seed: number): number[] {
    const scale = [0, 2, 4, 7, 9, 12]; let s = seed >>> 0; const out: number[] = [];
    for (let i = 0; i < 8; i++) { s = (s * 1664525 + 1013904223) >>> 0; out.push(i % 4 === 3 ? -1 : scale[s % scale.length]); }
    return out;
  }
  private makeBed(panValue: number): Bed {
    const gain = this.ctx.createGain(); gain.gain.value = 0;
    const lp = this.ctx.createBiquadFilter(); lp.type = "lowpass"; lp.frequency.value = 1200;
    const pan = this.ctx.createStereoPanner(); pan.pan.value = panValue;
    lp.connect(gain).connect(pan).connect(this.crowdBus); return { gain, lp, pan };
  }
  start(): void {
    const t = this.ctx.currentTime;
    for (const n of ["swell", "tense", "away"] as const) {
      const src = this.ctx.createBufferSource(); src.buffer = this.buf[n]; src.loop = true;
      src.connect(this.beds.get(n)!.lp); src.start(t, Math.random() * this.buf[n].duration);
    }
    this.nextGrain = t; this.nextBeat = t;
    this.timer = setInterval(() => this.schedule(), 25);                // "two clocks": 25 ms timer, 100 ms ahead
    this.setState(this.state, 0.5);
  }
  stop(): void { if (this.timer) clearInterval(this.timer); this.timer = null; this.master.gain.setTargetAtTime(0, this.ctx.currentTime, 0.3); }

  /** Crossfade every layer toward the new state; rises faster than falls. */
  setState(s: CrowdState, tc = 0.6): void {
    const e = clamp(s.excitement), v = clamp(s.valence, -1, 1), d = clamp(s.danger, -1, 1);
    const ours = Math.max(d, 0), theirs = Math.max(-d, 0), now = this.ctx.currentTime;
    const go = (p: AudioParam, target: number) => {
      const rising = target > p.value;
      p.cancelScheduledValues(now); p.setValueAtTime(p.value, now);
      p.setTargetAtTime(target, now, rising ? tc * 0.5 : tc * 2);
    };
    const m = this.beds.get("murmur")!, sw = this.beds.get("swell")!, te = this.beds.get("tense")!, aw = this.beds.get("away")!;
    go(m.gain.gain, (0.25 + 0.35 * e) * (1 - 0.45 * theirs));          // home end goes quiet under pressure
    go(m.lp.frequency, 700 + 4500 * e);                                 // bigger crowd = brighter
    go(sw.gain.gain, Math.pow(ours, 1.5) * (0.3 + 0.7 * e));            // rising "ooh" on our dangerous attacks
    go(sw.lp.frequency, 900 + 6000 * ours);
    go(te.gain.gain, 0.45 * theirs * (0.5 + 0.5 * e)); go(te.lp.frequency, 500 + 600 * e);
    go(aw.gain.gain, 0.08 + 0.35 * theirs * e); go(aw.lp.frequency, 1400); // the other end, distant
    go(this.chantGain.gain, 0.5 * clamp((e - 0.3) / 0.5) * Math.max(v, 0) * (1 - theirs)); // sing when happy and safe
    this.state = { excitement: e, valence: v, danger: d };
  }

  /** One-shot (roar, ooh_groan, whistles_jeer, applause...). `when` = exact event time from the cue's tc_in. */
  trigger(name: string, when = this.ctx.currentTime, intensity = 1, refractoryS = 4): void {
    const variants = this.buf.shots[name]; if (!variants?.length) return;
    if (when - (this.lastShot.get(name) ?? -Infinity) < refractoryS) return; // anti-fatigue
    this.lastShot.set(name, when);
    const src = this.ctx.createBufferSource(); src.buffer = variants[Math.floor(Math.random() * variants.length)];
    src.playbackRate.value = 0.94 + Math.random() * 0.12;               // variation, not identical repeats
    const g = this.ctx.createGain(), p = this.ctx.createStereoPanner(); p.pan.value = this.homePan;
    g.gain.setValueAtTime(0, when); g.gain.linearRampToValueAtTime(clamp(intensity) * (0.8 + Math.random() * 0.2), when + 0.08);
    src.connect(g).connect(p).connect(this.crowdBus); src.start(when);
    if (name === "roar") this.chantGain.gain.setTargetAtTime(0, when, 0.2);
  }

  /** Duck under commentary / the fan's own question: level dip + 2 kHz speech-band cut. */
  duck(speaking: boolean, depth = 0.35): void {
    const t = this.ctx.currentTime;
    this.duckGain.gain.setTargetAtTime(speaking ? depth : 1, t, speaking ? 0.08 : 0.5);
    this.speechDip.gain.setTargetAtTime(speaking ? -6 : 0, t, speaking ? 0.08 : 0.5);
  }

  private schedule(): void {
    const now = this.ctx.currentTime, ahead = now + 0.1, e = this.state.excitement;
    if (this.nextGrain < now) this.nextGrain = now;                     // after a stalled tab: skip, never burst
    if (this.nextBeat < now) this.nextBeat = now;
    const density = 6 + 30 * e;                                          // murmur grains per second
    while (this.nextGrain < ahead) { this.grain(this.nextGrain, 0.08 + 0.12 * Math.random()); this.nextGrain += (0.5 + Math.random()) / density; }
    const beatS = 60 / (96 + 20 * e) / 2;                                // eighth notes
    while (this.nextBeat < ahead) {
      const step = this.motif[this.beat % this.motif.length];
      if (step >= 0 && this.chantGain.gain.value > 0.02) this.chantNote(step, this.nextBeat, beatS * 0.9);
      if (this.beat % 2 === 0 && this.state.valence > 0.3 && e > 0.35) this.clap(this.nextBeat, 0.4 * e);
      this.beat++; this.nextBeat += beatS;
    }
  }
  private grain(when: number, len: number): void {
    const b = this.buf.murmur, src = this.ctx.createBufferSource(); src.buffer = b;
    src.playbackRate.value = 0.97 + 0.06 * this.state.excitement;
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(0, when); g.gain.linearRampToValueAtTime(0.5, when + len / 2); g.gain.linearRampToValueAtTime(0, when + len);
    src.connect(g).connect(this.beds.get("murmur")!.lp); src.start(when, Math.random() * Math.max(0, b.duration - len), len);
  }
  private chantNote(semitones: number, when: number, dur: number): void {
    for (let voice = 0; voice < 3; voice++) {                            // 3 detuned copies = many voices
      const src = this.ctx.createBufferSource(); src.buffer = this.buf.vowel;
      src.playbackRate.value = Math.pow(2, semitones / 12); src.detune.value = (voice - 1) * 15 + (Math.random() - 0.5) * 10;
      const g = this.ctx.createGain();
      g.gain.setValueAtTime(0, when); g.gain.linearRampToValueAtTime(0.3, when + 0.04); g.gain.setTargetAtTime(0, when + dur * 0.7, 0.05);
      src.connect(g).connect(this.chantGain); src.start(when + voice * 0.012, 0.2, dur + 0.2);
    }
  }
  /** Procedural clap ensemble: band-passed noise bursts with exponential decay (after Lee & Reiss 2020). */
  private clap(when: number, level: number): void {
    if (!this.noise) { const n = this.ctx.createBuffer(1, this.ctx.sampleRate * 0.2, this.ctx.sampleRate);
      const d = n.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1; this.noise = n; }
    for (let k = 0; k < 12; k++) {                                       // 12 clappers, slightly early/late
      const t = when + (Math.random() - 0.5) * 0.04, src = this.ctx.createBufferSource(); src.buffer = this.noise;
      const bp = this.ctx.createBiquadFilter(); bp.type = "bandpass"; bp.frequency.value = 900 + Math.random() * 1500; bp.Q.value = 1.2;
      const g = this.ctx.createGain(); g.gain.setValueAtTime(level / 4, t); g.gain.setTargetAtTime(0, t + 0.002, 0.012);
      const p = this.ctx.createStereoPanner(); p.pan.value = clamp(this.homePan + (Math.random() - 0.5) * 0.6, -1, 1);
      src.connect(bp).connect(g).connect(p).connect(this.chantGain); src.start(t, Math.random() * 0.1, 0.06);
    }
  }
}
```

**Wiring (client).**
- On each crowd cue: `eng.setState(cue.payload)`.
- On one-shot cues: `eng.trigger(cue.one_shot, clock.toCtxTime(cue.tc_in))`, using the file-24 clock mapping.
- When commentary or Voice Live audio starts and ends: `eng.duck(true/false)`.
- Call `ctx.resume()` from a user gesture (browser autoplay rule).

Links:
- granular browser sampler: https://github.com/Kenneth-Rakentine/Grains
- Web Audio scheduling: https://web.dev/articles/audio-scheduling
- `start(when, offset, duration)`: https://developer.mozilla.org/en-US/docs/Web/API/AudioBufferSourceNode/start

## Sources

- AP via WSLS, "EA Sports in the game with Premier League and La Liga" (11 Jun 2020) — https://www.wsls.com/sports/2020/06/12/ea-sports-in-the-game-with-premier-league-and-la-liga/ — accessed 20 Oct 2026
- Deseret News, Premier League to use FIFA/EA Sports crowd sounds (8 Jun 2020) — https://www.deseret.com/sports/2020/6/8/21283895/premier-league-fifa-ea-sports-sounds — accessed 20 Oct 2026 (via search summary)
- Inside Sport, "Sky Sports boosts Premier League experience with artificial crowd noises" — https://insidersport.com/2020/06/08/sky-sports-boosts-premier-league-experience-with-artificial-crowd-noises/ — accessed 20 Oct 2026 (403; facts via search summary)
- Sound Particles blog, "How Paul Boechler Created Live Stadium Crowds From FIFA Recordings" — https://blog.soundparticles.com/how-paul-boechler-created-live-stadium-crowds-from-fifa-recordings — accessed 20 Oct 2026
- ESPN, Tom Hamilton, Bundesliga crowd-noise feed (29 May 2020) — https://global.espn.com/football/story/_/id/37583797/where-crowd-noise-feed-comes-how-made-it — accessed 20 Oct 2026
- Audiokinetic, Planet Coaster crowd audio part 3 — https://audiokinetic.com/en/planet-coaster-crowd-audio-additional-layers-part-3 — accessed 20 Oct 2026 (403; search summary only)
- Nevill, Balmer & Williams (2002), Psychology of Sport & Exercise 3(4) — https://wlv.openrepository.com/items/2a37e72f-d492-4e51-aaec-76f45dcba34f — accessed 20 Oct 2026
- Leitner & Richlan (2021), "No Fans–No Pressure", Frontiers in Sports and Active Living 3:720488 — https://pmc.ncbi.nlm.nih.gov/articles/PMC8416626/ — accessed 20 Oct 2026
- Dilger & Vischer, "No Home Bias in Ghost Games" — https://papers.ssrn.com/abstract=3674876 — accessed 20 Oct 2026 (via search summary)
- "Home-Bias in Referee Decisions: Evidence from 'Ghost Matches'", Economics Letters 2020 (data, Gesche) — https://data.mendeley.com/datasets/hv8777dn5m — accessed 20 Oct 2026 (via search summary)
- Russell (1980), "A Circumplex Model of Affect", JPSP 39(6) — https://pdodds.w3.uvm.edu/research/papers/others/1980/russell1980a.pdf — accessed 20 Oct 2026
- Franzoni et al., Emotional Crowd Sound dataset — https://ieee-dataport.org/open-access/emotional-crowd-sound ; follow-up arXiv 2509.16329 — https://arxiv.org/abs/2509.16329 — accessed 20 Oct 2026 (via search summary)
- Lee & Reiss (2020), procedural applause model, AES e-library — https://aes.org/publications/elibrary-page/?id=20732 — accessed 20 Oct 2026 (abstract via search; page 403)
- Related works on acoustic audience feedback (granular synthesis, grain 10–200 ms) — https://hackernoon.com/related-works-on-acoustic-audience-feedback-in-large-virtual-events — accessed 20 Oct 2026 (via search summary)
- Shah, Agrawal & Pedanekar (2021), "Adding Crowd Noise to Sports Commentary using Generative Models", LIQUE — https://sol.sbc.org.br/index.php/lique/article/view/15715 — accessed 20 Oct 2026
- Freesound sound/pack pages: 829456 & pack 44412 (Sound Of Sankt Pauli), 612131 (felix.blume), 651646 & pack 36296 (Krizin), 764324 & pack 42102 (ShangusBurger GSC24), 870651 & pack 46348 (CHallSmith); CC0 search results — https://freesound.org/search/?q=football+crowd&f=license%3A%22Creative+Commons+0%22 — accessed 20 Oct 2026
- BBC Sound Effects RemArc licence coverage (MusicTech) — https://musictech.com/news/music/the-bbc-sound-effects-archive-over-33000-free-samples — accessed 20 Oct 2026 (licence page https://sound-effects.bbcrewind.co.uk/licensing could not be fetched)
- Managing IP, "Football's coming home: IP rights…" (9 Jul 2021) — https://www.managingip.com/article/2a5czh91g6c8zww2yd43k/footballs-coming-home-ip-rights-germans-and-that-final — accessed 20 Oct 2026
- GGI, Dorneanu, "Roaring fans and copyright laws" (2024) — https://www.ggi.com/news/general-interest/roaring-fans-and-copyright-laws-from-melodies-to-anthems-the-legal-pitch-of-football-chants — accessed 20 Oct 2026
- JSLHR (2026), dialogue-to-background ratio study — https://pubs.asha.org/doi/10.1044/2026_JSLHR-25-00127 — accessed 20 Oct 2026 (403; abstract via search)
- AES TD1008 summaries — https://productionadvice.co.uk/td1008/ and https://docs.telosalliance.com/docs/understanding-loudness-for-streaming-audio — accessed 20 Oct 2026
- WHO-ITU H.870, Safe listening devices and systems — https://www.who.int/publications/i/item/9789241515276 — accessed 20 Oct 2026 (via search summary)
- MDN, AudioBufferSourceNode.start() — https://developer.mozilla.org/en-US/docs/Web/API/AudioBufferSourceNode/start — accessed 20 Oct 2026
- Chris Wilson, "A tale of two clocks" — https://web.dev/articles/audio-scheduling — accessed 20 Oct 2026
- Kenneth-Rakentine/Grains (Web Audio granular sampler) — https://github.com/Kenneth-Rakentine/Grains — accessed 20 Oct 2026 (via search summary)
