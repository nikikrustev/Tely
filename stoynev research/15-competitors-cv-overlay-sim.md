# 15 — Competitor deep dive: the projects closest to our likely build (CV auto-eventing, simulators, real overlays, speed tags)

_Accessed/compiled: 20 Oct 2026 · Priority area: competitive positioning for TwinCast (A) and Speed Trap (B)_

## TL;DR

- **Two entries come close to TwinCast.** **The Ninety Labs (126492)** describes almost exactly our pipeline: a seeded engine renders broadcast-style footage, CV auto-events it, and the system grades itself against a hidden answer key and draws overlays on the footage. But on 20 Oct its page had **no repo, video or demo**. **Floodlight (126495)** has shipped: live demo, MIT repo, 111 tests, an MCP endpoint on Azure Container Apps and a "vision lab" scored against ground truth. Its vision runs on a **top-down raster of coloured discs**, and pass recall is 50%.
- **PitchPulse (126499) is the main rival to Speed Trap and One Number.** It has threshold name tags (shot over 110 km/h, pass over 40 m), a "focus metric" mode, producer approval, Azure Speech in 7 languages, Foundry plus Agent Framework plus MCP, and a live app. It is **event-level only**: no tracking, so no player running speed and no video.
- **The other CV teams use real footage or real tracking data.** MatchSight trains and evaluates on DFL, SkillCorner and SoccerNet. Match Mind AI and Kicklytics process real match clips (unverified for Match Mind). That is a compliance risk under the challenge's synthetic-only rule, and it gives us a clean "zero real pixels" story.
- **Nobody in this set has shipped broadcast-graphics overlays composited onto (synthetic) video, or a perspective broadcast-camera CV benchmark.** Those two gaps are TwinCast's headline.
- The remaining entries (MatchDesk, Pitchside, Director's Cut, KooraVision, Fire AI, Turning Point, Mauled by the Tigers, Sisyphus, PlayerLens, ATLAS, Kicklytics) are plans or early work with no public code. Their threat is low unless they ship this week.

## Findings

**Method.** Innovation Studio project pages are a JS app behind Entra sign-in. Its data API (`/api/graphql/`) needs a bearer token, so WebFetch and curl only return the login shell. I read every page on 20 Oct 2026 through a signed-in browser session, with "Show all page details" expanded. I checked linked GitHub repos through the GitHub API and raw READMEs, YouTube titles through oEmbed, and live demos with HTTP GETs. Pages can change, and everything below is as seen on 20 Oct.

### CV / auto-eventing

**The Ninety Labs — 126492** (K. Lakhani, D. Haisley, J. Clarke; created 13 Oct). Product name "Spotter". Its business case is replacing manual Opta-style tagging. A seeded match engine renders broadcast-style footage (pans, zoom, occlusion, blur) and keeps a hidden event and position log. A CV pipeline handles detection, homography and tracking, then derives passes, shots, tackles, possession, and ball, shot and sprint speed. Spotter grades itself live (precision and recall per event, speed error) and publishes a rerunnable seeded benchmark. A "data agent" generates targeted hard footage when vision struggles. Analyst, Tactician, Verifier and Producer agents run on Agent Framework. Name tags, speeds and pass-difficulty arcs are drawn "on the footage" as timed cues, with audio description for blind fans. **Shipped:** nothing public. The code-repository field is empty, and there is no video or link. **Strengths:** the strongest framing in the field, plus a 3-person team. **Gaps:** everything is still a claim. **Threat to TwinCast: HIGH** on concept, so we must out-ship them visibly. **To Speed Trap: medium.**

**Floodlight — 126495** (Boon Jin Yi; solo; 13 Oct). Covered under simulators below. Its "auto-eventing lab" makes it a CV rival too.

**MatchSight AI — 126600** (Nguyen Truong Manh Quan; solo; 17 Oct; has a video). Reconstructs players hidden from the broadcast camera, with calibrated uncertainty, and detects tactical states. **Shipped:** the public repo `NTMQuannuaQMTN/football-analyzer`, last pushed 17 Oct. It holds about 1.3 MB of Python plus a Next.js UI and ~547 files, many of them `cv/audit_*` scripts. The README reports measured errors: hidden-player replay error 3.03–5.33 m on its synthetic seed, and tactical F1 tables. **But** the live lobby replays "a recorded real DFL match", and its models are trained and evaluated on DFL, SkillCorner A-League and SoccerNet-GSR broadcast data. Foundry is only a stub: "implement `FoundryNarrativeGenerator.generate`". **Strengths:** serious evaluation discipline, and "observed vs inferred" labelling. **Gaps:** real-data dependence, no overlays on video, no Azure in the running code, and a research UI more than a broadcast product. **Threat: MEDIUM** to TwinCast's CV-credibility pitch, low to Speed Trap.

**Match Mind AI with Auto Event — 126679** (Newton Juma; solo; 19 Oct). A custom YOLO model (`best.pt`) with BoT-SORT, optical-flow camera compensation and K-Means jersey clustering, run on 625 frames (~26 s) for 14,632 detections. It computes pass difficulty, xP%, xT, sprint speed and distance, a Control-vs-Chaos index (−100 to +100), and a Tactical Pressure index (0–100). The UI is Streamlit plus an HTML5 Canvas 2D radar, with timed graphics on the video. gpt-4o-mini via Foundry and Azure AI Inference writes analyst, fan and broadcast commentary in EN/ES/FR/Swahili, with Web Speech TTS. **Shipped:** no repo or video link. The module names match the widely copied YOLO football-analysis tutorial pattern, and the clip is very likely real broadcast footage (unverified). **Threat: MEDIUM** to Speed Trap, because it already pairs sprint speed with overlays on video. **Low–medium** to TwinCast: no simulator and no ground-truth grading.

**ATLAS — 126519** (H. Choubik, S. Khattami, L. Benlakhbaizi; 14 Oct). YOLO plus ByteTrack, SigLIP+UMAP+KMeans team clustering, and 29-keypoint homography (the Roboflow `sports` recipe). An EGNN with 6 heads was "trained on 97,000+ match situations", with a FastAPI/React coaching chatbot. **Shipped:** no repo. **Gaps:** aimed at coaches and scouts rather than broadcast, and no synthetic-data story. **Threat: LOW.**

**Kicklytics — 126685** (Lijo Joseph; 19 Oct). Detects players, ball and referee in ~30 s tactical-camera clips and plots pass lanes. The page itself says it "contains numerous errors". **Shipped:** a public Gradio Space `Lijo21/kicklytics` (SigLIP, homography, pass-lane modules). Hugging Face reports it was last modified 6 Sep 2026, before the hackathon opened. The project field says "Writing Code: No". **Threat: LOW.**

### Simulators / data

**Floodlight — 126495.** This is the most complete shipped entry in this set. A TypeScript monorepo (MIT) has packages for simulator, engine, agents, cuesheet, vision, dataset, dataservice and MCP. The seeded simulator produces 90-minute events plus a 10 Hz positional feed, scripted storylines (comeback, siege, derby with a VAR overturn) and calibration tests (~3.4 goals, ~82% pass accuracy). A crew of Director, Analyst, Commentator, Verifier and Personalizer agents sits behind a deterministic fact gate. A versioned **cue sheet** handles lower thirds, momentum ribbon, telestration, player tags, priorities, slot exclusivity and expiry. The Three.js "program monitor" has 3 camera presets. A spoiler-safe catch-up mode is included. Nine MCP tools are served over Streamable HTTP on ACA. Committed datasets come with a DATA_CARD. **Vision lab:** a software rasterizer draws "kit coloured players" on a top-down tactical view, and a blob detector, tracker and state machine run on it. The published scorecard shows pass P/R/F1 of 100/50/67%, ball speed error 3.6 km/h, player speed error 2.1 km/h, over 901 frames at 10 Hz. **Weaknesses:** the CV is not a learned model and not a perspective broadcast view. The LLM defaults to Featherless (Qwen3-30B), with Azure Foundry only as an optional provider. Azure use is ACA hosting. Overlays sit on a 3D sim, not on video. GitHub shows the last push on 14 Oct. Live: GitHub Pages app and ACA `/health` both returned HTTP 200 on 20 Oct. **Threat: HIGH** to TwinCast (same "simulate → see → score" arc, already public). **Medium** to Speed Trap.

**Turning Point — 126672** (Derrick Deng; 19 Oct). A Gillespie-style continuous-time simulator with hidden ground truth, live xG, win probability and pass difficulty. It scores moment importance as impact (ΔWP) plus surprise, uses a control/chaos regime detector, and emits timed overlay JSON. **Shipped:** no repo. Smart maths, but no visuals. **Threat: LOW** (relevant to Realism Bench).

**Fire AI — 126729** (19 Oct). An 11v11 "physics-constrained" sim with velocity clamping, a FastAPI WebSocket updating every 4 s, and Tactical, Storyteller and Personalization agents. **Shipped:** no repo. **Threat: LOW.**

**KooraVision — 126707** (Omar Eltouny; 19 Oct). A seeded open generator for a fictional league. The description still contains template placeholders ("[One sentence on who is missing out and why.]"). **Threat: LOW.**

### Overlays / broadcast direction / speed

**PitchPulse – AI Broadcast Director — 126499** (Albion Hoxha, Afron Makolli, Rinesa Sekiraça; 13 Oct). A calibrated event simulator (~2.6 goals, ~77% pass accuracy) with a Statistician, Analyst, Narrator, Director and Fact-Checker. It shows **name tags with speed/distance indicators when a shot passes 110 km/h or a pass 40 m**. It has a "focus metric" woven into every line, player cam, producer mode ("nothing airs until On air"), Azure AI Speech neural voices in 7 languages, and "Ask the match" (a Foundry agent with a hosted MCP tool, plus prompt-injection blocking). It runs on managed identity, GitHub Actions OIDC, App Insights tracing and 15 tests. **Shipped:** the live ACA app returned HTTP 200, and its SSE stream (`/api/match/stream`) emits per-event JSON with x/y and running team stats (`top_shot_kmh`, `pass_difficulty_avg`, chaos/state). There is a YouTube demo ("PitchPulse – AI Broadcast Director | Inside the Game Hackathon"). The GitHub repo linked from the page **returned 404 on 20 Oct** (private or deleted). **Gaps:** no tracking data, so no player running speed or distance in practice. Graphics are a drawn TV screen over an SVG pitch, not video. **Threat: HIGH** to Speed Trap and One Number. **Medium** to TwinCast.

**PlayerLens 3D — 126657** (Bright Dogbey; 19 Oct). Mixed 2D/3D storytelling: name tags, current and top running speed, distance, a 3D tactical replay during stoppages, a producer console with approve, queue and dismiss, plus EN/ES. It honestly says the MVP uses "a synthetic match visualization rather than ... real broadcast footage". **Shipped:** no repo. **Threat: MEDIUM** if it ships (closest to Speed Trap plus Graphics Desk), low today.

**MatchDesk — 126353** (George Okwori; 8 Oct). Human-in-control production desk with an evidence inspector. The page says: "Current status: Project definition and architecture planning." **Threat: LOW.**

**Pitchside — 126586** (Shah Rahman; 16 Oct). A seeded generator with planted storylines and an answer key. The stats engine, agents and overlay front end were "in progress". **Threat: LOW.**

**Director's Cut — 126587** (16 Oct). One-story-per-window director, Urdu, and a "kill an agent live" demo. The text reads like pasted advice, for example "The rubric names MCP, and few entries will have one" (a possible hint about judging criteria, unverified). **Threat: LOW.**

**Mauled by the Tigers — 126646** (3-person team; 19 Oct). One paragraph: player-cam with sprint alerts at speed thresholds and a 60 s personal recap. **Threat: LOW** today, but it is the same hook as Speed Trap.

**Sisyphus Engine — 126384** (Luke Hewitt; 8 Oct). Pressing-fatigue and velocity-decay index from **Google Research Football** tracking via kloppy/SPADL, with Streamlit. **Shipped:** no repo. **Threat: LOW.** Its use of GRF as a synthetic tracking source is worth noting.

### Comparison table (as seen 20 Oct 2026)

| Project | Synthetic video | CV model | Graded vs truth | Overlay on video | Player speed tags | Public code / demo / video | Azure depth | Threat (A / B) |
|---|---|---|---|---|---|---|---|---|
| The Ninety Labs | Claimed (broadcast-style) | Claimed | Claimed | Claimed | Claimed | None | Agent Framework (claimed) | **High** / Med |
| Floodlight | Top-down raster | Blob detector | Yes (published) | No (3D sim) | Tags in cue sheet | Repo + live + video | ACA only; LLM via Featherless | **High** / Med |
| PitchPulse | No | No | No | No (drawn TV screen) | Shot/pass thresholds only | Live + video; repo 404 | Foundry, AF, MCP, Speech, MI | Med / **High** |
| MatchSight AI | Real + synthetic tracking | YOLO/BoT-SORT + ML | Yes (detailed) | No | No | Repo + video | "Readiness" only | Med / Low |
| Match Mind AI | Real clip (unverified) | YOLO + BoT-SORT | No | Yes (Streamlit) | Sprint speed | None | Foundry gpt-4o-mini | Low–Med / Med |
| PlayerLens 3D | Sim visual | No | No | No | Planned | None | Unclear | Low / Med |
| ATLAS / Kicklytics | Real footage | YOLO, SigLIP | No | No | No | Kicklytics HF Space only | None stated | Low / Low |
| Others (MatchDesk, Pitchside, Director's Cut, Turning Point, Fire AI, KooraVision, Sisyphus, Mauled) | No | No | Some answer keys | No | Mauled (idea) | None | Plans | Low / Low |

## So what for us

**Stages: Ingest → Render (TwinCast, Speed Trap, One Number, Graphics Desk, Realism Bench).**

**Top 3 things they do well that we must match**
1. **A public, no-login demo, a repo with tests and CI, and a YouTube video.** Floodlight and PitchPulse both have all three. Judges can click through. Our minimum is a Static Web Apps link, a public repo and a 3-minute video.
2. **Numbers from code, words from AI, a verifier, click-to-evidence, and a producer "take".** PitchPulse's "✓ fact-checked ▾" and Floodlight's retraction-aware rundown are now baseline. Our cue JSON's `evidence ids` and `truth_check` must be visible in the UI.
3. **A published, honest scorecard and an MCP surface.** Floodlight prints misses as misses, and MatchSight publishes F1 tables. PitchPulse adds managed identity, App Insights and Speech. We need a scorecard page plus an MCP tool (`get_cues`, `get_scorecard`).

**Top 5 gaps we can own**
1. **A perspective broadcast camera with a learned detector.** Render Three.js broadcast-angle video with pans and zoom, then run YOLO+ByteTrack with homography on it. Floodlight's top-down discs and Ninety Labs' unshipped claim leave this open. Show our numbers next to theirs, for example "pass recall on a moving broadcast camera".
2. **Real broadcast-grade overlays composited on video.** Use ffmpeg key/fill, so name tags follow tracked players frame-accurately. No one in this set has shipped this.
3. **Player running speed and distance from tracking, tied to consequence (Speed Trap).** PitchPulse only has event-level shot and pass speeds. Ours: "34.1 km/h recovery sprint, the 2nd fastest today, stopped a 0.21 xG break".
4. **"Zero real pixels" compliance.** Train and evaluate only on our own renders. MatchSight, Kicklytics and probably Match Mind rely on real footage or tracking. Say this outright in the write-up.
5. **Azure-native CV and cue-timing accuracy.** Run CV on ACA serverless GPU or Azure ML, and grade not just events but **cue timing** (`tc_in` error in frames) and speed error against ground truth. Floodlight's Azure is hosting only, and nobody grades overlay timing.

**Recommendation:** commit to TwinCast with Speed Trap as its first overlay pack. Ship a public demo and repo early (by mid-week) so judges see it before Ninety Labs ships. Lead the video with the side-by-side of predicted vs ground-truth overlays on the moving camera.

## Reuse: code & links

The Floodlight scorecard shape is a good model. Here is a time-tolerant event matcher for our grader (our own code, which mirrors their P/R/F1 report):

```python
def match_events(pred, truth, tol_s=0.5, kind_key="type"):
    """Greedy 1:1 match of predicted vs ground-truth events within tol_s seconds."""
    used, tp, dt = set(), 0, []
    for p in sorted(pred, key=lambda e: e["t"]):
        best = min((i for i, g in enumerate(truth)
                    if i not in used and g[kind_key] == p[kind_key] and abs(g["t"] - p["t"]) <= tol_s),
                   key=lambda i: abs(truth[i]["t"] - p["t"]), default=None)
        if best is not None:
            used.add(best); tp += 1; dt.append(p["t"] - truth[best]["t"])
    prec = tp / len(pred) if pred else 0.0
    rec = tp / len(truth) if truth else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"precision": prec, "recall": rec, "f1": f1,
            "mean_timing_err_ms": 1000 * sum(map(abs, dt)) / len(dt) if dt else None}
```

PitchPulse's SSE payload (observed live) is a handy reference for an event plus running-stats frame:
`{"event":{"id","t","clock","type","team","player","x","y","end_x","end_y"},"stats":{"momentum","flow":{"chaos","state","tempo_ppm"},"teams":{"home":{"xg","top_shot_kmh","pass_difficulty_avg",...}}},"moments":[]}`

Floodlight's MCP tool names (`prepare_match`, `state_at`, `query_events`, `get_cue_sheet`, `run_vision_pass`) are a sensible template for our MCP surface.

- Floodlight repo: https://github.com/JinYi123456/floodlight (see `packages/cuesheet/src/compiler.ts`, `packages/vision/src/*`)
- MatchSight repo (evaluation and uncertainty ideas): https://github.com/NTMQuannuaQMTN/football-analyzer

## Sources

- The Ninety Labs (126492) — https://innovationstudio.microsoft.com/hackathons/insidethegamedeveloperhackathon/project/126492 — accessed 20 Oct 2026
- Match Mind AI with Auto Event (126679) — https://innovationstudio.microsoft.com/hackathons/insidethegamedeveloperhackathon/project/126679 — accessed 20 Oct 2026
- MatchSight AI (126600) — https://innovationstudio.microsoft.com/hackathons/insidethegamedeveloperhackathon/project/126600 — accessed 20 Oct 2026
- MatchSight repo README — https://github.com/NTMQuannuaQMTN/football-analyzer — accessed 20 Oct 2026
- ATLAS (126519) — https://innovationstudio.microsoft.com/hackathons/insidethegamedeveloperhackathon/project/126519 — accessed 20 Oct 2026
- Kicklytics (126685) — https://innovationstudio.microsoft.com/hackathons/insidethegamedeveloperhackathon/project/126685 — accessed 20 Oct 2026
- Kicklytics HF Space / API — https://huggingface.co/spaces/Lijo21/kicklytics — accessed 20 Oct 2026
- Floodlight (126495) — https://innovationstudio.microsoft.com/hackathons/insidethegamedeveloperhackathon/project/126495 — accessed 20 Oct 2026
- Floodlight repo README and source — https://github.com/JinYi123456/floodlight — accessed 20 Oct 2026
- Floodlight live app — https://jinyi123456.github.io/floodlight/ — accessed 20 Oct 2026
- Floodlight demo video — https://youtu.be/TE-OzAD8lKo — accessed 20 Oct 2026
- Turning Point (126672) — https://innovationstudio.microsoft.com/hackathons/insidethegamedeveloperhackathon/project/126672 — accessed 20 Oct 2026
- Fire AI (126729) — https://innovationstudio.microsoft.com/hackathons/insidethegamedeveloperhackathon/project/126729 — accessed 20 Oct 2026
- KooraVision (126707) — https://innovationstudio.microsoft.com/hackathons/insidethegamedeveloperhackathon/project/126707 — accessed 20 Oct 2026
- MatchDesk (126353) — https://innovationstudio.microsoft.com/hackathons/insidethegamedeveloperhackathon/project/126353 — accessed 20 Oct 2026
- PitchPulse – AI Broadcast Director (126499) — https://innovationstudio.microsoft.com/hackathons/insidethegamedeveloperhackathon/project/126499 — accessed 20 Oct 2026
- PitchPulse live app and SSE stream — https://pitchpulse.livelyfield-1dcb67cb.polandcentral.azurecontainerapps.io/ — accessed 20 Oct 2026
- PitchPulse demo video — https://youtu.be/jB36TWpEmLc — accessed 20 Oct 2026
- PitchPulse repo (404 on access) — https://github.com/Albion-Hoxha/pitchpulse — accessed 20 Oct 2026
- Pitchside (126586) — https://innovationstudio.microsoft.com/hackathons/insidethegamedeveloperhackathon/project/126586 — accessed 20 Oct 2026
- Director's Cut (126587) — https://innovationstudio.microsoft.com/hackathons/insidethegamedeveloperhackathon/project/126587 — accessed 20 Oct 2026
- Mauled by the Tigers (126646) — https://innovationstudio.microsoft.com/hackathons/insidethegamedeveloperhackathon/project/126646 — accessed 20 Oct 2026
- Sisyphus Engine (126384) — https://innovationstudio.microsoft.com/hackathons/insidethegamedeveloperhackathon/project/126384 — accessed 20 Oct 2026
- PlayerLens 3D (126657) — https://innovationstudio.microsoft.com/hackathons/insidethegamedeveloperhackathon/project/126657 — accessed 20 Oct 2026
- Berbata Hackathon Intel Pack (sections 2–3), compiled 19 Oct 2026 — local file `Berbata_Hackathon_Intel.md` — accessed 20 Oct 2026
