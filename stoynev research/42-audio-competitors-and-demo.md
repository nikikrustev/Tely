# 42 — Audio-first rivals in the field, and how to demo an audio experience in a 2-minute video

_Accessed/compiled: 20 Oct 2026 · Priority area: competitors (audio/accessibility) + demo video (Render, Personalise; Agentic Design and UX criteria)_

## TL;DR

- **The rival to watch is The Ninety Labs (126492), not the "blind-fan" entries.** Its public repo has an audio-description "Describer" in open PRs #129 and #134 (not merged yet). Lines are fact-checked, start at most 2 s after the event, are panned left or right by pitch x, and come with a WebVTT description track. Its video script already plans a **15-second black-screen, audio-only shot**. So "screen goes dark" alone will not look new.
- **The strongest voice product is Matchday Companion (126542, `ogu83/inside-the-game-hackathon`).** It has a live ACA demo (HTTP 200 today), a 2-minute YouTube video, push-to-talk barge-in on Foundry Voice Live, MCP ledger tools, a speech audit, and measured numbers (Q&A median 4.66 s). Its 20 s delay is used **only to verify** lines. ADR 0004 deliberately blocks the Q&A agent from seeing the future. Nobody we found uses the delay to **build anticipation**.
- **No public evidence of the dedicated blind-fan entries.** Audio Eyes (126311) and Blind-side (126432) have no findable code. `Majordev77/Blind-side` is probably theirs (same name, created 9 Oct), but it holds only a Django/React scaffold and a stereo pan-sweep test (unverified link). VYBE (126450) uses browser TTS and says its accessibility validation is still to do. **No hackathon repo we found reports testing with blind or low-vision users, crowd atmosphere or haptics.** The real-world products all do test with BLV users (OneCourt, Columbia, Sky with RNIB).
- **Demo craft:** in a 2019 survey of 5,616 US adults, 69% watched video with sound off in public. So the video must work **muted** (burned-in English captions, including non-speech sounds like [crowd rises]) and on **laptop speakers** (mono-safe; show position on screen as a radar, never rely on panning alone). Give "headphones" as a bonus, not a requirement. Let a real listener carry the story, the way Seeing AI, Be My Eyes and Apple's "The Greatest" did.
- **Category:** enter **Best Use of Microsoft Foundry** (Voice Live, Agent Service, evaluations and tracing all live in Foundry). Use Real-World Impact and UX for the Grand Prize. Frame the agents around **information asymmetry**: a Director who knows the next N seconds, and a Commentator and Q&A agent who must not spoil them, with a measured spoiler-leak eval.

## Findings

### 1. Audio and accessibility rivals (public evidence only)

Innovation Studio pages need sign-in, so the one-line pitches come from `Berbata_Hackathon_Intel.md`. Everything else comes from public GitHub and YouTube.

| ID · Project | What it does | Evidence shipped (public) | Strengths | Gaps |
|---|---|---|---|---|
| 126492 **The Ninety Labs** (3 people) | CV auto-eventing from synthetic video, agents, overlays. Personas include **audio description for blind/low-vision fans** | MIT repo `KLKH7/the-ninety-labs`, pushed 20 Oct. Describer in **open** PRs #129/#134: fact-checked lines, a 2 s lag limit (drop rather than delay), `pan = x/52.5 − 1`, WebVTT descriptions, `aria-live` switched off while the voice speaks, R to repeat, mutation-tested. Video script shot 4: "Screen dark: audio description only" (1:00–1:15) | Rigorous; already frames impact for blind fans; the same verified facts reach both audio and screen | Describer not merged; event detection from video not done yet. **Reactive only** (describes what has just happened); one voice; no crowd, haptics or Q&A for the listener |
| 126542 **Matchday Companion** (ogu83) | "A live co-commentator you can interrupt, and that can't lie". Director, Commentator, two-layer Fact-Checker, Producer; EN/TR | Repo, live ACA app, YouTube video "the AI commentator that can't lie". Q&A median 4.66 s (was 11.76 s); barge-in halts audio in under 0.4 s; 0 of 4 planted errors aired; verbatim speech audit | Best voice UX in the field; numbers measured | **Not accessibility-framed.** The delay is for verification, and the future is firewalled from Q&A. No atmosphere, no haptics, no spatial audio |
| 126450 **VYBE** | Young, Accessible and Analyst modes; captions in EN/AR/CS; step-by-step screen-reader playback | Repo `Hapinam/vybe-ai`, 53 s video. README: "Live demo: pending Azure deployment". Browser SpeechSynthesis, not Azure Speech | Real a11y controls (keyboard, contrast, step mode) | Text-first, not audio-first. Admits narration "needs manual timing/accessibility validation" |
| 126311 **Audio Eyes** (2 people) | "Spatial audio, conversational", full write-up | **No public repo or video found** (searched GitHub by name and by both members' names; `ishrastogi` has no recent repos) | On paper the closest concept to ours (spatial + conversation) | Unverifiable |
| 126432 **Blind-side** | "Spatial audio for blind fans" | Probably `Majordev77/Blind-side` (unverified): scaffold plus a commit "Play beep left-only then right-only to prove stereo" (15 Oct) | Stereo proof planned for the demo | No football logic in the public code |
| 126309 **Sauti** | Agent Framework + Speech audio commentary | No repo found | — | Unverifiable |
| 126306 **Msimulizi** (4 people) | Swahili/EN/FR commentary with Azure Speech `sw-KE` voices | Repo `kurosakiaduma/msimulizi`; 30 Swahili lines rated 4.2/5 by a native speaker; audio p50 target ≤ 8 s | Language and voice quality | Not accessibility; audio latency is a target, not a measurement |
| 126465 **Matchday Crew** | EN/Swahili/Japanese spoken lines (`en-GB-RyanNeural` and others), "one line at a time so the voice never falls behind" | Repo `timsheldon1/matchday-crew`, 45 tests, ACA | Simple, working voice | Voice is an add-on |
| 126666 Mic'd Up · 126613 Twelfth Voice · 126648 Coach in Your Ear | Commentary at your level / fan's own voice / teaching new fans | Pitch lines only; no repos found | — | Unverifiable |

Related entries, not audio-first: 126398 Matchmate ("talk to the match"), 126595 La Liguilla (conversational stats via MCP), 126499 PitchPulse (control room plus voice).

### 2. White space for Tely (only what the evidence supports)

1. **Anticipation is unclaimed.** Matchday Companion's ADR 0004 says its Q&A tools read a `LedgerView` filtered by `playback_t`, so the Q&A agent "cannot observe events … in the 20-second future ingest buffer". The Ninety Labs drops late lines rather than delaying them. **No public entry uses look-ahead to shape tension.**
2. **Atmosphere and haptics.** No public hackathon repo we found has a crowd mix or haptics. One older repo, `DilipReddy72/haptic-football-accessibility` ("In progress", May 2026), predates the hackathon window.
3. **Measured with blind users.** No public entry reports BLV testing. The real-world bar is testing:
   - OneCourt (Microsoft AI for Accessibility grant, runs on Azure) found that **audio works better for "gameplay events, player names, and emotions"**, while **haptics are preferred for spatial details**. Fans rated comprehension **74.3% higher** with haptics plus generated audio description than with radio alone.
   - Columbia's spatial-audio system was validated with 12 BLV users.
   - Sky's Premier League Descriptive Audio Commentary (live from 10 Oct 2026, about 109 games a season) was tested with RNIB.
4. **The combination.** Spatial crowd + anticipatory commentary + voice Q&A + haptics appears in **no public entry**. Audio Eyes might overlap on spatial + conversation, but it is unverifiable, so say "no public entry", not "no entry".

### 3. Demo craft for an audio-first product

The constraints come from [12](12-judging-criteria-and-rules.md) and [14](14-demo-video-and-writeup.md): under 2:00, English materials, no copyrighted music, judges may never open the app.

- **Assume muted or laptop speakers.** 69% watch with sound off in public and 25% even in private (Verizon Media/Publicis 2019, n = 5,616). YouTube's own spatial-audio support targets 360°/VR video (first-order ambisonics), so a normal upload is plain stereo. Bake binaural rendering into the stereo mix with Web Audio `PannerNode.panningModel = "HRTF"`, and make sure nothing depends on it.
- **Caption everything heard**, not just speech. WCAG's intent for captions includes "non-speech information conveyed through sound, including meaningful sound effects". Use SDH style: `[crowd swells, left]`, `[whistle]`, `[phone pulses ×3]`. Burn them in (the rules require English) and also upload the SRT. Our commentary comes from cue text, so the captions are exact (see 32).
- **Make the sound visible:**
  - a **spatial radar**: a top-down disc around the listener, with the ball and crowd sections lighting up where the sound comes from
  - a thin **waveform/level strip** per channel, so L/R is visible
  - a **haptic indicator**: a phone outline that pulses in time with the vibration pattern, with the pattern string shown
  - a **look-ahead timeline**: "Director knows: shot in 6 s" next to "Fan hears: build-up". This one shot sells the agentic idea.
- **Open with the framing, not the architecture.** 0:00–0:10: black screen, the caption "This is how a blind fan watches. Headphones help, but the captions tell you everything", crowd audio fading in. The Ninety Labs uses black at 1:00. We should own the opening and then go further than they do, with a live question.
- **Show the Q&A live and unedited.** One question in one take, the answer starting on screen with a latency badge. Matchday Companion shows barge-in under 0.4 s, so cutting around the wait would look weaker.
- **Let a real listener carry it** (with consent and a release). What made known accessibility films land:

| Example | What made it work |
|---|---|
| Seeing AI, Build 2016 | Saqib Shaikh, a blind Microsoft engineer, uses it himself on everyday tasks (reading a menu, describing people nearby). It closed Satya Nadella's keynote |
| Be My Eyes / Be My AI | A blind beta tester (Lucy Edwards) does a real task, a tube-map route, and the outcome comes in her words: "I have my autonomy back" |
| Apple "The Greatest" (2022) | Disabled people using built-in features in daily routines, music-led and with no product talk. Won the Emmy for Outstanding Commercial (and, per coverage, the Ad Age ad of the year and D&AD pencils; unverified) |
| Action Audio (Tennis Australia/AKQA) | Abstract, "filterable" sounds from live ball-tracking data, overlaid on commentary. Shortlisted at D&AD and Cannes Lions |

  The common pattern: a first-person user, one everyday task completed on camera, and the outcome stated by the user. If we cannot recruit a BLV tester this week, use an eyes-closed sighted volunteer, **labelled as such**. Never imply BLV validation we did not do.

## So what for us

**Tely (main):**

- **Render/Personalise: differentiate on anticipation + embodiment, not on "audio description".**
  - The Ninety Labs will show verified, panned description. Matchday Companion will show verified, interruptible voice.
  - Our hero is the thing neither can show: the commentator's voice rising **before** the chance, with crowd and haptics following the tension curve from 23, and an answer to a spoken question.
  - Keep a truth_check on every spoken number (table stakes, see 16).
- **Interpret/Explain: build the agent split as an information firewall** (and measure it):
  - **Director agent:** reads the delayed buffer (next N s). It outputs only a *tension plan* (`build_up_level`, `hold_ms`, `hint_type`), never the outcome.
  - **Commentator agent:** writes lines from present facts plus the tension plan. SSML prosody comes from `build_up_level` (see 27).
  - **Conversational agent (Voice Live, function tools):** `get_score`, `where_is_ball`, `explain_last_moment`, `player_status`. The tools are bounded by `playback_t`, the same pattern as Matchday Companion's ADR 0004, so the fan cannot be spoiled.
  - **Verifier:** checks numbers and runs a **spoiler-leak eval**: the rate at which lines or answers mention a future event before `playback_t`. Target 0, and report it.
  - **Crowd and haptics:** keep them deterministic code driven by the same tension signal. Say so honestly; do not call them agents.
- **Category:** Best Use of Microsoft Foundry (Voice Live, Agent Service, Evaluations, Tracing). Name it in the first line of the write-up. Use Multi-Agent only if we really ship handoff (barge-in moves the turn from Commentator to Q&A and back) plus failure recovery (fallback to pre-rendered lines).
- **Evidence we must create:** a small listening test.
  - Ideally with BLV fans: contact RNIB or a local organisation (unverified whether that is feasible in a week).
  - Otherwise eyes-closed, measuring "who has the ball / which side / was it dangerous" accuracy across radio-style commentary only, + crowd, + haptics.
  - OneCourt's study is the model to cite.

**Other ideas, briefly:** 17 Heartbeat and 20 Home End are absorbed into Tely. **D Chalk Talk** shares the Voice Live tool pattern. **A TwinCast**: The Ninety Labs is the same CV-from-synthetic-video concept with a head start, so TwinCast would need a different hero.

## Reuse: code & links

**Video assembly (ffmpeg):** burned-in SDH captions, a per-channel level meter (so L/R is visible on mute), and a waveform strip. Untested: check the filter names against your ffmpeg build.

```bash
ffmpeg -i screen.mp4 -i mix_binaural.wav -filter_complex \
 "[1:a]asplit=2[a1][a2];[a1]showwaves=s=1920x120:mode=cline:split_channels=1:colors=white|cyan[w]; \
  [a2]showvolume=w=400:h=20:o=h[m]; \
  [0:v][w]overlay=0:H-h-60[v1];[v1][m]overlay=40:40, \
  subtitles=captions_sdh.srt:force_style='FontSize=26,BorderStyle=3,Outline=0,BackColour=&H80000000'[v]" \
 -map "[v]" -map 1:a -c:v libx264 -crf 18 -c:a aac -b:a 192k -shortest tely_demo.mp4
```

**SDH captions straight from our cue stream (Python),** with no speech-to-text needed:

```python
def srt(cues):  # cues: [{tc_in_ms, ttl_ms, text_spoken, sfx: ["crowd swells, left"]}]
    ts = lambda ms: f"{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}"
    out = []
    for i, c in enumerate(cues, 1):
        line = " ".join(f"[{s}]" for s in c.get("sfx", [])) + " " + c.get("text_spoken", "")
        out.append(f"{i}\n{ts(c['tc_in_ms'])} --> {ts(c['tc_in_ms'] + c['ttl_ms'])}\n{line.strip()}\n")
    return "\n".join(out)
```

**Haptic indicator on screen, matching the real vibration (TS).** `navigator.vibrate` is unsupported on iOS Safari (unverified here), so the on-screen pulse doubles as the fallback.

```ts
export function pulse(pattern: number[], el: HTMLElement) {
  try { navigator.vibrate?.(pattern); } catch {}
  let t = 0;
  pattern.forEach((ms, i) => { if (i % 2 === 0) setTimeout(() => el.animate(
    [{ transform: "scale(1)" }, { transform: "scale(1.15)" }, { transform: "scale(1)" }],
    { duration: ms }), t); t += ms; });
  el.dataset.pattern = pattern.join("·"); // show the pattern as on-screen text in the video
}
```

**Spoiler-firewalled Q&A tool (the pattern from Matchday Companion's ADR 0004):**

```python
def get_score(ledger, playback_t: float) -> dict:
    ev = [e for e in ledger.events if e.t <= playback_t]  # never the look-ahead buffer
    return {"home": sum(e.type == "goal" and e.team == "home" for e in ev),
            "away": sum(e.type == "goal" and e.team == "away" for e in ev), "as_of": playback_t}
```

Links to learn from:

- The Ninety Labs Describer: PR #134, https://github.com/KLKH7/the-ninety-labs/pull/134
- Matchday Companion: demo script https://github.com/ogu83/inside-the-game-hackathon/blob/main/docs/demo-script.md and ADR 0004 (`docs/adr/0004-broadcast-delay.md`)

## Sources

- Berbata_Hackathon_Intel.md (local; project pitch lines for 126306–126727) — accessed 20 Oct 2026
- The Ninety Labs README — https://github.com/KLKH7/the-ninety-labs — accessed 20 Oct 2026
- The Ninety Labs video script — https://github.com/KLKH7/the-ninety-labs/blob/main/docs/video-script.md — accessed 20 Oct 2026
- The Ninety Labs PR #134 (Describer) — https://github.com/KLKH7/the-ninety-labs/pull/134 — accessed 20 Oct 2026
- Matchday Companion README, demo script, ADR 0004 — https://github.com/ogu83/inside-the-game-hackathon — accessed 20 Oct 2026
- Matchday Companion live app — https://ca-matchday.orangetree-bcef6d10.eastus2.azurecontainerapps.io — accessed 20 Oct 2026 (HTTP 200)
- Matchday Companion video (YouTube oEmbed title) — https://youtu.be/wi6E7SjbZjQ — accessed 20 Oct 2026
- VYBE README and storyboard — https://github.com/Hapinam/vybe-ai — accessed 20 Oct 2026; video https://youtu.be/c717qul116M
- Blind-side (probable) — https://github.com/Majordev77/Blind-side — accessed 20 Oct 2026 (unverified link to 126432)
- Msimulizi — https://github.com/kurosakiaduma/msimulizi — accessed 20 Oct 2026
- Matchday Crew — https://github.com/timsheldon1/matchday-crew — accessed 20 Oct 2026
- Microsoft Accessibility Blog, "OneCourt: Revolutionizing accessibility in live sports" — https://blogs.microsoft.com/accessibility/onecourt-revolutionizing-accessibility-in-live-sports/ — accessed 20 Oct 2026
- Columbia Technology Ventures, CV-enabled immersive audio for BLV sports fans — https://inventions.techventures.columbia.edu/technologies/computer-vision--CU23071 — accessed 20 Oct 2026
- Diageo/Sky Media press release (Descriptive Audio Commentary) — https://www.diageo.com/en/news-and-media/press-releases/2026/sky-media-and-guinness-launch-sky-sports-biggest-expansion — accessed 20 Oct 2026
- InAVate APAC, interview with Tim Devine (AKQA) on Action Audio — https://www.inavateapac.com/features/article/interview-tim-devine--akqa — accessed 20 Oct 2026
- D&AD, Action Audio — https://dandad.org/awards/professional/2021/234948/action-audio — accessed 20 Oct 2026 (via search)
- Cannes Lions "The Work", Action Audio — https://www.lovethework.com/work-awards/entries/582122 — accessed 20 Oct 2026
- Mediaweek, Apple's "The Greatest" wins Emmy — https://mediaweek.com.au/apples-outstanding-accessibility-ad-the-greatest-wins-primetime-emmy — accessed 20 Oct 2026
- Campaign, "Apple wins an Emmy for The Greatest" — https://campaignlive.com/article/apple-wins-emmy-the-greatest/1856769 — accessed 20 Oct 2026 (403; details via search summary, unverified)
- Scroll.in, Seeing AI Build 2016 video — https://scroll.in/video/807836/scroll_in — accessed 20 Oct 2026 (via search)
- OnMSFT, Seeing AI at Build 2016 — https://onmsft.com/?p=54041 — accessed 20 Oct 2026 (via search)
- OpenAI, Be My Eyes — https://openai.com/index/be-my-eyes — accessed 20 Oct 2026 (403; via search)
- The Decoder, "How GPT-4 is helping the blind to see" (Lucy Edwards) — https://the-decoder.com/how-gpt-4-is-helping-the-blind-to-see/ — accessed 20 Oct 2026 (via search)
- Streaming Media, Verizon Media/Publicis captions study — https://www.streamingmedia.com/Articles/News/Online-Video-News/80-of-Video-Caption-Users-Arent-Hearing-Impaired-Finds-Verizon-131860.aspx — accessed 20 Oct 2026
- W3C, Understanding SC 1.2.2 Captions (Prerecorded) — https://www.w3.org/WAI/WCAG22/Understanding/captions-prerecorded.html — accessed 20 Oct 2026
- YouTube Help, spatial audio in 360/VR videos — https://support.google.com/youtube/answer/6395969 — accessed 20 Oct 2026
- MDN, PannerNode.panningModel — https://developer.mozilla.org/en-US/docs/Web/API/PannerNode/panningModel — accessed 20 Oct 2026
- Penn State PLAINTEXT, AICommentator (conversational agent for football viewing; DOI 10.1145/3640543.3645197) — https://plaintext.psu.edu/2024/07/22/paper-presentation-aicommentator-conversational-agent-for-football-viewing-presented-by-dr-jonathan-dodge — accessed 20 Oct 2026
