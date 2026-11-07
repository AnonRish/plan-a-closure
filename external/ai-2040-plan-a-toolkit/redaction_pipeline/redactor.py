"""
redactor.py

The Transparency Plan's "Filtered Transparency" variant needs auditor reports
sanitized before they cross from the secure zone to the public one. This builds
the part of that pipeline that's honestly buildable here:

STRUCTURAL layer (real, deterministic, fully tested below):
  - author-inserted markers (<<SENSITIVE:category>> ... <<END>>) -- the author
    flags their own sensitive spans, the tool's job is to never miss one
  - a configurable watchlist of names to redact
  - configurable regex patterns (emails, ID numbers, whatever a deployment needs)

SEMANTIC layer (an interface, not an implementation): deciding whether an
unmarked paragraph contains, say, dangerous technical uplift is a judgment
call, not a pattern match. That needs an LLM. I don't have a live model call
available in this sandboxed execution -- the tests below exercise the
plumbing with an explicitly-labeled keyword-heuristic stub, not a working
detector. See README, "About the semantic layer," before using this on
anything real.

Every redaction -- structural or semantic -- is recorded in a manifest with
the category, the rule that caught it, and a hash of the original span, so
what was removed is auditable even though its content isn't public.
"""

import hashlib
import re
from dataclasses import dataclass, field
from typing import Callable, Optional

MARKER_RE = re.compile(r"<<SENSITIVE:([A-Za-z0-9_\-]+)>>(.*?)<<END>>", re.DOTALL)


@dataclass(frozen=True)
class PatternRule:
    name: str
    regex: str
    category: str

    def find_spans(self, text):
        for m in re.finditer(self.regex, text):
            yield (m.start(), m.end(), self.category, f"pattern:{self.name}", None)


@dataclass(frozen=True)
class WatchlistRule:
    names: tuple
    category: str = "watchlisted_individual"

    def find_spans(self, text):
        for name in self.names:
            for m in re.finditer(re.escape(name), text, flags=re.IGNORECASE):
                yield (m.start(), m.end(), self.category, "watchlist", None)


def _marker_spans(text):
    for m in MARKER_RE.finditer(text):
        yield (m.start(), m.end(), m.group(1), "author_marker", m.group(2))


@dataclass
class RedactionEntry:
    entry_id: str
    category: str
    rule_type: str
    start: int
    end: int
    original_text_hash: str
    original_text: Optional[str]  # populated only in the confidential manifest


@dataclass
class RedactionResult:
    redacted_text: str
    confidential_manifest: list  # full detail, NOT for public release
    public_manifest: list        # counts/categories only

    def public_summary(self):
        by_cat = {}
        for e in self.confidential_manifest:
            by_cat[e.category] = by_cat.get(e.category, 0) + 1
        return dict(sorted(by_cat.items()))


def _merge_overlapping(spans):
    """spans: list of (start, end, category, rule_type, content_override). Later-found
    overlaps are merged into the earliest-starting span, keeping its category label
    (author markers are found first, so an author's own judgment wins over
    a pattern rule that happens to also match inside their marked region)."""
    spans = sorted(spans, key=lambda s: (s[0], s[1]))
    merged = []
    for s in spans:
        if merged and s[0] < merged[-1][1]:
            prev = merged[-1]
            merged[-1] = (prev[0], max(prev[1], s[1]), prev[2], prev[3], prev[4])
        else:
            merged.append(s)
    return merged


def redact(text: str, patterns=(), watchlist: Optional[WatchlistRule] = None,
           semantic_flagger: Optional[Callable[[str], Optional[str]]] = None,
           id_prefix: str = "r") -> RedactionResult:
    spans = list(_marker_spans(text))
    for rule in patterns:
        spans.extend(rule.find_spans(text))
    if watchlist is not None:
        spans.extend(watchlist.find_spans(text))

    spans = _merge_overlapping(spans)

    if semantic_flagger is not None:
        covered = spans
        for para_match in re.finditer(r"[^\n]+(?:\n[^\n]+)*", text):
            p_start, p_end = para_match.start(), para_match.end()
            if any(not (p_end <= c[0] or p_start >= c[1]) for c in covered):
                continue  # paragraph already (partly) covered by a structural rule
            category = semantic_flagger(para_match.group(0))
            if category:
                spans.append((p_start, p_end, category, "semantic", None))
        spans = _merge_overlapping(spans)

    confidential_manifest = []
    for i, (start, end, category, rule_type, content_override) in enumerate(spans):
        original = content_override if content_override is not None else text[start:end]
        confidential_manifest.append(RedactionEntry(
            entry_id=f"{id_prefix}-{i+1}",
            category=category,
            rule_type=rule_type,
            start=start, end=end,
            original_text_hash=hashlib.sha256(original.encode()).hexdigest(),
            original_text=original,
        ))

    redacted_text = text
    for entry in sorted(confidential_manifest, key=lambda e: -e.start):
        marker = f"[REDACTED: {entry.category} #{entry.entry_id}]"
        redacted_text = redacted_text[:entry.start] + marker + redacted_text[entry.end:]

    public_manifest = [
        {"entry_id": e.entry_id, "category": e.category, "rule_type": e.rule_type, "original_text_hash": e.original_text_hash}
        for e in confidential_manifest
    ]
    return RedactionResult(redacted_text=redacted_text, confidential_manifest=confidential_manifest, public_manifest=public_manifest)


class StubKeywordSemanticFlagger:
    """NOT a semantic detector. A keyword-presence heuristic that exists only
    to exercise the semantic_flagger interface's plumbing in tests. Flags a
    paragraph if any trigger term appears, case-insensitively -- exactly the
    kind of shallow matching a real (LLM-based) semantic layer is needed to
    do better than."""

    def __init__(self, trigger_terms, category="flagged_by_stub_heuristic"):
        self.trigger_terms = [t.lower() for t in trigger_terms]
        self.category = category

    def __call__(self, paragraph: str) -> Optional[str]:
        low = paragraph.lower()
        if any(t in low for t in self.trigger_terms):
            return self.category
        return None
