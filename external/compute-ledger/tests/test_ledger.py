import json

import pytest
from hypothesis import settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule

from compute_ledger.ledger import Event, Ledger, LedgerError, produce, retire, transfer

US, CN = ("US", "datacenter"), ("China", "datacenter")


def small():
    led = Ledger(opening={US: 100.0})
    led.post(produce(CN, 40.0))
    led.post(transfer(US, CN, 30.0))
    led.post(retire(CN, 10.0))
    return led


def test_basic_accounting_and_marginals():
    led = small()
    assert led.balance("US", "datacenter") == 70.0 and led.balance("China", "datacenter") == 60.0
    assert led.total() == 130.0 and led.produced == 40.0 and led.retired == 10.0
    assert led.by_owner() == {"US": 70.0, "China": 60.0} and led.by_category() == {"datacenter": 130.0}
    assert led.conservation_error() == 0.0
    led.check()


def test_a_transfer_never_changes_the_total():
    led = small()
    before = led.total()
    led.post(transfer(CN, ("China", "in-transit"), 25.0))
    assert led.total() == before and led.balance("China", "in-transit") == 25.0


def test_retiring_or_moving_an_entire_balance_is_allowed():
    led = Ledger(opening={US: 5.0})
    led.post(transfer(US, CN, 5.0))
    assert led.balance("US", "datacenter") == 0.0
    led.post(retire(CN, 5.0))
    assert led.total() == 0.0


def test_overdraw_is_refused_and_leaves_the_ledger_untouched():
    led = small()
    snap = (led.accounts(), len(led.history), led.produced, led.retired)
    for ev in (retire(US, 70.0000001), transfer(US, CN, 1e9)):
        with pytest.raises(LedgerError):
            led.post(ev)
    assert (led.accounts(), len(led.history), led.produced, led.retired) == snap


@pytest.mark.parametrize("amount", [0.0, -1.0, float("nan"), float("inf")])
def test_bad_amounts_are_refused(amount):
    led = Ledger(opening={US: 10.0})
    with pytest.raises(LedgerError):
        led.post(produce(US, amount))


def test_malformed_events_are_refused():
    led = Ledger(opening={US: 10.0})
    for ev in (Event("produce", 1.0), Event("produce", 1.0, to=US, frm=CN), Event("retire", 1.0),
               Event("retire", 1.0, frm=US, to=CN), Event("transfer", 1.0, to=US), Event("explode", 1.0, to=US)):
        with pytest.raises(LedgerError):
            led.post(ev)
    with pytest.raises(LedgerError):
        Ledger(opening={US: -1.0})


def test_post_all_is_atomic():
    led = small()
    snap = (led.accounts(), len(led.history), led.produced, led.retired, led.digest())
    with pytest.raises(LedgerError):
        led.post_all([produce(US, 5.0), transfer(US, CN, 3.0), retire(CN, 1e9)])
    assert (led.accounts(), len(led.history), led.produced, led.retired, led.digest()) == snap


def test_json_round_trip_and_digest():
    led = small()
    back = Ledger.from_dict(json.loads(json.dumps(led.to_dict())))
    assert back.accounts() == led.accounts() and back.digest() == led.digest()
    assert back.produced == led.produced and back.retired == led.retired


def test_digest_detects_any_change_to_the_history():
    led = small()
    d0 = led.digest()
    d = led.to_dict()
    d["events"][1]["amount"] = 29.0
    assert Ledger.from_dict(d).digest() != d0                              # an amount changed
    d = led.to_dict()
    d["events"][0], d["events"][1] = d["events"][1], d["events"][0]
    assert Ledger.from_dict(d).digest() != d0                              # events reordered
    led.post(produce(US, 1.0))
    assert led.digest() != d0                                              # an event appended


def test_a_history_that_overdraws_is_rejected_on_load():
    d = small().to_dict()
    d["events"].append({"kind": "retire", "amount": 1e9, "from": ["US", "datacenter"]})
    with pytest.raises(LedgerError):
        Ledger.from_dict(d)


def test_opening_position_is_recovered_from_the_history():
    led = small()
    assert led.opening_position() == {US: 100.0}


def test_check_catches_corruption():
    led = small()
    led._bal[US] = led._bal[US] - 1.0                                      # a silent edit outside post()
    with pytest.raises(LedgerError):
        led.check()


class LedgerMachine(RuleBasedStateMachine):
    """Random valid and invalid event sequences; the conservation law and non-negativity must always hold."""

    def __init__(self):
        super().__init__()
        self.led = Ledger(opening={("A", "x"): 1000.0})
        self.keys = [("A", "x"), ("B", "x"), ("A", "y"), ("B", "y")]

    @rule(k=st.integers(0, 3), amt=st.floats(1e-3, 500))
    def make(self, k, amt):
        self.led.post(produce(self.keys[k], amt))

    @rule(a=st.integers(0, 3), b=st.integers(0, 3), amt=st.floats(1e-3, 800))
    def move(self, a, b, amt):
        try:
            self.led.post(transfer(self.keys[a], self.keys[b], amt))
        except LedgerError:
            pass

    @rule(a=st.integers(0, 3), amt=st.floats(1e-3, 800))
    def scrap(self, a, amt):
        try:
            self.led.post(retire(self.keys[a], amt))
        except LedgerError:
            pass

    @invariant()
    def laws_hold(self):
        self.led.check(1e-9)
        assert all(v >= -1e-9 for v in self.led.accounts().values())
        assert sum(self.led.by_owner().values()) == pytest.approx(self.led.total(), rel=1e-9, abs=1e-9)
        assert sum(self.led.by_category().values()) == pytest.approx(self.led.total(), rel=1e-9, abs=1e-9)


LedgerMachine.TestCase.settings = settings(max_examples=60, stateful_step_count=30, deadline=None)
TestLedgerMachine = LedgerMachine.TestCase
