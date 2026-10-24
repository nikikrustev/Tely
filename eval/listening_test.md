# Audio Stands: eyes-closed listening test

_Owner: A (potencialbg). BUILD_PLAN Stage 8 item 6. The protocol follows `stoynev research/36-blind-fans-and-audio-description.md`
("Testing with blind users"): two clips, comprehension probes, then RNIB's 15-point scale. Print this file. Run one copy
of the score sheet (last page) per participant, then type it into `eval/listening_test.csv`._

| | |
|---|---|
| Session length | about 20 minutes per participant (BUILD_PLAN Stage 8) |
| People | at least 3 (BUILD_PLAN Stage 8). Blind or partially sighted fans first. Sighted people with closed eyes are a fallback, not a substitute (file 36), and the report counts them separately |
| Format | one-to-one, on Teams/Zoom or in person, on the participant's own device and screen reader, with headphones if they have them |
| What you compare | the same AI commentary **alone**, against **full Audio Stands** (commentary + reactive crowd + ball sound + earcons + vibration) |
| Afterwards | `python eval/score_listening.py` then `python eval/build_report.py` |

---

## 1. The two clips

Both come from the judge cut of the synthetic match (Reds v Navy, seed 24). Every clip lasts **3 minutes** and stops by
itself with "End of the clip." The participant presses **Start** (or Enter). If they press Play again afterwards, the
match carries on, so ask them not to.

| Clip | Match clock | Playhead (s) | What happens (answer key in section 5) |
|---|---|---|---|
| **Clip 1** | 56:10 → 59:10 | 670 → 850 | Navy score at 56:19, VAR check, the goal stands, then midfield play |
| **Clip 2** | 61:10 → 64:10 | 970 → 1150 | Midfield play, a Reds shot blocked at 62:47, a Navy shot wide at 63:59 |

**The four URLs** (deployed demo, judge cut):

| Clip | Commentary only | Full Audio Stands |
|---|---|---|
| Clip 1 | https://lively-ocean-0efe4ae0f.2.azurestaticapps.net/?from=670&to=850&sound=commentary | https://lively-ocean-0efe4ae0f.2.azurestaticapps.net/?from=670&to=850 |
| Clip 2 | https://lively-ocean-0efe4ae0f.2.azurestaticapps.net/?from=970&to=1150&sound=commentary | https://lively-ocean-0efe4ae0f.2.azurestaticapps.net/?from=970&to=1150 |

- `from` and `to` are playhead seconds (the `?debug=1` panel shows the same number). `sound=commentary` mutes the
  crowd, the ball, the earcons and the vibration; the commentary voice is unchanged.
- To run it on your own machine instead: `cd web && npm run dev`, then use the same query strings on the local address
  Vite prints.

**Groups (counterbalancing).** Clip 1 always plays first, so the match story runs forward. What alternates is which
clip gets the full sound:

| Group | Who | Clip 1 | Clip 2 |
|---|---|---|---|
| **A** | P01, P03, P05, … | commentary only | full Audio Stands |
| **B** | P02, P04, P06, … | full Audio Stands | commentary only |

Clip 1 has a goal and Clip 2 does not, so the clips are not equally easy. The groups balance that only with an even
number of people; with 3 people, say so in the write-up.

**Send the links one at a time**, in the chat, just before each clip. Don't send a list: the URL says which condition
it is.

---

## 2. Pre-flight check (the day before, 10 minutes)

- [ ] Open all four URLs on a phone and a laptop. Commentary-only: the voice alone, no crowd. Full: crowd and ball.
      Each one stops after 3 minutes with "End of the clip." If a URL plays from 56:10 with full sound whatever you
      put in it, the deployed site is older than this kit: redeploy the web app first.
- [ ] Press Start on the Clip 1 full URL with a screen reader running (NVDA, Narrator, VoiceOver or TalkBack).
- [ ] Time "Learn the sounds" on the Start screen once: ______ min.
- [ ] Print one score sheet per participant (section 7). Give each person an ID (P01, P02, …) and keep the list of
      names **off** the repo and off the CSV.

---

## 3. Consent script (read it out at the start; tick the answers on the score sheet)

> "Thank you for helping. I'm testing Audio Stands, a student hackathon project: an audio experience for following
> football without seeing it. The match is made up by a computer; the teams and players aren't real. The commentator
> is an AI voice.
>
> I'll play you two short clips of about three minutes each, ask you four quick questions about what happened, and ask
> you to score each clip. There are no right or wrong answers: if you can't follow something, that's what I need to
> know. It takes about twenty minutes and you can stop at any time without giving a reason.
>
> I won't record your name with your answers. You'll be 'P' and a number. Your scores go into a public results table
> with no name, and I'll only say whether you are blind, partially sighted or sighted, if you're happy to tell me.
>
> Four questions, and 'no' is fine for any of them:
> 1. Are you happy to take part?
> 2. May I quote something you say, word for word, without your name, in our write-up and on GitHub?
> 3. May I film or screen-record your reaction, for a two-minute project video that will be public on YouTube?
> 4. Would you like to tell me whether you're blind, partially sighted or sighted, and which screen reader you use?
>
> If you change your mind later, tell me and I'll take your quote or video out of anything we haven't published yet."

- If question 1 is no, stop and thank them.
- If question 3 is yes, start the recording **now** and say "Recording has started."
- File 36 recommends paying participants for their time. If you offer anything, say what before question 1.

---

## 4. Running the session (about 20 minutes)

1. **Set-up (3 min).** Ask them to put headphones on and to pause their screen reader's speech when they want to talk
   to you. Tell them: "Reds attack to your right, Navy attack to your left. You are sitting on the halfway line."
2. **If Clip 1 is the full one (group B):** ask them to press "Learn the sounds" on the Start screen first and listen
   to the whole tour. Group A hears the tour before Clip 2 instead. Never before a commentary-only clip.
3. **Clip 1 (3 min).** Send the Clip 1 URL for their group. "Press Start and close your eyes. It stops by itself."
   Don't talk during the clip.
4. **Probes for Clip 1 (1–2 min).** Ask the four questions in section 5 in this order, without hints. Write down what
   they say, and score each 1 (right) or 0 (wrong or "don't know") against the answer key.
5. **Scale for Clip 1 (1 min).** Ask the three questions in section 6. Write each number down.
6. **Learn the sounds** (group A only), then **Clip 2**: same as steps 3–5 with the Clip 2 URL. Before it, say: "We've
   skipped ahead two minutes. The score is still Reds nil, Navy one."
7. **Preference (1 min).** "Which of the two clips would you rather follow a whole match with, and why?" Record 1, 2 or
   "none", and their reason in their own words.
8. **Try asking the commentator (2 min).** Send the full Clip 2 URL again. While it plays: "Press A, or the Ask button,
   and ask where the ball is." Note whether they managed it (yes / partly / no) and anything they said.
9. **Close.** Thank them. Ask: "Is there anything we should change before anyone else hears it?" Stop any recording.

---

## 5. Comprehension probes and answer key

Ask the same four questions after each clip:

1. **Where:** "Think of the biggest moment in that clip. Where on the pitch was the ball: which end, and how close to
   goal?"
2. **Which side:** "Which side of the pitch did that attack come down: the near side, the far side or the middle?"
3. **Danger:** "Was there a moment when a goal looked likely? For which team?"
4. **Who scored:** "Did anyone score? Who?"

Scoring: **1** if the answer matches the key below, **0** if it's wrong, missing or "don't know". Leave the box blank
only if you forgot to ask. Player names are fictional and hard to catch, so the team is enough; note a name if they
give one.

**Clip 1 (56:10–59:10).** Source: `web/public/replay/v1/judge/events.jsonl` and `cues.en.radio.jsonl`.

| Probe | Counts as right | What the data says |
|---|---|---|
| Where | In or near Reds' box, at the **left** end (Navy attack left) | Header from x −45.7 m, 6.8 m out from the goal line at −52.5 (e00675, 56:19) |
| Which side | The **far** side (the cross came from there) | "Olvholm's cross from the far side... and Fenford heads it in!" (cue at 56:47; cross from y +19.2) |
| Danger | Yes, **Navy** | Navy attack, header, goal |
| Who scored | **Navy** (Fenford, with a header) | "The goal stands! Goal for Navy!" after the VAR check (56:43) |

**Clip 2 (61:10–64:10).**

| Probe | Counts as right | What the data says |
|---|---|---|
| Where | Navy's box, at the **right** end (Reds attack right); or the Navy shot from outside the box at the left end | Reds shot from x 51.5 m, 1 m from the goal line, blocked (e00740, 62:47) |
| Which side | The **middle** for the Reds chance (or the far side, if they describe the Navy shot) | "Attacking third, centre, Reds" (62:34); the Navy shot came after "Attacking third, far side, Navy" (63:54) |
| Danger | Yes, **Reds** (blocked) and/or **Navy** (wide) | "Reds... Orlani... danger!", "Blocked! Rilford gets in the way." (62:43–62:47); "Wide from Kelski!" (64:00) |
| Who scored | **Nobody** | No goal in the clip; the score stays Reds nil, Navy one |

---

## 6. RNIB's 15-point scale

RNIB's 2022 TV football research used "an attitude scale combining the enjoyability, accessibility and the ability to
follow a match accurately", out of 15. Football on TV scored **6.1 out of 15** across its 10 interviews (RNIB, Nov 2022,
see file 36). That 6.1 was for TV broadcasts in general, after 10-minute clips, so treat it as a reference point only,
not as a baseline for these clips.

The report names the three parts and the total of 15, but not the wording or the range of each part. **Our version
(unverified against RNIB's own topic guide):** three questions, each scored 1–5, added up to 3–15.

After each clip, read out:

1. **Enjoyment:** "From 1 to 5, how much did you enjoy listening to that clip? 1 is not at all, 5 is very much."
2. **Access:** "From 1 to 5, how well did it give you what you need to follow football without seeing it? 1 is not at
   all, 5 is completely."
3. **Following:** "From 1 to 5, how accurately could you follow what was happening on the pitch? 1 is not at all,
   5 is completely."

If someone says "0" or "six", ask them to pick between 1 and 5.

---

## 7. Filling in `eval/listening_test.csv`

One row per participant. `c1_*` is Clip 1 and `c2_*` is Clip 2, **whatever condition they were in**; the script works
out the condition from `group`. Never put a name, email, age or anything else that identifies someone in the CSV: the
repo is public.

| Column | Values |
|---|---|
| `participant` | P01, P02, … |
| `session_date` | YYYY-MM-DD |
| `group` | A or B (section 1) |
| `sight` | blind, partially_sighted, sighted, or blank if they'd rather not say |
| `screen_reader` | e.g. NVDA, JAWS, Narrator, VoiceOver, TalkBack, none |
| `device` | e.g. Android phone, iPhone, Windows laptop |
| `headphones` | yes or no |
| `listened_via` | own_device (they opened the URL), shared_audio (you shared your sound on the call), in_person |
| `c1_where`, `c1_side`, `c1_danger`, `c1_scored` | 1 or 0 (blank = not asked) |
| `c1_enjoy`, `c1_access`, `c1_follow` | 1 to 5 |
| `c2_…` | the same seven columns for Clip 2 |
| `preferred` | 1, 2 or none (the clip they'd rather follow a match with) |
| `ask_tried` | yes or no |
| `ask_worked` | yes, partly or no |
| `consent_take_part`, `consent_quote`, `consent_film` | yes or no (section 3) |
| `quote` | their words, only if `consent_quote` is yes (the script drops it otherwise) |
| `notes` | anything else, without names |

Shared audio over a call loses most of the left/right ball panning, so the script reports `listened_via` alongside the
scores.

---

## Score sheet (print one per participant)

**Participant:** P____  **Date:** ________  **Group:** A / B  **Listened via:** own device / shared audio / in person

**Consent:** take part Y / N  quote Y / N  film Y / N  **Sight (if told):** blind / partially sighted / sighted

**Screen reader:** __________  **Device:** __________  **Headphones:** Y / N

| | Clip 1 (56:10–59:10) | Clip 2 (61:10–64:10) |
|---|---|---|
| Condition (from group) | A: commentary only · B: full | A: full · B: commentary only |
| Learn the sounds played first? | B only: ☐ | A only: ☐ |
| Where (1/0) | | |
| Which side (1/0) | | |
| Danger (1/0) | | |
| Who scored (1/0) | | |
| What they said | | |
| Enjoyment (1–5) | | |
| Access (1–5) | | |
| Following (1–5) | | |

**Preferred clip:** 1 / 2 / none  **Why (their words):** ____________________________________________

**Ask the commentator:** tried Y / N  worked yes / partly / no  **What happened:** _________________________

**Quote (only with consent):** ______________________________________________________________________

**Notes:** ________________________________________________________________________________________
