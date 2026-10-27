# The "how it works" segment: screen recordings + AI voiceover

_27 Oct 2026. Fills 0:25–1:44 of the 1:52 video, between the Higgsfield clips. The shape follows the common
pattern for a "how it works" half: app → Foundry portal → trust beat → architecture → CI → end card._

## The whole video

| Time | What | Sound |
|---|---|---|
| 0:00–0:10 | Higgsfield clip 1: home, tap, "Start button" | its own |
| 0:10–0:25 | Higgsfield clip 2: the stadium goal | its own |
| **0:25–1:44** | **This segment: the real app, then what's under it** | narrator (`voiceover_infra.srt`) + the app's own audio |
| 1:44–1:52 | Higgsfield clip 3: back home, logo, "Telly: teleport to the stands" | its own. Add the URL and the footer as text (below) |

Transitions:
- **Home → stadium:** a J-cut. Detach clip 2's audio and start the crowd about 1 s early, under the tap. Cut on the
  green glow, with a 0.3–0.5 s Zoom in or Fade through white.
- **Stadium → segment:** a hard cut on the roar.
- **Segment → clip 3:** a hard cut. Clip 3's pull-back to black does the work.
- If clip 2 runs straight into clip 3 in a shorter cut: a 0.3 s cross fade on his face (the shots match), and let the
  roar run about 1 s into the living room (L-cut).

## Beats, pages and voiceover

Every number here is in `eval/report.json` or the README; the voiceover keeps the three phrases
`pipeline/tests/test_video_captions.py` checks, should this file ever replace `voiceover.srt`.

| Time | Record this page | Do on screen | Lower-third label | Voiceover (cue) |
|---|---|---|---|---|
| 0:25–0:38 | **The live app:** https://lively-ocean-0efe4ae0f.2.azurestaticapps.net/?radar=1 | Phone frame. Tap **Reds v Navy**, press **Start**. Keep recording ~12 s: at about 5 s the voice builds, "Navy coming... Olvholm... here's a chance!", the radar moves and the crowd rises. In the edit, keep 0:29–0:35 as the app's own audio, no narrator | `Live demo · Azure Static Web Apps` | 1 "This is Tely, running live on Azure." · (app audio) · 2 "The voice lifted four seconds before the header." |
| 0:38–0:50 | **Architecture diagram:** https://github.com/nikikrustev/BerbataAI#architecture-what-shipped | Scroll so the whole diagram is in view. Slow zoom in the edit (Clipchamp: Zoom effect) from the generator box to the Director box | `Microsoft Agent Framework · look-ahead firewall` | 3 "Here's how. A seeded generator plays a synthetic match. Our Director agent…never the result." |
| 0:50–0:54 | **Microsoft Foundry:** https://ai.azure.com → project **audiostands** → **Models + endpoints** | Show the gpt-5-mini deployment row (and the realtime model for Voice Live if it's in the same list) | `Microsoft Foundry · gpt-5-mini` | 4 "It runs on gpt-5-mini in Microsoft Foundry… |
| 0:54–0:58 | **Application Insights:** https://portal.azure.com → the Application Insights resource with the Director traces → **Transaction search** → open one `workflow.run` | The end-to-end trace: director → commentator → verifier → tts | `Application Insights · OpenTelemetry` | …and every run is traced in Application Insights." |
| 0:58–1:05 | **The eval report:** https://github.com/nikikrustev/BerbataAI/blob/main/eval/report.md | Scroll to the lines / spoiler leaks / numbers verified rows. Optional: a highlight box over them in the edit | `Measured · eval/report.json` | 5 "A Verifier checks every line in code: seventy lines, zero spoiler leaks, every number verified." |
| 1:05–1:20 | **The live app again**, same URL | Mid-match, press **Ask the commentator**, wait for the beep, ask **"Who wins?"**. It refuses to predict. This is our trust beat: the AI can't be talked into spoiling the match. One take, unedited, app audio only from 1:09 | `LIVE · Foundry Voice Live · unedited` | 6 "And fans can ask out loud, through Foundry Voice Live." then silence for the answer |
| 1:20–1:28 | **Azure portal:** https://portal.azure.com → Resource groups → **rg-as-judge** → Overview | The resource list: Static Web App, the Container App relay, Application Insights, the identity | `Azure Container Apps · managed identity` | 7 "Its tools are locked to the fan's moment, on a Container Apps relay with a managed identity: no keys." |
| 1:28–1:35 | **VS Code**, GitHub Copilot Chat in **Agent** mode | Ask: *"Using the Tely stats MCP server, what's the score at 60:00?"* and let the tool call and answer show. If time: *"List the resources in rg-as-judge"* (Azure MCP Server) | `GitHub Copilot · Azure MCP · Stats MCP` | 8 "The same tools are an MCP server we query from GitHub Copilot in VS Code." |
| 1:35–1:44 | **GitHub Actions:** https://github.com/nikikrustev/BerbataAI/actions | The run list, all green. Hover the CI workflow (it includes the WCAG 2.2 AA axe tests) | `CI on every push · WCAG 2.2 AA` | 9 "Every line is voiced by Azure Speech HD, in seven languages, and every push runs our tests, accessibility included." |

**Over clip 3 (1:44–1:52), as text in the edit:** the URL `lively-ocean-0efe4ae0f.2.azurestaticapps.net`, then
"Best Use of Microsoft Foundry · Berbata AI", and the footer **"AI voices (Azure AI Speech) · AI-generated imagery
(Higgsfield) · synthetic data · fictional clubs and players"**. Hold the URL for at least 3 s.

While each Higgsfield clip plays, keep a small **"AI-generated imagery"** label on screen (our plan labels every AI asset). The clips must carry no visible Higgsfield watermark: the rules ban third-party
logos in the video (`stoynev research/12`).

## Recording checklist

- **Record in Clipchamp** (Record & create → Screen), or with the Windows Snipping Tool's video mode. 1920×1080.
- Browser: hide the bookmarks bar, close other tabs, zoom 125% so text reads at 720p, dark theme where the site has one.
- **Before you record the portals, check nothing secret is on screen:** no keys, connection strings or tokens. Subscription
  IDs are not secret, but blur them if you'd rather.
- Wake the relay first: open https://ca-relay-calef3.icycliff-4b45d13b.swedencentral.azurecontainerapps.io/health and reload
  until it shows JSON. Do one throwaway question first, so the microphone prompt doesn't appear in the real take.
- Record each beat a bit longer than its slot (2–3 s either side). Cut to the slot in the edit.
- Speed up any loading screens in the edit (Clipchamp: Speed) rather than showing a spinner.

## The narrator

The narrator is **en-US-Ava HD**, a different voice from the commentator (Brian) and the deep voice in clip 3. Render it
with Azure Speech on your machine (keyless, `az login`):

```
python video/narration.py --srt video/voiceover_infra.srt --out out/narration_infra
```

It writes one MP3 per cue to `out/narration_infra/` (drop each on the timeline at its start time) and the whole track
as `out/narration_infra.mp3`. A cue that runs past its slot is reported. Trim the line or the slot.
Check the cues first without calling Azure: add `--dry-run`.
