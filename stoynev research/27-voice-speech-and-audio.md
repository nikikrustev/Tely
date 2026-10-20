# 27 — Voice in and out: Foundry Voice Live, realtime speech, spoken commentary and audio personalisation

_Accessed/compiled: 20 Oct 2026 · Priority area: Render + Personalise (audio channel); voice input for D Chalk Talk and 22 Half-Time Talk_

## TL;DR

- **Use two separate speech paths.**
  - **One-way commentary.** Turn our cue text into audio with plain Azure TTS and SSML. Pre-render it when the cue is created.
  - **Two-way talk** (pundit asks, the system answers and draws). Use the **Voice Live API**: one WebSocket, `api-version=2026-04-10`. It bundles speech-to-text, an LLM (`gpt-realtime-2.1`, `gpt-realtime-2.1-mini`, `gpt-5.x`, `gpt-4.1` and more), Azure voices, semantic end-of-turn detection, barge-in, echo cancellation and **function calling**. Function calling is how Chalk Talk triggers a "draw on frame" tool.
- **Only one voice in the whole catalogue has a sports-commentary style: `zh-CN-YunjianNeural` (Mandarin).** The voice table lists the styles as `sports-commentary` and `sports-commentary-excited`. The SSML reference spells them `sports_commentary` and `sports_commentary_excited`. No en-GB, en-US or bg-BG voice has these styles.
  - For English excitement, use **HD (DragonHD) voices**. Their styles `excited`, `ecstatic`, `shouting` and `urgent` work on all English text. Add `<prosody>` on top.
  - The Bulgarian voices (Kalina, Borislav) have **no styles**, so use prosody only.
- **Streaming text into TTS (websocket v2) does not accept SSML.** So styled commentary has to be sent as whole sentences of SSML.
  - Pre-generate anything predictable. Our match is seeded and synthetic, so the whole demo can be pre-rendered.
  - Stream live only for Q&A answers.
- **Cost is negligible at hackathon scale.** List prices for East US 2:
  - Neural TTS: $15 per 1M characters. HD: $22 per 1M.
  - Real-time STT: $1 per hour.
  - Voice Live Pro with Azure-voice output: $0.031 per 1K output audio tokens (about $0.04 per minute of speech).
  - The free F0 tier gives 0.5M TTS characters and 5 STT hours per month.
- **Responsible AI.** Custom neural voice and personal voice are **Limited Access, for Microsoft-managed customers only**, so we cannot use them. Use stock voices, label every clip "AI voice", and never imitate a real commentator. Browser audio covers crowd ducking (Web Audio) and tempo-following music (Tone.js). I found **no Azure music-generation model**.

## Findings

### 1. Voice Live API (Azure Speech in Foundry Tools)

| Topic | What the docs say (Voice Live overview and how-to, updated Oct 2026) |
|---|---|
| What it is | "Low-latency, high-quality speech-to-speech interactions for voice agents." STT, a generative model and TTS sit behind **one interface**, and the models are fully managed, so there is nothing to deploy. |
| Protocol | WebSocket: `wss://<resource>.services.ai.azure.com/voice-live/realtime?api-version=2026-04-10&model=gpt-realtime`. The how-to recommends **Voice Live with WebRTC** for browser and mobile clients. Events "mostly match" the Azure OpenAI Realtime events. |
| Auth | Entra ID bearer token (scope `https://ai.azure.com/.default`, roles *Cognitive Services User* and *Foundry User*), or an `api-key` header or query parameter. Browsers cannot set the header. |
| Models and tiers | **Pro:** `gpt-realtime-2.1`, `gpt-realtime-1.5`, `gpt-realtime`, `gpt-4o`, `gpt-4.1`, `gpt-5`/`5.1`/`5.2`/`5.4`, `gpt-5.6-terra`, `azure-realtime`. **Standard:** `gpt-realtime-2.1-mini`, `gpt-realtime-mini`, `gpt-4o-mini`, `gpt-4.1-mini`, `gpt-5-mini`, `gpt-5.6-luna`. **Lite:** `gpt-4.1-nano`, `gpt-5-nano`, `phi4-mm-realtime` (preview). You pick a model and the tier follows from it. |
| Conversation features | Noise suppression (`azure_deep_noise_suppression`) and server echo cancellation. Turn detection types `server_vad`, `semantic_vad`, `azure_semantic_vad` and `azure_semantic_vad_multilingual`. Other settings: `interrupt_response` (barge-in, default **true**), `auto_truncate`, `remove_filler_words` (cuts false barge-ins on "umm", "yeah"), `silence_duration_ms` (default 500). |
| Output extras | `output_audio_timestamp_types: ["word"]` returns `response.audio_timestamp.delta` with `audio_offset_ms`. Viseme IDs are available. Avatars (standard, photo with `vasa-1`/`vasa-2`) can be streamed over WebRTC. Voice `rate` ranges 0.5–1.5. |
| Echo and our mixing | Server AEC assumes the client plays audio as soon as it arrives. If playback is delayed by **more than 2 s**, AEC quality drops. **Live-Reference AEC** (API version `2026-07-15`) exists for the case where the client mixes audio before playback, which is exactly our case: crowd bed plus commentary. The client sends stereo PCM16: mic on channel 0, playback reference on channel 1. |
| Latency numbers | **None published.** The docs claim low latency but give no millisecond figures. Measure it yourself: the SDK's telemetry exposes `gen_ai.voice.first_token_latency_ms`. |

**Languages (relevant to Bulgarian):**
- **Speech in.** `gpt-realtime`/`-mini` list Bulgarian. `mai-transcribe-2` (preview) lists `bg`. The default `azure-speech` multilingual auto-detect model covers only 15 locales and **excludes Bulgarian**, so set `"language": "bg-BG"` explicitly.
- **Filler-word removal** in semantic VAD works only for EN/ES/FR/IT/DE/JA/PT/ZH/KO/HI.
- **Speech out.** Any Azure TTS voice works, including `bg-BG-KalinaNeural` and `bg-BG-BorislavNeural`.

### 2. GPT Realtime direct (Azure OpenAI in Foundry)

- **Models:**
  - `gpt-realtime` (2025-08-28)
  - `gpt-realtime-mini` (2025-10-06, 2025-12-15)
  - `gpt-realtime-1.5` (2026-02-23)
  - `gpt-realtime-2` (2026-05-07)
  - `gpt-realtime-2.1` and `-2.1-mini` (2026-07-07)
  - `gpt-realtime-translate` and `gpt-realtime-whisper` (2026-05-06)
- **Regions:** global deployments in **East US 2 and Sweden Central**.
- **GA flow:**
  1. Your server POSTs to `https://<res>.openai.azure.com/openai/v1/realtime/client_secrets` to get an ephemeral token.
  2. The browser does an SDP exchange with `.../openai/v1/realtime/calls`.
  3. Audio flows over WebRTC. Events flow over a data channel.
- The docs say *"WebSockets aren't recommended for real-time audio streaming because they have higher latency than WebRTC."* Use WebSocket server-to-server only.
- **`gpt-realtime-translate`** translates continuously and returns translated speech plus a transcript. It is **priced per hour** and is aimed at "live streaming events … broadcasts". It is a candidate for live dubbing of English commentary into other languages. Bulgarian quality is **untested** (unverified), and Microsoft says to validate each language pair.
- **Voice Live or raw Realtime?** Voice Live adds Azure voices (including Bulgarian), semantic VAD with filler removal, deep noise suppression and non-realtime LLMs. Raw Realtime gives only the OpenAI built-in voices. **Choose Voice Live.**

### 3. Voices, styles and SSML

| Need | What exists (verified on the Language support and SSML pages) |
|---|---|
| Sports commentary style | Only `zh-CN-YunjianNeural`: `sports-commentary`, `sports-commentary-excited`, `documentary-narration`, `narration-relaxed` and others. The SSML reference describes `sports_commentary` as a *"relaxed and interested tone for broadcasting a sports event"* and the excited variant as an *"intensive and energetic tone"*. The spelling differs between the two pages, so test both. |
| English excitement | HD voices (`en-GB-Ryan:DragonHDLatestNeural`, `en-GB-Ollie:DragonHDLatestNeural`, `en-US-Ava:DragonHDLatestNeural`, …) support styles including `excited`, `ecstatic`, `shouting`, `urgent`, `confident` and `amazed`. The docs say *"Styles are available on all English content for all voices."* Two ways to apply them: `<mstts:express-as style="ecstatic">` or inline markers `[ecstatic] …`. A marker lasts until `[Neutral]`, a `<p>` tag or a sentence boundary. |
| British standard voices | `en-GB-RyanNeural`: chat, cheerful, sad, whispering. `en-GB-SoniaNeural`: cheerful, sad. Both are mild and not commentary-grade. |
| Bulgarian | `bg-BG-KalinaNeural` (F) and `bg-BG-BorislavNeural` (M) are Standard voices with **no styles or roles**. Use `<prosody rate pitch volume>`. |
| Two-person booth | **Multi-talker** `en-US-MultiTalker-Ava-Andrew:DragonHDLatestNeural` uses `<mstts:dialog><mstts:turn speaker="ava">…`. It is in preview, East US / West Europe / Southeast Asia only, and supports **en-US content only**. |
| Knobs | `styledegree` 0.01–2. Prosody `rate` 0.5–2× and `pitch` 0.5–1.5× (or `x-slow`…`x-fast`). `mstts:backgroundaudio` mixes a bed under speech (volume 0–100, fade in/out up to 10,000 ms), which suits pre-rendered clips. |

### 4. Latency design

- **TTS metrics.** The docs define *first byte latency* (independent of text length) and *finish latency* (grows with text length). Their target is *"one network route trip time plus the first audio chunk latency"*.
- **How to get there:**
  - stream the audio chunks;
  - pre-connect (`Connection.from_speech_synthesizer(...).open(True)`) when you know a line is coming;
  - reuse one synthesizer object;
  - use compressed formats (for example 48 kbps MP3 instead of 384 kbps PCM).
- **Text streaming input** (`wss://{region}.tts.speech.microsoft.com/cognitiveservices/websocket/v2`) feeds LLM tokens straight into TTS. It **does not support SSML**, so you lose styles and prosody. Use it for Q&A answers only.
- **Barge-in.** On `input_audio_buffer.speech_started`, flush the local playback queue (the official sample calls `skip_pending_audio()`). Voice Live already cancels the response when `interrupt_response` is true. Turn on `remove_filler_words` so crowd noise or "yeah" doesn't cut the pundit off.
- **When to pre-generate vs go live:**

| Pre-generate (at cue creation, or offline for the demo) | Live |
|---|---|
| Templated cues (milestones, speed-trap callouts, name intros), replays, recap, half-time summary script, all audio in the recorded demo video | Pundit or fan questions (Chalk Talk, Half-Time Talk), LLM explanations created after a live event, translation |

- **Queue rules.** Every speech item inherits the cue's `ttl_ms`. Drop stale lines rather than speaking late. A higher-priority line (goal) cancels a lower one (pass). Keep lines to roughly 8–15 words. Cue JSON gets an optional `speech` block: `{voice, style, ssml, audio_url, duration_ms, word_timings[]}`.

### 5. Pricing (list price, East US 2, USD)

The pricing page loads its figures with JavaScript, so these come from the **Azure Retail Prices API** (`serviceName 'Foundry Tools'`, product `Azure Speech`), pulled 20 Oct 2026.

| Meter | Price |
|---|---|
| Neural TTS (S1) | $15 / 1M characters |
| Neural HD TTS | $22 / 1M characters |
| Personal voice TTS / Custom neural realtime | $24 / 1M characters (Limited Access) |
| Real-time STT (S1) | $1 / audio hour; fast transcription $0.36/h; batch $0.18/h |
| Voice Live Pro: Azure standard speech audio in / out | $0.017 / $0.031 per 1K tokens |
| Voice Live Pro: LLM native audio in / out (`gpt-realtime` voice) | $0.032 / $0.064 per 1K tokens |
| Voice Live Pro: text in / out | $0.004 / $0.016 per 1K tokens |
| Voice Live Standard: speech audio in / out | $0.015 / $0.026 per 1K tokens |
| Voice Live Lite: speech audio in / out | $0.015 / $0.025 per 1K tokens |
| Standard avatar, real time | $0.50 / minute |
| Free tier F0 (pricing page) | 0.5M neural TTS characters/month; 5 STT audio hours/month |

**Our estimates, based on the documented rates of about 10 input and about 20 output audio tokens per second:**
- One minute of Voice Live answer speech with an Azure voice costs about 1,200 tokens × $0.031/1K ≈ **$0.037**. With the native `gpt-realtime` voice it costs about $0.077.
- A 70-character commentary line costs about $0.001 with TTS. The free tier covers about 7,000 lines a month.

### 6. Responsible AI

- **Limited Access.** Custom neural voice, its lite version, **personal voice** (including the demo) and custom avatars require registration. *"Only customers managed by Microsoft … are eligible."* Approved use is limited to registered use cases, written consent from the voice talent is required, and you must *"disclose the synthetic nature"* of the voice and offer a feedback channel. **We cannot use any of this. Don't plan for a branded or cloned voice.**
- **Disclosure guidelines.** A voice "based on the voice of a widely recognizable real person (e.g., celebrity…)" counts as a *Human-like persona*. That raises the disclosure level, and long or frequent exposure raises it further. A 90-minute commentary is high exposure. **Recommendation:** add a visible "AI voice" badge on the audio toggle, a spoken disclosure on first play, and an info link.
- **Never prompt for or name a real commentator's style** ("say it like <famous pundit>"). Don't use real club chants or anthems in Home End: they may be copyrighted and trademarked, and the event bans real PL data anyway.

### 7. Browser audio: mixing, crowd and music

- **Ducking.** `AudioParam.setTargetAtTime(target, startTime, timeConstant)` is an exponential approach. It reaches 63.2% after one time constant and **95% after three**. MDN suggests setting `timeConstant` to "one third of the desired duration".
- **Autoplay.** Web Audio playback outside a user gesture "is subject to autoplay rules". Start or resume the `AudioContext` (or call `Tone.start()`) from the "Enable audio" click.
- **Music (19 Match Music).** No music-generation model turned up in my searches of the Foundry catalogue (unverified, because the catalogue is huge). Procedural audio in the browser is the practical route. **Tone.js 15.1.22** (latest on npm) offers `Tone.getTransport().bpm.rampTo(120, 10)` and `scheduleRepeat(cb, "8n")`. Map a rhythm metric (passes per minute, possession-change rate) to BPM, and map pressure to filter cutoff or minor/major.
- **Crowd (20 Home End).** Use filtered noise plus gain envelopes driven by events (a swell on a shot, a roar on a goal, a groan on a miss), panned by club end (`StereoPannerNode`). Ship royalty-free, generic crowd beds per "home/away". The Home End twist is the mix, not real chants.

## So what for us

**Stages:** Render (an audio track timed by the cue clock) and Personalise (voice, language, verbosity and mix per viewer). The Ingest-to-Explain path is unchanged: speech is produced from the cue JSON we already have.

| Idea | Recommendation |
|---|---|
| Spoken co-commentary per audience/language (A TwinCast, B Speed Trap, C One Number) | At cue creation, render `text[audience]` to SSML and store `audio_url` and word timings. Voices: English casual = `en-GB-Ollie:DragonHDLatestNeural` with `[excited]` on big moments; analyst = calmer `en-GB-Ryan:DragonHDLatestNeural`; Bulgarian = Borislav with prosody. Use a "Mandarin" toggle with Yunjian `sports-commentary-excited` as a showcase. Sync captions and overlays with word timestamps (see 03). |
| **D Chalk Talk** | Voice Live, `gpt-realtime-2.1-mini` or `gpt-5.6-luna` (Standard tier), `azure_semantic_vad` with `remove_filler_words`, and **one function tool `draw_on_frame`** whose arguments are our overlay shapes. The tool handler publishes a cue over Web PubSub, returns "drawn", and the model narrates while the drawing appears. Ground it by giving the tool only ids from our event store. Use Live-Reference AEC if crowd audio plays from the same speakers. |
| 22 Half-Time Talk | Pre-generate a two-voice recap with the multi-talker Ava/Andrew voice (en-US only). Then open a Voice Live session for follow-up questions. |
| 20 Home End | Client-side Web Audio: club-end crowd bed, event envelopes, duck under speech (snippet below). No Azure service is needed. |
| 19 Match Music | Tone.js Transport BPM follows our rhythm metric with `rampTo`. Say plainly in the write-up that it is procedural, not AI-generated. |
| Accessibility audio description | Add an "Audio description" profile: a priority queue (goal > shot > dangerous pass), a short factual script, and ball x position mapped to stereo pan. Competitors (Audio Eyes, Blind-side, per our lead's notes; research 15 also records a rival claiming audio description for blind fans) mean this is **not unique on its own**. It becomes ours if it is *verified* (every spoken number has a truth_check) and *synced* (word timings drive the queue). |

**Do first:** pre-rendered SSML commentary for the demo (deterministic, zero latency, cheap). **Do second:** a Voice Live Chalk Talk with one tool. Skip avatars (extra cost and regions), custom voice (not allowed) and live translation (polish only).

## Reuse: code & links

**Voice Live session for Chalk Talk (Python, `pip install azure-ai-voicelive[aiohttp]`, v1.3.0).** The structure follows the official `function-calling-quickstart.py`. Mic capture and playback are omitted; copy them from `model-quickstart.py`.

```python
import asyncio, base64, json
from azure.identity.aio import DefaultAzureCredential
from azure.ai.voicelive.aio import connect
from azure.ai.voicelive.models import (RequestSession, Modality, AzureStandardVoice, InputAudioFormat,
    OutputAudioFormat, AudioEchoCancellation, AudioNoiseReduction, AzureSemanticVadMultilingual,
    FunctionTool, FunctionCallOutputItem, ItemType, ServerEventType)

DRAW = FunctionTool(name="draw_on_frame", description="Draw a telestrator shape on the current frame.",
    parameters={"type": "object", "properties": {
        "shape": {"type": "string", "enum": ["arrow", "circle", "zone", "pass_lane"]},
        "player_ids": {"type": "array", "items": {"type": "string"}},
        "event_id": {"type": "string"}, "label": {"type": "string"}},
        "required": ["shape", "event_id"]})

async def main(publish_cue, play_pcm, stop_playback):
    async with connect(endpoint="https://<res>.services.ai.azure.com/", credential=DefaultAzureCredential(),
                       model="gpt-realtime-2.1-mini") as conn:
        await conn.session.update(session=RequestSession(
            modalities=[Modality.TEXT, Modality.AUDIO],
            instructions="You are a football analyst. Use only event ids from tools. Max 2 sentences.",
            voice=AzureStandardVoice(name="en-GB-RyanNeural"),
            input_audio_format=InputAudioFormat.PCM16, output_audio_format=OutputAudioFormat.PCM16,
            input_audio_echo_cancellation=AudioEchoCancellation(),
            input_audio_noise_reduction=AudioNoiseReduction(type="azure_deep_noise_suppression"),
            turn_detection=AzureSemanticVadMultilingual(),   # barge-in on by default
            tools=[DRAW]))
        # mic loop elsewhere: await conn.input_audio_buffer.append(audio=base64.b64encode(chunk).decode())
        pending = {}
        async for ev in conn:
            if ev.type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED:
                stop_playback()                                   # barge-in: flush local queue
            elif ev.type == ServerEventType.RESPONSE_AUDIO_DELTA:
                play_pcm(ev.delta)
            elif ev.type == ServerEventType.CONVERSATION_ITEM_CREATED and ev.item.type == ItemType.FUNCTION_CALL:
                pending[ev.item.call_id] = ev.item.id
            elif ev.type == ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE:
                args = json.loads(ev.arguments)
                ok = publish_cue(args)                            # -> Web PubSub overlay cue, validated ids
                await conn.conversation.item.create(previous_item_id=pending.pop(ev.call_id),
                    item=FunctionCallOutputItem(call_id=ev.call_id, output=json.dumps({"drawn": ok})))
                await conn.response.create()
```

**SSML: commentary styles (pre-rendered per cue).**

```xml
<!-- Mandarin showcase: the only voice with sports styles. Voice table spells it with hyphens, SSML ref with underscores: test both -->
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="zh-CN">
  <voice name="zh-CN-YunjianNeural">
    <mstts:express-as style="sports-commentary-excited" styledegree="1.6">射门！球进了！</mstts:express-as>
  </voice>
</speak>

<!-- English: HD voice style + prosody -->
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-GB">
  <voice name="en-GB-Ollie:DragonHDLatestNeural">
    <mstts:express-as style="ecstatic"><prosody rate="+15%" pitch="+5%">Thirty-four kilometres an hour, and he's clean through!</prosody></mstts:express-as>
  </voice>
</speak>

<!-- Bulgarian: no styles, prosody only -->
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="bg-BG">
  <voice name="bg-BG-BorislavNeural"><prosody rate="+20%" pitch="high" volume="+10%">Гол! Невероятен удар!</prosody></voice>
</speak>
```

```python
import azure.cognitiveservices.speech as speechsdk  # render once, upload to Blob, put URL in cue.speech.audio_url
cfg = speechsdk.SpeechConfig(subscription=KEY, region="swedencentral")  # HD voices: limited regions
cfg.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio24Khz48KBitRateMonoMp3)
synth = speechsdk.SpeechSynthesizer(speech_config=cfg, audio_config=None)
res = synth.speak_ssml_async(ssml).get()   # res.audio_data -> bytes
```

**Web Audio: duck the crowd under commentary.**

```js
const ctx = new AudioContext();                       // create/resume inside the "Enable audio" click
const crowdGain = ctx.createGain(), voiceGain = ctx.createGain();
crowdGain.connect(ctx.destination); voiceGain.connect(ctx.destination);
const pan = new StereoPannerNode(ctx, { pan: homeEndIsLeft ? -0.6 : 0.6 });  // Home End side
async function loop(url, gainNode, panner) {
  const buf = await ctx.decodeAudioData(await (await fetch(url)).arrayBuffer());
  const src = new AudioBufferSourceNode(ctx, { buffer: buf, loop: true });
  (panner ? src.connect(panner).connect(gainNode) : src.connect(gainNode)); src.start();
}
function duck(on) {                                   // 3 x timeConstant ≈ 95% of the way
  crowdGain.gain.setTargetAtTime(on ? 0.25 : 1.0, ctx.currentTime, on ? 0.08 : 0.4); // fast down, slow up
}
async function speak(url) {
  const buf = await ctx.decodeAudioData(await (await fetch(url)).arrayBuffer());
  const src = new AudioBufferSourceNode(ctx, { buffer: buf }); src.connect(voiceGain);
  duck(true); src.onended = () => duck(false); src.start();
  return src;                                         // keep handle: src.stop() for barge-in / stale cue
}
function roar(level = 1.6, holdS = 2) {               // event swell on goal/shot
  const g = crowdGain.gain, t = ctx.currentTime;
  g.cancelScheduledValues(t); g.setTargetAtTime(level, t, 0.15); g.setTargetAtTime(1.0, t + holdS, 0.8);
}
```

**Tone.js: tempo follows match rhythm (Tone.js 15.1.22).**

```js
import * as Tone from "tone";
const kick = new Tone.MembraneSynth().toDestination();
const pad = new Tone.PolySynth(Tone.Synth).connect(new Tone.Filter(800, "lowpass").toDestination());
const T = Tone.getTransport();
T.bpm.value = 90;
T.scheduleRepeat((time) => kick.triggerAttackRelease("C1", "8n", time), "4n");
T.scheduleRepeat((time) => pad.triggerAttackRelease(window.pressure > 0.6 ? ["A3","C4","E4"] : ["C4","E4","G4"], "1m", time), "1m");
document.querySelector("#music").onclick = async () => { await Tone.start(); T.start(); };
// called on every rhythm update from our pipeline (e.g. passes/min over last 2 minutes)
export function onRhythm(passesPerMin) {
  const bpm = Math.min(150, Math.max(70, 60 + passesPerMin * 3));   // our mapping, tune by ear
  T.bpm.rampTo(bpm, 4);                                              // smooth 4 s glide
}
```

**Links**
- Voice Live samples (Python quickstarts, function calling, Live-Reference AEC, avatar, web assistant): https://github.com/microsoft-foundry/voicelive-samples
- Python SDK `azure-ai-voicelive` 1.3.0: https://pypi.org/project/azure-ai-voicelive/
- TTS text-stream sample (LLM tokens to TTS): https://github.com/Azure-Samples/cognitive-services-speech-sdk/tree/master/samples/python/tts-text-stream
- Realtime WebRTC token-service plus browser sample: on the Learn WebRTC page (sources)

## Sources

- Voice Live API overview (models, tiers, features) — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live — accessed 20 Oct 2026
- How to use the Voice Live API (endpoint, session, VAD, AEC, voices, timestamps, avatars) — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live-how-to — accessed 20 Oct 2026
- Voice Live API language support — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live-language-support — accessed 20 Oct 2026
- Use the GPT Realtime API via WebRTC — https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/realtime-audio-webrtc — accessed 20 Oct 2026
- GPT Realtime Translate overview — https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/gpt-realtime-translate — accessed 20 Oct 2026
- Language and voice support (TTS voices, styles, footnotes) — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=tts — accessed 20 Oct 2026
- SSML voice and sound (express-as, styles, HD styles, multi-talker, prosody, background audio) — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-synthesis-markup-voice — accessed 20 Oct 2026
- How to lower speech synthesis latency (streaming, pre-connect, text streaming) — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-lower-speech-synthesis-latency — accessed 20 Oct 2026
- Limited Access, custom neural voice / personal voice / custom avatar — https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/speech-service/text-to-speech/limited-access — accessed 20 Oct 2026
- Disclosure design guidelines for synthetic voices — https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/speech-service/text-to-speech/concepts-disclosure-guidelines — accessed 20 Oct 2026
- Azure Speech pricing page (free tier only; paid figures load via script) — https://azure.microsoft.com/en-us/pricing/details/speech/ — accessed 20 Oct 2026
- Azure Retail Prices API (eastus2, serviceName 'Foundry Tools', product 'Azure Speech') — https://prices.azure.com/api/retail/prices — accessed 20 Oct 2026
- azure-ai-voicelive on PyPI (README, events) — https://pypi.org/project/azure-ai-voicelive/ — accessed 20 Oct 2026
- voicelive-samples: model-quickstart.py, function-calling-quickstart.py — https://github.com/microsoft-foundry/voicelive-samples/tree/main/python/voice-live-quickstarts — accessed 20 Oct 2026
- MDN, AudioParam.setTargetAtTime() — https://developer.mozilla.org/en-US/docs/Web/API/AudioParam/setTargetAtTime — accessed 20 Oct 2026
- MDN, Autoplay guide for media and Web Audio APIs — https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Autoplay — accessed 20 Oct 2026
- Tone.js Transport source (bpm.rampTo, scheduleRepeat), v15.1.22 — https://github.com/Tonejs/Tone.js/blob/15.1.22/Tone/core/clock/Transport.ts — accessed 20 Oct 2026
- Tone.js on npm (latest 15.1.22) — https://www.npmjs.com/package/tone — accessed 20 Oct 2026
