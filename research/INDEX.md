# Research Library — Index

Research for the "Inside the Game" hackathon (Microsoft × Premier League, Synthetic Match Insights Engine).
It covers the parts almost any of our candidate ideas will need. Every file has the same parts: TL;DR, Findings,
So what for us, Reuse: code & links, and Sources. Context: [Intel pack](../Berbata_Hackathon_Intel.md) ·
[Idea shortlist](../Berbata_Idea_Shortlist.html) · [Idea brainstorm](../Berbata_Idea_Brainstorm.html).

## Files

| # | File | One line |
|---|---|---|
| 01 | [01-azure-realtime-pipeline.md](01-azure-realtime-pipeline.md) | Stage-by-stage Azure map; Event Hubs (+ local emulator), ACA worker vs Functions vs Stream Analytics, Web PubSub groups per audience, Cosmos free tier, credits |
| 03 | [03-foundry-llm-explain.md](03-foundry-llm-explain.md) | Calling Foundry models (v1 API), structured outputs for cues, grounding checks, Translator/Speech (Bulgarian), quotas and cost |
| 05 | [05-cv-auto-eventing.md](05-cv-auto-eventing.md) | Licence-safe CV stack (RF-DETR + `trackers` + `supervision`), the known-camera auto-label trick, rule-based events, SoccerNet metrics, event-F1 grader, Azure GPU |
| 06 | [06-synthetic-broadcast-rendering.md](06-synthetic-broadcast-rendering.md) | Three.js + Playwright lockstep rendering, broadcast camera prior, YOLO auto-labels and homography export, ffmpeg degradations, SoccerSynth prior art |
| 08 | [08-pass-difficulty-xpass-xt.md](08-pass-difficulty-xpass-xt.md) | xPass and a 0–10 pass-difficulty score, Spearman time-to-intercept model, xT value iteration, VAEP, and the risk of using real data |

## Next topics (queue)

Priority 1 (build/tech)
- Computer vision for auto-eventing: YOLO, ByteTrack, Roboflow `sports`/`supervision`, homography to pitch coordinates (TwinCast)
- Rendering synthetic broadcast video: Three.js broadcast camera, headless capture to MP4 (TwinCast, Ghost Team, Chalk Talk)
- Starter repos and Azure samples to fork (Event Hubs + Functions + Web PubSub + OpenAI end-to-end)

Priority 2 (football domain)
- xG models: features, open models, a logistic-regression xG we can implement
- Pass difficulty / expected pass (xP) and expected threat (xT)
- Pressure, pressing and PPDA: definitions and formulas
- Pitch control (Spearman, Fernández & Bornn) with a NumPy implementation
- How broadcasters show stats on screen (Premier League, Sky, Amazon/AWS, Opta graphics)

Priority 3 (judging and winners)
- This hackathon's judging criteria, prize categories and deadlines (About page)
- What past Microsoft and sports-tech hackathon winners did
- Demo video and write-up best practice

Priority 4 (competitors)
- Deep dive on the closest competitors: what they do well and where the gaps are
