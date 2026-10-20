# 28 — What Microsoft and the Premier League say they want (to score on Real-World Impact)

_Accessed/compiled: 20 Oct 2026 · Priority area: Real-World Impact (20% of Stage 2), write-up and pitch framing_

## TL;DR

- **The sponsors have told us what they want, in their own announcements.** The July 2025 deal lists four pillars: fan engagement, match insights and analysis, cloud transformation, and organisational productivity. The roadmap names **real-time data overlays, post-match analysis, in-broadcast insights, and native-language Q&A with text and audio translation**, all built on Foundry and Azure OpenAI. Richard Masters summed it up as "From personalised content to real-time match insights." ([PL](https://www.premierleague.com/en/news/4338015/premier-league-announces-partnership-with-microsoft))
- **The fan-app side is already built, so we should not pitch it.** The Premier League Companion (Copilot, Foundry, Cosmos DB, AI Search, multi-agent with Semantic Kernel) answers archive and stats questions and has had Open Prompt since Feb 2026. FPL Companion (GPT-5.4 on Foundry) launched for 2026-27. The app already has vertical match stories, predictors and quizzes. Microsoft's own figures are 60M users and about +20% engagement.
- **The studio and broadcast side is the open gap, and it is new.** From 2026-27, **Premier League Studios** (Olympia, London) produces all international content in-house: 380 matches, about 6,000 hours a season for 55 broadcast partners in 189 markets. The PL also launched its first direct-to-consumer service, **Premier League+** in Singapore, which offers "real-time data overlays". We found no public evidence of an AI producer tool for graphics, explained overlays, or multilingual cue text at Studios. The hackathon is titled "...for Premier League Studio" for good reason.
- **The users judges will find credible are:** a Premier League Studios graphics producer, a rights-holding broadcaster in a non-English market, the Premier League+ product owner, and the newer or casual fan. 34% of PL followers arrived in the last four years ([PL 2024](https://www.premierleague.com/en/news/4016793)).
- **The playlists file is thin.** RESOURCE PLAYLISTS.md lists five AI Skills Navigator playlists: GitHub Copilot, Azure AI Foundry, Foundry Agents, Agentic Workflows and Data. The playlist pages are a JS app, so we could not read their items. The only public session in the series is "Build AI-powered soccer insights apps with AKS and ACA" (14 Oct 2026).

## Findings

### 1. What the sponsors say they want solved (paraphrased, attributed)

We give one verbatim quote above (Masters). Everything below is a close paraphrase; the exact wording is at the links.

| Problem | Who said it, and where | Paraphrase |
|---|---|---|
| Personalisation at scale | Richard Masters, PL CEO, app launch, 1 Jul 2025 ([PL](https://www.premierleague.com/en/news/4337361/premier-league-launches-new-fan-facing-platforms-as-part-of-digital-transformation)) | A more personalised digital experience that matches the league's scale and global reach. |
| Fans follow many clubs | Alexandra Willis, PL Director of Digital Media & Audience Development ([SportsPro, Jul 2025](https://www.sportspro.com/analysis/sponsorship-marketing/premier-league-microsoft-technology-sponsor-app-ai-fpl-dtc-radio/)) | Fans now follow several clubs and players, and overseas fans watch more than one club. |
| Context and relevance | Willis ([Microsoft Source EMEA](https://news.microsoft.com/source/emea/features/premier-league-microsoft-partnership/)) | Live is what makes sport special. Information has to be contextual and relevant. |
| Global, multilingual fans | Joint release ([Microsoft, 1 Jul 2025](https://news.microsoft.com/source/2025/07/01/premier-league-and-microsoft-announce-five-year-strategic-partnership-to-personalize-the-fan-experience-with-ai-for-1-8-billion-people/)) | Open-text Q&A in fans' native languages, using text and audio translation. Still listed as coming, not shipped. |
| Real-time overlays and in-broadcast insights | Same release; PL partner page ([PL](https://www.premierleague.com/en/about/partners/microsoft)) | Foundry and Azure OpenAI for live real-time data overlays, post-match analysis, archive innovation and in-broadcast insights. |
| Transformation from match to boardroom | Judson Althoff, Microsoft EVP & CCO (same release) | Change how football is experienced, delivered and managed, on and off the pitch. |
| Studio control and speed | Paul Molnar, PL Chief Media Officer ([IBC, Sep 2025](https://ibc.org/production/news/building-a-true-premier-league-facility/22336)) | The new facility gives the PL full creative and operational control. Its stated goals include responding faster to platform needs and engaging audiences more deeply. |
| Serving broadcast partners | Molnar ([SVG, Nov 2024](https://www.sportsvideo.org/2024/11/22/premier-league-to-establish-in-house-media-operations-business-for-2026-27-season/)); Masters ([Broadcast, Oct 2025](https://www.broadcastnow.co.uk/broadcasting/premier-league-chief-move-to-in-house-production-provides-option-for-future-dtc-service/5209609.article)) | A best-in-class content service for partners. Being in the content supply chain gives the PL stronger control over content and "optionality" for a future streaming service. |
| Owning the customer | Masters ([SportsPro, May 2026](https://www.sportspro.com/news/broadcast-ott/premier-league-plus-dtc-streaming-singapore-starhub-may-2026/)) | Premier League+ is the first time the PL has its own customers. |
| Multi-agent personalisation | Chris Archer, PL Director of Digital Products & Technology ([Microsoft brand page](https://www.microsoft.com/en-us/customers/brand-collections/premier-league-transforming-fan-experiences)) | Real-time personalisation through a multi-agent system on Foundry. |
| Information overload | Microsoft Unlocked feature, Feb 2026 ([Microsoft](https://unlocked.microsoft.com/premier-league-companion/)) | Fans are swamped by stats spread across many sources, and debates get settled by opinion instead of facts. |
| Governance | Microsoft customer story, Nov 2025 ([Microsoft](https://www.microsoft.com/en/customers/story/25725-premier-league-azure-ai-foundry)) | Guardrails and traceability for every AI answer, GDPR-safe data handling, and coping with live demand spikes. |
| Hackathon framing | Reactor series S-1709 ([Microsoft Reactor](https://developer.microsoft.com/en-us/reactor/series/S-1709/)) | Football stories go beyond the scoreline. The task: turn synthetic events into explainable match intelligence for broadcast and streaming. |

**Accessibility** is named only in general terms: making the league "more accessible" and immersive. There is no PL or Microsoft AI accessibility product. Separately, Sky Sports added live subtitles to about 210 matches and descriptive audio to about 109 matches from 10 Oct 2026. The descriptions are done by specialist commentators; the article does not say AI is used ([Broadcast, 14 Oct 2026](https://www.broadcastnow.co.uk/broadcasting/sky-sports-adds-live-subtitles-and-descriptive-audio-commentary-to-premier-league/5221427.article)).

### 2. Numbers we can cite (all from the sources linked)

| Fact | Figure | Source (whose figure) |
|---|---|---|
| Followers worldwide | 1.87bn engage at least weekly; 34% became interested in the past 4 years | PL, 2023/24 season review |
| Reach | Broadcast in 189 of 193 UN states, 900M homes | PL 2024; also SVG Europe 2025 |
| Fan base (rounded) | 1.8bn in 189 countries | PL and Microsoft releases |
| Studios output | 380 matches; about 6,000 hours a season (PLP-era figure); 55 international partners; 189 markets | SVG 2024, IBC 2025 |
| Companion scale | 30 seasons, 10,000 matches, 300,000 articles, 9,000 videos; under 500 ms live replies via cache; designed for 8,000 TPS | Microsoft customer story (vendor) |
| Companion results | 60M users across web and app in the first months; about +20% engagement year on year | Microsoft customer story and brand page (vendor-reported) |
| FPL | More than 13M players | Technology Record, Jul 2026 |
| Premier League+ (Singapore) | Launched 5 Aug 2026; S$44 a month or S$399 a year; all 380 matches; multi-camera, real-time data overlays | SportsPro, May and Aug 2026 |
| Rights | International rights £2.1bn a year (+27%); domestic £6.7bn | SportsPro, Aug 2026 |
| PL website languages | English, Español, Arabic, Thai (site navigation) | premierleague.com |

We found **no official count of commentary languages** for the international feed (unverified gap). Do not quote one.

### 3. What the PL already ships, and the gaps

| Already exists (don't pitch as new) | Status |
|---|---|
| PL Companion: archive and stats Q&A, personalised feed, Open Prompt | Shipped Jul 2025; Open Prompt by Feb 2026 |
| FPL Companion: transfer and captain advice; the manager keeps control | Shipped for 2026-27 |
| App: vertical match stories, Matchday Live stats, predictors, quizzes, voting, PL Radio | Shipped Jul 2025 |
| Automated video clips: Companion integrates WSC Sports | Customer story |
| Data Zone L-bar (Genius Sports), one match per round; semi-automated offside graphics | See research 11 |
| Real-time data overlays on Premier League+ | Shipped Aug 2026 (provider not stated) |

| Gap (announced but not seen shipped, or never addressed) | Evidence |
|---|---|
| Native-language Q&A with text and audio translation | Announced Jul 2025. No language list found by Oct 2026 (unverified whether shipped) |
| AI "in-broadcast insights" on the produced feed | Announced. No public tool at Premier League Studios found |
| Audio match summaries, vertical video | "Planned" in Microsoft pieces |
| Producer-side AI graphics tooling at Studios (AI proposes, human takes) | Not mentioned anywhere |
| Explained overlays with evidence and confidence, graded against truth | Not mentioned; Microsoft emphasises traceability for Companion only |
| Kids or simplified modes; single-metric viewing; accessible audio | Not addressed by the PL. Sky's descriptive audio is human-made and covers about half the matches |
| Data-rich coverage for all 380 matches, not one per round | Data Zone covers one match per round (research 11) |

## So what for us

Main stages: **Explain, Render, Personalise.** Our Real-World Impact paragraph should name **Premier League Studios** as the main user, with **broadcast partners and Premier League+** as the people who receive its output. It should not name "fans in an app": that market is taken by Companion. Use three facts: 380 matches, 55 partners in 189 markets, and Premier League+ selling real-time data overlays. Then show **our own measured numbers**: event-to-cue latency, cues per match per operator, CV event F1 against ground truth, languages per cue, and calibration. Do not borrow industry numbers we cannot source.

Phrases and framings to use, mapped to each idea:

| Idea | Primary user | Framing for Real-World Impact (our words, tied to their stated goals) | Value we can measure in the demo |
|---|---|---|---|
| **TwinCast** | Premier League Studios tech and data team | "A safe, synthetic test pitch for the in-broadcast insights roadmap: rehearse and grade overlay logic on rendered footage before it goes near a live feed." Ties to cloud transformation, traceability and synthetic-only rules. | CV detection F1 and timing error against the simulator's ground truth; cue accuracy (truth_check pass rate) |
| **Speed Trap** | Studios graphics producer; FPL and casual fans | "Threshold-triggered speed and distance tags that explain consequence, not just the number." This is the real-time data overlay goal in its simplest form. | Trigger precision against seeded thresholds; cue latency in ms |
| **Graphics Desk** | Studios producer serving 55 partners | "AI proposes, producer takes: the governance and control the PL asked for, at 380-match scale." Molnar's creative-control goal, plus traceability. | Cues proposed vs taken; seconds from event to on-air key/fill; operator actions per match |
| **One Number** | Premier League+ subscriber; newer fans (34% in 4 years) | "An answer to the stats overload: one metric, explained, for the fan who wants context, not clutter." This is the Unlocked "too many stats" problem. | Reading-time compliance (ttl_ms against words); fewer cues per minute than the full feed |
| **Story Time** | Families and newcomer fans; partner channels in new markets | "The accessible, kids-safe layer the roadmap doesn't have yet. The same evidence-backed cue, retold simply, in the viewer's language." | Readability score per audience; languages per cue; safety-filter pass rate |
| **Called It** | Premier League+ and FPL-style engagement; broadcaster second screen | "Predictions that keep score honestly: calibrated, evidence-linked calls, not hype." The app already has predictors, so pitch calibration plus live tie-in, not prediction games. | Brier score and reliability curve over simulated matches |

Concrete recommendation: write the impact section in this order. (1) User and job: a Studios producer making data graphics for 55 partners. (2) Gap: overlays and in-broadcast insights are on the roadmap, but the producer tooling and multilingual explained cues don't exist yet. (3) Proof: our graded numbers. (4) Path to production: the same cue JSON can feed Studios key/fill, partner localisation and Premier League+ overlays. One line on "what the PL already has (Companion, FPL Companion) and why we don't duplicate it" will show the judges we did our homework.

## Reuse: code & links

A small impact block our pipeline can emit at the end of each simulated match. Its numbers come from our own run, so the write-up quotes measured values:

```python
impact = {
  "matches_simulated": n_matches,
  "cues_proposed": len(cues), "cues_taken": sum(c.taken for c in cues),
  "p50_event_to_cue_ms": statistics.median(lat_ms),
  "truth_check_pass_rate": passed / len(cues),
  "cv_event_f1": f1,                      # TwinCast only
  "languages_per_cue": len(cfg.languages),
  "brier": brier,                          # Called It only
}
json.dump(impact, open("out/impact_report.json", "w"), indent=2)
```

Write-up skeleton line: *"Premier League Studios now produces 380 matches a season for 55 partners in 189 markets [SVG 2024]. Our engine turns events into explained, timed cues in N languages, with a p50 event-to-cue time of X ms and Y% truth-checked [our run]."*

**RESOURCE PLAYLISTS.md** ([GitHub](https://github.com/microsoft/insidethegamehackathon/blob/main/RESOURCE%20PLAYLISTS.md), last edited 6 Oct 2026). The items in each playlist are not readable without the JS app.

| Playlist | Link | Relevance to us |
|---|---|---|
| GitHub Copilot | https://aka.ms/asn/ghcopilot | Medium. Copilot Agent Mode is a named "hero technology" |
| Azure AI Foundry | https://aka.ms/asn/foundry | **High** (Explain stage, evaluation, Best Use of Foundry) |
| Foundry Agents | https://aka.ms/asn/foundryagents | **High** (agentic design criterion) |
| Agentic Workflows | https://aka.ms/asn/agenticworkflows | **High** (Graphics Desk take/hold flow, orchestration) |
| Data | https://aka.ms/asn/data | Medium (Fabric/Cosmos, synthetic data story) |

Session: "Build AI-powered soccer insights apps with AKS and ACA", Brian Benz, 14 Oct 2026, available on demand ([Reactor event 27536](https://developer.microsoft.com/en-us/reactor/events/27536/)). It describes a reference architecture for agents on AKS/ACA, which matches our ACA choice.

## Sources

- Premier League and Microsoft announce five-year strategic partnership (Microsoft Source, 1 Jul 2025) — https://news.microsoft.com/source/2025/07/01/premier-league-and-microsoft-announce-five-year-strategic-partnership-to-personalize-the-fan-experience-with-ai-for-1-8-billion-people/ — accessed 20 Oct 2026
- Premier League announces partnership with Microsoft (PL, 1 Jul 2025) — https://www.premierleague.com/en/news/4338015/premier-league-announces-partnership-with-microsoft — accessed 20 Oct 2026
- Premier League launches new fan-facing platforms (PL, 1 Jul 2025) — https://www.premierleague.com/en/news/4337361/premier-league-launches-new-fan-facing-platforms-as-part-of-digital-transformation — accessed 20 Oct 2026
- What is the Premier League Companion (PL) — https://www.premierleague.com/en/news/4345260/what-is-the-premier-league-companion — accessed 20 Oct 2026
- PL partner page: Microsoft — https://www.premierleague.com/en/about/partners/microsoft — accessed 20 Oct 2026
- The numbers that show this has been a season like no other (PL, May 2024) — https://www.premierleague.com/en/news/4016793 — accessed 20 Oct 2026
- Premier League and Microsoft join forces (Microsoft Source EMEA) — https://news.microsoft.com/source/emea/features/premier-league-microsoft-partnership/ — accessed 20 Oct 2026
- Premier League drives deep fan connection with Microsoft Foundry and Azure Cosmos DB (Microsoft customer story, 18 Nov 2025) — https://www.microsoft.com/en/customers/story/25725-premier-league-azure-ai-foundry — accessed 20 Oct 2026
- Premier League brand collection (Microsoft) — https://www.microsoft.com/en-us/customers/brand-collections/premier-league-transforming-fan-experiences — accessed 20 Oct 2026
- Meet your matchday companion (Microsoft Unlocked, 2 Feb 2026) — https://unlocked.microsoft.com/premier-league-companion/ — accessed 20 Oct 2026
- Microsoft Copilot-powered FPL Companion to debut this season (Technology Record, 28 Jul 2026) — https://www.technologyrecord.com/article/microsoft-copilot-powered-fantasy-premier-league-companion-to-debut-this-season — accessed 20 Oct 2026
- How the Premier League, Microsoft and AI will change the way fans consume English soccer (SportsPro, 1 Jul 2025) — https://www.sportspro.com/analysis/sponsorship-marketing/premier-league-microsoft-technology-sponsor-app-ai-fpl-dtc-radio/ — accessed 20 Oct 2026
- Premier League reveals cost and coverage plans for Singapore streaming launch (SportsPro, 20 May 2026) — https://www.sportspro.com/news/broadcast-ott/premier-league-plus-dtc-streaming-singapore-starhub-may-2026/ — accessed 20 Oct 2026
- The business of the 2026/27 Premier League season (SportsPro, 19 Aug 2026) — https://www.sportspro.com/analysis/finance-investment/premier-league-2026-27-season-tv-rights-sponsors-finances-valuations/ — accessed 20 Oct 2026
- Premier League to establish in-house media operations business for 2026-27 (SVG, 22 Nov 2024) — https://www.sportsvideo.org/2024/11/22/premier-league-to-establish-in-house-media-operations-business-for-2026-27-season/ — accessed 20 Oct 2026
- Premier League to establish new international broadcast production HQ at Olympia (SVG Europe, 9 Jun 2025) — https://www.svgeurope.org/blog/headlines/premier-league-confirms-it-is-set-to-establish-its-new-international-broadcast-production-hq-at-olympia-in-central-london/ — accessed 20 Oct 2026
- Building a true Premier League facility (IBC, 12 Sep 2025) — https://ibc.org/production/news/building-a-true-premier-league-facility/22336 — accessed 20 Oct 2026
- Premier League chief: move to in-house production provides option for future DTC service (Broadcast, 3 Oct 2025) — https://www.broadcastnow.co.uk/broadcasting/premier-league-chief-move-to-in-house-production-provides-option-for-future-dtc-service/5209609.article — accessed 20 Oct 2026
- Sky Sports adds live subtitles and descriptive audio commentary to Premier League (Broadcast, 14 Oct 2026) — https://www.broadcastnow.co.uk/broadcasting/sky-sports-adds-live-subtitles-and-descriptive-audio-commentary-to-premier-league/5221427.article — accessed 20 Oct 2026
- RESOURCE PLAYLISTS.md (microsoft/insidethegamehackathon) — https://github.com/microsoft/insidethegamehackathon/blob/main/RESOURCE%20PLAYLISTS.md — accessed 20 Oct 2026
- Inside the Game: Developer Hackathon, Reactor series S-1709 — https://developer.microsoft.com/en-us/reactor/series/S-1709/ — accessed 20 Oct 2026
