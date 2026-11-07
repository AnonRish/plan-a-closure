"""Real quorum experiment against three GENUINELY independent verifier
processes -- actual separate OS processes (subprocess.Popen running
uvicorn), not in-process module tricks.

An earlier version of this test used importlib.util.exec_module to
create "separate" main.py module instances within a single Python
process. That does NOT achieve real independence: frontier_verify.api.main
imports `store` FROM frontier_verify.api.store, and Python caches that
imported module globally the first time anything imports it -- so all
three "independent" instances silently shared the exact same evidence/
policy storage the whole time, only key_provider (assigned directly in
main.py's own body) was genuinely separate. This was caught empirically
(a disagreement test that should have shown 2-vs-1 showed 3-vs-0 instead)
and is exactly the kind of false-independence this whole experiment
exists to guard against -- see docs/research/verifier-trust.md. Real
subprocesses have fully separate memory and cannot have this problem by
construction.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import uuid

import httpx
import pytest

from frontier_verify.attestations.mock_provider import MockAttestationProvider
from frontier_verify.evidence.models import Evidence, ModelIdentity, RuntimeIdentity
from frontier_verify.policies.models import Policy
from frontier_verify.quorum.client import QuorumClient, QuorumMemberResult, QuorumReport
from frontier_verify.receipts.models import Receipt as ReceiptModel

QUORUM_API_KEY = "quorum-test-key"
QUORUM_ROLES = "PROVER|POLICY_AUTHORITY|ADMINISTRATOR|AUDITOR"


def _start_subprocess_verifier(port: int) -> subprocess.Popen:
    key_dir = tempfile.mkdtemp(prefix=f"quorum-keys-{port}-")
    data_dir = tempfile.mkdtemp(prefix=f"quorum-data-{port}-")
    env = dict(os.environ)
    env["FV_KEY_DIR"] = key_dir
    env["FV_DATA_DIR"] = data_dir
    env["FV_API_KEYS"] = f"{QUORUM_API_KEY}:{QUORUM_ROLES}"

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "frontier_verify.api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        try:
            r = httpx.get(f"http://127.0.0.1:{port}/health", timeout=1.0)
            if r.status_code == 200:
                return proc
        except httpx.HTTPError:
            pass
        time.sleep(0.1)

    proc.terminate()
    raise RuntimeError(f"quorum verifier subprocess on port {port} never became healthy")


@pytest.fixture(scope="module")
def three_independent_verifiers():
    ports = (8921, 8922, 8923)
    procs = [_start_subprocess_verifier(p) for p in ports]
    yield ports
    for proc in procs:
        proc.terminate()
    for proc in procs:
        try:
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_three_independent_verifiers_have_genuinely_different_keys(three_independent_verifiers):
    """Confirms independence empirically before testing anything else --
    real separate processes, so this MUST be true by construction, but
    the earlier bug this file's docstring describes is exactly why
    'must be true by construction' still gets checked directly rather
    than assumed."""
    key_ids = set()
    for port in three_independent_verifiers:
        r = httpx.get(f"http://127.0.0.1:{port}/v1/verifier/public-key", timeout=2.0)
        key_ids.add(r.json()["key_id"])
    assert len(key_ids) == 3, "quorum members unexpectedly share a key -- not actually independent"


def test_quorum_agrees_on_honest_evidence(three_independent_verifiers):
    endpoints = [f"http://127.0.0.1:{p}" for p in three_independent_verifiers]
    quorum = QuorumClient(endpoints=endpoints, api_key=QUORUM_API_KEY)

    hw = MockAttestationProvider().get_platform_evidence()
    evidence = Evidence(
        evidence_id=str(uuid.uuid4()),
        model_identity=ModelIdentity(model_digest="quorum-honest-test"),
        runtime_identity=RuntimeIdentity(serving_engine="e"),
        hardware_evidence=hw,
    )
    policy = Policy(policy_id="quorum-policy-" + evidence.evidence_id, version="0.1.0", allow_mock_hardware=True)

    report = quorum.submit_and_verify(evidence, policy)

    assert report.any_errors is False
    assert report.all_agree is True
    assert report.dissenting_members == []
    key_ids = {r.receipt.verifier_key_id for r in report.results}
    assert len(key_ids) == 3, "each member should sign with its OWN key despite reaching the same decision"
    quorum.close()


def test_quorum_detects_disagreement_from_a_misconfigured_member(three_independent_verifiers):
    """The actual point of a quorum: one member registers a LOOSER
    policy under the same policy_id string than the other two -- with
    genuinely separate processes/storage, this cannot silently overwrite
    across members the way the earlier in-process version accidentally
    allowed. A relying party checking only one verifier would never
    notice; checking all three catches it immediately."""
    endpoints = [f"http://127.0.0.1:{p}" for p in three_independent_verifiers]
    quorum = QuorumClient(endpoints=endpoints, api_key=QUORUM_API_KEY)

    hw = MockAttestationProvider().get_platform_evidence()
    evidence = Evidence(
        evidence_id=str(uuid.uuid4()),
        model_identity=ModelIdentity(model_digest="quorum-disagreement-test"),
        runtime_identity=RuntimeIdentity(serving_engine="e"),
        hardware_evidence=hw,
    )
    policy_id = "quorum-disagreement-policy-" + evidence.evidence_id
    strict_policy = Policy(policy_id=policy_id, version="0.1.0", allow_mock_hardware=False)
    loose_policy = Policy(policy_id=policy_id, version="0.1.0", allow_mock_hardware=True)

    for client, policy in zip(quorum.clients, [strict_policy, strict_policy, loose_policy], strict=True):
        client.submit_evidence(evidence)
        client.validate_policy(policy)

    results = []
    for client in quorum.clients:
        result = client.verify_inference(evidence.evidence_id, policy_id)
        receipt = ReceiptModel.model_validate(result["receipt"]) if result.get("receipt") else None
        results.append(
            QuorumMemberResult(
                endpoint=client.endpoint,
                passed=result["passed"],
                assurance_level=result["assurance_level_achieved"],
                receipt=receipt,
            )
        )
    report = QuorumReport(results=results)

    assert report.all_agree is False
    assert len(report.dissenting_members) == 1
    assert report.dissenting_members[0].endpoint == endpoints[2]
    assert report.dissenting_members[0].passed is True
    quorum.close()


def test_quorum_reports_member_unavailability_separately_from_disagreement():
    """A quorum member that's simply unreachable is a DIFFERENT finding
    than one that actively disagrees -- conflating them would hide which
    situation a relying party is actually in. Deliberately no fixture
    dependency: this test wants a port nothing is listening on."""
    quorum = QuorumClient(endpoints=["http://127.0.0.1:19999"], api_key=QUORUM_API_KEY)
    hw = MockAttestationProvider().get_platform_evidence()
    evidence = Evidence(
        evidence_id=str(uuid.uuid4()),
        model_identity=ModelIdentity(model_digest="d"),
        runtime_identity=RuntimeIdentity(serving_engine="e"),
        hardware_evidence=hw,
    )
    policy = Policy(policy_id="unreachable-test", version="0.1.0")

    report = quorum.submit_and_verify(evidence, policy)
    assert report.any_errors is True
    assert report.all_agree is False
    quorum.close()
