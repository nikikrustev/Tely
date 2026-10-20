# 35 — Multi-language storytelling done right: glossaries, locked placeholders, number/date formats, RTL and quality checks

_Accessed/compiled: 20 Oct 2026 · Priority area: Personalise (language) → Render (overlay layout) · Builds on 03 §6, 22 §6, 27, 28_

## TL;DR

- **Translate templates, not cues.** Our cue text comes from a finite set of templates with slots (doc 22), so each template is translated once per language before the match. Do it with Translator, a glossary, back-translation and a QE score, then have a person review it and cache it. At runtime we only fill slots with locale-formatted numbers and names, so no MT runs at runtime and adds no latency. Runtime MT is only for LLM-polished free text and Q&A, and placeholders stay locked with `notranslate`.
- **Demo EN + BG + ES + AR.** Bulgarian is our home language. Spanish and Arabic are two of the four languages premierleague.com offers (EN, Español, Arabic, Thai; doc 28). Arabic gives us the RTL case.
- **Translator's term-forcing tools are weakest exactly for Bulgarian and Arabic.**
  - Adaptive custom translation (AdaptCT) is listed only for en, fr, fr-ca, de, it and es. This corrects doc 03, which implied it works for every language.
  - Neural (inflecting) phrase dictionary covers pl, es, de and others, but **not bg or ar**.
  - For BG/AR we only have the dynamic dictionary and Custom Translator phrase dictionaries. Both are exact, case-sensitive find-and-replace, and Microsoft says to use them only for compound nouns.
  - So for BG we enforce football terms when we author templates, then check them automatically with a lemma/stem match. We don't force them at runtime.
- **Let CLDR/ICU do numbers and plurals, but know the gaps.** Verified on Node 24 (ICU 78.2, CLDR 48) and Babel 2.17.0:
  - Bulgarian has **no ordinal categories**, so "3-ти" needs our own suffix function.
  - Arabic has six cardinal plural forms.
  - `ar` defaults to Latin digits, while `ar-EG`/`ar-SA` give Arabic-Indic digits in JS. Babel never converts digits.
- **For QE, CometKiwi works but its licence is CC BY-NC-SA 4.0 and it is gated.** Use it only as an offline dev-time check, and keep it out of the shipped repo/pipeline. The hackathon grants Microsoft/PL a perpetual licence to the submission (doc 12). MetricX-24 (Apache-2.0, QE mode) is the permissive alternative.

## Findings

### 1. Which languages, and why

| Lang | Why | Translator support (language table) | Gotchas |
|---|---|---|---|
| **bg** | Our language. We can review it ourselves | Text, Custom Translator, dictionary, transliteration Cyrl↔Latn, **LLM translation**. No AdaptCT, no neural dictionary | No CLDR ordinals; definite article (вратар → вратарят/вратаря) breaks exact-match glossaries; CLDR short unit is Latin "km/h" (a native reviewer may prefer "км/ч") |
| **es** | On the PL site; LLM + **AdaptCT** + neural dictionary all supported | Full | `many` plural category for millions; "62 %" has a space |
| **ar** | On the PL site; the RTL test case | Text, Custom Translator, dictionary, LLM, transliteration Arab↔Latn. No AdaptCT/neural dictionary | Six cardinal plural forms; digit choice by region; bidi with Latin names and numbers |

Do not quote PL audience sizes per language. Doc 28 found no official count of commentary languages. The hackathon also requires all submission materials to be **in English** (doc 12), so the video narration stays English and the overlays show the other languages.

### 2. Azure Translator: what to use for what

- **Text API `2026-06-06` (GA, breaking vs v3).**
  - The request shape is `{"inputs":[{"text","language","textType","targets":[{"language","deploymentName",...}]}]}` and the response is `value[]`.
  - `deploymentName` defaults to `general` (NMT). It can name a GPT-5.1 deployment (which needs a Foundry resource) or a Custom Translator category ID.
  - LLM-only controls are `tone` (formal/informal/neutral), `gender`, `adaptiveDatasetId` and `referenceTextPairs`.
  - `allowFallback` defaults to true, which silently drops back to NMT. **Set it to false in tests** so you see which engine actually ran.
  - Limits: NMT takes 1,000 elements × 50,000 chars; LLM takes 50 × 5,000.
  - LLM translation is unavailable behind a private endpoint, and it is billed by tokens at Azure OpenAI rates, not per character.
- **Locking text.** `<span class="notranslate">` or `translate="no"` works **only with `textType=html`**. Doc 22's `protect()`/`unprotect()` already wraps `[[P0]]`/`[[N0]]` this way.
- **Dynamic dictionary.**
  - Syntax: `<mstrans:dictionary translation="…">phrase</mstrans:dictionary>`.
  - One side must be English, and `language` (source) must be set; autodetect is not allowed.
  - Microsoft calls it "safe only for compound nouns like proper names and product names".
  - **Unverified:** whether `notranslate` and the dynamic dictionary apply when `deploymentName` is an LLM. The 2026-06-06 docs don't say. Smoke-test both engines with `allowFallback:false`.
- **Custom Translator dictionaries.**
  - **Phrase dictionaries** are case- and punctuation-sensitive. **Sentence dictionaries** are case-insensitive, need a whole-sentence match, and ignore final punctuation.
  - Duplicate source lines resolve to the last entry. Avoid number-only entries and entries of 2-3 letters (so no "xG").
  - Dictionary-only training needs no minimum sentence count. The resulting model is called with `deploymentName=<categoryID>`.
  - Custom model hosting is a flat monthly fee per model per region. The pricing page showed placeholders, not the amount, so it is not worth paying for in a hackathon.
- **Neural phrase dictionary** inflects terms, but only for en↔{zh, fr, de, it, ja, ko, pl, ru, es, sv}. It needs Custom Translator retraining.
- **AdaptCT.** Upload 5-10,000 pre-aligned pairs (≤250 chars each, TSV/TMX) and the index is ready in minutes. At request time it uses few-shot retrieval, or you pass up to 5 `referenceTextPairs` inline. Language column: **en, fr, fr-ca, de, it, es only**.
- **Document translation.**
  - Batch mode is async through Blob storage. Sync mode takes a single file and needs no storage.
  - It accepts **XLIFF/TSV/CSV/HTML** documents plus a **glossary** in TSV/CSV/XLF.
  - This is the easiest way to translate our whole template bundle offline: export it as XLIFF, add `glossary.tsv`, and translate one file per language.
- **Transliterate.**
  - `POST /transliterate?api-version=2026-06-06&language=bg&fromScript=Latn&toScript=Cyrl`, with at most 10 elements, 1,000 chars each and 5,000 in total.
  - bg Cyrl↔Latn and ar Arab↔Latn are both bidirectional.
  - **Unverified:** it applies the target language's script rules to the letters, not English pronunciation, so "Rowe" may not become the "Роу" a Bulgarian sports desk would write. Test it, and keep a reviewed name table.
- **Cost.** F0 gives "2 million characters … free per month". S1 NMT is $10 per 1M chars (doc 03). Our template bundle is a few thousand characters per language.

### 3. Glossary: 40 core terms EN → BG

We write all terms in their base (lemma) form. **(?)** marks a term one of us should confirm against the BFS translation of the IFAB Laws (2021/22 Bulgarian edition on theifab.com) or Bulgarian TV usage.

| EN | BG | EN | BG |
|---|---|---|---|
| goal | гол | own goal | автогол |
| shot | удар | shot on target | точен удар / удар във вратата |
| header | удар с глава | save | спасяване |
| pass | пас (подаване) | pass accuracy | точност на пасовете |
| key pass | ключов пас | assist | асистенция |
| cross | центриране | through ball | пас в дълбочина **(?)** |
| dribble | дрибъл | tackle | отнемане / шпагат (sliding) **(?)** |
| interception | пресичане | clearance | изчистване |
| goalkeeper | вратар | defender | защитник |
| centre-back | централен защитник | full-back | краен защитник |
| midfielder | полузащитник (халф) | winger | крило |
| striker / forward | нападател | referee | съдия (рефер) |
| offside | засада | penalty (kick) | дузпа |
| penalty area | наказателно поле | free kick | свободен удар (пряк / непряк) |
| corner kick | ъглов удар (корнер) | throw-in | тъч / вкарване от тъч **(?)** |
| foul | нарушение (фал) | yellow / red card | жълт / червен картон |
| VAR | VAR / ВАР **(?)** | possession | притежание на топката (владение) |
| pressing | пресиране (преса) **(?)** | counter-attack | контраатака |
| sprint | спринт | top speed | максимална скорост |
| distance covered | изминато разстояние **(?)** | expected goals (xG) | очаквани голове (xG) **(?)** |
| first half / half-time | първо полувреме / почивка | added time | добавено време |
| clean sheet | суха мрежа | hat-trick | хеттрик |
| post / crossbar | греда / напречна греда | high defensive line | висока защитна линия **(?)** |

**Method for other languages (es, ar, pl …).**

1. Seed each term from the official IFAB Laws translation for that language. The IFAB publishes EN/FR/DE/ES itself, national FAs publish the others, and an Arabic 2026/27 PDF is on theifab.com. For Spanish/French/Portuguese, also use Canada's Translation Bureau soccer glossary (931 concepts).
2. Fill the gaps with Translator's Dictionary Lookup and an LLM suggestion.
3. A native reviewer signs off on each term.
4. Store the result as `glossary/<lang>.tsv` with the columns `en, target_lemma, pos, gender, status`.

The `gender` column feeds ICU `select` (for example спринт is masculine, атака feminine; انطلاقة is feminine).

**Enforcement, by language.**

- **es:** use AdaptCT `referenceTextPairs` built from glossary example sentences, or the neural dictionary.
- **bg/ar:**
  1. Put glossary terms into templates when authoring them.
  2. Use the dynamic dictionary only for compound nouns ("clean sheet" → "суха мрежа", feature names).
  3. Run a **term-adherence check** after any MT: if the source contains "goalkeeper", the target must contain a word starting with the stem "вратар". The stem match lets inflected forms pass.

### 4. Names, numbers, units, clock, ordinals and plurals

- **Names.** The rules forbid real player names (doc 12), so all names are synthetic. Generate a name table offline: Latin spelling, then transliteration plus a human fix, giving `name_bg` and `name_ar`. Store it in seed data. Bulgarian and Arabic sports media normally write foreign names in their own script (general practice, unverified against a style guide). Keep Latin as a per-viewer option. In Arabic overlays, wrap any Latin name in `<bdi>`.
- **Numbers** (all values below verified by running Node 24 / CLDR 48):

  | Input | Output |
  |---|---|
  | 34.2 km/h in `en` / `bg` / `es` / `pl` / `ar` / `ar-EG` | `34.2 km/h`, `34,2 km/h`, `34,2 km/h`, `34,2 km/godz.`, `34.2 كم/س`, `٣٤٫٢ كم/س` |
  | 1234567.89 in `bg` | `1 234 567,89`, with NBSP as the group separator. **Never `str.replace`** (it replaces doc 22's `fmt_num`) |

- **Arabic digits.** CLDR 48 `ar` and `ar-AE` use Latin digits; `ar-EG` and `ar-SA` use Arabic-Indic. Pick `ar` (Latin) for the demo so numbers match the video's tracking graphics. Ask a reviewer before choosing otherwise.
- **Babel** formats separators but **does not convert digits**: `format_decimal(34.2, locale="ar_EG", numbering_system="arab")` returns `34٫2`. So do all number formatting in one place, the overlay JS.
- **Units.** `Intl.NumberFormat` accepts `kilometer-per-hour` and `mile-per-hour` (sanctioned units). In ICU message skeletons, intl-messageformat 10.7.16 rejects `::unit/kilometer-per-hour` and accepts `::measure-unit/speed-kilometer-per-hour` (tested). Store speeds in m/s and convert at render time (1 mph = 1.609344 km/h). Default to km/h and offer mph as a viewer preference.
- **Clock.** Keep `67′` / `45+2′` as a locked placeholder with U+2032 prime. An ASCII `'` is ICU's quote character. Isolate it as LTR inside RTL text. `Intl.RelativeTimeFormat` handles recap phrasing: `bg` "преди 2 минути", `ar` "قبل دقيقتين" (dual form, done for us).
- **Plurals and ordinals** (CLDR 48 categories):

  | Locale | Cardinal | Ordinal |
  |---|---|---|
  | en | one, other | one, two, few, other |
  | bg | one, other | **other only** |
  | es | one, many, other | other |
  | pl | one, few, many, other | other |
  | ar | zero, one, two, few, many, other | other |

  - The Bulgarian count form is handled for us by `other`: "3 спринта", not "спринтове".
  - Follow ICU's guidance: whole sentences per message, `select` outside, `plural` inside, no string concatenation.

### 5. Quality checks

1. **Automatic, every string:**
   - Placeholders survive (doc 22 check).
   - Digits and units are unchanged.
   - Glossary stems are present.
   - Length is within budget (see §6).
   - Script check: Cyrillic for bg, Arabic for ar.
   - No source-language leftovers.
2. **QE score per template × language.**
   - **CometKiwi** `Unbabel/wmt22-cometkiwi-da`: reference-free, outputs 0-1, InfoXLM-large backbone, covers bg/ar/es. It is CC BY-NC-SA 4.0 and gated (you must log in and accept), and runs on CPU with `gpus=0`.
   - **XCOMET-XL** (3.5B) adds error spans, but its examples need a reference, and it is also NC.
   - **MetricX-24 hybrid** (Apache-2.0) has a QE mode with `--qe` and an empty reference; scores run 0-25, lower is better.
   - No official thresholds exist, so rank the strings and send the bottom 10-20% to review. QE on 5-10-word overlay strings is noisier than on sentences (unverified, but expected).
3. **Back-translation spot check.** Translate bg/ar → en with a *different* engine (an LLM deployment if the forward pass used NMT) and compare meaning and numbers by eye. This catches meaning flips ("over 34" becoming "about 34"). It does not catch fluency problems.
4. **Human review checklist, per language:**
   - Term matches the glossary.
   - Gender and number agreement (3-ти спринт / 3-та атака; Arabic feminine ordinal with انطلاقة).
   - Register fits the audience (casual vs analyst; tone=informal for casual if using the LLM).
   - Name is in the right script.
   - Number format and digits are correct.
   - Units are correct.
   - It fits the box with no truncation.
   - RTL: word order, punctuation and numbers read correctly.
   - No accidental idiom or offence.
5. **Cache.** Key = `sha256(template_id, template_version, src_skeleton, lang, engine, glossary_version)` → `{text, qe, reviewed_by, ts}`. Keep it in Cosmos DB, or a JSON file committed with the repo. A glossary or template change invalidates only the affected keys.

### 6. Text expansion and RTL overlays

- **Expansion (W3C, from IBM guidelines):**

  | English source length | Typical translated length |
  |---|---|
  | up to 10 chars | 200-300% |
  | 11-20 chars | 180-200% |
  | 21-30 chars | 160-180% |
  | 31-50 chars | 140-160% |
  | over 70 chars | 130% |

  Name tags and stat chips fall in the worst band. Hold a `short` variant per template, measure the rendered width, and fall back automatically. Avoid fixed-width boxes and English-only abbreviations.
- **RTL rules:**
  - Set `dir="rtl" lang="ar"` explicitly on the overlay root, because we know the cue language. `lang` alone does not set the direction.
  - Use `dir="auto"` / `<bdi>` only for embedded data whose direction we don't know (names, user Q&A). `dir="auto"` goes by the first strong character, so "Rowe سجّل" would come out LTR.
  - Lay out the inside of each graphic with logical properties (`inset-inline-start`, `padding-inline`, `border-inline-start`, `text-align:start`) so lower-thirds, chips and arrows mirror on their own.
  - **Don't mirror** anything anchored to video coordinates (name tag position over a tracked player, pitch telestration, ball trails). Those use physical `left/top` from the tracker.
  - Fonts: Noto Sans plus Noto Sans Arabic. No `letter-spacing` or faux-italic on Arabic.

## So what for us

**Stages:** Personalise (language axis of the cue JSON) and Render (layout and fit). It helps every idea that puts text on screen: **B Speed Trap** (short name tags are the worst case for expansion), **F Graphics Desk** (the producer previews all languages before the take), **A TwinCast**, **10 Story Time** and **12 Jargon Buster** (glossary reuse).

1. Add `lang` and `dir` to the cue's `text` map: `text: {casual: {en, bg, es, ar}, analyst: {...}}`. The `truth_check` field should also record `l10n: {placeholders_ok, terms_ok, qe, reviewed}`.
2. Build `l10n/` with five parts:
   - `glossary/<lang>.tsv`
   - `templates.<lang>.json`: ICU messages, translated once with Translator plus glossary and checks
   - `names.json`: synthetic names in Latin, Cyrillic and Arabic
   - `format.ts`: Intl, one place
   - `cache.json`
3. Runtime: fill the ICU template with numbers and names, and call no MT. LLM-polished casual text uses generate-then-translate (doc 22) with `notranslate`. Spanish uses AdaptCT reference pairs, while BG/AR use the plain LLM deployment plus the term check.
4. Run CometKiwi or MetricX offline. Show "4 languages · 100% placeholders intact · N% human-reviewed · median QE" as a demo metric (doc 28 wants our own measured numbers).
5. The 30-second demo moment is the same Speed Trap cue in EN → BG → AR: the layout mirrors, the name switches script, the digits stay correct, and a glossary term is highlighted.

## Reuse: code & links

**Translator 2026-06-06 call with locked placeholders and a dynamic dictionary (Python).** Reuses `protect`/`unprotect`/`PH` from doc 22.

```python
import os, re, requests
from explain import protect, unprotect, PH            # doc 22

EP  = "https://api.cognitive.microsofttranslator.com/translate?api-version=2026-06-06"
HDR = {"Ocp-Apim-Subscription-Key": os.environ["TRANSLATOR_KEY"],
       "Ocp-Apim-Subscription-Region": os.environ["TRANSLATOR_REGION"],
       "Content-Type": "application/json"}
DYN = {"bg": {"clean sheet": "суха мрежа"}}             # compound nouns only (MS guidance)

def mark_terms(html: str, lang: str) -> str:
    for en, tgt in DYN.get(lang, {}).items():
        html = re.sub(rf"\b{re.escape(en)}\b",
                      f'<mstrans:dictionary translation="{tgt}">{en}</mstrans:dictionary>', html)
    return html

def translate_skeleton(skel_en: str, langs, deployment="general"):
    out = {}
    for l in langs:                                          # per-lang markup differs, so one call per lang
        body = {"inputs": [{
            "text": mark_terms(protect(skel_en), l),
            "language": "en", "textType": "html",            # source MUST be set for dyn. dictionary
            "targets": [{"language": l, "deploymentName": deployment, "allowFallback": False}]}]}
        r = requests.post(EP, headers=HDR, json=body, timeout=10); r.raise_for_status()
        txt = unprotect(r.json()["value"][0]["translations"][0]["text"])
        if sorted(PH.findall(txt)) != sorted(PH.findall(skel_en)):
            raise ValueError(f"placeholder lost in {l}: {txt}")
        out[l] = txt
    return out
# translate_skeleton("[[P0]] keeps a clean sheet after [[N0]] saves.", ["bg", "es", "ar"])
# For the LLM path pass deployment="<your-gpt-5.1-deployment>"; verify notranslate still holds (unverified).
```

**ICU MessageFormat for "3rd sprint over 34 km/h" in EN/BG/AR (JS, run with intl-messageformat 10.7.16, Node 24).**

```js
import { IntlMessageFormat } from 'intl-messageformat';

// CLDR gives bg no ordinal categories, so we compute the suffix. Valid 1..99 (100 = "100-тен"); verify with a native speaker.
function bgOrdSuffix(n, g = 'm') {               // g: m | f | n  (спринт m, атака f, попадение n)
  const t = n % 100, u = n % 10;
  const stem = (t >= 11 && t <= 19) ? '' : ({1:'в',2:'р',3:'т',4:'т',7:'м',8:'м'}[u] ?? '');
  return stem + { m: 'и', f: 'а', n: 'о' }[g];
}
const U = '::measure-unit/speed-kilometer-per-hour';   // '::unit/kilometer-per-hour' throws in this lib
const MSG = {
  en: `{ord, selectordinal, one {#st} two {#nd} few {#rd} other {#th}} sprint over {speed, number, ${U}}`,
  bg: `{ord}-{suf} спринт над {speed, number, ${U}}`,
  ar: `الانطلاقة {ord, select, 1 {الأولى} 2 {الثانية} 3 {الثالثة} 4 {الرابعة} 5 {الخامسة} other {رقم {ord}}} بسرعة تتجاوز {speed, number, ${U}}`,
};
const COUNT = {
  en: '{n, plural, one {# sprint} other {# sprints}} this half',
  bg: '{n, plural, one {# спринт} other {# спринта}} през това полувреме',
  ar: '{n, plural, zero {لا انطلاقات} one {انطلاقة واحدة} two {انطلاقتان} few {# انطلاقات} many {# انطلاقة} other {# انطلاقة}} في هذا الشوط',
};
for (const l of ['en', 'bg', 'ar'])
  console.log(new IntlMessageFormat(MSG[l], l).format({ ord: 3, suf: bgOrdSuffix(3), speed: 34 }));
// 3rd sprint over 34 km/h
// 3-ти спринт над 34 km/h
// الانطلاقة الثالثة بسرعة تتجاوز 34 كم/س
// COUNT ar, n = 0/1/2/3/11/100 -> لا انطلاقات / انطلاقة واحدة / انطلاقتان / 3 انطلاقات / 11 انطلاقة / 100 انطلاقة
```

The Arabic and Bulgarian strings are our drafts and need a native review before the demo. The word choice for "sprint" (انطلاقة) is a placeholder.

**Python formatting (Babel 2.17.0, verified output):**

```python
from babel.units import format_unit
format_unit(34.2, "speed-kilometer-per-hour", length="short", locale="bg")   # '34,2 km/h'
format_unit(34.2, "speed-kilometer-per-hour", length="short", locale="pl")   # '34,2 km/godz.'
# Babel keeps Latin digits even for ar_EG -> format digits in the overlay JS (Intl), not in Python.
```

**CometKiwi QE scoring (offline dev check only; model is CC BY-NC-SA 4.0 and gated. Run `huggingface-cli login` and accept the terms first).**

```python
# pip install "unbabel-comet>=2.0.0"
from comet import download_model, load_from_checkpoint
model = load_from_checkpoint(download_model("Unbabel/wmt22-cometkiwi-da"))
rows = [{"src": en, "mt": tr} for en, tr in pairs]          # pairs from templates.<lang>.json
out = model.predict(rows, batch_size=16, gpus=0)            # CPU is fine for a few hundred strings
worst = sorted(zip(out.scores, rows), key=lambda x: x[0])[: max(1, len(rows) // 10)]
for s, r in worst: print(f"{s:.3f}  {r['src']}  ->  {r['mt']}")   # send to human review
```

Permissive alternative: MetricX-24. Each JSONL line is `{"source":…, "hypothesis":…, "reference":""}`. Run `python -m metricx24.predict --tokenizer google/mt5-xl --model_name_or_path google/metricx-24-hybrid-large-v2p6 --max_input_length 1536 --batch_size 1 --input_file in.jsonl --output_file out.jsonl --qe`. The score is in `prediction`, from 0 to 25, lower is better.

**RTL-safe overlay CSS + fit fallback:**

```html
<div class="cue" lang="ar" dir="rtl" style="left:612px; top:388px">   <!-- physical anchor from tracker -->
  <span class="name"><bdi>Rowe</bdi></span>
  <span class="metric">الانطلاقة الثالثة بسرعة تتجاوز <span class="num">34 كم/س</span></span>
  <span class="metric-short"><span class="num">34 كم/س</span></span>
  <span class="clock">67′</span>
  <span class="arrow">▶</span>
</div>
```
```css
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans:wght@500;700&family=Noto+Sans+Arabic:wght@500;700&display=swap');
.cue { position:absolute; max-inline-size: 22rem; white-space:nowrap; overflow:hidden; display:flex; gap:.5rem; align-items:center;
       padding-block:.25rem; padding-inline:.75rem 1rem; border-inline-start:4px solid var(--club,#0af);
       text-align:start; font-family:"Noto Sans","Noto Sans Arabic",sans-serif; }
.cue .num, .cue .clock { unicode-bidi:isolate; direction:ltr; font-variant-numeric:tabular-nums; }
.cue .arrow { transform:scaleX(var(--flip,1)); }  .cue[dir="rtl"] .arrow { --flip:-1; }  /* points "forward" */
.cue[lang="ar"] { letter-spacing:0; font-style:normal; }
.cue .metric-short { display:none; }
.cue.too-long .metric { display:none; } .cue.too-long .metric-short { display:inline; }
```
```js
// swap to the short variant if the translated text overflows its box
for (const el of document.querySelectorAll('.cue')) el.classList.toggle('too-long', el.scrollWidth > el.clientWidth + 1);
```

**Links:**
- Translator 2026-06-06 translate reference: https://learn.microsoft.com/en-us/azure/ai-services/translator/text-translation/2026-06-06/translate-api
- Adaptive custom translation API: https://learn.microsoft.com/en-us/azure/ai-services/translator/custom-translator/azure-ai-foundry/concepts/adaptive-custom-translation
- intl-messageformat: https://www.npmjs.com/package/intl-messageformat
- COMET: https://github.com/Unbabel/COMET
- MetricX: https://github.com/google-research/metricx
- IFAB documents (Laws in many languages): https://theifab.com/documents

## Sources

- Microsoft Learn, What is Azure text translation (2026-06-06 GA, limits, pricing model) — https://learn.microsoft.com/en-us/azure/ai-services/translator/text-translation/overview — accessed 20 Oct 2026
- Microsoft Learn, 2026-06-06 translate method — https://learn.microsoft.com/en-us/azure/ai-services/translator/text-translation/2026-06-06/translate-api — accessed 20 Oct 2026
- Microsoft Learn, 2026-06-06 transliterate method — https://learn.microsoft.com/en-us/azure/ai-services/translator/text-translation/2026-06-06/transliterate-api — accessed 20 Oct 2026
- Microsoft Foundry blog, Translator API 2026-06-06 GA — https://devblogs.microsoft.com/foundry/azure-translator-api-version-2026-06-06-ga-supporting-multilingual-applications-with-flexible-translation-options/ — accessed 20 Oct 2026
- Microsoft Learn, Dynamic dictionary — https://learn.microsoft.com/en-us/azure/ai-services/translator/text-translation/how-to/use-dynamic-dictionary — accessed 20 Oct 2026
- Microsoft Learn, Prevent content translation — https://learn.microsoft.com/en-us/azure/ai-services/translator/text-translation/how-to/prevent-translation — accessed 20 Oct 2026
- Microsoft Learn, Custom Translator dictionaries — https://learn.microsoft.com/en-us/azure/ai-services/translator/custom-translator/concepts/dictionaries — accessed 20 Oct 2026
- Microsoft Learn, Neural dictionary — https://learn.microsoft.com/en-us/azure/ai-services/translator/text-translation/how-to/use-neural-dictionary — accessed 20 Oct 2026
- Microsoft Learn, Adaptive custom translation — https://learn.microsoft.com/en-us/azure/ai-services/translator/custom-translator/azure-ai-foundry/concepts/adaptive-custom-translation — accessed 20 Oct 2026
- Microsoft Learn, Translator language support (incl. LLM/AdaptCT columns, transliteration table) — https://learn.microsoft.com/en-us/azure/ai-services/translator/language-support — accessed 20 Oct 2026
- Microsoft Learn, Document translation overview — https://learn.microsoft.com/en-us/azure/ai-services/translator/document-translation/overview — accessed 20 Oct 2026
- Azure Translator pricing (F0 2M chars/month; hosting fee model) — https://azure.microsoft.com/en-us/pricing/details/translator/ — accessed 20 Oct 2026
- Unicode CLDR, Language Plural Rules chart — https://www.unicode.org/cldr/charts/48/supplemental/language_plural_rules.html — accessed 20 Oct 2026
- ICU User Guide, Formatting Messages — https://unicode-org.github.io/icu/userguide/format_parse/messages/ — accessed 20 Oct 2026
- MDN, dir global attribute — https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Global_attributes/dir — accessed 20 Oct 2026
- MDN, CSS logical properties and values — https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_logical_properties_and_values — accessed 20 Oct 2026
- W3C Internationalization, Text size in translation — https://www.w3.org/International/articles/article-text-size — accessed 20 Oct 2026
- Hugging Face, Unbabel/wmt22-cometkiwi-da — https://huggingface.co/Unbabel/wmt22-cometkiwi-da — accessed 20 Oct 2026
- Hugging Face, Unbabel/XCOMET-XL — https://huggingface.co/Unbabel/XCOMET-XL — accessed 20 Oct 2026
- Hugging Face, Unbabel/wmt23-cometkiwi-da-xl (licence, 3.5B; via search snippet) — https://huggingface.co/Unbabel/wmt23-cometkiwi-da-xl — accessed 20 Oct 2026
- GitHub, Unbabel/COMET — https://github.com/Unbabel/COMET — accessed 20 Oct 2026
- GitHub, google-research/metricx — https://github.com/google-research/metricx — accessed 20 Oct 2026
- Hugging Face, google/metricx-24-hybrid-large-v2p6 — https://huggingface.co/google/metricx-24-hybrid-large-v2p6 — accessed 20 Oct 2026
- IFAB, Documents (Laws of the Game translations) — https://theifab.com/documents — accessed 20 Oct 2026 (via search snippet)
- IFAB, Laws of the Game 2021/22 Bulgarian (BFS translation) — https://downloads.theifab.com/downloads/laws-of-the-game-2021-22-bulgarian — accessed 20 Oct 2026 (page too large to fetch; existence via search)
- IFAB, Laws of the Game 2026/27 Arabic — https://downloads.theifab.com/downloads/laws-of-the-game-202627-arabic-double-pages — accessed 20 Oct 2026 (via search snippet)
- Translation Bureau (Canada), Soccer Glossary — https://tplus-pp.btb.gc.ca/publications/soccer-eng.html — accessed 20 Oct 2026 (via search snippet)
- Our runs: Node 24.14.1 (ICU 78.2, CLDR 48) `Intl.*` outputs; intl-messageformat 10.7.16; Babel 2.17.0 — 20 Oct 2026
- Internal: 03-foundry-llm-explain.md, 12-judging-criteria-and-rules.md, 22-explanation-generation-patterns.md, 27-voice-speech-and-audio.md, 28-sponsor-goals-and-real-world-impact.md
