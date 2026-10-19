# Research Library — Index

Research for the "Inside the Game" hackathon (Microsoft × Premier League, Synthetic Match Insights Engine).
It covers the parts almost any of our candidate ideas will need. Every file has the same parts: TL;DR, Findings,
So what for us, Reuse: code & links, and Sources. Context: [Intel pack](../Berbata_Hackathon_Intel.md) ·
[Idea shortlist](../Berbata_Idea_Shortlist.html) · [Idea brainstorm](../Berbata_Idea_Brainstorm.html).

## Files

| # | File | One line |
|---|---|---|
| 01 | [01-azure-realtime-pipeline.md](01-azure-realtime-pipeline.md) | Stage-by-stage Azure map; Event Hubs (+ local emulator), ACA worker vs Functions vs Stream Analytics, Web PubSub groups per audience, Cosmos free tier, credits |
| 02 | [02-synthetic-match-data.md](02-synthetic-match-data.md) | CDF/SPADL schemas, why we write our own possession-chain generator, licences of real samples (calibration only), cited realism ranges, tested 53-line generator |
| 03 | [03-foundry-llm-explain.md](03-foundry-llm-explain.md) | Calling Foundry models (v1 API), structured outputs for cues, grounding checks, Translator/Speech (Bulgarian), quotas and cost |
| 04 | [04-overlay-output-formats.md](04-overlay-output-formats.md) | CasparCG/SPX/OGraf template API (update/play/stop), alpha and key/fill via ffmpeg, media-clock sync (rVFC, WebVTT/HLS cues), EBU safe areas, OBS studio, SCTE-35 |
| 05 | [05-cv-auto-eventing.md](05-cv-auto-eventing.md) | Licence-safe CV stack (RF-DETR + `trackers` + `supervision`), the known-camera auto-label trick, rule-based events, SoccerNet metrics, event-F1 grader, Azure GPU |
| 06 | [06-synthetic-broadcast-rendering.md](06-synthetic-broadcast-rendering.md) | Three.js + Playwright lockstep rendering, broadcast camera prior, YOLO auto-labels and homography export, ffmpeg degradations, SoccerSynth prior art |
| 08 | [08-pass-difficulty-xpass-xt.md](08-pass-difficulty-xpass-xt.md) | xPass and a 0–10 pass-difficulty score, Spearman time-to-intercept model, xT value iteration, VAEP, and the risk of using real data |

## In progress

07 xG · 09 pressure/PPDA/control-vs-chaos · 10 pitch control · 11 broadcast stat
presentation · 12 this hackathon's judging criteria and rules · 13 past winners · 14 demo video and write-up ·
15 competitors (CV, simulators, overlays) · 16 competitors (front-runners)

## Next topics (queue)

Priority 1 (build/tech)
- Starter repos and Azure samples to fork (Event Hubs + Container Apps + Web PubSub + Foundry end-to-end)
- Realistic off-ball movement for the generator: jitter, pressing triggers, overlapping runs. Closes the "4 km per player" gap found in 02
- CDF compliance: settle the validator's v0.3.2 vs paper's v1.0.0 and the exact JSON nesting (from 02)
- Web PubSub event handlers / upstream messages, so Graphics Desk take/hold commands can go from browser to worker (from 01)
- Serving RF-DETR (ONNX/TensorRT) on an ACA serverless T4: cold start, image size, quota on Students/Free Trial (from 01, 05)
- Camera calibration from frames (SoccerNet calibration tools: TVCalib, PnLCalib) for TwinCast's "CV calibration" mode (from 05, 06)
- Grader setup: MOTChallenge GT format, `trackers eval` / TrackEval for HOTA and IDF1 (from 05, 06)
- Synthetic-to-real gap: texture, lighting and kit randomisation; low-poly GLTF players with run cycles (from 05, 06)
- Foundry Voice Live / speech-in, speech-out for Chalk Talk and Half-Time Talk (from 03)
- Priority vs Flex processing on Global Standard for live vs offline calls (from 03)
- Deterministic offline overlay render: OGraf non-real-time mode, Puppeteer virtual time, as an ACA job (from 04)
- SCTE-35 generation in Python (`threefive`) for Safe Break; NDI-with-alpha from OBS (DistroAV) for a live key/fill demo (from 04)
- Fabric Real-Time Intelligence (Eventstream/Eventhouse): does it beat our own Python windowing? (from 01)

Priority 2 (football domain)
- Converting synthetic events to SPADL so socceraction xT/VAEP runs unchanged (from 08)
- Calibration and reliability diagrams for xPass/xT/predictions (Called It, Realism Bench) (from 08)
- Translator custom glossaries for football jargon in other languages (from 03)
