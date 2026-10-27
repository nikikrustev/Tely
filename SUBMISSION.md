**Category: Best Use of Microsoft Foundry**

# Tely (said "telly")

**A seat in the stands for fans who can't see the pitch: a crowd, a commentator and a phone that rise with the match, and a voice you can ask.**

- **Live demo (no login):** https://lively-ocean-0efe4ae0f.2.azurestaticapps.net/?view=laptop&radar=1
- **Video (under 2 min):** >>> YOUTUBE URL GOES HERE <<<
- **Code:** https://github.com/nikikrustev/BerbataAI
- **Team:** Berbata AI (entry 126726): Nikolay Krastev and potencialbg

## Judges: hear it in under 60 seconds

Open the demo link above in Chrome or Edge, with headphones if you have them.

1. Press **Start** (or Space). About 5 s in, the voice builds ("Navy coming... Olvholm... here's a chance!") four seconds *before* the header, and the crowd rises with it.
2. Press **Ask the commentator** (or Enter), wait for the beep and ask out loud: "What's the score?", "Where's the ball?", "Who wins?" (it won't tell you). Press it again mid-answer and it stops at once.
3. Say "speak Spanish" (or pick **Commentator language** in **Setup**): the answers and the match commentary switch language mid-match.

The live relay sleeps when idle. If the first question says live questions aren't available, wait 30 s and ask again; **Quick questions** works offline.

## The problem

In RNIB's 2022 research, blind and partially sighted fans scored ordinary TV football commentary 6.1 out of 15. They want one voice that says where the ball is, in real time, and they hate the lag: the crowd roars before the description says why. What they have today is one-way and the same for everyone.

## What it does

Tely generates the crowd, the commentary and the vibration **from one event stream**, so they can't drift apart.

- **A look-ahead commentator.** Our Director agent sees the next 10 s the fan hasn't heard yet and builds the voice before the chance. A **spoiler firewall** keeps it honest: the Director never sees the outcome and outputs only a tension plan, and code checks every line for truth and spoilers.
- **A crowd at each end** that reacts to the play, and lifts at the end nearest the ball, so the fan hears where play is. The commentary puts the ball first, every few seconds.
- **Ask by voice** (Foundry Voice Live) in the commentator's own voice, with **press-to-interrupt**. The relay injects the playhead, so the model can't look ahead. **Quick questions** work offline: *Where's the ball?*, *What's the score?*, *What just happened?*, *What did I miss?*. After each Ask, a short catch-up covers what you missed.
- **Six languages**: English, Bulgarian, Spanish, Arabic, French and German for the match commentary and the live answers, in one multilingual voice. You pick it in Setup or ask for it out loud.
- **Haptics** on Android: a heartbeat that follows the tension, and a pattern for each shot and goal.
- **The fan's own mix.** A helper sets every sound once with the fan on a 0–100 scale (commentator, crowd, chants, reactions, kicks, whistle), and it's saved on the device. The fan can also change it by voice: "turn the whistle down by 5".
- **Choose your end** (Reds or Navy), crowd level, vibration, Bluetooth delay calibration, **Next big moment**, and a "Learn the sounds" tour.
- **Built for a screen reader and touch.** On a phone, the screen is two big halves (Ask on top, Start/Pause below). On a laptop, use Space, Enter and Esc. CI fails on any **axe WCAG 2.2 AA** violation, at three viewports, in light and dark, with and without reduced motion.

## What we measured

From `eval/report.json`, on the judge cut (8 synthetic minutes).

| Measure | Result |
|---|---|
| Spoiler leaks in commentary | **0** in 70 lines |
| Truth check / spoken numbers verified | **70/70** lines, **10/10** numbers |
| Director on Foundry (gpt-5-mini) | 4 calls, 4 plans, **0 fallbacks**, 488 tokens per call |
| Plan → verify → speech per build-up | **10/10** inside the 5.8 s budget, p50 2.98 s, p95 3.56 s |
| Numeric truth as a Foundry custom evaluator | **4/4** passed |
| Live spoken questions (Voice Live) | **31/31** answered, **0** spoiler hits, 43 tool calls |
| End of question → first answer audio | **p50 1.14 s**, p95 1.82 s |
| Offline router | 31/31 correct: answer 18/18, clarify 4/4, redirect 2/2, refuse 7/7 |

**Honest limits.** 21 of the 70 lines (30%) use a shorter fallback text to fit their gap. Spoiler lift can't be judged yet: n = 2. **We haven't run the listening test with blind or partially sighted fans yet.**

## How it maps to the brief

| Brief | Tely |
|---|---|
| Ingest | A seeded synthetic match: CDF events, the ball at 25 Hz, 22 players at 5 Hz |
| Interpret | Per second: win probability, tension, danger and each end's crowd mood. Per shot: xG. |
| Explain | The Director plans the build-up; templates say why each moment matters; `explain_moment` answers "why?" live |
| Render | A pre-rendered Azure Speech HD voice, Web Audio crowd and cues, phone vibration, a sound radar, all on a timed cue track |
| Personalise | End, language, the whole sound mix, vibration, and questions asked by voice |
| (ii) Real-time intelligence | Players named in the commentary, plus "where is …" and player-stat tools. **Not done:** pass difficulty, ball and shot speed, video auto-eventing. |
| (iii) Narrative | Build-ups, "What just happened?", "What did I miss?", and a catch-up after each Ask. **Not done:** half-time and full-time recaps. |
| (iv) Explainability | Tension plans, `explain_moment`, and a firewall you can audit |
| (v) Data innovation | An open, seeded generator with a realism report (it misses 2 targets, and we say so) |
| (vi) Multi-language | Six languages for the commentary and the live answers. **Not yet:** the offline presets and the captions, which are English only. |

We don't yet offer an analyst/casual split or a player-focus mode.

## Microsoft technology

- **Microsoft Foundry** (gpt-5-mini): the Director agent and the translations, plus a **Foundry evaluation** with our custom numeric-truth evaluator.
- **Microsoft Agent Framework**: the workflow Director → Commentator → Verifier → TTS.
- **Foundry Voice Live** (gpt-realtime-2.1-mini): live spoken questions, with 10 playhead-clamped tools, also served as an MCP server.
- **Azure Speech**: HD neural and multilingual voices.
- **Azure Static Web Apps**: the zero-backend replay.
- **Azure Container Apps** and Container Registry: the relay, which scales to zero.
- **Application Insights**: OpenTelemetry traces.
- **azd and Bicep**: provisioning and deploys. **GitHub Actions**: CI and the uptime check.
- **GitHub Copilot Agent Mode with the Azure MCP Server**: read-only checks of our deployment only. Copilot wrote none of our code.

## What's next

- Test with blind and partially sighted fans, one to one.
- Spoken half-time and full-time recaps.
- A "follow my player" mode, and a "key moments only" detail level.
- Native-speaker review of every language.
- A live event feed instead of the replay.
