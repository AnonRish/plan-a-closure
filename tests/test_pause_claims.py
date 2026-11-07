import json
from pathlib import Path

import pytest

from closure.cli import main
from closure.pause import census, thresholds
from closure.pause import coverage as PC
from closure.pause import gemm_audit as G
from closure.pause import paper_claims as P

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_WORDING = {"HP.62.FE.printed", "HP.64.hc.two.sum", "HP.61.twin"}


def test_paper_claims_reproduce_except_flagged():
    cs = P.check_all()
    bad = {c.id: c.status for c in cs if c.status != "OK"}
    assert set(bad) == EXPECTED_WORDING and set(bad.values()) == {"WORDING"}
    s = P.summary(cs)
    assert s["INCONSISTENT"] == 0 and s["total"] >= 100 and s["OK"] == s["total"] - 3
    ids = [c.id for c in cs]
    assert len(ids) == len(set(ids)) and all(i.startswith("HP.") for i in ids)
    assert all(c.note for c in cs if c.status == "WORDING")                 # every reading is stated
    for must in ("HP.T31.FE", "HP.T31.FB", "HP.T51.KM.us", "HP.T51.KM.cn", "HP.64.dark.nc.cn", "HP.65.allow.B", "HP.53.detect95", "HP.73.stranded"):
        assert must in ids


def test_claims_are_sensitive_to_the_model(monkeypatch):
    """A re-derivation that cannot fail is not one: perturb the model and the matching claims must break."""
    assert {c.id: c.status for c in P.check_all()}["HP.55.mu.on"] == "OK"
    monkeypatch.setattr(census, "UNDECLARED_ON_BOOKS", 0.12)
    after = {c.id: c.status for c in P.check_all()}
    assert after["HP.55.mu.on"] == "INCONSISTENT" and after["HP.T51.KM.us"] == "INCONSISTENT"
    monkeypatch.undo()
    monkeypatch.setattr(thresholds, "SECONDS_PER_YEAR", 360 * 24 * 3600)    # a 360-day year moves every fleet threshold
    after = {c.id: c.status for c in P.check_all()}
    assert after["HP.T31.FE"] == "INCONSISTENT" and after["HP.62.FP"] != "WORDING"
    monkeypatch.undo()
    assert P.summary()["INCONSISTENT"] == 0


def test_hp_matrix_references_exist():
    assert PC.validate() == []
    ids = [r["id"] for r in PC.ROWS]
    assert len(ids) == len(set(ids)) and all(i.startswith("HP-") for i in ids)


def test_hp_matrix_is_documented_and_current():
    doc = (ROOT / "docs" / "HARDWIRED_PAUSE_COVERAGE.md").read_text(encoding="utf-8")
    assert doc == PC.to_markdown()


def test_hp_matrix_does_not_overclaim():
    rows = {r["id"]: r for r in PC.ROWS}
    for r in PC.ROWS:
        if r["status"] in ("physical", "policy"):
            assert not r["where"] and not r["tests"], r["id"]                 # nothing is claimed for what code cannot do
        if r["status"] == "implemented":
            assert r["kind"] == "software" and r["where"] and r["tests"], r["id"]
    s = PC.summary()
    assert s["policy"] >= 10 and s["partial"] >= 1 and s["hardware-gated"] >= 4
    assert rows["HP-3.3.3h"]["status"] == "hardware-gated" and "not a bound" in rows["HP-3.3.3h"]["note"]   # defence in depth only
    assert rows["HP-3.3.3a"]["status"] == "hardware-gated" and "pre-registered" in rows["HP-3.3.3a"]["note"]
    assert rows["HP-4.2"]["status"] == "hardware-gated"                        # the graph screen is not a hardware audit
    assert rows["HP-5.5c"]["source"].endswith("not in the paper)")             # additions are labelled as additions


def test_cli_pause_commands(capsys, tmp_path):
    assert main(["pause", "claims"]) == 0
    out = capsys.readouterr().out
    assert "WORDING" in out and "0 INCONSISTENT" in out.splitlines()[-1]
    assert main(["pause", "claims", "--strict"]) == 1                          # strict mode fails on WORDING rows
    capsys.readouterr()
    assert main(["pause", "claims", "--all"]) == 0 and capsys.readouterr().out.count("\nOK") + 1 >= 100

    def run(*args):
        capsys.readouterr()
        rc = main(["pause", *args])
        return rc, json.loads(capsys.readouterr().out)

    rc, o = run("thresholds")
    assert rc == 0 and o["thresholds"]["F_E"] == pytest.approx(6_387_820, abs=2) and len(o["breakout_sensitivity"]) == 6
    rc, o = run("ledger", "--state", "China", "--scenario", "low")
    assert rc == 0 and len(o["lines"]) == 5 and o["headroom_after_transition"]["E_sum_oom"] > 1.0
    rc, o = run("census")
    assert o["table_5_1"]["United States"]["K_M"] == pytest.approx(11_987, rel=0.01) and set(o["dark_compute"]) == {"high", "low", "non_deniable"}
    rc, o = run("diversion")
    assert o["p_detect"] == pytest.approx(0.95, abs=0.001) and o["months_to_detect"] == pytest.approx(6.0, abs=0.05)
    rc, o = run("transition")
    assert o["phase1_months"] == 26 and o["phase2_months"] == pytest.approx(16.2, abs=0.05)
    rc, o = run("msic")
    assert o["panel"]["designs"] > 0 and 0 <= o["unserved_share_bound_pure_msic_world"] <= 1
    rc, o = run("game", "--delta", "0.8", "--detect", "0.5")
    assert o["sustainable"] is True and o["game"] == "prisoners_dilemma"
    rc, o = run("coverage")
    assert rc == 0 and o["rows"] == len(PC.ROWS)
    rc, o = run("coalition")                                                    # the paper's section 3.1 list controls every stage
    assert rc == 0 and o["open_stages"] == [] and "United Kingdom" in o["critical_members"]
    rc, o = run("coalition", "--members", "United States,China")                # a bilateral deal does not, and the exit code says so
    assert rc == 1 and len(o["open_stages"]) >= 5
    rc, o = run("ledger", "--stock", "44e6")
    assert next(x for x in o["lines"] if x["name"] == "transitional service")["share_B"] == pytest.approx(0.25, abs=0.002)

    # the GEMM screen exits non-zero when a design fails the licensing criterion, so it can gate a build
    capsys.readouterr()
    assert main(["pause", "gemm-audit"]) == 1
    assert json.loads(capsys.readouterr().out)["passes_licensing_criterion"] is False
    assert main(["pause", "gemm-audit", "--sealed"]) == 0
    capsys.readouterr()
    exposed = tmp_path / "exposed.json"
    exposed.write_text(json.dumps(G.design_to_dict(G.example_attention_block())), encoding="utf-8")
    assert main(["pause", "gemm-audit", "--design", str(exposed)]) == 1
    capsys.readouterr()
    sealed = tmp_path / "sealed.json"
    sealed.write_text(json.dumps(G.design_to_dict(G.example_attention_block(authenticated_links=True))), encoding="utf-8")
    assert main(["pause", "gemm-audit", "--design", str(sealed)]) == 0


def test_cli_pause_bridge_reads_a_results_file(capsys, tmp_path):
    res = {"status": "MEASURED", "closure_gap_fraction": 0.02, "hidden_compute_at_gap_per_week": {"energy_floor_j_per_flop": 0.5e-12}}
    (tmp_path / "results.json").write_text(json.dumps(res), encoding="utf-8")
    for target in (tmp_path, tmp_path / "results.json"):                      # a run directory or the file itself
        capsys.readouterr()
        assert main(["pause", "bridge", str(target), "--fleet", "1e6", "--coverage", "1.0"]) == 0
        o = json.loads(capsys.readouterr().out)
        assert o["closure_discount"]["pi_e"] == 0.02 and o["paper_assumption_pi_e"] == 0.001
        assert o["ledger_line"]["k_e"] == pytest.approx(1e6 * 0.02 * o["closure_discount"]["tau_e"])


def _table_rows(doc: str):
    for line in doc.splitlines():
        cells = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(cells) == 8 and cells[0] in ("US", "China") and cells[1].endswith(("cooperation", "non-deniable")):
            yield cells


def test_docs_quote_what_the_code_computes():
    """The headroom table and the headline counts in the docs are generated from the code, then pasted; keep them honest."""
    from closure.pause import treaty_ledger as TL
    doc = (ROOT / "docs" / "HARDWIRED_PAUSE.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    scen = {"high cooperation": "high", "low cooperation": "low", "non-deniable": "non_deniable"}
    rows = list(_table_rows(doc))
    assert len(rows) == 6
    for state, label, binding, e_line, e_sum, b_line, b_sum, years in rows:
        led = TL.section_6_4("United States" if state == "US" else "China", scen[label])
        h = led.headroom(durable=True)
        got = [h["E_line_oom"], h["E_sum_oom"], h["B_line_oom"], h["B_sum_oom"], led.years_of_durability(1.57, True)]
        for want, have in zip((e_line, e_sum, b_line, b_sum, years), got):
            assert float(want) == pytest.approx(have, abs=0.051), (state, label, want, have)
        assert float(b_sum) <= float(b_line) + 1e-9 and float(e_sum) <= float(e_line) + 1e-9     # a sum cannot beat its worst line
    s, m = P.summary(), PC.summary()
    for text in (doc, readme):
        assert f"{s['total']} numbers" in text or f"{s['total']} printed numbers" in text
        assert f"{s['OK']} OK" in text or f"{s['OK']} reproduce" in text
    assert f"{m['rows']}-row matrix" in doc and f"{m['implemented']} are implemented" in doc
    assert f"Of {m['rows']} items, {m['software_rows']} are" in doc
