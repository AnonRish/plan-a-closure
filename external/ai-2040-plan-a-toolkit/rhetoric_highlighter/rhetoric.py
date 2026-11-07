"""
rhetoric.py

AI for Epistemics wants tools that flag manipulative rhetorical technique in
text. "Manipulative" is a judgment call an LLM could make; what's honestly
buildable without one is surface pattern-matching -- lexicons and
structural signals, not understanding. This is organized around the
Institute for Propaganda Analysis's seven classic techniques (1937, "The
Fine Art of Propaganda") because it's a real, well-established framework,
not because I invented seven categories myself. Of the seven, four have a
real surface signature this module can look for; three don't, and are
named as gaps rather than quietly skipped -- see README.

DETECTABLE (implemented below):
  - Bandwagon            -- "everyone knows", "no one disputes"
  - Testimonial          -- appeal to unnamed authority: "experts say",
                             "studies show", with no specific source nearby
  - Name-Calling / Glittering Generalities -- loaded language, pejorative
                             or glowing, chosen for charge over precision
  - (structural, not one of the seven but the same family) Repetition of a
    phrase for emphasis -- a named classic propaganda technique in its own
    right, and the one signal here that's pure structure, no lexicon at all

NOT DETECTABLE by pattern-matching (named, not built):
  - Card Stacking   -- selective use of TRUE facts; needs fact-checking
  - Transfer        -- borrowing a respected symbol's authority; needs
                        entity recognition plus cultural knowledge of what
                        counts as respected
  - Plain Folks     -- speaker performing ordinariness; needs speaker
                        identity and audience context this module never has

Plus two general psycholinguistic signals with real (if contested)
literature behind them, included for the same reason repetition is:
  - absolutist_language  -- "always", "never", "everyone", "impossible"
  - false_urgency        -- "act now", "before it's too late"
"""

import re
from dataclasses import dataclass
from collections import Counter

# ---------- lexicons: self-constructed, not claimed to be a validated
# academic word list -- see README for why that distinction matters here
# specifically, of all places to overclaim a citation. ----------

BANDWAGON_PHRASES = [
    "everyone knows", "everybody knows", "everyone agrees", "no one disputes",
    "nobody disputes", "it's obvious that", "it is obvious that", "obviously,",
    "clearly, everyone", "most people agree", "no reasonable person",
    "any reasonable person", "we all know", "as everyone knows",
]

AUTHORITY_TRIGGERS = [
    "experts say", "experts agree", "studies show", "studies suggest",
    "research shows", "research proves", "science says", "scientists agree",
    "scientists say", "doctors recommend", "doctors agree", "data shows",
]

LOADED_NEGATIVE = [
    "radical", "extremist", "shill", "sheeple", "traitor", "puppet",
    "propaganda", "brainwashed", "cult", "regime", "thugs", "cronies",
    "so-called", "hack", "corrupt", "sham", "witch hunt", "hoax",
]

LOADED_POSITIVE = [
    "real americans", "common sense", "family values", "true patriots",
    "freedom-loving", "hardworking taxpayers", "silent majority",
    "god-given", "founding principles", "the will of the people",
]

ABSOLUTIST_WORDS = [
    "always", "never", "everyone", "no one", "nobody", "everybody",
    "completely", "totally", "absolutely", "impossible", "guaranteed",
    "every single", "without exception", "all of them", "none of them",
    "entirely", "undeniably", "unquestionably",
]

URGENCY_PHRASES = [
    "act now", "before it's too late", "limited time", "don't wait",
    "urgent:", "time is running out", "last chance", "act immediately",
    "the window is closing", "you must act",
]


@dataclass
class Span:
    start: int
    end: int
    category: str
    technique: str
    note: str


def _find_phrases(text, phrases, category, technique, note=""):
    low = text.lower()
    spans = []
    for phrase in phrases:
        start_idx = 0
        while True:
            idx = low.find(phrase, start_idx)
            if idx == -1:
                break
            spans.append(Span(idx, idx + len(phrase), category, technique, note or phrase))
            start_idx = idx + len(phrase)
    return spans


def detect_bandwagon(text):
    return _find_phrases(text, BANDWAGON_PHRASES, "bandwagon", "Bandwagon",
                          "asserts consensus instead of evidence")


def detect_unsourced_authority(text, window=80):
    spans = []
    low = text.lower()
    proper_noun_re = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+|\b[A-Z]{2,}\b)")
    year_re = re.compile(r"\(?(19|20)\d{2}\)?")
    for phrase in AUTHORITY_TRIGGERS:
        start_idx = 0
        while True:
            idx = low.find(phrase, start_idx)
            if idx == -1:
                break
            end = idx + len(phrase)
            nearby = text[max(0, idx - window):min(len(text), end + window)]
            has_source = bool(proper_noun_re.search(nearby) or year_re.search(nearby))
            if not has_source:
                spans.append(Span(idx, end, "unsourced_authority", "Testimonial",
                                   "cites authority with no specific, checkable source nearby"))
            start_idx = end
    return spans


def detect_loaded_language(text):
    neg = _find_phrases(text, LOADED_NEGATIVE, "loaded_language", "Name-Calling",
                         "pejorative word chosen for charge, not precision")
    pos = _find_phrases(text, LOADED_POSITIVE, "loaded_language", "Glittering Generalities",
                         "virtue phrase invoked without specifics")
    return neg + pos


def detect_absolutist_language(text):
    return _find_phrases(text, ABSOLUTIST_WORDS, "absolutist_language", "Absolutist framing",
                          "over-claims certainty or universal scope")


def detect_false_urgency(text):
    return _find_phrases(text, URGENCY_PHRASES, "false_urgency", "Urgency pressure",
                          "pushes immediate action, discourages reflection")


def detect_repetition(text, min_words=3, max_words=8, min_repeats=3):
    """Longest-match-first: an n-gram repeated min_repeats+ times is flagged;
    shorter sub-phrases already covered by a flagged longer phrase are not
    separately flagged too (they'd trivially also repeat)."""
    words = list(re.finditer(r"\S+", text))
    covered = [False] * len(words)
    spans = []
    for n in range(max_words, min_words - 1, -1):
        counts = Counter()
        positions = {}
        for i in range(len(words) - n + 1):
            if any(covered[i:i + n]):
                continue
            phrase = " ".join(w.group().lower().strip(".,!?;:\"'") for w in words[i:i + n])
            counts[phrase] += 1
            positions.setdefault(phrase, []).append(i)
        for phrase, count in counts.items():
            if count >= min_repeats and len(phrase) > 0:
                for i in positions[phrase]:
                    if any(covered[i:i + n]):
                        continue
                    start = words[i].start()
                    end = words[i + n - 1].end()
                    spans.append(Span(start, end, "repetition", "Repetition",
                                       f'repeated {count}x: "{phrase}"'))
                    for j in range(i, i + n):
                        covered[j] = True
    return spans


def analyze(text):
    spans = (
        detect_bandwagon(text) + detect_unsourced_authority(text) +
        detect_loaded_language(text) + detect_absolutist_language(text) +
        detect_false_urgency(text) + detect_repetition(text)
    )
    spans.sort(key=lambda s: s.start)
    counts = Counter(s.category for s in spans)
    word_count = max(1, len(text.split()))
    return {
        "spans": spans,
        "counts": dict(counts),
        "total_flags": len(spans),
        "flags_per_1000_words": len(spans) / word_count * 1000,
    }
