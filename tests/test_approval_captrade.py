import pytest

from closure import approval as A
from closure import captrade as K
from closure.evidence import Chain


def _m(**kw):
    base = dict(workload_id="w1", code_sha256="code1", data_sha256=("d1",), techniques=frozenset({"safety_eval"}), flops=1e21)
    base.update(kw)
    return A.Manifest(**base)


def test_approval_stages_and_lists(tmp_path):
    assert A.approve(_m(), A.Policy(gold={"software": frozenset({"safety_eval"})})).approved
    d = A.approve(_m(), A.Policy(flops_cap=1e20))
    assert not d.approved and "exceeds cap" in d.reasons[0]
    assert not A.approve(_m(), A.Policy(technique_blacklist=frozenset({"safety_eval"}))).approved
    assert "required (gold)" in A.approve(_m(techniques=frozenset()), A.Policy(gold={"software": frozenset({"safety_eval"})})).reasons[0]
    ad = A.Policy(stage="ad_hoc", code_whitelist=frozenset({"code1"}), data_whitelist=frozenset({"d1"}))
    assert A.approve(_m(), ad).approved
    assert not A.approve(_m(data_sha256=("d1", "unknown")), ad).approved
    hi = A.Policy(stage="human_interpretable", code_whitelist=frozenset({"code1"}), data_whitelist=frozenset({"d1"}), min_reviewers=2)
    assert not A.approve(_m(reviewers=1), hi).approved and A.approve(_m(reviewers=2), hi).approved
    sc = A.Policy(stage="safety_case", code_whitelist=frozenset({"code1"}), data_whitelist=frozenset({"d1"}),
                  min_reviewers=0, accepted_safety_cases=frozenset({"sc1"}))
    assert not A.approve(_m(), sc).approved and A.approve(_m(safety_case_sha256="sc1"), sc).approved
    chain = Chain(tmp_path / "c.jsonl")
    A.record(chain, _m(), A.approve(_m(), ad))
    assert Chain.verify(tmp_path / "c.jsonl")[0]


def test_stage_progression():
    assert [A.stage_for_year(y) for y in (2029, 2032, 2034, 2036)] == ["caps", "ad_hoc", "human_interpretable", "safety_case"]


def test_permit_ledger_respects_cap_path():
    path = K.CapPath(100.0, 6.0)
    assert abs(path.cap_at(6) - 200.0) < 1e-9
    led = K.PermitLedger(path)
    with pytest.raises(ValueError):
        led.issue("A", 1.0, months=0)                       # already at the cap
    led.issue("A", 60.0, months=6)
    with pytest.raises(ValueError):
        led.issue("B", 50.0, months=6)                      # 100 + 60 + 50 > 200
    led.transfer("A", "B", 10.0)
    with pytest.raises(ValueError):
        led.transfer("A", "B", 100.0)
    led.retire("B", 4.0)
    assert abs(led.outstanding() - (60.0 - 4.0)) < 1e-9 and led.bal == {"A": 50.0, "B": 6.0}


def test_fleet_caps_and_edge_cap():
    e = K.EdgeCap()
    assert e.credits == 5e6
    assert e.register(2e6, verified=False) == "credit-consumed" and e.credits == 3e6
    assert e.register(1e9, verified=True) == "exempt"
    with pytest.raises(ValueError):
        e.register(4e6, verified=False)
    f = K.FleetCaps()
    f.allocate("total_zdr", 1e5)
    with pytest.raises(ValueError):
        f.allocate("total_zdr", 1.0)
    f.allocate("probabilistic_zdr", 1e8)
