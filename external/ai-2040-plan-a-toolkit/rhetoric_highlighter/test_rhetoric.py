import pytest
from .rhetoric import (
    analyze, detect_bandwagon, detect_unsourced_authority, detect_loaded_language,
    detect_absolutist_language, detect_false_urgency, detect_repetition, Span,
)
from .render import render_html, _non_overlapping
from .run_demo import NEUTRAL, MANIPULATIVE, FALSE_POSITIVE_URGENT_BUT_REAL, FALSE_NEGATIVE_CALM_BUT_ONE_SIDED


def test_neutral_text_gets_no_flags():
    result = analyze(NEUTRAL)
    assert result["total_flags"] == 0


def test_bandwagon_detector_fires():
    spans = detect_bandwagon("Everyone knows this policy is correct.")
    assert len(spans) == 1
    assert spans[0].category == "bandwagon"


def test_unsourced_authority_fires_without_nearby_source():
    spans = detect_unsourced_authority("Studies show this approach works best for everyone.")
    assert len(spans) == 1
    assert spans[0].category == "unsourced_authority"


def test_unsourced_authority_does_not_fire_with_nearby_named_source():
    text = "A 2021 study from Stanford University shows this approach reduces costs."
    # rephrase to hit the trigger phrase with a source right next to it
    text2 = "Studies show, according to Stanford University researchers, that this works."
    spans = detect_unsourced_authority(text2)
    assert len(spans) == 0


def test_unsourced_authority_does_not_fire_with_year_citation_nearby():
    text = "Research shows (Nguyen 2020) that participation increased significantly."
    spans = detect_unsourced_authority(text)
    assert len(spans) == 0


def test_loaded_language_detects_both_negative_and_positive():
    spans = detect_loaded_language("The radical proposal ignores common sense entirely.")
    categories = [s.technique for s in spans]
    assert "Name-Calling" in categories
    assert "Glittering Generalities" in categories


def test_absolutist_language_fires_on_multiple_markers():
    spans = detect_absolutist_language("This always works and it will never fail anyone.")
    assert len(spans) >= 2


def test_false_urgency_fires():
    spans = detect_false_urgency("Act now before it's too late to change anything.")
    assert len(spans) >= 1


def test_repetition_requires_at_least_three_occurrences():
    two_times = "We must act together. We must act together on other things too."
    spans_two = detect_repetition(two_times, min_repeats=3)
    assert spans_two == []

    three_times = "We must act together. Later, we must act together again. Finally, we must act together once more."
    spans_three = detect_repetition(three_times, min_repeats=3)
    assert len(spans_three) == 3  # three occurrences of the flagged phrase


def test_repetition_longest_match_does_not_double_flag_subphrases():
    text = ("This is a very important issue for everyone. "
            "This is a very important issue for the town. "
            "This is a very important issue, full stop.")
    spans = detect_repetition(text, min_words=3, max_words=8, min_repeats=3)
    # the long shared prefix should be flagged as ONE phrase-length, not also
    # separately flagged at every shorter sub-length within the same span
    starts = sorted(s.start for s in spans)
    assert len(starts) == len(set(starts))  # no duplicate start positions from nested lengths


def test_honest_false_positive_case_triggers_urgency_only():
    """A real emergency notice should trip the surface urgency pattern --
    that's the honest limitation, not a bug -- but shouldn't trip the
    lexicon-based categories that require actual loaded/absolutist wording,
    which a well-written emergency notice won't contain."""
    result = analyze(FALSE_POSITIVE_URGENT_BUT_REAL)
    assert result["counts"].get("false_urgency", 0) >= 1
    assert result["counts"].get("loaded_language", 0) == 0
    assert result["counts"].get("bandwagon", 0) == 0


def test_honest_false_negative_case_gets_zero_flags():
    """Card Stacking -- calm, selective, no loaded surface language -- should
    evade every detector here. This is the headline limitation, verified,
    not just claimed."""
    result = analyze(FALSE_NEGATIVE_CALM_BUT_ONE_SIDED)
    assert result["total_flags"] == 0


def test_manipulative_example_trips_every_category():
    result = analyze(MANIPULATIVE)
    expected_categories = {
        "bandwagon", "unsourced_authority", "loaded_language",
        "absolutist_language", "false_urgency", "repetition",
    }
    assert expected_categories.issubset(result["counts"].keys())


def test_non_overlapping_resolution_keeps_first_and_drops_overlap():
    spans = [
        Span(0, 10, "a", "A", "first"),
        Span(5, 15, "b", "B", "overlaps first"),
        Span(20, 25, "c", "C", "no overlap"),
    ]
    kept = _non_overlapping(spans)
    assert len(kept) == 2
    assert kept[0].start == 0 and kept[1].start == 20


def test_render_html_includes_all_category_labels_and_counts():
    result = analyze(MANIPULATIVE)
    out = render_html(MANIPULATIVE, result, title="test")
    assert "Bandwagon" in out
    assert "Repetition" in out
    assert str(result["total_flags"]) in out


def test_render_html_does_not_crash_on_empty_text():
    result = analyze("")
    out = render_html("", result, title="empty")
    assert "<html>" in out
