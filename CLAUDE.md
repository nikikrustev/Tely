# BerbataAI: notes for Claude

Team Berbata AI (Innovation Studio entry 126726) is building for the "Inside the Game" hackathon (Microsoft × Premier League):
the Synthetic Match Insights Engine. The pipeline has five stages: Ingest → Interpret → Explain → Render → Personalise.

## Read before starting work
1. `stoynev research/INDEX.md` lists the research library, one file per topic. Every file has a TL;DR, Findings,
   "So what for us", reusable code and dated sources. Read the TL;DR of the relevant files before researching
   or building anything. Don't redo work that is already there.
2. `Berbata_Hackathon_Intel.md` has the brief and a snapshot of the 332 competing projects.
3. `Berbata_Idea_Shortlist.html` and `Berbata_Idea_Brainstorm.html` have our candidate ideas. TwinCast is the recommended one.
   Don't edit these three files.

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
