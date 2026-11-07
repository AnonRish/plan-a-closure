"""The Verification Plan's evaluation metrics as a checked scorecard (VP-2.8)."""
import json

import pytest

from closure import metrics as M
from closure.assurance import confidence_at_coverage
from closure.cli import main


def test_every_recorded_scorecard_is_complete_and_in_range():
    assert set(M.DEFINITIONS) == {"assurance_curve", "execution_difficulty", "preparation_required", "privacy_level",
                                  "economic_cost", "scope"}                  # the plan says five and lists six
    for c in M.CARDS:
        assert M.validate(c) == [], c.mechanism


def test_the_assurance_metric_is_the_plans_formula():
    c = M.CARDS[0]
    assert c.assurance(0.999) == pytest.approx(confidence_at_coverage(10_000, 0.999))
    assert M.Scorecard("x", 0, "low", 0, "none", 0, "supporting", "b").assurance() == 0.0


def test_bad_scorecards_are_refused():
    bad = M.Scorecard("bad", -1, "trivial", -2, "everything", 1.5, "all", " ")
    errs = M.validate(bad)
    assert len(errs) == 6


def test_metrics_cli(capsys):
    assert main(["metrics"]) == 0
    assert "economic cost" in capsys.readouterr().out
    assert main(["metrics", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == len(M.CARDS) and all("assurance_at_99.9pct" in r for r in rows)
