# 14 — Demo video and project write-up best practice for hackathon judging

_Accessed/compiled: 20 Oct 2026 · Priority area: submission (UX & Presentation 20%, plus how every other criterion is seen); all pipeline stages as shown on screen_

## TL;DR

- **Our hard limit is under 2:00, not Devpost's usual "about 3 minutes".** The official rules say the video must "be less than two (2) minutes" and "judges are not required to watch beyond two (2) minutes". They also say judges are not required to test the project. So the video and the write-up are what gets scored. Cut to **1:52 and never go over 1:55** (see [12](12-judging-criteria-and-rules.md)).
- **What judges do (sourced):** Devpost calls the video "one of the first things" judges look at. An MLH coach estimates about **5 minutes per project**. MLH plans **3–4 minutes per team** for live judging and asks for a **2-minute video** that is "a demo of their hack, not a presentation". We have **no source** on whether these judges read the README before or after the video. Assume (our guess) video first, then a skim of the write-up, and the repo only for finalists.
- **Structure:** say what it is in the first sentence (Paul Graham, Devpost), show the real product working with real input, show proof with numbers we measured, then architecture, then close. No slide decks. Our 60s script already does this. The 2:00 cut below adds a **problem beat, an agent-trace beat** (for the Agentic Design criterion), a **longer architecture shot** and a **"try it yourself" beat**.
- **Saying "synthetic" is a strength, not a disclaimer.** The rules require synthetic data. Say it in the first 7 seconds and turn it into the pitch: we know the ground truth, so we can grade ourselves. Never imply that rendered or replayed footage is live. The rules say the project "must work as shown".
- **Tooling:** record in OBS (MKV, auto-remux to MP4, 1080p at 30 or 60 fps). Our overlay page goes in a **Browser Source** with a transparent background. Edit in **Clipchamp**, whose autocaptions run on Azure and download as SRT, or in DaVinci Resolve. Upload to **YouTube, Public or Unlisted, "not made for kids"**, with an uploaded SRT. Loom is fine for internal drafts but is **not an allowed host**.

## Findings

### What judges actually do (only what sources say)

| Claim | Source | Applies to us? |
|---|---|---|
| Video under 2 min; judges not required to watch past 2:00; not required to test; repo must be public; working-demo access required; English (translate non-English parts) | Official rules §4.4, 4.8, 4.9 | **Yes. Binding.** |
| UX & Presentation asks "Does the demo video clearly communicate the Project's value?" | Rules §6.2 | Yes, 20% |
| The video is "one of the first things judges review", usually about 3 min | Devpost blog | Order yes, length no |
| Judges have "around five minutes" per project and move on if they can't find key information | J. Biggin (MLH coach), DEV | Plausible (unverified for this event) |
| Live judging: 4 min per project (2 min demo, 1 min Q&A, 1 min travel); 2-min video, "a demo… not a presentation"; at least 3 judges per project | MLH Judging Plan | Format differs (we're online), but the video advice holds |
| A live working demo "beats a more ambitious project shown as slides"; naming no weaknesses loses credibility; scores bunch mid-range | M. Kurbaitaev, DEV (2026) | Yes |
| Many judges are non-technical, so don't link only to GitHub | TRON hackathon guide | Partly. The PL "will assist with judging", so expect broadcast people (rules §2, per [12](12-judging-criteria-and-rules.md)) |
| Watch video first? Read README? | **No source found** | Guess: video, then write-up, then repo for finalists only (unverified) |

### Video structure

Devpost asks for a screencast, not a marketing video. Put the pitch in "the first few seconds", "like a movie trailer". Write a script and rehearse it, cut the rough parts, and upload early (Devpost help). YC and Paul Graham add more:

- Say what you do "as soon as possible, preferably in the first sentence".
- Narrow beats vague.
- Use four or five specific numbers at most.
- Keep slide text under 20 words. YC says more than 7 words is "likely too many".
- Use one speaker.
- Speak slowly: "if you think you're speaking too slowly, you're probably at about the right pace".
- Exaggeration is "fatal".

| Beat | Purpose | Rule |
|---|---|---|
| Hook (0–10 s) | What it is, and that the data is synthetic | Real product footage. No logo intro, no title card longer than 1 s |
| Problem | Why studios care | One sentence. No market-size slide (YC) |
| Live product | Real UI with real input | Screen capture of our app, not mock-ups. Rules: "footage that shows the Project functioning" |
| Proof | Measured metrics plus one honest failure | Only numbers from our own grader. Show the point where the degradation sweep breaks |
| Architecture | Azure services, event-driven | 10–18 s animated diagram, five stages labelled |
| Close | Name, link, category | End card with URL readable for 3 s or more |

**Captions:** burn in English captions or upload an SRT. Both are needed if the Bulgarian quadrant has speech, because the rules require English translations. Azure's captioning guide says to tell viewers when captions are automated, and to centre them in a large font.

**Voiceover vs music:** use a voiceover. Music is optional and risky: the rules ban "copyrighted music or other material" without permission, so use none or a sting we made ourselves.

**Honest synthetic framing:** "Every frame here is synthetic" works as a hook, not an apology. Label anything not live on screen: "replayed at match clock", or "rendered offline, same cue JSON". This matches the shortlist's GPU-fallback rule.

### Recording and editing tooling

| Need | Tool and settings | Source |
|---|---|---|
| Capture | **OBS Studio**: record as **MKV** (safe if OBS crashes), then File › Remux, or turn on "Automatically remux to mp4". Canvas and output at 1920×1080. Keep the frame rate the same from recording to export | OBS KB |
| Overlays live on footage | OBS **Browser Source** pointed at our overlay page. Default custom CSS makes the background transparent (`rgba(0,0,0,0)`). Set width and height to 1920×1080. "Refresh when scene becomes active" resets cue state per take | OBS KB |
| Quality preset | Simple mode "Indistinguishable Quality" (option name from the OBS UI, unverified against docs) | — |
| Upload encode | MP4, H.264 High, AAC-LC 48 kHz. **1080p SDR: 8 Mbps at 24/25/30 fps, 12 Mbps at 48/50/60 fps.** Stereo audio 384 kbps | YouTube help |
| Edit + captions | **Clipchamp**: autocaptions use Azure Cognitive Services, the transcript is editable, download as **.SRT**, one language per video. **DaVinci Resolve (free)**: manual subtitles and SRT export. Auto-transcription is reportedly Studio-only (unverified) | Microsoft Support; third-party |
| Voice | **Own voice**: authentic, but re-recording costs time. **Azure AI Speech TTS**: regenerates in seconds when Day 10 numbers change, timing is exact via SSML, and it counts as Azure AI use. Voices: `en-GB-RyanNeural`, `en-GB-SoniaNeural`; Bulgarian `bg-BG-KalinaNeural`, `bg-BG-BorislavNeural` | MS Learn language support |
| Draft review | Loom Starter: 5-min limit, 25 videos. **Not an allowed host.** Rules allow only YouTube, Vimeo, Facebook and Youku | Atlassian support; rules |
| Thumbnail | 16:9, JPG/PNG, at least 640 px wide (3840×2160 recommended), 2 MB limit from mobile. Account verification may be needed | YouTube help |
| YouTube audience | Set to "No, it's not made for kids". "Made for kids" turns off comments, cards and end screens. Devpost advises the same so judges can view it | YouTube help; Devpost blog |

### Write-up (submission page)

The Devpost template headings are Inspiration, What it does, How we built it, Challenges, Accomplishments, What we learned and What's next. Keep them where the form has them, because teams that delete them leave things out (Biggin). The Innovation Studio form fields are **not verified** ([12](12-judging-criteria-and-rules.md)). The rules require an elevator pitch naming what we built and the Microsoft/Azure tech. Devpost-style pitches are about 200 characters (unverified for this platform). Our order:

1. **Title + tagline.** Tagline in plain words, for example "Synthetic match, real pipeline: auto-evented, explained, personalised overlays".
2. **Category** in the first line ([12](12-judging-criteria-and-rules.md)).
3. **Problem → solution** in 3 sentences.
4. **How it works:** Ingest → Interpret → Explain → Render → Personalise, one line each with the Azure service.
5. **Architecture diagram** (PNG in the gallery and in the README).
6. **Proof:** a table of measured metrics, with one honest limitation.
7. **Judges' quick path** (a 60-second test).
8. **What's next.**
9. **Team.**

Map each section to a criterion, since judges score against the published criteria (Biggin; YC "vertebrae": 3–4 key points).

**README essentials:** GitHub says a README should cover what the project does, why it's useful, how to start, where to get help, and who maintains it. Content past 500 KiB is truncated. Relative image links work. Add a data note (synthetic, seed, generator), licences per model and dataset, and badges.

### Pitfalls

| Pitfall | Fix |
|---|---|
| **Cold start on judging day.** ACA defaults to **min 0 / max 10 replicas** and scales to zero; with no ingress and min 0 it "has no way of starting back up" | `--min-replicas 1` on the API/web app from 27 Oct to 10 Nov. A cached replay mode for GPU parts. A daily uptime ping (below) |
| Private repo / missing video | Rules: repo "must be public". Only 19 of 332 entries had a video on 19 Oct ([12](12-judging-criteria-and-rules.md)). Upload by 26 Oct. YouTube processing can take hours (Devpost) |
| Over 2:00 | `ffprobe` check below. Hard stop at 1:55 |
| Unreadable text at 1080p | YC: big fonts, high contrast. Our rule of thumb (unverified): no UI text under ~28 px at 1080p. Zoom the browser to 125–150% before recording. Check the upload on a phone at 720p |
| Jargon | "xT", "F1", "ByteTrack" need one plain gloss each, or cut them. YC: buzzword pitches lose the audience |
| Fake or mock claims | Every number on screen comes from the grader output file. Label replays. Don't call it "real-time" unless it is |
| Trademarks | Fictional clubs only. No PL marks or real player names (rules) |

## So what for us

This affects **Render and Personalise** most, because those are what the video shows, and the framing of **Interpret** as agentic. It applies to every idea, and most directly to **A TwinCast**, **F Graphics Desk** and **C One Number** (shown in the 2×2 grid).

1. Keep the 60s script as the core. The 2:00 cut below only adds beats; it doesn't reorder them. Target **1:52**, about **255 words** of voiceover at the 60s script's pace (~140 words/min).
2. Record overlays live through an OBS Browser Source over our rendered clip. That is honest ("functioning on the platform") and needs no compositing in the edit.
3. Use **Azure Speech TTS for the narration** (fast re-takes when metrics change) and say so on the end card. Use own voice only if someone has a good microphone (Devpost tip).
4. Lock in the deliverables: video and SRT by **25 Oct**, upload **26 Oct**, min-replicas 1 plus the uptime action until **10 Nov**.

### 2-minute extended script outline (builds on the 60s script)

| Time | On screen | Voiceover (new lines in full; others refer to 60s beats) |
|---|---|---|
| 0:00–0:07 | = 60s beat 1 (VANCE name strap) | = 60s beat 1 |
| 0:07–0:15 | **NEW problem:** a cluttered stats wall fades to one clean name strap. Caption: "Right stat · right fan · right second" | "Studios drown in stats. Turning one into the right graphic, for the right fan, on time, still takes a crew." |
| 0:15–0:25 | = 60s beat 2 (CV split screen, ticker) | = 60s beat 2 |
| 0:25–0:38 | = 60s beat 3 (accuracy panel) **+ degradation chart with the failure point circled** | 60s beat 3, + "…and here's where it breaks: heavy blur drops pass accuracy to [measured]." |
| 0:38–0:52 | **NEW agent trace:** Director → Explainer → Verifier panel beside the 28 m shot. Verifier ticks `truth_check` | "Three agents run the desk. A Director picks the moment, an Explainer writes it for each audience, and a Verifier checks every claim against ground truth before it airs." |
| 0:52–1:06 | = 60s beat 5 (2×2 grid). **English subtitles on the Bulgarian quadrant** | = 60s beat 5 |
| 1:06–1:16 | = 60s beat 6 (take/hold, key and fill) | = 60s beat 6 |
| 1:16–1:34 | **NEW architecture:** animated five-stage diagram, each stage lighting up with its Azure service (Event Hubs, ACA jobs + serverless GPU, Foundry, Cosmos DB, Web PubSub, Static Web Apps) | "Under the hood it's event-driven Azure. Events stream through Event Hubs, vision runs on Container Apps GPUs, Foundry agents explain, and Web PubSub pushes each cue to each viewer." |
| 1:34–1:44 | **NEW try-it beat:** a real browser at our URL clicks "Play hero clip" and toggles audience. URL large on screen | "Try it yourself: one link, no login, sixty seconds." |
| 1:44–1:52 | = 60s beat 7 (end card + category + "Narration: Azure AI Speech") | "Built on Azure, dataset open source. Berbata AI: synthetic match, real pipeline." |

### Submission checklist

- [ ] Video 1:45–1:55 (`ffprobe`), public or unlisted on YouTube, not made for kids, custom thumbnail, English SRT uploaded
- [ ] First 7 s say what it is and that it's synthetic. No logo intro
- [ ] Every on-screen number is traceable to `grader_report.json`. One honest limitation shown
- [ ] All text readable on a phone at 720p. Jargon glossed or cut
- [ ] No third-party music, logos or real names
- [ ] Write-up: category first line, five stages, diagram, proof table, judges' quick path, what's next, team
- [ ] README: quick start, architecture, data note, licences, badges, video and live links at the top
- [ ] Repo public. Live URL works logged-out in a private window. min-replicas 1. Uptime action green until 10 Nov

## Reuse: code & links

Check length and encode for YouTube (values from YouTube help, 1080p30):

```bash
ffprobe -v error -show_entries format=duration -of csv=p=0 demo_final.mp4   # must print < 115
ffmpeg -i edit.mov -c:v libx264 -profile:v high -pix_fmt yuv420p -b:v 8M -maxrate 10M -bufsize 16M \
  -g 15 -bf 2 -c:a aac -ar 48000 -b:a 384k -movflags +faststart demo_final.mp4
```

Narration with Azure Speech TTS (re-run whenever the Day 10 numbers change):

```python
import azure.cognitiveservices.speech as speechsdk, os
cfg = speechsdk.SpeechConfig(subscription=os.environ["SPEECH_KEY"], region=os.environ["SPEECH_REGION"])
cfg.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Riff48Khz16BitMonoPcm)
ssml = """<speak version="1.0" xml:lang="en-GB"><voice name="en-GB-RyanNeural">
<prosody rate="-5%">Every frame here is synthetic.<break time="300ms"/>
We simulated this match, then filmed it like a broadcaster.</prosody></voice></speak>"""
speechsdk.SpeechSynthesizer(cfg, speechsdk.audio.AudioOutputConfig(filename="vo_01.wav")).speak_ssml_async(ssml).get()
```

Captions from our own narration (Speech CLI, from the MS Learn captioning guide):

```bash
spx recognize --file vo_full.wav --format any --output srt file demo_en.srt
```

Keep the demo warm, and ping it daily during judging (`.github/workflows/uptime.yml`):

```bash
az containerapp update -n berbata-api -g berbata-rg --min-replicas 1
```

```yaml
on: { schedule: [ { cron: "0 */6 * * *" } ], workflow_dispatch: {} }
jobs:
  ping:
    runs-on: ubuntu-latest
    steps:
      - run: curl -fsS --max-time 30 https://<our-swa>.azurestaticapps.net/ && curl -fsS --max-time 30 https://<our-api>/health
```

README template skeleton:

~~~markdown
# Berbata AI — TwinCast
**Synthetic match, real pipeline.** Auto-evented, explained, personalised broadcast overlays on Azure.
Target category: <Best Azure Cloud Native Integration>

![Azure](https://img.shields.io/badge/Built%20on-Azure-0078D4) ![Data](https://img.shields.io/badge/data-100%25%20synthetic-2ea44f) ![Licence](https://img.shields.io/badge/licence-MIT-blue)

▶ **Demo video (1:52):** <YouTube link> · 🌐 **Live demo:** <URL> (no login) · 📄 Write-up: <project page>

## Judges' quick path (60 seconds)
1. Open <URL> → press **Play hero clip**.
2. Toggle **Casual / Analyst / BG fan #8 / Top speed only**.
3. Open **Accuracy** → CV events vs ground truth, plus the degradation sweep.
4. Click any overlay → **Evidence** shows the source events and `truth_check`.

## The problem
## How it works: Ingest → Interpret → Explain → Render → Personalise
| Stage | What happens | Azure service |
## Architecture
![architecture](docs/architecture.png)
## Agents & MCP tools   (Director · Explainer · Verifier)
## Results (measured, seed <n>)
| Metric | Value | How measured |
Known limitations: …
## Synthetic data note
All data and footage are generated by `sim/` (seed, generator version). No real Premier League data, footage, names or marks.
## Quick start
```bash
git clone … && cd … && cp .env.example .env
docker compose up   # or: make demo
```
## Repo layout
## Licences & third-party components   (model / dataset / licence table)
## What's next
## Team
~~~

## Sources

- Microsoft Premier League Hackathon Official Rules (§4.4, 4.8, 4.9, 6.2) — https://github.com/microsoft/insidethegamehackathon/blob/main/OFFICIAL%20RULES.md — accessed 20 Oct 2026
- Devpost, "6 tips for making a hackathon demo video" — https://info.devpost.com/blog/6-tips-for-making-a-hackathon-demo-video — accessed 20 Oct 2026
- Devpost Help, "Video making best practices" — https://help.devpost.com/article/84-video-making-best-practices — accessed 20 Oct 2026
- MLH Hackathon Organizer Guide, "Judging Plan" — https://guide.mlh.com/general-information/judging-and-submissions/judging-plan — accessed 20 Oct 2026
- Jacklyn Biggin, "How to make your Devpost submissions not suck" (DEV) — https://dev.to/jacklyn/how-to-make-your-devpost-submissions-not-suck-37i0 — accessed 20 Oct 2026
- Magomed Kurbaitaev, "What judges actually score" (DEV) — https://dev.to/kurbaitaev/what-judges-actually-score-notes-from-a-year-of-hackathon-judging-3p4l — accessed 20 Oct 2026
- TRON Grand Hackathon, "Improving your Devpost judge score" — https://forum.trondao.org/t/tron-grand-hackathon-improving-your-devpost-judge-score/9393 — accessed 20 Oct 2026
- Hack AI (LF Labs) Devpost submission notes (gallery 3:2, 5 MB; video at top) — https://lf-hyperledger.atlassian.net/wiki/spaces/labs/pages/20291400/Hack+AI — accessed 20 Oct 2026
- Y Combinator, "A Guide to Demo Day Presentations" (G. Ralston) — https://www.ycombinator.com/blog/guide-to-demo-day-pitches/ — accessed 20 Oct 2026
- Paul Graham, "How to Present to Investors" — https://paulgraham.com/investors.html — accessed 20 Oct 2026
- OBS Knowledge Base, Standard Recording Output Guide — https://obsproject.com/kb/standard-recording-output-guide — accessed 20 Oct 2026
- OBS Knowledge Base, Browser Source — https://obsproject.com/kb/browser-source — accessed 20 Oct 2026
- YouTube Help, Recommended upload encoding settings — https://support.google.com/youtube/answer/1722171 — accessed 20 Oct 2026
- YouTube Help, Add video thumbnails — https://support.google.com/youtube/answer/72431 — accessed 20 Oct 2026
- YouTube Help, Set your audience (made for kids) — https://support.google.com/youtube/answer/9610989 — accessed 20 Oct 2026
- Microsoft Support, How to use autocaptions in Clipchamp — https://support.microsoft.com/en-us/clipchamp/how-to-use-autocaptions-in-clipchamp — accessed 20 Oct 2026
- DaVinci Resolve subtitles (third-party; free vs Studio) — https://davinciresolveclub.com/davinci-resolve-subtitles-captions.md — accessed 20 Oct 2026
- Microsoft Learn, Speech service language and voice support (TTS) — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=tts — accessed 20 Oct 2026
- Microsoft Learn, Captioning with speech to text — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/captioning-concepts — accessed 20 Oct 2026
- Microsoft Learn, Scaling in Azure Container Apps — https://learn.microsoft.com/en-us/azure/container-apps/scale-app — accessed 20 Oct 2026
- Atlassian Support, Loom: How long can I record? — https://support.atlassian.com/loom/docs/how-long-can-i-record/ — accessed 20 Oct 2026
- GitHub Docs, About READMEs — https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes — accessed 20 Oct 2026
- Berbata Idea Shortlist, 60-second demo script (internal) — `Berbata_Idea_Shortlist.html` — accessed 20 Oct 2026
