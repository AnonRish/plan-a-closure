from pathlib import Path

from closure import coverage as V


def test_matrix_references_exist(tmp_path):
    assert V.validate() == []
    from closure.cli import main                                   # --write creates missing directories, for both matrices
    assert main(["coverage", "--write", str(tmp_path / "a" / "b" / "plan_a.md")]) == 0
    assert main(["pause", "coverage", "--write", str(tmp_path / "c" / "d" / "pause.md")]) == 0
    assert (tmp_path / "a" / "b" / "plan_a.md").exists() and (tmp_path / "c" / "d" / "pause.md").exists()


def test_matrix_is_documented_and_current():
    doc = Path(__file__).resolve().parents[1] / "docs" / "PLAN_A_COVERAGE.md"
    assert doc.read_text(encoding="utf-8") == V.to_markdown(), "run: closure coverage --write docs/PLAN_A_COVERAGE.md"


def test_every_workstream_and_phase_has_a_row():
    ids = {r["id"] for r in V.ROWS}
    assert all(f"GI-WS-{i:02d}" in ids for i in range(1, 18))
    assert {"GI-T1", "GI-T2", "GI-T3", "GI-T4"} <= ids
    assert all(f"GI-OP.{i}" in ids for i in range(1, 8))
    for prefix in ("VP-1.", "VP-IO.", "VP-2.", "VP-3.", "VP-A."):
        assert any(i.startswith(prefix) for i in ids), prefix


def test_summary_counts_add_up_and_nothing_physical_is_counted_as_covered():
    s = V.summary()
    assert sum(s[k] for k in V.STATUSES) == s["rows"]
    assert all(r["status"] in ("physical", "policy") for r in V.ROWS if r["kind"] != "software")


def test_readme_status_table_matches_the_matrix():
    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
    s = V.summary()
    for label, key in (("implemented (code and tests here)", "implemented"), ("hardware-gated (code here, needs a cluster)", "hardware-gated"),
                       ("partial", "partial"), ("physical (outside software)", "physical"), ("policy (outside software)", "policy")):
        assert f"| {label} | {s[key]} |" in readme, label
    assert s["external"] == 0 and s["not-started"] == 0         # the README says no row only points elsewhere and none is unstarted
    for r in V.ROWS:
        if r["status"] == "partial":
            assert r["note"], r["id"]                            # every partial row says what is missing
