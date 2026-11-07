from embedded_audit.redteam import run_redteam


def test_track1_redteam():
    result = run_redteam()
    assert result["findings"]["cross_round_challenge_replay"] == "DETECTED"
    assert result["findings"]["evidence_omission"] == "UNKNOWN"
    assert result["findings"]["challenged_content_not_truth_checked"] == "KNOWN_LIMITATION"
