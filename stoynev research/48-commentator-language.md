# 48. How football commentators talk: language for a less bland AI commentator

_Researched 24 Oct 2026 for Tely. Builds on file 36 (what blind fans want) and file 39 (prosody and anticipation).
This file is about the **words**, not the voice._

## TL;DR

- **Commentary is a recognised register with its own grammar.** Ferguson (1983) is still the reference. Its markers are dropped
  copulas ("Saka on the ball"), sentence-initial names and places, inverted order ("Up goes Gyokeres"), heavy modifiers
  and set routines such as giving the score. Play-by-play is in the simple present, in short or fragmentary clauses.
- **There are two jobs, and both matter on radio.** *Play-by-play* says what is happening now. *Colour* adds evaluation,
  context and feeling ("What a save!", "He'll feel he should have done better"). Our radio_v1 lines were nearly all
  play-by-play labels ("Midfield, far side, Reds."), which is why they sounded bland.
- **Radio practitioners' rules:**
  - "You are the listener's eyes": keep saying where the ball is and update the score (Phil Parry, via Spencer 2015).
  - Don't give the pitch position every ten seconds, or you do nothing else (Pat Nevin, BBC 5 Live).
  - Make clear who is attacking.
  - Add colour so the listener can imagine the game, and let your enjoyment show (Vicki Sparks, BBC/TNT, 2023).
- **Big moments get shorter, not longer.** One-word ("holophrastic") utterances rise with the chance's xG
  (Univ. of Stavanger thesis, 2023). Goal routines pair the scorer's name with formulaic goal wording. Pitch and loudness
  peak at the goal (Trouvain 2011, file 39).
- **Figurative language is mostly hyperbole.** A small study of Peter Drury found hyperbole the most common device
  (22 of 71 figures), then synecdoche and litotes. That is small-sample evidence.

## Findings

### 1. The register (syntax)
- Ferguson's markers (*Language in Society* 12(2):153–172, 1983; abstract only, paywalled):
  - omitted copulas and sentence-initial nominals;
  - inverted word order;
  - heavy modifiers;
  - result expressions;
  - routines ("giving the count").
- Football studies find the same pattern:
  - play-by-play narration in the simple present;
  - syntactic reduction and inversion (a single-match Champions League thesis, so small);
  - clause fragmentation, idioms, evaluative tone and pacing that changes with the action (Djamereng & Abdullah 2025;
    method only partly reported, unverified for sample size).

### 2. Play-by-play vs colour
- Ferguson's two roles are reporting the action (play-by-play) and presenting background and evaluation (colour).
- On TV the pictures carry the action. On radio the commentator must give **both what happened and how it feels**
  (Nevin, Champions Journal, undated). Tyler's ten seconds of silence after "Agüeroooo!" works on TV, not on radio.

### 3. Radio rules from working commentators
- **Where the ball is, who has it, and how likely a goal looks, plus colour** (Sparks 2023).
- **Update the score regularly.** There's no football rule for how often. Baseball broadcasters use a 90-second hourglass
  or a "SCORE" card (Barrett Media 2019). Our planner already says the score at least every SCORE_EVERY_S.
- **Balance:** don't give the pitch position every ten seconds (Nevin). Peter Jones "could make a poor match bearable,
  and a good match almost unbearable" (David Hatch, quoted by Spencer 2015).

### 4. Big moments
- Holophrastic (one-word) utterances are more frequent at higher xG. Goal routines pair names with goal wording
  (Stavanger thesis 2023, abstract via search; unverified details).
- Goal-call styles differ by region. Latin American calls elongate "gol". Arabic calls repeat and elongate the
  scorer's name. European calls centre on the scorer's name (Mental Floss, informal).

## So what for us

- **`lively` template set (`pipeline/tely/commentary/lively.py`, D21):**
  - **Verbs and movement:** "picks it up", "takes a touch, head up", "lets fly", "steps in".
  - **Places said the way commentators say them:** "over on the far side in midfield", "right below us in the final third".
  - **Directions:** the listener's side ("to your left") when the ball is clearly in one half.
  - **Inversion and fragments at peaks:** "Up goes Gyokeres... header!", and one-word fallbacks when the gap is tight.
  - **Colour, only after the outcome is known:**
    - "What a save from Alisson!", "He'll feel he should have done better", "What a header!";
    - crowd references ("listen to this place");
    - "the whole ground holding its breath" during a VAR check.
  - **Unchanged:**
    - the spoiler rules, the truth verifier, the seeded RNG and the ball-first fallbacks;
    - the score/clock routine;
    - the AI label.
- **Keep the score routine.** It is the one fixed habit every radio practitioner names.
- **Not done yet:**
  - player background colour (form, records), which would need facts we don't have in a synthetic match;
  - a co-commentator voice. Candidates for the LLM-colour item on the drop list (file 39: colour lines may go stale).

## Reuse: code & links
- Build: `python -m tely.build_commentary --style lively [--names pipeline/names/<x>.local.json]`.
- Local listening test: `npm run dev`, then `/?names=<stem>` (dev server only; `web/.local/` is git-ignored).
- Tests: `pipeline/tests/a/test_lively.py`.

## Sources (accessed 24 Oct 2026)
- Ferguson, C. A. (1983) "Sports announcer talk: syntactic aspects of register variation", *Language in Society* 12(2) —
  https://resolve.cambridge.org/core/journals/language-in-society/article/abs/sports-announcer-talk-syntactic-aspects-of-register-variation/6B134D8B6D90BD6B5B073B6C10A33FC0
- Science Friday, "Sports announcer talk" (Valerie Fridland) — https://www.sciencefriday.com/segments/sports-announcer-talk-linguistics/
- Djamereng & Abdullah (2025) "Register Variation in European Football Commentary", IDEAS 13(1) — https://ejournal.iainpalopo.ac.id/index.php/ideas/article/view/5941
- Univ. of Stavanger master's thesis (2023), football commentary syntax under time pressure — https://uis.brage.unit.no/uis-xmlui/handle/11250/3077641 (page unreachable on 24 Oct; summary from search, unverified)
- UCFB, "Vicki Sparks' top tips for football commentary" (27 Dec 2023) — https://www.ucfb.ac.uk/news/bbc-and-tnt-sport-journalist-vicki-sparks-top-tips-for-football-commentary/
- Lizzie Coan, "Listen up" (Pat Nevin), Champions Journal (undated) — https://www.champions-journal.com/1000/listen-up
- David Spencer, "Radio's hardest job?", HuffPost UK (28 May 2015) — https://huffingtonpost.co.uk/amp/entry/football-commentator_b_7457706
- Barrett Media, "More bad habits from the broadcast booth" (14 Jun 2019) — https://barrettmedia.com/2019/06/14/more-bad-habits-from-the-broadcast-booth/
- "Figurative language of football commentary by Peter Drury" — https://ejournal.stkipbudidaya.ac.id/index.php/ja/article/view/1434
- Trouvain (2011), football commentary phonetics — https://www.coli.uni-saarland.de/~trouvain/trouvain_football_2011.pdf
- Mental Floss, "5 different linguistic styles of exciting goal calls" — https://www.mentalfloss.com/article/57203/5-different-linguistic-styles-exciting-goal-calls
