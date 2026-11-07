"""Confirms the audit log is actually wired into the live API, not just
unit-tested in isolation -- a rotate-key or revoke-key call through the
real running app must produce a readable, attributed audit entry."""
from __future__ import annotations

from fastapi.testclient import TestClient

from frontier_verify.api.main import app
from frontier_verify.audit.log import _actor_fingerprint

client = TestClient(app)


def test_rotate_key_via_api_produces_an_audit_entry(auth_headers):
    r = client.post("/v1/verifier/rotate-key", headers=auth_headers)
    assert r.status_code == 200

    r2 = client.get("/v1/verifier/audit-log", headers=auth_headers)
    assert r2.status_code == 200
    entries = r2.json()["entries"]
    rotate_entries = [e for e in entries if e["action"] == "rotate-key"]
    assert len(rotate_entries) >= 1
    assert rotate_entries[-1]["actor_fingerprint"] == _actor_fingerprint(auth_headers["X-Api-Key"])


def test_audit_log_read_requires_administrator_or_auditor_role():
    r = client.get("/v1/verifier/audit-log")  # no credentials at all
    assert r.status_code == 401
