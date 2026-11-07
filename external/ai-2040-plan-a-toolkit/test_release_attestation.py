from release_attestation import build_attestation

def test_release_attestation_has_explicit_external_gates():
    r=build_attestation()
    assert r["software_gates"]["all_17_workstreams_modeled"] is True
    assert r["software_gates"]["adversary_case_count"] >= 12
    assert r["external_gates"]
    assert 0 < r["statistical_sanity"]["exact_detection_probability"] < 1
