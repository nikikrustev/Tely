# 47 — Does Audio Stands already exist? Prior art beyond the hackathon (products, startups, research, patents)

_Accessed/compiled: 20 Oct 2026 · Priority area: Real-World Impact + write-up honesty (novelty claims); Audio Stands across Interpret → Explain → Render → Personalise_

## TL;DR

- **Each pillar of Audio Stands already exists somewhere. We found nobody who combines them.** We found no product, paper or patent that does all four for blind fans: a crowd driven by events, commentary shaped by look-ahead, voice talk-back and phone haptics. The closest single items are:
  - OneCourt: haptics plus generated audio description, blind-first.
  - Disney patent US11843473B2: tracking data drives spatial enhancement audio that does not depend on visuals, and names visually impaired users.
  - AiCommentator (IUI 2024): interactive AI commentary for football, not blind-first.
  - Samsung Vision AI Companion: Q&A about the match on screen.
- **AI commentary from data is old news. Do not claim it.** IBM generated spoken commentary for Wimbledon and Masters highlights in 2023. Stats Perform and Veritone launched "Opta Voice" in 2022. Tencent filed a patent on match data stream → commentary scripts → virtual presenter in 2019. NHK automated sports audio description at Rio 2016 (see 36). Amazon holds a patent on AI audio description for live sport (US11736775B1, 2023).
- **The one claim that holds up: using a known look-ahead window to build tension.** The recent research benchmarks require causal commentary, meaning no future information (StreamSoccer, Aug 2026). Matchday Companion keeps the future away from its Q&A agent (see 42). The nearest prior art is narrow:
  - NHK delayed video by about one second, only to keep haptics in sync.
  - A Twente thesis predicts events before they happen.

  Neither one shapes emotion from a known future.
- **Phrase novelty as "a combination we have not found", with the search scope stated.** Never write "first" or "never been done". Cite OneCourt's Microsoft AI for Accessibility grant and RNIB's research as **validation of the need**, not as competitors we beat.
- **We are not lawyers.** The patent list below comes from a keyword search, and Google Patents rate-limited us part-way through. It is a map, not a freedom-to-operate opinion.

## Findings

### 1. Landscape table

The table covers what we found outside the hackathon. Hackathon rivals are in [42](42-audio-competitors-and-demo.md). Sky Descriptive Audio Commentary, Touch2See, Field of Vision, FIFA's app, Action Audio/HawkAR and the NHK auto-AD are covered in depth in [36](36-blind-fans-and-audio-description.md) and appear here only briefly.

Key: **Y** = does it · **~** = partly or adjacent · **–** = no evidence.

| Name (year) | Type | What it does | Crowd | Look-ahead build-up | Talk-back | Haptics | Blind-first |
|---|---|---|---|---|---|---|---|
| IBM watsonx, Wimbledon and Masters (2023–24) | Product | Generated spoken narration on **highlight clips** (EN, with ES added at the Masters in 2024). Hole Insights gives written projections | – | – (post-hoc clips) | – | – | – |
| Stats Perform + Veritone "Opta Voice" (2022) | Product/B2B | Synthetic voices read Opta data as play-by-play, previews and recaps in 7 languages. Visually impaired audiences were named in the pitch | – | – | – | – | ~ |
| WSC Sports for the NBA (2025) | Product | GenAI writes and **voices** 2-min highlight commentary in FR/PT/ES within minutes of the final whistle | – | – | – | – | – |
| NBC Peacock "Your Daily Olympic Recap" (Paris 2024) | Product | Cloned Al Michaels voice over personalised 10-min recaps. Humans reviewed every recap | – | – | – | – | – |
| ESPN FACTS avatar (2024, in development) | Prototype | Analytics avatar built on Azure OpenAI + ElevenLabs. ESPN's game recaps are text only | – | – | ~ | – | – |
| DFL / Sportec Solutions + AWS (2024–) | Product | AI **text** live ticker in several languages and styles | – | – | – | – | – |
| Camb.ai on Ligue 1+ (Jan 2026) | Product | Live AI **translation** of the French commentary into Italian | – | – | – | – | – |
| FOX Sports × ElevenLabs "Colin Cowherd" (Apr 2026) | Product | Voice agent with a cloned pundit persona. Covers headlines and opinion, **not live play** | – | – | Y | – | – |
| Samsung Vision AI Companion (2025–26) | Product (TV) | Ask questions about the match on screen, including "who will win?". Needs a broadcaster setup; 9 countries | – | – | Y | – | – |
| Alexa+ sports (2026) | Product | Scores, then play detail on request (one third-party report; **unverified**) | – | – | Y | – | – |
| Premier League Companion (2025–) | Product | Copilot Q&A over the archive and stats. Voice was promised (see [28](28-sponsor-goals-and-real-world-impact.md)) | – | – | ~ | – | – |
| Pixellot (2025) | Product | Grassroots auto-production. Listed feature: AI commentary cloned from a friend's or relative's voice (single trade report, **unverified**) | – | – | – | – | – |
| WorldCupVoice (open source) | Repo | Samples frames from a live feed, LLM play-by-play, TTS into an RTC room. Returns `NO_CALL` when a frame is unclear | – | – | – | – | ~ |
| **AiCommentator**, Andrews et al. (IUI 2024) | Research | Football broadcast + CV tracking + LLM. Two modes, automatic and **interactive**. The 16 users preferred interactive. Speech modality not confirmed | – | – | Y | – | – |
| **CompanionCast**, Wang et al. (CHI'26 workshop) | Research | Several AI co-viewing agents for soccer, with **spatial audio** for co-presence. Raised social presence vs watching alone | ~ | – | ~ | – | – |
| MatchTime/MatchVoice (EMNLP'24); LFC dataset (INLG'25); StreamSoccer (2026) | Research | Commentary from soccer video or tracking data. StreamSoccer is strictly causal | – | **No (by design)** | – | – | – |
| MCAD (arXiv, Nov 2025) | Research | Video-LLM **audio description** for soccer clips. No live use and no BLV study reported | – | – | – | – | Y |
| Sky/BT/BBC virtual crowds (2020) | Broadcast | Crowd audio from EA FIFA samples, fired by an operator, with or without crowd as a viewer choice (see [38](38-reactive-crowd-atmosphere.md)) | Y (human-run) | – | – | – | – |
| Sky Dolby Atmos PL (since 2017/18) | Broadcast | Immersive mix of the real stadium sound | ~ | – | – | – | – |
| Yamaha Remote Cheerer (2020) | Product | Fans' taps play cheers through 58 stadium speakers | ~ (fan-driven) | – | – | – | – |
| NHK STRL haptic public viewing (SIGGRAPH'21, SMPTE'23) | Research | Real-time video analysis drives a haptic chair and handheld device (judo). Video **delayed "about one second"** to stay in sync | – | ~ (delay for sync only) | – | Y | – |
| NTT goalball "watching by ear" (Dec 2021) | Demo | About 100 speakers recreate ball and player positions. Co-designed with visually impaired students | ~ | – | – | – | Y |
| Newcastle × CuteCircuit SoundShirt (2024–) | Product | Stadium noise turned into shirt haptics for **deaf** fans | ~ | – | – | Y | – (deaf-first) |
| **OneCourt** (2024–26) | Startup | Tactile pitch board plus generated audio. Microsoft AI for Accessibility grant. Seattle WC 2026 match, Seahawks tests | – | – | – | Y | Y |
| Columbia **Front Row** (UIST 2023) | Research, licensable | CV on tennis broadcast → 3D audio cues. 12 BLV users | – | – | – | – | Y |
| Touch2See · Field of Vision · Action Audio · Sky DAC · FIFA ADC (see 36) | Products | Tactile tablets, ball sonification, human describers | – | – | – | Y/– | Y |
| **Audio Stands (ours)** | Hackathon | Event-driven crowd + look-ahead commentary + talk-back + phone haptics, synthetic data | Y | Y | Y | Y | Y |

### 2. Patents (keyword search; we are not lawyers)

We searched Google Patents' public pages for these themes: live sports audio description, spatial audio for visually impaired viewers, commentary from match data, crowd noise, spectator haptics, and delay/anticipation. Google rate-limited us part-way through (HTTP 503), so some details below come from USPTO full-text PDFs or search-engine summaries, and those are marked.

| Patent | Assignee | Priority → grant | Relevance to Audio Stands |
|---|---|---|---|
| **US11736775B1** "Artificial intelligence audio descriptions for live events" | Amazon Technologies | 9 Dec 2021 → 22 Aug 2023 | ML finds visual elements in live sports video and generates AD as an alternative audio track. No crowd, no spatial audio, no Q&A |
| **US11843473B2** "Audio-orientated immersive experience of an event" (also US11381413, same title) | Disney Enterprises | 8 Jan 2020 → 12 Dec 2023 (via search summary) | **Closest to our crowd/spatial pillar.** Tracking data plus a preset event condition select or generate extra (enhancement) audio, which can be spatial. Works without visuals and names universal design, including visually impaired users |
| **US9691238** "Crowd-based haptics" (family US10083578, US10593167; JP6923245B2) | Immersion Corp. | 29 Jul 2015 → 27 Jun 2017 | Data from attendees' phones becomes haptic tracks for remote viewers, live or stored |
| **CN117377519A** "Simulating crowd noise at live events through sentiment analysis of distributed inputs" (probable US twin: US12706081, unverified) | Sony Interactive Entertainment | 27 May 2021 | Remote viewers' utterances become reaction states, mixed with generic crowd noise. Ours comes from match events, not viewers' voices |
| **US11765439** (continuation US12273600, 8 Apr 2025) "Intelligent commentary generation and playing…" | Tencent | 12 Dec 2019 | Match data stream → candidate events → event sequence → commentary scripts → virtual presenter. This is generic data-to-commentary, so it is not our novelty |
| **US12283291B1** "Factually consistent generative narrations" | Amazon Technologies | filed 16 Aug 2023 → 22 Apr 2025 | Metadata plus transcribed commentary → LLM narration → consistency score → narrated highlight. Relevant to our truth_check |
| **US12483761B2** "Technologies for communicating an enhanced event experience" | Pacers Basketball, LLC | 13 Feb 2020 (grant date unverified) | A claim covers real-time audio highlights in which synthetic voices commentate through the game |
| **ES2894123T3** (JP-origin "audio guide" generation, NHK) | Japan Broadcasting Corp. | 24 May 2017 | Generates audio-description data and multiplexes it with the video and original audio. Matches NHK's Rio-era system (claims not read) |

Also seen, details unverified:
- **US12561976** (JP priority 18 Nov 2021, applicant unknown): live commentary timed adaptively.
- **NVIDIA app. 18/620,998**, "Generating event commentary in videos using AI models" (published 2 Oct 2025).
- **WO2021242325A1** (Sei Consult, 2020): generated artificial ambient sound for remote audiences.

**Not found:** any patent claiming look-ahead from a broadcast delay to shape commentary emotion or build-up. One quick search proves nothing; it only means we found none.

### 3. What prior art says about each pillar

- **Crowd.** In 2020 the crowd was human-operated (Sky/EA). The patents feed it from fans' voices (Sony) or fans' phones (Immersion). Disney is the exception: it covers *event-condition → audio*. Our crowd is driven by the event state and is in sync with the commentary by construction. That is a design choice, not a patentable-looking novelty.
- **Anticipatory commentary.** The research community treats future information as **leakage**. StreamSoccer limits each utterance to information that already existed when it is spoken, and the NBA_Streaming benchmark says the same (via search summary). Our framing differs: a declared broadcast delay, like TV (see [39](39-anticipatory-emotional-commentary.md)). Prior art on delays is either sync-only (NHK haptics, about 1 s) or prediction (a Twente thesis forecasts set pieces in a soccer video game; abstract via search, unverified).
- **Talk-back.** This is common now (FOX/ElevenLabs, Samsung, Alexa+, PL Companion, AiCommentator). Nobody we found **ties the answers to a delayed playback clock**, so that they cannot spoil a look-ahead commentator (see [40](40-conversational-commentator.md)). Nobody we found offers it for blind fans during live play.
- **Haptics.** Blind-first haptics use dedicated hardware: OneCourt, Touch2See, Field of Vision. For sighted or deaf fans there are chairs and shirts (NHK, CuteCircuit). We found no blind-first haptic product that uses only the fan's phone. But phone haptics is a weak channel on the web (see [41](41-haptics-match-tension.md)), so treat it as a bonus, not a claim.

## So what for us

**Audio Stands. Novelty lives in Interpret (tension plan from look-ahead) plus Personalise (spoiler-safe talk-back). It does not live in Explain or Render on their own.**

1. **Write-up claim, safe version:** "Audio Stands combines four channels for blind and low-vision fans: an event-driven crowd, a commentator that uses a declared look-ahead to build tension without spoiling, voice questions answered on the delayed clock, and phone haptics. In a search of products, research and patents (20 Oct 2026), we found each channel separately but not this combination. We found no system that uses look-ahead to shape commentary emotion." Then cite OneCourt, Disney US11843473B2 and AiCommentator as the nearest neighbours. Judges trust a claim more when you name the work closest to it.
2. **Words to avoid:** "first", "world's first", "never done", "patent-pending", "revolutionary", and "predicts the future" (it is a delay, not prediction). "AI commentary" by itself is not novel: IBM, Opta Voice, WSC and Tencent all predate us.
3. **Validation to cite, not compete with:**
   - **OneCourt**: a Microsoft AI for Accessibility grantee. It reports +74.3% comprehension with haptics plus generated AD vs radio (see 42). This is sponsor-aligned proof that generated audio plus touch helps.
   - **RNIB's 6.1/15 TV score** (see 36).
   - **AiCommentator**: 16 users preferred interactive commentary.
   - **CompanionCast**: AI co-viewers raised social presence, which speaks to the isolation pain point in 36.
4. **Partner and contact shortlist, for after the hackathon (no sign-ups now):**
   - Microsoft AI for Accessibility: sponsor fit; OneCourt precedent.
   - RNIB Media & Culture, and CAFE: testing and describer grammar.
   - Columbia CEAL: Front Row is listed for licensing.
   - The AiCommentator authors (Bergen/Chalmers) and the CompanionCast authors: research collaboration.
   - NHK STRL: auto-AD and haptic sync research.
   - OneCourt or Field of Vision: a hardware haptics channel later.
5. **Patent hygiene (not legal advice):** our synthetic-data prototype is a demo. If anyone commercialises it, have counsel look at Disney US11843473B2 (event-triggered spatial enhancement audio) and Amazon US11736775B1 first.

**Other ideas, briefly:**
- **20 Home End / 17 Heartbeat** are absorbed into Audio Stands, and the same caveats apply: Sky 2020 and Immersion are prior art.
- **D Chalk Talk** and **22 Half-Time Talk** sit among many talk-to-sports assistants (Samsung, FOX). They need a distinct hook.
- **13 Recap Dial** overlaps with WSC, Peacock and IBM. Personalised voiced recaps are well established.

## Reuse: code & links

Re-run the patent sweep later. This uses the public Google Patents JSON endpoint, which needs no account but is rate-limited; back off on a 503.

```python
import json, sys, time, urllib.parse, urllib.request, html
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
def gp(q, n=10):
    url = "https://patents.google.com/xhr/query?url=" + urllib.parse.quote(f"q={q}&num={n}") + "&exp="
    d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})))
    for c in d["results"]["cluster"]:
        for r in c["result"]:
            p = r["patent"]; print(p["publication_number"], "|", html.unescape(p["title"]).strip(), "|", p.get("assignee"), "|", p.get("priority_date"))
for q in ['("audio description") (sport) ("visually impaired")', '("crowd noise") (virtual) ("game state")',
          '(commentary) ("broadcast delay") (excitement)']:
    gp(q); time.sleep(5)
```

Lint the write-up for over-claims before submitting:

```python
import re, pathlib
BANNED = r"\b(world'?s first|the first|first ever|never (been )?done|patent[- ]pending|revolutionary|predicts? the future)\b"
for f in pathlib.Path(".").glob("**/*.md"):
    for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        if re.search(BANNED, line, re.I): print(f"{f}:{i}: {line.strip()}")
```

Links:
- AiCommentator full text: https://research.chalmers.se/publication/541995
- WorldCupVoice repo: https://github.com/zicojiao/worldcupvoice
- Disney patent: https://patents.google.com/patent/US11843473
- Amazon AD patent: https://patents.google.com/patent/US11736775

## Sources

- IBM watsonx AI commentary at Wimbledon (AAP/Cision, Jun 2023) — https://www.aap.com.au/aapreleases/cision20230621ae33027 — accessed 20 Oct 2026 (via search summary)
- IBM watsonx Masters 2024 (VKTR reprint of IBM release) — https://www.vktr.com/the-wire/ibm-watsonx-brings-new-generative-ai-capabilities-to-masters-tournament-digital-platforms/ — accessed 20 Oct 2026 (via search summary)
- Stats Perform × Veritone press release (2022) — https://www.statsperform.com/press/veritone-and-stats-perform-partner-to-give-sports-data-a-new-voice/ — accessed 20 Oct 2026 (403; via search summary)
- Speech Technology, Stats Perform/Veritone — https://www.speechtechmag.com/Articles/News/Speech-Technology-News/Stats-Perform-Partners-with-Veritone-for-AI-Commentary-155360.aspx — accessed 20 Oct 2026 (via search summary)
- WSC Sports, NBA GenAI multilingual content (Apr 2025) — https://wsc-sports.com/blog/customer-spotlight/nba-launches-genai-technology-with-wsc-sports-to-automate-multilingual-content/ — accessed 20 Oct 2026
- NBC News, AI Al Michaels for Olympics — https://www.nbcnews.com/news/nbc-use-ai-generated-version-al-michaels-voice-summer-olympics-rcna159108 — accessed 20 Oct 2026 (via search summary)
- TheWrap, ESPN FACTS avatar — https://www.thewrap.com/espn-sec-nation-generative-ai-avatar-facts — accessed 20 Oct 2026 (via search summary)
- SVG Europe, GenAI commentary on Bundesliga — https://www.svgeurope.org/blog/headlines/genai-to-be-used-to-broaden-commentary-options-on-bundesliga-coverage/?print=1 — accessed 20 Oct 2026 (via search summary)
- CAMB.AI, Trophée des Champions AI-translated commentary (Jan 2026) — https://www.camb.ai/fr/blog-post/2026-trophee-des-champions-to-become-first-european-football-match-with-ai-dubbed-commentary — accessed 20 Oct 2026
- ElevenLabs, FOX Sports Colin Cowherd agent — https://elevenlabs.io/blog/foxsports — accessed 20 Oct 2026
- Samsung Newsroom, Vision AI Companion — https://news.samsung.com/us/samsung-vision-ai-companion-bringing-conversational-ai-households-worldwide — accessed 20 Oct 2026 (via search summary)
- Cord Cutters News, Alexa+ sports upgrade — https://cordcuttersnews.com/amazon-quietly-unveils-major-alexa-upgrade/ — accessed 20 Oct 2026 (via search summary, unverified)
- TechRadar, Premier League Companion review — https://www.techradar.com/computing/artificial-intelligence/the-premier-league-companion-is-a-new-ai-powered-tool-for-soccer-fans-but-its-useless-at-least-for-now — accessed 20 Oct 2026 (via search summary)
- Youth Sports Business Report, Pixellot $35M raise — https://youthsportsbusinessreport.com/pixellot-raises-35m-to-scale-ai-powered-game-capture-across-youth-and-high-school-sports/ — accessed 20 Oct 2026 (via search summary)
- DEV Community, WorldCupVoice spotlight — https://dev.to/jingyi_li/project-spotlight-an-open-source-ai-sports-commentator-that-watches-the-match-live-4pch — accessed 20 Oct 2026
- Andrews et al., AiCommentator, IUI 2024, DOI 10.1145/3640543.3645197 — https://research.chalmers.se/en/publication/541995 — accessed 20 Oct 2026
- Wang et al., CompanionCast (arXiv 2512.10918) — https://arxiv.org/abs/2512.10918 — accessed 20 Oct 2026
- Shao et al., StreamSoccer (arXiv 2608.19723) — https://arxiv.org/abs/2608.19723 — accessed 20 Oct 2026
- NBA_Streaming benchmark (arXiv 2608.09200) — https://arxiv.org/pdf/2608.09200 — accessed 20 Oct 2026 (via search summary)
- MatchTime (EMNLP 2024) — https://preview.aclanthology.org/setup/2024.emnlp-main.99 — accessed 20 Oct 2026 (via search summary)
- Live Football Commentary dataset (INLG 2025) — https://aclanthology.org/2025.inlg-main.13 — accessed 20 Oct 2026 (via search summary)
- Chaudhary et al., MCAD (arXiv 2511.09448) — https://arxiv.org/abs/2511.09448 — accessed 20 Oct 2026
- U. Twente thesis, event prediction for soccer video-game commentary — https://essay.utwente.nl/essays/100983 — accessed 20 Oct 2026 (page empty; title via search, unverified)
- SVG Europe, Premier League restart artificial atmosphere (2020) — https://www.svgeurope.org/blog/headlines/premier-league-re-start-uk-pay-tv-broadcasters-to-offer-artificial-atmosphere-and-watch-alongs/ — accessed 20 Oct 2026 (via search summary)
- SVG Europe, Sky Dolby Atmos implementation — https://www.svgeurope.org/blog/headlines/next-generation-audio-summit-inside-skys-implementation-of-dolby-atmos-for-the-latest-premier-league-season-coverage/ — accessed 20 Oct 2026 (via search summary)
- Mobile World Live, Yamaha Remote Cheerer — https://www.mobileworldlive.com/apps/news-apps/yamaha-gives-voice-to-remote-cheering-at-events/ — accessed 20 Oct 2026 (via search summary)
- SIGGRAPH history, Takahashi et al., real-time sports video analysis with haptics (2021) — https://history.siggraph.org/?p=79485 — accessed 20 Oct 2026
- SMPTE MIJ 132(3), Haptic presentation synced with live sports broadcasts (2023) — https://journal.smpte.org/periodicals/SMPTE%20Motion%20Imaging%20Journal/132/3/22/ — accessed 20 Oct 2026
- NTT, goalball watching by sound (Dec 2021) — https://group.ntt/en/newsrelease/2021/12/17/211217a.html — accessed 20 Oct 2026
- Newcastle United, haptic shirts for deaf fans — https://www.newcastleunited.com/en/news/watch-life-changing-reaction-from-deaf-fans-as-they-wear-haptic-shirts-at-st.-james-park — accessed 20 Oct 2026 (via search summary)
- Microsoft Accessibility Blog, OneCourt — https://blogs.microsoft.com/accessibility/onecourt-revolutionizing-accessibility-in-live-sports/ — accessed 20 Oct 2026
- Columbia CEAL, Front Row / tennis video accessibility — https://ceal.cs.columbia.edu/tennisvideoa11y — accessed 20 Oct 2026 (via search summary)
- Google Patents, US11736775B1 (Amazon) — https://patents.google.com/patent/US11736775B1/en — accessed 20 Oct 2026
- Google Patents, US11843473B2 (Disney) — https://patents.google.com/patent/US11843473 — accessed 20 Oct 2026 (via search summary; page rate-limited)
- USPTO full text, US9691238 Crowd-based haptics (Immersion) — https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9691238 — accessed 20 Oct 2026 (scanned; details via search summary)
- Google Patents, JP6923245B2 Audience-based haptics (Immersion) — https://patents.google.com/patent/JP6923245B2/en — accessed 20 Oct 2026 (via public JSON search)
- Google Patents, CN117377519A (Sony Interactive Entertainment) — https://patents.google.com/patent/CN117377519A/en — accessed 20 Oct 2026 (via public JSON search)
- USPTO Official Gazette, US12273600 (Tencent continuation) — https://patentsgazette.uspto.gov/week14/OG/html/1533-2/US12273600-20250408.html — accessed 20 Oct 2026 (via search summary)
- Google Patents, US12283291B1 (Amazon) — https://patents.google.com/patent/US12283291 — accessed 20 Oct 2026 (via search summary)
- Google Patents, US12483761B2 (Pacers Basketball) — https://patents.google.com/patent/US12483761B2/en — accessed 20 Oct 2026 (claim snippet via public JSON search)
- Google Patents, ES2894123T3 (NHK) — https://patents.google.com/patent/ES2894123T3/en — accessed 20 Oct 2026 (snippet via public JSON search)
- USPTO full text, US12561976 Comment generation device — https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12561976 — accessed 20 Oct 2026 (scanned; via search summary)
- Google Patents, WO2021242325A1 (Sei Consult) — https://patents.google.com/patent/WO2021242325A1/en — accessed 20 Oct 2026 (snippet via public JSON search)
