# 39 — A commentator who knows what's coming: look-ahead, tension build-up and emotional voice

_Accessed/compiled: 20 Oct 2026 · Priority area: Tely (Explain → Render audio), voice, timing_

## TL;DR

- **Run the commentator a fixed delay behind a "truth buffer".** It plans lines with up to N seconds of look-ahead, so it can start the rise *before* the shot. On a real live match this is just a broadcast delay. Over-the-air TV is already about 11-12 s behind the pitch, and streams 26-78 s (Comcast and Phenix, Super Bowl 2025). Say this openly: "your audio runs 10 s behind the pitch, like TV". Do not call it prediction.
- **Drive voice intensity from suspense and surprise, not from the outcome.** Ely, Frankel & Kamenica (2015) define suspense as the spread of *next-period* beliefs and surprise as how far the belief just moved. Buraimo et al. (2020) applied both to minute-by-minute Premier League TV audiences, using win probability over home/draw/away. Over 47,520 minute-observations, suspense, surprise and "shock" all raised audience size. We compute all three from the file 23 win-probability model; the code is below.
- **Anti-spoiler rule: foreshadow on *danger*, never on the outcome.** Ely et al. show that if a channel only shows the comebacks, the comebacks stop being surprising. In the same way, a build-up that fires only before goals *is* a spoiler. Build-ups therefore fire the same way for saves and misses. The look-ahead may only shift timing and add a capped bonus (≤35% of intensity, our guess).
- **Copy real commentators' prosody, within Azure's limits.**
  - Building suspense: pitch rises across phrases, the range within a phrase stays narrow, and there are no pauses (Kern 2010). Articulation speeds up from 4.2 to 4.64 syllables/s in attacks (Sivachenko 2021).
  - The climax: speech *slows*, the key syllable stretches, and pitch jumps to roughly 2-3× narrative F0. Measured values are 337-484 Hz against 109-257 Hz (Trouvain 2011).
  - Azure prosody is capped at 0.5-1.5× pitch. **DragonHD voices don't support `<prosody>` at all**, so English peaks come from style markers (`[shouting]`, `[excited]`), wording and the crowd bed.
- **Pre-synthesise every planned line during the look-ahead.** The HD voice doc says latency is "less than 300 ms", so a 10 s delay leaves plenty of slack. The real latency risk is LLM polish: the DFL ticker takes 7-12 s (file 22). So event calls stay templated, and the LLM is used only for colour lines that are allowed to go stale.

## Findings

### 1. Suspense, surprise and shock: definitions we can compute

| Measure | Definition | Source | Our computation |
|---|---|---|---|
| Suspense at t | sqrt(E_t ‖μ_{t+1} − μ_t‖²), the std-dev of next beliefs | Ely et al. 2015, baseline spec | Three branches for the next tick: home goal, away goal, no goal. Each is re-scored with the file 23 Poisson grid and weighted by P(goal in the tick). Buraimo et al. use the same "score in the next minute" branches. They note that betting odds can't give suspense, because the branches are hypothetical. |
| Surprise at t | ‖μ_t − μ_{t−1}‖ (Euclidean over H/D/A) | Ely et al.; Buraimo et al. eq. 1 | Spikes on goals and red cards. This is the trigger for the "goal call". |
| Shock at t | ‖μ_t − μ_0‖ vs pre-match | Buraimo et al. eq. 2 | Slow "upset brewing" signal. Buraimo found it mattered **only in the second half**. |

- **Soccer is a suspense sport.** Ely et al. describe soccer belief paths as smooth with rare large jumps, which makes the game "very suspenseful". Basketball, with many small jumps, is a surprise game. For us this means long, quiet stretches punctuated by sharp rises, so the voice should spend most of the time calm.
- **Effect size is real but small.** In Buraimo et al., a 1 SD rise in both suspense and surprise predicts about **+1.2%** audience. In a simulated pair of matches, the 3-3 game kept 12,904 more viewers per minute than the 0-0 one over the last 20 minutes, even though their suspense values were identical. They also cite Mutz & Wahnschaffe: in the last 15 minutes, each extra goal of margin cost **8.5%** of viewers.
- **Minute-level suspense is too coarse for a voice.** Inside one attack, the WP-based suspense hardly moves unless P(goal in the next second) moves. So we feed the branch weights from **live danger** (xT/xG of the current possession, files 07/08) rather than from the flat goal hazard. In our toy run, suspense rises from 0.02 at rest to 0.66 one second before a 0.3-xG shot. At the goal, surprise reads 0.92 and suspense collapses. Run it yourself; the numbers are illustrative only.

### 2. What commentary research says about timing and voice

| Finding | Source |
|---|---|
| Two dramatic styles. **Building suspense:** continuous F0 rise across units, narrow pitch range within units, no pauses within or between units. **Presenting a climax:** marked slowing of articulation and extremely lengthened nuclear syllables. | Kern 2010 (abstract) |
| In the 10 s after a goal, the mean F0 of the first phrase is 337-393 Hz for male commentators, against 109-172 Hz narrative (female: 484 vs 257). Maxima exceed 400 Hz. Some speakers hold the "Tor" vowel for up to 3 s. | Trouvain 2011, Tables 1, 3 |
| **Radio talks more than TV** in the 10 s after a goal: 4.6 vs 2.3 inter-pause stretches, 25 vs 20 syllables, 7.7 vs 4.96 s of articulation. After goals against their team, two of three TV commentators began with several seconds of silence. | Trouvain 2011, Table 2 |
| Articulation is 4.2 syll/s in narrative and 4.64 in a goal attack. Commentators slow down at the scoring chance itself, whatever the outcome. Tempo falls in the 10 s after a goal. | Sivachenko 2021 (abstract) |
| Speaking rate in words per minute (NFL, first 15 minutes of each Week 1 game): play-by-play 55.4-120.9, booth pairs averaging 158.4. These are American-football figures and only a rough guide. | WSJ "The Count" via Awful Announcing 2011 |
| Text-commentary datasets are badly timed. SoccerNet-Caption has about 37k commentaries over 715.9 h of video. MatchTime hand-checked 49 matches: mean absolute offset **16.6 s**, mean signed offset +13.9 s (commentary lags), and only 26% within ±10 s. After automatic alignment, 81% are within ±10 s. A 30 s context window worked best for generation. | Mkhallati 2023; Rao et al. 2024 |

**What this means for us:** learned video-to-commentary models are tuned to roughly 10 s accuracy, not to the sub-second timing a goal call needs. Our timing comes from our own event clock, which is exact because the match is synthetic. Use those papers for phrasing ideas, not for timing.

### 3. Describing for blind listeners (36 is in progress)

- **Follow the ball, not the player.** Divide the pitch into thirds (defence, midfield, attack), say near or far, name the end being attacked, and place shots by direction and height (Bohemians FC audio-descriptive-commentary (ADC) volunteers, Moorkens & Pintado Gutiérrez 2026). FIFA's ADC service also centres on where the ball is.
- **Description beats chit-chat.** The guidance is to describe on-pitch action, not statistics or tactics (CAFE via EFDN). In RNIB's focus group (4 severely sight-impaired fans), participants found radio more detailed than TV and wanted VAR decisions described.
- **Rule for us:** silence is fine when the crowd mix (Home End) carries the meaning, for example the 3 s roar after our team scores. But never leave more than about 20 s without spoken state (ball zone, score, clock), and always say the score and clock after a goal. Both numbers are our guesses. This is "radio style", not TV style.

### 4. Azure voice capabilities that matter here (correction to file 27)

| Voice family | Prosody | Styles | Pauses | Use |
|---|---|---|---|---|
| **DragonHD** (`en-US-Andrew:DragonHDLatestNeural` etc.) | **No** `<prosody>` | `[style]` markers. `express-as` is "No" in the HD support table, but the SSML page shows it working, so test both. | `<break>` yes, `mstts:silence` no | EN main voice. Intensity comes from style + words + `temperature` (0-1). |
| **DragonHD Omni** (`…:DragonHDOmniLatestNeural`, 700+ voices) | No | `express-as` yes. Styles only for English content. | `<break>` no | EN alternative. `cfg_scale` 1.0-2.0 changes speed. Word-boundary events are available for timing. |
| **Standard neural** (`bg-BG-BorislavNeural`, `bg-BG-KalinaNeural`) | **Yes.** Pitch 0.5-1.5×, rate 0.5-2×, volume. | None for BG (file 27) | `<break>` 0-20,000 ms, `mstts:silence` | **Bulgarian**, and any EN mode that needs fine prosody |

- **Correction to file 27.** The HD-voice page (updated 24 Sep 2026) lists **only en-US** English DragonHD voices; `en-GB-Ollie`/`en-GB-Ryan` are not in the DragonHD table. An en-GB HD voice probably exists only as `…:DragonHDOmniLatestNeural` (unverified). The file 27 example that puts `<prosody>` inside an HD voice is ignored per the support table.
- Style markers carry on until `[Neutral]`, `<p>` or a sentence boundary. So **put one sentence in each SSML document** and set the style per line.
- Styles also work in **plain text** ("[excited] …"). That may let the SSML-less text-streaming websocket keep styles for live Q&A answers (unverified, worth a 10-minute test).

## So what for us

**Tely. Stages: Interpret (tension) → Explain (script planner) → Render (TTS + timed audio) → Personalise (language, club, verbosity).**

1. **Architecture.**
   - The generator writes to a **truth buffer**. The listener's playhead runs at `t_true − D`, with **D = 10 s** (our pick; OTA TV is about 11.5 s).
   - The planner sees events in `[playhead, playhead + D]` and emits timed lines, each pre-synthesised and cached by an SSML hash.
   - The crowd engine (Home End) and haptics (Heartbeat) read the **same tension curve**, so voice, crowd swell and pulse rise together.
   - Templated calls (goal, save, shot) are instant. LLM colour lines need roughly 7-12 s of polish and get a `stale_s`, so they are dropped if late.
2. **Reveal policy.**
   - Build-up intensity = 65% observable suspense (danger-weighted) + up to 35% look-ahead ramp. The ramp is weighted by pre-shot xG, never by outcome.
   - The ramp starts `LEAD_S = 4 s` before a shot. Our guess from the 2-5 s window: tune it by measuring the time from the first rise in danger to the shot in our generator logs.
   - Audit the policy with "spoiler lift": P(goal | build line fired) should match the mean xG of those chances. Show this number to judges.
3. **Talk-back (Voice Live, file 27).** The Q&A agent's tools may read **only events up to the playhead**, never the truth buffer, or a question could leak the future. One unique advantage: the planner *knows* a goal is due in 3 s, so it delays or trims a long answer so it doesn't talk over the call.
4. **Voice.** EN uses DragonHD with style bands calm → curious → urgent → excited → shouting. Lower `temperature` keeps one consistent "commentator". BG uses Borislav with prosody: build-up +10% rate and rising pitch with no breaks; call −25% rate, +45% pitch, then a 3 s crowd hold.
5. **Other ideas.** **21 Called It** reuses suspense as its "big moment" flag. **F Graphics Desk** gets a tension sparkline. **C One Number** can be "tension" itself. **23 Safe Break** can pick ad breaks at low-suspense minutes.

## Reuse: code & links

**Suspense / surprise / shock from a WP series** (numpy; tested on a toy 80:00-82:00 sequence):

```python
import math, numpy as np
def pois(k, mu): return math.exp(-mu) * mu**k / math.factorial(k)
def wp(gd, mu_h, mu_a, kmax=10):                     # file 23 Poisson grid -> [H, D, A]
    out = np.zeros(3)
    for x in range(kmax):
        for y in range(kmax):
            d = gd + x - y; out[0 if d > 0 else 1 if d == 0 else 2] += pois(x, mu_h) * pois(y, mu_a)
    return out / out.sum()

def suspense_surprise(times_s, gd, r_h, r_a, p_goal_h, p_goal_a, end_s=95*60):
    """r_*: goals/s. p_goal_*: P(score before next tick) from live danger (xT/xG) or r*dt."""
    n = len(times_s); mu = np.zeros((n, 3)); susp = np.zeros(n)
    for i, t in enumerate(times_s):
        m_h, m_a = r_h * max(end_s - t, 0), r_a * max(end_s - t, 0)
        mu[i] = wp(gd[i], m_h, m_a)
        b_h, b_a = wp(gd[i] + 1, m_h, m_a), wp(gd[i] - 1, m_h, m_a)
        ph, pa = p_goal_h[i], p_goal_a[i]; p0 = 1 - ph - pa
        b_0 = (mu[i] - ph * b_h - pa * b_a) / max(p0, 1e-9)   # "nothing happens" branch (martingale)
        susp[i] = math.sqrt(ph*np.sum((b_h-mu[i])**2) + pa*np.sum((b_a-mu[i])**2) + p0*np.sum((b_0-mu[i])**2))
    surprise = np.r_[0, np.linalg.norm(np.diff(mu, axis=0), axis=1)]
    shock = np.linalg.norm(mu - mu[0], axis=1)
    return mu, susp, surprise, shock

def tension_curve(times_s, susp, lookahead, lead_s=4.0, tail_s=6.0, w_look=0.35, ref_p99=None):
    """lookahead: [(t_shot, weight_from_pre_shot_xG)] -- never weight by outcome (anti-spoiler).
    ref_p99: 99th pct of suspense over ~500 generated matches (normalise globally, not per window)."""
    s = np.clip(susp / (ref_p99 or np.percentile(susp, 99)), 0, 1); look = np.zeros_like(s)
    for te, w in lookahead:
        up = (times_s >= te - lead_s) & (times_s < te)
        look[up] = np.maximum(look[up], w * (times_s[up] - te + lead_s) / lead_s)
        dn = (times_s >= te) & (times_s < te + tail_s)
        look[dn] = np.maximum(look[dn], w * (1 - (times_s[dn] - te) / tail_s))
    return np.clip((1 - w_look) * s + w_look * look, 0, 1)
# voice intensity at t = max(tension[t], min(1, surprise[t] / 0.3))   # 0.3 = our guess
```

**Look-ahead planner** (priority placement + stale drop + quiet fill; tested on toy events. Output: `describe 4860.0 → build 4862.0 → GOAL! 4866.2 → detail 4870.2 → state lines every ~20 s → build 4926.0 → Saved! 4930.2`):

```python
import heapq
from dataclasses import dataclass, field
WPS, LEAD_S, CROWD_HOLD_S, MAX_QUIET_S, MIN_GAP_S = 2.6, 4.0, 3.0, 20.0, 0.4   # all our guesses

@dataclass(order=True)
class Line:
    prio: int; t_start: float
    kind: str = field(compare=False); text: str = field(compare=False)
    intensity: float = field(compare=False); style: str = field(compare=False, default="")
    stale_s: float = field(compare=False, default=3.0); evidence: tuple = field(compare=False, default=())

def zone(x, y, attacking_right=True):                 # 105x68 m pitch, attacker's view (Bohemians ADC)
    if not attacking_right: x, y = 105 - x, 68 - y
    third = "own half" if x < 35 else "midfield" if x < 70 else "final third"
    side = "left" if y > 45 else "right" if y < 23 else "centre"
    return f"{side} side, {third}" if side != "centre" else f"through the middle, {third}"

def plan(events, tension_at, quiet_fill):
    q = []
    for e in events:
        where = zone(e["x"], e["y"], e.get("attacking_right", True))
        if e["type"] == "shot":
            if e["xg"] >= 0.08:                       # danger-based: same for goal / save / miss
                heapq.heappush(q, Line(2, e["t"] - LEAD_S, "build", f"{e['team']} breaking, {where}... {e['player']}!",
                                       max(tension_at(e["t"] - LEAD_S), 0.5), stale_s=1.5, evidence=(e["id"],)))
            if e["outcome"] == "goal":
                heapq.heappush(q, Line(0, e["t"] + 0.2, "call", "GOAL!", 1.0, "shouting", 0.5, (e["id"],)))
                heapq.heappush(q, Line(1, e["t"] + 1.2 + CROWD_HOLD_S, "detail",
                                       f"{e['player']} scores. {e['score']}, {e['clock']}.", 0.7, "excited", 8, (e["id"],)))
            else:
                word = {"saved": "Saved!", "off_target": "Wide!", "blocked": "Blocked!"}[e["outcome"]]
                heapq.heappush(q, Line(1, e["t"] + 0.2, "react", word, 0.8, "excited", 1.0, (e["id"],)))
        elif e["type"] in ("pass", "carry") and e.get("xt_gain", 0) > 0.03:
            heapq.heappush(q, Line(3, e["t"], "describe", f"{e['player']}, {where}.", tension_at(e["t"]), stale_s=2.0,
                                   evidence=(e["id"],)))
    placed = []
    free = lambda a, b: all(b + MIN_GAP_S <= s or a >= en + MIN_GAP_S for s, en, _ in placed)
    while q:                                          # highest priority claims its slot first
        ln = heapq.heappop(q); dur = len(ln.text.split()) / (WPS * (1 + 0.15 * ln.intensity))
        for k in range(int(ln.stale_s / 0.1) + 1):    # slide later in 100 ms steps, else drop as stale
            a = ln.t_start + 0.1 * k
            if free(a, a + dur): ln.t_start = round(a, 2); placed.append((a, a + dur, ln)); break
    placed.sort(key=lambda p: p[0]); out, last = [], (events[0]["t"] if events else 0.0)
    for s, en, ln in placed:
        while s - last > MAX_QUIET_S:                 # blind listener: never > 20 s without state
            t = last + MAX_QUIET_S; txt = quiet_fill(t)
            out.append(Line(4, round(t, 2), "state", txt, tension_at(t))); last = t + len(txt.split()) / WPS
        out.append(ln); last = max(last, en)
    return out
```

**SSML builders.** EN DragonHD: style markers only. EN Omni: express-as + cfg_scale. BG: prosody.

```python
from xml.sax.saxutils import escape
NS = 'version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="http://www.w3.org/2001/mstts"'
band = lambda i: "calm" if i < .25 else "curious" if i < .5 else "urgent" if i < .75 else "excited"

def ssml_en_dragonhd(ln, voice="en-US-Andrew:DragonHDLatestNeural", temperature=0.6):
    body = f"[{ln.style or band(ln.intensity)}] {escape(ln.text)}" + ('<break time="300ms"/>' if ln.kind == "call" else "")
    return f'<speak {NS} xml:lang="en-US"><voice name="{voice}" parameters="temperature={temperature}">{body}</voice></speak>'

def ssml_en_omni(ln, voice="en-US-Andrew:DragonHDOmniLatestNeural"):
    return (f'<speak {NS} xml:lang="en-US"><voice name="{voice}" parameters="cfg_scale={1.2 + 0.6*ln.intensity:.2f}">'
            f'<mstts:express-as style="{ln.style or band(ln.intensity)}">{escape(ln.text)}</mstts:express-as></voice></speak>')

def ssml_bg(ln, text_bg, voice="bg-BG-BorislavNeural"):
    i = ln.intensity
    if ln.kind == "call":   # climax: slower, stretched, high (Kern; Trouvain); +45% sits under Azure's 1.5x cap
        inner = f'<prosody rate="-25%" pitch="+45%" volume="+40%">{escape(text_bg)}</prosody><break time="300ms"/>'
    else:                   # build-up: faster, rising, no pauses (Kern; Sivachenko +10% syll/s)
        inner = f'<prosody rate="+{round(12*i)}%" pitch="+{round(20*i)}%" volume="+{round(25*i)}%">{escape(text_bg)}</prosody>'
    return (f'<speak {NS} xml:lang="bg-BG"><voice name="{voice}">'
            f'<mstts:silence type="Sentenceboundary-exact" value="150ms"/>{inner}</voice></speak>')
```

**Pre-synthesis cache** (Speech SDK; untested here, no key used). Reuse one synthesizer and use MP3 output, as in file 27. Put `duration` into the cue `speech` block and re-plan with real durations instead of `WPS`.

```python
import hashlib, azure.cognitiveservices.speech as sdk
cfg = sdk.SpeechConfig(subscription=KEY, region=REGION)
cfg.set_speech_synthesis_output_format(sdk.SpeechSynthesisOutputFormat.Audio24Khz48KBitRateMonoMp3)
synth = sdk.SpeechSynthesizer(speech_config=cfg, audio_config=None)
cache = {}
def presynth(ssml):
    key = hashlib.sha256(ssml.encode()).hexdigest()
    if key not in cache:
        r = synth.speak_ssml_async(ssml).get()
        if r.reason == sdk.ResultReason.SynthesizingAudioCompleted:
            cache[key] = {"audio": r.audio_data, "duration_s": r.audio_duration.total_seconds()}
    return key
```

Links:
- SoccerNet-Caption: https://github.com/SoccerNet
- MatchTime: https://arxiv.org/abs/2406.18530
- GOAL benchmark (8.9k clips, 22k sentences, 42k knowledge triples): https://github.com/THU-KEG/goal

## Sources

- Ely, Frankel & Kamenica, "Suspense and Surprise", JPE 123(1) 2015 (author PDF) — https://www.wiwi.uni-bonn.de/kraehmer/Lehre/TopicsSS14/ElyEtAl-SurpriseSuspense.pdf — accessed 20 Oct 2026
- Buraimo, Forrest, McHale & Tena, "Unscripted drama: soccer audience response to suspense, surprise and shock", Economic Inquiry 58(2) 2020 (AAM) — https://livrepository.liverpool.ac.uk/3063874/6/paper.pdf — accessed 20 Oct 2026
- Trouvain, "Between excitement and triumph – live football commentaries in radio vs. TV", ICPhS 2011 — https://www.coli.uni-saarland.de/~trouvain/trouvain_football_2011.pdf — accessed 20 Oct 2026
- Kern, "Speaking dramatically: the prosody in radio live commentaries of football games", in Prosody in Interaction 2010 (abstract) — https://pub.uni-bielefeld.de/record/2704369 — accessed 20 Oct 2026
- Sivachenko, "The influence of prosody on the effectiveness of sports commentators' speech", 2021 (abstract) — http://dspace.uzhnu.edu.ua/handle/lib/60874 — accessed 20 Oct 2026
- "The Count" NFL words-per-minute (via Awful Announcing, 2011) — https://awfulannouncing.com/?p=6729 — accessed 20 Oct 2026
- Mkhallati et al., SoccerNet-Caption, CVPRW 2023 — https://arxiv.org/abs/2304.04565 — accessed 20 Oct 2026
- Rao et al., MatchTime: Towards Automatic Soccer Game Commentary Generation, EMNLP 2024 — https://arxiv.org/html/2406.18530 — accessed 20 Oct 2026
- GOAL: knowledge-grounded video captioning benchmark for soccer commentary, CIKM 2023 — https://arxiv.org/abs/2303.14655 — accessed 20 Oct 2026
- Super Bowl LIX streaming latency (Phenix; Comcast update) — https://www.sportsvideo.org/2025/02/10/super-bowl-lix-tubi-leads-all-streaming-platforms-in-least-lag-time-according-to-phenix-report/ — accessed 20 Oct 2026
- Moorkens & Pintado Gutiérrez, "Audio Describing Football: A Case Study of Bohemians FC", JoSTrans 45 (2026) — https://www.jostrans.org/article/view/5620 — accessed 20 Oct 2026
- FIFA, audio descriptive commentary at Qatar 2022 — https://www.fifa.com/en/social-impact/news/en/news/audio-descriptive-commentary-makes-qatar-2022-accessible-for-blind-fans — accessed 20 Oct 2026 (search snippet only)
- EFDN, Respect inclusion: audio-descriptive commentary — https://efdn.org/blog/resource/audio-descriptive-commentary — accessed 20 Oct 2026 (search snippet only)
- RNIB, second focus group on accessibility of football broadcasts (2022) — https://media.rnib.org.uk/documents/RNIB_second_focus_group_on_accessibility_of_football_broadcasts_2022.pdf — accessed 20 Oct 2026
- Microsoft Learn, SSML voice and sound (prosody, styledegree, HD style markers) — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-synthesis-markup-voice — accessed 20 Oct 2026
- Microsoft Learn, HD voices (DragonHD / Omni list, SSML support table, latency, temperature, cfg_scale) — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/high-definition-voices — accessed 20 Oct 2026
- Microsoft Learn, SSML document structure (break 0-20,000 ms, mstts:silence) — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-synthesis-markup-structure — accessed 20 Oct 2026
- Internal: files 22 (DFL ticker latency, salience), 23 (WP model), 24 (scheduler, stale/TTL), 27 (voices, Voice Live, latency)
