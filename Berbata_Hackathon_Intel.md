# Berbata – Hackathon Intel Pack
**Inside the Game: Developer Hackathon (Microsoft × Premier League)**
Challenge: *The Synthetic Match Insights Engine for Premier League Studio*
Compiled 19 Oct 2026 (≈20:15 UK) from Innovation Studio · 332 projects linked to the challenge (all projects in the hackathon)
Project page URL pattern: `https://innovationstudio.microsoft.com/hackathons/insidethegamedeveloperhackathon/project/<ID>`

---

## 1. Challenge brief (full)

**Tagline:** An AI insights engine running on Azure that explains the game beyond the stats. It turns football events into real-time insights, key narratives and recaps, personalised for every fan, for studio and streaming use.

**Core ask:** Build AI-driven apps or agents that turn **synthetic** football events into **explainable match intelligence**. Surface meaningful stats, find key moments, explain why they matter, and generate personalised experiences. **No real Premier League data is provided. Projects must use synthetic, football-realistic data.** The output should suit studio, broadcast and streaming use, and fans in any market should be able to tailor it.

**Allowed forms:** AI agent, workflow, integration, data platform, analytics experience, automation solution, or a new experience. It must be responsive enough for live play and clear enough for real-time narratives and automated recaps.

### (i) One pipeline, five stages
| Stage | Requirement |
|---|---|
| a. Ingest | Synthetic match events as they happen (passes, shots, tackles, possession changes, pressure events, match metadata) |
| b. Interpret | Turn them into meaningful stats and patterns, with the context behind them |
| c. Explain | Say *why* a moment matters, not only that it happened |
| d. Render | Turn the insight into something that can sit on screen alongside the match |
| e. Personalise | The same intelligence should reach a data-hungry analyst and a casual fan as two genuinely different experiences: custom modes, favourite club(s), favourite player(s), a player-focus mode that follows one player all match, plus "many more ideas" |

Focus can be **on-screen storytelling** (clean, timed, machine-readable output that can drive synchronised graphic overlays on a live feed, the way the platform's rendering partner handles overlays in production), **personalised audience experiences** (modes by language, club, player or a single metric), or both. The brief warns: *"a Project that only generates metrics has no audience, and a solution that only personalizes has nothing to personalize."*

### (ii) Real-time match intelligence: suggested features
- **Player identification:** real-time name tagging, plus optional speed and distance indicators when thresholds are hit
- **Pass quality:** distance, accuracy, pass difficulty rating
- **Speed metrics:** ball speed, shot speed
- **Auto-eventing:** run a model over an incoming video feed to produce the pass and speed metrics automatically instead of tagging by hand

### (iii) Narrative generation
Key narratives, player-performance context, notable milestones, match recaps.

### (iv) Explainability
Why moments matter, for example control vs chaos, tactical pressure changes, game-rhythm patterns.

### (v) Data innovation
Create or extend synthetic, football-realistic datasets: passes, shots, tackles, possession changes, pressure events, match metadata.

### (vi) Multi-language storytelling
Clear natural-language output for global studio and streaming use, in multiple languages.

*Resources section on the challenge: empty. Judging criteria, prize categories and deadlines are on the hackathon's About page, which I didn't capture. Several teams name the category they're targeting, e.g. "Best Multi-Agent System / Best Multi-Agent Orchestration", so prize categories exist.*

---

## 2. Landscape at a glance

| Metric | Value |
|---|---|
| Total projects | **332** (first created 6 Oct; 30+ created today, 19 Oct) |
| Empty description | 122 (37%) |
| Placeholder / under 300 chars | 40 |
| Moderately described (300–1,500 chars) | 67 |
| Fully written up (≥1,500 chars) | 103 |
| Have a video attached | 19 |
| Public GitHub link in description | ~14 |
| Team size | solo 259 · 2 people 34 · 3 people 11 · 4 people 10 · 5 people 1 · 0 listed 17 |
| Open to new members | 171 |

**Most-used keywords:** Football Analytics (58), Microsoft Foundry (53), Explainable AI (50), Synthetic Data (31), Azure (23), Match Intelligence (21), AI Agents (19), Personalization (17), Multi-Agent (15+11+9 variants), Microsoft Agent Framework (14), MCP (9), Broadcast overlays (8).

**Tech mentioned in descriptions:** Foundry 93 · Personalisation 91 · Overlays 62 · Container Apps 52 · Agent Framework 49 · Multi-agent 45 · Copilot 30 · xG 30 · Azure OpenAI 28 · Multilingual 28 · Event Hubs 23 · Cosmos DB 20 · Speech 20 · MCP 19 · Fabric 16 · Translator 13.

### What almost everyone is building (crowded, so it won't stand out on its own)
**"Multi-agent studio crew + Verifier/Fact-checker + analyst vs casual fan mode + multilingual + overlay JSON + evidence-linked claims."** At least 40–50 serious entries are some version of this. Common names: MatchMind (×12+), MatchLens (×9), PitchPulse (×6), Touchline/Pitchside (×8), The Gallery, MatchDesk. Being "grounded / every sentence cites event IDs" is now table stakes, not a differentiator.

### Distinct angles already taken (each has 1–3 teams)
- **What-if / counterfactual simulation:** Second Guess (5-person team), Fulcrum, ParallelPitch (Monte Carlo), Rematch, Tactic Replay, The Half-Time Lab, MatchLens What-If
- **Missed-pass / better-option analysis:** Touchline AI (126715), The Better Ball, Before the Pass
- **Accessibility (blind/low-vision, spatial audio):** Audio Eyes, Blind-side, VYBE
- **Local-language commentary:** Msimulizi (Swahili/EN/FR), Matchday Crew (Swahili/Japanese), Sauti, Touchline (German)
- **Rival-fan spin with fact auditor:** Both Ends
- **Fan-generated video:** Roar (fan phone clips → Moments)
- **Computer vision / auto-eventing from video:** The Ninety Labs, ATLAS, MatchSight AI, Match Mind AI (126679), Kicklytics
- **Fantasy football integration:** FantasyVerse, Fantasy Vision, Lasso (out-predict the "AI Gaffer")
- **Defensive "invisible work":** Shield
- **Fatigue / physical:** Sisyphus Engine, Fatigue index
- **Player-cam mode:** Mauled by the Tigers
- **Vendor data normalisation:** VendorIQ (Opta/StatsBomb/Wyscout → CDF)
- **Fact-checking pundit narratives:** Narrative VAR
- **AI broadcast director (picks the story):** Director's Cut, SignalFlow, PitchPulse – AI Broadcast Director

### Gaps I see (opportunities for Berbata)
1. **Auto-eventing from video (brief ii-d)** is the hardest bullet and the least covered by teams that also have a strong explainability and personalisation layer. CV teams lack the story layer; story teams skip CV.
2. **Player identification with threshold-triggered speed/distance tags plus ball/shot speed** (brief ii-a, ii-c) are named outright, yet few entries make them the hero.
3. **A real overlay renderer.** Most entries emit "overlay JSON". Few show an actual broadcast-grade overlay composited on a video feed.
4. **Single-metric viewing mode** ("a single performance metric a viewer cares about") is in the brief and almost nobody uses it as the headline.
5. **Data innovation (v):** publishing an open, seeded synthetic dataset or generator with a realism eval (a few teams do it, e.g. Turning Point with a Gillespie-style simulator).

### Honest note on our own entry
**Berbata AI (ID 126726)** · Nikolay Krastev, Martin Stoynev · created today 19:01
Description: "In progress... 🏋️" · Tagline: *"Get even or get even worse"* · Keyword: *"Niki Aleksandrov Mafia"*.
Next to the polished entries, the listing currently reads like a joke entry. Before judging, I'd replace the tagline, keyword and description with a real problem → solution → five-stage pipeline → Azure stack → demo/repo/video write-up. The top entries all follow this structure.

---

## 3. Strongest competitors to watch (most complete and most visible)
| ID | Project | Team | Why it's strong |
|---|---|---|---|
| 126601 | Inside the Game – Explainable Match Intelligence for Every Fan | Karel Rejthar | Live Azure demo, public GitHub, MCP server, YouTube video; Foundry + Agent Framework + Event Hubs |
| 126532 | Inside the Game: verified football recaps by a team of AI agents | Kumara Swamy Padigeri | Video; four agents with a Verifier; every sentence links to proof; targets Best Multi-Agent |
| 126602 | PitchMind: proves every claim before it goes on air | Prasanna ram | Video; Agent Framework, Foundry, ACA, Cosmos, Functions, App Insights, OpenTelemetry |
| 126547 | Matchroom: Explainable Multi-Agent AI Match Studio | Sai Shankar Yalla | Live ACA demo and public GitHub |
| 126574 | MatchLens by Dhisana | Madhukar Devaraju | Video; stories update when evidence is corrected (smart angle); targets Best Multi-Agent |
| 126727 | Roar | Abel Adigun | Unique fan-video angle; deployed end-to-end on ACA/Postgres/Blob; CI green |
| 126558 | MatchShift | Peter Didow | 9k-char write-up; question, verify and replay |
| 126652 | Event Horizon – AI Match Intelligence | Dmitri Rotari | 10k-char write-up; "Why this moment?" cards |
| 126674 | TactiPulse SI | tiagomonteiro2011 | 9k-char tactical write-up |
| 126571 | PULSE XI | 4-person team | Tactical sandbox plus what-ifs; 8k chars |
| 126394 | CounterPress | Jia Hong Lee, Dushyant Agre | 8k chars; Foundry Agent Service + MCP |
| 126450 | VYBE — Every Fan Belongs | Mohamed Dawood | Video; accessibility-first personalisation |
| 126312 | Second Guess: The Football What-If Engine | 5-person team | Counterfactual xG; largest team |
| 126311 | Audio Eyes | Ish Rastogi, Chandrasheker Gadiwala | Spatial audio for blind fans |
| 126492 | The Ninety Labs | 3-person team | Auto-eventing to replace manual Opta-style tagging; strong business case |
| 126721 | OmniPitch | Riccardo Giorgio Ponte | 6k chars; Foundry + Fabric OneLake + MCP for Copilot Studio |
| 126495 | Floodlight | BOON JIN YI | Video; seeded simulator, automated broadcast direction |
| 126306 | Msimulizi | 4-person team | Native Swahili/EN/FR commentary |
| 126309 | Sauti | Peter Kioko | Agent Framework + Speech; audio commentary |
| 126341 | MatchMind: AI Broadcast Booth | Muhammad Ali Saeed | Video; Agent Framework, MCP, Foundry Local |
| 126715 | Touchline AI | Dinesh Sonachalam | Video, public GitHub; missed-pass alternatives |
| 126595 | La Liguilla | Adrian Mustelier | Video; conversational stats via MCP |
---

## 4. Full project directory (all 332, newest first)
**Detail:** E = empty · B = brief/placeholder (<300 chars) · D = described (300–1,500) · F = full write-up (≥1,500) · ▶ = video attached

| # | ID | Project | Team | Created | Detail | Pitch |
|---|---|---|---|---|---|---|
| 1 | 126730 | Footpro | Murad San | 19 Oct | E | #football #ai |
| 2 | 126729 | Fire AI: Real-Time Multi-Agent Football Telemetry | (none listed) | 19 Oct | D | 11v11 physics sim, WebSocket, Tactical/Storyteller/Personalisation agents |
| 3 | 126728 | PlayerTracker | Xiran Liu | 19 Oct | E | Track player performance |
| 4 | 126727 | Roar | Abel Adigun | 19 Oct | F | Fan phone clips → AI-clustered live Moments; deployed on Azure |
| 5 | 126726 | **Berbata AI (ours)** | Nikolay Krastev; Martin Stoynev | 19 Oct | B | "Get even or get even worse" – in progress |
| 6 | 126725 | Football analytics | Sergio Martínez | 19 Oct | E | – |
| 7 | 126724 | Pizarra | Carmen San Nicolas Martinez | 19 Oct | D | Match explained at your level |
| 8 | 126723 | Premier Insights | shivam Agrawal | 19 Oct | E | – |
| 9 | 126722 | Injury development app (late entry) | Arjun Wara | 19 Oct | B | Injury-risk predictor from biomechanics |
| 10 | 126721 | OmniPitch | Riccardo Giorgio Ponte | 19 Oct | F | Multi-agent, overlays, scouting dossiers, Fabric OneLake, MCP |
| 11 | 126720 | FairPlay Exchange | Logan Cowan | 19 Oct | F | AI transfer valuation platform (off-brief) |
| 12 | 126719 | The Synthetic Match Insights Engine | Abdelrazek Rizk; Sherine Rizk | 19 Oct | E | – |
| 13 | 126718 | Foot Fall | (none listed) | 19 Oct | E | WIP |
| 14 | 126717 | MatchMind – AI Live Football Companion | Sandeepa Wimalasiri | 19 Oct | F | Scoreboard + momentum + late-game predictions |
| 15 | 126716 | kuwas | Exodus Tesfaye Gebre | 19 Oct | D | Scouting app for Ethiopian academies (off-brief) |
| 16 | 126715 | Touchline AI | Dinesh Sonachalam | 19 Oct | D ▶ | Missed passing options; GitHub public |
| 17 | 126714 | We Got this | ken kangi | 19 Oct | E | EPL analysis |
| 18 | 126713 | Premier League Insights | Thomas Black | 19 Oct | E | – |
| 19 | 126712 | MatrixAE Footballytics | F. F. Gondal; Fahad Ramzan; Sheheryar Ramzan | 19 Oct | E | See the game behind the game |
| 20 | 126711 | TurningPoint - AI | Ashae Byam | 19 Oct | E | Evidence-interpreting agent, audience-adaptive |
| 21 | 126710 | Tornarem | Guillermo Alamán Requena | 19 Oct | E | – |
| 22 | 126709 | Title | Michael Siu | 19 Oct | E | – |
| 23 | 126708 | playstyler | Shourya Pratap Singh | 19 Oct | B | Playstyle-personality agents |
| 24 | 126707 | KooraVision | Omar Eltouny | 19 Oct | D | Multi-agent storytelling, multilingual, seeded generator |
| 25 | 126706 | Redmoor FC Coach Room | Issatay Massalin | 19 Oct | E | Coach XI and subs assistant from wearables |
| 26 | 126705 | MatchLens | Tristan Friend | 19 Oct | E | See the match through your own lens |
| 27 | 126704 | Why That Goal? | Muthukumar Arunachalam | 19 Oct | F | Rewind goal build-up, evidence pack, EN/ES |
| 28 | 126702 | Top Analysts | Evan Yap | 19 Oct | E | – |
| 29 | 126701 | Databall.eu | Tarvi Tamm | 19 Oct | E | Real-time match understanding |
| 30 | 126700 | Real-Time AI Football Analytics & B2B Data Platform | Femi Ogunbiyi | 19 Oct | D | XGBoost win probability + GPT-4o stories |
| 31 | 126699 | Second Screen | Varad Paradkar | 19 Oct | F | Agent Framework, Event Hubs, Cosmos, Fact-Checker, overlay JSON |
| 32 | 126698 | Agile | Bojan Makivic | 19 Oct | E | Agile periodisation |
| 33 | 126697 | MatchLens — Match Intelligence & Player Performance | Muh Fachrul Razy | 19 Oct | F | Per-player live dashboards |
| 34 | 126696 | Football Hackaton ex Hiop | Andrea Giuseppe Licata | 19 Oct | E | – |
| 35 | 126695 | FB-XLR8 | Shashank hirwani | 19 Oct | B | "Just building" |
| 36 | 126694 | Gru-Po | Daniel Nonchev; Hugo López | 19 Oct | E | – |
| 37 | 126693 | Park the Prompt | Jash Fijiwala | 19 Oct | E | – |
| 38 | 126692 | The Better Ball | Kartik Shanbhag | 19 Oct | D | Was there a better pass/shot available? |
| 39 | 126691 | Compressing Space (High Line / Offside Trap) | Juvencio Ribeiro Franco Neto | 19 Oct | D | High-line explainer |
| 40 | 126690 | up_the_chels | Chee Pheng Kee | 19 Oct | E | – |
| 41 | 126689 | MatchIQ | Joseph Daaboul | 19 Oct | E | AI in midfield |
| 42 | 126688 | TacticLens | (none listed) | 19 Oct | F | Multi-agent explanations for fans |
| 43 | 126687 | The 12th player | Thomas Delmas; Eddi Chatra | 19 Oct | E | – |
| 44 | 126686 | Kairos | Karthik Arun Ragupathy | 19 Oct | E | Foundry + Video Indexer |
| 45 | 126685 | Kicklytics | Lijo Joseph | 19 Oct | D | CV: detects players/ball/ref, pass lanes |
| 46 | 126684 | MatchLens | Pablo Ros | 19 Oct | D | Win prob, pass difficulty, control vs chaos, overlays |
| 47 | 126683 | commentAItors | E. Cardiel Gascón; V. Sierra; D. Blanchard Lobaco | 19 Oct | E | Multi-agent expert commentary |
| 48 | 126682 | Inside the Game | Hadi Sotudeh | 19 Oct | E | – |
| 49 | 126681 | Vantage AI | Matthew Moore | 19 Oct | E | Insight + visualisation for broadcast |
| 50 | 126680 | Premier Analytics | Alexander Darlington | 19 Oct | D | Live cues and checked stats for commentators |
| 51 | 126679 | Match Mind AI with Auto Event | NEWTON JUMA | 19 Oct | F | CV tracking, 2D digital twin, Foundry agents |
| 52 | 126678 | CoachAssistant | Valentino Pintar | 19 Oct | D | Coaching alerts + replacement players |
| 53 | 126677 | TactiX AI – Tactical Swarm | Luis Teran; Josue Cusquisiban | 19 Oct | D | Multi-agent swarm |
| 54 | 126676 | PitchPulse | A. Singh A/L Ravinder Singh | 19 Oct | E | – |
| 55 | 126675 | The Assistant Coach | Iwinosa Osagie-Okah | 19 Oct | E | CV real-time insights |
| 56 | 126674 | TactiPulse SI | tiagomonteiro2011 | 19 Oct | F | Tactical super-intelligence (9k chars) |
| 57 | 126673 | MatchDesk | (none listed) | 19 Oct | F | Evidence-cited overlays, Verifier recomputes numbers |
| 58 | 126672 | Turning Point | Derrick Deng | 19 Oct | D | Gillespie-style simulator, moment impact scoring |
| 59 | 126671 | Placeholder | Zachary Chua | 19 Oct | E | – |
| 60 | 126670 | LeagueVoice AI | Hamed, Mohammed | 19 Oct | B | Voice agent for leagues |
| 61 | 126669 | Momentum Ledger | Kipngeno Gregory | 19 Oct | F | Impact measurement + claim verification |
| 62 | 126668 | Rematch | Youssef Mohammed + 3 | 19 Oct | D | What could have happened |
| 63 | 126667 | Football AI | Taha Sismanoglu | 19 Oct | E | – |
| 64 | 126666 | Mic'd Up | Maayan Dotan; Dean Bazak | 19 Oct | D | Live commentary track at your level |
| 65 | 126665 | Tactical SuperIntelligence | Thomas James | 19 Oct | F | View a moment through different managers' philosophies |
| 66 | 126664 | Care coder | Ankit Dixit | 19 Oct | B | Off-brief |
| 67 | 126662 | SLAO Sports Analytics | Christopher Sloan; Stuart Yao | 19 Oct | E | – |
| 68 | 126660 | colazer0 | Anuarbek Bektemirov | 19 Oct | E | CV + LLM formation decoding |
| 69 | 126657 | PlayerLens 3D | Bright Dogbey | 19 Oct | F | Mixed 2D/3D broadcast illustrations |
| 70 | 126656 | ShapeShift | Zidan Patel | 19 Oct | F | Tactical shape, overloads → xG, predictions |
| 71 | 126655 | Interactive Football Trivia Game | Jan Botorek | 19 Oct | E | Live trivia vs peers |
| 72 | 126654 | EPL - ETL & Analytics | Samuel Varkey | 19 Oct | E | – |
| 73 | 126653 | Project | Oscar Yu | 19 Oct | E | – |
| 74 | 126652 | Event Horizon | Dmitri Rotari | 19 Oct | F | "Why this moment?" cards (10k chars) |
| 75 | 126651 | Matchlight | Peace Awodoye | 19 Oct | D | Five-stage multi-agent |
| 76 | 126650 | AI in Football | Nik Arif | 19 Oct | E | – |
| 77 | 126649 | The Match Desk | Banele Nelson Ntuli | 19 Oct | D | Evidence cards that stay accurate when data changes |
| 78 | 126648 | Coach in Your Ear | Shobhit Asai | 19 Oct | F | Teaches new fans football as they watch |
| 79 | 126647 | Hackathon project as525975 | Aditya Srivastava | 19 Oct | E | – |
| 80 | 126646 | Mauled by the Tigers | S. Y. L. Caleb; Chua Han Wei; Lu Shi Kai | 19 Oct | B | Player-cam mode, sprint alerts, personal recap |
| 81 | 126645 | UK FC | T. Zhanmadi; T. Tanirtayev; Z. Dzholdybayev | 19 Oct | E | – |
| 82 | 126644 | CrowdPlay | Deepjyoti Paul | 19 Oct | E | Fan suggestions → decisions |
| 83 | 126643 | InVision | Quy Minh Nguyen; Vinh Nguyen | 19 Oct | E | – |
| 84 | 126642 | CLXI | Pankaj Kumar | 19 Oct | F | Practice-video technique feedback (off-brief) |
| 85 | 126641 | Xibobo Football Match Insights | N. Nkosi; T. Nzuza; J. Ramputa; N. Sithole | 19 Oct | E | – |
| 86 | 126640 | Read the Game | Dami Oyeniyi | 19 Oct | E | Explainable fan experiences |
| 87 | 126639 | MatchPulse | Diego Lopes | 19 Oct | F | Databricks; evidence-backed stories |
| 88 | 126638 | MatchLens | Riaan Engelbrecht | 19 Oct | F | Foundry, Agent Framework, ACA, Event Hubs |
| 89 | 126637 | Football fun index | Malek Azaiz | 19 Oct | B | Fun metric |
| 90 | 126636 | Premier League DNA | Juan Vasquez | 19 Oct | F | Player style "blends" from PL history |
| 91 | 126635 | The Metronome | Syahrier Firmansyah Wakid | 19 Oct | F | Detects when the match changes shape |
| 92 | 126634 | Visual Match Intelligence | Nadav Gonen; Avishay Eizenberg | 19 Oct | E | – |
| 93 | 126632 | Achilles Sports | José Carlos Alania Agüero | 19 Oct | E | – |
| 94 | 126631 | Achilles | José Carlos Alania Agüero | 19 Oct | B | – |
| 95 | 126630 | Premier League Hackathon | Jason Loo | 19 Oct | E | – |
| 96 | 126627 | 4th Dimension of the Premier League | santhanam lakshmanan | 18 Oct | E | – |
| 97 | 126626 | Second Half | Ilknur Kazimli; Imran Mehdiyev | 18 Oct | D | AI TV studio; fact-checked; MCP |
| 98 | 126625 | MatchSense AI | Debadyuti SahaRoy | 18 Oct | D | Explainable, personalised |
| 99 | 126624 | Tactic Replay Agentic System | (none listed) | 18 Oct | D | Pundits test tactical ideas against the match |
| 100 | 126623 | Beyond The Roar | Jeff Lynch | 18 Oct | F | Personalised explainable studio |
| 101 | 126622 | MatchTurning AI | Victoria Ntinyari | 18 Oct | F | Evidence-backed turning points + replays |
| 102 | 126621 | Match Microscope | Bankole David | 18 Oct | F | Zero-scroll replay; Narrator → Verifier crew |
| 103 | 126620 | Virtual Assistant | Logeswaran Ramasamy | 18 Oct | B | – |
| 104 | 126618 | KickStream | Yashkumar Kavaiya; Samridh Khaneja | 18 Oct | E | AI stream agents |
| 105 | 126617 | Ravi Sport | Meysam Pourmonfared Azimi | 18 Oct | F | C#/.NET multi-agent |
| 106 | 126616 | football 101 | تسنيم حسن | 18 Oct | E | – |
| 107 | 126615 | Matchday Explainer | Walter Onyango | 18 Oct | F | RAG on Laws of the Game for referee decisions; AI Search |
| 108 | 126614 | PitchPulse AI | Glen Clayton Biggie | 18 Oct | B | – |
| 109 | 126613 | Twelfth Voice | Atif Sarfraz | 18 Oct | B | Fan's own commentary voice |
| 110 | 126612 | ThroughPass | Santiago Rodriguez Ramirez | 17 Oct | E | Live win probability |
| 111 | 126611 | MatchLens | Jani Nevalainen | 17 Oct | F | Agent Framework, Speech, predictions |
| 112 | 126610 | REGISTA | Ali Anass Amradouch | 17 Oct | E | – |
| 113 | 126609 | Outside the GAMENN | Mohamed Javid | 17 Oct | F | Persona-based tactical stories |
| 114 | 126608 | Match insights engine | Malik Bello | 17 Oct | E | – |
| 115 | 126607 | ParallelPitch | M. Ayaan Adil Ahmed; Sufiya Shariff | 17 Oct | F | Monte Carlo parallel futures; Durable Functions |
| 116 | 126606 | KinetIQ AI | Mateusz Kursa; Wojciech Palczewski | 17 Oct | E | – |
| 117 | 126605 | Match Insights | (none listed) | 17 Oct | B | – |
| 118 | 126604 | After90 | Ayesha Asim | 17 Oct | D | Smart insights + live stories |
| 119 | 126603 | Jahbadh-ai | Vimukthi Ashen | 17 Oct | F | "Explain the game and prove every word" |
| 120 | 126602 | PitchMind | Prasanna ram | 17 Oct | F ▶ | Proves every claim before air; full Azure stack |
| 121 | 126601 | Inside the Game – Explainable Match Intelligence | Karel Rejthar | 17 Oct | F ▶ | Live demo + GitHub + MCP server |
| 122 | 126600 | MatchSight AI | Nguyen Truong Manh Quan | 17 Oct | F ▶ | CV: reconstructs off-camera players |
| 123 | 126599 | Inside the Game | Sherine Rizk | 17 Oct | E | – |
| 124 | 126598 | v0.0 | Duy Nguyen Bao | 17 Oct | B | WIP |
| 125 | 126596 | Live On Air | Parth Shah | 17 Oct | E | – |
| 126 | 126595 | La Liguilla | Adrian Mustelier | 16 Oct | D ▶ | Conversational stats via MCP |
| 127 | 126594 | Sixth Official | Seth Rockafellow | 16 Oct | E | – |
| 128 | 126593 | Eagles - EPL Data App | Emmanuel Okponobi | 16 Oct | B | – |
| 129 | 126592 | Microsoft ETL/Machine Learning | Omar Mahmoud Ismail Abdo Ibrahim | 16 Oct | B | – |
| 130 | 126590 | FanAssist | Kiran Kumar Reddy | 16 Oct | E | – |
| 131 | 126588 | PitchMind | Prateek Gangopadhyay | 16 Oct | E | – |
| 132 | 126587 | Director's Cut | huzaifaa.ayyazz | 16 Oct | D | AI director picks one story per time window |
| 133 | 126586 | Pitchside | Shah Rahman | 16 Oct | F | Grounded explanations as timed overlays |
| 134 | 126585 | Inside the game - Azure tools | Sivakumar Kasi | 16 Oct | B | CV win/loss prediction |
| 135 | 126583 | MatchTrace | Serhat Demir | 16 Oct | F | Multi-agent real-time |
| 136 | 126582 | SynqTix AI | Raya Ramadha Fitroh | 16 Oct | B | – |
| 137 | 126580 | Iteration 1 | (none listed) | 16 Oct | E | Fan engagement |
| 138 | 126579 | All in one Football Analytics | Athul Thomas | 16 Oct | E | – |
| 139 | 126578 | Many Hands | (none listed) | 16 Oct | B | Details coming soon |
| 140 | 126577 | Football TV development | pitchtopixel | 16 Oct | E | – |
| 141 | 126575 | Inside The Game Ivan | Ivan G. Alvarez Vargas | 16 Oct | D | – |
| 142 | 126574 | MatchLens by Dhisana | Madhukar Devaraju | 15 Oct | F ▶ | Story updates when evidence is corrected |
| 143 | 126573 | MatchLens | Mohamed Alahyani | 15 Oct | D | – |
| 144 | 126572 | MatchMind AI — Storytelling | Bommesh Kori | 15 Oct | F | For hardcore fans |
| 145 | 126571 | PULSE XI | Diyan Patel; Satvik Patel; Vishwam Anghan; Mahir Chaudhary | 15 Oct | F | Tactical sandbox + what-ifs |
| 146 | 126570 | MATSCORE | Binay Topno | 15 Oct | D | Real-time visual analytics |
| 147 | 126569 | Matchweave AI | Ahmed Kadiwala | 15 Oct | F ▶ | Evidence you can see |
| 148 | 126568 | Invincibles | Pushpesh Basak | 15 Oct | D | Gaming (off-brief) |
| 149 | 126567 | MatchMind intelligence room | Sayon Bhattacharyya | 15 Oct | D | Clickable traceable sentences |
| 150 | 126566 | Klopp Strategy | Keezhatta, Anvar S | 15 Oct | B | – |
| 151 | 126565 | SmartNutrition | Abhinav Chauhan | 15 Oct | B | Off-brief |
| 152 | 126564 | Leo | Abdulbasit Ayinla | 15 Oct | E | – |
| 153 | 126563 | Sports-IA | Rahul Basu | 15 Oct | E | – |
| 154 | 126562 | Beyond The Score | Jared Cowan | 15 Oct | F | Five virtual hosts; Semantic Kernel, Blazor |
| 155 | 126561 | TactiCore | Pranay Merugu | 15 Oct | D | Tactical dashboard + NL questions |
| 156 | 126560 | Touchline AI | Abdul Basit | 15 Oct | D | – |
| 157 | 126559 | no more violence to football | Gordon Liew + 2 | 15 Oct | D | Joke entry |
| 158 | 126558 | MatchShift | Peter Didow | 15 Oct | F | Question, verify, replay (9k chars) |
| 159 | 126556 | xbvnfgnf | BASTIAN OBERST | 15 Oct | E | – |
| 160 | 126555 | Touchline: Live Match Intelligence | Ahmodu Ahmed | 15 Oct | F | MCP, multilingual overlays |
| 161 | 126554 | Both Ends | Nimatallahi Masuud | 15 Oct | F | Rival-fan commentary + Spin Auditor |
| 162 | 126553 | test | Sandeep Kuruva | 15 Oct | E | – |
| 163 | 126551 | Neural Ninjas | Harshvardhan Bhosale | 15 Oct | D ▶ | – |
| 164 | 126550 | MatchMind AI — Explainable | Aryan Gaikwad | 15 Oct | F ▶ | Ranked turning points |
| 165 | 126549 | MatchMind AI | P. K. Veera Kowshik | 15 Oct | D | – |
| 166 | 126548 | BoDev | BASTIAN OBERST | 15 Oct | E | – |
| 167 | 126547 | Matchroom | Sai Shankar Yalla | 15 Oct | F | Live demo + GitHub |
| 168 | 126545 | InsideLens | Siyabonga Ncube | 15 Oct | F | Weighted factors + counterfactual |
| 169 | 126544 | MatchMind AI - Beyond the Scoreline | Aarush Raj Gandhari | 15 Oct | D | – |
| 170 | 126543 | Football Decipher | Kanha Biswal; Piyush Takale | 15 Oct | E | – |
| 171 | 126542 | Matchday Companion | ogu83 Koroglu | 15 Oct | B | Interruptible spoken co-commentator |
| 172 | 126541 | Before the Pass | (none listed) | 15 Oct | F | Predicts receiving windows before the pass |
| 173 | 126540 | ReactCoach | Debamalya Gupta | 15 Oct | F | Decision coaching |
| 174 | 126538 | Soccer analytics project | Barry Brown | 15 Oct | E | – |
| 175 | 126537 | NextGen Scout AI | Leonardo Bravo | 14 Oct | F | Youth soccer narratives |
| 176 | 126536 | Proyecto en preparación | I. Bengoechea; M. A. Menéndez Suárez | 14 Oct | E | – |
| 177 | 126535 | PhaseShift AI | Milad Babadi | 14 Oct | F | Evidence-linked turning points |
| 178 | 126534 | Footy Stats | Sudharshan Prakash G | 14 Oct | D | – |
| 179 | 126532 | Inside the Game: verified recaps | Kumara Swamy Padigeri | 14 Oct | F ▶ | Verifier agent; Best Multi-Agent |
| 180 | 126531 | PitchPulse multi-agent | Muchamat Riyan Khamdani | 14 Oct | F | – |
| 181 | 126530 | Lasso | Brad Hack | 14 Oct | D | Why the odds moved + predict vs AI Gaffer; A2A |
| 182 | 126529 | LiveDesk | Fahad Sarwar | 14 Oct | D | Fabric agent |
| 183 | 126528 | Fulcrum | Martin Russ | 14 Oct | D | Counterfactual win-prob swing with CI |
| 184 | 126527 | My Project | Choudhury, Maharshi | 14 Oct | B | Dummy |
| 185 | 126526 | Fooball | Hoang Anh Nguyen | 14 Oct | D | Amateur recaps |
| 186 | 126525 | The_boys_AGH | M. Mróz; M. Nowak; F. Różański | 14 Oct | E | – |
| 187 | 126524 | PitchVolt AI | Tolis, Nikolaos | 14 Oct | F | – |
| 188 | 126523 | Multi-Agent Data Analyst (Excel) | Premanshu Kumar; Gopi K | 14 Oct | D | Off-brief |
| 189 | 126521 | Synthetic Match Insights Engine | Ronak Bansal | 14 Oct | F | Multilingual studio UI (6k chars) |
| 190 | 126520 | Project 101 | SAKSHAM KUMAR | 14 Oct | E | – |
| 191 | 126519 | ATLAS | H. Choubik; S. Khattami; L. Benlakhbaizi | 14 Oct | F | CV + EGNNs + coaching chatbot |
| 192 | 126515 | Broadcast & Technical Focus | Ndivho Netshirembe | 14 Oct | D | – |
| 193 | 126514 | vibing | Achim Imboden | 14 Oct | B | – |
| 194 | 126511 | Total Football | Febin Thomas | 14 Oct | E | – |
| 195 | 126510 | EPL Insights | (none listed) | 14 Oct | E | – |
| 196 | 126509 | Touchline | Emandleni Moyo | 14 Oct | B | – |
| 197 | 126508 | Tiki-Taka | (none listed) | 14 Oct | E | Watch 10 matches at once with an AI crew |
| 198 | 126506 | Ideate | Minh Tran | 14 Oct | E | – |
| 199 | 126504 | Fatigue index | (none listed) | 14 Oct | E | Real-time stamina estimates |
| 200 | 126503 | PitchSignal | Mike Karanja | 13 Oct | D | – |
| 201 | 126502 | FansReel | Padz Majecha | 13 Oct | E | – |
| 202 | 126501 | PRO-VISION AI | Micheal Berry | 13 Oct | B ▶ | Trading memory cards; live demo |
| 203 | 126499 | PitchPulse – AI Broadcast Director | A. Hoxha; R. Sekiraça; A. Makolli | 13 Oct | F | Control room, voice, graphics |
| 204 | 126498 | PL-1-test | Colin Hui | 13 Oct | B | – |
| 205 | 126497 | Fantasy Vision | W. J. Lyu; N. M. Wu; L. B. Shepard | 13 Oct | E | Fantasy viewing |
| 206 | 126496 | MTLstrikers | SRINIVAS T | 13 Oct | D | – |
| 207 | 126495 | Floodlight | BOON JIN YI | 13 Oct | F ▶ | Seeded sim + automated broadcast direction |
| 208 | 126494 | Kickers | Cosmas Mandikonza | 13 Oct | E | – |
| 209 | 126493 | PitchVision AI | P. R. Karmakar + 3 | 13 Oct | E | – |
| 210 | 126492 | The Ninety Labs | K. Lakhani; D. Haisley; J. Clarke | 13 Oct | F | Auto-eventing to replace manual tagging |
| 211 | 126487 | Match Story | M. Elsherif; R. Medhat | 13 Oct | E | – |
| 212 | 126486 | Player Scouting | Vishal Surya A.P | 13 Oct | E | – |
| 213 | 126485 | Player Scouting (dup.) | Vishal Surya A.P | 13 Oct | E | – |
| 214 | 126482 | Overlap | A. Gupta; V. Narang; P. Anand; M. Azeem | 13 Oct | E | – |
| 215 | 126479 | TBD | Abenezer Abebe | 13 Oct | B | – |
| 216 | 126478 | Soccer Image Processing | William Heinecke | 13 Oct | E | – |
| 217 | 126477 | Footydata | Thomas Aucott | 13 Oct | E | – |
| 218 | 126476 | TBD | Darren Funes; Jun Koo | 12 Oct | E | – |
| 219 | 126475 | AI - Premier League | David Ortega | 12 Oct | F | Opponent game plans for analysts |
| 220 | 126474 | TouchlineAI | (none listed) | 12 Oct | D | Agent Framework + Foundry |
| 221 | 126473 | The Gallery | Lindokuhle Nyoka | 12 Oct | F | "No evidence, no airtime" producer assistant |
| 222 | 126472 | Gantry | Erwin Bosman | 12 Oct | B | WIP |
| 223 | 126470 | App | Srikanth Krishnan; Ajai Arjun | 12 Oct | E | – |
| 224 | 126469 | The Gallery — AI Broadcast Crew | Sumeet Basu | 12 Oct | F | Personalised fact-checked broadcast |
| 225 | 126468 | the start of something big | L. Melvin + 3 | 12 Oct | B | – |
| 226 | 126467 | PH-I | Manavdeep Singh | 12 Oct | E | – |
| 227 | 126465 | Matchday Crew | Timsheldon Oure | 12 Oct | F | EN/Swahili/Japanese, spoken |
| 228 | 126464 | Project Brigma | Takoda Mundy | 12 Oct | B | – |
| 229 | 126463 | MatchMind — Agentic | Gayathri Nagarajan | 12 Oct | D | Five agents incl. Translator, FanChat |
| 230 | 126458 | OmniPitch | Akash S Vora; Tanmayee Maram | 12 Oct | E | – |
| 231 | 126457 | Chalkboard | Neel Thomas | 11 Oct | F | "Commentary with receipts" |
| 232 | 126456 | Tactix Ai | VASU REDDY | 11 Oct | D | Semantic Kernel |
| 233 | 126455 | Isagi's Eyes | (none listed) | 11 Oct | E | – |
| 234 | 126454 | FantasyVerse | Sherif Ahmed | 11 Oct | F | Live FPL integration |
| 235 | 126453 | TactIQ | Muhammad Faizan Mustafa | 11 Oct | F | MERN + Foundry |
| 236 | 126452 | CRONISTA | Carlos Sandi | 10 Oct | D | Bilingual clickable evidence |
| 237 | 126451 | TouchlineLens | Prince Anokye Frimpong | 10 Oct | D | MCP |
| 238 | 126450 | VYBE — Every Fan Belongs | Mohamed Dawood | 10 Oct | F ▶ | Accessibility-first (7k chars) |
| 239 | 126449 | MatchMind: Synthetic → Stories | Debarun Banerjee | 10 Oct | D | M365 Copilot, Foundry IQ |
| 240 | 126448 | VendorIQ | Oluwaseyi | 10 Oct | F | 7-agent vendor-format normaliser |
| 241 | 126447 | xPlain Live | Charalampis Andreou | 10 Oct | E | xP pass difficulty + SHAP |
| 242 | 126446 | qdqdq | Om Chauhan; Shreyaan Kovur | 10 Oct | E | – |
| 243 | 126445 | Agent XI | Shaukat Ali | 10 Oct | F | Eleven agents |
| 244 | 126444 | Narrative VAR | Long Vu | 10 Oct | F | Fact-check pundit narratives |
| 245 | 126443 | MatchMind Studio | Hamzat A. A. Adeleke | 10 Oct | F | Recaps in nine languages, shot map |
| 246 | 126442 | MatchLens: What-If | Vishnu Govind; Peter Krul | 10 Oct | F | Grounded "what if this continues" |
| 247 | 126441 | PitchPulse | Setlhomara Malefo | 10 Oct | F | – |
| 248 | 126440 | One Match, Many Matches | Eric Amenya; Daniel Githumbi | 10 Oct | D | Analyst / casual / newcomer |
| 249 | 126437 | TBD | Mohamed Nour | 10 Oct | E | – |
| 250 | 126436 | Control or Chaos | Joshua Oyewole | 10 Oct | D | Fact-checked, own-language |
| 251 | 126435 | TOUCH LINE. | Paul Davis | 10 Oct | B | – |
| 252 | 126434 | TactIQ | (none listed) | 10 Oct | B | Tactical change impact |
| 253 | 126432 | Blind-side | Korede Kayode-ojo | 10 Oct | D | Spatial audio for blind fans |
| 254 | 126431 | Snap ⚽️ | Jovin Mathew | 9 Oct | E | CV |
| 255 | 126430 | Pivot | Etimbuk Afia | 9 Oct | E | – |
| 256 | 126429 | Between the Lines | Josh Bellamy | 9 Oct | F | 6k chars |
| 257 | 126428 | PremierLeague Hackathon | A. Asfour; M. Hidalgo Sola | 9 Oct | E | – |
| 258 | 126425 | Control vs. Chaos | Tadeo Castillo | 9 Oct | F | Live control/chaos index |
| 259 | 126424 | GESPort | J. E. García Rojas + 2 | 9 Oct | B | – |
| 260 | 126423 | MatchMind AI: Every Match Has a Personality | jyothiswarup seethala | 9 Oct | F ▶ | Host personalities |
| 261 | 126422 | 88 PLS Synthetic Match Insights | J. Nie; J. Zhuo; L. Shi; A. Xu | 9 Oct | E | WIP |
| 262 | 126421 | Proj | Robson Chow | 9 Oct | E | – |
| 263 | 126420 | PitchMind: AI Football Studio | Supratim Dey | 9 Oct | D | – |
| 264 | 126418 | MatchEyes | Olatunbosun Ibiyinka | 9 Oct | F | – |
| 265 | 126406 | Touchline (German) | Marco Pöschmann | 9 Oct | D | German-language |
| 266 | 126403 | SyncComm | Phaneendra Gandi | 9 Oct | E | – |
| 267 | 126402 | Inside the Game | Yuval Antman; Dekel Winkler | 9 Oct | E | – |
| 268 | 126400 | energy mgt | Rama K P | 9 Oct | B | – |
| 269 | 126399 | Infinite Stadium | Rahman Salam | 9 Oct | F | Ask-the-match companion |
| 270 | 126398 | Matchmate | Göran Halvarsson | 9 Oct | D | Talk to the match / club / stadium |
| 271 | 126397 | Touchline Signal | Amahle Mohlokonya | 9 Oct | D | Local-first prototype |
| 272 | 126394 | CounterPress | Jia Hong Lee; Dushyant Agre | 9 Oct | F | 8k chars; Agent Service + MCP |
| 273 | 126392 | GhostPlay AI | Ankit Pal | 9 Oct | D | Off-ball support creation, xT |
| 274 | 126391 | Pitch Ledger | Ephraim Cabanlit | 9 Oct | F | Audited claims; Fabric IQ |
| 275 | 126390 | WhyLine | Adnan Saleem | 9 Oct | F | 7k chars |
| 276 | 126388 | MatchMind AI | Sujith Chowdari | 9 Oct | E | – |
| 277 | 126387 | MSFT x EPL Hackathon | Zekarias Asaminew | 9 Oct | E | – |
| 278 | 126386 | Second Story | Ajmal Khidri | 8 Oct | E | What the match was becoming |
| 279 | 126384 | Sisyphus Engine | Luke Hewitt | 8 Oct | F | Pressing fatigue / velocity decay |
| 280 | 126381 | GoalGetter | Simon Vereecke | 8 Oct | E | – |
| 281 | 126379 | MATCH⚽MINE | Dimitro Romanyszyn | 8 Oct | D | – |
| 282 | 126378 | SecondTouch | Sean Elamparo | 8 Oct | B | Second-screen |
| 283 | 126377 | SportyFy | Ofentse Khampe | 8 Oct | E | – |
| 284 | 126376 | Will Figure out a name | Y. B. Nandamuru | 8 Oct | E | – |
| 285 | 126374 | Risk Radar | Zia Mohammed | 8 Oct | D | Predict risky/productive player actions |
| 286 | 126372 | Match Storyteller | Faisal Basra | 8 Oct | D | Fan / Analyst styles |
| 287 | 126371 | CoachView | E. Diakakis; A. Chaideftos | 8 Oct | E | – |
| 288 | 126369 | MatchMind AI: Beyond the Scoreline | Kok Wai Leong | 8 Oct | D | – |
| 289 | 126368 | DataRed | Omri Zalait; Elon Bryger | 8 Oct | E | – |
| 290 | 126367 | PitchPulse AI | (none listed) | 8 Oct | D | – |
| 291 | 126366 | mwx-footbal | Masato Kashiwagi | 8 Oct | E | – |
| 292 | 126365 | Virtual Studio Crew | Timilehin David Owolabi | 8 Oct | F | Five agents, spoken recaps |
| 293 | 126363 | MatchMind Studio: AI Broadcast Crew | Saksham Nishant Malge | 8 Oct | D | – |
| 294 | 126362 | inside the game | Michail Christoforatos | 8 Oct | E | – |
| 295 | 126361 | Shift11 | Aryan Chand | 8 Oct | F | Momentum attribution to players |
| 296 | 126360 | THE HALF-TIME LAB | Fernando Torres | 8 Oct | F | Fans coach the second half |
| 297 | 126359 | Shield: Play Like Your Idol | Matthew Hatton | 8 Oct | F ▶ | Defensive work made visible |
| 298 | 126358 | SignalFlow | Kamal Saleh | 8 Oct | F | AI attention engine |
| 299 | 126356 | Tactiq | Kaniujeffray | 8 Oct | F | – |
| 300 | 126355 | PetKingDom | Manoj Rayalla | 8 Oct | D | Off-brief (pet e-commerce) |
| 301 | 126354 | Pulse | A. Wafula; D. Parekh; V. Shah; J. Gakuya | 8 Oct | F | Interactive pitch, evidence |
| 302 | 126353 | MatchDesk | George Okwori | 8 Oct | F | Human producer in control |
| 303 | 126352 | MatchPulse | G. Abhinay; Kumah Richard | 8 Oct | D | – |
| 304 | 126350 | Pitchside | Mpho Maribo | 8 Oct | F | Timed overlays |
| 305 | 126349 | PL Studio Insights -- DD | Dayton Drilling | 8 Oct | E | – |
| 306 | 126348 | Pitchside | Alex Knotwell | 8 Oct | F | – |
| 307 | 126347 | test | Zhilong ANG | 8 Oct | E | – |
| 308 | 126343 | Inside the Game | (none listed) | 7 Oct | E | – |
| 309 | 126342 | tbd | Nayan Ghimire | 7 Oct | E | – |
| 310 | 126341 | MatchMind: AI Broadcast Booth | Muhammad Ali Saeed | 7 Oct | F ▶ | Agent Framework, MCP, Foundry Local |
| 311 | 126336 | MatchDirector | P. A. P. Gururaj Thomas | 7 Oct | F | Fabric IQ |
| 312 | 126335 | Footbal AI | Dhanush _test | 7 Oct | E | – |
| 313 | 126334 | PitchLens | Ennio Bozzetti | 7 Oct | F ▶ | 3D visualisation |
| 314 | 126333 | MatchLens | Ayush Khati | 7 Oct | F | Event Hubs |
| 315 | 126331 | Antifreeze Team - Rabona | Peter-Gabriel ANA | 7 Oct | E | PPDA, tracking |
| 316 | 126330 | KickSense AI | Changan, Sakshi Santosh | 7 Oct | E | – |
| 317 | 126329 | GamePulse | Jessim Ziani; Wael Akhdar | 7 Oct | E | – |
| 318 | 126328 | MatchOS | Pierce Liam | 7 Oct | F | – |
| 319 | 126327 | Football Foundry | Wei Wang; Aaron Wang | 7 Oct | F | Casual-viewer explanations |
| 320 | 126326 | Larp | Dilmurod Akmalov | 7 Oct | B | – |
| 321 | 126325 | Premier League Match Pulse AI | Yondri Guarisma | 7 Oct | B ▶ | – |
| 322 | 126324 | MatchMind AI — The AI Football Analyst | S. Sudhakar; J. K. P. Ng; S. Hiregoudar | 7 Oct | F ▶ | Most engaged project (comments/likes) |
| 323 | 126322 | TBD | Zishen Harbour Wang; Ken Ruan | 7 Oct | E | – |
| 324 | 126321 | Adrena | Nam Pham | 6 Oct | B | – |
| 325 | 126320 | Game Co-Commentator | Ammad Faheem; Mike Chen | 6 Oct | E | – |
| 326 | 126315 | Soccalytics | Paul Mojica | 6 Oct | D | CV scouting |
| 327 | 126312 | Second Guess | Ish Rastogi + 4 | 6 Oct | F | What-if engine |
| 328 | 126311 | Audio Eyes | Ish Rastogi; Chandrasheker Gadiwala | 6 Oct | F | Spatial audio, conversational |
| 329 | 126310 | Untitled | Ireoluwatomiwa Akinfisoye | 6 Oct | B | – |
| 330 | 126309 | Sauti | Peter Kioko | 6 Oct | F | Agent Framework + Speech |
| 331 | 126307 | Ultimate PL Experience | Robert Obrochta | 6 Oct | E | – |
| 332 | 126306 | Msimulizi | Tevin Aduma + 3 | 6 Oct | F | Native Swahili/EN/FR |

*Team names come from the platform. "(none listed)" means the API returned no members. Pitches are my one-line summaries of each tagline and description.*
