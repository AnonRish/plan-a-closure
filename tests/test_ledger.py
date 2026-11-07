import math

from closure import ledger as L


def test_combine_reduces_uncertainty():
    e = L.combine([L.Estimate(224.0, 2.0), L.Estimate(226.0, 2.0)])
    assert abs(e.mean - 225.0) < 1e-9 and abs(e.sd - 2.0 / math.sqrt(2)) < 1e-9
    w = L.combine([L.Estimate(100.0, 1.0), L.Estimate(110.0, 10.0)])           # precise estimate dominates
    assert abs(w.mean - 100.0) < 0.2 and w.sd < 1.0


def test_reconcile_flags_underdeclaration():
    est = [L.Estimate(224.0, 1.5)]
    ok = L.reconcile(224.0, est)
    assert ok["consistent"] and abs(ok["undeclared_upper_bound"] - 1.5 * L.Z90) < 1e-9
    bad = L.reconcile(220.0, est)
    assert not bad["consistent"] and bad["undeclared_upper_bound"] > 5.0
    lo, hi = L.Estimate(1.5, 1.95).ci80()                                    # plan: 1.5M best guess, 80% CI top ~4M
    assert abs(hi - 4.0) < 0.01 and lo < 0


def test_stock_ledger_accounting():
    led = L.StockLedger("US", L.Estimate(100.0, 1.0))
    led.add(L.Event("production", 50, 2.0))
    led.add(L.Event("shipment_out", 20, 1.0))
    led.add(L.Event("death", 5, 0.5))
    s = led.stock()
    assert s.mean == 125.0 and abs(s.sd - math.sqrt(1 + 4 + 1 + 0.25)) < 1e-12


def test_audit_sample_size_hypergeometric():
    n, b, conf = 100, 10, 0.99
    k = L.audit_sample_size(n, b, conf)
    miss = lambda kk: math.comb(n - b, kk) / math.comb(n, kk)
    assert miss(k) <= 1 - conf < miss(k - 1)                                  # minimal k
    assert L.audit_sample_size(100, 0) == 0 and L.audit_sample_size(10, 10) == 1
    assert L.audit_sample_size(1000, 1, 0.99) > 900                           # one bad site among many is hard to find


def test_bucket_and_tier_rules():
    assert L.bucket_intervention(1e6) == "inference-only retrofit"
    assert "spot checks" in L.bucket_intervention(500)
    assert L.bucket_intervention(1e3, consumer=True).startswith("intelligence")
    t = L.chip_tier(mem_capacity_tb=13, mem_bw_tbs=0.2)
    assert t["tier"] == 1 and t["exceeded"] == ["memory capacity"] and "compute" in t["thresholds_not_applied"]
    assert L.chip_tier(0.1, 0.1)["tier"] == 0
    t3 = L.chip_tier(0.1, 0.1, compute_h100e=5.0, th=L.ChipTierThresholds(compute_h100e=1.0))
    assert t3["tier"] == 1 and t3["exceeded"] == ["compute"]
