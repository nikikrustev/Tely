# Higgsfield prompts: two b-roll clips (draft, not generated yet)

Model: **Seedance 2.0** (not Fast or Mini), **720p**, **16:9**, **sound on**. Character: the saved Element `[@avatar]` in both clips.

> Round 1 (27 Oct) ran on **Seedance 2.0 Mini at 480p** (864×496). Mini is the smaller model. Run round 2 on full Seedance 2.0 at 720p, so we know whether a fault comes from the prompt or the model.

## Before you generate

1. **Make `[@avatar]` an Element from the granddad photo.** Uploading the photo as it is works. Higgsfield says a plain in-clip reference only keeps the face within one generation; saving it as an Element (or Soul ID) is what keeps the same man across the two clips. *Optional:* add a tight crop of his face as a second image. Runway's guide says that in a full-scene image the face is too small to anchor on, so a crop helps if his face drifts.
2. **Upload the app screenshot as a plain image reference for clip 1 only,** and replace `[@screen]` with the tag Higgsfield gives it.
3. **Don't use the granddad photo as a start frame.** It's 9:16 and these clips are 16:9. Use it only as the Element.
4. **The text matches the reference image on purpose.** Your first draft described a cream sweater, a green mug and an armchair, but the reference shows a navy jumper, a red-and-white scarf, a white mug, a sofa and an earbud. When the text and the reference disagree, the face and clothes drift. If you want the cream sweater, regenerate the reference instead of only changing the text.
5. **One audio caveat.** Higgsfield's help centre says the sound toggle doesn't change the cost, but Higgsfield's blog says audio adds 50–100%. Check the credit estimate before you click.

---

## Clip 1 · "Home", 10 s

```
References: [@avatar] is the man. [@screen] is used only for what the phone screen shows; it does not change the room, the lighting or the colours.

[@avatar] is the same man as in the reference: late 70s, short thin white hair, white stubble, a kind weathered face with deep smile lines. He wears a navy V-neck jumper over a pale blue collared shirt, a red-and-white striped knitted scarf, and small white wireless earbuds. A red-and-green tartan blanket lies over his knees. He is blind: his eyes stay gently closed, and his face is calm and listening. He moves slowly and finds things by touch.

Setting: a cosy British living room at dusk. He sits on a grey fabric sofa between two warm table lamps. Behind him, a large window shows blue evening light over a quiet street of red-brick houses. Photorealistic, 35mm film, warm tungsten lamplight against cool blue window light, soft grain, shallow depth of field.

Shot 1 (about 0–7 s, the longer shot): A medium-wide shot at seated eye level. The camera dollies in slowly and ends on a medium shot. He lifts a white mug of tea in his left hand, takes a small sip as steam rises, then lowers the mug onto his knee with a soft, contented smile. Then, slowly and by touch, he lifts the black smartphone from the blanket with his right hand and raises it to chest height. We hear quiet room tone, a mantel clock ticking slowly, a car passing softly outside, the gentle clink of the mug and a quiet sip.

Shot 2 (about 7–10 s, a short shot of about three seconds): Cut to an over-the-shoulder close-up from just above his right shoulder, looking down at the black smartphone he holds upright in his right hand at chest height. The screen faces him and the camera and fills the centre of the frame, upright and the right way round, matching [@screen] exactly: a black background, the cream "Tely" wordmark at the top left, a dark dashed panel with a microphone icon in the upper half, and a large rounded green button with a cream outline and a cream play triangle filling the lower half. This is how a blind person uses a phone screen reader, and it happens briskly, in this order. Tap one: his thumb taps the green button once and lifts off; the button gets a thin highlight outline. Straight away, a calm synthetic screen-reader voice from the phone speaker says the two words "Start button" one single time, then stays silent for the rest of the clip. Tap two, right after the voice: his thumb clearly presses the green button a second time to confirm, and we hear the second soft tap. The green glow brightens, he lifts his thumb off the glass, and a faint, distant stadium crowd fades in, as if heard through his earbuds. The camera is locked off. The clip ends one moment after the glow.

Audio: no music. Every sound is quiet and close, and the screen-reader voice is clear. Keep the frame free of subtitles, captions, logos and watermarks.
```

## Clip 3 · "Back home" end card, 8 s

Why 8 s: about 1.5 s on him at home, about 1.5 s for the fast pull-back, then about 5 s of end card (about 1 s for the drop and bounce, about 2.5 s for the line and the tagline, and a short hold). Anything longer drags, because a professional brand sting is usually 5–8 s. Anything shorter rushes the voice. The full video has a hard stop at 1:55 (`video/script.md`), so this clip has to take its 8 s from somewhere else in the edit, for example by running straight into the URL end card at 1:46.

**New Element: the logo**
- Upload `assets/brand/tely-mark-512.png`. It's the clean master, so use it rather than a screenshot.
- Name: `TelyLogo`. Category: **Prop** (or Object or Product). Not Character, because there's no face to lock.
- Description:
  ```
  Tely app icon. A flat 2D graphic: a rounded-square near-black tile with cream headphones whose band arcs over the top, and a cream football with near-black pentagon patches sitting between the two ear cups. Two colours only, cream and near-black. No text, no 3D, no shine.
  ```

**Room reference (this clip only).** Pause the final clip 1 on a wide frame of the room, about 1 s in, and screenshot only the video (Win+Shift+S). Upload it as a plain image reference. It becomes `[@room]` below and keeps the home identical to clip 1.

Settings: Seedance 2.0 Mini, 720p, 16:9, **8 s**, sound on. References: `@Grandpa`, `@TelyEndCard`, `[@room]`.

**End card as an Element (what we use, since Higgsfield has no end-frame slot for us).**
- Upload `video/endframe/tely_endframe_1920x1080.png` as a new Element.
- Name: `TelyEndCard`. Category: **Prop** (or Object or Product).
- Description:
  ```
  The Tely end card, a flat 2D title card: a dark grey background, the Tely app icon (cream headphones over a cream football on a near-black rounded-square tile) in the upper middle, and below it one line of cream serif text reading exactly "Tely - teleport to the stands". Flat graphic, no 3D, no shine, no other text.
  ```
- In clip 3, use `@Grandpa`, `@TelyEndCard` and the room screenshot. **Drop `@TelyLogo`**, because the end card already contains the logo, and fewer references keeps the model focused (Runway).

**End frame slot (if you ever find one).** Upload `video/endframe/tely_endframe_1920x1080.png` in the **end frame / last frame** slot, not as a reference. It's the exact final image: the real logo over "Tely - teleport to the stands" in real Fraunces 800, rendered from `video/endframe/endframe.html`. Mini can't spell the tagline, so we give it the finished frame to land on. The background (`#111111`) and the darker tile (`#050505`) match what the model drew in earlier runs, so the hand-over is seamless.
- **If the end-frame slot greys out the Elements:** use first-and-last-frame mode instead. Put the room screenshot (with him on the sofa) in the **start frame** slot and this PNG in the **end frame** slot, and remove the "References:" line from the prompt. The start frame then keeps both him and the room exact.

```
References: @Grandpa is the man. [@room] is his living room; the room must match it exactly. @TelyEndCard is the finished end card: the icon and the title must look exactly like it, flat 2D, never redrawn, rotated or turned 3D, and the title copied letter for letter from it.

@Grandpa is the same man as in the reference: late 70s, short thin white hair, white stubble, a kind weathered face with deep smile lines. He wears a navy V-neck jumper over a pale blue collared shirt, a red-and-white striped knitted scarf, and small white wireless earbuds. A red-and-green tartan blanket lies over his knees. He is blind: his eyes stay gently closed.

Shot 1 (about 0–3 s): The same cosy British living room at dusk as [@room], warm lamplight against cool blue window light, photorealistic, 35mm film, soft grain. He sits on the grey sofa, the black phone glowing green in his right hand, a small blissful smile, as if he can still hear the stadium. A medium shot holds still for a moment, then the camera pulls back fast in one smooth dolly out: the room shrinks into the distance, and the lamps become small points of warm light until everything falls away into pure black. We hear quiet room tone and, faintly from his earbuds, a distant stadium roar, then a deep rising whoosh as the camera pulls away.

Shot 2 (about 3–8 s): A clean premium motion-graphics end card on the dark grey background of @TelyEndCard. The icon from @TelyEndCard drops in from above the top of the frame, lands in its place in the upper middle and bounces twice, each bounce smaller, then settles perfectly still. We hear one deep cinematic boom on the first landing and a softer thud on the second. Then a deep, warm, resonant male voice-over, slow and confident, says: "Telly: teleport to the stands." As he speaks, the title from @TelyEndCard fades in below the icon, copied exactly. The clip finishes looking exactly like @TelyEndCard: the icon on its near-black rounded-square tile, with the title underneath, held perfectly still for the last second as the distant stadium roar fades out underneath.

Audio: no music. The voice is deep, clear and above everything else. Keep the frame free of subtitles, captions, watermarks, and any text or logo other than what @TelyEndCard shows.
```

Notes:
- The voice line says **"Telly"** so the name is pronounced right (D26). The on-screen title is exactly **"Tely - teleport to the stands"**, with a plain hyphen.
- **Run 4 (user's screenshot, Mini)** gave "Telly - telesport to the stands" in a sans-serif. That's four misspellings in four runs, so the prompt now hands Mini the finished end frame and never asks it to spell the title. Check the middle of the title fade: the half-faded letters can still wobble before they settle on the end frame. If they do, cut in the edit to the PNG itself for the last 2 s.
- **Run 2 (`165322`, Mini at 720p)** gave "Telly - trelsport to the stands" in a sans-serif, and the icon lost its tile. Spelling the words out letter by letter made it worse, so that is gone. The title is now quoted once, in plain words, and fades in rather than writing out. Our plan only has Mini, and text is where the smaller model is weakest. Give it two or three more rolls at most, then switch to the route below.
- **Run 3 (`170248`, Mini at 720p)** gave "Telli - teosport to the stands". All three runs garbled "teleport" (Telesport, trelsport, teosport), and the spoken "Telly" bled into the name. The font and size description is now gone, and the title fades in whole instead of word by word, so the prompt makes one simple request.
- **Guaranteed-correct route (recommended, given the deadline):** in the prompt, replace the sentence that starts "As he speaks, the title…" with *"The screen shows no text at all, only the icon."* and change the last line to *"Keep the frame free of any text."* Then add "Tely - teleport to the stands" in the edit, in Fraunces 800, `#f2ead8`, with a word-by-word fade timed to the voice. You can also do that on top of a run whose voice you like: the background is flat `#0d0d0d`, so a box in that colour hides the wrong text.
- **Run 1 (`163841`, Mini at 720p)** had a great voice and logo, but the text read "Telesport to the stands" in a regular-weight serif. The model blended the spoken "Telly" into "Teleport". The prompt now puts the text on its own line, says the spelling differs from the voice, spells out both tricky words letter by letter, and asks for word-by-word instead of letter-by-letter (fewer frames of half-written text to get wrong).
- **Keep the voice from run 1 if a rerun loses it.** The end-card background is flat `#0d0d0d` (sampled at 7.9 s), so in the edit you can cover the wrong tagline with a `#0d0d0d` box and put the right text on top in Fraunces 800. It will match seamlessly.
- **Seedance can't be told to use a font.** "Like Fraunces ExtraBold" only describes the look, and text can come out garbled or in the wrong typeface. If the tagline isn't clean, remove the sentence about the words writing themselves out, add "no text on screen" to the last line, and put the tagline on in the edit in real Fraunces 800.

## Clip 2 · "The goal he heard", 15 s

```
[@avatar] is the same man as in the reference: late 70s, short thin white hair, white stubble, a kind weathered face with deep smile lines. He wears a navy V-neck jumper over a pale blue collared shirt, a red-and-white striped knitted scarf, and small white wireless earbuds. A red-and-green tartan blanket lies over his knees, and he holds a white mug of tea in his left hand. He is blind: his eyes stay closed, and he listens with his head tilted slightly up.

Beside him: on his left, a big, friendly bearded man in his 40s in a dark jacket and a plain red scarf. On his right, a young woman in her 20s in a cream woolly hat and a red-and-white striped scarf.

Setting: a packed, historic English football stadium at night. The steep stands are full of fans in plain red shirts and scarves, with floodlights on tall towers and a bright green pitch below. Every shirt, scarf and kit is plain fabric with no badge, crest, number or sponsor, and the pitchside advertising boards and the scoreboard are blank and unlit. Breath vapour shows in the cold air. Photorealistic documentary look, 35mm film, cool blue night air against warm skin tones, soft grain.

Shot 1 (about 0–5 s): A medium shot from his right at seated eye level. The camera pushes in slowly toward his face. He sits in the stand with the blanket and the mug, out of place but completely at home, smiling gently as he listens. Around him, fans lean forward, hands on their heads, scarves held up. We hear a huge live crowd clapping in rhythm, a tense murmur rising, and a warm, excited British male football commentator, off screen and heard as if through his earbuds, says: "Red on the ball, edge of the box... this could be it..."

Shot 2 (about 5–8 s): Hard cut to a dreamy side-on shot from pitchside at grass level, level with the edge of the penalty area, with soft bloom on the floodlights. The goal is on the right of the frame and the attacker on the left. The shot opens on the kick: a player in a plain red kit drives one white football low and hard with his right foot, and at that exact instant, as boot meets ball, we hear the deep thud of the strike and the commentator shouts: "He shoots!" After that the commentator is silent until the next shot. In slow motion, the camera pans right to follow that same ball as it skids and rolls along the grass the whole way, never leaving the ground, past a goalkeeper in plain lime green diving the wrong way, and into the bottom corner of the net. The bottom of the net ripples. There is only ever one ball, and it stays in view from the kick until it rests in the net. As the ball rolls, the crowd draws one collective gasp, and the net rustles softly as the ball hits it.

Shot 3 (about 8–15 s): Hard cut back to him in a medium close-up. The camera orbits slowly from his right to the front. The whole stand erupts in an explosive roar, arms thrown up and scarves twirling, and the commentator shouts: "GOAL! Oh, what a strike!" He breaks into a huge open-mouthed laugh, head tilted back, eyes still closed. The bearded man grabs his shoulder, shakes him happily and shouts, "Get in!" The young woman throws her arms around him, and he pats her hand, laughing. A little tea splashes from the mug. End on a close-up of his joyful face, a tear at the corner of his closed eye. We hear the roar, hands slapping his shoulder and his warm, loud laugh above the crowd.

Audio: no music and no stadium announcer. The commentator is off screen, and nobody on screen speaks his lines. The stadium atmosphere is loud and full from the very first frame to the last, as if recorded from inside the stand: constant crowd noise, clapping and chanting under everything, and even in the slow-motion shot the crowd stays clearly present. The commentator's lines and the old man's laugh sit just above the crowd. Keep the frame free of subtitles, captions, logos, club crests, sponsor names and watermarks.
```

---

## Round 2 fixes (after the first test run)

| Problem seen in round 1 | Fix in the prompt |
|---|---|
| Clip 1: the app screen was flipped and too small to read. The phone lay flat on his lap, filmed from in front of him | Over-the-shoulder shot of the phone held upright, so the screen is the right way round for both him and the camera, and it fills the centre of the frame. Full 2.0 at 720p should sharpen it. If small text is still garbled, corner-pin the real screenshot in the edit |
| Clip 1: he tapped the screen many times | "Exactly two times, one quick double-tap", then he lifts his thumb and keeps his hand still, and the glow brightens once. Without an end state, the model keeps the finger moving |
| Clip 2: two balls, one over the bar and one in the net (frames 6.6–7.3 s) | "One white football", the camera follows that same ball from the kick to the net, and the shot is simplified to a low finish in the bottom corner. Fewer defenders means fewer objects to invent |
| Clip 2: the goal was filmed from behind the net, with no visible scorer | Shot from the stand behind the attacker, with the red player in the foreground striking the ball, so it's clear the red team scores |
| Clip 2: badges | Every shirt, scarf and kit is plain, with no badge, crest, number or sponsor, and the advertising boards are blank and unlit (round 1 had a red lit board behind the crowd) |
| Clip 2: no commentator | A short commentator line in each shot, off screen, as if heard through his earbuds. Lines are kept under 10 words, because long lines drift (Cutout) |

## Round 3 fixes (after the second test run, still on Mini at 480p)

| Problem seen in round 2 | Fix in the prompt |
|---|---|
| Clip 1: the tap sequence must follow how a screen reader really works | One light tap selects the button, the phone says "Start. Button.", he pauses to listen, then confirms with a double-tap. That's how VoiceOver (iPhone) and TalkBack (Android) work. The over-the-shoulder framing worked: the screen is now upright |
| Clip 2: the ball rose over the bar, then ended in the net. The model read "the stand behind the attacker" as the stand behind the goal, so the shot came toward the camera | A side-on pitchside camera at grass level, with the goal on the right and the attacker on the left, and the camera panning right with the ball. The shot is driven low, skidding and rolling along the grass "the whole way, never leaving the ground". Seen side-on, a ground shot can't look like it went over the bar |
| Clip 2: a lit red board above the far stand (6.4 s) | The scoreboard is now blank and unlit too |

## Round 4 fixes (after the third test run, still on Mini at 480p)

| Problem seen in round 3 | Fix in the prompt |
|---|---|
| Clip 1: the taps must be tap, voice, tap: exactly two touches, with "Start. Button." between them | The shot says "exactly two times", then numbers them: tap one, the voice, tap two. No double-tap. (Real VoiceOver confirms with a double-tap; this is a simplification for the camera.) |
| Clip 2: "He shoots" came when the ball was already in the net (the kick is at about 4.6–5.0 s, the ball reaches the net at about 7 s). The line sat at the end of the shot's description, so the model played it there | The shot now opens on the kick, and "He shoots!" sits in the same sentence as the boot hitting the ball, "at that exact instant". The commentator is told to stay silent for the rest of the shot. The ground shot worked: the ball now rolls into the net |
| Clip 2: the stadium was too quiet, about -38 dB in the first second | The audio line now says the atmosphere is loud and full from the very first frame to the last, and stays present in slow motion. If it's still low, raise it in the edit; the Seedance audio comes as one mixed track, so this boosts everything together |

Clip 2 was done after this round (27 Oct).

## Round 5 fixes (clip 1 only, after the 720p run)

The 480p run (`155525`) was right; the 720p run (`160204`) wasn't. Each run is a fresh random take, so even an unchanged prompt can fail or succeed.

| Problem seen in the 720p run | Fix in the prompt |
|---|---|
| The cut to the phone came at about 4 s instead of 6 s, which left about 6 s on the phone. The model filled the gap with a second "button" (voice bursts at 5.5 s and 6.2 s) and no second tap | Shot 1 now has one more action, lifting the phone to chest height, and is marked "about 0–7 s, the longer shot". Shot 2 is "about 7–10 s, a short shot of about three seconds", and the clip ends one moment after the glow |
| The voice said "Start button, button" | The line is now one phrase, "Start button", said "one single time", then the voice "stays silent for the rest of the clip". The old "Start. Button." punctuation read as two separate lines |
| No second tap | Tap two now comes "right after the voice", he "clearly presses" a second time, and we hear the second tap. A visible action plus a sound is harder for the model to skip |

> Seedance's commentator is a generic AI voice, not Tely's. If you'd rather the judges hear the real product, mute these lines in the edit and lay the same words from our Azure commentator voice over the clip.

## What changed and why (round 1)

| Change | Why (source) |
|---|---|
| Sound is written into each shot, next to the action that makes it | Audio is generated in the same pass, so put each sound in the sentence with its action (Runway). Without that the model guesses, and the timing may not be frame-accurate (Cutout) |
| "No music" stated explicitly, and every sound named | When the audio is left blank, the model adds a random score (heyuan110) |
| At most 2–3 sound layers per shot | More than three layers turns the mix muddy (Cutout) |
| The "Avoid" lists became one closing line, and scenes are described positively ("a single white ball", "eyes closed") | Seedance has no negative-prompt field. Close with constraints and say what should appear (Runway) |
| Shot timings say "about" | Precise timing support is unstable (Runway). Timestamps still help sound effects land (Cutout) |
| One camera move per shot | Stacking moves causes jitter (Runway, heyuan110) |
| Shot 2 of clip 2 is in slow motion | Fast motion is where warping appears (Runway) |
| Eyes closed instead of "open but unfocused" | Matches the reference and removes a gaze instruction the model often breaks. If you prefer open eyes, swap in: *"his eyes are open but unfocused, resting on a point above and beyond the camera."* |
| The woman hugs him instead of wrapping a scarf around him | In the reference he already wears the red-and-white scarf |
| The phone speaks "Start. Button." (clip 1, shot 2) | That's what a screen reader says on our real button (`web/index.html`, `#start`). His face is off screen in that shot, so no lip sync is needed. Real dialogue in quotes syncs best when the lines are short (Cutout) |
| Clip 1 ends with a faint crowd fading in | It bridges sound into clip 2 |
| The real app screen comes from the screenshot (`[@screen]`), with its role stated in the first line | If you don't state each reference's job, the model borrows its colours and layout for the whole scene (Runway). Small text such as "Works once the match starts" may still come out garbled. If it does, replace the screen in the edit; the screen is flat and filmed straight on, so that's a simple corner-pin |
| Shot 2 tilts down from his face to the phone instead of hard-cutting | You asked for the camera to move to the phone. A tilt is one camera move, so it stays within the one-move-per-shot rule |

## Iterate cheaply

- Change one thing per run (Higgsfield).
- Watch the whole clip; quality problems often appear around 5–8 s (Higgsfield).
- If a clip ignores the end of the prompt, trim before you add. Adherence fades toward the end of a prompt, and the non-negotiables are already front-loaded (heyuan110).

## Sources (fetched 27 Oct 2026)

- Higgsfield help centre, Seedance: https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-use-seedance
- Higgsfield blog, generating with Seedance 2.0: https://higgsfield.ai/blog/generating-with-seedance-2-0
- Runway, Seedance 2.0 prompt guide: https://runway.com/resources/seedance-2-0-prompt-guide
- Cutout.pro, Seedance 2.0 audio guide: https://www.cutout.pro/learn/blog-seedance-2-0-audio-guide/
- heyuan110, Seedance 2.0 prompt guide and failure modes: https://www.heyuan110.com/posts/ai/2026-07-11-seedance-2-prompt-guide/
