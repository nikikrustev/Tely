# Research Library — Index

Research for the "Inside the Game" hackathon (Microsoft × Premier League, Synthetic Match Insights Engine).
It covers the parts almost any of our candidate ideas will need. Every file has the same parts: TL;DR, Findings,
So what for us, Reuse: code & links, and Sources. Context: [Intel pack](../Berbata_Hackathon_Intel.md) ·
[Idea shortlist](../Berbata_Idea_Shortlist.html) · [Idea brainstorm](../Berbata_Idea_Brainstorm.html).

> **Deadline (verified in the official rules, 20 Oct):** submissions close **27 Oct 2026, 23:59 PT** (28 Oct 08:59 Sofia). Registration closes 20 Oct 12:00 PT. See [12](12-judging-criteria-and-rules.md).

## Current focus (20 Oct 2026): "Audio Stands", the blind-fan audio experience (working name)

Brainstorm ideas **20 Home End** (a crowd mix tuned to your club) and **17 Heartbeat** (haptic tension) combined. A blind or
low-vision fan should feel as if they are in the stands: a reactive crowd around them, and an AI commentator who builds
emotion because the pipeline **knows what is coming** (look-ahead / short delay). The fan can **talk to the commentator** and
ask questions at any time. Research for it: 36–42 (in progress), plus 27 (voice), 32 (accessibility), 22 (explanation text),
23 (tension from win probability) and 09 (pressure / chaos).

## For Claude: which file for which job

| Building… | Read |
|---|---|
| **Audio Stands** (blind-fan audio) | 36–42, then 27, 32, 22, 23, 09 |
| Pitch, impact framing, what the sponsor wants | 28 |
| Azure architecture, infra, deploy, Fabric | 01, 17, 21, 30, 34 |
| Synthetic events, tracking, realism, data format | 02, 19, 26 |
| LLM explanations, translation, speech | 03, 22, 27, 35 |
| Overlays, cues, producer console, accessibility | 04, 11, 24, 32 |
| Computer vision, rendered video, grading, GPU serving | 05, 06, 20, 29, 31 |
| Football metrics | 07 xG · 08 xPass/xT · 09 pressure/PPDA · 10 pitch control · 23 win prob · 25 team shape |
| Agent layer / MCP | 18 |
| Submission, video, judging | 12, 13, 14 |
| Competitors | 15, 16 |

## Files

| # | File | One line |
|---|---|---|
| 01 | [01-azure-realtime-pipeline.md](01-azure-realtime-pipeline.md) | Stage-by-stage Azure map; Event Hubs (+ local emulator), ACA worker vs Functions vs Stream Analytics, Web PubSub groups per audience, Cosmos free tier, credits |
| 02 | [02-synthetic-match-data.md](02-synthetic-match-data.md) | CDF/SPADL schemas, why we write our own possession-chain generator, licences of real samples (calibration only), cited realism ranges, tested 53-line generator |
| 03 | [03-foundry-llm-explain.md](03-foundry-llm-explain.md) | Calling Foundry models (v1 API), structured outputs for cues, grounding checks, Translator/Speech (Bulgarian), quotas and cost |
| 04 | [04-overlay-output-formats.md](04-overlay-output-formats.md) | CasparCG/SPX/OGraf template API (update/play/stop), alpha and key/fill via ffmpeg, media-clock sync (rVFC, WebVTT/HLS cues), EBU safe areas, OBS studio, SCTE-35 |
| 05 | [05-cv-auto-eventing.md](05-cv-auto-eventing.md) | Licence-safe CV stack (RF-DETR + `trackers` + `supervision`), the known-camera auto-label trick, rule-based events, SoccerNet metrics, event-F1 grader, Azure GPU |
| 06 | [06-synthetic-broadcast-rendering.md](06-synthetic-broadcast-rendering.md) | Three.js + Playwright lockstep rendering, broadcast camera prior, YOLO auto-labels and homography export, ffmpeg degradations, SoccerSynth prior art |
| 07 | [07-expected-goals-xg.md](07-expected-goals-xg.md) | xG features and cited coefficients, penalty values (Opta 0.79, StatsBomb 0.78), a hand-set logistic xG we sample shots from, linear-SHAP "because" sentences, StatsBomb licence risk |
| 08 | [08-pass-difficulty-xpass-xt.md](08-pass-difficulty-xpass-xt.md) | xPass and a 0–10 pass-difficulty score, Spearman time-to-intercept model, xT value iteration, VAEP, and the risk of using real data |
| 09 | [09-pressure-pressing-ppda.md](09-pressure-pressing-ppda.md) | PPDA (original + provider variants), StatsBomb pressure/counterpress, Opta sequence metrics, Andrienko and Bekkers pressure models, our control/chaos indices, CUSUM change detection |
| 10 | [10-pitch-control-space.md](10-pitch-control-space.md) | Voronoi vs Spearman vs Fernández-Bornn pitch control, tested vectorised NumPy (~1–6 ms/frame, our timing), `space_created` for decoy runs, homography overlay, licences |
| 11 | [11-broadcast-stats-presentation.md](11-broadcast-stats-presentation.md) | Catalogue of on-screen stat formats, the 16 Bundesliga Match Facts, DFL Story Finder, PL/Genius tracking, opt-in data feeds, and a 10-value `layout` grammar with timing rules |
| 12 | [12-judging-criteria-and-rules.md](12-judging-criteria-and-rules.md) | **Official rules:** submit by 27 Oct 23:59 PT; five criteria at 20% each; prizes and four categories; video under 2 min, public repo, working demo; synthetic data only |
| 13 | [13-past-winners-patterns.md](13-past-winners-patterns.md) | Microsoft 2024–26 and sports-tech winners (Big Data Bowl, SoccerNet, Sloan), 10 cited patterns (narrow job, measured result vs ground truth, newest sponsor services, open repo) and anti-patterns |
| 14 | [14-demo-video-and-writeup.md](14-demo-video-and-writeup.md) | Video under 2:00 (rules), judges may not test the demo; structure, OBS/Clipchamp/Azure TTS tooling, 2-minute script extending our 60s one, README template, pitfalls |
| 15 | [15-competitors-cv-overlay-sim.md](15-competitors-cv-overlay-sim.md) | 16 CV/simulator/overlay rivals checked on 20 Oct: high threats Ninety Labs (same pipeline as TwinCast, nothing shipped), Floodlight (shipped, top-down CV), PitchPulse (speed tags); gaps we can own |
| 16 | [16-competitors-front-runners.md](16-competitors-front-runners.md) | Front-runners (126601, Matchroom, 126532) set the bar: public repos, CI, live demos, measured groundedness; table stakes vs common gaps (no overlays on video, no latency or CV accuracy) and 5 ways to beat them |
| 17 | [17-starter-repos-and-samples.md](17-starter-repos-and-samples.md) | No azd template fits: borrow Bicep from 3 live MIT templates + Azure Verified Modules; SWA for front end only; MCP on the worker; licence traps and archived starters; repo skeleton and day-0 commands |
| 18 | [18-agentic-design-for-pipelines.md](18-agentic-design-for-pipelines.md) | What the rules reward for agentic design; Director/Explainer-via-Stats-MCP/code Verifier/HITL take-hold design off the hot path; MCP SDK v2 (`MCPServer`) and Agent Framework 1.22 gotchas; tracing and evals |
| 19 | [19-realistic-player-movement.md](19-realistic-player-movement.md) | Rule-based steering model (formation anchor, role behaviours, pressing triggers, OU jitter, accel caps) that lifts distance from ~4 to ~10 km/player; our measured speed bands, sprints, team shape vs published ranges; 84-line NumPy class |
| 20 | [20-ground-truth-grader-and-calibration.md](20-ground-truth-grader-and-calibration.md) | MOTChallenge format and HOTA/IDF1 commands, GS-HOTA, a simpler pitch-metre grader, FIFA EPTS speed method, NBJW/PnLCalib/TVCalib calibration, degradation-sweep design |
| 21 | [21-demo-uptime-cost-and-ops.md](21-demo-uptime-cost-and-ops.md) | Static replay mode as the judge landing page (~$0), 21-day cost arithmetic (~$25–34 minimal stack), availability tests, LLM abuse caps, OIDC CI/CD, freeze at deadline, judge-day runbook |
| 22 | [22-explanation-generation-patterns.md](22-explanation-generation-patterns.md) | Templates vs LLM on facts (RotoWire, Thomson & Reiter), wordalisation, salience formula, template → placeholder-locked LLM polish → code verifier → fallback, faithfulness metrics, translate-with-locked-numbers |
| 23 | [23-win-probability-and-momentum.md](23-win-probability-and-momentum.md) | Live win probability (Poisson grid / Skellam, red-card and xG blending), possession value, Bundesliga-style momentum, Brier/RPS/ECE and reliability diagrams for Called It; tested on toy data |
| 24 | [24-producer-console-control-path.md](24-producer-console-control-path.md) | Commands as Web PubSub events to a FastAPI webhook (ack via 200 body), dedupe with cmd_id/seq, group-based personalisation, NEXT/TAKE/CLEAR/KILL mapped to playout systems, NTP-style clock sync, tested asyncio cue scheduler, audit log |
| 25 | [25-team-shape-and-tactical-metrics.md](25-team-shape-and-tactical-metrics.md) | FIFA EFI definitions (line height, line breaks, phases), cited shape ranges (length 31–46 m, area ~900 m²), SkillCorner phase rules, formation matching (Hungarian) and change detection; tested code |
| 26 | [26-cdf-spadl-data-tooling.md](26-cdf-spadl-data-tooling.md) | Target CDF v0.3.2 (validator-checked examples that pass), fixes to file 02's examples, CDF→SPADL converter tested with socceraction xT/VAEP, kloppy status, CI validation; pin multimethod<2 |
| 27 | [27-voice-speech-and-audio.md](27-voice-speech-and-audio.md) | Pre-rendered TTS for commentary vs Voice Live (barge-in, function calling) for Chalk Talk; sports styles only on one Mandarin voice; Bulgarian speech in/out limits; prices; Limited Access voice rules; Web Audio ducking and Tone.js tempo |
| 28 | [28-sponsor-goals-and-real-world-impact.md](28-sponsor-goals-and-real-world-impact.md) | What Microsoft and the PL say they want (4 pillars, real-time overlays, native-language Q&A), what already ships (PL Companion, FPL Companion, Premier League+), the gap (PL Studios producer tooling), framings per idea, resource playlists |
| 29 | [29-render-realism-and-sim2real.md](29-render-realism-and-sim2real.md) | Mixamo is out (no redistribution); CC0 Quaternius players + ambientCG grass + Poly Haven HDRIs; Three.js skinned-player gotchas; which randomisations matter (Tobin, SoccerSynth); realism ladder (stop at level 3) |
| 30 | [30-infra-as-code-azd-bicep.md](30-infra-as-code-azd-bicep.md) | One `azd up`: 16 AVM modules with current versions, production defaults to override, 9 verified role GUIDs, azd deploys ACA jobs natively since 1.23.8, low-TPM Foundry deployment, dev vs judge params, postprovision hook (Bicep not yet compiled) |
| 31 | [31-cv-inference-serving.md](31-cv-inference-serving.md) | RF-DETR → ONNX/TensorRT export gotchas, sourced T4/L4/CPU speeds, batch-then-replay recommendation (ball tiling breaks real time), ACA GPU vs Azure ML costs, CUDA 12 vs 13 driver trap, cold start, Dockerfile |
| 32 | [32-accessible-responsive-viewer.md](32-accessible-responsive-viewer.md) | WCAG 2.2 for live overlays (contrast plates, hide/freeze, live captions, audio description), tested colour-blind team-colour checker, BBC subtitle rules, throttled aria-live announcer, phone layout, Playwright+axe CI |
| 33 | [33-synthetic-possession-value.md](33-synthetic-possession-value.md) | Ran it: 200 synthetic matches → SPADL → socceraction xT + VAEP (our metrics: VAEP scores AUC 0.75, sane xT grid); found 2 generator bugs in 02; uses for momentum, Relay Credit (VAEP = Shapley), Ghost Team, Called It baseline |
| 34 | [34-fabric-real-time-intelligence.md](34-fabric-real-time-intelligence.md) | Verdict: optional half-day side quest. Judges can't open Fabric dashboards; trial needs a work email; F2 cost; FabricTool retires 6 Nov 2026 mid-judging; side consumer-group tap; ready KQL for possession/PPDA/speeds; Activator rule |
| 35 | [35-multilingual-pipeline.md](35-multilingual-pipeline.md) | Translate templates offline, fill slots at runtime; EN+BG+ES+AR demo; Translator 2026-06-06 details and bg/ar limits; ICU plurals/ordinals tested; quality-score licence traps (CometKiwi NC vs MetricX Apache); RTL overlays; 40-term EN→BG glossary |
| 36 | [36-blind-fans-and-audio-description.md](36-blind-fans-and-audio-description.md) | What blind fans want (RNIB 2022–23: ball-first, real-time, one voice), lag as the top pain, UEFA/CAFE guidance, what exists (Sky's new descriptive commentary, Touch2See, OneCourt, FIFA 2026), the gap (no Q&A, no detail control, no synced crowd), design principles, ethical testing plan |
| 37 | [37-spatial-audio-in-the-browser.md](37-spatial-audio-in-the-browser.md) | Native Web Audio is enough (HRTF PannerNode, Convolver), Firefox listener fallback, halfway seat default, rattle-like ball sound, earcon rules (Sonification Handbook), no web head tracking, iOS audioSession, Bluetooth latency, synthetic stadium IR, typed 126-line AudioStands module |
| 38 | [38-reactive-crowd-atmosphere.md](38-reactive-crowd-atmosphere.md) | How EA/Sky faked crowds in 2020, home-advantage research, spoiler-safe crowd state machine {excitement, valence, danger} (toy-tested, flips for away end), Web Audio CrowdEngine (granular bed, synthetic chants, ducking), CC0 Freesound packs, no real chants (legal), mixing levels |
| 39 | [39-anticipatory-emotional-commentary.md](39-anticipatory-emotional-commentary.md) | Commentator runs a 10 s delay behind the truth buffer (framed as broadcast delay), suspense/surprise from win-prob (Ely et al., PL audience evidence), anti-spoiler cap, prosody evidence for build-ups and goal calls, priority planner, SSML for EN HD + BG, tested on toy data |
| 40 | [40-conversational-commentator.md](40-conversational-commentator.md) | Ask toggle button (VoiceOver-friendly), Voice Live WebRTC with a server relay for tool calls, six read-only tools that only see the delayed playhead (no spoilers), same voice as commentary, Bulgarian STT limits, ~$0.02/question, code for relay and browser |
| 41 | [41-haptics-match-tension.md](41-haptics-match-tension.md) | iOS web can't vibrate; Firefox Android silently fails; rhythm-only tacton vocabulary (heartbeat, attack, shot, goal), gamepad rumble, audio-clock sync ~20 ms early, anti-fatigue cap, real tactile products, typed haptics.ts + AHAP for later native |
| 42 | [42-audio-competitors-and-demo.md](42-audio-competitors-and-demo.md) | Audio rivals with evidence: Ninety Labs' audio-description PRs and Matchday Companion's Voice Live Q&A are the real threats; white space (anticipation, crowd, haptics, blind-user testing); muted/laptop-speaker demo craft; Foundry category; agents as a spoiler firewall |

## In progress

43 Audio Stands architecture on the hero stack · 44 accounts, quotas and setup checklist · 45 Agent Framework orchestration for Audio Stands · 46 Copilot, GitHub CLI and Azure MCP workflow · 47 prior art outside the hackathon

## Next topics (queue)

Priority 1 (build/tech)
- Priority vs Flex processing on Global Standard for live vs offline calls (from 03)
- Deterministic offline overlay render: OGraf non-real-time mode, Puppeteer virtual time, as an ACA job (from 04)
- SCTE-35 generation in Python (`threefive`) for Safe Break; NDI-with-alpha from OBS (DistroAV) for a live key/fill demo (from 04)
- Animated architecture diagram and readable on-screen agent traces for the video (from 14)
- Score our own demo against the Agent Academy 2026 rubric before submitting (from 13)
- EPTS certification reports: real provider speed/position error per velocity band as a benchmark (from 20)
- A permissive (MIT/Apache) pitch-keypoint detector fine-tuned on our renders, to avoid GPL calibration repos (from 20)
- Foundry Toolbox / hosted Agent Framework agents for a "Best Use of Foundry" angle (from 18)
- Matchroom's hidden-truth evaluation (`scripts/evaluate`, `truth.json`) as a template for our grader (from 16)
- `rejcom/inside-the-game-insights` `demo/make_video.py`: automated demo-video generation (from 16)
- Live added-time estimation for win probability (from 23)
- Hash-and-lock predictions at issue so Called It is tamper-evident (from 23)
- Error-annotation report for our generated text (Thomson & Reiter corpus as template) (from 22)
- Static Web Apps auth/roles to protect /api/negotiate (from 24)
- Live HLS media-clock sync (PROGRAM-DATE-TIME vs server clock) for overlays on a delayed stream (from 24)
- Event-only fallback for line breaks and blocks when there is no tracking (from 25)
- Offside-line graphics (Genius, FIFA SAOT) as a precedent for drawing line height (from 25)
- Lens-distortion pass that also distorts labels and homography (from 29)
- Crowd and ad-board distractor generator for detector robustness (from 29)
- Premier League Studios tech stack and graphics vendor, to aim our key/fill output at what they use (from 28)
- Microsoft's PL Companion customer story as a reference multi-agent pattern judges will recognise (from 28)
- Fatigue model (late-match drop in high-intensity running) as a Realism Bench check (from 19)
- Calibrate speed bands and accelerations against SkillCorner open data (MIT) (from 19)
- Hands-on test of gpt-realtime-translate for English → Bulgarian live dubbing (from 27)
- Royalty-free / procedural crowd audio for Home End (from 27)
- Cross-file id checks and a CDF conformance badge for Realism Bench (from 26)

Priority 4 (competitors)
- Study Floodlight's cue-sheet compiler (priorities, slot exclusivity, expiry) against our cue contract (from 15)
- Re-check Ninety Labs, PlayerLens 3D and PitchPulse closer to the deadline (from 15)

Priority 2 (football domain)
- Post-shot xG / xGOT for synthetic shots: sampling where shots end up on goal (Keeper Brain) (from 07)
- DFL AI Live Ticker (Bedrock) and Genius skeletal-tracking graphics as precedents for live multilingual text and speed tags (from 11)
- Bayesian online change-point detection for calibrated "the game has changed" probabilities (from 09)
- Run-timing counterfactual (CRSV, open-starlab spaceEval) and BIMOS for Ghost Team / Decoy Credit (from 10)
