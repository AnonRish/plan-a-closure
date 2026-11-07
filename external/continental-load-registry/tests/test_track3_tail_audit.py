
from track3_tail_audit import *

def accounts():
    return {
        "A": OwnerAccount("A", 2, 2, 0, True),
        "B": OwnerAccount("B", 6, 0, 0, True),
    }

def test_weighted_sampling_is_reproducible():
    r=[TailRecipient("A",4),TailRecipient("B",6)]
    x=run_tail_population(r,accounts(),5,"seed")
    y=run_tail_population(r,accounts(),5,"seed")
    assert x["outcomes"]==y["outcomes"]

def test_balanced_population_produces_zero_failures():
    r=run_tail_population([TailRecipient("A",4),TailRecipient("B",6)],accounts(),5,"seed")
    assert r["failures"]==0
    assert r["upper_bound_untraced_tail_units"]>0

def test_incomplete_account_is_failure():
    bad={"A":OwnerAccount("A",2,2,0,False)}
    r=run_tail_population([TailRecipient("A",1)],bad,1,"seed")
    assert r["failures"]==1

def test_missing_owner_is_failure():
    r=run_tail_population([TailRecipient("MISSING",1)],{},1,"seed")
    assert r["failures"]==1


def test_sample_resolves_in_proportion_to_holdings():
    # One recipient received 1000 units: 100 still held, 900 sold onward.
    # Sampling the whole population must see exactly that split.
    r = run_tail_population([TailRecipient("A", 1000)], {"A": OwnerAccount("A", 100, 900, 0, True)}, 1000, "seed")
    results = [o["result"] for o in r["outcomes"]]
    assert results.count("PASS") == 100
    assert results.count("TRACE_FORWARD") == 900


def test_unresolved_traces_are_not_passes():
    r = run_tail_population([TailRecipient("A", 1000)], {"A": OwnerAccount("A", 0, 1000, 0, True)}, 200, "seed")
    assert r["status"] == "INCOMPLETE_TRACES"
    assert r["failures"] == 0 and r["unresolved_traces"] == 200
    assert r["failures_counted_in_bound"] == 200
    assert r["upper_failure_rate"] == 1.0


def test_attrition_claim_is_not_a_pass():
    r = run_tail_population([TailRecipient("A", 10)], {"A": OwnerAccount("A", 0, 0, 10, True)}, 10, "seed")
    assert r["failures"] == 10


def test_offset_outside_recipient_is_rejected():
    import pytest
    with pytest.raises(ValueError):
        audit_recipient(TailRecipient("A", 4), OwnerAccount("A", 4, 0, 0, True), 4)


def test_large_population_does_not_materialize_units():
    n = 289_000_000
    r = run_tail_population([TailRecipient("A", n)], {"A": OwnerAccount("A", n, 0, 0, True)}, 50, "seed")
    assert r["passes"] == 50 and r["failures"] == 0
