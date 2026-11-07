# Rhetoric-technique highlighter

AI for Epistemics wants tooling that flags manipulative rhetoric. "Manipulative" is
a judgment call — an LLM could make it; pattern-matching can't, honestly. What
pattern-matching *can* do is flag specific, named, surface-level techniques from a
real framework, and be upfront about which techniques in that same framework it
structurally cannot touch.

## The framework

The Institute for Propaganda Analysis's seven techniques (1937, *The Fine Art of
Propaganda*) — a real, citable, 88-year-old piece of media-literacy scholarship, not
seven categories I invented for this. Four have a surface signature:

- **Bandwagon** — "everyone knows," "no one disputes"
- **Testimonial** (unsourced form) — "experts say," "studies show," with no
  specific, checkable source nearby
- **Name-Calling** / **Glittering Generalities** — pejorative or glowing words
  chosen for charge over precision

Three don't, and this tool says so rather than pretending otherwise:

- **Card Stacking** — selective use of *true* facts. Needs fact-checking against
  what was left out, not text analysis of what's present.
- **Transfer** — borrowing a respected symbol's authority. Needs entity recognition
  plus cultural knowledge of what a given audience considers respected.
- **Plain Folks** — a speaker performing ordinariness. Needs to know who's speaking
  and to whom.

Plus two general signals with real (if contested) literature behind them:
**absolutist language** ("always," "never," "everyone") and **false urgency**
("act now," "before it's too late"). Repetition of a phrase for emphasis is its own
classic propaganda technique, and the one signal here that's pure structure — n-gram
counting, no lexicon at all.

**On the word lists**: self-constructed for this tool, not lifted from a validated
academic lexicon I'd need to cite precisely. Saying so plainly, on a tool whose whole
subject is unsourced authority claims, matters more here than almost anywhere else
in this set.

## Four real results, not cherry-picked

| Text | Flags | Categories triggered |
|---|---|---|
| Neutral council announcement | 0 | none |
| Deliberately manipulative version, same topic | 15 (166.7/1000 words) | all six |
| Real emergency notice ("gas leak, evacuate now") | 1 | false_urgency only |
| Calm, selectively-framed version (Card Stacking) | **0** | **none** |

## The two findings that matter more than the working case

**The false positive**: a genuine gas-leak evacuation notice trips the urgency
detector, because "evacuate immediately" and "this is not a drill" are surface-
identical to manipulative urgency pressure. The tool cannot distinguish real
urgency from performed urgency — it only sees the pattern. A pattern-matcher that
flagged every real emergency notice as "manipulative" would be actively harmful if
deployed carelessly; this is disclosed, not discovered by a user the hard way.

**The false negative**: the Card Stacking example — same underlying facts as the
neutral version, but reporting only the cost figure from a public session that also
covered projected landfill savings — gets **zero flags**. No loaded words, no
absolutist claims, nothing repeated. Perfectly calm, perfectly one-sided, completely
invisible to every detector in this file. This is arguably the more common form of
real-world misleading writing, and it's exactly the gap the "not detectable" section
above predicts — verified with a constructed case, not just asserted.

## Running it

```
python3 run_demo.py              # analyzes all four texts, writes 4 HTML files
python3 -m pytest test_rhetoric.py -v   # 16 tests
```

Open any `example_*.html` in a browser for the highlighted view — hover a highlight
for which technique and why.

## What this does not do

Three of the seven classic techniques, by design (see above). No semantic
understanding — it cannot tell a real emergency from a performed one, sincere
conviction from manufactured outrage, or satire from the thing it's satirizing. No
weighting by real-world harm — a flagged absolutist word in an exaggerated joke
counts the same as one in a targeted lie. The lexicons are English-only, US-register,
and nowhere near exhaustive. This is a first-pass surface scanner, not an
arbiter of what's manipulative — and the false-negative case above is the honest
argument for why a real deployment needs a second, semantic layer behind this one,
same conclusion as the redaction pipeline's "About the semantic layer" a few pieces
back in this set.
