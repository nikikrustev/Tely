# Research Library — Index

Research for the "Inside the Game" hackathon (Microsoft × Premier League, Synthetic Match Insights Engine).
It covers the parts almost any of our candidate ideas will need. Every file has the same parts: TL;DR, Findings,
So what for us, Reuse: code & links, and Sources. Context: [Intel pack](../Berbata_Hackathon_Intel.md) ·
[Idea shortlist](../Berbata_Idea_Shortlist.html) · [Idea brainstorm](../Berbata_Idea_Brainstorm.html).

> **Deadline (verified in the official rules, 20 Oct):** submissions close **27 Oct 2026, 23:59 PT** (28 Oct 08:59 Sofia). Registration closes 20 Oct 12:00 PT. See [12](12-judging-criteria-and-rules.md).

## For Claude: which file for which job

| Building… | Read |
|---|---|
| Azure architecture, infra, deploy | 01, 17, 21 |
| Synthetic events, tracking, realism | 02, 19 |
| LLM explanations, translation, speech | 03, 22 |
| Overlays, cues, producer console | 04, 11, 24 |
| Computer vision, rendered video, grading | 05, 06, 20 |
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
| 20 | [20-ground-truth-grader-and-calibration.md](20-ground-truth-grader-and-calibration.md) | MOTChallenge format and HOTA/IDF1 commands, GS-HOTA, a simpler pitch-metre grader, FIFA EPTS speed method, NBJW/PnLCalib/TVCalib calibration, degradation-sweep design |
| 21 | [21-demo-uptime-cost-and-ops.md](21-demo-uptime-cost-and-ops.md) | Static replay mode as the judge landing page (~$0), 21-day cost arithmetic (~$25–34 minimal stack), availability tests, LLM abuse caps, OIDC CI/CD, freeze at deadline, judge-day runbook |
| 23 | [23-win-probability-and-momentum.md](23-win-probability-and-momentum.md) | Live win probability (Poisson grid / Skellam, red-card and xG blending), possession value, Bundesliga-style momentum, Brier/RPS/ECE and reliability diagrams for Called It; tested on toy data |

## In progress

19 realistic player movement · 22 explanation generation patterns · 24 producer console control path · 25 team shape and tactical metrics · 26 CDF/SPADL data tooling · 27 voice, speech and audio · 28 sponsor goals and real-world impact · 29 render realism and sim-to-real

## Next topics (queue)

Priority 1 (build/tech)
- Serving RF-DETR (ONNX/TensorRT) on an ACA serverless T4: cold start, image size, quota on Students/Free Trial (from 01, 05)
- Priority vs Flex processing on Global Standard for live vs offline calls (from 03)
- Deterministic offline overlay render: OGraf non-real-time mode, Puppeteer virtual time, as an ACA job (from 04)
- SCTE-35 generation in Python (`threefive`) for Safe Break; NDI-with-alpha from OBS (DistroAV) for a live key/fill demo (from 04)
- Animated architecture diagram and readable on-screen agent traces for the video (from 14)
- Score our own demo against the Agent Academy 2026 rubric before submitting (from 13)
- EPTS certification reports: real provider speed/position error per velocity band as a benchmark (from 20)
- A permissive (MIT/Apache) pitch-keypoint detector fine-tuned on our renders, to avoid GPL calibration repos (from 20)
- One Bicep/azd module for the whole judge environment (SWA Standard + linked ACA, Key Vault, low-TPM Foundry deployment, App Insights) (from 21)
- Accessibility and phone-width checks for the viewer, since judges may open the link on a phone (from 21)
- Foundry Toolbox / hosted Agent Framework agents for a "Best Use of Foundry" angle (from 18)
- AVM Bicep for the full stack with exact keyless role names (from 17)
- Deploying ACA jobs under azd (no job host type): hooks vs azd deploy vs Actions (from 17)
- Matchroom's hidden-truth evaluation (`scripts/evaluate`, `truth.json`) as a template for our grader (from 16)
- `rejcom/inside-the-game-insights` `demo/make_video.py`: automated demo-video generation (from 16)
- Live added-time estimation for win probability (from 23)
- Hash-and-lock predictions at issue so Called It is tamper-evident (from 23)
- Fabric Real-Time Intelligence (Eventstream/Eventhouse): does it beat our own Python windowing? (from 01)

Priority 4 (competitors)
- Study Floodlight's cue-sheet compiler (priorities, slot exclusivity, expiry) against our cue contract (from 15)
- Re-check Ninety Labs, PlayerLens 3D and PitchPulse closer to the deadline (from 15)

Priority 2 (football domain)
- Post-shot xG / xGOT for synthetic shots: sampling where shots end up on goal (Keeper Brain) (from 07)
- DFL AI Live Ticker (Bedrock) and Genius skeletal-tracking graphics as precedents for live multilingual text and speed tags (from 11)
- Bayesian online change-point detection for calibrated "the game has changed" probabilities (from 09)
- Run-timing counterfactual (CRSV, open-starlab spaceEval) and BIMOS for Ghost Team / Decoy Credit (from 10)
- Synthetic EPV/OBSO grid fitted on our generator so EPV × pitch control ships without real-data risk (from 10)
- Translator custom glossaries for football jargon in other languages (from 03)
