# 11 — How broadcasters show football stats on screen (patterns we can copy)

_Accessed/compiled: 20 Oct 2026 · Priority area: Render + Personalise stages (what is shown, when, and how) for F Graphics Desk, B Speed Trap, C One Number, A TwinCast, 10 Story Time_

## TL;DR

- **Bundesliga Match Facts (DFL + AWS) is the closest real precedent.** There are 16 facts: xGoals, Shot Speed, Speed Alert, Average Positions (+ Trends), Passing Profile, Attacking Zones, Most Pressed Player, Pressure Handling, Win Probability, Set Piece Threat, Skill, Shot Efficiency, Keeper Efficiency, Ball Recovery Time, Match Momentum. The pipeline is Kafka (MSK) → stateful per-fact containers → results pushed back to the data provider. AWS publishes **no end-to-end latency number**, only "within seconds".
- **Facts fire on three kinds of trigger.** DFL's Data Story Finder sorts them as *event-based* (goal → scorer's season rank), *threshold/exceptional* (speed record, season-best pass accuracy) and *summary* (half-time, key moments). An editor **Story Monitor** can review, edit or remove a story before commentators see it. This is the same shape as our "AI proposes, producer takes" Graphics Desk.
- **Live data on the Premier League today runs through Genius Sports (Second Spectrum tech).** It is Football DataCo's official tracking provider, capturing every player and the ball at 25 fps. It produces the PL "Data Zone" L-bar mode (one match per round) and, from April 2025, semi-automated offside graphics. From 2026-27 the PL produces its international feed in-house, replacing IMG/PLP.
- **The richest data goes on a separate, opt-in feed.** Prime Vision (Champions League 2025/26, NFL), Data Zone and Nickelodeon's NFL altcast each sit beside a clean main broadcast. That supports our audience modes being *separate cue streams* rather than one feed crammed with everything.
- **No source we found publishes on-screen durations.** Every duration below is marked as our guess. We derive `ttl_ms` from word count, using a subtitle-style reading rate (Ofcom 160-180 wpm for pre-recorded), with hard caps per layout.

## Findings

### 1. Who does what on Premier League coverage (verified)

| Role | Who | Note |
|---|---|---|
| Official tracking (Football DataCo) | Genius Sports, using Second Spectrum (acquired 2021) | 25 fps optical tracking in every PL venue. It powers "Premier League Data Zone": an L-bar with player names, pass accuracy, shot speed, sprints, distance, final-third touches, pitch maps and FPL updates. Used by NBC, Sky, Optus, ESPN Brazil and Canal+ ([SVG 2023](https://www.sportsvideo.org/2023/10/05/premier-league-productions-partners-with-genius-sports-to-deliver-premier-league-data-zone/)). |
| Semi-automated offside | Genius Sports (GeniusIQ) | Live from PL Matchweek 32, 2024/25. It generates virtual offside graphics for the stadium and the broadcast. Genius says it produces "broadcast-ready decision visuals within seconds" (vendor claim). |
| Match graphics, world feed | AE Live (current); deltatre and DixonBaxi in earlier eras | DixonBaxi designed the 2016 package: match graphics, AR and studio graphics ([Creative Review](https://www.creativereview.co.uk/premier-league-branding-by-dixon-baxi/)). |
| International production | Premier League, in-house from 2026-27 | This ends about 20 years of IMG running PLP ([SVG 2024](https://www.sportsvideo.org/2024/11/22/premier-league-to-establish-in-house-media-operations-business-for-2026-27-season/)). |
| Hawk-Eye | Goal-line technology and VAR replay tooling on PL coverage (unverified for 2026/27 scope) | Not researched in depth here. |

### 2. Catalogue of on-screen formats

"Duration" is **our guess** unless a source is given. No vendor or broadcaster we found publishes durations.

| Format | Trigger | Duration (our guess) | Audience |
|---|---|---|---|
| Score bug (teams, score, clock, added time, red cards) | Always on. Must be "immediately readable without interfering with the action" ([wTVision](https://www.wtvision.com/football-graphics-explained)) | Persistent | All |
| Lower third / name strap | Substitution, card, goal, a player in focus at a stoppage | 5-7 s | All |
| Tracked player tag (follows the player) | Player in possession (Prime Vision "Player ID") or threshold crossed (Speed Alert). Sky ran tracked tags with ChyronHego TRACAB ([TV Tech](https://tvtechnology.com/news/sky-sports-takes-chyronhegos-player-tracking-graphics-to-air)) | 3-5 s; sticks to the player | Casual |
| Stat pop-up (one number + label) | Threshold or record (DFL "exceptional performance") | 4-6 s | Casual |
| Comparison card (A vs B, 2-4 rows) | Stoppage, duel, pre-match | 6-8 s | Both |
| Momentum / xG timeline | Bundesliga Momentum: full screen at half-time/full-time, and live "when the flow shifts significantly", on a full reversal or at key events ([Bundesliga](https://www.bundesliga.com/en/bundesliga/news/bundesliga-match-facts-aws-match-momentum-34052)) | 8-10 s full screen | Analyst-leaning |
| Shot map | Half-time, after a shot in replay | 8-10 s | Analyst |
| Pass map / passing profile | Half-time, or a player-focus segment (BMF Passing Profile) | 8-10 s | Analyst |
| Heatmap / average positions | Bundesliga showed Average Positions live and xGoals in highlights at launch ([DTVE 2020](https://digitaltveurope.com/2020/05/26/bundesliga-taps-aws-for-new-features-as-season-restarts)) | 8-10 s | Analyst |
| AR line overlays (offside line, distance, speed tag) | VAR check, set piece, replay | Length of the replay | Both |
| Win probability | Swings after goals, red cards or substitutions ([Bundesliga](https://bundesliga.com/en/bundesliga/news/pressure-handling-win-probability-join-bundesliga-match-facts-powered-by-aws-21390)) | 5-6 s | Both |
| Live tactical map + momentum bar | Persistent on the alt feed. Prime Vision's bar shows "probability that either team scores in the next 10 seconds" ([TVBEurope](https://www.tvbeurope.com/media-consumption/prime-video-introudces-alternate-uefa-champions-league-feed-for-broadcast-innovations)) | Persistent (alt feed only) | Analyst |
| Passing options (top-3 likely receivers) | Live, on the alt feed (Prime Vision) | Duration of the possession | Analyst |
| HT/FT summary (stats table + 1 story) | Whistle | 10-15 s | All |

### 3. Bundesliga Match Facts: list, triggers, architecture

The 16 facts as of the Momentum launch ([BMF Zone](https://www.bundesliga.com/en/bundesliga/stats/bmf-zone/2025-2026)), with the presentation details that sources actually state:

| Fact | What it shows | Presentation notes (sourced) |
|---|---|---|
| xGoals | Chance that a shot is scored | After each shot. Highlights at launch (2020) |
| Shot Speed | Peak ball speed at the start of a shot, from tracking | Data Story Finder lets broadcasters flag goals over 100 km/h ([SVG Europe](https://www.svgeurope.org/blog/news-roundup/dfl-and-aws-add-shot-speed-to-bundesliga-match-facts/)) |
| Speed Alert | Top speeds per match and season | Top 3 updated after the 30th and 90th minutes. Alerts broadcasters when a record breaks ([About Amazon](https://www.aboutamazon.eu/news/amazon-web-services/new-bundesliga-match-fact-will-showcase-the-speed-on-the-pitch)) |
| Average Positions / Trends | Formation in and out of possession | Trends lets media partners choose any time window to compare |
| Attacking Zones | Final third split into 4 vertical zones; counts entries | Partners may overlay the zones live ([Amazon press 2021](https://press.aboutamazon.com/2021/2/aws-and-bundesliga-enhance-real-time-game-analysis-with-new-performance-stats-for-2021-season)) |
| Most Pressed Player | Pressure situations vs the team average | Broadcast graphics and app |
| Pressure Handling | "Escape rate" from high pressure | Broadcast and app |
| Passing Profile | xPass-based quality, direction and type | See file 08 |
| Win Probability | Uses goal difference, time left, xG, Skill, Set Piece Threat | Shown on swings |
| Set Piece Threat, Skill, Shot Efficiency, Keeper Efficiency, Ball Recovery Time | Team and player profiles | Not stated |
| Match Momentum | 0-10 threat score per team, computed every minute over the last 5 minutes, home minus away; resets each half | Full screen at HT/FT, plus live on swings |

**Architecture** ([AWS M&E blog](https://aws.amazon.com/blogs/media/behind-the-scenes-aws-real-time-architecture-for-bundesliga-match-facts)):

- EventBridge Scheduler → Lambda starts per-match ECS tasks.
- A WebSocket container ingests the live feed into MSK. Metadata arrives through API Gateway.
- Each fact runs in a stateful Fargate container per game and calls SageMaker endpoints.
- A Lambda pushes results back to the upstream data provider, which then reaches TV and the app.
- Results also go to Aurora for QC dashboards. Pydantic validates payloads and Datadog traces events.

Published figures are "over 3.6 million events" per match and events "collected, parsed, and analyzed within seconds". **No numeric end-to-end latency.** Newer AWS pages cite 200 million data points, so the figures across AWS pages disagree.

**Data Story Finder** ([AWS blog](https://aws.amazon.com/blogs/media/bundesliga-data-story-finder-delivering-fans-the-stories-they-love/)):

- Story templates evaluated against the facts. Each story type is its own Lambda workflow with its own guardrails.
- An editor Story Monitor sits before the Commentary Live System.
- Stories are available in German and English.

### 4. FIFA World Cup 2022 "Enhanced Football Intelligence"

FIFA's release ([FIFA](https://inside.fifa.com/innovation/media-releases/fifa-to-introduce-enhanced-football-intelligence-at-fifa-world-cup-2022-tm)) lists 11 metrics:

1. Possession control
2. Ball recovery time
3. Line breaks
4. Defensive line height and team length
5. Final third entries
6. Forced turnovers
7. Pressure on the ball
8. Expected goals
9. Team shape
10. Receptions behind midfield and defensive lines
11. Phases of play

They were shown "as augmented reality and traditional graphics", both in-match and post-match. "Offers to receive" is **not** in that release. It appears in FIFA Training Centre material (unverified; not fetched).

### 5. Editorial rules (what we could and could not source)

- **Restraint.** NBC, CBS, HBO and MSG art directors describe the trend as "very clean, flat", with packages that "get out of the way" ([SVG 2017](https://www.sportsvideo.org/?p=113461)). Vendor guides say event graphics should identify players "without distracting from the live action" (wTVision).
- **Football has few stoppages.** A graphics vendor at SVGE argued this is why near-live graphics add value ([SVGE](https://www.svgeurope.org/blog/headlines/svges-football-production-summit-graphics-makers-respond-to-need-for-speed/)). So "never during play" is too strict a rule. "Small during play, big at stoppages" fits what broadcasters do (our synthesis).
- **No published rule on word counts, frequency, or banning graphics during attacks.** Our rules below are design guesses. The closest numeric anchor is subtitling: Ofcom guidance is 160-180 wpm for pre-recorded TV. Ofcom proposed dropping these targets in 2023, and the outcome is unverified ([Ofcom review](https://ofcom.org.uk/tv-radio-and-on-demand/accessibility/access-services-review)).
- **Human in the loop.** DFL editors can veto stories. The Nickelodeon producers stress that "normal NFL-game coverage" must stay intact ([SVG 2025](https://www.sportsvideo.org/2025/01/10/nfl-playoffs-2025-cbs-sports-and-nickelodeon-go-beyond-spongebob-universe-boost-ar-technology-with-latest-slime-filled-altcast/)).

**Accessibility.**

- WCAG 2.1 asks for text contrast of 4.5:1, or 3:1 for large text (18 pt / 14 pt bold), and about 3:1 for non-text graphics ([W3C](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html)).
- The FA's 2017 colour-blindness guidance, backed by UEFA, names TV graphics as a problem area. It lists problem pairs such as red/black, red/green/orange, blue/purple and yellow/orange. About 8% of men and 0.5% of women have red/green colour blindness ([The FA](https://www.thefa.com/news/2017/jun/19/colour-blindness-guidance-190617)).
- So team colour alone must never carry meaning. Add the team abbreviation and a shape or position cue.

### 6. Personalisation precedents

| Precedent | What it shows |
|---|---|
| Prime Video X-Ray (TNF, 2019) | Next Gen Stats on demand: flip the phone or press "up" on Fire TV ([Amazon](https://press.aboutamazon.com/news-releases/news-release-details/amazon-prime-video-launches-new-features-thursday-night-football)) |
| Prime Vision / Prime Insights | AI features (Defensive Alerts, Pocket Health) tested on an alt feed, then promoted to the main feed. Built with AWS ([SVG](https://www.sportsvideo.org/?p=291014)) |
| Prime Vision UCL 2025/26 | Tactical Map, Momentum bar, Physical Insights, xG/xGOT/xPass/xSave, Passing Options, Player ID. Main broadcast kept clean |
| PL Data Zone | Opt-in data mode for one match per round |
| Nickelodeon NFL (CBS, since 2021) | Kids altcast: AR slime, a "CatDog" down-and-distance graphic, Dora explaining penalties. Real game coverage stays primary. Run on Unreal 5.4 / Pixotope |
| Apple TV MLS | One consistent package across all matches, built on Vizrt. Advanced data from Sportec Solutions, the DFL's data company ([MLS](https://www.mlssoccer.com/news/mls-season-pass-talent-pairings-live-event-production-plan-unveiled)) |
| Multi-language | DFL stories are produced in DE and EN. AI Live Ticker is described as "multilingual" (Bedrock) |
| Second screen | 54% of UK Euro 2012 viewers used a second device, 68% of them for tournament content ([SportBusiness](https://media.sportbusiness.com/news/more-than-50-of-uk-football-fans-used-second-screen-while-watching-euro-2012)) |

We found no DAZN or TNT data-feed specifics (unverified).

## So what for us

This research feeds **Render** (the cue `layout`, `ttl_ms` and trigger rules) and **Personalise** (separate cue streams per audience). It directly shapes **F Graphics Desk**, **B Speed Trap**, **C One Number**, **A TwinCast**, **10 Story Time** and **13 Recap Dial**.

**Recommendation: a 10-layout "graphics grammar".** Every cue's `layout` must be one of these values. The scheduler enforces three things:

- **(a) Play-state gating.** Only `tag`, `pop` and `bar` may appear while the ball is in play in the final third.
- **(b) One slot rule.** At most one transient graphic per screen region at a time.
- **(c) `ttl_ms` from words.** `ttl_ms = clamp(1000 + words × 360, min, max)`. The 360 ms per word is our guess, slightly slower than 180 wpm, because viewers are also watching play.

| layout | Use | Allowed in live play? | min-max s (our guess) | Cooldown (our guess) |
|---|---|---|---|---|
| `bug` | Score/clock (+ One Number slot) | Yes, persistent | — | — |
| `tag` | Tracked player tag (name + 1 metric) | Yes | 3-5 | 20 s per player |
| `pop` | One number + up to 8 words | Yes, if no shot in last 3 s | 4-6 | 45 s global |
| `strap` | Lower third, up to 12 words | Stoppage only | 5-7 | 30 s |
| `compare` | 2-4 row A vs B card | Stoppage only | 6-8 | 90 s |
| `bar` | L-bar / momentum strip (alt feed) | Yes (analyst stream) | Persistent | — |
| `pitch` | Shot, pass or heat map, avg positions (full or half screen) | Replay or HT only | 8-10 | 5 min |
| `ar` | Lines and distances drawn on the frame | Replay only | Length of replay | — |
| `prob` | Win probability or "called it" meter | Stoppage | 5-6 | On swings ≥10 pp only |
| `summary` | HT/FT card + 1 story | Whistle | 10-15 | — |

**Ideas mapped to layouts**

| Idea | Primary layouts |
|---|---|
| A TwinCast | `tag`, `pop`, `ar` (CV-vs-truth on replay), `summary` (grading) |
| B Speed Trap | `tag` (threshold), `pop` (shot speed → consequence), `compare` (top 3 at 30'/90', copying Speed Alert) |
| C One Number | `bug` slot + `pop` on change; nothing else in this mode |
| D Chalk Talk | `ar`, `pitch` |
| F Graphics Desk | All layouts. The producer takes or holds, like the DFL Story Monitor |
| 03 Dive Judges | `pop` (0-10 score), `compare` |
| 04 Duel Card | `compare` |
| 05 Set-Piece X-Ray | `ar`, `pitch` |
| 10 Story Time | `pop`, `strap` with kid wording, plus a playful `ar` celebration on goals (the Nickelodeon pattern). Football stays primary |
| 12 Jargon Buster | `strap` |
| 13 Recap Dial / 22 Half-Time Talk | `summary`, `pitch` |
| 15 Record Watch | `pop` (DFL "exceptional performance" trigger) |
| 21 Called It | `prob`, `summary` |
| 23 Safe Break | Schedules `strap`/`compare` into stoppages |

Also copy the DFL trigger taxonomy (`event`, `threshold`, `summary`) as a `trigger` field, and the Momentum maths (per-minute, 5-minute window, reset each half) for a cheap `bar`.

## Reuse: code & links

```python
# graphics_grammar.py: layout rules plus a gate the cue scheduler calls (durations are our guesses)
from dataclasses import dataclass
LAYOUTS = {  # name: (min_s, max_s, live_ok, region, cooldown_s)
  "tag": (3, 5, True, "player", 20), "pop": (4, 6, True, "upper_right", 45),
  "strap": (5, 7, False, "lower", 30), "compare": (6, 8, False, "lower", 90),
  "pitch": (8, 10, False, "full", 300), "ar": (2, 12, False, "frame", 0),
  "prob": (5, 6, False, "upper_right", 60), "summary": (10, 15, False, "full", 0),
  "bar": (0, 0, True, "lbar", 0), "bug": (0, 0, True, "bug", 0)}

def ttl_ms(layout: str, text: str) -> int:
    lo, hi, *_ = LAYOUTS[layout]
    if hi == 0: return 0                       # persistent
    return int(min(hi*1000, max(lo*1000, 1000 + 360*len(text.split()))))

@dataclass
class PlayState: in_play: bool; final_third: bool; replay: bool; secs_since_shot: float

def allowed(layout: str, s: PlayState, busy_regions: set, last_shown: dict, now: float) -> bool:
    lo, hi, live_ok, region, cd = LAYOUTS[layout]
    if region in busy_regions: return False                      # one graphic per region
    if now - last_shown.get(layout, -1e9) < cd: return False     # cooldown
    if layout in ("pitch", "ar") and not (s.replay or not s.in_play): return False
    if s.in_play and not live_ok: return False                   # stoppage-only layouts
    if layout == "pop" and s.secs_since_shot < 3: return False   # don't cover the shot moment
    return True
```

```python
# Bundesliga-style momentum (per minute, last 5 min, reset each half), our simplified weights
def momentum(events, minute, half_start):
    w = {"shot": 1.0, "xg": 6.0, "box_touch": 0.5, "final_third_entry": 0.3, "corner": 0.4}
    win = [e for e in events if max(half_start, minute-5) <= e["min"] < minute]
    score = {t: min(10, sum(w.get(e["type"], 0) + w["xg"]*e.get("xg", 0) for e in win if e["team"] == t)) for t in ("home", "away")}
    return score["home"] - score["away"]   # -10..+10 for the `bar` layout
```

```python
# WCAG contrast check for team-colour text on graphics (4.5:1 normal, 3:1 large)
def _lum(hex_):
    c = [int(hex_[i:i+2], 16)/255 for i in (1, 3, 5)]
    c = [x/12.92 if x <= 0.03928 else ((x+0.055)/1.055)**2.4 for x in c]
    return 0.2126*c[0] + 0.7152*c[1] + 0.0722*c[2]
def contrast(a, b): la, lb = sorted((_lum(a), _lum(b)), reverse=True); return (la+0.05)/(lb+0.05)
```

Links: BMF architecture blog · Data Story Finder blog · BMF Zone · FIFA EFI metric pages (fifatrainingcentre.com/en/fwc2022/efi-metrics/) · Opta Graphics (statsperform.com/broadcast/) for template/trigger ideas.

## Sources

- Bundesliga Match Facts Zone 2025-26 — https://www.bundesliga.com/en/bundesliga/stats/bmf-zone/2025-2026 — accessed 20 Oct 2026
- Bundesliga: Match Momentum (16th BMF) — https://www.bundesliga.com/en/bundesliga/news/bundesliga-match-facts-aws-match-momentum-34052 — accessed 20 Oct 2026
- Bundesliga: Pressure Handling & Win Probability — https://bundesliga.com/en/bundesliga/news/pressure-handling-win-probability-join-bundesliga-match-facts-powered-by-aws-21390 — accessed 20 Oct 2026
- AWS M&E: Behind the scenes, real-time architecture for BMF — https://aws.amazon.com/blogs/media/behind-the-scenes-aws-real-time-architecture-for-bundesliga-match-facts — accessed 20 Oct 2026
- AWS M&E: Bundesliga Data Story Finder — https://aws.amazon.com/blogs/media/bundesliga-data-story-finder-delivering-fans-the-stories-they-love/ — accessed 20 Oct 2026
- Amazon press: Attacking Zones, Most Pressed Player, Average Positions Trends (2021) — https://press.aboutamazon.com/2021/2/aws-and-bundesliga-enhance-real-time-game-analysis-with-new-performance-stats-for-2021-season — accessed 20 Oct 2026
- About Amazon EU: Speed Alert — https://www.aboutamazon.eu/news/amazon-web-services/new-bundesliga-match-fact-will-showcase-the-speed-on-the-pitch — accessed 20 Oct 2026
- SVG Europe: Shot Speed added to BMF — https://www.svgeurope.org/blog/news-roundup/dfl-and-aws-add-shot-speed-to-bundesliga-match-facts/ — accessed 20 Oct 2026
- Digital TV Europe: Bundesliga taps AWS (2020) — https://digitaltveurope.com/2020/05/26/bundesliga-taps-aws-for-new-features-as-season-restarts — accessed 20 Oct 2026
- SVG: PLP + Genius Sports Premier League Data Zone — https://www.sportsvideo.org/2023/10/05/premier-league-productions-partners-with-genius-sports-to-deliver-premier-league-data-zone/ — accessed 20 Oct 2026
- Genius Sports SAOT for the Premier League (press release) — https://www.silicon.co.uk/press-release/genius-sports-to-supply-semi-automated-offside-technology-for-the-premier-league — accessed 20 Oct 2026
- Business Wire: CBF adopts Genius SAOT (Nov 2025) — https://www.businesswire.com/news/home/20251126518075/en/ — accessed 20 Oct 2026
- SVG: Premier League in-house media operations 2026-27 — https://www.sportsvideo.org/2024/11/22/premier-league-to-establish-in-house-media-operations-business-for-2026-27-season/ — accessed 20 Oct 2026
- Creative Review: DixonBaxi PL on-air branding — https://www.creativereview.co.uk/premier-league-branding-by-dixon-baxi/ — accessed 20 Oct 2026
- TV Technology: Sky Sports ChyronHego player tracking graphics — https://tvtechnology.com/news/sky-sports-takes-chyronhegos-player-tracking-graphics-to-air — accessed 20 Oct 2026
- FIFA: Enhanced football intelligence at FIFA World Cup 2022 — https://inside.fifa.com/innovation/media-releases/fifa-to-introduce-enhanced-football-intelligence-at-fifa-world-cup-2022-tm — accessed 20 Oct 2026
- TVBEurope: Prime Vision alternate UCL feed — https://www.tvbeurope.com/media-consumption/prime-video-introudces-alternate-uefa-champions-league-feed-for-broadcast-innovations — accessed 20 Oct 2026
- SVG: Prime Video TNF 2025 Prime Insights — https://www.sportsvideo.org/?p=291014 — accessed 20 Oct 2026
- Amazon press: Prime Video TNF features / X-Ray — https://press.aboutamazon.com/news-releases/news-release-details/amazon-prime-video-launches-new-features-thursday-night-football — accessed 20 Oct 2026
- SVG: CBS/Nickelodeon NFL playoff altcast 2025 — https://www.sportsvideo.org/2025/01/10/nfl-playoffs-2025-cbs-sports-and-nickelodeon-go-beyond-spongebob-universe-boost-ar-technology-with-latest-slime-filled-altcast/ — accessed 20 Oct 2026
- MLS: Apple/MLS live production plan — https://www.mlssoccer.com/news/mls-season-pass-talent-pairings-live-event-production-plan-unveiled — accessed 20 Oct 2026
- SVG: Sports Graphics Forum, clean look (2017) — https://www.sportsvideo.org/?p=113461 — accessed 20 Oct 2026
- SVG Europe: Football Production Summit, graphics need for speed — https://www.svgeurope.org/blog/headlines/svges-football-production-summit-graphics-makers-respond-to-need-for-speed/ — accessed 20 Oct 2026
- wTVision: Football graphics explained (vendor guide) — https://www.wtvision.com/football-graphics-explained — accessed 20 Oct 2026
- Stats Perform: Opta Graphics launch — https://www.businesswire.com/news/home/20200224005575/en/Stats-Perform-Launches-Opta-Graphics-Intuitive-Multimedia — accessed 20 Oct 2026
- W3C: Understanding SC 1.4.3 Contrast (Minimum) — https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html — accessed 20 Oct 2026
- The FA: Colour blindness guidance (2017) — https://www.thefa.com/news/2017/jun/19/colour-blindness-guidance-190617 — accessed 20 Oct 2026
- Ofcom: Access services review (subtitle speed 160-180 wpm) — https://ofcom.org.uk/tv-radio-and-on-demand/accessibility/access-services-review — accessed 20 Oct 2026
- SportBusiness: Second screen during Euro 2012 — https://media.sportbusiness.com/news/more-than-50-of-uk-football-fans-used-second-screen-while-watching-euro-2012 — accessed 20 Oct 2026
