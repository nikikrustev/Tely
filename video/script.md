# Tely: demo video script (1:52)

_ Stage 9a, 24 Oct 2026. Target length 1:52, hard stop 1:55 (file 14). Category: Best Use of Microsoft Foundry._

**How to read this.** One row per beat. "On screen" is what the viewer sees, "Voiceover" is the narrator (exact text and
timing in [voiceover.srt](voiceover.srt)), and "Burned caption" is what [captions_sdh.srt](captions_sdh.srt) shows
(non-speech sounds in square brackets). The match footage is real replay audio and radar from the deployed site, cut
from the judge cut at the match times given; [make_captions.py](make_captions.py) holds that edit list (`EDIT`) and
builds the SDH track from the bundle's cue text, crowd captions and sound events. Record the takes in the order of
[shotlist.md](shotlist.md).

**Design rules for this cut** (files 14 and 42):
- It must work **muted**: every sound has a caption, and the sound radar shows where the ball and crowd are.
- It must work on **laptop speakers**: nothing depends on stereo; "left" is captioned and drawn on the radar.
- Every number on screen or in the voiceover is in `eval/report.json`, the bundle's `manifest.json`, or a cited
  research file. `pipeline/tests/test_video_captions.py` fails if the report stops saying what the voiceover says.
- No music, no logos, no real clubs, players or commentators (file 12). AI voices are labelled on screen and on the end card.
- The voiceover is about **165 words**, not file 14's 255: about 35 s of the video is the product's own audio (the
  match and the live answers), and the voiceover stays off it.

## Beats

| Time | On screen | Voiceover | Burned caption |
|---|---|---|---|
| 0:00–0:08 | Black. Small white text, top: **"Tely"**. Crowd audio fades in (match 954.8–966.8 s: the stoppage after the yellow card, no commentary). | "Tely: a seat in the stands for fans who can't see the pitch." / "Synthetic match, real pipeline." | [stadium crowd fades in], then the voiceover |
| 0:08–0:20 | Still black. Text card, centred: **"RNIB research: TV commentary scored 6.1 / 15 with blind fans"**, then **"Description lags: the roar comes first"**. Source line, small: "RNIB 2022 (file 36)". Crowd fades out by 0:12. | "In RNIB's research, blind fans scored ordinary TV commentary 6.1 out of 15." / "And description often lags: you hear the roar before you know why." | the voiceover |
| 0:20–0:30.6 | **The hero, part 1.** The site with the sound radar (`?radar=1`), match 674.0–684.6 s. Lower third at 0:20: **"Listen: the voice builds before the chance"**. At 0:21.4 the build-up starts; at 0:25.4 the header. The radar shows the ball moving left, the tension line climbing, the haptic pulse. | (none: the product speaks) | AI COMMENTATOR: Navy coming... Olvholm... here's a chance! · [crowd rises] · [phone pulses: attack] · [shot, left] [phone pulses: shot] [ball hits the net] · Fenford, the header! · It's in the net... but hold on, VAR is checking it. · [Navy end hush] [Reds end hush] |
| 0:30.6–0:35.7 | **The hero, part 2.** Hard cut, with a 1.8 s title "(18 seconds later, after the VAR check)". Match 702.8–707.9 s: the verdict and the roar. | (none) | (18 seconds later, after the VAR check) · [Navy end roars] [Reds end falls silent] [phone pulses: goal] · AI COMMENTATOR: The goal stands! Goal for Navy! |
| 0:35.7–0:45 | Freeze on the radar; roar fades under the voiceover. Overlay, two lines: **"Build-up: 4.0 s before the header"** · **"Director plan: level 0.62 · lead 4 s · hold 300 ms · hint: danger"** | "The voice lifted four seconds before the header." / "Our Director agent hears ten seconds ahead, but it only shapes the build-up." | the voiceover |
| 0:45–0:50 | The site playing (match from 754 s). The Ask button is pressed (key **A**), then **Ask out loud**. | "And at any moment, the fan can ask the commentator out loud." | the voiceover |
| 0:50–1:01 | **Live, one take, unedited.** Label top-right: **"LIVE · Foundry Voice Live · unedited"**. The fan asks **"Where's the ball?"**; the answer plays in the commentator's voice; the match resumes. | (none: the fan and the live answer) | FAN: Where's the ball? · the live answer, typed from the take into `video/takes.srt` |
| 1:01–1:05 | Same frame. Overlay: **"31 test questions · median 1.14 s to the first answer audio"** | "Foundry Voice Live, in the commentator's own voice." | the voiceover |
| 1:05–1:11 | **Live take 2.** The fan asks **"Who wins?"**; the commentator refuses to predict. Label: **"LIVE · unedited"**. | (none) | FAN: Who wins? · the live answer, from `video/takes.srt` |
| 1:11–1:25 | **The spoiler firewall.** A simple diagram: **"Look-ahead (next 10 s)" → Director → "tension plan only: level, lead, hold, hint"** → Commentator → Verifier → Azure Speech. Then the Application Insights trace of one Director run (`workflow.run` → director → commentator → verifier → tts). From 1:20, an eval card: **"70 lines · 0 spoiler leaks · 70/70 truth check · 10/10 spoken numbers verified"** and **"31 live questions · 0 spoiler hits"**. | "Here's why it can't spoil the match." / "The Director sees the next ten seconds, but it outputs only a tension plan, never the result." / "Code checks every line: seventy lines, zero spoiler leaks, every number verified." | the voiceover |
| 1:25–1:35 | **What we shipped:** the README architecture diagram, each box lighting as it's named: synthetic match generator → Agent Framework + Foundry (gpt-5-mini) → Azure Speech HD → Static Web Apps; Container Apps relay → Foundry Voice Live + Stats MCP. | "Under the hood: a seeded match generator, Agent Framework on Foundry, Azure Speech HD voices, Static Web Apps, and a Container Apps relay." | the voiceover |
| 1:35–1:40 | VS Code, GitHub Copilot Chat in **Agent mode**, answering from the **Azure MCP Server**: the resources in `rg-as-judge`. | "We checked our Azure deployment from Copilot Agent Mode through Azure MCP." | the voiceover |
| 1:40–1:46 | **A listener.** TODO (listening test not run yet): a consenting listening-test participant's reaction, their own words, captioned verbatim. No voiceover. If nobody consents, or the test hasn't run: hold the eval card from 1:20 instead, and do **not** imply any test with blind fans. | (none) | the listener's words, from `video/takes.srt` |
| 1:46–1:52 | **End card.** Large URL: `lively-ocean-0efe4ae0f.2.azurestaticapps.net` · "Best Use of Microsoft Foundry" · "Berbata AI" · footer: **"AI voices (Azure AI Speech) · synthetic data · fictional clubs and players"**. Hold the URL at least 3 s. | "Tely. Put on headphones and try it: the link is below." | the voiceover |

## Where each number comes from

| Said or shown | Value | Source |
|---|---|---|
| TV commentary for blind fans | 6.1 / 15 | RNIB 2022 research report, via `stoynev research/36-blind-fans-and-audio-description.md` |
| Build-up lead before the header | 4.0 s (build-up 675.4 s, shot 679.4 s) | `eval/report.json` → `director.windows_detail[e00675].plan.lead_s`; `cues.en.radio.jsonl` c_0002 |
| Director plan for that chance | level 0.62, lead 4 s, hold 300 ms, hint danger | `eval/report.json` → `director.windows_detail[e00675].plan` |
| The Director's look-ahead | 10 s | `web/public/replay/v1/judge/manifest.json` → `delay_s` |
| Lines, spoiler leaks, truth check | 70 lines, 0 leaks, 70/70 | `eval/report.json` → `lines`, `spoiler_leaks`, `truth_check_pass` |
| Spoken numbers verified | 10/10 (100%) | `eval/report.json` → `numbers` |
| Live questions: answered, spoiler hits, median first audio | 31 answered, 0 spoiler hits, p50 1.14 s | `eval/report.json` → `qa_latency` (`p50_ms` 1137) |
| The VAR cut | 18 s (684.6 → 702.8) | `EDIT` in `video/make_captions.py` |

Don't add a number that isn't in this table. If `eval/report.json` changes, rerun `python video/make_captions.py` and the
test, and update this table.

## If something isn't ready on the day

- **Live Ask fails or the relay is cold:** record the **preset** "Where's the ball?" (offline, rendered in the
  commentator's voice), change the label to **"PRESET answer (works offline)"**, and change voiceover cue 8 to "The
  presets work offline, in the commentator's own voice." Drop the "Who wins?" take and hold the firewall diagram longer.
- **Listener footage:** see 1:40 above. Never caption an eyes-closed sighted volunteer as a blind fan (file 42).
- **Too long:** trim the VAR title (0:30.6) and the 1:01 overlay first; never trim the build-up (never cut it).
