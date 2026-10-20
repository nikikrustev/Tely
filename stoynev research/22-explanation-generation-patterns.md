# 22 — Turning numbers into "why it matters" text: wordalization, salience and audience variants

_Accessed/compiled: 20 Oct 2026 · Priority area: Interpret → Explain → Personalise (salience, sentence planning, faithfulness checks, multilingual)_

## TL;DR

- **Templates are near-perfect on facts; free neural or LLM text is not.** On RotoWire basketball recaps, a template baseline got 99.3% of its facts right against the data. The best neural model of the time got 71.8% (Wiseman et al. 2017). Human checking of three later systems found about **20 errors per recap**, and 184 of the 418 errors were **wrong numbers** (Thomson & Reiter 2020). In 2024, **more than 80%** of open-LLM data-to-text outputs had at least one semantic error (Kasner & Dušek 2024).
- **"Wordalization" (Sumpter / Twelve Football) is the proven middle path.** Code turns numbers into words first: z-score or percentile bands such as "outstanding" or "slim chance", plus a ranked list of reasons. The LLM only polishes that text. With an LLM judge, the share of texts with unsupported claims fell from **91% (no data) and 50% (raw stats) to 18% (wordalized)**. Humans rated the wordalized texts as faithful as the raw-stats texts and more engaging (Caut et al. 2025). The xG version (Rahimian, Flisar & Sumpter 2025, arXiv 2504.00767) uses the same linear-SHAP "because" contributions we already build in file 07.
- **Our pattern: template first, then LLM polish with locked placeholders, then a code verifier, with the template as fallback.** The LLM never sees a player name or a number. It sees `[[P1]]` and `[[N1]]`. Code then checks four things: the placeholders survived, no new digits or names appeared, there are no polarity contradictions, and length and reading-ease limits hold. If any check fails, we fall back to the deterministic template. For a two-stage template + neural pipeline, Kasner & Dušek (2022) counted **3 hallucinations in 100 WebNLG outputs, against 28** for the one-stage model.
- **Salience should be a transparent, additive score shown on screen as "why this fired".** Our formula combines rarity (surprise, −log₂ p vs a baseline), leverage (win-probability swing), consequence (what happens in the next 10 s) and narrative arc. It is multiplied by a novelty/cooldown factor. Weights are ours and can be tuned. Leverage follows Tango's Leverage Index and Burke's Excitement Index.
- **Multilingual: generate the English skeleton, translate it with placeholders wrapped in `notranslate`, then fill in locale-formatted numbers.** The DFL AI live ticker instead asks the LLM directly for each language and style. Its published latency is 7-12 s, and no validation step is described.

## Findings

### 1. What the precedents actually do

| System | How text is made | Checks | Source |
|---|---|---|---|
| **Wordalisations** (Caut, …, Sumpter 2025; Twelve Football) | 4-part prompt: "tell it who it is" → "what it knows" (expert Q&A pairs) → "what data to use" (z-scores turned into words: >1.5 outstanding, 1-1.5 excellent, 0.5-1 good, ±0.5 average, −1 to −0.5 below average, < −1 poor) → "how to answer" (format + few-shot) | LLM judge plus a human study (121 responses from 26 people) | arXiv 2503.15509; repo `amandinecaut/wordalisation` |
| **xG wordalization** (Rahimian, Flisar, Sumpter 2025) | Contribution = βⱼ(xⱼ − μⱼ). Only features with \|contribution\| > 0.1 log-odds are mentioned (the authors call this "somewhat arbitrary"). xG bands: slim < 0.028, low < 0.056, decent < 0.096, high-quality < 0.3, excellent above that (25th/50th/75th/90th percentiles). Prompt: "shot commentator" role, 43 Q&A pairs, 3 human few-shot examples. Sentence 1 says how good the chance was, sentences 2-3 give the top factors, the last sentence is praise or advice | LLM rates engagement 0-5 over 10 runs. Accuracy = does the LLM get the sign of a factor right. **Engagement and accuracy trade off.** The paper's own example says "right foot" while also listing a left-foot factor, so even the authors' sample slipped | arXiv 2504.00767; repo `Peggy4444/shotsGPT`; app shotsgpt.streamlit.app |
| **DFL Data Story Finder** (AWS) | Event-based, threshold/exceptional and summary stories, checked against "pre-defined story templates". Each type has "its own business rules and guardrails". Summaries use generative AI. DE + EN | **Story Monitor**: editors review, modify or remove a story before commentators see it | AWS M&E blog |
| **Bundesliga AI live ticker** (AWS + Sportec Solutions) | LLM-first. Lambda builds a prompt from about 1,600 event data points per match and calls Bedrock. The prompt sets language and style ("Sports Journalist", "Casual", "Bro (Gen Z)") | None described. 7-12 s from action to ticker | AWS M&E blog |
| **AP + Automated Insights Wordsmith** | Configured templates (rule-based NLG) for Minor League Baseball: 142 teams, 13 leagues, MLBAM stats. AP editors "configure[d] the Wordsmith platform to conform with the news judgment and standards" | "Fewer errors" than human writers is claimed but not quantified (vendor/press claim) | Capitol Broadcasting 2016; tech.co |

**Licence note:** `twelve-gpt-educational`, `shotsGPT` and `wordalisation` are all **GPL-3.0**. Copy the ideas (thresholds, prompt structure), not the code, unless we accept GPL for our repo.

### 2. Evidence: template-first vs LLM-first

- **Reiter & Dale pipeline (2000):** document planning (what to say) → microplanning (wording, aggregation, referring expressions) → surface realisation. Our "salience → sentence plan → LLM polish" maps onto this. The LLM only does the last step.
- **Castro Ferreira et al. 2019 (WebNLG):** explicit pipeline steps gave better text than end-to-end models on automatic, human and qualitative evaluation, and generalised better to unseen input.
- **Kasner & Dušek 2022:** a hand-written template for each predicate (354 templates), then neural ordering, aggregation and compression. In a manual check of 100 outputs, the 3-stage model had 3 hallucinations and 2 omissions on WebNLG and 0/0 on E2E. The 1-stage model had 28/6 and 17/1.
- **LLM-era:** Kasner & Dušek 2024 report that >80% of open-LLM outputs had at least one semantic error, even though the text was fluent.
- **Verdict for us:** template + constrained LLM rewrite + code verifier, with the template as fallback. LLM-first + verification is fine for **offline** recaps (13 Recap Dial, 11 Player Diary). There we can afford regenerate loops and report a sentence-level verification score.

### 3. Salience: deciding a moment is worth explaining

| Signal | How to compute | Precedent |
|---|---|---|
| Rarity | Percentile vs a baseline (our synthetic season, the player's own history). Surprise = −log₂(tail p): a 1-in-50 event is 5.6 bits | DFL "exceptional performance" thresholds; Caut z-bands |
| Leverage | \|ΔWP\| from our win-probability model, or the swing that *could* happen (prospective) | Tango LI = possible WP swing ÷ average swing, normalised so the average is 1.0. FanGraphs bins: low < 0.85, medium 0.85-2.0, high > 2.0. Burke's Excitement Index sums \|ΔWP\| over the game |
| Consequence | Best outcome in the next N s (goal > shot on target > shot > box entry > turnover) | Prime Vision's "score in next 10 s" bar (file 11) |
| Novelty / cooldown | Decays per (metric, player) key, plus the layout cooldowns from file 11 | Broadcast cooldowns (our guesses, file 11) |
| Narrative arc | Milestone, streak (start/end), comeback, season best | DFL event-based stories (goal → season rank; clean-sheet streak ends) |

**Our salience score (labelled ours; weights are guesses):**
`S = novelty × (0.35·rarity + 0.30·leverage + 0.20·consequence + 0.15·arc)`. Every term is in [0,1]. Rarity = −log₂p / −log₂(0.001). Leverage = min(\|ΔWP\|/0.20, 1). Novelty = 1 − e^(−Δt/120 s). Fire when S ≥ 0.45 and the layout gate (file 11) allows it. In our test, a 1-in-50 moment with a +13 pp WP swing followed by a shot on target scored 0.53 and fired. The same moment 60 s after a cue on the same key scored 0.21 and was suppressed. Put the components into the cue's `evidence` so the producer (F Graphics Desk) sees *why* it fired.

### 4. Audience variants and length budgets

| Audience | Content rule | Reading target (ours) | Vocabulary |
|---|---|---|---|
| Analyst | Number + the top 1-2 contributions; jargon allowed (xG, PPDA) | none | Full metric names |
| Casual | Band word + one reason, ≤1 number | Flesch Reading Ease ≥ 60 ("plain English, 13-15 year olds") | Ban list: xG, PPDA, xT, "progressive", "half-space" (or route them to 12 Jargon Buster) |
| Kids (10 Story Time) | Band word in kid language ("really hard chance"), cause → effect, no numbers except the score | FRE ≥ 80 (6th grade: "easy to read") | Kid band words; analogies |
| Single-metric (C One Number) | Only the chosen metric's template family; drop the other reasons | as casual | — |

Flesch Reading Ease = 206.835 − 1.015·(words/sentences) − 84.6·(syllables/words). FK grade = 0.39·(w/s) + 11.8·(syl/w) − 15.59. **Caveat:** on 6-12-word captions the score is noisy (it can go above 100). Use it as a guard against long words, not as a target. It is English-only. **Length budgets** come from file 11's layouts: `tag` = name + 1 metric, `pop` ≤ 8 words, `strap` ≤ 12 words. For `summary`, ~40 words is our guess. `ttl_ms = clamp(1000 + 360·words, …)`.

### 5. Faithfulness checks and demo metrics

- **Placeholder survival** (exact multiset of `[[P*]]`/`[[N*]]`), **no bare digits** outside slots, **no raw roster names** typed by the model.
- **Polarity / contradiction:** each plan carries a polarity (e.g. a low chance). Words for the opposite polarity ("sitter", "great chance") fail the check. Direction words must match the sign of the contribution.
- **Numeric verification for free text:** a number passes if some evidence value rounds to it *at the precision shown* ("24" ≈ 23.6 passes; "11.2" vs 11.3 fails).
- **Claim-level metrics from the literature:** FActScore = % of atomic facts supported (ChatGPT scored 58% on biographies; the automatic estimator has <2% error). RAGAS faithfulness = supported claims ÷ total claims. QAGS asks the same questions of the source and the summary and compares the answers. The **Foundry Groundedness evaluator** (`builtin.groundedness`) scores 1-5 with a default pass threshold of 3. **Groundedness Pro** (preview, Content Safety) returns true/false. Inputs are `response` + `context` (+ `query`).
- **Report in the demo:** % of cues that pass all checks; % of LLM rewrites accepted vs template fallback; % of sentences with verified numbers; Foundry groundedness pass rate on a sample, with our serialized evidence as `context`; reading-target hit rate per audience; and cues fired per 90 min.

### 6. Multilingual

- **Generate-then-translate (recommended for live):** take the English skeleton with placeholders, wrap each placeholder in `<span class="notranslate">` with `textType=html` in Azure Translator, re-check placeholder survival, then fill. Fill numbers with locale formatting (`0,04` for bg/de) and names from a per-language name table (for example a Cyrillic spelling for bg, if we want one). The dynamic dictionary or a Custom Translator dictionary can force football terms.
- **Generate-in-language:** the LLM writes each language directly, as the DFL ticker does. More natural idiom, but you need a verifier per language and reading-ease formulas do not transfer. Use it only for offline recaps, with the same placeholder lock.

## So what for us

**Stages:** Interpret (salience), Explain (planner + rewrite + verifier), Personalise (audience/language variants), Render (length budget → layout and `ttl_ms`).

1. Build `explain.py` (below) as one deterministic module **before** any agent work. Every cue's `text` per audience comes from `plan_*()`. The LLM polish is optional and toggled per audience. `truth_check` in the cue = verifier result, and `source` = `llm` or `template`. This is our answer to the 40-50 "fact-checker agent" entries: our fact-checker is code and never takes the LLM's word for a number.
2. Write one template family per metric we ship: xG (file 07), pass difficulty (file 08), pressure (file 09), speed (B Speed Trap). Use Caut z-bands for "season-normal" comparisons and Rahimian xG bands for shots.
3. Salience drives **F Graphics Desk** proposals (show S and its components), **15 Record Watch** (arc term) and **21 Called It** (the leverage term doubles as the "big moment" flag).
4. **10 Story Time / 12 Jargon Buster / C One Number** are just audience keys in the same planner. That is cheap breadth to show judges.
5. Demo slide: "N cues, X% LLM-polished, 100% numbers verified, Y% template fallback". Back it with the Foundry groundedness pass rate on a sample. Judges reward measurable trust.

## Reuse: code & links

Tested with Python 3.12, standard library only. A 1-in-50 moment with a +13 pp WP swing and a shot on target gives S = 0.533 and fires. 60 s after a cue on the same key it gives 0.21 and does not. An injected bad LLM output ("Kai Rowe had a great chance from 18 metres") is rejected on all four checks, and the code falls back to the template.

```python
# explain.py - salience -> template plan -> LLM rewrite with locked placeholders -> verify -> fill
import math, re
from dataclasses import dataclass, field

# ---------- 1. Salience (our formula; weights are our guesses, tune on synthetic matches) ----------
W = {"rarity": 0.35, "leverage": 0.30, "consequence": 0.20, "arc": 0.15}
FIRE_AT = 0.45          # fire a cue when S >= this (our guess)
TAU_S = 120.0           # novelty recovers with time constant 2 min per (metric, player) key

def rarity(tail_p: float, p_floor: float = 1e-3) -> float:
    """Surprise in bits, -log2 p, scaled to 0..1. tail_p = share of baseline at least this extreme."""
    p = min(max(tail_p, p_floor), 1.0)
    return math.log2(1 / p) / math.log2(1 / p_floor)

def leverage(wp_before: float, wp_after: float, cap: float = 0.20) -> float:
    return min(abs(wp_after - wp_before) / cap, 1.0)

CONSEQ = {"goal": 1.0, "shot_on_target": 0.7, "shot": 0.5, "box_entry": 0.3, "turnover": 0.2, None: 0.0}
ARC = {"milestone": 1.0, "comeback": 1.0, "streak_end": 0.8, "streak": 0.6, "season_best": 0.6, None: 0.0}

def novelty(now_s: float, last_s: float | None) -> float:
    return 1.0 if last_s is None else 1 - math.exp(-(now_s - last_s) / TAU_S)

@dataclass
class Moment:
    key: str                  # e.g. "xg:P7" - cooldown key (metric + player)
    t: float                  # match seconds
    tail_p: float             # from percentile vs baseline
    wp_before: float
    wp_after: float
    next_event: str | None    # most valuable outcome within next 10 s
    arc: str | None = None

def salience(m: Moment, last_seen: dict) -> dict:
    parts = {"rarity": rarity(m.tail_p), "leverage": leverage(m.wp_before, m.wp_after),
             "consequence": CONSEQ[m.next_event], "arc": ARC[m.arc]}
    base = sum(W[k] * v for k, v in parts.items())
    nov = novelty(m.t, last_seen.get(m.key))
    s = round(base * nov, 3)
    return {"score": s, "fire": s >= FIRE_AT, "novelty": round(nov, 3),
            **{k: round(v, 3) for k, v in parts.items()}}   # goes into cue evidence: "why this fired"

# ---------- 2. Wordalization bands + template sentence planner (3 audiences) ----------
XG_BANDS = [(0.028, "slim"), (0.056, "low"), (0.096, "decent"), (0.30, "high-quality"), (1.01, "excellent")]  # Rahimian et al. 2025
KID_WORDS = {"slim": "really hard", "low": "hard", "decent": "okay", "high-quality": "good", "excellent": "super"}

def band(x, bands):
    return next(w for lim, w in bands if x < lim)

def z_word(z):  # Caut et al. 2025 scout thresholds
    return ("outstanding" if z > 1.5 else "excellent" if z > 1 else "good" if z > 0.5 else
            "average" if z >= -0.5 else "below average" if z >= -1 else "poor")

@dataclass
class Plan:
    text: str                                   # skeleton with [[P1]] / [[N1]] placeholders
    slots: dict = field(default_factory=dict)   # placeholder -> value (never shown to the LLM)
    polarity: str = "neutral"                   # "low" / "high" chance etc. for contradiction checks

def plan_shot(ev: dict, audience: str) -> Plan:
    b = band(ev["xg"], XG_BANDS)
    top = max(ev["contrib"], key=lambda k: abs(ev["contrib"][k]))      # biggest log-odds push
    reason = REASONS[top][ev["contrib"][top] > 0]
    slots = {"[[P1]]": ev["player"], "[[N1]]": f'{ev["xg"]:.2f}', "[[N2]]": f'{ev["dist_m"]:.0f}'}
    pol = "high" if b in ("high-quality", "excellent") else "low" if b in ("slim", "low") else "neutral"
    if audience == "analyst":
        t = f"[[P1]] xG [[N1]] from [[N2]] m: {b} chance, {reason}."
    elif audience == "casual":
        t = f"{b.capitalize()} chance for [[P1]], [[N2]] metres out: {reason}."
    else:  # kids
        t = f"That was a {KID_WORDS[b]} chance for [[P1]]. {reason.capitalize()} made it {'easier' if ev['contrib'][top] > 0 else 'harder'}."
    return Plan(t, {k: v for k, v in slots.items() if k in t}, pol)   # only slots this variant uses

REASONS = {  # feature -> (phrase if it lowered xG, phrase if it raised xG)
    "distance": ("the long distance", "being close to goal"),
    "angle": ("the tight angle", "a wide view of goal"),
    "pressure": ("a defender right next to him", "having space"),
    "header": ("it being a header", "it being a header"),
}

LENGTH_BUDGET = {"tag": 4, "pop": 8, "strap": 12, "summary": 40}   # words; pop/strap from file 11, summary is our guess
READING_TARGET = {"kids": 80, "casual": 60, "analyst": 0}          # min Flesch reading ease (our targets)

# ---------- 3. LLM rewrite prompt (placeholders locked) ----------
SYSTEM = """You polish one on-screen football caption.
Rules:
- Keep every token of the form [[P1]], [[N1]] etc. exactly as written, each exactly once. Never replace them with names or numbers.
- Do not add any number, name, team, time or fact that is not in the draft.
- Keep the meaning and the direction of every claim (e.g. 'hard' stays hard, 'close' stays close).
- Audience: {audience}. {style}
- At most {max_words} words. Return only the caption."""
STYLE = {"analyst": "Precise, allow terms like xG.", "casual": "Plain English, no jargon.",
         "kids": "Age 8-11. Short words, short sentences, warm tone, no jargon."}

def rewrite_messages(plan: Plan, audience: str, layout: str):
    return [{"role": "system", "content": SYSTEM.format(audience=audience, style=STYLE[audience],
                                                         max_words=LENGTH_BUDGET[layout])},
            {"role": "user", "content": plan.text}]

# ---------- 4. Verifier ----------
PH = re.compile(r"\[\[[PN]\d+\]\]")
NUM = re.compile(r"\d+(?:[.,]\d+)?")
OPPOSITE = {"low": ["great chance", "excellent", "sitter", "easy", "good chance"],
            "high": ["slim", "hard chance", "difficult", "unlikely", "long shot"]}

def verify(draft: Plan, out: str, roster: set, layout: str, audience: str) -> list[str]:
    errs = []
    if sorted(PH.findall(out)) != sorted(draft.slots):
        errs.append(f"placeholders changed: {sorted(PH.findall(out))} vs {sorted(draft.slots)}")
    bare = PH.sub("", out)
    if NUM.search(bare):
        errs.append(f"new number outside slots: {NUM.findall(bare)}")
    if any(name in bare for name in roster):
        errs.append("raw player name typed by model")
    low = bare.lower()
    errs += [f"contradiction: '{w}' vs polarity {draft.polarity}" for w in OPPOSITE.get(draft.polarity, []) if w in low]
    words = len(out.split())
    if words > LENGTH_BUDGET[layout]:
        errs.append(f"too long: {words} > {LENGTH_BUDGET[layout]}")
    fre = flesch_reading_ease(fill(out, draft.slots))
    if fre < READING_TARGET[audience]:
        errs.append(f"reading ease {fre:.0f} < {READING_TARGET[audience]}")
    return errs

def fill(text: str, slots: dict) -> str:
    for k, v in slots.items():
        text = text.replace(k, v)
    return text

def explain(plan: Plan, audience, layout, roster, llm=None, retries=1) -> tuple[str, dict]:
    """LLM is optional polish; on any failure fall back to the deterministic template."""
    if llm:
        for _ in range(retries + 1):
            out = llm(rewrite_messages(plan, audience, layout)).strip()
            errs = verify(plan, out, roster, layout, audience)
            if not errs:
                return fill(out, plan.slots), {"source": "llm", "truth_check": "pass"}
    errs = verify(plan, plan.text, roster, layout, audience)
    return fill(plan.text, plan.slots), {"source": "template", "truth_check": "pass" if not errs else errs}

# ---------- 5. Flesch reading ease (English only) ----------
def syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups)
    if w.endswith("e") and not w.endswith(("le", "ee")) and n > 1:
        n -= 1                                   # silent final e
    return max(n, 1)

def flesch_reading_ease(text: str) -> float:
    sentences = max(len(re.findall(r"[.!?]+", text)), 1)
    words = re.findall(r"[A-Za-z']+", text) or ["x"]
    syl = sum(syllables(w) for w in words)
    return 206.835 - 1.015 * (len(words) / sentences) - 84.6 * (syl / len(words))

def fk_grade(text: str) -> float:
    sentences = max(len(re.findall(r"[.!?]+", text)), 1)
    words = re.findall(r"[A-Za-z']+", text) or ["x"]
    syl = sum(syllables(w) for w in words)
    return 0.39 * (len(words) / sentences) + 11.8 * (syl / len(words)) - 15.59
```

Usage and the LLM hook (the `llm` callable wraps the `openai` client from file 03, e.g. `lambda msgs: client.responses.create(model=DEPLOY, input=msgs, max_output_tokens=60).output_text`):

```python
ev = {"player": "Kai Rowe", "xg": 0.04, "dist_m": 24, "contrib": {"distance": -0.9, "angle": 0.3, "pressure": -0.2}}
roster = {"Kai Rowe", "Leo Hart"}
for aud, lay in [("analyst", "strap"), ("casual", "strap"), ("kids", "summary")]:
    print(explain(plan_shot(ev, aud), aud, lay, roster))
# ('Kai Rowe xG 0.04 from 24 m: low chance, the long distance.', {'source': 'template', 'truth_check': 'pass'})
# ('Low chance for Kai Rowe, 24 metres out: the long distance.', {'source': 'template', 'truth_check': 'pass'})
# ('That was a hard chance for Kai Rowe. The long distance made it harder.', {'source': 'template', 'truth_check': 'pass'})
good = lambda msgs: "[[P1]] had a low chance from [[N2]] metres: too far out."
print(explain(plan_shot(ev, "casual"), "casual", "strap", roster, llm=good))
# ('Kai Rowe had a low chance from 24 metres: too far out.', {'source': 'llm', 'truth_check': 'pass'})
```

Free-text number check (for offline LLM-first recaps), translation protection and locale numbers:

```python
import re
NUM = re.compile(r"\d+(?:[.,]\d+)?")
PH = re.compile(r"\[\[[PN]\d+\]\]")

def sentence_number_report(text: str, evidence: list[float]) -> dict:
    """For free text (e.g. an LLM-first recap): share of number-bearing sentences whose numbers all match evidence."""
    sents = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]
    with_nums = verified = 0
    bad = []
    for s in sents:
        toks = NUM.findall(s)
        if not toks:
            continue
        with_nums += 1
        # a number is verified if some evidence value rounds to it at the precision shown ("24" ~ 23.6, "11.2" != 11.3)
        ok = all(any(abs(float(t.replace(",", ".")) - e) <= 0.5 * 10 ** -len(re.split(r"[.,]", t + ".")[1]) + 1e-9
                     for e in evidence) for t in toks)
        verified += ok
        if not ok:
            bad.append(s)
    return {"sentences": len(sents), "with_numbers": with_nums,
            "pct_verified": round(100 * verified / with_nums, 1) if with_nums else 100.0, "failed": bad}

def protect(text: str) -> str:
    """Wrap placeholders so Azure Translator (textType=html) leaves them alone."""
    return PH.sub(lambda m: f'<span class="notranslate">{m.group(0)}</span>', text)

def unprotect(html: str) -> str:
    return re.sub(r'<span class="notranslate">\s*(\[\[[PN]\d+\]\])\s*</span>', r"\1", html)

def fmt_num(x: float, lang: str, nd=2) -> str:
    s = f"{x:.{nd}f}"
    return s.replace(".", ",") if lang in ("bg", "de", "fr", "es", "it", "pt") else s

print(sentence_number_report("Rowe's shot was worth 0.04 xG from 24 metres. He has now run 11.2 km.", [0.04, 23.6, 11.3]))
# {'sentences': 2, 'with_numbers': 2, 'pct_verified': 50.0, 'failed': ['He has now run 11.2 km.']}
# Translator: POST {endpoint}/translate?api-version=3.0&to=bg&textType=html  body=[{"Text": protect(skeleton)}]
# then unprotect(), re-run the placeholder check, and fill with fmt_num(x, "bg") -> "0,04"
```

**Links**
- Wordalisation code, prompt cards, demo: https://github.com/amandinecaut/wordalisation · https://wordalisations.streamlit.app/ (GPL-3.0)
- xG wordalization: https://github.com/Peggy4444/shotsGPT (`classes/description.py`, model card) · https://shotsgpt.streamlit.app/ (GPL-3.0)
- Teaching base: https://github.com/soccermatics/twelve-gpt-educational (GPL-3.0; Q&A-pair embeddings for "tell it what it knows")
- Error-annotation corpus for sports data-to-text: Thomson & Reiter "evaluating_accuracy" (linked from arXiv 2011.03992); SportSett:Basketball dataset (Thomson, Reiter & Sripada 2020)
- Foundry groundedness sample: https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/ai/azure-ai-projects/samples/evaluations/agentic_evaluators/sample_groundedness.py
- `pip install factscore` (atomic-fact scoring) and `ragas` (`Faithfulness`), useful for offline recap evaluation only

## Sources

- Caut, Rouillard, Zenebe, Green, Morthens, Sumpter, Representing data in words (wordalisations), arXiv 2503.15509 — https://arxiv.org/html/2503.15509v2 — accessed 20 Oct 2026
- Rahimian, Flisar & Sumpter, Automated explanation of machine learning models of footballing actions in words, arXiv 2504.00767 — https://arxiv.org/html/2504.00767v1 — accessed 20 Oct 2026
- shotsGPT repository and description class — https://github.com/Peggy4444/shotsGPT/blob/main/classes/description.py — accessed 20 Oct 2026
- wordalisation repository — https://github.com/amandinecaut/wordalisation — accessed 20 Oct 2026
- twelve-gpt-educational repository — https://github.com/soccermatics/twelve-gpt-educational — accessed 20 Oct 2026
- Wiseman, Shieber & Rush, Challenges in Data-to-Document Generation (RotoWire), EMNLP 2017 — https://ar5iv.labs.arxiv.org/html/1707.08052 — accessed 20 Oct 2026
- Thomson & Reiter, A Gold Standard Methodology for Evaluating Accuracy in Data-To-Text Systems, INLG 2020 — https://ar5iv.labs.arxiv.org/html/2011.03992 — accessed 20 Oct 2026
- Thomson, Reiter & Sripada, SportSett:Basketball, IntelLang 2020 — https://preview.aclanthology.org/fix_video/2020.intellang-1.4.pdf — accessed 20 Oct 2026
- Castro Ferreira et al., Neural data-to-text generation: a comparison between pipeline and end-to-end architectures, EMNLP 2019 — https://ar5iv.labs.arxiv.org/html/1908.09022 — accessed 20 Oct 2026
- Kasner & Dušek, Neural Pipeline for Zero-Shot Data-to-Text Generation, ACL 2022 — https://arxiv.org/html/2203.16279 — accessed 20 Oct 2026
- Kasner & Dušek, Beyond Traditional Benchmarks: Analyzing Behaviors of Open LLMs on Data-to-Text Generation, ACL 2024 — https://aclanthology.org/2024.acl-long.651 — accessed 20 Oct 2026
- Reiter & Dale, Building Natural Language Generation Systems (CUP 2000), chapter pages — https://www.cambridge.org/core/books/abs/building-natural-language-generation-systems/surface-realisation/D45A2AC42657177D950874E6322D2609 — accessed 20 Oct 2026
- AWS M&E, Bundesliga Data Story Finder — https://aws.amazon.com/blogs/media/bundesliga-data-story-finder-delivering-fans-the-stories-they-love/ — accessed 20 Oct 2026
- AWS M&E, Bundesliga generative-AI live commentary (AI live ticker) — https://aws.amazon.com/blogs/media/revolutionizing-fan-engagementcer-bundesliga-generative-ai-powered-live-commentary/ — accessed 20 Oct 2026
- Capitol Broadcasting, AP to use Automated Insights for Minor League Baseball (2016) — https://capitolbroadcasting.com/2016/07/08/associated-press-to-utilize-automated-insights-robotic-software-to-cover-minor-league-baseball/ — accessed 20 Oct 2026
- tech.co, The Associated Press Will Automate Minor League Coverage (2016) — https://tech.co/news/associated-press-will-automate-minor-league-coverage-2016-06 — accessed 20 Oct 2026 (search-result snippet only)
- Min et al., FActScore, arXiv 2305.14251 — https://arxiv.org/abs/2305.14251 — accessed 20 Oct 2026
- Wang, Cho & Lewis, QAGS: Asking and Answering Questions to Evaluate the Factual Consistency of Summaries, arXiv 2004.04228 — https://arxiv.org/abs/2004.04228 — accessed 20 Oct 2026
- Ragas docs, Faithfulness — https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/ — accessed 20 Oct 2026
- Microsoft Learn, RAG evaluators (Groundedness, Groundedness Pro) — https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/evaluation-evaluators/rag-evaluators — accessed 20 Oct 2026
- Microsoft Learn, Prevent content translation (Azure Translator) — https://learn.microsoft.com/en-us/azure/ai-services/translator/text-translation/how-to/prevent-translation — accessed 20 Oct 2026
- FanGraphs Library, Leverage Index — https://library.fangraphs.com/misc/li — accessed 20 Oct 2026
- FiveThirtyEight, Super Bowl XLIX was not the most exciting Super Bowl ever (Burke Excitement Index) — https://fivethirtyeight.com/features/super-bowl-xlix-was-not-the-most-exciting-super-bowl-ever — accessed 20 Oct 2026 (via search snippet)
- Wikipedia, Flesch–Kincaid readability tests — https://en.wikipedia.org/wiki/Flesch%E2%80%93Kincaid_readability_tests — accessed 20 Oct 2026
- Internal: 07-expected-goals-xg.md (linear-SHAP contributions), 03-foundry-llm-explain.md (client, Translator), 11-broadcast-stats-presentation.md (layouts, ttl, cooldowns)
