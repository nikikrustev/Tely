# 13 — What past Microsoft and sports-tech hackathon winners did

_Accessed/compiled: 20 Oct 2026 · Priority area: Strategy and positioning across all stages (Ingest to Personalise), for A TwinCast first, then B Speed Trap, F Graphics Desk, E Realism Bench and 21 Called It_

## TL;DR

- **Recent Microsoft winners solve one narrow job for one named user.** Examples: supply-chain risk for expeditors (RiskWise), tariff questions (TARIFFED!), meeting notes turned into Jira sprints (SprintForge), copy detection for creators (CopyFlag). None of them is a general assistant.
- **Winners show a number.** SoccerNet, the Big Data Bowl 2026 leaderboard and the MIT Sloan rubric all score against ground truth or demand rigour and reproducibility. Microsoft write-ups also quote numbers: "~70% reduction in sprint-prep time" and "94% accurate", though both are self-reported. TwinCast's ground-truth grading is exactly this kind of evidence, and almost nobody else in our field can produce it.
- **Winners build on the sponsor's newest services and name them.** RiskWise and TARIFFED! were built on the then-new Azure AI Agent Service with Bing grounding. CopyFlag lists four Azure AI services. Agent Academy 2026 winners leaned on MCP servers.
- **Explainability, human-in-the-loop and safety are now scored, not optional extras.** Agent Academy 2026 gave "Reliability & Safety" 10% of the score, and judges praised an "AI-safety-first design". RiskWise's write-up has a Responsible AI section and calls the system "explainable" and assistive, not autonomous.
- **Small teams win: one to three people.** RiskWise had 3, TARIFFED! 1, Big Data Bowl 2025 had 2 and Big Data Bowl 2026 had 1. A 2-person team is normal. Multi-agent architecture is common among winners, but it is not what sets them apart, and in our field 40-50 entries already use it.

## Findings

### 1. Microsoft-run hackathons (2024-2026)

| Event | Winner(s) and what they built | Microsoft stack | Team | What organisers highlighted |
|---|---|---|---|---|
| **AI Agents Hackathon** (Apr 2025, 570 submissions) | **Best Overall ($20k): RiskWise**. A multi-agent system that gives expeditors "near real-time, explainable" supply-chain risk intelligence. Category winners include Apollo (a coordinator agent with research and analysis sub-agents), ModelProof (two LLMs cross-checking each other for hallucination and bias) and TARIFFED! (tariff Q&A over a SQL database with Bing grounding). | Azure AI Agent Service, Azure OpenAI, Bing grounding, Semantic Kernel, Azure SQL, Blob; React/Next.js | RiskWise 3; TARIFFED! 1 | Judged on "innovation, impact, technical usability, and alignment with category". Submissions were GitHub issues with a repo link, a YouTube demo and an architecture section. Neither RiskWise nor TARIFFED! gave a deployed endpoint. |
| **Agent Academy Hackathon** (May-Jun 2026, Power Platform) | **VendorGuard**: multi-agent contract compliance, "the single highest-scoring entry". **SprintForge**: notes to sprint plan to Jira through two MCP servers, "~70% reduction in sprint-prep time", "a unanimous favourite". **Calamity Agent**: weather and fire alerts, praised for its "AI-safety-first design". | Copilot Studio, Dataverse MCP, Power Automate, Azure AI Foundry, custom MCP servers | Mostly solo GitHub handles | Published weights: Accuracy & Relevance 25%, Technical Execution 25%, Creativity 15%, UX & Presentation 15%, Reliability & Safety 10%, Use-case Impact 10%. One entry was singled out for "how clearly the presentation conveyed the scenario". Several runners-up had human approval before any write action. |
| **Agents League** (Feb and Jun 2026) | Feb 2026 Enterprise Agents winner: **WAIA** (Franck Cornu, MVP). No technical detail is published. | Foundry IQ / Work IQ / Fabric IQ, M365 Copilot | 1 | The June 2026 brief asks for a real business scenario, grounding, "clear agent architecture", security and responsible AI, and a "compelling user experience". |
| **Azure Cosmos DB + Azure AI Learning Hackathon** (2024) | 1st UHIRED (interview coach), 2nd VISOUNDAY (video music and cover generator), 3rd Foodi Copilot | Azure OpenAI / GPT-4, Cosmos DB vector search | Solo builders named | No reasons given. All three are consumer copilots with one clear task each. |
| **FabCon Global Hack** (Sep-Nov 2025) | Grand Prize: **HERO, the Hybrid Emergency Route Optimizer**. Also Smart Waste Management for Dallas. | Microsoft Fabric | n/a | Judged on "innovation, impact, reproducibility, and demo quality" (from search snippet; page returned 403, unverified). |
| **Imagine Cup** (startup track) | 2024: FROM YOUR EYES (Türkiye), visual descriptions for blind users. 2025: **Argus** (Stanford), a voice-driven wearable for low vision on Azure AI Foundry and Azure AI Speech. 2026: **CopyFlag** (UK), copy and AI-alteration detection using Azure AI Vision, Azure OpenAI, AI Search and Azure ML. The founder claims 94% accuracy and "real customers". | Must require 2 or more Microsoft AI services | 1-2 founders | Criteria: cloud and AI implementation, inclusive design, viability, "founder-led validation". Microsoft said the 2026 finalists stood out for "clarity, execution, and focus on creating meaningful impact". |

We could not reach the RAGHack (2024) and Fabric & AI Learning Hackathon winner lists. The pages were blocked (403/404) or we could not find them (unverified).

### 2. Sports-tech competitions

| Competition | Winner and what they did | Why it won (per source) |
|---|---|---|
| **NFL Big Data Bowl 2025** (AWS Next Gen Stats; 400+ participants) | NYU duo (2 people), "Exposing Coverage Tells in the Pre-Snap". It included an interactive "digital whiteboard" where users move the players. | The 2025 rubric gives Football Score 30%, which asks "Would NFL teams... be able to use these results on a week-to-week basis?", and Data Science 30%. The rest covers write-up and visualisation (exact split unverified). The winners called their work "the blend between the narrative and the numbers". |
| **NFL Big Data Bowl 2026** | Lucca Ferraz (solo, Rice), "Ghostbusters". It models defender movement while the ball is in the air against "ghost" defender distributions, which yields a new coverage-impact metric. | This edition added a public leaderboard that scored predicted player locations against real tracking data. Finalists then pitched to club analytics staff at the Combine. |
| **SoccerNet 2025** (broadcast-video CV) | Game State Reconstruction was won by KIST-GSR (GS-HOTA 63.90) with YOLO-X, Deep-EIoU tracking, OSNet re-ID, keypoint pitch mapping and jersey-colour clustering for teams. | The organisers' report says every winner started from a strong pretrained backbone, used staged training and designed augmentations and losses for the domain. All tasks were ranked purely on a metric. |
| **MIT Sloan SSAC Research Papers 2025** | Syracuse et al., penalty-kick location optimisation (game theory and gradient boosting) | Criteria: novelty, rigour, **reproducibility** and application. Papers must be open source with a data repo. In the final, the panel "gives more weight to the presentation, especially its highlighted application and impact". |
| **SkillCorner x PySport Analytics Cup 2026** | Amar Shah, "Simulated Annealing for Positional Optimisation" | It was later released as a module in the open-source DataballPy package, which shows a reusable artefact. Finalists presented live. |
| **Premier League x Microsoft** (context, not a hackathon) | The 5-year deal (Jul 2025) covers the Copilot-powered PL Companion, "real-time data overlays during live matches", post-match analysis and native-language Q&A. | It is built on Azure OpenAI and Azure AI Foundry. These are the sponsor's stated priorities, and our Render and Personalise stages map directly onto them. |

### 3. Recurring patterns (each backed by at least two cited examples)

1. **A narrow job for a named user.** RiskWise (expeditors), TARIFFED! (importers), SprintForge (scrum leads), Argus (low-vision users), CopyFlag (creators). All of them are scoped to a single workflow.
2. **A measurable result against ground truth or a baseline.** SoccerNet (GS-HOTA), the Big Data Bowl 2026 leaderboard, MIT Sloan rigour and reproducibility, SprintForge (~70%) and CopyFlag (94%). The last two are self-reported, and nobody challenged them.
3. **The sponsor's newest services, named explicitly.** Azure AI Agent Service in 2025 (RiskWise, TARIFFED!), MCP and Dataverse MCP in 2026 (VendorGuard, SprintForge, Warehouse Picking). Imagine Cup goes further and requires 2 or more Microsoft AI services.
4. **Explainable, assistive and human-in-the-loop by design.** RiskWise ("transparent reasoning", assists humans), ModelProof (cross-model auditing), and the Agent Academy runners-up with escalation and approval gates.
5. **Safety and responsibility scored explicitly.** Agent Academy (10% Reliability & Safety; Calamity Agent praised), the Agents League brief (responsible AI) and Imagine Cup (inclusive design).
6. **Useful to the domain practitioner, not just clever.** The Big Data Bowl Football Score ("use... week-to-week"), the MIT Sloan final weighting on application, and the BDB 2025 whiteboard, which one analyst called "exactly what teams want".
7. **A clear story in the demo or presentation.** Agent Academy (UX & Presentation 15%; one runner-up praised for clarity), Imagine Cup ("clarity, execution"), MIT Sloan (presentation weighted in the final) and FabCon (demo quality, unverified).
8. **An open, reproducible artefact.** MIT Sloan (open source is mandatory), the AI Agents Hackathon (a public repo and video for every entry), SkillCorner (the winner became a library module).
9. **In CV tasks: a pretrained backbone, then domain tuning.** This held for all four SoccerNet 2025 winners (one report).
10. **Small teams.** One to three people in every case where team size was published.

### 4. Anti-patterns

- **Eye-candy without decision value.** One analyst criticised the "pointless use of 3D graphics" in Big Data Bowl 2025 entries (single source; partly our judgement).
- **Accuracy without baselines or uncertainty.** The same source calls prediction accuracy "a minor point" next to its downstream use (single source).
- **Generic chat over data.** The 2024 winners were simple copilots. By 2025-26 the winners were tied to a workflow with tools and actions (our judgement from the tables above).
- **Architecture as the pitch.** Multi-agent was common among winners, but each winner led with the problem. In a field with 40-50 near-identical "studio crew" entries, the architecture will not differentiate (our judgement).

## So what for us

- **Interpret / Explain → A TwinCast.** Pattern 2 is our strongest card. Lead the demo with one scoreboard: "CV auto-events vs simulator ground truth: precision, recall and timing error ±N frames, per event type". Then show an overlay whose `truth_check` field cites that grade. That turns explainability into a number that others cannot fake.
- **Render → A TwinCast and F Graphics Desk.** Pattern 6: frame outputs as what a PL Studio producer can use on air, such as timed cue JSON and key/fill. Mirror the sponsor's own words ("real-time data overlays during live matches").
- **Ingest / CV → A TwinCast.** Pattern 9: don't train from scratch. Use the SoccerNet-winner recipe (YOLO plus a ByteTrack/Deep-EIoU-style tracker, keypoint homography, jersey-colour clustering) and spend our time on grading.
- **Personalise → B Speed Trap and C One Number.** Pattern 1: if time runs short, one sharp mode for one named user (the casual fan in single-metric mode) beats five shallow modes.
- **Trust → 21 Called It and E Realism Bench.** Patterns 4 and 5: a calibration or realism report counts as a "Reliability & Safety" section, not decoration.

**Five concrete actions**
1. Put a ground-truth grading table on screen in the first 30 seconds of the demo, and commit the eval script plus seed so judges can reproduce it.
2. Write a one-line user story, "PL Studio graphics producer during a live match", and cut any feature that does not serve it.
3. Name every Azure service on the architecture slide, and include at least one new flagship service: the Foundry Agent Service or MCP. File 12 has the exact rule list.
4. Add a short Responsible AI section covering synthetic-only data, the fact-checker plus `truth_check` field, human take/hold before anything goes to air, and known failure cases.
5. Ship a public repo with a README in the winners' order: Problem → Demo video → Architecture → Measured results → Responsible AI → Setup.

## Reuse: code & links

Event-spotting grade vs simulator truth, scored as greedy one-to-one matching within a tolerance window. This is the "measurable result" metric:

```python
def grade(pred, truth, tol_ms=500):
    """pred/truth: lists of (t_ms, event_type). Returns per-type P/R/F1 and mean |dt|."""
    out = {}
    for et in {e for _, e in truth} | {e for _, e in pred}:
        P = sorted(t for t, e in pred if e == et); T = sorted(t for t, e in truth if e == et)
        used, dts = set(), []
        for p in P:
            best = min((abs(p - t), i) for i, t in enumerate(T) if i not in used) if len(used) < len(T) else None
            if best and best[0] <= tol_ms: used.add(best[1]); dts.append(best[0])
        tp = len(dts); prec = tp / len(P) if P else 0; rec = tp / len(T) if T else 0
        out[et] = dict(precision=round(prec, 3), recall=round(rec, 3),
                       f1=round(2*prec*rec/(prec+rec), 3) if tp else 0.0,
                       mean_abs_dt_ms=round(sum(dts)/tp) if tp else None)
    return out
```

README skeleton, mirroring the section structure of winning AI Agents Hackathon submissions:

```markdown
# TwinCast — <one-line user story>
## Problem (who, when, why now)   ## Demo (video link, 2-3 min)
## Architecture (diagram + every Azure service named)
## Measured results (grading table, seed, how to reproduce)
## Responsible AI (synthetic-only data, truth_check, human take/hold, limits)
## Setup   ## Team
```

- RiskWise repo: https://github.com/oh-qi-qi/azure-ai-agent-hackathon-2025
- TARIFFED! repo: https://github.com/tagr/ai-agents-hack
- SoccerNet 2025 results (winning GSR pipeline details): https://arxiv.org/abs/2508.19182

## Sources

- AI Agents Hackathon: winners page — https://microsoft.github.io/AI_Agents_Hackathon/winners/ — accessed 20 Oct 2026
- AI Agents Hackathon: home, prizes and criteria — https://microsoft.github.io/AI_Agents_Hackathon/ — accessed 20 Oct 2026
- AI Agents Hackathon 2025: Category Winners Showcase (Microsoft Community Hub; title only fetched, details via search) — https://techcommunity.microsoft.com/blog/azuredevcommunityblog/-/4415088 — accessed 20 Oct 2026
- RiskWise submission (issue #526) — https://github.com/microsoft/AI_Agents_Hackathon/issues/526 — accessed 20 Oct 2026
- TARIFFED! submission (issue #349) — https://github.com/microsoft/AI_Agents_Hackathon/issues/349 — accessed 20 Oct 2026
- Agent Academy Hackathon winners (Power Platform Dev Blog, Jun 2026) — https://devblogs.microsoft.com/powerplatform/agent-academy-hackathon-winners — accessed 20 Oct 2026
- Agents League 2026: Enterprise Agents — https://devblogs.microsoft.com/microsoft365dev/agents-league-hackathon-2026-enterprise-agents — accessed 20 Oct 2026
- Meet the winners: Azure AI + Azure Cosmos DB Learning Hackathon — https://devblogs.microsoft.com/cosmosdb/meet-the-winners-microsoft-developers-azure-ai-azure-cosmos-db-learning-hackathon — accessed 20 Oct 2026
- Winners of the Microsoft Fabric FabCon Global Hack (403 on fetch; search snippet only, unverified) — https://blog.fabric.microsoft.com/en-us/blog/announcing-the-winners-of-the-microsoft-fabric-fabcon-global-hack — accessed 20 Oct 2026
- Imagine Cup winners — https://imaginecup.microsoft.com/winners — accessed 20 Oct 2026
- Imagine Cup FAQ (criteria, 2 or more AI services) — https://imaginecup.microsoft.com/support/faq — accessed 20 Oct 2026
- Meet the future of innovation: Imagine Cup World Championship 2026 — https://blogs.microsoft.com/bayarea/2026/05/29/meet-the-future-of-innovation-microsoft-imagine-cup-world-championship/ — accessed 20 Oct 2026
- Microsoft for Startups on Argus — https://www.microsoft.com/en-us/startups/blog/?p=3676 — accessed 20 Oct 2026
- Stanford Daily: Argus wins Imagine Cup — https://stanforddaily.com/2025/06/05/juniors-ai-assistive-vision-device-takes-top-prize-at-microsoft-competition/ — accessed 20 Oct 2026
- Oriel College: CopyFlag wins Imagine Cup 2026 — https://www.alumni.oriel.ox.ac.uk/news/oriel-student-creates-history-with-imagine-cup-success/ — accessed 20 Oct 2026
- NFL Big Data Bowl (2026 winner, format) — https://operations.nfl.com/gameday/analytics/big-data-bowl — accessed 20 Oct 2026
- Rice News: Ferraz wins 2026 Big Data Bowl — https://news.rice.edu/news/2026/classroom-combine-champion-rice-student-wins-nfl-analytics-title — accessed 20 Oct 2026
- NYU SPS: 2025 Big Data Bowl winners — https://www.sps.nyu.edu/about/news-and-ideas/articles/preston-robert-tisch-institute-for-global-sport/2025/nyu-duo-crowned-winners-of-the-2025-nfl-big-data-bowl.html — accessed 20 Oct 2026
- Kaggle: NFL Big Data Bowl 2025 overview (rubric via search snippet) — https://kaggle.com/competitions/nfl-big-data-bowl-2025/overview — accessed 20 Oct 2026
- Thoughts on Big Data Bowl 2025 (analyst commentary) — https://statthinksportsanalytics.substack.com/p/thoughts-on-big-data-bowl-2025 — accessed 20 Oct 2026
- SoccerNet 2025 Challenges Results (arXiv 2508.19182) — https://arxiv.org/html/2508.19182v1 — accessed 20 Oct 2026
- MIT Sloan SSAC Research Paper Competition — https://www.sloansportsconference.com/research-paper-competition — accessed 20 Oct 2026
- Syracuse: Falk team wins 2025 SSAC paper competition — https://news.syr.edu/2025/03/18/falk-college-research-team-wins-prestigious-sports-analytics-research-paper-competition/ — accessed 20 Oct 2026
- SkillCorner x PySport Analytics Cup — https://skillcorner.com/analytics-cup-2027 — accessed 20 Oct 2026
- Premier League and Microsoft five-year partnership — https://news.microsoft.com/source/2025/07/01/premier-league-and-microsoft-announce-five-year-strategic-partnership-to-personalize-the-fan-experience-with-ai-for-1-8-billion-people/ — accessed 20 Oct 2026
