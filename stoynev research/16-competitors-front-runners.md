# 16 — Competitor deep dive: the front-runners (most complete multi-agent/explainability entries)
_Accessed/compiled: 20 Oct 2026 · Priority area: competitive positioning (all stages; mainly Explain, Render, Personalise)_

## TL;DR
- **Three entries set the bar on public evidence:** Inside the Game / Rejthar (126601), Matchroom (126547) and the verified-recaps entry by Padigeri (126532). Each has a public MIT repo, a live Azure demo that returns HTTP 200, tests with CI, and **published measurements**. Those include Foundry evals at 59/60 groundedness, explanations scored against hidden simulator truth (53% vs about 20% by chance), and agent latency of roughly 1–4 s.
- **Table stakes now:** stats computed in code (the LLM only writes the words), a fact guard with a rewrite loop, evidence event IDs on every claim, analyst/casual/club/player modes in 3–5 languages, timed overlay-cue JSON, a 2D top-down pitch replay, deterministic fallbacks, an MCP server, Container Apps with managed identity, and App Insights/OpenTelemetry traces.
- **Common gap:** no front-runner's README describes overlays composited on real video. The pitch is drawn as a diagram. None measures event-to-screen latency end to end. None does computer-vision auto-eventing with a measured accuracy. Several prominent write-ups have no public code, or are plans.
- **Rules to keep in mind** (from a copy of the Official Rules committed in a competitor's public repo, so unverified against the official page): **the submission period ends 27 Oct 2026, 11:59 pm PT**. Entries need a demo video under 2 minutes and a public GitHub repo. Judging is 5 equally weighted criteria (tech, agentic design, impact, UX/presentation, category fit). Category prizes are Foundry, Enterprise, Multi-Agent and Azure Cloud Native.
- **How we win:** real pixels (overlays on video), a measured scoreboard across stages, the hard brief bullets as the hero (CV auto-events, speed tags, ball speed), personalisation beyond preset personas, and clean submission hygiene aimed at a less crowded category.

## Findings

### How this was gathered (and what is labelled)
Innovation Studio project pages need a Microsoft sign-in. The SPA calls an authenticated `innovationstudio.microsoft.com/api/graphql/` endpoint, so WebFetch and curl only get an empty shell. **For this file I used only public sources:** GitHub repos and READMEs (via the GitHub API), GitHub repo search, HTTP GETs on public demo URLs, and YouTube oEmbed titles.

Where a project has no findable public repo, the description comes from the team's own intel pack (`Berbata_Hackathon_Intel.md` §2–3) and is marked **[intel pack]**. Project-page claims I could not check publicly are left out.

### Rules and judging (from a public third-party copy)
`riccardoponte/OmniPitch` (OmniPitch's public repo) contains `OFFICIAL RULES.md`. It gives:
- Submission period: 6 Oct to 27 Oct 2026, 11:59 pm PT. Judging: 27 Oct to 10 Nov. Winners announced by 20 Nov.
- The demo video must be under 2 minutes and hosted on YouTube, Vimeo or similar. The repo must be public. Judges get a working link, but may judge from the text and video alone.
- Stage-two criteria, each 20%:
  - Technological Implementation, which explicitly mentions "optimized synthetic data creation" and hero tech (Foundry, Agent Framework, Azure MCP, Copilot agent mode, Fabric…)
  - Agentic Design & Innovation
  - Real-World Impact
  - UX & Presentation, including "does the demo video clearly communicate the value"
  - Adherence to Category
- Ties are broken on the first criterion, Technological Implementation.
- Prizes: 1st and 2nd Grand Prize, plus category prizes for Best Use of Microsoft Foundry, Best Enterprise Solution, Best Multi-Agent, and Best Azure Cloud Native Integration. A project can win one Grand Prize and one Category Prize.

(unverified against the official site, since that page sits behind the sign-in)

### Tier 1: shipped, measured, demo-ready (all facts from public repos)
| | **126601 Inside the Game (K. Rejthar)** | **126547 Matchroom (S. S. Yalla)** | **126532 Verified recaps (K. S. Padigeri)** |
|---|---|---|---|
| Pitch | Analyst ∥ Tactician → Narrator → deterministic Fact Guard (rewrite loop) → Persona → Producer schedules timed overlay cues | Engine emits timed cues with `why` and evidence IDs. Personaliser → Narrator → code Verifier → Localiser → Verifier | Analyst ∥ Retrieval (Cosmos vector search) → Narrator → Verifier. Every recap sentence links to its events |
| Stack | Agent Framework workflow, Foundry gpt-5.4-mini, Functions → **Event Hubs** → ACA worker, MCP server, App Insights, Foundry evals | **Foundry Agent Service** (3 versioned agents), ACA plus managed identity, Bicep/azd, App Insights, OTel GenAI spans | Agent Framework, Foundry gpt-5.4-mini, ACA (FastAPI), Static Web Apps (React), Cosmos DB vectors, MCP, GitHub Actions |
| Proof | Repo created 16 Oct, 10 commits, CI. `docs/project-page.md`: Foundry evals 59/60 groundedness, 60/60 fact guard. 2,641 events via Event Hubs in 116 s at 60×. 29 tests. README: median agent latency 2–4 s, full match in 79 s. Demo returned 200 but **took 23 s on a cold start** (my curl) | 14 commits. 20-match eval: pressing explanations at **53% precision vs about 20% by chance**. Agents take 0.7–1.3 s per line, under $0.001 per line. 1 Hz tracking with **27 km/h sprint tags, 105 km/h shot-speed cues**, a **single-metric mode**, and a fault-injection mode | 44 commits, 74 tests. Quality log: 43 recaps, 106 claims sent back, 12 sentences removed. 5 languages. 2-minute YouTube video. Live SWA demo returned 200 |
| Strengths | The most complete five-stage story. A real event-driven Azure path. Spoiler guard on MCP Q&A. Automated demo-video script (`demo/make_video.py`) | The most honest measurements. A labelled dataset with hidden tactical truth. Covers nearly every brief bullet as data | The clearest evidence UX. A retrieval agent makes the multi-agent case stronger |
| Gaps | Pitch replay with dots and pass trails, no video. Long cold start. Solo dev | README checklist still shows **"[ ] Demo video"**, and the intel pack lists no video. No Event Hubs (in-process replay). Diagram pitch | Recap-first, so live overlays are secondary. Diagram pitch |
| Category | Not stated in README (likely Grand Prize / Foundry) | Not stated (fits Foundry / Enterprise) | Multi-Agent [intel pack] |

### Tier 2: public code, narrower proof
| ID / project | What it is (public README) | Evidence (20 Oct) | Strength | Gap | Category |
|---|---|---|---|---|---|
| 126602 PitchMind | Lead, Analyst, Proof, Story, Recap, Fan and Scout agents, plus a fan-league game. Agent Framework, Foundry **gpt-4o**, ACA, Cosmos serverless, Storage Queue → Functions, App Insights/OTel, ARM template | Public repo with **3 commits** (16–17 Oct). Video [intel pack]. No live URL in README | A detailed observability design (`proof.verdict` spans, `claim_rejected` events) | The fan game dilutes the focus. No timed overlays. Older model | Likely Enterprise / Cloud Native |
| 126574 MatchLens (Dhisana) | Corrected evidence retracts stale stories (a voided goal). **OpenAI Agents SDK** and Azure, ACA, MCP Apps. EN/ES | 11 commits on a `codex/…` default branch, **no license file**. Demo returned 200. 1:53 YouTube video. `docs/evaluation.md`: multi-agent 8/8 vs single-agent 3/8 pass rate, 23.8 s vs 12.6 s latency | A clever correction angle and an honest baseline comparison | Doesn't use Microsoft Agent Framework (weaker hero-tech fit). Small, scripted scenario | Multi-Agent [intel pack] |
| 126450 VYBE | Accessibility-first young, accessible and analyst modes. EN/AR/CS deterministic captions, browser TTS | **128 commits**, the most active (last commit 19 Oct). Playwright plus backend tests, CI. 53 s YouTube video. README: "Live Microsoft Foundry integration… **not yet verified or deployed**" | Strong engineering hygiene and a real accessibility story | Thin on AI and agents. No live demo. Browser TTS, not Azure Speech | Likely Grand Prize (impact/UX) |
| 126715 Touchline AI | Missed-pass alternatives shown next to the actual pass. Python scanner, React, Foundry gpt-5-mini | 3 commits on 19 Oct. README: "**not yet publicly deployed**" | A distinct, visual idea | Single agent. No pipeline, personas or overlays | Unclear |
| 126721 OmniPitch | Multi-agent pipeline, Event Hubs/Functions, Fabric Lakehouse export, MCP for Copilot and Foundry, a broad dashboard | Public repo `riccardoponte/OmniPitch`: 15 commits (17–19 Oct), MIT. README only covers running on localhost. Claims to target **all five** prizes | Breadth, and the Fabric angle | No live demo or video found. Claims ("sub-second", "zero hallucination") have no measurements behind them | All, which dilutes category fit |

### Tier 3: no verifiable public code found
| ID / project | Summary | Public check on 20 Oct |
|---|---|---|
| 126727 Roar | Fan phone clips → AI-clustered live "Moments". Says it is deployed on ACA/Postgres/Blob with CI green [intel pack] | No public repo found by search. Off-brief (fan media, not event intelligence) |
| 126558 MatchShift | 9k-char write-up: "question, verify and replay" [intel pack] | GitHub search found only `pdidow/MatchShift-Demo`: 1 commit (17 Oct), a static HTML site. No public source for the engine |
| 126652 Event Horizon | 10k-char write-up with "Why this moment?" cards [intel pack] | No public repo found |
| 126324 MatchMind AI | The most engaged page (comments and likes). 3-person team. Video [intel pack] | No public repo found by search |
| 126312 Second Guess | Counterfactual-xG what-if engine. 5-person team [intel pack] | No public repo found |
| 126394 CounterPress | 8k-char write-up. Foundry Agent Service and MCP [intel pack] | No public repo found |

Under the rules above, entries without a public repo and a video can't be judged as they stand. They may still publish before 27 Oct.

### The bar a winning entry currently sets
1. **Features:** all five stages working on one seeded match. A visible multi-agent workflow with a fact guard and fallbacks. Four or more viewer modes in three or more languages. Timed cue JSON. Q&A that can't spoil later events. An MCP server.
2. **Polish:** a live URL with no login, deep links to key moments, an agent-activity view, and a "same moment, different viewers" comparison (126601).
3. **Proof:** numbers in the README, not adjectives. Foundry evals, accuracy against hidden truth, latency and cost per line, test counts, CI, and traces visible in Foundry.

### Weaknesses shared across the front-runners
- **No real video.** Every shipped front-runner renders a diagram pitch (dots, pass trails) with HTML cards. No README describes key/fill, broadcast-safe graphics, or cues driving graphics on actual frames.
- **Latency is only partly measured.** Teams report agent time (0.7–4 s) or batch throughput. Nobody reports p50/p95 event-to-pixel latency on the live path, or a latency budget per stage.
- **Accuracy is measured on the text, not the perception.** Only Matchroom scores explanations against ground truth. No shipped front-runner does CV auto-eventing or reports precision/recall for detected events.
- **Speed and distance tags exist only as data** (Matchroom's 27 km/h sprint tags, 126601's `player_alert`). They are never shown on a player in an image.
- **Personalisation is shallow:** preset personas plus a language toggle. Only Matchroom has a single-metric mode. There is no learned preference, no density control, and voice is missing or browser-only.
- **The Verifier is now a commodity.** At least six entries here say "numbers from code, words from AI, a verifier rejects bad claims".
- **Proof gaps:** missing demo video (Matchroom), a slow cold start (126601), Azure not yet deployed (VYBE, Touchline), and no public code (Tier 3).
- **Category crowding:** the stated targets cluster on **Multi-Agent**.

## So what for us
Stages: **Render** and **Interpret** (perception) are where the field is thinnest. **Explain** and **Personalise** are saturated, so we should match them, not lead with them.

Five ways to beat them, whichever idea we pick:
1. **Show real pixels.** Composite our cue JSON onto broadcast-style video (rendered synthetic footage, or at least an angled 3D render), with key/fill or alpha output. Nobody shipped does this. It helps **A TwinCast**, **F Graphics Desk** and **B Speed Trap**. Even with **C One Number**, put the metric on video.
2. **Publish a scoreboard for every stage, in the UI and in the video.** Include event-to-pixel p50/p95 per hop (Event Hubs → worker → agent → Web PubSub → render), the late-cue drop rate, cost per cue, the verifier's fault-injection catch rate, and, for TwinCast, CV event precision/recall/F1 against simulator truth. Matchroom's "53% vs 20%" is the most credible line in the field. We should beat it with more metrics, not more adjectives. "Optimized synthetic data creation" is named under the tie-break criterion, so **E Realism Bench** numbers count too.
3. **Make the hard brief bullets the hero:** player ID tags with threshold speed/distance, ball and shot speed tied to the consequence, and auto-eventing from video. The front-runners keep these as JSON fields.
4. **Go beyond preset personas.** Add a single-metric mode (**C**), producer take/hold control (**F**), Azure Speech output, and per-viewer playhead timing. Show one moment rendered for N viewers *on video*, which tops 126601's text-only strip.
5. **Tidy submission hygiene, plus a deliberate category.** Use a public MIT repo with CI and `azd up`. Keep ACA minReplicas set to 1 during judging (no 23 s cold start). Add deep links, a judge guide, and a video under two minutes that opens on the composited overlay. Name one category: **Best Azure Cloud Native Integration** (Event Hubs, ACA jobs and GPU, Functions, Web PubSub, measured ops) or **Best Use of Foundry** (versioned Agent Service agents, Foundry evals, traces). Keep the Verifier as hygiene, not as our pitch.

Also: fix our own listing (126726) well before 27 Oct.

## Reuse: code & links
Align with the cue shapes judges will already have seen. Matchroom's cue (MIT, from its README):
```json
{"kind":"pressure_surge","t_in":3824.1,"t_out":3836.1,"clock":"63'","priority":2,"team":"RVA",
 "headline":"RVA have turned up the press",
 "data":{"pressures_per_opp_min":14.3,"match_avg_per_opp_min":10.4},
 "explain":{"why":"...","evidence_event_ids":["SYN-0007-02402","SYN-0007-02404"]}}
```
Fields of 126601's `OverlayCue` (MIT, `src/insights/models.py`):
```python
cue_id, match_id, moment_id, moment_kind, profile_id, language, template,
slot: Literal["center","lower","corner","fullscreen"], priority,
trigger_match_seconds, display_at_match_seconds, duration_s, clock,
team_id, player_id, headline, caption, stats, why_it_matters, data, provenance
```
Our contract adds `tc_in` (SMPTE timecode), `ttl_ms`, `anchor` (a pixel or world anchor on the video) and `truth_check`. Those are what let a cue drive graphics on video. Copy Matchroom's evaluation pattern (`python -m scripts.evaluate` → precision/recall against `truth.json`) for Realism Bench and TwinCast.

Worth skimming:
- rejcom/inside-the-game-insights: the Event Hubs ingest Function, and `demo/make_video.py` for automated demo videos
- saisyalla96/matchroom: `agents/foundry.py` for versioned Agent Service agents, and the Verifier's unit and script checks
- KumarPadigeri/inside-the-game: the SSE overlay feed API and Cosmos vector retrieval

## Sources
- Official Rules (third-party copy) — https://github.com/riccardoponte/OmniPitch/blob/main/OFFICIAL%20RULES.md — accessed 20 Oct 2026
- rejcom/inside-the-game-insights (README, docs/project-page.md, models.py) — https://github.com/rejcom/inside-the-game-insights — accessed 20 Oct 2026
- 126601 live demo — https://insidethegame-player.whiteplant-48237189.swedencentral.azurecontainerapps.io — accessed 20 Oct 2026
- 126601 video ("inside the game demo") — https://youtu.be/_QToXIQQ3Nk — accessed 20 Oct 2026
- saisyalla96/matchroom — https://github.com/saisyalla96/matchroom — accessed 20 Oct 2026
- Matchroom live demo — https://ca-matchroom-oy5o46jqadfro.bluebush-9765fe66.eastus2.azurecontainerapps.io/ — accessed 20 Oct 2026
- KumarPadigeri/inside-the-game — https://github.com/KumarPadigeri/inside-the-game — accessed 20 Oct 2026
- 126532 live app — https://gentle-mushroom-01796580f.4.azurestaticapps.net — accessed 20 Oct 2026
- 126532 video — https://www.youtube.com/watch?v=R1PiQ1_6rPE — accessed 20 Oct 2026
- Prasannaverse13/Pitchmind — https://github.com/Prasannaverse13/Pitchmind — accessed 20 Oct 2026
- madhukard/matchlens (README, docs/evaluation.md) — https://github.com/madhukard/matchlens — accessed 20 Oct 2026
- MatchLens live demo — https://matchlens-dev.redforest-787f42f7.westus2.azurecontainerapps.io — accessed 20 Oct 2026
- MatchLens video — https://www.youtube.com/watch?v=qdtIEEIp8bE — accessed 20 Oct 2026
- Hapinam/vybe-ai — https://github.com/Hapinam/vybe-ai — accessed 20 Oct 2026
- VYBE video — https://youtu.be/c717qul116M — accessed 20 Oct 2026
- dineshsonachalam/touchline-ai — https://github.com/dineshsonachalam/touchline-ai — accessed 20 Oct 2026
- riccardoponte/OmniPitch — https://github.com/riccardoponte/OmniPitch — accessed 20 Oct 2026
- pdidow/MatchShift-Demo — https://github.com/pdidow/MatchShift-Demo — accessed 20 Oct 2026
- Berbata_Hackathon_Intel.md §2–3 (local intel pack; source of every [intel pack] label)
