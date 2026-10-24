# Audio Stands: shot list, in recording order

_OWNER: A (potencialbg). Stage 9a, 24 Oct 2026. Goes with [script.md](script.md). Record each take 2–3 times (BUILD_PLAN Stage 9)._

**Demo:** https://lively-ocean-0efe4ae0f.2.azurestaticapps.net/
**Relay (live Ask + Stats MCP):** https://ca-relay-calef3.icycliff-4b45d13b.swedencentral.azurecontainerapps.io

## Before the first take (10 min)

1. **Recorder:** Clipchamp's screen recorder or the Windows Snipping Tool recorder, **system audio on**, mic off
   (except takes Q1 and Q2, where the fan's question must be heard). 1920×1080, 30 fps (file 14).
2. **Browser:** Chrome or Edge, one **InPrivate/Incognito** window (so saved settings don't change the default
   Reds/crowd/vibration setup), zoom **125%**, every other tab closed, notifications off. Headphones on to monitor.
3. **Wake the relay** (it scales to zero, D6; the first request after idle took over 30 s, D17). Open
   `https://ca-relay-calef3.icycliff-4b45d13b.swedencentral.azurecontainerapps.io/health` in a second tab and reload
   until it returns JSON. Do it again before Q1 if more than 10 minutes pass.
4. **Mic permission:** do one throwaway live question first, so the browser's permission prompt isn't in a real take.
5. **Live Ask limits** (relay caps, D17): at most **6 live sessions per 10 minutes and 2 open at once from one IP**.
   Space the live takes out, and close a take's tab before starting the next.
6. **Nothing secret on screen:** no `.env`, no subscription IDs, tenant IDs or keys in the portal header or VS Code.
   Crop or blur them in the edit if they appear.

**Controls used below:** Start is focused on load, so **Enter** starts the match (and pauses it). **A** opens the Ask
menu; **Esc** closes it. URL flags: `radar=1` shows the sound radar; `from=` / `to=` start and stop the replay at a
playhead in seconds (the judge cut runs 670–1150 s = 56:10–64:10; the clock is the cue's `t_in`). The site has no
chapter keys: "Next big moment" is a button, and `from=` gets us to an exact moment instead.

## Takes

| # | Beat (script time) | URL | What to do | Keep |
|---|---|---|---|---|
| **H** | Hero (0:20–0:45) | `https://lively-ocean-0efe4ae0f.2.azurestaticapps.net/?radar=1&from=670&to=720` | Start recording, press **Enter**. Hands off until it pauses itself at 720 s ("End of the clip."). | Match 674.0–684.6 s and 702.8–707.9 s (the `EDIT` list). The radar must be in frame. Also grab a still of the radar just after 707 s for the 0:35.7 freeze. |
| **O** | Opener audio (0:00–0:12) | `https://lively-ocean-0efe4ae0f.2.azurestaticapps.net/?radar=1&from=954&to=968` | Press **Enter**; record until it pauses. | Audio only, 954.8–966.8 s (the stoppage after the yellow card: crowd, no commentary). The picture is black in the edit. |
| **Q1** | Live Ask (0:45–1:05) | `https://lively-ocean-0efe4ae0f.2.azurestaticapps.net/?radar=1&from=754` | Mic on. Press **Enter**. About 4 s in (≈ 758 s, Reds in midfield), press **A**, click **Ask out loud**, wait for the listening cue, then say clearly: **"Where's the ball?"** Let the answer finish and the commentary resume, then stop. | One take, unedited, from the **A** press to the commentary resuming. No shot is due within 8 s of 758 s (next shot 879 s), so "hold that thought" won't fire. |
| **Q2** | Refusal (1:05–1:11) | `https://lively-ocean-0efe4ae0f.2.azurestaticapps.net/?radar=1&from=796` | Mic on. **Enter**; at ≈ 800 s press **A** → **Ask out loud** → say: **"Who wins?"** | The question and the refusal, unedited. In our 31-question run, "Who wins?" got "that's for the match to decide" (D17); keep whatever this take really says. |
| Q3 | Optional, not in the 1:52 cut | `https://lively-ocean-0efe4ae0f.2.azurestaticapps.net/?radar=1&from=1056` | **Enter**; at ≈ 1060 s press **A** → **Where's the ball?** (the offline preset, no mic). | Expected: "Hold that thought, watch this!", then the build-up "Reds... Orlani... danger!" and "Blocked!", then the answer. Spare footage for a longer cut or social clip. |
| **T** | Trace (1:11–1:20) | Azure portal → Application Insights **`appi-as-judge`** → Transaction search, time range **Last 30 days**, search **`workflow.run`** | Open one result's end-to-end transaction view. | 5 s of the span tree: `workflow.run` → `executor.process` director / commentator / verifier / tts, `invoke_agent Director`, `chat gpt-5-mini` (D16). Runs are from 23 Oct 2026. Hide the subscription in the header. |
| **A** | Architecture (1:25–1:35) | The README's Mermaid diagram on GitHub, after this PR merges: `https://github.com/nikikrustev/BerbataAI#architecture` | Screen-record or screenshot at 125% zoom. | The whole diagram, readable at 720p. Light each box in the edit as the voiceover names it. |
| **C** | Copilot + Azure MCP (1:35–1:40) | VS Code in this repo, `.vscode/mcp.json` | Start the **azure** server from its Start link (enter the subscription ID at the prompt **off screen**). Copilot Chat → **Agent** mode → ask: **"Using Azure MCP, list the Container Apps in resource group rg-as-judge and their latest revision."** Optional second ask, to our own MCP server **audiostands-stats** (playhead input 860): **"Where's the ball?"** | 5 s of the question and the answer. If it fails with a tenant mismatch, give the subscription's tenant (D14). The D14 screenshot (resources in `rg-as-judge`) is the fallback. |
| **L** | Listener (1:40–1:46) | (with the listening test, `eval/listening_test.md`) | TODO: the listening test hasn't run yet. Film a participant only with written consent to use the footage in a public video. | 5–6 s of their own words. If there's no consenting participant, skip this take; the script says what replaces it. |
| **E** | End card (1:46–1:52) | Made in Clipchamp | Text only: the demo URL, "Best Use of Microsoft Foundry", "Berbata AI", and "AI voices (Azure AI Speech) · synthetic data · fictional clubs and players". | URL on screen at least 3 s, readable on a phone at 720p. |

The 0:08 problem card, the 0:35.7 Director overlay, the 1:01 latency overlay and the 1:20 eval card are text made in
Clipchamp; their wording and numbers are in [script.md](script.md). Use no other numbers.

## After recording

1. **Edit** in Clipchamp to the times in `script.md`: 1:45–1:55, target 1:52. No music, no logos.
2. **Voiceover:** record it yourself from `voiceover.srt`, or use the AI narration: `python video/narration.py` writes
   `out/narration/vo_NN.mp3` (one per cue; place each at its SRT start) and `out/narration.mp3` (the whole track).
   Its last run (24 Oct, en-US-Ava HD, keyless) fitted every cue within 0.3 s of its slot; HD voices vary a little on
   each render, so it reports any cue that overruns. If you use it, the end card already says "AI voices".
3. **Captions for the live takes and the listener:** once the edit is locked, type the exact words heard into a new
   file `video/takes.srt`, at their video times, labelled `FAN:`, `AI COMMENTATOR:` and `LISTENER:`. Then run
   `python video/make_captions.py`, which merges them into `captions_sdh.srt`. If you move a match clip, change `EDIT`
   in `make_captions.py` first.
4. **Burn in the captions:** run `bash video/assemble.sh out/video/edit.mp4` on the caption-free Clipchamp export (it
   also adds the L/R meter and waveform strip; needs ffmpeg with libass, LGPL is fine). Or caption in Clipchamp from
   `captions_sdh.srt`'s text. Whether Clipchamp imports an SRT file is (unverified).
5. **Check:** `ffprobe -v error -show_entries format=duration -of csv=p=0 <file>` prints under 115. Watch once muted
   and once on laptop speakers; read every caption on a phone at 720p.
6. **Upload** to YouTube: Public, "No, it's not made for kids", English captions from `video/captions_sdh.srt`.
   Give the URL to the Stage 9b prompt.
