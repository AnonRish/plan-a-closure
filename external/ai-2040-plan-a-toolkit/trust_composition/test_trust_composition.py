from .trust_composition import TrustRoot, min_attack, resource_fanout, analyze


def test_no_shared_dependencies_needs_full_threshold():
    """Fully independent roots: hitting all 3 genuinely requires 3 resources."""
    roots = [TrustRoot("A", {"r1"}), TrustRoot("B", {"r2"}), TrustRoot("C", {"r3"})]
    size, hazard = min_attack(roots, threshold=3)
    assert size == 3
    assert hazard == {"r1", "r2", "r3"}


def test_single_shared_dependency_breaks_threshold():
    """One resource shared by all roots: a single compromise takes out all of them."""
    roots = [
        TrustRoot("A", {"shared", "a1"}),
        TrustRoot("B", {"shared", "b1"}),
        TrustRoot("C", {"shared", "c1"}),
    ]
    size, hazard = min_attack(roots, threshold=3)
    assert size == 1
    assert hazard == {"shared"}


def test_partial_overlap_needs_exactly_two():
    """A and B share 'x'; C is independent. Need x (covers A,B) plus C's own resource."""
    roots = [TrustRoot("A", {"x"}), TrustRoot("B", {"x"}), TrustRoot("C", {"y"})]
    size, hazard = min_attack(roots, threshold=3)
    assert size == 2
    assert hazard == {"x", "y"}


def test_lower_threshold_is_easier_to_hit():
    """Asking for only 2-of-3 should never need more resources than asking for 3-of-3."""
    roots = [TrustRoot("A", {"a"}), TrustRoot("B", {"b"}), TrustRoot("C", {"c"})]
    size2, _ = min_attack(roots, threshold=2)
    size3, _ = min_attack(roots, threshold=3)
    assert size2 <= size3


def test_empty_trust_roots_returns_none():
    size, hazard = min_attack([], threshold=1)
    assert size is None and hazard is None


def test_threshold_exceeding_root_count_is_unsatisfiable():
    roots = [TrustRoot("A", {"a"}), TrustRoot("B", {"b"})]
    size, hazard = min_attack(roots, threshold=5)
    assert size is None


def test_fanout_counts_match_dependency_membership():
    roots = [TrustRoot("A", {"x", "y"}), TrustRoot("B", {"x"}), TrustRoot("C", {"z"})]
    fanout = resource_fanout(roots)
    assert fanout == {"x": 2, "y": 1, "z": 1}


def test_analyze_reports_violation_verdict(capsys):
    roots = [
        TrustRoot("A", {"shared"}), TrustRoot("B", {"shared"}), TrustRoot("C", {"shared"}),
    ]
    result = analyze(roots, claimed_threshold=3, label="test")
    assert result["verdict"] == "violation"
    assert result["min_attack_size"] == 1


def test_analyze_reports_holds_verdict():
    roots = [TrustRoot("A", {"a"}), TrustRoot("B", {"b"}), TrustRoot("C", {"c"})]
    result = analyze(roots, claimed_threshold=3, label="test")
    assert result["verdict"] == "holds"
    assert result["min_attack_size"] == 3
