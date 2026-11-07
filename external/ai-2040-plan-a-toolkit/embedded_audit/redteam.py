from __future__ import annotations

import hashlib

from .audit import AuditRound, run_audit_round


def run_redteam() -> dict[str, object]:
    findings = {}

    a = AuditRound.create("rt-a", "company", ["compute-log"])
    b = AuditRound.create("rt-b", "company", ["compute-log"])
    old_response = hashlib.sha256((a.nonce + "compute-log").encode()).hexdigest()
    try:
        b.add_evidence(
            evidence_id="replay",
            artifact_type="compute-log",
            content=b"x",
            source_locator="company:compute-log",
            response=old_response,
        )
        findings["cross_round_challenge_replay"] = "MISSED"
    except ValueError:
        findings["cross_round_challenge_replay"] = "DETECTED"

    c = AuditRound.create("rt-c", "company", ["compute-log", "access-log"])
    run_audit_round(c, artifacts={"compute-log": b"x"})
    findings["evidence_omission"] = c.evaluate()["status"]

    d = AuditRound.create("rt-d", "company", ["compute-log"])
    run_audit_round(d, artifacts={"compute-log": b"tampered-but-challenged"})
    findings["challenged_content_not_truth_checked"] = "KNOWN_LIMITATION"

    return {
        "suite": "T1-PROTOCOL-REDTEAM-V1",
        "findings": findings,
        "expected": {
            "cross_round_challenge_replay": "DETECTED",
            "evidence_omission": "UNKNOWN",
            "challenged_content_not_truth_checked": "KNOWN_LIMITATION",
        },
    }
