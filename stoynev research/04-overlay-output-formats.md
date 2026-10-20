# 04 — Real-time broadcast overlay output: formats, timing and tools

_Accessed/compiled: 20 Oct 2026 · Priority area: Render stage (timed cue JSON → on-screen graphics, key/fill, burn-in)_

## TL;DR

- **Broadcast graphics today are HTML pages driven by four JS functions: `update(data)`, `play()`, `stop()` and `next()`.** CasparCG (GPL-3.0) calls them through AMCP. SPX Graphics Controller (MIT) uses the same functions plus a `SPXGCTemplateDefinition` object. EBU **OGraf** (MIT, Graphics spec v1 stable since 2025-09-17) is the new vendor-neutral version: a Web Component with `load/playAction/stopAction/updateAction`. If we write one template that exposes the CasparCG functions, CasparCG, SPX, OBS and a plain browser can all run it.
- **Alpha is easy if we keep it in the browser and render it once.** The HTML has a transparent background. Puppeteer `omitBackground` gives PNG frames with alpha. ffmpeg turns those into **ProRes 4444** (`prores_ks -profile:v 4444 -pix_fmt yuva444p10le`), **VP9 WebM** (`yuva420p`) or **qtrle** (`argb`), splits them into **key + fill** with `alphaextract`, or burns them in with `overlay` (which supports `enable='between(t,a,b)'`).
- **Sync on the media clock, not the wall clock.** In the browser, `requestVideoFrameCallback` (Baseline 2024) gives `metadata.mediaTime` for each presented frame. Convert `tc_in` to seconds and compare. For delivery, the cue JSON can ride as **WebVTT metadata cues** (any one-line text, JSON allowed) or as HLS `EXT-X-DATERANGE` with `X-` attributes (hls.js turns these into metadata TextTrack cues).
- **Safe areas (verified in EBU R 95 v1.1, note 5):** action-safe margin 3.5% and graphics-safe margin 5% on each edge. On 1920×1080 that is about 67/38 px and 96/54 px. SMPTE ST 2046-1 gives the same boxes as 93% / 90% (from secondary sources).
- **Demo studio:** OBS (obs-websocket built in since 28.0, port 4455) with a 1920×1080 browser source. Push cues with `CallVendorRequest → obs-browser / emit_event`. SCTE-35 (`splice_insert`, or `time_signal` + segmentation descriptor) is the standard way to signal breaks, which is useful for **23 Safe Break**.

## Findings

### 1. How HTML graphics are driven (template APIs and tools)

**CasparCG HTML producer.** The server embeds Chromium (CEF). `PLAY 1-20 [HTML] http://host/page.html` loads any URL as a layer, and the `[HTML]` prefix is parsed in `html_producer.cpp`. For templates, the CG proxy source (`html_cg_proxy.cpp`) shows exactly what each AMCP command runs inside the page:

| AMCP | JS executed in page |
|---|---|
| `CG 1-20 ADD 1 tpl 1 "<data>"` | `update("<data>")`, then `play()` if play-on-load = 1 |
| `CG 1-20 UPDATE 1 "<data>"` | `update("<data>")` (string escaped) |
| `CG 1-20 PLAY 1` / `STOP 1` / `NEXT 1` | `play()` / `stop()` / `next()` |
| `CG 1-20 REMOVE 1` | `remove()` |
| `CG 1-20 INVOKE 1 "fn(1)"` | `fn(1)` (any function) |

The data is passed as a raw string. The official AMCP docs still say "inline XML or a reference to a saved dataset". The old wiki says JSON works from Server 2.1.0b1 / Client 2.0.8, and the proxy code forwards any string. So templates should accept both: parse JSON first, then fall back to XML `<templateData>`. The default AMCP TCP port in the shipped `casparcg.config` is **5250**. The latest release is v2.5.1-stable (2026-09-16).

**SPX Graphics Controller** (MIT, Node.js, web UI) plays HTML templates to OBS, vMix or CasparCG renderer URLs. Its `spx_interface.js` defines `update(data)`, which does `JSON.parse` and writes each field into the DOM element with that id (`f0`, `f1`, …) before calling `runTemplateUpdate()`. It also defines `play()`, `stop()` (calls `runAnimationOUT()`) and `next()` (calls `runAnimationNEXT()`). Each template declares a `window.SPXGCTemplateDefinition` with `playserver`, `playchannel`, `playlayer`, `webplayout`, `out` ("manual" or a duration), `dataformat: "json"` and `DataFields[]` (`field`, `ftype`, `title`, `value`). This is the same function contract as CasparCG, so one template can serve both.

**EBU OGraf.** This is an open spec for portable HTML graphics. A graphic is a manifest whose name must end in `.ograf.json`, plus a Web Component. Required methods are `load()`, `dispose()`, `playAction()`, `stopAction()`, `updateAction()` and `customAction()`. Non-real-time graphics also need `goToTime()` and `setActionsSchedule()`, which is relevant for frame-accurate offline rendering. The Server API v1 became stable on 2026-08-13. SPX already lists OGraf support, and its repo ships `ograf/` versions of its template pack.

| Tool | What it is | Free / open? |
|---|---|---|
| CasparCG Server | Playout server: HTML/Flash/video layers → SDI (DeckLink), NDI, screen | Yes, GPL-3.0 |
| SPX-GC | Web rundown controller for HTML templates | Yes, MIT. Paid Solo/Production/Broadcast tiers add features (prices not shown) |
| OGraf | EBU template spec + devtool + simple renderer (SuperFlyTV) | Yes, MIT |
| LOOPIC | Browser-based template builder that exports to OGraf, CasparCG, SPX, LiveOS, H2R | "Get started for free"; limits/pricing not checked (unverified) |
| H2R Graphics | Desktop graphics app with browser output and an HTTP API | Free tier; Pro is a one-time USD 80 (2 activations) |
| Singular.live | Cloud HTML graphics, REST/SDK | Free plan = 1 watermarked output, 5,000 REST calls/day. Pro USD 150/month |
| Viz Flowics | Cloud HTML5 graphics with no-code sports/data connectors | Commercial. No public price found |

### 2. Key & fill, alpha output

**Key & fill** means two video signals: *fill* (the colour graphic) and *key* (a greyscale matte where white = opaque). A downstream keyer in the vision mixer cuts the fill over programme video. CasparCG's DeckLink consumer has `<keyer>external|external_separate_device|internal|disabled|default</keyer>` (default `external`), with `external_separate_device` sending key out of a second card (`<key-device>`). Both the DeckLink and screen consumers have a `<key-only>` flag, so a second consumer can output just the matte. CasparCG also has an `<ndi>` consumer.

**NDI with alpha:** full-bandwidth NDI (SpeedHQ) carries 4:2:2:4 YUVA, and the SDK FourCC `UYVA` is the UYVY plane followed by an 8-bit alpha plane. NDI HX alpha (H.264/H.265 YUVA 4:2:0:4) works only in some Vizrt software. vMix documents an NDI alpha switch with Straight or Premultiplied modes.

**HTML with a transparent background:** OBS browser source default CSS already sets a transparent `body` background (default size 800×600, so set 1920×1080). For offline rendering, Puppeteer `page.screenshot({omitBackground: true})` "allows capturing screenshots with transparency" (PNG by default).

**ffmpeg alpha formats** (verified against FFmpeg source and docs):
- `prores_ks` profiles include `4444` and `4444xq`. `alpha_bits` can be 0, 8 or 16, and the encoder accepts `yuva444p10`.
- `libvpx-vp9` accepts `yuva420p`. It encodes alpha as a second stream.
- `qtrle` (QuickTime Animation) accepts `argb`. It is lossless but produces large files.
- `alphaextract` outputs the alpha as greyscale (key), and `alphamerge` puts it back.
- `overlay` has `x`, `y`, `eof_action` (repeat/endall/pass), `format`, `alpha` (straight/premultiplied) and timeline `enable`. The docs advise `setpts=PTS-STARTPTS` when the two inputs start at different timestamps.

### 3. Timing and sync

- **SMPTE timecode** is `HH:MM:SS:FF` (ST 12-1). Drop-frame is shown with `;` and only applies to 29.97/30 fps (secondary sources). Using **25 fps non-drop** avoids the issue. Then `seconds = ((HH*60+MM)*60+SS) + FF/25`.
- **`requestVideoFrameCallback`** fires once per *presented* video frame, at the video rate or the display rate, whichever is lower. It gives `mediaTime`, which is on the `currentTime` timeline, and `presentedFrames`, where gaps mean dropped frames. It can be one v-sync late. It is Baseline 2024, and you can detect it with `"requestVideoFrameCallback" in HTMLVideoElement.prototype`. Fall back to polling `video.currentTime` in a `requestAnimationFrame` loop. `timeupdate` fires too rarely to rely on.
- **WebVTT metadata cues:** in a `<track kind="metadata">`, the cue text is "time-aligned metadata". The spec says it "is often provided as a JSON construct". The payload cannot contain blank lines or `-->`, and cue identifiers must be unique. Set the track's `mode = "hidden"`: cues stay active and events fire, but nothing is drawn. Then use `cuechange` and `track.activeCues`.
- **HLS:** `EXT-X-DATERANGE` needs `ID` and `START-DATE`. It can take `DURATION`, `CLASS`, `X-<client-attribute>` and `SCTE35-OUT/IN/CMD`. A playlist that uses it **must** also contain `EXT-X-PROGRAM-DATE-TIME` (RFC 8216). hls.js adds DATERANGE, ID3 (TS/audio) and emsg cues to a metadata TextTrack (`enableDateRangeMetadataCues`, `enableID3MetadataCues`, `enableEmsgMetadataCues`), and raises `FRAG_PARSING_METADATA`.

### 4. Broadcast-safe design

EBU R 95 v1.1 (June 2017), note 5: "The action safe area is 3.5% and the graphics safe area is 5%, at the top, bottom and lateral parts of the image." R 95 footnote 1 confirms that 3.5% of 1920 is 67 px. SMPTE ST 2046-1 defines Safe Action = 93% and Safe Title = 90% of width and height (NAB summary and Netflix help; ST 2046-1 itself not read). These are the same boxes. On 1920×1080 the graphics-safe box is x 96–1823, y 54–1025 (our arithmetic). Lower thirds and score bugs go inside it. A practical layout: score bug top-left at (96, 54); lower third bottom-left with its baseline about 54 px above the bottom edge; name tags anchored to tracked players, but clamped to the box.

### 5. OBS + obs-websocket as the demo studio

obs-websocket v5 has been bundled with OBS Studio since 28.0.0 and listens on port 4455. Requests use `{"op":6,"d":{"requestType","requestId","requestData"}}`. Useful requests are `SetInputSettings` (for example, change a browser source URL), `SetSceneItemEnabled`, `StartRecord` and `BroadcastCustomEvent`. The obs-browser plugin registers vendor `obs-browser` with request `emit_event {event_name, event_data}`, and every browser source receives `window` event `event_name` with `event.detail = event_data`. The browser source also gets events such as `obsSourceVisibleChanged`, and `window.obsstudio` control functions gated by permission level 0–5.

### 6. SCTE-35 in one paragraph

SCTE-35 inserts splice messages into the stream. `splice_insert` (simple out/in with duration) or `time_signal` + `segmentation_descriptor` (richer metadata, type IDs such as 0x30 = provider ad start) mark breaks. AWS MediaTailor writes them into HLS as `EXT-X-DATERANGE ... SCTE35-OUT=0xFC...` or as `EXT-X-CUE-OUT:Duration=30` / `EXT-X-CUE-IN`. For **23 Safe Break**, our "safe to break now" decision could be emitted as a DATERANGE with `CLASS="com.berbata.safebreak"` and optionally a real `SCTE35-OUT` blob. That would be a credible broadcast-native output, and almost nobody in the field will do it.

## So what for us

- **Stage: Render** (and the producer workflow for **F Graphics Desk**). This directly serves **A TwinCast**, **B Speed Trap** (name tags, speed bugs), **C One Number** (single persistent bug), **D Chalk Talk** (full-frame transparent layer), **23 Safe Break** (DATERANGE/SCTE-35) and **24 Big Screen**.
- **Recommended stack:**
  1. **One cue JSON → three carriers:** a live WebSocket (Web PubSub), a `.vtt` metadata track for replay/VOD, and optionally HLS DATERANGE. The carrier holds `{cue_id, tc_in, ttl_ms, …}`. Never put display logic in it.
  2. **Browser compositor:** a transparent 1920×1080 page over the `<video>`, scheduled by `requestVideoFrameCallback` mediaTime. State is derived purely from time ("which cues are active at t"), so seeking and scrubbing just work.
  3. **Templates use the CasparCG/SPX contract** (`update/play/stop/next`), so the same files load in OBS, SPX or CasparCG. Wrapping them as OGraf later is a bonus for judges.
  4. **Exports:** a headless render of the same page with virtual time and `omitBackground` → PNG frames → ProRes 4444 (master), key/fill pair (broadcast proof), VP9 alpha (web) and an H.264 burn-in (judging video). This gives "ffmpeg key/fill" in TwinCast a concrete, demonstrable output.
- Use **25 fps non-drop timecode** everywhere (simulator, renderer, cues) so `tc_in` maps exactly to frames.
- Keep all graphics inside the **5% graphics-safe box**. Add a debug toggle that draws the 3.5% and 5% guides. It costs little and signals broadcast literacy.

## Reuse: code & links

**Cue as WebVTT metadata (`cues.vtt`, one-line JSON, unique id):**
```
WEBVTT

c_0042
00:12:34.160 --> 00:12:40.160
{"cue_id":"c_0042","match_clock":"23:41","tc_in":"00:12:34:04","ttl_ms":6000,"layout":"lower_third","anchor":"bl","metric":"pass_difficulty","text":{"casual":"Rice threads it through three lines","analyst":"xPass 0.18, 3 lines broken"},"evidence":["ev_9812"],"source":"interpreter","truth_check":"pass"}
```

**HLS alternative (quoted strings cannot contain `"`, so reference the cue id):**
```
#EXT-X-PROGRAM-DATE-TIME:2026-10-20T15:00:00.000Z
#EXT-X-DATERANGE:ID="c_0042",CLASS="com.berbata.cue",START-DATE="2026-10-20T15:12:34.160Z",DURATION=6.0,X-CUE-ID="c_0042"
```

**Minimal compositor (show at `tc_in`, hide after `ttl_ms`):**
```html
<div id="stage" style="position:relative;width:1920px;height:1080px">
  <video id="v" src="match.mp4" controls style="position:absolute;inset:0;width:100%"></video>
  <div id="lt" class="lt" hidden><b id="ltName"></b> <span id="ltLine"></span></div>
</div>
<style>
  .lt{position:absolute;left:96px;bottom:54px;background:#111c;color:#fff;padding:16px 28px;
      font:600 40px system-ui;transition:opacity .25s}
  .lt[hidden]{display:block;opacity:0}
</style>
<script>
const FPS = 25, AUDIENCE = "casual";
const tcToSec = tc => { const [h,m,s,f] = tc.split(/[:;]/).map(Number); return h*3600+m*60+s+f/FPS; };
let cues = [];                                   // filled from fetch('/cues.json') or WebSocket
fetch("cues.json").then(r => r.json()).then(list => {
  cues = list.map(c => ({...c, t0: tcToSec(c.tc_in), t1: tcToSec(c.tc_in) + c.ttl_ms/1000}))
             .sort((a,b) => a.t0 - b.t0);
});
const $ = id => document.getElementById(id);
const v = $("v"), lt = $("lt"), ltName = $("ltName"), ltLine = $("ltLine");
let shown = null;
function render(t) {                              // pure function of media time -> seek-safe
  const c = cues.filter(c => c.layout === "lower_third" && t >= c.t0 && t < c.t1).at(-1) || null;
  if (c?.cue_id === shown) return;
  shown = c?.cue_id ?? null;
  if (c) { ltName.textContent = c.metric; ltLine.textContent = c.text[AUDIENCE]; lt.hidden = false; }
  else lt.hidden = true;
}
if ("requestVideoFrameCallback" in HTMLVideoElement.prototype) {
  const tick = (_, md) => { render(md.mediaTime); v.requestVideoFrameCallback(tick); };
  v.requestVideoFrameCallback(tick);
} else {
  (function loop(){ render(v.currentTime); requestAnimationFrame(loop); })();
}
v.addEventListener("seeked", () => render(v.currentTime)); // rVFC may not fire while paused
</script>
```
To read the `.vtt` instead: `<track kind="metadata" src="cues.vtt">`, then `track.mode="hidden"` and `track.oncuechange = () => [...track.activeCues].map(c => JSON.parse(c.text))`.

**CasparCG/SPX-compatible template skeleton (`lowerthird.html`):**
```html
<!doctype html><html><head><meta charset="utf-8">
<style>
  html,body{margin:0;width:1920px;height:1080px;background:transparent;overflow:hidden}
  #lt{position:absolute;left:96px;bottom:54px;opacity:0;transform:translateX(-40px);
      transition:all .3s ease;background:#0b1f3a;color:#fff;font:600 40px sans-serif;padding:16px 28px}
  #lt.in{opacity:1;transform:none}
</style></head><body>
<div id="lt"><div id="f0"></div><div id="f1" style="font-weight:400;font-size:28px"></div></div>
<script>
  let data = {}, outTimer = null;
  function parse(str) {                       // JSON (Caspar 2.1+/SPX) or legacy XML templateData
    try { return JSON.parse(str); } catch (_) {}
    const x = new DOMParser().parseFromString(str, "text/xml"), o = {};
    x.querySelectorAll("componentData").forEach(n =>
      o[n.getAttribute("id")] = n.querySelector("data")?.getAttribute("value") ?? "");
    return o;
  }
  function update(str) {
    data = Object.assign(data, parse(str));
    for (const k in data) { const el = document.getElementById(k); if (el) el.textContent = data[k]; }
  }
  function play() {
    document.getElementById("lt").classList.add("in");
    clearTimeout(outTimer);
    if (data.ttl_ms) outTimer = setTimeout(stop, Number(data.ttl_ms));  // self-timed cue
  }
  function stop()  { document.getElementById("lt").classList.remove("in"); }
  function next()  { /* step 2, e.g. swap casual -> analyst text */ }
  function remove(){ stop(); }
  // Optional: lets SPX import this file as a template
  window.SPXGCTemplateDefinition = { description:"Berbata lower third", playserver:"OVERLAY",
    playchannel:"1", playlayer:"5", webplayout:"5", out:"manual", dataformat:"json",
    DataFields:[{field:"f0",ftype:"textfield",title:"Headline",value:"Rice"},
                {field:"f1",ftype:"textfield",title:"Line",value:"Breaks three lines"}] };
</script></body></html>
```
CasparCG control (telnet/TCP 5250): `CG 1-20 ADD 1 "berbata/lowerthird" 1 "{\"f0\":\"Rice\",\"f1\":\"xPass 0.18\",\"ttl_ms\":6000}"`, then `CG 1-20 STOP 1`.

**OBS push (Python, `obsws-python` or a raw websocket, op 6):**
```json
{"op":6,"d":{"requestType":"CallVendorRequest","requestId":"c_0042",
 "requestData":{"vendorName":"obs-browser","requestType":"emit_event",
  "requestData":{"event_name":"berbata-cue","event_data":{"cue_id":"c_0042","tc_in":"00:12:34:04","ttl_ms":6000}}}}}
```
In the page: `window.addEventListener("berbata-cue", e => { update(JSON.stringify(e.detail)); play(); });`

**ffmpeg recipes (frames rendered with Puppeteer `omitBackground:true` at 25 fps):**
```bash
# 1. Alpha master: ProRes 4444 with 16-bit alpha
ffmpeg -framerate 25 -i frames/%06d.png -c:v prores_ks -profile:v 4444 -pix_fmt yuva444p10le -alpha_bits 16 gfx_4444.mov
# 2. Web alpha: VP9 WebM
ffmpeg -framerate 25 -i frames/%06d.png -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 0 -crf 30 gfx_alpha.webm
# 3. Lossless legacy alpha: QuickTime Animation
ffmpeg -framerate 25 -i frames/%06d.png -c:v qtrle -pix_fmt argb gfx_qtrle.mov
# 4. Key/fill pair for a hardware keyer
ffmpeg -i gfx_4444.mov -filter_complex "[0:v]split[f][a];[a]alphaextract[k]" \
  -map "[f]" -c:v prores_ks -profile:v hq -pix_fmt yuv422p10le fill.mov \
  -map "[k]" -c:v prores_ks -profile:v hq -pix_fmt yuv422p10le key.mov
# 5. Burn-in the whole graphics layer over the match video
ffmpeg -i match.mp4 -i gfx_4444.mov -filter_complex \
  "[0:v]setpts=PTS-STARTPTS[b];[1:v]setpts=PTS-STARTPTS[o];[b][o]overlay=0:0:eof_action=pass[v]" \
  -map "[v]" -map 0:a? -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy match_burned.mp4
# 6. Single-cue burn-in from a PNG, timed by the cue (tc_in 00:12:34:04 = 754.16 s, ttl 6 s)
ffmpeg -i match.mp4 -loop 1 -i lt_c_0042.png -filter_complex \
  "[0:v][1:v]overlay=x=96:y=H-h-54:shortest=1:enable='between(t,754.16,760.16)'" -c:a copy out.mp4
```
To read VP9 alpha back in ffmpeg, put `-c:v libvpx-vp9` **before** `-i gfx_alpha.webm`, because the native decoder drops alpha. This comes from community forums (unverified).

Repos: CasparCG server https://github.com/CasparCG/server · SPX-GC https://github.com/TuomoKu/SPX-GC (templates in `ASSETS/templates/softpix/`) · OGraf https://github.com/ebu/ograf (examples in `v1/examples`) · OGraf devtool https://github.com/SuperFlyTV/ograf-devtool · obs-websocket https://github.com/obsproject/obs-websocket · DistroAV (NDI for OBS, GPL-2.0) https://github.com/DistroAV/DistroAV

## Sources

- CasparCG server `html_cg_proxy.cpp` (CG → JS mapping) — https://github.com/CasparCG/server/blob/master/src/modules/html/producer/html_cg_proxy.cpp — accessed 20 Oct 2026
- CasparCG server `casparcg.config` (port 5250, keyer, key-only, NDI consumer) — https://github.com/CasparCG/server/blob/master/src/shell/casparcg.config — accessed 20 Oct 2026
- CasparCG AMCP protocol — https://casparcg.com/docs/wiki/protocols/amcp-protocol — accessed 20 Oct 2026
- CasparCG server configuration — https://casparcg.com/docs/wiki/server/configuration — accessed 20 Oct 2026
- CasparCG wiki (legacy): HTML Templates — https://github.com/CasparCG/help/wiki/Media:-HTML-Templates — accessed 20 Oct 2026
- SPX-GC README and `spx_interface.js` / `NAME_LEFT.html` — https://github.com/TuomoKu/SPX-GC — accessed 20 Oct 2026
- EBU OGraf site — https://ograf.ebu.io/ — accessed 20 Oct 2026
- OGraf specification v1 — https://github.com/ebu/ograf/blob/main/v1/specification/docs/Specification.md — accessed 20 Oct 2026
- LOOPIC — https://www.loopic.io/ — accessed 20 Oct 2026
- H2R Graphics — https://h2r.graphics/ — accessed 20 Oct 2026
- Singular.live pricing — https://www.singular.live/pricing — accessed 20 Oct 2026
- Vizrt Flowics rebrand press release — https://www.vizrt.com/press-center/flowics-rebrand/ — accessed 20 Oct 2026
- FFmpeg filters (overlay, alphaextract/alphamerge, timeline editing) — https://ffmpeg.org/ffmpeg-filters.html — accessed 20 Oct 2026
- FFmpeg codecs (prores_ks profiles, alpha_bits) — https://ffmpeg.org/ffmpeg-codecs.html — accessed 20 Oct 2026
- FFmpeg source: libvpxenc.c, qtrleenc.c, proresenc_kostya.c, vf_overlay.c — https://github.com/FFmpeg/FFmpeg/tree/master/libavcodec — accessed 20 Oct 2026
- VideoHelp forum, VP9 alpha decode tip (unverified) — https://forum.videohelp.com/showthread.php?p=2657473 — accessed 20 Oct 2026
- NDI SDK frame types (UYVA) — https://docs.ndi.video/docs/sdk/frame-types — accessed 20 Oct 2026
- NDI codecs and format matrix — https://docs.ndi.video/all/using-ndi/ndi-for-video/ndi-video-codecs-and-format-matrix — accessed 20 Oct 2026
- vMix NDI alpha channel support — https://img.vmix.com/help/NDIAlphaChannel.html — accessed 20 Oct 2026
- Puppeteer ScreenshotOptions (omitBackground) — https://pptr.dev/api/puppeteer.screenshotoptions — accessed 20 Oct 2026
- MDN requestVideoFrameCallback — https://developer.mozilla.org/en-US/docs/Web/API/HTMLVideoElement/requestVideoFrameCallback — accessed 20 Oct 2026
- MDN TextTrack.mode / cuechange — https://developer.mozilla.org/en-US/docs/Web/API/TextTrack/mode — accessed 20 Oct 2026
- W3C WebVTT (metadata cues) — https://www.w3.org/TR/webvtt1/ — accessed 20 Oct 2026
- RFC 8216 HTTP Live Streaming (EXT-X-DATERANGE) — https://datatracker.ietf.org/doc/html/rfc8216 — accessed 20 Oct 2026
- hls.js API docs (metadata cues) — https://github.com/video-dev/hls.js/blob/master/docs/API.md — accessed 20 Oct 2026
- EBU R 95 v1.1 Safe areas for 16:9 TV production (PDF) — https://tech.ebu.ch/docs/r/r095.pdf — accessed 20 Oct 2026
- NAB TV Tech Check on SMPTE ST 2046-1 — https://nab.org/xert/scitech/2010/TVTechCheck/TV031510.asp — accessed 20 Oct 2026
- Netflix: Title Safe and Safe Action best practices — https://backlothelp.netflix.com/hc/en-us/articles/4406208331923-Title-Safe-and-Safe-Action-Best-Practices — accessed 20 Oct 2026
- SMPTE timecode overview (drop-frame) — https://en.wikipedia.org/wiki/SMPTE_timecode — accessed 20 Oct 2026
- OBS browser source KB — https://obsproject.com/kb/browser-source — accessed 20 Oct 2026
- obs-browser README (obsstudio API, emit_event vendor) — https://github.com/obsproject/obs-browser — accessed 20 Oct 2026
- obs-websocket README and protocol.md — https://github.com/obsproject/obs-websocket — accessed 20 Oct 2026
- AWS MediaTailor: SCTE-35 messages for ad breaks — https://docs.aws.amazon.com/mediatailor/latest/ug/ca-scte-35-messages.html — accessed 20 Oct 2026
- Google Ad Manager SCTE-35 cue types — https://support.google.com/admanager/answer/13049027 — accessed 20 Oct 2026
