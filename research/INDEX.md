# Research Library — Index

Research for the "Inside the Game" hackathon (Microsoft × Premier League, Synthetic Match Insights Engine).
It covers the parts almost any of our candidate ideas will need. Every file has the same parts: TL;DR, Findings,
So what for us, Reuse: code & links, and Sources. Context: [Intel pack](../Berbata_Hackathon_Intel.md) ·
[Idea shortlist](../Berbata_Idea_Shortlist.html) · [Idea brainstorm](../Berbata_Idea_Brainstorm.html).

> **Deadline (verified in the official rules, 20 Oct):** submissions close **27 Oct 2026, 23:59 PT** (28 Oct 08:59 Sofia). Registration closes 20 Oct 12:00 PT. See [12](12-judging-criteria-and-rules.md).

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
| 11 | [11-broadcast-stats-presentation.md](11-broadcast-stats-presentation.md) | Catalogue of on-screen stat formats, the 16 Bundesliga Match Facts, DFL Story Finder, PL/Genius tracking, opt-in data feeds, and a 10-value `layout` grammar with timing rules |
| 12 | [12-judging-criteria-and-rules.md](12-judging-criteria-and-rules.md) | **Official rules:** submit by 27 Oct 23:59 PT; five criteria at 20% each; prizes and four categories; video under 2 min, public repo, working demo; synthetic data only |
| 14 | [14-demo-video-and-writeup.md](14-demo-video-and-writeup.md) | Video under 2:00 (rules), judges may not test the demo; structure, OBS/Clipchamp/Azure TTS tooling, 2-minute script extending our 60s one, README template, pitfalls |

## In progress

10 pitch control · 13 past winners · 
15 competitors (CV, simulators, overlays) · 16 competitors (front-runners) · 17 starter repos and samples · 18 agentic design for pipelines · 19 realistic player movement · 20 ground-truth grader and calibration · 21 demo uptime, cost and ops

## Next topics (queue)

Priority 1 (build/tech)
- CDF compliance: settle the validator's v0.3.2 vs paper's v1.0.0 and the exact JSON nesting (from 02)
- Web PubSub event handlers / upstream messages, so Graphics Desk take/hold commands can go from browser to worker (from 01)
- Serving RF-DETR (ONNX/TensorRT) on an ACA serverless T4: cold start, image size, quota on Students/Free Trial (from 01, 05)
- Synthetic-to-real gap: texture, lighting and kit randomisation; low-poly GLTF players with run cycles (from 05, 06)
- Foundry Voice Live / speech-in, speech-out for Chalk Talk and Half-Time Talk (from 03)
- Priority vs Flex processing on Global Standard for live vs offline calls (from 03)
- Deterministic offline overlay render: OGraf non-real-time mode, Puppeteer virtual time, as an ACA job (from 04)
- SCTE-35 generation in Python (`threefive`) for Safe Break; NDI-with-alpha from OBS (DistroAV) for a live key/fill demo (from 04)
- Animated architecture diagram and readable on-screen agent traces for the video (from 14)
- Fabric Real-Time Intelligence (Eventstream/Eventhouse): does it beat our own Python windowing? (from 01)

Priority 2 (football domain)
- Converting synthetic events to SPADL so socceraction xT/VAEP runs unchanged (from 08)
- Calibration and reliability diagrams for xPass/xT/predictions (Called It, Realism Bench) (from 08)
- Rahimian/Sumpter "wordalization" code: regression contributions → words → LLM rewrite, a near-template for Explain (from 07)
- Post-shot xG / xGOT for synthetic shots: sampling where shots end up on goal (Keeper Brain) (from 07)
- FIFA EFI metric definitions (line breaks, receptions behind lines, phases of play) to copy into Interpret (from 11)
- DFL AI Live Ticker (Bedrock) and Genius skeletal-tracking graphics as precedents for live multilingual text and speed tags (from 11)
- Possession value (StatsBomb OBV / Opta PV) as a transparent synthetic "momentum" model (from 09)
- Bayesian online change-point detection for calibrated "the game has changed" probabilities (from 09)
- Team compactness, block height and line-breaking passes from tracking (Opta Vision definitions) (from 09)
- Translator custom glossaries for football jargon in other languages (from 03)
