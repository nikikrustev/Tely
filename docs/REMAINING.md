# Tely: what's left before "only testing remains"

_Written Sat 24 Oct 2026 from the state of `main` at `ded7aff` (PR #25), GitHub, and the live site._

**Deadline:** the form closes **Tue 27 Oct, 23:59 PT**, which is **Wed 28 Oct, 08:59 Sofia** (Bulgaria moves to winter time on 25 Oct).
The plan's own target is **Tue 27, 08:00 PT (17:00 Sofia)**, which leaves a buffer.

## Where we are (against PROMPTS.md)

| Prompt | Status | Evidence |
|---|---|---|
| A1–A7 | Done | PRs #4–#21 merged. Director on Foundry, offline answers and Voice Live are deployed. |
| A8 (CI, uptime, report) | Done | #22, #23. CI is green on `main`, uptime workflow exists. |
| A9 (video script and write-up) | Done | #25: `video/script.md`, `shotlist.md`, `captions_sdh.srt`, `narration.py`, README, SUBMISSION. |
| A10 (final checks and submit) | **Waiting** | Needs the YouTube URL. |
| B1–B7 | Done | Nikolay handed his lane to A on 24 Oct (`6baefe8`). |
| B8 (video drafts) | Not needed | A9 wrote the final versions directly. |
| B9 (final checks before going public) | **Not done** | It's A's job now: see prompt P1 below. |

**Live checks today:** the demo returns 200, `manifest.json` returns 200, and relay `/health` returns `{"ok":true,"mode":"live"}`.

**Not done or no evidence found:**
- **The repo is still PRIVATE.** The badges, the README links and the judges' quick path all fail for anyone outside the team.
- The listening test hasn't run (`eval/listening.json` says `"not run yet"`). README, SUBMISSION and the video script all carry TODOs that depend on it.
- No record of the Narrator, TalkBack or VoiceOver walkthrough.
- No record of the Android haptics check or the iPhone "audio only" check.
- No trace or Copilot screenshots are committed. The video needs takes T and C.
- No insurance video.
- No video and no YouTube upload.
- A stale worktree remains: `.claude/worktrees/modest-thompson-4cbcbe` (branch `a/commentary-density`, already merged as #13).

---

## Order of work

### Sat 24, this evening
1. **[Claude] P1: the final-checks scan.** Run it before the repo goes public, because the scan covers git history too.
2. **[Manual, 10 min] Decide what goes public.** `Berbata_Hackathon_Intel.md` is a snapshot of 332 rival projects, and `stoynev research/` contains the competitor notes. Keep them (the brief only needs the code to be public), or move them out with P1's help. **The history keeps them either way:** a file deleted now still shows in old commits. If they must not be public at all, P1 has to rewrite history or you have to start a fresh public repo.
3. **[Manual, Nikolay, 2 min] Make the repo public.** Nikolay is the owner (`nikikrustev`): Settings → General → Danger zone → Change visibility. Only he can do it, so message him now.
4. **[Manual, 30 min] Record the insurance video:** 60–90 s of the deployed site with system audio (BUILD_PLAN Stage 4). It's cheap cover if anything later goes wrong.

### Sun 25
5. **[Manual, 1 h 15 min] Run the listening test** with at least 3 people (`eval/listening_test.md`), and fill in `eval/listening_test.csv`. Get **written** consent before filming anyone for the video. If you can't run it, P4's "not run" branch removes the TODOs honestly.
6. **[Manual, 30 min] Run the accessibility walkthroughs.** Windows Narrator (Ctrl+Win+Enter), then TalkBack on Android or VoiceOver on iPhone: Start, Ask (preset and out loud), Settings, Next big moment. Note every blocker.
7. **[Manual, 20 min] Check phones.** On Android Chrome, the heartbeat and goal vibration. On iPhone Safari, that the audio works and the "audio only" message shows. If you have Bluetooth earbuds, also try the Bluetooth calibration.
8. **[Claude] P4: listening results and walkthrough fixes.**
9. **[Claude] P2: the showcase website**, without the video embed at first.
10. **[Claude] P3: Higgsfield shots.** It writes the shot prompts and updates the script. Do this only if you decide to use Higgsfield (see the note under P3).

### Mon 26
11. **[Manual, 1 h 30 min] Record every take** in `video/shotlist.md` (H, O, Q1, Q2, T, C, plus L if a participant consented). Wake the relay first: open `/health` and reload until it returns JSON. Do a throwaway mic question first, so the permission prompt doesn't appear in a real take.
12. **[Manual, about 1 h] Generate the Higgsfield clips** from P3's prompts. Use them only if they have no watermark (see the note under P3).
13. **[Manual, 15–45 min] Record the voiceover.** Either record it yourself from `video/voiceover.srt`, or approve the AI narration (`python video/narration.py`; it's already rendered in `out/narration/`).
14. **[Manual, 2 h] Edit in Clipchamp** to 1:45–1:55 (target 1:52). Use no music and no logos. Keep the build-up moment intact.
15. **[Manual, 20 min] Type `video/takes.srt`.** Write the exact words from the live takes and the listener take. Then run `python video/make_captions.py` and `bash video/assemble.sh out/video/edit.mp4`.
16. **[Manual, 15 min] Check the export.** `ffprobe` must report under 115 s. Watch it once muted and once on laptop speakers, and read the captions on a phone.
17. **[Manual, 20 min] Upload to YouTube:** Public, "not made for kids", English captions from `video/captions_sdh.srt`.

### Tue 27 (submit by 08:00 PT / 17:00 Sofia)
18. **[Claude] A10** from PROMPTS.md, with the YouTube URL. It fills the video link in README and SUBMISSION, refreshes the numbers and does the last link check.
19. **[Claude] P2 follow-up:** add the YouTube embed to the showcase page and redeploy.
20. **[Manual, 10 min] Check as a stranger.** In a private window and logged out, open the repo, the demo, the showcase page and the video. Also open the demo on a phone. The uptime and CI badges should be green.
21. **[Manual, 30 min] Submit on Innovation Studio.** Use category **Best Use of Microsoft Foundry**, and paste from `SUBMISSION.md`. Screenshot the confirmation.
22. **[Manual, 10 min] After submitting:**
    - Stop deploying feature changes.
    - Set reminders for 31 Oct, 5 Nov and 10 Nov to check the demo, the badge and the budget.
    - Check when the Azure free credit expires (Portal → Subscriptions). It runs out 30 days after sign-up, so around 19–20 Nov, which is after judging ends on 10 Nov. If the credit runs out, Azure switches the services off.

**Then only testing is left.**

---

## Paste-ready Claude prompts

Every block starts in a **new** session on an up-to-date `main` (`git checkout main && git pull origin main`).
Nikolay has handed over his lane, so all of these run as A.

### P1 · Final checks before going public (replaces B9)

```text
I am potencialbg (Person A). Nikolay handed me his lane on 24 Oct, so I own every file in TEAM_SPLIT.md.
Rules: read CLAUDE.md and TEAM_SPLIT.md first. Never print or commit keys. Work on branch a/final-checks and open a PR.
Explain as you go with one-line "TIP:" or "WHY:" notes. Finish by listing every file you changed.

Task: the B9 final checks from PROMPTS.md, run before the repo is made public.
1. Secret scan of the working tree AND the full git history (all branches): key-like strings, connection strings,
   subscription or tenant IDs, .env contents, SAS tokens. Use gitleaks if available, otherwise a careful grep over
   `git log -p --all`. If anything real is found, STOP and tell me: I will rotate it before we decide on a history rewrite.
2. Real-name scan: real clubs, players, commentators or Premier League marks anywhere in web/public, the bundle,
   README, SUBMISSION and video/. Research notes may mention them; report those separately.
3. Every link in README.md and SUBMISSION.md returns 200 (repo links will 404 until it is public; list them apart).
4. assets/licences.json covers every file in web/public/crowd/ and all are CC0.
5. Licences from the lockfiles (web/package-lock.json, pipeline, relay): no GPL/AGPL. Replace the "(unverified)" rows in
   README's licence table with what the installed package metadata says.
6. Run every test: pytest (pipeline/tests), vitest, Playwright + axe.
7. List what would become public that we might not want public (Berbata_Hackathon_Intel.md, stoynev research/,
   .claude/, out/), and what a history rewrite would take if we chose to remove any of it. Don't rewrite anything.
8. Remove the stale worktree .claude/worktrees/modest-thompson-4cbcbe (its branch was merged as #13), and make sure
   .claude/ is git-ignored.
Put the findings in the PR description, most urgent first.
```

### P2 · Showcase website (on the same Static Web App, free)

```text
I am potencialbg (Person A, I own every file now). Rules: read CLAUDE.md and TEAM_SPLIT.md first. Never print or
commit keys. Branch a/showcase, open a PR. Explain as you go with one-line "TIP:"/"WHY:" notes.

Task: a showcase page for judges who may never put on headphones, served at /about/ on the SAME Static Web App
(Vite multi-page build: web/about/index.html + its own entry), so it costs nothing and stays up with the demo.
Do NOT change the demo at / : README, SUBMISSION, the shot list and the Playwright tests rely on Start being focused
on load at the root URL.
Content, in this order:
- Hero: name, tagline from SUBMISSION.md, one big "Listen to the match (headphones)" link to /?radar=1, and a
  slot for the YouTube embed (privacy-enhanced youtube-nocookie.com, lazy, with a text link fallback). Leave a clear
  placeholder until I give you the URL.
- "Hear it in 20 seconds": an <audio controls> player for a short clip of the hero moment (build-up -> header ->
  VAR -> goal stands). I will export the audio from shot-list take H into web/public/showcase/hero.mp3; put a
  transcript right under the player (the SDH caption lines for that moment from video/captions_sdh.srt).
- The problem (RNIB 6.1/15, lag), the five stages, the spoiler firewall as an accessible inline SVG with a text
  equivalent, the results card, the Microsoft tech we shipped, the team and links (repo, demo, video).
- Every number must come from eval/report.json or a research file cited in SUBMISSION.md; read them at build time
  or copy them with a test that fails if report.json changes (like pipeline/tests/a/test_video_captions.py).
Rules: this page is FOR blind fans, so it must be exemplary: semantic landmarks, one h1, skip link, visible focus,
44 px targets, no autoplay, reduced motion respected, light and dark themes, readable at 320 px. No logos, no real
clubs, no stock photos. Add /about/ to the Playwright + axe tests at the 3 viewports, add a small "About this
project" link on the demo page footer (not before Start in tab order), link it from README and SUBMISSION, then
npm run build, azd deploy, and confirm both / and /about/ in a private window.
```

### P3 · Higgsfield shots for the video (only if you decide to use it)

> **Read before using Higgsfield.**
> - The rules ban third-party trademarks and logos in the video (`stoynev research/12`), and a Higgsfield watermark is a logo. Higgsfield's help centre says only paid plans make clips without the visible watermark. Paying breaks our "no money" decision, D6 in `docs/DECISIONS.md`. So: use Higgsfield only if you can get **watermark-free** output without spending team money. Otherwise, skip it.
> - Higgsfield's help centre says commercial use of outputs is allowed on all plans, but third-party reviews disagree about the free tier. Check the current Terms of Use yourself before you rely on it.
> - Keep the AI clips to the opener and the end, about 10–15 s in total. File 14 says judges want real product footage early. And never make an AI "blind fan" look like a real user or a testimonial (file 42).

```text
I am potencialbg (Person A, I own every file now). Rules: read CLAUDE.md, TEAM_SPLIT.md, video/script.md,
video/shotlist.md and stoynev research/14-demo-video-and-writeup.md and 42-audio-competitors-and-demo.md first.
Branch a/video-broll, open a PR. Explain as you go with one-line "TIP:"/"WHY:" notes.

Task: plan at most 15 s of AI-generated b-roll (Higgsfield, image-to-video or text-to-video) for the 1:52 video,
without breaking the rules or the honesty of the cut.
1. Propose where it goes. Candidates: 0:00–0:08 (instead of black: a fictional stadium at dusk, a fan in a stand
   wearing headphones, eyes closed, a phone in their hand) and the 1:46 end card background. Keep the hero (0:20–0:45)
   and everything after it as real product footage. Total length stays 1:45–1:55.
2. Write video/higgsfield_prompts.md: for each clip, the exact prompt, negative prompt, camera move, duration,
   aspect 16:9, and a reference-image note. Hard rules in every prompt: fictional kits in plain red and navy with no
   crests, sponsors, numbers or text; no real stadium, club, player or Premier League mark; no readable signage; no
   commentator likeness. The fan is a character, not a real person, and must not be presented as a test participant.
3. Update video/script.md and video/shotlist.md for the new shots (add a take "B" for b-roll), add an on-screen label
   "AI-generated imagery" while each clip plays, and add "AI-generated imagery (Higgsfield)" to the end-card footer.
   If you move any match clip, update EDIT in video/make_captions.py and keep pipeline/tests/a/test_video_captions.py
   passing.
4. Add one row to README's licence/credits table for the generated clips, citing Higgsfield's current Terms of Use
   page with an access date, and mark anything you couldn't confirm "(unverified)".
```

### P4 · Listening results, walkthrough fixes, remove the TODOs

```text
I am potencialbg (Person A, I own every file now). Rules: read CLAUDE.md and TEAM_SPLIT.md first. Branch
a/listening-results, open a PR. Explain as you go with one-line "TIP:"/"WHY:" notes.

Task:
1. Listening test: <EITHER "eval/listening_test.csv is filled in with N participants" OR "we could not run it">.
   If filled in: run eval/score_listening.py then eval/build_report.py, and put the real summary into README's results
   table, SUBMISSION.md ("What's next" and Accomplishments), and video/script.md at 1:40 if a participant consented
   to filming. Quote people only where the CSV records consent. Never call a sighted volunteer a blind fan.
   If not run: remove every listening-test TODO from README, SUBMISSION and video/script.md, and say plainly
   "not yet tested with blind or partially sighted fans; that is the next step" (the 1:40 beat holds the eval card).
2. Accessibility walkthrough notes (Narrator, TalkBack/VoiceOver), from me: <paste notes>. Fix each blocker, add a
   regression test where it can be tested, and record the walkthrough (date, screen reader, browser, result) in
   docs/DECISIONS.md and README.
3. Phone checks: <paste: Android haptics worked? iPhone "audio only" message shown?>. Fix or document.
4. grep the repo for TODO in README.md, SUBMISSION.md and video/, and confirm none are left that a judge would see.
npm test, pytest, Playwright + axe, then azd deploy if web/ changed.
```

### Already written in PROMPTS.md
- **A10** on Tue morning, with the YouTube URL.
- **"A · Fix-up"** for any CI failure or bug that turns up while testing.

---

## Notes behind some of these items

- **The relay goes cold.** It scales to zero, and the first live question after it has been idle can say "not available". SUBMISSION's testing instructions already tell judges to wait 30 s and ask again. Keeping it warm would cost money (D6), so leave it as it is.
- **Don't add Copilot-written code just to get the credit.** SUBMISSION says "Copilot wrote none of our code" and credits Copilot only for the Azure MCP checks. That's honest and consistent, so leave it.
- **The uptime cron** only runs on the default branch. Its badge will show correctly once the repo is public.
