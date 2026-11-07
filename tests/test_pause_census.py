import pytest

from closure.pause import census as C


def test_missing_fraction_chain():
    assert C.site_miss_fraction() == pytest.approx(0.16)
    assert C.missing_fraction("public") == 0.0
    assert C.missing_fraction("on_books") == pytest.approx(0.16 * 0.06 * 0.20)      # 0.19%
    assert C.missing_fraction("off_books") == pytest.approx(0.16 * 0.20 * 0.50)     # 1.6%
    assert C.missing_fraction("informal") == pytest.approx(0.10)
    # better anchors give a smaller miss: the chain is monotone in every link
    assert C.missing_fraction("on_books", out_of_dc=0.05) < C.missing_fraction("on_books")
    with pytest.raises(ValueError):
        C.missing_fraction("mystery")


def test_table_5_1_reproduces():
    t = C.table_5_1()
    us, cn = t["United States"], t["China"]
    assert us["K_M"] == pytest.approx(11_987, rel=0.005) and cn["K_M"] == pytest.approx(11_288, rel=0.005)
    assert us["functional_missing"] == pytest.approx(7_500, rel=0.01) and cn["functional_missing"] == pytest.approx(9_600, rel=0.01)
    assert us["failed_missing"] == pytest.approx(4_500, rel=0.02) and cn["failed_missing"] == pytest.approx(1_700, rel=0.02)
    # row arithmetic: totals are sums of rows, working chips are stock less failed
    for state in t.values():
        assert sum(r["total_missing"] for r in state["rows"]) == pytest.approx(state["K_M"])
        for r in state["rows"]:
            assert r["functional"] == pytest.approx(r["stock"] - r["failed"])
            assert r["total_missing"] == pytest.approx(r["failed_missing"] + r["mu"] * r["functional"])
    # the paper's bounds on unrecorded failures: 1-10% for owners with records, 50% off-books, all of it for individuals
    for h in C.TABLE_5_1["United States"] + C.TABLE_5_1["China"]:
        share = h.miss_failed / h.failed
        lo, hi = {"public": (0.01, 0.10), "on_books": (0.01, 0.10), "off_books": (0.5, 0.5), "informal": (1.0, 1.0)}[h.kind]
        assert lo - 1e-3 <= share <= hi + 1e-3, h.kind


def test_failure_model_vintages():
    assert C.cumulative_hazard(2.0) == pytest.approx(2 * C.FAIL_RATE["central"])
    assert C.cumulative_hazard(5.0) == pytest.approx(5 * 0.0045 + 0.5 * 0.03 * 4)        # rises after the warranty
    v = [(2020.5, 1e6), (2023.5, 2e6), (2026.5, 4e6)]
    total, late = C.failed_by_vintage(v, 2027.0)
    assert 0 < late < total < 7e6 * 0.05
    # only chips older than the warranty can fail late; a fleet bought yesterday has none
    assert C.failed_by_vintage([(2026.9, 1e6)], 2027.0)[1] == 0.0
    assert C.failed_by_vintage(v, 2027.0, rate=C.FAIL_RATE["high"])[0] > total
    # warranty failures are mostly recorded, late ones less so
    assert C.missing_failed("public", total, late) == pytest.approx(0.01 * (total - late) + 0.10 * late)
    assert C.missing_failed("off_books", 100.0) == 50.0 and C.missing_failed("informal", 100.0) == 100.0


def test_split_residual():
    us = C.split_residual(2135e3)
    assert us["on_books"] == pytest.approx(2114e3, rel=0.002) and us["informal"] == pytest.approx(35e3, rel=0.01)
    cn = C.split_residual(2379e3, diverted_stock=990e3)
    assert cn["off_books"] == pytest.approx(99e3) and cn["on_books"] == pytest.approx(2256e3, rel=0.002)
    assert sum(cn.values()) == pytest.approx(2379e3 + 13_750)                           # the half month of inventory is added


def test_dark_compute_scenarios():
    assert C.dark_compute(10_000, "United States", "high") == {"k0": 12_000.0, "pi": 0.5, "scenario": "high"}
    assert C.dark_compute(10_000, "United States", "low")["k0"] == 50_000 and C.dark_compute(10_000, "China", "low")["k0"] == 100_000
    nc = C.dark_compute(10_000, "China", "non_deniable")
    assert nc["k0"] == 1_000_000 and nc["pi"] == 1.0


def test_reconcile_documented_but_undeclared():
    declared = {"A", "B", "C", "D"}
    sources = {"customs": {"A", "B", "X"}, "vendor_sales": {"A", "C", "X", "Y"}, "tax_deduction": {"A", "B", "C"}}
    r = C.reconcile(declared, sources)
    assert r["documented_undeclared"] == ["X", "Y"]          # in records, never declared: first leads
    assert r["declared_undocumented"] == ["D"]               # declared, in no record
    # A in three records; B, C, X in two; Y in one: so f1 = 1 and f2 = 3
    assert r["n_sources"] == {"A": 3, "B": 2, "C": 2, "X": 2, "Y": 1}
    assert (r["f1"], r["f2"], r["n_documented"]) == (1, 3, 5)
    assert r["coverage_by_source"]["tax_deduction"] == pytest.approx(0.75)
    assert set(C.EVIDENCE_SOURCES) >= {"customs", "vendor_sales", "tax_deduction"} and len(C.EVIDENCE_SOURCES) == 13


def test_chao1_and_lincoln_petersen():
    assert C.chao1_unseen(10, 4) == pytest.approx(10 * 9 / (2 * 5))
    assert C.chao1_unseen(0, 0) == 0.0 and C.chao1_unseen(1, 0) == 0.0
    # two lists of 100 that share 50 chips imply about 200 in total
    assert C.lincoln_petersen(100, 100, 50) == pytest.approx(199.0, abs=3)
    assert C.lincoln_petersen(100, 100, 100) == pytest.approx(100.0, abs=1.5)


def test_buyback_budget():
    assert C.buyback_budget(25e6, 20e3, 1.0) == 500e9 and C.buyback_budget(25e6, 20e3, 2.0) == 1e12
