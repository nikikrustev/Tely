# BerbataAI: notes for Claude

Team Berbata AI (Innovation Studio entry 126726) is building for the "Inside the Game" hackathon (Microsoft × Premier League):
the Synthetic Match Insights Engine. The pipeline has five stages: Ingest → Interpret → Explain → Render → Personalise.

## Read before starting work
1. `stoynev research/INDEX.md` lists the research library, one file per topic. Every file has a TL;DR, Findings,
   "So what for us", reusable code and dated sources. Read the TL;DR of the relevant files before researching
   or building anything. Don't redo work that is already there.
2. `Berbata_Hackathon_Intel.md` has the brief and a snapshot of the 332 competing projects.
3. `Berbata_Idea_Shortlist.html` and `Berbata_Idea_Brainstorm.html` have our candidate ideas. The shortlist recommended TwinCast, but the user has since chosen to focus on Audio Stands (below).
   Don't edit these three files.

## Current focus (from the user, 20 Oct 2026)
"Audio Stands" (working name): the best audio experience for a blind fan. It combines brainstorm ideas 20 Home End and
17 Heartbeat: an immersive reactive crowd, an AI commentator who builds emotion because the pipeline knows what is
coming, and the fan can talk to the commentator and ask questions. See the "Current focus" section in INDEX.md.

## Two people, two Claudes (from 20 Oct 2026)
Read `TEAM_SPLIT.md` before editing anything. Person A (potencialbg) owns all Microsoft software. Person B (Nikolay) has
no Microsoft in his lane: no Azure, Foundry, Speech or Copilot calls, packages or keys. **One file, one owner:** edit only
files your person owns in TEAM_SPLIT.md's "File ownership". Put anything else under "HANDOFF to A/B" in the PR description.
Work on short `a/<topic>` or `b/<topic>` branches and open PRs into main daily. If you don't know whose session you are,
ask before editing.

## Hard facts (verified 20 Oct 2026, see `stoynev research/12-judging-criteria-and-rules.md`)
- Submissions close **27 Oct 2026, 23:59 PT**. Judging runs to 10 Nov, and the demo must stay up and free until then.
- Deliverables: a video **under 2 minutes** (YouTube/Vimeo), a **public** GitHub repo, a working demo link, and a pitch naming the Microsoft tech.
- Five criteria at 20% each: Technological Implementation, Agentic Design & Innovation, Real-World Impact,
  UX & Presentation, Category fit. There are four category prizes; Best Azure Cloud Native Integration looks least crowded.
- **Synthetic data only.** Don't ship anything trained on, or derived from, real match data: no StatsBomb open data,
  no Karun Singh xT grid, no LaurieOnTracking EPV grid.
- Licence traps: Ultralytics YOLO is AGPL, so use RF-DETR (Apache) instead. The NBJW and PnLCalib calibration tools are GPL.
  The jersey-number pipeline is non-commercial. `sv.ByteTrack` was removed in supervision 0.31; use the `trackers` package.

## Conventions
- New research goes in `stoynev research/NN-topic.md` using the same section layout. Add a row to INDEX.md and move items
  through its "Next topics" queue. Commit and push after each file.
- Mark anything unverified as "(unverified)". Never invent numbers.
