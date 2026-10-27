# Tely: notes for Claude

Tely (said "telly") is Team Berbata AI's entry (Innovation Studio 126726) to the "Inside the Game" hackathon
(Microsoft × Premier League): the best audio experience for a blind or partially sighted fan. It has a reactive
crowd at each end, an AI commentator who builds tension because the pipeline knows what is coming (behind a
spoiler firewall), and a voice the fan can question. One owner: potencialbg.

## Read before starting work
1. `README.md`, then `docs/architecture.md` for the code map and the seams, and `docs/DECISIONS.md` for why each
   thing is the way it is (D1–D37, dated).
2. `stoynev research/INDEX.md` lists the research library, one file per topic, each with a TL;DR and sources. Read
   the relevant TL;DR before researching or building. Don't redo work that is already there.
3. `Berbata_Hackathon_Intel.md`, `Berbata_Idea_Shortlist.html` and `Berbata_Idea_Brainstorm.html` hold the brief and
   our early ideas. Don't edit these three files.

## Layout
`web/` the player · `pipeline/` generator, commentary, agents, Q&A tools, evals · `relay/` live Ask and MCP ·
`infra/` Bicep · `eval/` results · `video/` · `assets/` · `docs/`. Tests: `cd pipeline && pytest`,
`cd relay && pytest`, `cd web && npm test && npm run test:a11y`. Use a worktree per branch, and set `PYTHONPATH` to
the worktree's `pipeline;.` so tests don't import the main checkout's editable `tely`.

## Working rules
- Short `a/<topic>` branches, one PR per item. Wait for green CI, then `gh pr merge --squash` (the repo refuses
  auto-merge). Push after every commit.
- Deploy from a clean worktree of `origin/main` (copy `.azure/` in), never from a checkout other sessions use:
  `azd deploy web` (its predeploy hook also pushes the relay), then check the demo, `/health` and the manifest.
- Never print or commit keys. Never name another hackathon entry in a public file.
- New research goes in `stoynev research/NN-topic.md` in the same section layout, with a row in its INDEX.md.
- Mark anything unverified "(unverified)". Never invent numbers: every number in README and SUBMISSION comes from
  `eval/report.json` or a cited decision.

## Hard facts (see `stoynev research/12-judging-criteria-and-rules.md`)
- Submissions close **27 Oct 2026, 23:59 PT**. Judging runs to 10 Nov, and the demo must stay up and free until then.
- Deliverables: a video **under 2 minutes**, a **public** GitHub repo, a working demo link, a pitch naming the
  Microsoft tech. Five criteria at 20% each; our category is Best Use of Microsoft Foundry.
- **Synthetic data only.** Nothing trained on or derived from real match data: no StatsBomb open data, no xT or
  EPV grid fitted on real matches. Real names may appear only in git-ignored local test renders (D21).
- Licence traps: Ultralytics YOLO is AGPL (use RF-DETR, Apache); the NBJW and PnLCalib calibration tools are GPL.
