import json

import pytest

from compute_ledger.cli import main, parse_amount
from compute_ledger.ledger import Ledger, produce, retire, transfer


def run(argv, capsys):
    rc = main(argv)
    return rc, capsys.readouterr().out


@pytest.mark.parametrize("text,want", [("224M", 224e6), ("397K", 397e3), ("1.5m", 1.5e6), ("8.6e6", 8.6e6),
                                        ("1,234", 1234.0), ("2B", 2e9), (" 5 ", 5.0)])
def test_parse_amount(text, want):
    assert parse_amount(text) == pytest.approx(want)


def test_parse_amount_rejects_garbage():
    with pytest.raises(ValueError):
        parse_amount("lots")


def test_plan_a_reports_zero_failures(capsys):
    rc, out = run(["plan-a"], capsys)
    assert rc == 0 and "0 failing" in out and "289" in out


def test_plan_a_json(capsys):
    rc, out = run(["plan-a", "--json"], capsys)
    rows = json.loads(out)
    assert rc == 0 and rows and all(r["ok"] for r in rows)


def test_roll(capsys):
    rc, out = run(["roll", "--stock0", "8.6M", "--production", "14.2M,35.7M,80.6M,159.7M", "--half-life", "15"], capsys)
    assert rc == 0 and "after year 4: 288.72M" in out
    rc, out = run(["roll", "--stock0", "8.6M", "--production", "14.2M,35.7M,80.6M,159.7M"], capsys)
    assert "after year 4: 298.80M" in out


def test_reconcile(capsys):
    rc, out = run(["reconcile", "--declared", "224M", "--lo", "222M", "--hi", "226M", "--exceeds", "4M"], capsys)
    assert rc == 0 and "median 1.05M" in out and "P(undeclared > 4.00M)" in out
    rc, out = run(["reconcile", "--declared", "224M", "--lo", "222M", "--hi", "226M", "--prior", "halfnormal:1M"], capsys)
    assert rc == 0 and "median" in out
    rc, out = run(["reconcile", "--declared", "224M", "--lo", "222M", "--hi", "226M", "--prior", "fitted:0.289M,1.5M,4.046M"], capsys)
    assert rc == 0
    with pytest.raises(SystemExit):
        main(["reconcile", "--declared", "224M", "--lo", "222M", "--hi", "226M", "--prior", "bogus"])


def test_ledger_command(tmp_path, capsys):
    led = Ledger(opening={("US", "dc"): 100.0})
    led.post(produce(("China", "dc"), 40.0))
    led.post(transfer(("US", "dc"), ("China", "dc"), 30.0))
    led.post(retire(("China", "dc"), 10.0))
    good = tmp_path / "good.json"
    good.write_text(json.dumps(led.to_dict()))
    rc, out = run(["ledger", str(good)], capsys)
    assert rc == 0 and "valid: 2 accounts, 3 events" in out and "owner US" in out
    d = led.to_dict()
    d["events"].append({"kind": "retire", "amount": 1e9, "from": ["US", "dc"]})
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(d))
    rc, out = run(["ledger", str(bad)], capsys)
    assert rc == 1 and "INVALID" in out
    rc, out = run(["ledger", str(tmp_path / "missing.json")], capsys)
    assert rc == 1 and "INVALID" in out
