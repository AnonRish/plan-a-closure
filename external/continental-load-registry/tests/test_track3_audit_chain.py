import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

from track3_audit_chain import clean_traces_needed, run_audit_chain
from track3_certificate import one_sided_failure_upper_bound as exact_upper

ROOT = Path(__file__).resolve().parents[1]
T = 30000


def pop(sales, accounts, **extra):
    data = {
        "population_closed": True,
        "threshold_T": {"value": T, "unit": "H100e"},
        "delta": 0.05,
        "sales": sales,
        "accounts": accounts,
    }
    data.update(extra)
    return data


def sale(buyer, units, producible=True):
    return {"vendor": "V", "buyer": buyer, "units": units, "buyer_producible": producible}


def big(**overrides):
    acct = {"held": 100000, "inspected": 100000}
    acct.update(overrides)
    return acct


def example():
    return json.loads((ROOT / "data/track3/audit_chain_input.example.json").read_text(encoding="utf-8"))


# ---- the synthetic closed population end to end -------------------------------------------------


def test_example_population_certifies_and_follows_transfers():
    data = example()
    r = run_audit_chain(data, sample_size=data["sample_size"])
    assert r["status"] == "PASS"
    assert r["untraced_pool_L"]["units"] == 0
    assert [a["owner"] for a in r["audited_firms"]] == ["CloudCo", "ResellerCo"]
    assert r["tail"]["delivered_units"] == 70000 and r["tail"]["recipients"] == 3
    assert r["tail"]["failures"] == 0
    assert any(len(o["path"]) > 1 for o in r["tail"]["outcomes"])  # traces really were followed onward
    n = r["tail"]["sample_size"]
    assert r["tail"]["D_units"] == pytest.approx(70000 * (1 - 0.05 ** (1 / n)))
    assert r["upper_bound_units"] == pytest.approx(r["tail"]["D_units"])


def test_clean_sample_matches_the_supplements_rule_of_thumb():
    data = example()
    r = run_audit_chain(data, sample_size=300)
    assert r["tail"]["D_units"] == pytest.approx(70000 / 300 * math.log(1 / 0.05), rel=0.01)


def test_clean_traces_needed_inverts_the_bound():
    n = clean_traces_needed(70000, 700, 0.05)
    assert n == 299
    assert 70000 * (1 - 0.05 ** (1 / n)) <= 700
    assert 70000 * (1 - 0.05 ** (1 / (n - 1))) > 700
    with pytest.raises(ValueError):
        clean_traces_needed(1000, 1000, 0.05)
    with pytest.raises(ValueError):
        clean_traces_needed(1000, 10, 1.0)


# ---- layer 1: exhaustive audit above T, recursively ---------------------------------------------


def test_second_tier_owner_above_T_is_audited_not_sampled():
    r = run_audit_chain(
        pop(
            [sale("Big", 100000)],
            {"Big": big(held=65000, inspected=65000, transfers=[{"buyer": "Mid", "units": 35000}]), "Mid": {"held": 35000, "inspected": 35000}},
        )
    )
    assert [a["owner"] for a in r["audited_firms"]] == ["Big", "Mid"]
    assert r["tail"]["delivered_units"] == 0
    assert r["status"] == "PASS" and r["upper_bound_units"] == 0


def test_owner_above_T_only_in_aggregate_is_audited():
    r = run_audit_chain(
        pop(
            [sale("Reseller", 60000), sale("Firm", 20000)],
            {
                "Reseller": {"held": 40000, "inspected": 40000, "transfers": [{"buyer": "Firm", "units": 20000}]},
                "Firm": {"held": 40000, "inspected": 40000},
            },
        )
    )
    assert [a["owner"] for a in r["audited_firms"]] == ["Reseller", "Firm"]
    assert r["tail"]["delivered_units"] == 0


@pytest.mark.parametrize("units,expected_status", [(T, "BLOCKED"), (40000, "BLOCKED"), (T - 1, "PASS")])
def test_unauditable_buyer_blocks_only_at_or_above_T(units, expected_status):
    acct = big(held=100000 - units, inspected=100000 - units, transfers=[{"buyer": "Shell", "units": units, "buyer_producible": False}])
    r = run_audit_chain(pop([sale("Big", 100000)], {"Big": acct}))
    assert r["status"] == expected_status
    assert r["untraced_pool_L"]["units"] == units  # added in full either way
    assert r["upper_bound_units"] >= units
    if expected_status == "BLOCKED":
        assert r["blocking_events"][0]["kind"] == "UNAUDITABLE_COUNTERPARTY"


def test_unauditable_vendor_sale_goes_to_L():
    r = run_audit_chain(pop([sale("Big", 100000), sale("Shell", 50000, producible=False)], {"Big": big()}))
    assert r["status"] == "BLOCKED" and r["untraced_pool_L"]["units"] == 50000


@pytest.mark.parametrize("units,verified,status,in_l", [(35000, False, "BLOCKED", 35000), (35000, True, "PASS", 0), (5000, False, "PASS", 5000)])
def test_decommissioning_claims(units, verified, status, in_l):
    acct = big(held=100000 - units, inspected=100000 - units, decommissions=[{"units": units, "verified": verified}])
    r = run_audit_chain(pop([sale("Big", 100000)], {"Big": acct}))
    assert r["status"] == status and r["untraced_pool_L"]["units"] == in_l


def test_inspection_shortfall_at_an_audited_firm_goes_to_L():
    r = run_audit_chain(pop([sale("Big", 100000)], {"Big": big(inspected=99000)}))
    assert r["status"] == "PASS"
    assert r["untraced_pool_L"]["events"][0] == {"kind": "INSPECTION_SHORTFALL", "units": 1000, "owner": "Big"}


def test_unaccounted_units_go_to_L():
    r = run_audit_chain(pop([sale("Big", 100000)], {"Big": big(held=98000, inspected=98000)}))
    assert r["untraced_pool_L"]["events"][0]["kind"] == "UNACCOUNTED_UNITS"
    assert r["untraced_pool_L"]["units"] == 2000


def test_overstated_dispositions_block_without_inflating_L():
    r = run_audit_chain(pop([sale("Big", 100000)], {"Big": big(held=102000, inspected=102000)}))
    assert r["status"] == "BLOCKED"
    assert r["blocking_events"][0]["kind"] == "INCONSISTENT_RECORDS"
    assert r["untraced_pool_L"]["units"] == 0


# ---- layer 2: the tail ---------------------------------------------------------------------------


def diverting_tail(firms=100, units_each=100, diverting=10):
    sales, accounts = [], {}
    for i in range(firms):
        name = f"F{i:03d}"
        sales.append(sale(name, units_each))
        if i < diverting:
            accounts[name] = {"held": 0, "inspected": 0, "transfers": [{"buyer": "Shell", "units": units_each, "buyer_producible": False}]}
        else:
            accounts[name] = {"held": units_each, "inspected": units_each}
    return sales, accounts


def test_tail_diversion_is_caught_and_the_bound_covers_it():
    sales, accounts = diverting_tail()  # 1,000 of 10,000 tail units sold to a shell
    covered = 0
    for s in range(40):
        r = run_audit_chain(pop(sales, accounts), sample_size=500, seed=f"coverage-{s}")
        assert r["status"] == "PASS" and r["untraced_pool_L"]["units"] == 0  # invisible to layer 1
        assert r["tail"]["failures"] > 0
        assert {o["terminal"] for o in r["tail"]["outcomes"] if o["result"] == "FAIL"} == {"buyer_not_produced"}
        covered += r["upper_bound_units"] >= 1000
    assert covered >= 36  # one-sided 95% bound: expect about 38 of 40 or better


def test_same_seed_reproduces_and_a_new_seed_changes_the_sample():
    sales, accounts = diverting_tail()
    a = run_audit_chain(pop(sales, accounts), sample_size=200, seed="a")
    b = run_audit_chain(pop(sales, accounts), sample_size=200, seed="a")
    c = run_audit_chain(pop(sales, accounts), sample_size=200, seed="b")
    assert a == b
    assert a["tail"]["outcomes"] != c["tail"]["outcomes"]


def test_traces_are_resolved_in_proportion_to_each_account():
    accounts = {"F": {"held": 200, "inspected": 200, "transfers": [{"buyer": "G", "units": 800}]}, "G": {"held": 800, "inspected": 800}}
    r = run_audit_chain(pop([sale("F", 1000)], accounts), sample_size=1000)
    ended_at_f = sum(len(o["path"]) == 1 for o in r["tail"]["outcomes"])
    assert 140 <= ended_at_f <= 260  # about 200 of 1,000
    assert r["tail"]["failures"] == 0


def test_cycle_is_cut_off_by_the_depth_limit():
    accounts = {
        "A": {"held": 1000, "inspected": 1000, "transfers": [{"buyer": "B", "units": 500}]},
        "B": {"held": 0, "inspected": 0, "transfers": [{"buyer": "A", "units": 500}]},
    }
    data = pop([sale("A", 1000)], accounts)
    assert run_audit_chain(data, sample_size=300, max_depth=25)["tail"]["failures"] == 0
    shallow = run_audit_chain(data, sample_size=300, max_depth=2)
    assert shallow["tail"]["failures"] > 0
    assert {o["terminal"] for o in shallow["tail"]["outcomes"] if o["result"] == "FAIL"} == {"max_depth_exceeded"}


def test_unbalanced_tail_account_fails_every_trace():
    r = run_audit_chain(pop([sale("F", 100)], {"F": {"held": 90, "inspected": 90}}), sample_size=50)
    assert r["tail"]["failures"] == 50 and r["tail"]["upper_failure_rate"] == 1.0
    assert r["tail"]["D_units"] == 100
    assert {o["terminal"] for o in r["tail"]["outcomes"]} == {"unbalanced_account"}


@pytest.mark.parametrize("verified,result,terminal", [(False, "FAIL", "unverified_decommission"), (True, "PASS", "verified_decommission")])
def test_decommissioning_in_the_tail(verified, result, terminal):
    accounts = {"F": {"held": 0, "inspected": 0, "decommissions": [{"units": 100, "verified": verified}]}}
    r = run_audit_chain(pop([sale("F", 100)], accounts), sample_size=20)
    assert {(o["result"], o["terminal"]) for o in r["tail"]["outcomes"]} == {(result, terminal)}


def test_inspection_shortfall_in_the_tail_fails_in_proportion():
    accounts = {"F": {"held": 1000, "inspected": 500}}
    r = run_audit_chain(pop([sale("F", 1000)], accounts), sample_size=1000)
    assert 400 <= r["tail"]["failures"] <= 600  # about half of the held chips could not be produced


def test_trace_reaching_an_audited_firm_ends_as_a_pass():
    accounts = {"Big": {"held": 100100, "inspected": 100100}, "F": {"held": 0, "inspected": 0, "transfers": [{"buyer": "Big", "units": 100}]}}
    r = run_audit_chain(pop([sale("Big", 100000), sale("F", 100)], accounts), sample_size=50)
    assert {o["terminal"] for o in r["tail"]["outcomes"]} == {"audited_firm"}
    assert r["tail"]["failures"] == 0


# ---- when no certificate can be computed ---------------------------------------------------------


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(population_closed=False),
        lambda d: d.pop("population_closed"),
        lambda d: d.update(threshold_T={"value": 30000, "unit": "MW"}),
        lambda d: d.update(threshold_T={"value": None, "unit": "H100e"}),
        lambda d: d.update(threshold_T={"value": 0, "unit": "H100e"}),
        lambda d: d.pop("threshold_T"),
    ],
)
def test_open_population_or_missing_threshold_gives_unknown(mutate):
    data = pop([sale("Big", 100000)], {"Big": big()})
    mutate(data)
    r = run_audit_chain(data)
    assert r["status"] == "UNKNOWN" and r["upper_bound_units"] is None


@pytest.mark.parametrize(
    "data,kwargs",
    [
        (pop([sale("A", -5)], {"A": {}}), {}),
        (pop([sale("A", True)], {"A": {}}), {}),
        (pop([sale("A", 1.5)], {"A": {}}), {}),
        (pop([sale("A", 10)], {"A": {"held": 1, "inspected": 2}}), {}),
        (pop([sale("Ghost", 10)], {}), {}),
        (pop([sale("A", 100)], {"A": {"held": 100, "inspected": 100}}), {"sample_size": 101}),
        (pop([sale("A", 100)], {"A": {"held": 100, "inspected": 100}}), {}),
        (pop([sale("A", 100)], {"A": {"held": 100, "inspected": 100}}), {"sample_size": 10, "delta": 1.5}),
        (pop([sale("A", 100)], {"A": {"held": 100, "inspected": 100}}), {"sample_size": 10, "max_depth": 0}),
    ],
)
def test_bad_input_is_rejected(data, kwargs):
    with pytest.raises(ValueError):
        run_audit_chain(data, **kwargs)


def test_transfer_to_a_buyer_without_an_account_is_rejected():
    accounts = {"Big": big(held=90000, inspected=90000, transfers=[{"buyer": "Ghost", "units": 10000}])}
    with pytest.raises(ValueError):
        run_audit_chain(pop([sale("Big", 100000)], accounts))


def test_upper_failure_rate_is_the_exact_bound():
    sales, accounts = diverting_tail()
    r = run_audit_chain(pop(sales, accounts), sample_size=400, seed="exact")
    k = r["tail"]["failures"]
    assert r["tail"]["upper_failure_rate"] == exact_upper(k, 400, 0.05)


# ---- command line -------------------------------------------------------------------------------


def _cli(path):
    return subprocess.run([sys.executable, "track3_audit_chain.py", "--input", str(path)], cwd=ROOT, capture_output=True, text=True)


def test_cli_exit_code_follows_status(tmp_path):
    ok = _cli(ROOT / "data/track3/audit_chain_input.example.json")
    assert ok.returncode == 0 and json.loads(ok.stdout)["status"] == "PASS"
    blocked = pop([sale("Big", 100000)], {"Big": big(held=60000, inspected=60000, transfers=[{"buyer": "Shell", "units": 40000, "buyer_producible": False}])})
    path = tmp_path / "blocked.json"
    path.write_text(json.dumps(blocked), encoding="utf-8")
    bad = _cli(path)
    assert bad.returncode == 1 and json.loads(bad.stdout)["status"] == "BLOCKED"
