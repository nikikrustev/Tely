**Category: Best Use of Microsoft Foundry**

# Tely (said "telly")

**A seat in the stands for fans who can't see the pitch: a crowd, a commentator and a phone that rise with the match, and a voice you can ask.**

- **Live demo (no login):** https://lively-ocean-0efe4ae0f.2.azurestaticapps.net/?view=laptop&radar=1
- **Video (under 2 min):** >>> YOUTUBE URL GOES HERE <<<
- **Code:** https://github.com/nikikrustev/BerbataAI
- **Team:** Berbata AI (entry 126726): Nikolay Krastev and potencialbg

## Judges: hear it in under 60 seconds

Open the demo link in Chrome or Edge, with headphones if you have them.

1. Press **Start** (or Space). About 5 s in, the voice builds ("Navy coming... Olvholm... here's a chance!") four seconds *before* the header, and the crowd rises with it.
2. Press **Ask the commentator** (or Enter), wait for the beep and ask out loud: "What's the score?", "Who wins?" (it won't tell you). Press it again mid-answer and it stops.
3. Say "speak Spanish": the answers and the match switch language. Below the radar, **Director's notes** show what the agents decided, after each moment.

If the first question says live questions aren't available, the relay was asleep: wait 30 s and ask again. **Quick questions** work offline.

## The problem

In RNIB's 2022 research, blind and partially sighted fans scored ordinary TV football commentary 6.1 out of 15. They want one voice that says where the ball is, in real time, and they hate the lag. What they have today is one-way and the same for everyone.

## What it does

The crowd, the commentary and the vibration come **from one event stream**, so they can't drift apart.

- **A look-ahead commentator.** Our Director agent sees the next 10 s and builds the voice before the chance. A **spoiler firewall** keeps it honest: the Director never sees the outcome, outputs only a tension plan, and code checks every line.
- **A crowd at each end** that lifts where the ball is, and ball-first commentary every few seconds.
- **Ask by voice** (Foundry Voice Live) with press-to-interrupt. Offline quick questions: *Where's the ball?*, *What's the score?*, *What just happened?*, *What did I miss?*, *Recap so far*. A spoken recap also plays when the match ends.
- **Seven languages** (English, Bulgarian, Spanish, Arabic, French, German, Hindi) for commentary, quick answers and live answers, in one multilingual voice.
- **Listening modes:** screen-reader mode (your screen reader reads each line at your speed), one-ear mono with a position tone, and *Key moments only* or *Full radio*.
- **Follow a player:** a cue, a buzz and the name each time they get the ball.
- **Haptics** on Android, a **0–100 mixer** a helper sets once (or "whistle down by 5" by voice), and **low-data mode** for slow connections.
- Built for screen readers and touch, with **WCAG 2.2 AA** axe tests in CI.

## What we measured

From `eval/report.json` on the judge cut (8 synthetic minutes); the translated lines are checked by a CI test.

| Measure | Result |
|---|---|
| Spoiler leaks in commentary | **0** in 70 lines, and 0 in 6 × 70 translated lines |
| **Planted errors caught** (names, scores, minutes, invented numbers, outcome words) | **148/148** commentary, **1015/1015** answers; 0 clean lines blocked |
| Verifier switched off | 0/1163 caught |
| Director handed the outcome | input unchanged 4/4; replies carrying it rejected 8/8 |
| Director on Foundry (gpt-5-mini) | 4 calls, **0 fallbacks**, 10/10 build-ups inside the 5.8 s budget (p95 3.56 s) |
| Live spoken questions | **31/31** answered, **0** spoiler hits, **p50 1.14 s** to the first answer audio |
| Event → commentary heard | scheduled at the event (p50 0.0 s), heard a median 84 ms late |
| Goal confirmed → crowd roar | 0.0 s (scheduled) |

The planted-error thresholds were committed before the first run. That run failed (a checker bug blocked 18.9 % of clean answers); we fixed the checker, not the threshold. **We haven't run the listening test with blind fans yet.**

## How it maps to the brief

| Brief | Tely |
|---|---|
| Ingest | A seeded synthetic match: CDF events, ball at 25 Hz, 22 players at 5 Hz |
| Interpret | Per second: win probability, tension, danger, each end's crowd mood. Per shot: xG |
| Explain | Director plans; templates say why; `explain_moment` answers "why?" |
| Render | Voice, crowd, vibration, plus `overlays.json` and WebVTT in every language for any renderer |
| Personalise | End, language, detail, listening mode, followed player, sound mix, low data |
| (ii) Real-time | Players named, "where is …", player stats. **Not done:** pass difficulty, speeds, video auto-eventing |
| (iii) Narrative | Build-ups, catch-ups, spoken recaps |
| (iv) Explainability | Tension plans, Director's notes, an auditable firewall |
| (v) Data | An open, seeded generator with a realism report (it misses 2 targets) |
| (vi) Multi-language | Seven languages. **Not yet:** the page's own words |

## Microsoft technology

- **Microsoft Foundry** (gpt-5-mini): the Director agent and the translations. **Foundry evaluations**: our custom numeric-truth evaluator, including the planted errors.
- **Microsoft Agent Framework**: Director → Commentator → Verifier → TTS.
- **Foundry Voice Live** (gpt-realtime-2.1-mini): live questions with 11 playhead-clamped tools, also an MCP server.
- **Azure Speech**: HD and multilingual neural voices.
- **Azure Static Web Apps**, **Container Apps** (relay, scales to zero), **Application Insights**, **azd + Bicep**, **GitHub Actions**.
- **GitHub Copilot + Azure MCP Server**: read-only deployment checks only. Copilot wrote none of our code.

## What's next

Testing with blind and partially sighted fans, native-speaker review of each language, the page's own words translated, and a live event feed.
