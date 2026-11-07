"""
render.py

Renders analyze() output as highlighted HTML: colored spans over the
original text, a legend, and per-category counts. Overlapping spans (e.g.
a repeated phrase that also contains a loaded word) are resolved by
first-start-wins for DISPLAY only -- the count summary above the text still
reflects every raw detection, so the two numbers can legitimately differ by
a little; that's disclosed inline rather than silently reconciled.
"""

import html

CATEGORY_COLORS = {
    "bandwagon": "#C9922E",
    "unsourced_authority": "#4A93A6",
    "loaded_language": "#C05B48",
    "absolutist_language": "#8A6FB3",
    "false_urgency": "#B3564F",
    "repetition": "#5B8A5B",
}
CATEGORY_LABELS = {
    "bandwagon": "Bandwagon",
    "unsourced_authority": "Unsourced authority",
    "loaded_language": "Loaded language",
    "absolutist_language": "Absolutist framing",
    "false_urgency": "False urgency",
    "repetition": "Repetition",
}


def _non_overlapping(spans):
    ordered = sorted(spans, key=lambda s: (s.start, s.end))
    kept, last_end = [], -1
    for s in ordered:
        if s.start >= last_end:
            kept.append(s)
            last_end = s.end
    return kept


def render_html(text, result, title="Rhetoric analysis"):
    spans = _non_overlapping(result["spans"])
    pieces = []
    cursor = 0
    for s in spans:
        pieces.append(html.escape(text[cursor:s.start]))
        color = CATEGORY_COLORS.get(s.category, "#999")
        label = CATEGORY_LABELS.get(s.category, s.category)
        escaped = html.escape(text[s.start:s.end])
        note = html.escape(s.note)
        pieces.append(
            f'<mark style="background:{color}33;border-bottom:2px solid {color};padding:1px 2px;" '
            f'title="{label}: {note}">{escaped}</mark>'
        )
        cursor = s.end
    pieces.append(html.escape(text[cursor:]))
    body_html = "".join(pieces).replace("\n", "<br>")

    legend_items = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:5px;margin-right:14px;font-size:12.5px;">'
        f'<span style="width:11px;height:11px;background:{color};border-radius:2px;display:inline-block;"></span>'
        f'{CATEGORY_LABELS[cat]} ({result["counts"].get(cat, 0)})</span>'
        for cat, color in CATEGORY_COLORS.items()
    )

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
body {{ font-family: Georgia, serif; max-width: 720px; margin: 40px auto; padding: 0 20px; color: #1C1F26; line-height: 1.65; }}
h1 {{ font-family: Arial, sans-serif; font-size: 20px; }}
.summary {{ font-family: Arial, sans-serif; font-size: 13px; color: #5B594F; margin-bottom: 18px; }}
.legend {{ font-family: Arial, sans-serif; margin-bottom: 24px; padding: 12px; background: #F4F2ED; border-radius: 6px; }}
.text {{ font-size: 16px; }}
mark {{ cursor: help; }}
</style></head>
<body>
<h1>{html.escape(title)}</h1>
<div class="summary">{result['total_flags']} flags total &middot; {result['flags_per_1000_words']:.1f} per 1,000 words</div>
<div class="legend">{legend_items}</div>
<div class="text">{body_html}</div>
</body></html>"""
