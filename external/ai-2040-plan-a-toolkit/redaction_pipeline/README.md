# Redaction pipeline (Filtered Transparency)

The other half of the Transparency Plan gap: before an auditor's report crosses from
the secure zone to the public one, sensitive spans need to come out — but "sensitive"
splits into two genuinely different kinds of problem, and this pipeline is honest
about which one it actually solves.

## Structural layer — real, deterministic, fully tested

Three rule types, all pattern-based, none requiring judgment:

- **Author markers** — `<<SENSITIVE:category>>...<<END>>`. The report's own author
  flags what they know is sensitive; the tool's only job is to never miss one.
- **Watchlist** — redact specific named individuals, case-insensitive.
- **Patterns** — regex, for whatever a deployment needs (emails, internal IDs).

Every redaction produces two manifests: a **public** one (category + rule + hash, safe
to publish alongside the redacted report, so a reader can see *that* something was
removed and *what kind* of thing, without seeing what) and a **confidential** one
(the actual original text, for internal reviewers or a dispute-resolution process —
never meant to leave the secure zone). See `run_demo.py` for a full worked report
going through all three rule types plus the semantic stub below.

## Semantic layer — an interface, not a working detector

Deciding whether an *unmarked* paragraph contains dangerous technical uplift isn't
pattern matching, it's judgment — which means it needs an LLM, and I don't have a
live model call available in this sandboxed execution. Rather than fake it, the
pipeline defines the interface a real one would fill (`semantic_flagger: paragraph ->
category | None`, called only on paragraphs no structural rule already caught) and
ships an explicitly-labeled `StubKeywordSemanticFlagger` that does nothing but
substring matching, used only to test that the plumbing works.

The demo makes the gap vivid on purpose: the stub is configured to flag the trigger
word "banana," and it dutifully redacts a paragraph about restocking the office
banana supply — a keyword matcher can't tell "banana" the concerning word from
"banana" the fruit, which is exactly why this layer needs real understanding, not a
bigger keyword list. A real implementation replaces the stub with a call like: *"Does
this paragraph disclose unpatched vulnerability details, specific dangerous-capability
elicitation results, or information a competitor could use to reproduce non-public
research, that isn't already covered by an author marker? Answer with a category or
'none.'"* — same interface, same call site, real judgment behind it.

## A bug the tests actually caught

First implementation of author markers recorded the *entire* `<<SENSITIVE:category>>
...<<END>>` span — delimiters included — as the "original text" in the confidential
manifest, instead of just the sensitive content between them. `test_confidential_manifest_hash_matches_original_span`
failed immediately, because the hash of "exact payload" didn't match the hash of
"<<SENSITIVE:secret>>exact payload<<END>>". Fixed by capturing the inner group
separately from the outer span used for text replacement. Leaving this in the README
rather than quietly fixing it — it's the concrete case for why the test suite exists
at all, not just a formality.

## Running it

```
python3 run_demo.py                    # full worked report, both manifests
python3 -m pytest test_redactor.py -v  # 12 tests
```

## What this does not do

No semantic understanding, by design and by disclosure, not by oversight. No
handling of sensitive information that's implied across *multiple* paragraphs but
not present in any single one. No defense against an author who simply doesn't mark
something they should have — structural rules only catch what markers, watchlists,
or patterns are configured to catch; the semantic layer is the backstop for
everything else, and right now that backstop is an interface waiting for a real
implementation, not one.
