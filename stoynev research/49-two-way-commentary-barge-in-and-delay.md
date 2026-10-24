# 49 — Talking over the commentator: barge-in, "is that for me?", the delay and the agent layout

_Accessed/compiled: 24 Oct 2026 · Priority area: Audio Stands Personalise + Render (two-way audio), with the whole pipeline's timing (Interpret → Explain → Render). Builds on [36](36-blind-fans-and-audio-description.md), [39](39-anticipatory-emotional-commentary.md), [40](40-conversational-commentator.md), [43](43-audio-stands-architecture.md), D17 and D21._

## TL;DR

- **Barge-in has two halves, and only one of them needs the network.** *Detecting* that the fan spoke happens on the Voice Live server: `speech_started` needs at least `speech_duration_ms` of speech (80 ms default on `azure_semantic_vad`), plus the uplink and downlink time. *Stopping* the sound is entirely our browser code. Voice Live's `interrupt_response` stops only the server-side response, and Microsoft's own samples drop their local queue on `speech_started`. A press of a button or key skips detection completely, so it is **the only path that can promise a stop "within a fraction of a second"** today.
  - No vendor publishes a Voice Live first-audio or barge-in latency. Ours, from D17: first answer audio **p50 1.14 s, p95 1.82 s** after the fan stops speaking.
- **Echo is the blocker for an always-open mic, not the VAD.** Voice Live's default server echo cancellation "uses its own internal audio as the echo reference". It knows the model's voice but **not our crowd bed or the pre-rendered commentary**.
  - **Live-Reference AEC** fixes that: the client sends stereo PCM16, mic on channel 0 and the playback mix on channel 1. It needs api-version **`2026-07-15`**, and we run **`2026-04-10`**.
  - Chrome's own `echoCancellation` also covers same-page Web Audio output: one community test measured 37.7 dB of reduction (unverified elsewhere). Since Chrome 141 it also offers `"all"` (whole system).
  - Open-ear headphones and laptop speakers are where both will be tested hardest. No vendor publishes numbers for double-talk.
- **There is no reliable, browser-ready way on the Microsoft stack to know the fan is talking to the commentator and not a friend.**
  - The Speech SDK for JavaScript "doesn't support keyword recognition".
  - Azure Speaker Recognition was retired on 30 Sep 2025.
  - An LLM asked "was this said to the assistant?" with no training is poor: Apple measured a **46.7% false-accept rate** when prompting only. GPT-4o scored 80.9% on three-party addressee detection against an 80.6% chance level.
  - Fine-tuned models get to roughly **8% EER**, which still means about one call in twelve is wrong.
  - **Recommendation:** keep the explicit Ask (button, key, headset button) as the primary trigger. Add a short **follow-up window** with start and end earcons, the way Alexa (about 5 s) and Google (about 10 s) do. When unsure, **ignore silently**, as every production system we found does.
- **A fixed 60 s delay buys little we can't get another way, and it costs the thing blind fans complain about most.**
  - LLM text fits in 7–12 s (DFL ticker), so 15–20 s already covers it.
  - Lag is the top documented pain:
    - Luton's 40 s radio delay meant fans "can't keep up with play";
    - a blind MLB fan on a 30 s delay: "You have to have it in real time";
    - 45% of UK adults have had a result spoiled by delay (Opinium/Uswitch 2024).
  - **Recommended instead:**
    1. keep **D ≈ 10 s as the floor**;
    2. write colour and stoppage segments from the past (≤ P), which needs no extra delay;
    3. later, make the delay **elastic**: the match *waits for the fan* while they talk, then catches up by trimming dead-ball time. A Premier League match has only 55–57 min of ball in play.
- **Agent layout:** add two deterministic (non-LLM) pieces to what we have.
  - **Floor Manager:** decides who speaks now (fan, commentary call, answer, catch-up) and owns barge-in, holds and deferred answers.
  - **Heard Ledger:** per listener, what was *actually* played, cut at the point of interruption. Both the Q&A agent and the catch-up read it.
  - That ledger is how live answers stay consistent with what the fan heard. Today the relay sends only `[LISTENER AT mm:ss]`.
- **Sharing the audio:**
  - **Pause the commentary, don't duck it.** In a study, 20 of 23 visually impaired listeners could pick out a target among two voices, but only 7 understood more than half of the content.
  - Duck the crowd harder than today's −12 dB while answering: Torcoli et al. found commentary needs at least 15 LU over ambience.
  - **Never resume a pre-rendered line mid-sentence after a question.** Today's track does: `commentary-track.ts` resumes the interrupted line at the playhead offset. Restart the line if it is still fresh, otherwise drop it and let the catch-up summarise.
  - Orientation questions are answered at once in one breath.
  - Analysis questions wait for a stoppage of 25 s or more (goal kick 27.7 s, corner 33.9 s, sub 64.3 s on average). A throw-in (15.3 s) is too short.
- **Before 27 Oct, only client-side, low-risk changes:**
  - press-to-interrupt everywhere, plus a keyboard shortcut;
  - the resume-mid-sentence fix;
  - optionally the Heard Ledger in the relay with `auto_truncate`, if it can be redeployed and re-evaluated before Monday's video takes.
  
  Open-mic barge-in, Live-Reference AEC, the follow-up window and the elastic delay come after the deadline.

## Findings

### 0. Where we are today (code read on 24 Oct, branch `a/audio-mix`)

| Piece | Today | File |
|---|---|---|
| Trigger | Ask button → menu → "ask live". The mic opens about 250 ms after the earcon, only while asking, and closes on `speech_stopped`. | `web/src/lane-a/live-ask.ts`, `web/src/ask/ask.ts` |
| Voice Live session | `2026-04-10`, `azure_semantic_vad` (500 ms, `remove_filler_words: true`), `server_echo_cancellation`, `azure_deep_noise_suppression`, 300 output tokens. **`interrupt_response` and `auto_truncate` are not set** (defaults true and false). | `relay/voicelive.py:62-79` |
| Browser mic | `echoCancellation: true, noiseSuppression: true, autoGainControl: true`, mono. Each answer has its own AudioContext (D17). | `live-ask.ts:347` |
| During an answer | Commentary paused (its AudioContext suspended), crowd ducked −12 dB, playhead **keeps running** | `ask.ts:99-103` |
| After an answer | Templated catch-up from the pause to now, then `commentary.resume()` | `ask.ts:105-111` |
| Resume | The line that was speaking when paused **resumes mid-sentence at the playhead offset** (built for pause and seek) | `commentary-track.ts:97, 164, 235-239` |
| Second press while busy | `AskController.run` returns at once while `busy`. Whether the live answer can be stopped by a press: unverified, check on device. | `ask.ts:86` |
| Hold that thought | A shot with xG ≥ 0.08 due within 8 s → "hold that thought", wait 8 s | `pipeline/audiostands/qa/__init__.py:156-165` |
| Shared context | One system note per question, `[LISTENER AT mm:ss]`. **No record of aired lines** (file 40 §4 proposed `[AIRED …]`). | `relay/voicelive.py:45, 187` |

### 1. Barge-in: detection, echo and latency

**1a. What Voice Live gives us** (how-to, updated 8 Oct 2026; API reference, updated 24 Sep 2026)

| Setting | What it does | Default |
|---|---|---|
| `turn_detection.type` | `server_vad` (volume), `semantic_vad` (only gpt-realtime and gpt-realtime-mini), `azure_semantic_vad` / `_multilingual` (all models) | `server_vad` |
| `threshold` | Activation confidence, range [0.01, 1.0) | 0.5 |
| `speech_duration_ms` | Speech needed before detection starts | **80 ms** azure types, 200 ms `server_vad` |
| `prefix_padding_ms` | Audio kept from *before* detection, which is not a delay. 420 ms on the azure types from `2026-04-10`; the API reference still says 300, so the docs disagree. | 400 / 420 |
| `silence_duration_ms` | End of the fan's turn | 500 |
| `end_of_utterance_detection` | `semantic_detection_v1` (EN) or `_multilingual`, `threshold_level`, `timeout_ms` "Defaults to 1000 ms". No latency figure: the docs say only "without adding user-perceivable latency". | off |
| `interrupt_response` | Barge-in on/off. "Only available with" the azure semantic types; the API reference also lists it on `server_vad`, another doc conflict. | true |
| `auto_truncate` | "Auto-truncate on interruption", so the conversation keeps only what was heard | **false** |
| `remove_filler_words` | Ignores "ah, umm, mm, uh, huh, oh, yeah, hmm" **while a response is playing**. It "assumes the client plays response audio as soon as it receives them". English list; 10 languages, no Bulgarian. | false |
| `create_response` | false = transcribe without answering. Useful for a "was that for me?" gate (§2). | true |

- **Events on a barge-in:**
  - `input_audio_buffer.speech_started` carries `audio_start_ms`. The reference says the client "might want to use this event to interrupt audio playback".
  - `response.cancel` "immediately stops response generation and related audio output".
  - `conversation.item.truncate` (`item_id`, `content_index`, `audio_end_ms`) gets `conversation.item.truncated` back, which "removes the server-side text transcript" of the unheard audio.
  - `output_audio_timestamp_types: ["word"]` returns `response.audio_timestamp.delta` per word (`audio_offset_ms`, `audio_duration_ms`, `text`). That gives exact cut points for the Heard Ledger (§3).
- **How Microsoft's samples stop playback.** `voicelive-samples` `model-quickstart.js` and `.py` call `skipPendingAudio()` / `skip_pending_audio()` on `speech_started`, which bumps a sequence number so queued chunks are dropped. They send neither `response.cancel` nor `truncate`; they rely on `interrupt_response`. **So the stop is client code**, and nothing on the server silences audio already in our Web Audio queue.
- **Comparison (OpenAI Realtime, which Voice Live mostly mirrors).** Over WebSocket, the client must "immediately stop playback" and send `truncate` with the milliseconds it actually played. Over WebRTC the server tracks the output buffer and cuts it itself. OpenAI warns the model "doesn't have enough information to precisely align transcript and audio". Kwindla Kramer (Daily) adds: truncate always, so history holds only "the part of the LLM response that the user actually heard".

**1b. Echo: why an open mic is hard for us specifically**

| Echo path | Default `server_echo_cancellation` | Live-Reference AEC (`2026-07-15`+) | Chrome `echoCancellation: true` |
|---|---|---|---|
| Live answer (the model's voice) | Yes, if played within 2 s of arrival ("If playback is delayed for more than two seconds, echo cancellation quality is impacted") | Yes | Yes (same page) |
| Pre-rendered commentary (MP3 through Web Audio) | **No**: the reference is "its own internal audio" | Yes, if it goes through the bus that feeds channel 1 | Probably (see below) |
| Crowd bed, chants, reactions | **No** | Yes, same condition. Our case is described ("mixes audio before playback"), but crowd or music cancellation is not tested anywhere in the docs (unverified). | Probably |
| Screen reader voice, other apps | No | No ("Other tabs and OS sounds are not in the reference") | Only with `"all"` |

- **Live-Reference AEC mechanics** (how-to; sample `javascript/live-reference-aec`, added 4 Aug 2026):
  - `input_audio_format: pcm16`, `reference_source: "client"`, `channels: 2`, interleaved with the mic sample first.
  - The sample rate (8, 16 or 24 kHz) must match the AudioContext, and none of these can change mid-session.
  - The reference travels in the same packet as the mic, so jitter can't misalign the two.
  - Bandwidth is about 94 KB/s raw. The sample turns the browser's own echo cancellation, noise suppression and AGC off. "The server does not validate the quality of the reference channel", and quality drops in reverberant rooms.
  - It needs `@azure/ai-voicelive` ≥ 1.1.0 for the sample. Our relay uses the Python SDK, so whether that SDK accepts the field is unverified.
  - **Our problem:** today commentary, crowd and the live answer play from **three AudioContexts** (D12, D17). Live-Reference AEC needs one playback bus that everything goes through, tapped as the reference. That is a refactor, not a flag.
- **Browser echo cancellation:**
  - The W3C spec now allows `echoCancellation: "all" | "remote-only"`. With `"all"` the browser "MUST attempt to remove all sound being played by the system". Chrome shipped both in **Chrome 141** (Intent to Ship 22 Aug 2025).
  - Chrome's plain `true` has covered audio-service output, AudioContext included ("Chrome-wide AEC"), since about Chrome 111. That comes only from a Zoom SDK forum thread; Google doesn't confirm it.
  - One community test on Chrome 155 / macOS measured same-page echo reduced by **37.7 dB** with `true` and 42.3 dB with `"all"`. Other apps: 0.3 dB with `true`, 42.5 dB with `"all"`. `"all"` needs macOS 14.2+ and a system-audio permission. Single tester (unverified elsewhere).
  - Safari/iOS: WebKit bug 326286 (4 Oct 2026, NEW): page audio crackles while an echo-cancelled mic is open on iOS 26.2–27, and turning echo cancellation off routes output to the earpiece.
  - Firefox: no current documentation found (unverified).
- **What this means:**
  - With **closed headphones**, echo is a small problem, and today's settings would allow open-mic barge-in.
  - With **open-ear headphones** (which blind people often prefer, to keep hearing the room; file 37) or **laptop speakers**, our own commentator's voice reaches the mic. The failure mode is the commentator interrupting itself or answering its own line.
  - `remove_filler_words` doesn't help here: it only filters filler words, and only while a *response* plays, not our pre-rendered track.

**1c. Latency we can quote**

| Step | Figure | Source / status |
|---|---|---|
| Press → our audio silent | One Web Audio gain ramp (we'd use 80–150 ms to avoid a click) | Ours, **to measure**; no network involved |
| Speech onset → `speech_started` | ≥ 80 ms of speech (`speech_duration_ms`) + uplink + server + downlink | No published figure; **to measure** |
| Barge-in → stop (vendor comparison) | LiveKit adaptive interruption: median 216 ms of audio to trigger, ≤ 30 ms inference, "86% precision and 100% recall" at 500 ms overlap, rejects 51% of plain-VAD barge-ins | LiveKit blog, 19 Mar 2026 (vendor, Cloud only) |
| Rival in this hackathon | Matchday Companion: barge-in halts audio "in under 0.4 s" (push-to-talk) | File 42 |
| Fan stops → first answer audio | **p50 1.14 s, p95 1.82 s**; to the facts p50 2.66 s, p95 3.35 s | **Ours, measured** (D17, 31 questions, deployed) |
| Voice-to-voice target | "800ms voice-to-voice latency is a good target" (OpenAI time-to-first-byte about 500 ms for US clients); Bluetooth adds "several hundred milliseconds" | Kramer, latent.space, Nov 2024 (guidance) |
| End-of-turn models (comparison) | Pipecat Smart Turn v3.1: 94.7% EN accuracy (8 MB), ~12 ms CPU; Deepgram Flux ~260 ms end of turn | Daily, 3 Dec 2025; Deepgram, 2 Oct 2025 (vendor) |

**Realistic for us:** a press stops all audio in about 0.1 s, and the fan hears the start of an answer about 1.1–1.8 s after they stop talking. Voice barge-in adds an unmeasured detection delay (at least 80 ms of speech plus two network legs through the relay). We must measure it before quoting it.

### 2. "Is the fan talking to me?"

| Option | Accuracy / false triggers (published) | Browser + Microsoft stack? | Accessibility | Verdict |
|---|---|---|---|---|
| **Push-to-talk / toggle Ask** (button, key, headset media button) | No addressee errors by design; the fan decides | Yes, today | A standard VoiceOver/TalkBack double-tap. Hold-to-talk is awkward under VoiceOver (file 40). The fan must find the button, so give it a key and a headset button too. | **Primary, keep** |
| **Follow-up window** (mic stays open ~5–10 s after an answer, with earcons) | Alexa Follow-Up Mode: about 5 s, ended by "stop"/"thank you". Google Continued Conversation: about 10 s, uses speech plus phone motion. **No accuracy published.** | Yes: our VAD plus a gate (below) | Hands-free for the natural next question; the earcon says the mic is open (Alexa documents start and end sounds) | **Add later** (needs echo handling, §1b) |
| **Wake word / vocative** ("Commentator, …") | openWakeWord *target* <0.5 false accepts/hour, <5% false rejects (not a benchmark). Smart speakers misfired **0.95 times/hour** on TV audio (Dubois et al., PoPETs 2020). Azure keyword: no figures published. | **No.** The JS Speech SDK "doesn't support keyword recognition". openWakeWord isn't ported to the browser, and its pre-trained models are CC BY-NC-SA. Porcupine's free keys reportedly stopped on 30 Jun 2026 (secondhand, unverified). | Hands-free, no button to find. A football crowd and TV commentary are close to the worst case for false wakes (unverified). | Skip for now. A spoken name in the follow-up window is cheap context (Apple: the first query helps). |
| **LLM "addressed to me?" on the transcript** | Zero-shot prompt: FRR 13.8%, **FAR 46.7%** (Apple, Rudovic et al. 2024). With a trained head, previous query and 8-best ASR: **EER 7.9%**, FAR 4.8% at 10% FRR. GPT-4o three-party addressee: 80.9% vs 80.6% chance (Inoue et al. 2025). | Yes (Voice Live `create_response: false` → transcript → gpt-5-mini decides → `response.create`). Adds one LLM hop (~1–2 s, ours, unmeasured). | Invisible to the fan, but every miss is either a silent drop or a reply to a friend | Only as a second gate inside the follow-up window, biased to "ignore" |
| **Audio + text device-directed classifier** | Amazon fused model **5.2% EER** (Mallidi et al. 2018); Apple multimodal **8.23%** EER (Wagner et al. 2023) | No ready model; needs training data we don't have | Same as above | Later / research |
| **Speaker enrolment (target-speaker VAD)** | Personal VAD average precision 0.955 clean, 0.916 with noise and reverb (Ding et al. 2020, synthetic LibriSpeech mixes) | **No.** Azure Speaker Recognition was retired 30 Sep 2025. Silero VAD runs in the browser (`@ricky0123/vad-web`), but no browser target-speaker model was found. | Rejects the friend's voice, not the fan saying "wow" to the friend | Later |
| **Camera / gaze** (Alexa Conversation Mode, Google Look and Talk) | Alexa: FRR −80% with vision, false wakes from noise −80% (relative only). Google publishes none. | Possible with a webcam, but... | **Gaze is not an option for blind users** | No |
| **Gaze-free physical cues** | n/a | Media Session `play`/`pause` (Chrome 73, Safari 15), plus a `togglemicrophone` action; which headset buttons map to it is unverified. VoiceOver Magic Tap reaching a web page: unverified. AirPods head gestures (iOS 18): OS only, not exposed to the web. | A headset click is the most "blind-native" trigger, if it works | Test on device; bonus only |

- **Accessibility evidence:**
  - Blind users already rely on voice assistants. In a survey of 146 blind and visually impaired people, most used Siri or Alexa and found them helpful, but flagged privacy and misrecognition in noisy places (Oumard et al. 2022).
  - Pradhan et al. (CHI 2018, 16 interviews plus 346 reviews) found discoverability to be the main issue.
  - We found **no study of false-trigger frustration specific to blind users**. The design rule therefore comes from the general literature: a false trigger interrupts the one channel the blind fan has.
- **When unsure, what production systems do:** Alexa's cloud re-check discards speech judged "not intended" silently. Google ends Continued Conversation when it decides you've stopped addressing it. Gemini's "proactive audio" (preview) "can proactively decide not to respond". LiveKit resumes the agent after 2 s if an interruption turns out to be false. **We found no production system that asks "did you mean me?"** Asking it would itself interrupt the match. **Rule:** below confidence, ignore silently, and if the commentary was paused by the speech, resume it (LiveKit-style) after about 1.5–2 s.

### 3. The delay and the agent layout

**3a. What a longer delay buys and what it costs**

| | D = 10 s (today) | D = 20 s | D = 60 s |
|---|---|---|---|
| Versus real life | Faster than UK TV ("around 8-10 seconds" BBC, 2025) to about the same; US broadcast TV ~19 s (Super Bowl LX, 2026) | Like US broadcast TV | Like US streaming apps (Peacock 48 s, YouTube TV 53 s, DirecTV ~60 s; Stats Perform 2026). Worse than BBC iPlayer's ~40 s. |
| In the stadium, or with radio | Usable as "near live" | Borderline | **Unusable.** Luton's 40 s radio delay meant fans "can't keep up with play"; MLB fans on a 30 s radio delay asked for real time (WUSF 2024); NFB resolution 2023-05 |
| Spoilers | Few | Some | Phone alerts, messages, neighbours. 45% of UK adults have had a result spoiled by delay (2024); 35% in 2026; 62% across 7 markets saw a result or reaction first (2026). Scout feeds claim <1–2 s (vendor). |
| LLM on build-up lines | No: 6 s of wall time (file 43 §2). Measured plan→verify→TTS p95 3.56 s (D16) | Yes: DFL's LLM ticker takes 7–12 s per entry | Yes, with retries |
| Planning | Sees the next shot ≤ 10 s ahead: enough for build-ups (LEAD_S 4 s) and "hold that thought" | Sees most of an attack | Sees whole phases, the next stoppage, and the VAR verdict before the ball goes in. More power, and more spoiler surface for the firewall |
| Talk-back | Little room: a 20 s answer means 20 s of match narrated only by catch-up | Some | The match could **wait** for the fan (elastic delay, below) |

- **Our reading:**
  - The benefits that need a 60 s *fixed* delay are small. LLM text fits within about 20 s, and colour lines about the past need no look-ahead at all: they can be written at any time from state ≤ P and slotted into stoppages (`stale_ms`, file 43).
  - The costs land on exactly the users we serve. RNIB fans call lag the biggest technical problem (file 36). A 60 s commentary is also out of sync with a fan's in-stadium or pub reference ("not always synced", RNIB 2022).
- **Elastic delay: the better use of "more time".**
  - Keep D = 10 s as the **floor**. When the fan asks, **pause the listener's playhead** (the crowd holds a neutral bed). The delay grows by the length of the exchange, say to 30 s.
  - Then win it back by **trimming dead-ball time**: shorten restarts and skip the walk-up to a goal kick or throw-in, with a "we're back to live" cue once D is back at the floor.
  - There is plenty of dead ball to trim. Ball-in-play was 55:23 per match in 2025-26 and 56:35 so far in 2026-27 (Opta, 8 Oct 2026), so more than 33 of the regulation 90 minutes are dead ball. Throw-ins average 15.3 s to restart and there are about 36 per match (our arithmetic from 13,615 in 380 games), which is about 9 minutes from throw-ins alone.
  - Elastic delay keeps the floor live-like for fans who need that, and gives the conversation all the time it wants.
  - **Nobody found in 36/42/47 does this** (novelty claim unverified beyond those files).
  - In the static judge replay this is cheap: pause `ReplayClock` during an answer. Live, it needs the truth buffer to hold up to D_max (60 s) and a trim planner. A cap is needed: past D_max, fall back to today's catch-up.
- **If one fixed number must be picked for a live product:** D = 10 s with templated build-ups (today). Go to **D ≈ 20 s** only when LLM-written build-ups ship. Use 60 s only as an opt-in "Deep listen" for at-home or replay, with a "mute your score alerts" tip.

**3b. Agent layout**

```
                truth t                                   listener playhead P = t − D(t)   (D(t) ≥ 10 s, elastic later)
 Ingest ──▶ Interpret (code) ──▶ Director (LLM, sees [P, P+D]) ──▶ Commentator (templates; LLM colour from ≤ P only)
   events     signals, xG,          build-up level, lead, hold,          │
   ball       win prob,             next-stoppage forecast               ▼
   track      suspense              (says THAT, never WHAT)        Verifier (code: truth, spoiler, numbers)
                                                                        │
                                                                        ▼
                                                               TTS render (Azure HD) ──▶ cue track (tc_in, priority, stale_ms)
                                                                                                │
 ┌──────────────────────────── per listener, in the browser + relay ──────────────────────────┐ ▼
 │  FLOOR MANAGER (code)  owns the one audio floor: P0 calls > fan speech > answer > build-up > play-by-play > colour │
 │     │  barge-in, pause/duck, hold, deferred answers, resume/drop rules, catch-up, (later) elastic delay           │
 │     ▼                                                                                                             │
 │  HEARD LEDGER (code)  every line/answer actually played: id, start, played_ms, cut_at_word                      │
 │     │  ▲                                                                                                          │
 │     ▼  │                                                                                                          │
 │  Q&A agent (Voice Live, gpt-realtime-mini)  tools clamped to P; context = PERSONA + [LISTENER AT] + [AIRED…]      │
 └───────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

| Agent | Kind | Sees | New vs today |
|---|---|---|---|
| Ingest, Interpret | Code | Truth up to t | none |
| Director | LLM (Foundry gpt-5-mini) + rules fallback | [P, P+D] | Later: also a **next-stoppage forecast** for the Floor Manager. A boolean "stoppage ≥ 25 s within N s" says THAT, like hold-that-thought. |
| Commentator | Templates (+ LLM colour from state ≤ P) | Present facts + plan | Colour lines carry `stale_ms` and are only placed into stoppages |
| Verifier | Code | Lines | Later: also checks live-answer numbers against the tool results of that turn |
| **Floor Manager** | **Code, deterministic.** Must react in milliseconds, which rules out an LLM. | Cue track (priorities), Voice Live events, button/VAD, Director's stoppage flag | **New.** Today these rules are spread over `ask.ts`, `live-ask.ts` and `commentary-track.ts`. |
| **Heard Ledger** | Code (browser records, relay reads) | What actually played | **New.** Today the relay sends only `[LISTENER AT mm:ss]`. |
| Q&A agent | Voice Live | Tools ≤ P, ledger | Gets `[AIRED]` items; `auto_truncate: true` |

- **How live answers stay consistent with what the fan has heard:**
  1. **One fact source.** Commentary and answers both come from the same event ids and tools (exists: B's `audiostands.qa`, the truth check, 0 spoiler leaks in D16 and D17).
  2. **One clock.** Tools are clamped to the fan's P, never extrapolated (exists, D17).
  3. **One memory of what was said.** The Heard Ledger is fed to Voice Live as labelled system items (`[AIRED 63:12] …`; file 40 §4 already proposed this, unbuilt). Interrupted answers are cut to what was heard (`auto_truncate`, or `truncate` with the played milliseconds, or word timestamps). The model then won't say "as I said" about something the fan never heard. Keep the window small: it is billed as input (file 40).
  4. **Promises are state, not prose.** "I'll come back to that at the next break" is a deferred-answer entry in the Floor Manager with a TTL, not something the LLM must remember.
  5. **One persona and voice** (exists: Brian HD for both, D13 and D17).

### 4. Sharing the audio between commentary and talk-back

- **Pause, don't duck, the commentary.**
  - Guerreiro & Gonçalves (ASSETS 2014, 23 visually impaired participants, HRTF-separated voices): 20/23 identified the target with two talkers in every trial, but **only 7 reported more than half the content**. Spatial position helped; a different voice didn't.
  - A follow-up (ASSETS 2015) found two voices workable for *skimming* text, which is not our case.
  - So a commentary under an answer would cost the fan both.
  - **Exception:** a P0 call (goal, penalty, red card, VAR verdict) preempts the answer. `response.cancel` plus a local stop, play the call, then "want the rest of that answer?" (file 40 §1).
- **Duck the crowd harder while the fan speaks and while the answer plays.**
  - Torcoli et al. (JAES 2019, 22 listeners) found commentary needs **at least 15 LU over ambience** and 10 LU over music, and non-experts wanted 4 LU more than experts.
  - WCAG 1.4.7 (AAA) asks for background "at least 20 decibels lower" than speech.
  - Today's Ask duck is −12 dB (`ask.ts` `DUCK_DB`), with B's 2 kHz dip under commentary lines (D12). We found no source for the "+12 dB speech rule" cited in files 38 and D12.
  - Suggest about −18 dB during Q&A (ours, tune by ear). A lower crowd also helps the VAD and the transcription.
- **Fade out fast, never hard-cut.** Use an 80–150 ms gain ramp to avoid a click (ours). Stop answer playback locally on any stop, as the Microsoft samples do.
- **Resume rules for pre-rendered lines** (ours). In human dialogue people either resume, "repeat the last utterance" or "summarize the critical information" (Yang, Heeman & Kun 2011). Map those to:
  - **Restart from the start** of the interrupted line if its `tc_in` is within its `stale_ms` of the playhead and no newer line has started. This is the "repeat" option.
  - **Drop it** otherwise, and let the catch-up summarise (exists). This is the "summarize" option.
  - **Never resume mid-sentence after a question.** Today's `commentary-track.ts` does, because it keeps the line in sync with the playhead for pause and seek. After a 10 s answer that means half a sentence, or a line that has already ended.
- **Catching up** (exists: `catch_up`, at most 2 top events). Add the score and clock if a goal happened or the exchange lasted over about 20 s, and where the ball is now. Ball-first follows RNIB (file 36), and radio practice puts score and time remaining first (practitioner opinion, no official rule found).
- **When to answer now, and when to hold:**

| Question type | While the ball is in play | Why |
|---|---|---|
| Orientation: ball, score, clock, "what just happened?" | **Now**, one breath (≤ ~2 s), then straight back | That's what the fan needs to follow play. RNIB's "massive pause button" fan wanted stats on demand. |
| Anything, when a build-up is due within 8 s | "Hold that thought" (exists), then answer | Says THAT, never WHAT |
| Analysis or stats ("how far has 9 run?", "why did they change shape?") | **Defer to the next stoppage of ≥ 25 s** with a 1-line acknowledgement ("At the next break"). TTL 60 s, then answer briefly anyway. | About 110 stoppages a match, mean 20–23 s (World Cup data, Augste & Cordes 2016). Throw-ins average 15.3 s (too short); goal kicks 27.7, corners 33.9, free kicks 33.3, subs 64.3, VAR about 39–64 s per game (Opta and PL data). |
| Fan asks again or says "now" | Answer now | The fan is in charge |

With D = 10 s the Director knows a stoppage only up to 10 s ahead. The Floor Manager therefore waits for the stoppage to *happen* at P (live) or looks it up (replay), and never announces one in advance.

## So what for us

**(a) Recommended design, per question**

1. **Barge-in:** **press-to-interrupt now, voice barge-in later.**
   - Any press of Ask, a keyboard shortcut, or (if it works on device) the headset button stops *all* speech locally within one fade (~0.1 s), cancels a live answer (`response.cancel`), and opens the mic.
   - Turn on `auto_truncate`.
   - Voice barge-in comes later, as an opt-in "hands-free (headphones)" mode. It needs one playback bus, Live-Reference AEC on api-version 2026-07-15, and `interrupt_response` + `remove_filler_words`, with a local `speech_started` → fade-out.
   - Measure press→silence and speech→silence before quoting either.
2. **Addressee:** the explicit trigger stays primary. Later:
   - a 6–8 s follow-up window after each answer, with open and close earcons;
   - a gpt-5-mini "addressed to the commentator?" check biased to ignore;
   - silent ignore plus auto-resume of the commentary when unsure.
   
   No wake word and no speaker enrolment on our stack (unsupported in the JS SDK, and retired respectively).
3. **Delay and structure:**
   - Keep D = 10 s as the floor. Write colour from the past into stoppages.
   - Add the Floor Manager and the Heard Ledger.
   - Elastic delay (the match waits for the fan) is the headline "next" feature. 60 s fixed only as an opt-in "Deep listen".
4. **Sharing audio:**
   - Pause the commentary and duck the crowd to about −18 dB.
   - Restart-or-drop, never mid-sentence.
   - Orientation answers now; analysis at the next stoppage of ≥ 25 s.
   - A P0 call preempts the answer.

**(b) What fits before 27 Oct, and what comes later.** The schedule is the limit, not the tech. `docs/REMAINING.md` fills Sun 25 with the listening test and walkthroughs, Mon 26 with video takes, and Tue 27 with submission. Any change to the live path must be deployed and re-evaluated **before Monday's takes**.

| When | Item | Effort (ours) | Risk | Files |
|---|---|---|---|---|
| **Before Sun noon** | Press Ask during an answer = stop + listen (check the `busy` path), plus one keyboard shortcut. Announce it in the Ask button's help text. | 1–2 h | Low, client only | `ask.ts`, `live-ask.ts`, `main.ts` |
| **Before Sun noon** | After an Ask, restart-or-drop the interrupted line, never mid-sentence | 1 h + test | Low | `commentary-track.ts` |
| Before Sun noon, optional | Ask duck −12 → about −18 dB (by ear, with the `?mix=1` mixer) | 15 min | Low | `ask.ts` |
| Optional, only if the relay can be redeployed and the 31-question eval re-run by Sun evening | `auto_truncate: true`, plus `[AIRED mm:ss]` items for cue lines aired since the last question (from the bundle, ≤ P) | 2–3 h | Medium (live path, persona drift) | `relay/voicelive.py` |
| **Pitch wording** (no code) | "Interrupt any time with one press. The commentator stops at once, answers from what you've heard, catches you up, and never spoils what's coming." Name Voice Live, `interrupt_response`/`auto_truncate` and Live-Reference AEC as the path to hands-free. **Don't claim voice barge-in or hands-free.** | 15 min | none | README, SUBMISSION, video script |
| After | Media Session headset toggle (needs device tests) | 2 h | | |
| After | One playback bus + Live-Reference AEC + open-mic barge-in (headphones) | 1–2 days | High | |
| After | Follow-up window + addressee gate + silent ignore | 1 day | Medium | |
| After | Floor Manager as one module; Heard Ledger with word timestamps | 1–2 days | Medium | |
| After | Elastic delay (replay first, then live trim planner) | 2–3 days | Medium | |
| After | LLM colour into stoppages; D = 20 s for LLM build-ups | 1–2 days | Medium | |

**(c) Risks for a live demo**

| Risk | Where it bites | Mitigation |
|---|---|---|
| **False triggers** | An open mic hears the commentator on laptop speakers, a TV in the room, the screen reader's own voice, or the fan reacting to a friend. Smart speakers misfire about 0.95 times/hour even on TV audio (PoPETs 2020). | Push-to-talk in the judge build; earcon before the mic opens (exists, 250 ms); no open mic on the deployed site. |
| **Echo** | Server echo cancellation can't remove our crowd or pre-rendered lines. Chrome's AEC covers same-page audio in one test only. iOS crackle bug with an echo-cancelled mic. | Record takes with headphones (closed if possible). Keep the mic closed while our audio plays. Live-Reference AEC only after the deadline. |
| **Latency** | Cold relay > 30 s (D17). The per-IP cap fired during our own tests. Bluetooth adds hundreds of ms. First audio p95 1.82 s. | Wake `/health` before takes (REMAINING step 11). Wired headphones for takes. Show the latency badge. One question per take (file 42). |
| **Barge-in stop feels slow** | Waiting on the server's VAD before stopping local audio | Stop locally on the press, before any network call |
| **Talking over a goal** | An answer running into a P0 moment | Hold that thought (exists); P0 preempts the answer |
| **Mid-sentence resume** | Half a pre-rendered line after an answer sounds broken, in the video too | Fix before takes (table above) |

## Reuse: code & links

**a) Session settings to add after the deadline** (the Live-Reference AEC fields are from the how-to. Whether our Python SDK accepts `reference_source` is unverified. Needs api-version `2026-07-15`.)

```python
# relay/voicelive.py session_update(): changes only
"input_audio_format": "pcm16",
"input_audio_echo_cancellation": {"type": "server_echo_cancellation",
                                  "reference_source": "client", "channels": 2},   # mic ch0, our mix ch1
"turn_detection": {"type": "azure_semantic_vad", "silence_duration_ms": 500,
                   "remove_filler_words": True, "interrupt_response": True,
                   "auto_truncate": True},                                         # keep only what was heard
"output_audio_timestamp_types": ["word"],                                          # cut points for the Heard Ledger
```

**b) Floor Manager core (TypeScript, a sketch; ours)**

```ts
type Owner = 'none' | 'fan' | 'answer' | 'call' | 'line';
const RANK: Record<Owner, number> = { none: 0, line: 1, answer: 2, fan: 3, call: 4 };   // P0 calls outrank all
const FADE_S = 0.1;

export class FloorManager {
  owner: Owner = 'none';
  deferred: { q: string; until: number }[] = [];
  constructor(private ctx: AudioContext, private bus: { speech: GainNode; crowd: GainNode },
              private stopLine: () => number | null,           // returns the cut line's cue index, or null
              private stopAnswer: () => void, private openMic: () => void) {}

  /** Button, key, headset, or (later) a local speech_started. Never waits for the network. */
  bargeIn(now: number) {
    if (this.owner === 'call') return;                        // let a goal call finish; queue the question
    const t = this.ctx.currentTime;
    this.bus.speech.gain.setTargetAtTime(0, t, FADE_S / 3);   // ~95% down in one fade
    this.bus.crowd.gain.setTargetAtTime(Math.pow(10, -18 / 20), t, 0.05);
    const cut = this.stopLine();
    if (this.owner === 'answer') this.stopAnswer();           // + response.cancel in the relay
    this.owner = 'fan';
    this.openMic();
    return { cut, at: now };
  }

  /** Restart-or-drop: never resume a pre-rendered line mid-sentence after a question. */
  static resumeIndex(cut: number | null, cueStart: (i: number) => number, staleS: (i: number) => number,
                     newerStarted: boolean, playhead: number): number | null {
    if (cut === null || newerStarted) return null;
    return playhead - cueStart(cut) <= staleS(cut) ? cut : null;   // null = drop, the catch-up covers it
  }
}
```

**c) Links**
- Live-Reference AEC browser sample: https://github.com/microsoft-foundry/voicelive-samples/tree/main/javascript/live-reference-aec
- Voice Live quickstarts (`skipPendingAudio` on `speech_started`): https://github.com/microsoft-foundry/voicelive-samples
- Browser VAD (Silero on onnxruntime-web), if we ever stop locally on voice: https://github.com/ricky0123/vad (licence not checked)

## Sources

All accessed 24 Oct 2026.

**Microsoft and other vendors' docs**
- Microsoft Learn, How to use the Voice Live API (turn detection table, echo cancellation, Live-Reference AEC, audio timestamps), ms.date 8 Oct 2026 — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live-how-to
- Microsoft Learn, Voice Live API reference (events, `end_of_utterance_detection`, `truncate`), updated 24 Sep 2026 — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live-api-reference-2025-10-01
- Microsoft Learn, Voice Live with WebRTC, ms.date 29 Sep 2026 — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live-webrtc
- microsoft-foundry/voicelive-samples (quickstarts; live-reference-aec added 4 Aug 2026) — https://github.com/microsoft-foundry/voicelive-samples
- Microsoft Learn, Custom keyword basics (JavaScript: keyword recognition unsupported), ms.date 25 Feb 2026 — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/custom-keyword-basics?pivots=programming-language-javascript
- Microsoft Learn, Keyword recognition overview (no FA/FR figures), ms.date 25 Feb 2026 — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/keyword-recognition-overview
- Azure Speaker Recognition retirement on 30 Sep 2025 (notice 26 Sep 2024) — https://mc.merill.net/message/AZ-azure-ai-speaker-recognition-retirement
- W3C Media Capture and Streams (editor's draft, `echoCancellation` "all"/"remote-only") — https://w3c.github.io/mediacapture-main/
- Chrome 141 release notes (EchoCancellationMode) — https://developer.chrome.com/release-notes/141
- Zoom developer forum, Chrome-wide AEC version gate, 4 Aug 2026 (secondary) — https://devforum.zoom.us/t/issupportchromewideaec-sniffs-browser-name-version-breaking-echo-cancellation-on-microsoft-edge/145288
- Community test of Chrome echo cancellation modes, 23 Oct 2026 (single tester) — https://qiita.com/ntaka329/items/df8189f1be86b59e8bba
- OpenAI, Realtime conversations guide (truncate, interruptions) — https://developers.openai.com/api/docs/guides/realtime-conversations
- OpenAI, Realtime VAD guide (semantic_vad eagerness) — https://developers.openai.com/api/docs/guides/realtime-vad
- K. Kramer, "The Realtime API", latent.space, Nov 2024 — https://latent.space/p/realtime-api
- LiveKit, Adaptive interruption handling, 19 Mar 2026 (vendor) — https://livekit.com/blog/adaptive-interruption-handling
- LiveKit, turn handling options (`false_interruption_timeout`) — https://docs.livekit.io/reference/agents/turn-handling-options
- Daily, Smart Turn v3.1, 3 Dec 2025 (vendor) — https://www.daily.co/blog/improved-accuracy-in-smart-turn-v3-1/
- Deepgram changelog, Flux, 2 Oct 2025 (vendor) — https://developers.deepgram.com/changelog/2025/10/2
- Google, Gemini Live API guide (proactive audio), updated 18 Sep 2026 — https://ai.google.dev/gemini-api/docs/live-guide

**Addressee and directed-speech detection research**
- Mallidi et al., Device-directed utterance detection, Interspeech 2018 — https://arxiv.org/abs/1808.02504
- Wagner et al., Multimodal data and resource efficient device-directed speech detection with large foundation models, 6 Dec 2023 — https://arxiv.org/html/2312.03632v1
- Apple ML Research, multi-signal LLM device-directed speech detection, Mar 2024 — https://machinelearning.apple.com/research/llm-device-directed-speech-detection
- Rudovic et al., Device-directed speech detection for follow-up conversations using LLMs, 4 Nov 2024 — https://arxiv.org/html/2411.00023v2
- Inoue et al., LLM addressee recognition in multi-party conversation, IWSDS 2025 — https://arxiv.org/pdf/2501.16643
- Amazon Science, Alexa Conversation Mode, 18 Nov 2021 — https://amazon.science/blog/new-alexa-feature-enables-natural-multiparty-interactions
- Google Nest help, Look and Talk — https://support.google.com/googlenest/answer/11410414
- Google Assistant help, Continued Conversation — https://support.google.com/assistant/answer/10004407
- Voicebot.ai, Alexa Follow-Up Mode, 11 Mar 2018 — https://voicebot.ai/2018/03/11/amazon-introduces-alexa-follow-mode-streamline-user-interactions/
- Amazon letter to US senators on discarding audio not intended for Alexa, 27 Jul 2018 — https://www.coons.senate.gov/imo/media/doc/Response%20Letter%20-%20Senators%20Flake%20Coons%207-27-2018.pdf
- Ding et al., Personal VAD, Odyssey 2020 — https://arxiv.org/abs/1908.04284

**Wake words**
- openWakeWord (targets; model licence) — https://github.com/dscripka/openWakeWord
- Home Assistant forum, Picovoice free-tier keys end 30 Jun 2026, 4 Jun 2026 (secondhand) — https://community.home-assistant.io/t/fyi-picovoice-confirmed-free-tier-accesskeys-will-stop-working-after-june-30-2026/1012744
- Dubois et al., smart speaker misactivations, PoPETs 2020 — https://petsymposium.org/popets/2020/popets-2020-0072.php

**Accessibility**
- Oumard et al., "Pardon?", 2022 — https://arxiv.org/abs/2203.05848
- Pradhan, Mehta, Findlater, CHI 2018 — https://doi.org/10.1145/3173574.3174033
- web.dev, Media Session — https://web.dev/articles/media-session
- Apple, AirPods head gestures — https://support.apple.com/guide/airpods/devb2c431317/web

**Broadcast lag and spoilers**
- The Desk, Stats Perform Super Bowl LX latency, 9 Feb 2026 — https://thedesk.net/2026/02/stats-perform-phenix-latency-super-bowl-lx/
- SVG, Stats Perform 2026 Super Bowl latency report, 11 Feb 2026 — https://www.sportsvideo.org/2026/02/11/stats-perform-2026-super-bowl-latency-report/
- Broadcast, BBC iPlayer low-latency trial, 5 Jun 2025 — https://www.broadcastnow.co.uk/tech/bbc-iplayer-launches-low-latency-streaming-trial/5205759.article
- Uswitch / Opinium, delay spoilers survey, 12 Jun 2024 — https://www.uswitch.com/media-centre/2024/06/Match-Delay-almost-half-Brits-report-sports-spoilers-neighbours-phone-due-broadband-lag/
- Advanced Television, Uswitch 2026 (35%), 10 Jun 2026 — https://www.advanced-television.com/?p=286508
- Advanced Television, Big Blue Marble survey, 3 Sep 2026 — https://www.advanced-television.com/2026/09/03/survey-14-mull-switching-provider-over-delayed-sports-streaming/

**Blind fans and lag**
- Level Playing Field, Luton Town audio-descriptive commentary, 4 May 2017 — https://www.levelplayingfield.org.uk/news-item/audio-descriptive-commentary-at-luton-town-proving-to-be-a-success/
- WUSF, radio delay leaves blind MLB fans behind, 4 Oct 2024 — https://www.wusf.org/2024-10-04/the-audio-delay-on-radio-broadcasts-of-mlb-games-leaves-blind-fans-behind
- NFB Resolution 2023-05 and letter to the leagues (full text not opened, 403) — https://nfb.org/node/15471 · https://nfb.org/node/15677
- RNIB, first focus group on accessibility of football broadcasts, 7 Apr 2022 — https://media.rnib.org.uk/documents/RNIB_first_focus_group_on_accessibility_of_football_broadcasts_2022.pdf

**AI in live sport**
- AWS, Bundesliga generative-AI live ticker (7–12 s), 9 Jul 2024 — https://aws.amazon.com/blogs/media/revolutionizing-fan-engagementcer-bundesliga-generative-ai-powered-live-commentary/
- IBM, US Open 2025 Match Chat, 18 Aug 2025 — https://newsroom.ibm.com/2025-08-18-ibm-and-the-usta-roll-out-ai-powered-fan-experiences-for-2025-us-open

**Listening to two voices, ducking, resuming**
- Guerreiro & Gonçalves, Text-to-Speeches, ASSETS 2014 (secondary summary) — https://doi.org/10.1145/2661334.2661367
- Kidd et al., spatial release from masking, JASA 2010 — https://pmc.ncbi.nlm.nih.gov/articles/PMC2981113
- Torcoli et al., preferred background levels for commentary, JAES 67(12) 2019 — https://cris.fau.de/publications/234640600
- W3C, Understanding WCAG 2.2 SC 1.4.7 — https://www.w3.org/WAI/WCAG22/Understanding/low-or-no-background-audio.html
- Yang, Heeman & Kun, multi-tasking dialogue interruptions, Computational Linguistics 37(1), Mar 2011 — https://aclanthology.org/J11-1004/

**Stoppages**
- Opta / The Analyst, Premier League ball in play and restart times, 8 Oct 2026 — https://theanalyst.com/articles/premier-league-rules-throw-ins-goal-kicks-ball-in-play
- Refsplaining, VAR delay per game (official PL data), 28 Nov 2025 — https://refsplaining.substack.com/p/should-we-set-time-limits-on-var
- Augste & Cordes, game stoppages in World Cup knockouts, IJPAS 16(3) 2016 — https://opus.bibliothek.uni-augsburg.de/opus4/files/76143/IJPAS_Game_stoppages_manuscript.pdf
