import math

import pytest

from closure.pause import thresholds as T
from closure.pause import treaty_ledger as TL


def _line(led, name, durable=False):
    return next(x for x in led.lines(durable) if x["name"] == name)


def test_section_6_4_lines_match_reference_values():
    us, cn = TL.section_6_4("United States", "high"), TL.section_6_4("China", "high")
    # headroom in orders of magnitude, from the authors' line table
    ref = {("us", "transitional service", "E"): 1.66, ("cn", "transitional service", "E"): 1.71,
           ("us", "inference-only fleet", "E"): 3.71, ("us", "consumer GPUs", "E"): 2.72,
           ("us", "sovereign supercomputer (El Capitan scale)", "E"): 2.24, ("us", "dark compute", "E"): 2.346,
           ("us", "transitional service", "B"): 0.096, ("cn", "transitional service", "B"): 1.15,
           ("us", "inference-only fleet", "B"): 2.15, ("us", "consumer GPUs", "B"): 2.76,
           ("us", "sovereign supercomputer (El Capitan scale)", "B"): 2.98}
    for (who, name, which), want in ref.items():
        led = us if who == "us" else cn
        assert _line(led, name)[f"headroom_{which}_oom"] == pytest.approx(want, abs=0.011), (who, name, which)
    assert _line(us, "transitional service")["K_E"] == pytest.approx(35_200, rel=0.002)
    assert _line(us, "inference-only fleet")["K_B"] == pytest.approx(313_000, rel=0.002)
    assert _line(us, "dark compute")["K_E"] == pytest.approx(7_190, rel=0.01)     # 0.5 * 1.2 * K_M


def test_headroom_per_line_vs_summed():
    led = TL.section_6_4("United States", "high")
    h = led.headroom(durable=True)
    assert h["binding_E"] == "sovereign supercomputer (El Capitan scale)"
    assert h["E_line_oom"] == pytest.approx(2.24, abs=0.011)
    assert h["E_sum_oom"] < h["E_line_oom"]                  # adding the lines always costs headroom
    assert h["E_sum_oom"] == pytest.approx(1.91, abs=0.02)
    assert h["B_sum_oom"] == pytest.approx(2.0, abs=0.02)
    # one dominant line: the sum is close to the line
    big = TL.Ledger("x", 1e6, 1e6).add(TL.Source("a", 1000.0)).add(TL.Source("b", 1.0))
    assert big.headroom()["E_sum_oom"] - big.headroom()["E_line_oom"] < 0.001


def test_certify_and_erosion():
    led = TL.section_6_4("United States", "high")
    assert led.certify(1.0, durable=True)["ok_E"] and led.certify(1.0, durable=True)["ok_B"]
    assert led.certify(1.0, durable=False)["ok_B"]                     # transitional service only just fits at the pause date...
    assert not led.certify(1.3, durable=False)["ok_B"]                 # ...and 30% of erosion breaks it ("almost no headroom", 6.4.2)
    assert not led.certify(4.0, durable=False)["ok_B"]                 # two doublings of training-efficiency gains
    assert not led.certify(100.0, durable=True)["ok_E"]                # just short of two orders of magnitude (1.91)
    assert led.certify(50.0, durable=True)["ok_E"]
    c = led.certify(2.0, durable=True)
    assert c["allow_E"] == pytest.approx(0.25 * led.f_e / 2)


def test_years_of_durability():
    led = TL.section_6_4("United States", "high")
    years = led.years_of_durability(1.57, durable=True)
    assert years == pytest.approx(1.91 / math.log10(1.57), rel=0.02) and 9.0 < years < 10.0


def test_max_licensed_is_the_binding_budget():
    led = TL.section_6_4("United States", "high")
    name = "sovereign supercomputer (El Capitan scale)"
    k = led.max_licensed(name, durable=True)
    src = next(s for s in led.sources if s.name == name)
    src.k0 = k                                                          # license exactly the budget
    c = led.certify(1.0, durable=True)
    assert (c["ok_E"] and c["ok_B"]) and min(c["allow_E"] - c["L_E"], c["allow_B"] - c["L_B"]) == pytest.approx(0, abs=1e-6 * c["allow_B"])
    src.k0 = k * 1.01
    c = led.certify(1.0, durable=True)
    assert not (c["ok_E"] and c["ok_B"])
    assert led.max_licensed(name, erosion=1e6, durable=True) == 0.0    # already over: nothing left to license


def test_allowance_schedule():
    assert TL.allowance(0.0) == 1.0 and TL.allowance(1.0) == pytest.approx(0.25) and TL.allowance(5.0) == pytest.approx(0.25)
    assert TL.allowance(0.5) == pytest.approx(0.5)                     # geometric: halfway in log space
    assert TL.allowance(-1.0) == 1.0


def test_strategic_reserve_and_preserve_lines():
    r = TL.strategic_reserve(1e6)
    assert r.k_e == 0.0 and r.k_b == 1e6                               # off under seal: no covert use, full overt exposure
    assert TL.scientific_preserve(5e5).k_b == 0.0 and TL.scientific_preserve(5e5, neutral_host=False).k_b == 5e5


def test_offshore_removes_breakout_exposure_only():
    led = TL.section_6_4("United States", "high")
    before = _line(led, "transitional service")
    TL.offshore(led, "transitional service", 0.5)
    after = _line(led, "transitional service")
    assert after["K_B"] == pytest.approx(before["K_B"] / 2) and after["K_E"] == before["K_E"]


def test_scenarios_order_the_dark_compute_line():
    sizes = {sc: _line(TL.section_6_4("China", sc), "dark compute")["K_E"] for sc in ("high", "low", "non_deniable")}
    assert sizes["high"] < sizes["low"] < sizes["non_deniable"]
    assert TL.headroom_oom(0.0, 1e6, 0.25) == math.inf
    assert T.covert_evasion_fleet() == TL.section_6_4("China", "low").f_e
