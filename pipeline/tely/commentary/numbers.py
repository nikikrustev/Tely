"""The numbers a line says, in digits or in words, in each commentary language (D27 truth check).

    numbers("en", "Reds nil, Navy one, fifty-six minutes played.")   -> (Counter({0: 1, 1: 1, 56: 1}), 0)

languages.check() compares the English line's numbers with its translation's, as a multiset, so a translation can
neither drop, change nor add a number ("fünfundfünfzig" for fifty-six was shipped on 27 Oct and nothing caught it).
Covers 0..100, which is every score, minute and distance a line can say.

Ambiguous words: in German, Spanish, French, Bulgarian and Hindi the word for "one" is also the indefinite article
("ein Pass", "un centre", "एक मौका"), so those words come back as a separate count. The checker lets each of them stand
for a 1 the English says, but never counts one as a number the translation added.
"""
from __future__ import annotations

import re
from collections import Counter

_EN_UNITS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
             "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
_EN_TENS = {20: "twenty", 30: "thirty", 40: "forty", 50: "fifty", 60: "sixty", 70: "seventy", 80: "eighty", 90: "ninety"}


def _en() -> dict[str, int]:
    w = {s: i for i, s in enumerate(_EN_UNITS)} | {"nil": 0, "nought": 0}
    for t, s in _EN_TENS.items():
        w[s] = t
        for u in range(1, 10):
            w[f"{s}-{_EN_UNITS[u]}"] = w[f"{s} {_EN_UNITS[u]}"] = t + u
    return w | {"hundred": 100, "one hundred": 100, "a hundred": 100}


_DE_UNITS = ["null", "eins", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun", "zehn", "elf", "zwölf",
             "dreizehn", "vierzehn", "fünfzehn", "sechzehn", "siebzehn", "achtzehn", "neunzehn"]
_DE_TENS = {20: "zwanzig", 30: "dreißig", 40: "vierzig", 50: "fünfzig", 60: "sechzig", 70: "siebzig", 80: "achtzig",
            90: "neunzig"}


def _de() -> dict[str, int]:
    w = {s: i for i, s in enumerate(_DE_UNITS)} | {"zwo": 2}
    for t, s in _DE_TENS.items():
        w[s] = t
        for u in range(1, 10):
            w[("ein" if u == 1 else _DE_UNITS[u]) + "und" + s] = t + u
    return w | {"hundert": 100, "einhundert": 100}


_ES_UNITS = ["cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez", "once", "doce",
             "trece", "catorce", "quince", "dieciséis", "diecisiete", "dieciocho", "diecinueve", "veinte", "veintiuno",
             "veintidós", "veintitrés", "veinticuatro", "veinticinco", "veintiséis", "veintisiete", "veintiocho",
             "veintinueve"]
_ES_TENS = {30: "treinta", 40: "cuarenta", 50: "cincuenta", 60: "sesenta", 70: "setenta", 80: "ochenta", 90: "noventa"}


def _es() -> dict[str, int]:
    w = {s: i for i, s in enumerate(_ES_UNITS)}
    w |= {"dieciseis": 16, "veintidos": 22, "veintitres": 23, "veintiseis": 26, "veintiún": 21, "veintiun": 21,
          "veintiuna": 21}
    for t, s in _ES_TENS.items():
        w[s] = t
        for u in range(1, 10):
            w[f"{s} y {_ES_UNITS[u]}"] = t + u
        w[f"{s} y un"] = w[f"{s} y una"] = t + 1
    return w | {"cien": 100, "ciento": 100}


_FR_UNITS = ["zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix", "onze", "douze",
             "treize", "quatorze", "quinze", "seize", "dix-sept", "dix-huit", "dix-neuf"]


def _fr() -> dict[str, int]:
    w = {s: i for i, s in enumerate(_FR_UNITS)} | {"zero": 0}
    for t, s in {20: "vingt", 30: "trente", 40: "quarante", 50: "cinquante", 60: "soixante"}.items():
        w[s] = t
        w[f"{s} et un"] = w[f"{s}-et-un"] = w[f"{s} et une"] = t + 1
        for u in range(2, 10):
            w[f"{s}-{_FR_UNITS[u]}"] = t + u
    w["soixante et onze"] = w["soixante-et-onze"] = 71
    for u in range(10, 20):
        if u != 11:
            w[f"soixante-{_FR_UNITS[u]}"] = 60 + u
    w["quatre-vingts"] = w["quatre-vingt"] = 80
    for u in range(1, 20):
        w[f"quatre-vingt-{_FR_UNITS[u]}"] = 80 + u
    return w | {"cent": 100}


_BG_UNITS = ["нула", "едно", "две", "три", "четири", "пет", "шест", "седем", "осем", "девет", "десет"]
_BG_TEENS = {11: "едина", 12: "двана", 13: "трина", 14: "четирина", 15: "петна", 16: "шестна", 17: "седемна",
             18: "осемна", 19: "деветна"}
_BG_TENS = {20: ["двадесет", "двайсет"], 30: ["тридесет", "трийсет"], 40: ["четиридесет", "четирийсет"],
            50: ["петдесет"], 60: ["шестдесет"], 70: ["седемдесет"], 80: ["осемдесет"], 90: ["деветдесет"]}


def _bg() -> dict[str, int]:
    w = {s: i for i, s in enumerate(_BG_UNITS)} | {"два": 2}
    for n, stem in _BG_TEENS.items():
        w[stem + "десет"] = w[stem + "йсет"] = n
    units = {u: [_BG_UNITS[u]] for u in range(2, 10)} | {1: ["един", "една", "едно"], 2: ["два", "две"]}
    for t, forms in _BG_TENS.items():
        for s in forms:
            w[s] = t
            for u, us in units.items():
                for x in us:
                    w[f"{s} и {x}"] = t + u
    return w | {"сто": 100}


# Arabic: masculine and feminine units, and the nominative and oblique tens (خمسون / خمسين); "five and fifty" order.
_AR_UNITS = {1: ["واحد", "واحدة"], 2: ["اثنان", "اثنين", "اثنتان", "اثنتين"], 3: ["ثلاث", "ثلاثة"], 4: ["أربع", "أربعة"],
             5: ["خمس", "خمسة"], 6: ["ست", "ستة"], 7: ["سبع", "سبعة"], 8: ["ثمان", "ثماني", "ثمانية"], 9: ["تسع", "تسعة"]}
_AR_TENS = {20: ["عشرون", "عشرين"], 30: ["ثلاثون", "ثلاثين"], 40: ["أربعون", "أربعين"], 50: ["خمسون", "خمسين"],
            60: ["ستون", "ستين"], 70: ["سبعون", "سبعين"], 80: ["ثمانون", "ثمانين"], 90: ["تسعون", "تسعين"]}


def _ar() -> dict[str, int]:
    w = {"صفر": 0, "عشر": 10, "عشرة": 10, "أحد عشر": 11, "إحدى عشرة": 11, "اثنا عشر": 12, "اثني عشر": 12,
         "اثنتا عشرة": 12, "اثنتي عشرة": 12, "مئة": 100, "مائة": 100}
    for u, forms in _AR_UNITS.items():
        for s in forms:
            w[s] = u
    for u in range(3, 10):
        for s in _AR_UNITS[u]:
            w[f"{s} عشر"] = w[f"{s} عشرة"] = 10 + u
    for t, forms in _AR_TENS.items():
        for s in forms:
            w[s] = t
            for u, us in _AR_UNITS.items():
                for x in us:
                    w[f"{x} و{s}"] = t + u
    return w


_HI = ["शून्य", "एक", "दो", "तीन", "चार", "पाँच", "छह", "सात", "आठ", "नौ", "दस", "ग्यारह", "बारह", "तेरह", "चौदह", "पंद्रह",
       "सोलह", "सत्रह", "अठारह", "उन्नीस", "बीस", "इक्कीस", "बाईस", "तेईस", "चौबीस", "पच्चीस", "छब्बीस", "सत्ताईस", "अट्ठाईस",
       "उनतीस", "तीस", "इकतीस", "बत्तीस", "तैंतीस", "चौंतीस", "पैंतीस", "छत्तीस", "सैंतीस", "अड़तीस", "उनतालीस", "चालीस",
       "इकतालीस", "बयालीस", "तैंतालीस", "चवालीस", "पैंतालीस", "छियालीस", "सैंतालीस", "अड़तालीस", "उनचास", "पचास", "इक्यावन",
       "बावन", "तिरपन", "चौवन", "पचपन", "छप्पन", "सत्तावन", "अट्ठावन", "उनसठ", "साठ", "इकसठ", "बासठ", "तिरसठ", "चौंसठ",
       "पैंसठ", "छियासठ", "सड़सठ", "अड़सठ", "उनहत्तर", "सत्तर", "इकहत्तर", "बहत्तर", "तिहत्तर", "चौहत्तर", "पचहत्तर",
       "छिहत्तर", "सतहत्तर", "अठहत्तर", "उन्यासी", "अस्सी", "इक्यासी", "बयासी", "तिरासी", "चौरासी", "पचासी", "छियासी",
       "सत्तासी", "अट्ठासी", "नवासी", "नब्बे", "इक्यानवे", "बानवे", "तिरानवे", "चौरानवे", "पंचानवे", "छियानवे", "सत्तानवे",
       "अट्ठानवे", "निन्यानवे", "सौ"]


def _hi() -> dict[str, int]:
    return {s: i for i, s in enumerate(_HI)} | {"पांच": 5, "छः": 6, "छे": 6, "पन्द्रह": 15, "सौ": 100}


WORDS: dict[str, dict[str, int]] = {"en": _en(), "de": _de(), "es": _es(), "fr": _fr(), "bg": _bg(), "ar": _ar(),
                                    "hi": _hi()}
# The indefinite article that is also "one" (see the module note). Arabic has no such article; English "a" isn't "one".
AMBIGUOUS_ONE: dict[str, set[str]] = {
    "en": set(), "ar": set(),
    "de": {"ein", "eine", "einen", "einem", "einer", "eines"},
    "es": {"un", "una"},
    "fr": {"un", "une"},
    "bg": {"един", "една", "едно"},
    "hi": {"एक"},
}

# A word starts and ends where no letter or combining mark (Devanagari matras, Arabic harakat) touches it.
_MARK = "̀-ͯؐ-ًؚ-ٰٟۖ-ۭऀ-ःऺ-ॏ॑-ॗॢॣ"
_L = rf"(?:[^\W\d_]|[{_MARK}])"
_AR_PREFIX = "(?:[وفبل])?(?:ال)?"   # "و" (and), "ب" (with), "ال" (the) attach to the Arabic word


def _rx(lang: str) -> re.Pattern:
    words = sorted(set(WORDS[lang]) | AMBIGUOUS_ONE[lang], key=len, reverse=True)   # "fifty-six" before "fifty"
    alt = "|".join(re.escape(w).replace(r"\-", r"[-\s]").replace(r"\ ", r"\s+") for w in words)
    pre = _AR_PREFIX if lang == "ar" else ""
    return re.compile(rf"(?<!{_L}){pre}({alt})(?!{_L})|(\d+)", re.IGNORECASE)


def _norm(s: str) -> str:
    return re.sub(r"[-\s]+", " ", s.lower())    # "fifty-six", "fifty six", "dix sept" all read the same


_RX = {lang: _rx(lang) for lang in WORDS}
_VALUE = {lang: {_norm(k): v for k, v in w.items()} for lang, w in WORDS.items()}


def numbers(lang: str, text: str) -> tuple[Counter, int]:
    """(the numbers `text` says, as a multiset of ints; how many ambiguous "one"/article words it has)."""
    words, amb = _VALUE[lang], AMBIGUOUS_ONE[lang]
    found: Counter = Counter()
    ones = 0
    for m in _RX[lang].finditer(text):
        if m.group(2) is not None:
            found[int(m.group(2))] += 1          # any script's digits: int("٥٦") == 56
            continue
        w = _norm(m.group(1))
        if w in amb:
            ones += 1
        else:
            found[words[w]] += 1
    return found, ones


def mismatch(en: str, lang: str, tr: str) -> list[str]:
    """Errors when translation `tr` doesn't say exactly the numbers the English line `en` says."""
    want, _ = numbers("en", en)
    got, ones = numbers(lang, tr)
    errs = [f"number {n} missing" for n in sorted(want - got) if n != 1]
    if (want - got)[1] > ones:
        errs.append("number 1 missing")
    errs += [f"number {n} added" for n in sorted(got - want)]
    return errs
