from closure import claims as C
from closure import retrofit as R


def test_packet_math_identities():
    for n in (1, 10, 100, 1000):
        assert abs(C.p_undetected(C.budget_exact(n, 0.99), n) - 0.01) < 1e-12
        assert abs(1 - C.p_detect_poisson(C.budget_poisson(n, 0.99), n) - 0.01) < 1e-12
    assert C.budget_poisson(1, 0.99) > 1.0                       # Poisson breaks down for a single fake packet
    assert C.budget_exact(1000, 0.99) < C.budget_poisson(1000, 0.99)
    assert abs(C.rogue_work_bound(100, 0.01) - 46_052) < 5


def test_all_claims_reproduce_except_flagged():
    cs = C.check_all()
    s = C.summary(cs)
    assert s["total"] == len(cs) >= 50
    assert {c.id for c in cs if c.status == "INCONSISTENT"} == {"U.definition"}
    assert {c.id for c in cs if c.status == "WORDING"} == {"D.cover_world", "T.zdr", "A42.pool"}


def test_retrofit_schedule_matches_plan():
    cn_on_us = R.schedule(200_000, 20_000, 10_000, 6)
    us_on_cn = R.schedule(100_000, 10_000, 10_000, 6)
    assert [round(x[2], 2) for x in cn_on_us[:4]] == [0.40, 0.60, 0.80, 1.00]
    assert [round(x[2], 2) for x in us_on_cn[:3]] == [0.40, 0.80, 1.00]
    prop = R.proportional(cn_on_us, us_on_cn)
    assert prop[0][1] == 0.4 and prop[2][1] == 0.8                 # the plan's 40% (month 1) and 80% (month 3)
    capped = R.schedule(200_000, 20_000, 10_000, 4, install_cap_units_per_month=5_000)
    assert [x[1] for x in capped] == [5_000, 10_000, 15_000, 20_000]
