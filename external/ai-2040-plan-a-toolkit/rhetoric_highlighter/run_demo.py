from .rhetoric import analyze
from .render import render_html

# All examples concern a fictional town's recycling ordinance -- deliberately
# low-stakes and invented, so the point is the rhetorical pattern, not any
# real dispute or any real person's or party's position.

NEUTRAL = """The town council will vote on Ordinance 14-B next Tuesday, which would
require curbside sorting of recyclables starting in March. The public works
department estimates the program would cost the town approximately $80,000
per year to administer, based on figures from three neighboring towns that
adopted similar programs between 2019 and 2022. Residents who want to comment
can attend the public session on Thursday or submit written feedback by mail."""

MANIPULATIVE = """Everyone knows the so-called "recycling reform" is really just
another money grab dressed up as common sense. Studies show mandatory sorting
programs always fail within five years, and any reasonable person can see this
is a scam. This corrupt council wants your money -- act now before it's too
late, because once this radical program passes, it will never be reversed.
Real taxpayers deserve better. Call the council today. Call the council today
and tell them no. Don't wait one more day -- call the council today, before
Tuesday's vote."""

FALSE_POSITIVE_URGENT_BUT_REAL = """URGENT: Gas leak reported on Elm Street between
3rd and 5th Avenue. Evacuate the area immediately. Do not use light switches,
phones, or any device that could create a spark. Leave doors open behind you
as you exit. This is not a drill. Call 911 once you are at a safe distance.
Do not return to the area until the fire department confirms it is safe."""

FALSE_NEGATIVE_CALM_BUT_ONE_SIDED = """The proposed ordinance would introduce
mandatory sorting bins at every residence. The public works director noted in
last month's session that the administrative cost is estimated at $80,000
annually, funded through a modest increase in the sanitation fee. Some
residents have raised concerns about the added weekly sorting task. The
council will hear public comment before the vote."""
# (Note: this omits the diversion-rate and landfill-cost figures that were
# also part of that same session -- a real Card Stacking move, selectively
# quoting the cost side of a genuinely two-sided discussion, without a
# single "loaded" word anywhere in it.)


if __name__ == "__main__":
    examples = [
        ("neutral", NEUTRAL, "Baseline: neutral local news item"),
        ("manipulative", MANIPULATIVE, "Clear case: propaganda-style rhetoric"),
        ("false_positive", FALSE_POSITIVE_URGENT_BUT_REAL, "Honest false positive: real emergency, not manipulation"),
        ("false_negative", FALSE_NEGATIVE_CALM_BUT_ONE_SIDED, "Honest false negative: calm selective framing (Card Stacking)"),
    ]

    for key, text, label in examples:
        result = analyze(text)
        print(f"\n=== {label} ===")
        print(f"  total_flags={result['total_flags']}  per_1000_words={result['flags_per_1000_words']:.1f}")
        print(f"  by category: {result['counts']}")
        html_out = render_html(text, result, title=label)
        fname = f"example_{key}.html"
        with open(fname, "w") as f:
            f.write(html_out)
        print(f"  saved {fname}")
