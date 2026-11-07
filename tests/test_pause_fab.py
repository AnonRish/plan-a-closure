import math

import pytest

from closure.pause import fab as F


def test_sampling_detection_matches_paper():
    # section 5.3.2: 2400 chips a year, one in four inspections recognises an illicit chip, 1% diverted, six months
    assert F.p_detect(1200, 0.01, 0.25) == pytest.approx(0.95, abs=0.001)
    assert F.p_detect(1200, 0.01, 0.25) == pytest.approx(1 - math.exp(-3), abs=0.001)      # the Poisson(3) approximation
    assert F.p_detect(0, 0.01, 0.25) == 0.0 and F.p_detect(1000, 0.0, 0.25) == 0.0
    assert F.p_detect(1000, 0.02, 0.25) > F.p_detect(1000, 0.01, 0.25)


def test_min_detectable_and_months():
    n = F.samples_needed(0.01, 0.25, 0.95)
    assert n == 1197 and F.p_detect(n, 0.01, 0.25) >= 0.95 > F.p_detect(n - 1, 0.01, 0.25)
    assert F.months_to_detect(2400, 0.01, 0.25) == pytest.approx(6.0, abs=0.05)
    f = F.min_detectable_diversion(1200, 0.25, 0.95)
    assert f == pytest.approx(0.01, rel=0.01) and F.p_detect(1200, f, 0.25) == pytest.approx(0.95)


def test_reconcile_fab_flags_unlogged_wafers_and_missing_dies():
    ok = F.reconcile_fab(F.FabPeriod(1000, 10, 990, 600, 590_000, 4_000))
    assert ok["balanced"] and ok["missing_dies"] == 0 and ok["unlogged_wafers"] == 0
    # 15 wafers left the blank stock without a logged print or a witnessed scrap: an undeclared machine?
    r = F.reconcile_fab(F.FabPeriod(1000, 10, 975, 600, 585_000, 0))
    assert not r["balanced"] and r["unlogged_wafers"] == 15 and any("wafers" in f for f in r["findings"])
    # a lot of dies missing from the shipped and destroyed counts: diversion
    d = F.reconcile_fab(F.FabPeriod(1000, 0, 1000, 600, 590_000, 0))
    assert d["missing_dies"] == 10_000 and any("dies" in f for f in d["findings"])
    # more shipped than the prints can make is also a finding
    inflated = F.reconcile_fab(F.FabPeriod(1000, 0, 1000, 600, 601_000, 0))
    assert inflated["missing_dies"] == -1000 and not inflated["balanced"]
    # work in process carries over between periods
    assert F.reconcile_fab(F.FabPeriod(1000, 0, 1000, 600, 600_000, 0, wip_start=0, wip_end=0))["balanced"]
    assert F.reconcile_fab(F.FabPeriod(1000, 0, 1020, 600, 612_000, 0, wip_start=30, wip_end=10))["balanced"]


def test_consumable_balance():
    ok = F.consumable_balance(received=1000, used_per_wafer=1.0, wafers_printed=980, waste_recorded=20)
    assert ok["balanced"] and ok["unexplained"] == pytest.approx(0)
    skim = F.consumable_balance(received=1100, used_per_wafer=1.0, wafers_printed=980, waste_recorded=20)
    assert not skim["balanced"] and skim["unexplained_wafers"] == pytest.approx(100)    # about 100 wafers' worth printed unseen
    assert F.consumable_balance(1000, 1.0, 1000, inventory_start=5, inventory_end=5)["balanced"]


def test_custody_and_litho_reconciliation():
    c = F.custody_balance({"L1", "L2", "L3", "L4"}, installed={"L1", "L2"}, returned={"L2", "L3"}, ghost={"Z"})
    assert c["unaccounted"] == ["L4"] and c["double_counted"] == ["L2"] and c["unknown"] == ["Z"]
    r = F.reconcile_litho(registered={"M1", "M2"}, delivered={"M1", "M2", "M3"}, serviced={"M2", "M4"})
    assert r["delivered_unregistered"] == ["M3"] and r["serviced_unregistered"] == ["M4"]
    assert r["dark_candidates"] == ["M3", "M4"] and r["registered_without_delivery_record"] == []
    forged = F.reconcile_litho(registered={"M1", "M9"}, delivered={"M1"})
    assert forged["registered_without_delivery_record"] == ["M9"]


def test_litho_dark_source():
    assert F.dark_stock_after(1, 1) == 24_000 and F.dark_stock_after(2, 12, 38_000) == 912_000
    s = F.litho_dark_source(2, 12, high=True)
    assert s.k0 == 912_000 and s.k_e == s.k0 and s.k_b == s.k0                  # a covert line's chips are fully usable
    assert F.litho_dark_source(1, 6).k0 < F.litho_dark_source(1, 6, high=True).k0
