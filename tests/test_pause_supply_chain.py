import pytest

from closure.pause import supply_chain as S
from closure.pause import treaty_ledger as TL

BASE = S.PARTICIPANTS_3_1


def _transitional(led):
    return next(x for x in led.lines() if x["name"] == "transitional service")


def test_paper_coalition_controls_every_listed_stage():
    assert S.uncovered(BASE) == []
    assert S.minimum_coalition() <= S.expand(BASE)                      # the paper's list contains everything the table needs
    assert S.expand(["European Union"]) == {"European Union", "Netherlands", "Germany"}
    assert S.expand(["Japan"]) == {"Japan"}


def test_each_departure_opens_the_stages_the_paper_describes():
    crit = S.critical_members(BASE)
    assert {"EUV lithography machines", "EUV optics and precision mirrors"} <= set(crit["European Union"])
    assert crit["Japan"] == ["DUV (ArF immersion) lithography machines", "EUV coater/developer"]
    assert crit["Taiwan"] == ["leading-edge foundry and advanced packaging"]
    assert "high-bandwidth memory" in crit["South Korea"]
    assert "refined magnet rare earths" in crit["China"] and "high-purity quartz" in crit["United States"]
    # the UK has no hardware leverage in the paper's table (it matters for other reasons); every other member does
    assert crit["United Kingdom"] == [] and [m for m, v in crit.items() if not v] == ["United Kingdom"]


def test_a_single_outside_supplier_is_a_leak():
    without_japan = [m for m in BASE if m != "Japan"]
    u = {x["stage"]: x for x in S.uncovered(without_japan)}
    assert u["DUV (ArF immersion) lithography machines"]["outside"] == ["Japan"]       # ASML alone is not enough: Nikon sells too
    assert "EUV lithography machines" not in u                                         # EUV is ASML's alone
    assert S.uncovered(list(BASE) + ["Singapore"]) == []                               # a non-supplier changes nothing
    assert len(S.uncovered(["United States", "China"])) >= 5                           # a bilateral deal leaves most stages open


def test_census_gaps():
    g = S.census_gaps(BASE)
    assert g["census_transit"] == ["Singapore", "Malaysia", "United Arab Emirates"]    # Taiwan is already in
    assert set(g["stock_hosts"]) == set(S.STOCK_HOSTS)
    assert S.census_gaps(list(BASE) + list(S.STOCK_HOSTS)) == {"stock_hosts": [], "census_transit": []}


def test_table_6_1_ranges_move_the_transitional_line():
    lo, hi = TL.TABLE_6_1["United States"][1]
    share = lambda stock: _transitional(TL.section_6_4("United States", "high", stock=stock))["share_B"]
    assert share(lo) == pytest.approx(0.148, abs=0.002)
    assert share(hi) == pytest.approx(0.25, abs=0.002)            # at the top of the paper's range the line uses the whole allowance
    assert share(lo) < share(35e6) < share(hi)
    assert _transitional(TL.section_6_4("United States", "high"))["share_B"] == pytest.approx(0.2005, abs=0.0005)   # default unchanged
    full = next(x for x in TL.section_6_4("China", "high").lines() if x["name"] == "inference-only fleet")["K_B"]
    half = next(x for x in TL.section_6_4("China", "high", world_fleet=TL.WORLD_FLEET_YE2026 / 2).lines()
                if x["name"] == "inference-only fleet")["K_B"]
    assert half == pytest.approx(full / 2)                         # world fleet scales the inference demand served
    assert TL.TABLE_6_1["world"][0] == 47e6 and TL.TABLE_6_1["China"][1] == (2.6e6, 4.5e6)
