**Category: Best Use of Microsoft Foundry**

# Audio Stands

_OWNER: A (potencialbg). Text to paste into the Innovation Studio form (Stage 9). Every number is from
[`eval/report.json`](eval/report.json) or a cited research file; Stage 9b refreshes them and adds the video link._

**Tagline:** A seat in the stands for fans who can't see the pitch: a crowd, a ball and a commentator that rise with the match.

## Links

- **Demo (no login):** https://lively-ocean-0efe4ae0f.2.azurestaticapps.net/ (headphones; add `?radar=1` to see the sound)
- **Video (1:52):** _YouTube link added in Stage 9b_
- **Repo:** https://github.com/nikikrustev/BerbataAI
- **Team:** Berbata AI (entry 126726): Nikolay Krastev and potencialbg

## Elevator pitch

Audio Stands puts a blind or partially sighted fan in the stands. A crowd that reacts at each end, a ball you can hear
move from left to right and a heartbeat on your phone all rise with the match, and the commentator's voice builds
*before* the big chance, because our **Director agent on Microsoft Foundry** (built with **Microsoft Agent Framework**)
sees the next ten seconds that the fan hasn't heard yet. A spoiler firewall keeps that look-ahead honest: the Director
outputs only a tension plan, code verifies every line, and we measured **0 spoiler leaks in 70 lines** with every spoken
number checked against the synthetic ground truth. At any moment the fan can ask the same voice "where's the ball?" out
loud, through **Foundry Voice Live** and our own playhead-clamped tools, also served as an MCP server. The match is a
zero-backend replay on **Azure Static Web Apps**, the voice is **Azure Speech** HD, and the live questions run through an
**Azure Container Apps** relay, traced in **Application Insights**.

## Microsoft technology we shipped

| Technology | What it does in Audio Stands |
|---|---|
| **Microsoft Foundry** (gpt-5-mini) | The Director agent: plans the tension of each build-up from a 10 s look-ahead. 4 calls, 0 fallbacks on the judge cut. |
| **Microsoft Agent Framework** | The workflow Director → Commentator → Verifier → TTS, with the Director as an `Agent` on the Foundry chat client. |
| **Foundry Voice Live** (gpt-realtime-2.1-mini) | Live spoken questions, answered in the commentator's own voice with our 8 tools. 31/31 answered, 0 spoiler hits, median 1.14 s to the first answer audio. |
| **Foundry evaluations** | Our numeric-truth grader as a code-based custom evaluator (preview): 4/4 passed. |
| **Azure Speech** | The commentary pre-rendered in an HD neural voice (`en-US-Brian:DragonHDLatestNeural`), plus the offline answers and refusal clips. |
| **Azure Static Web Apps** (Free) | Hosts the whole replay: no backend is needed to hear the match. |
| **Azure Container Apps** + Container Registry | The relay for live questions and the Stats MCP server; scales to zero. |
| **Application Insights** + Log Analytics | OpenTelemetry traces of every Director run. |
| **Azure Developer CLI + Bicep** | Provisioning and deploys (`azd up`). |
| **Azure MCP Server** + **GitHub Copilot Agent Mode** | Read-only checks of our deployed resources from VS Code. Copilot wrote none of our code. |
| **GitHub Actions** | CI with WCAG 2.2 AA axe tests, and an uptime check every 6 h. |

## Testing instructions for judges

1. Open https://lively-ocean-0efe4ae0f.2.azurestaticapps.net/?radar=1 in Chrome or Edge, ideally with headphones.
2. Press **Start**, the lower big button (or Enter). About five seconds in, the voice builds ("Navy coming... Olvholm... here's a chance!")
   four seconds before the header, and the crowd rises with it.
3. Press **Ask the commentator**, the upper big button (or A), wait for the beep and ask anything about the match:
   "What's the score?", "Where is Fenford?", "Who wins?" (it won't tell you). Allow the microphone when asked. Press it
   again during an answer to stop it at once. **Quick questions** gives **Where's the ball?** and three more (works offline).
   The live relay sleeps when idle: if the first live question says live questions aren't available, wait 30 seconds and ask again.
4. **Next big moment** jumps to the next chance. **Settings**: your end (Reds or Navy), crowd level, vibration, and
   **Fine-tune every sound**, the per-sound mixer a helper sets up once with the fan (saved on that device).
5. On an Android phone in Chrome you also feel it: a heartbeat with the tension, and a pattern for each shot and goal.
   iPhone browsers can't vibrate, so iPhone gets the audio only.

## Inspiration

In RNIB's 2022 research, blind and partially sighted fans scored ordinary TV football commentary 6.1 out of 15. They want
one voice that says where the ball is, in real time, and they hate the lag: the crowd roars before the description says
why. Every service they have today is one-way and the same for everyone.

## What it does

A whole match experience for the ears: the crowd at each end reacts to what happens, the crowd end nearest the ball
lifts as play moves, the phone vibrates with the tension, and a commentator describes the ball first, then builds up
before the chances. On a phone the screen is two big halves, found by touch: Ask on top (press, speak, the commentator
answers; press again to stop it) and Pause/Resume below, each press confirmed by a vibration and a short tone. The fan
picks their end, the crowd level and the vibration. A sighted friend or carer can set every sound once with them in the
mixer (commentator, crowd, chants, reactions, kicks, whistle), and that mix is saved on their phone, so every fan gets
their own.

## How we built it

A seeded generator plays a synthetic match (CDF events, 25 Hz ball). Python turns it into signals: xG, tension, danger
and the crowd's mood per end. The Director agent on Foundry plans each build-up from a 10 s look-ahead; template lines
are verified in code and pre-rendered in an Azure Speech HD voice. The browser plays it all with Web Audio and the
Vibration API from static files. A FastAPI relay on Container Apps connects the fan's microphone to Foundry Voice Live
and runs our playhead-clamped tools. Nikolay built the match, sound stage, haptics, Q&A brain and MCP server;
potencialbg built the Microsoft side and finished Nikolay's Stage 8–9 items. We worked stage by stage with Claude Code,
and used GitHub Copilot Agent Mode with the Azure MCP Server for read-only checks of our deployment.

## Challenges we ran into

- **Spoilers.** A look-ahead commentator can give the result away in one word. The Director sees only an allow-list of
  features, never the outcome, and a test proves it by rewriting each shot's ending.
- **Real time.** A build-up must be planned, verified and spoken within about 6 s of the shot entering the look-ahead.
  We measured 10/10 within budget, p95 3.56 s, and found that a cold first call alone would miss it, so the service warms up first.
- **No money.** We stayed on the Azure free account: Static Web Apps Free, a relay that scales to zero, and a 1 GB/day
  logging cap.

## Accomplishments that we're proud of

- 0 spoiler leaks in 70 lines, and 0 spoiler hits in 31 live spoken questions.
- A live spoken answer in the commentator's own voice, median 1.14 s after the fan stops speaking.
- Accessibility CI that fails on any axe violation (WCAG 2.2 AA tags) at three viewports.

## What we learned

A blind fan needs to hear where the ball is every few seconds: our first cut went quiet for 18 s, and we changed the
planner so the ball is never silent in play for more than about 9 s. Silence and the crowd carry meaning too.

## What's next

Testing with blind and partially sighted fans (we haven't yet: the eyes-closed listening test result goes here, TODO, once
it has run), more detail levels, a live event path instead of the replay, and more languages.
