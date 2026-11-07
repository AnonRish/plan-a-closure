import math

from closure import assurance as A


def test_assurance_curve_matches_plan_formula():
    n = 10_000
    assert abs(A.confidence_at_coverage(n, 0.999) - (1 - math.exp(-10))) < 1e-12
    assert abs(A.coverage_at_confidence(n, 0.99) - (1 - math.log(100) / n)) < 1e-12
    confs = [c for _, c in A.assurance_curve(n)]
    assert all(a >= b for a, b in zip(confs, confs[1:]))            # more coverage demanded -> less confidence
    assert abs(A.nines(0.999) - 3.0) < 1e-9
    assert abs(A.n_verified(0.01, 100.0, 1e6) - 100.0) < 1e-9


def test_detection_time_and_granularity():
    assert abs(A.detection_time_hours(0.01, 100.0, 10_000) - 4.605) < 0.01      # plan: about 4.6 h
    assert abs(A.detection_time_hours(0.01, 100.0, 1_000) - 46.05) < 0.1        # plan: about 46 h
    assert A.GRANULARITY_H100E == {2030: 4000.0, 2032: 400.0, 2034: 100.0}
    t = [A.detection_time_hours(0.01, p, 10_000) for p in A.GRANULARITY_H100E.values()]
    assert t[0] > t[1] > t[2]                                                  # finer packets catch faster


def test_compose_independent_vs_correlated():
    ps = [0.9, 0.5, 0.2]
    ind, cor = A.compose(ps, 0.0), A.compose(ps, 1.0)
    assert abs(ind - (1 - 0.1 * 0.5 * 0.8)) < 1e-12 and abs(cor - 0.9) < 1e-12
    assert cor <= A.compose(ps, 0.5) <= ind
    assert abs(A.compose([0.3], 0.7) - 0.3) < 1e-12


def test_end_to_end_reports_both_bounds():
    r = A.end_to_end(1000.0, 100.0, 0.01, closure_p=0.5, state_p=0.1, rho=0.3)
    assert abs(r["layers"]["recompute"] - (1 - math.exp(-0.1))) < 1e-12
    assert r["independent"] >= r["assumed"] >= r["correlated"]
