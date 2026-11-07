from track3_bound import compute_track3_bound


def test_open_population_stays_unknown():
    result = compute_track3_bound(
        population_closed=False,
        sites=[{
            "site_id": "s1",
            "declared_accelerators": 100,
            "independent_capacity_estimates": {"power": 120},
        }],
    )
    assert result["status"] == "UNKNOWN"
    assert result["global_upper_bound_accelerators"] is None


def test_closed_population_produces_conservative_site_bound():
    result = compute_track3_bound(
        population_closed=True,
        sites=[
            {"site_id": "s1", "declared_accelerators": 100, "independent_capacity_estimates": {"power": 120, "cooling": 115}},
            {"site_id": "s2", "declared_accelerators": 50, "independent_capacity_estimates": {"power": 55}},
        ],
        untraced_pool_units=0,
    )
    assert result["status"] == "PASS"
    assert result["site_upper_bound_accelerators"] == 25
    assert result["global_upper_bound_accelerators"] == 25


def test_missing_site_evidence_blocks_numeric_global_bound():
    result = compute_track3_bound(
        population_closed=True,
        sites=[
            {"site_id": "s1", "declared_accelerators": 100, "independent_capacity_estimates": {"power": 120}},
            {"site_id": "s2", "declared_accelerators": 50, "independent_capacity_estimates": {}},
        ],
    )
    assert result["status"] == "UNKNOWN"


def test_tail_bound_is_added_only_when_sampling_inputs_are_complete():
    result = compute_track3_bound(
        population_closed=True,
        sites=[{"site_id": "s1", "declared_accelerators": 100, "independent_capacity_estimates": {"power": 120}}],
        tail_compute_units=1000,
        tail_sample_size=100,
        tail_failures=0,
        untraced_pool_units=0,
    )
    assert result["status"] == "PASS"
    assert result["global_upper_bound_accelerators"] > 20
    assert result["tail_sampling"]["upper_failure_rate"] > 0


def test_missing_untraced_pool_blocks_numeric_bound():
    result = compute_track3_bound(
        population_closed=True,
        sites=[{"site_id": "s1", "declared_accelerators": 100, "independent_capacity_estimates": {"power": 120}}],
    )
    assert result["status"] == "UNKNOWN"
    assert result["global_upper_bound_accelerators"] is None


def test_untraced_pool_is_added_in_full():
    result = compute_track3_bound(
        population_closed=True,
        sites=[{"site_id": "s1", "declared_accelerators": 100, "independent_capacity_estimates": {"power": 120}}],
        untraced_pool_units=7,
    )
    assert result["global_upper_bound_accelerators"] == 20 + 7
