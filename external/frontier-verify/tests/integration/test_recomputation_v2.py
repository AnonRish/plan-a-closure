from fastapi.testclient import TestClient

from frontier_verify.api.main import app
from frontier_verify.core.canonical import digest as canonical_digest
from frontier_verify.recomputation.pure_python_kernel import claimed_output_digest

client = TestClient(app)
HEADERS = {"X-Api-Key": "test-key-for-pytest"}


def test_track2_recomputation_v2_full_loop():
    vectors = {
        "c1": {"vector": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]},
        "c2": {"vector": [0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]},
    }
    chunks = [
        {
            "chunk_id": cid,
            "input_digest": canonical_digest(data),
            "claimed_output_digest": claimed_output_digest(data),
        }
        for cid, data in vectors.items()
    ]

    challenge = client.post(
        "/v1/recomputation/v2/challenges",
        json={"purpose": "track2-e2e", "sample_rate": 1.0},
        headers=HEADERS,
    )
    assert challenge.status_code == 200
    challenge_id = challenge.json()["challenge_id"]

    submission = client.post(
        "/v1/recomputation/v2/submissions",
        json={
            "challenge_id": challenge_id,
            "workload_id": "w-e2e",
            "chunks": chunks,
            "inputs": vectors,
            "metadata": {"policy_id": "T2-LAB", "model_identity_digest": "model-1"},
        },
        headers=HEADERS,
    )
    assert submission.status_code == 200
    submission_id = submission.json()["submission_id"]

    check = client.post(
        "/v1/recomputation/v2/check",
        json={"challenge_id": challenge_id, "submission_id": submission_id, "sample_rate": 1.0},
        headers=HEADERS,
    )
    assert check.status_code == 200
    body = check.json()
    assert body["status"] == "PASS"
    assert body["sampled_chunks"] == 2
    assert body["mismatches"] == []
    assert body["work_accounting"]["coverage_fraction"] == 1.0
    assert body["verifier_elapsed_ns"] >= 0
    assert body["receipt"]["result"] is True


def test_track2_recomputation_v2_wrong_claim_fails():
    data = {"vector": [1, 0, 0, 0, 0, 0, 0, 0]}
    challenge = client.post(
        "/v1/recomputation/v2/challenges",
        json={"purpose": "track2-negative"},
        headers=HEADERS,
    ).json()["challenge_id"]
    submission = client.post(
        "/v1/recomputation/v2/submissions",
        json={
            "challenge_id": challenge,
            "workload_id": "w-bad",
            "chunks": [{
                "chunk_id": "bad",
                "input_digest": canonical_digest(data),
                "claimed_output_digest": "0" * 64,
            }],
            "inputs": {"bad": data},
        },
        headers=HEADERS,
    )
    submission_id = submission.json()["submission_id"]
    check = client.post(
        "/v1/recomputation/v2/check",
        json={"challenge_id": challenge, "submission_id": submission_id, "sample_rate": 1.0},
        headers=HEADERS,
    )
    assert check.status_code == 200
    body = check.json()
    assert body["status"] == "FAIL"
    assert body["passed"] is False
    assert len(body["mismatches"]) == 1


def test_track2_recomputation_v2_auth_separation():
    r = client.post(
        "/v1/recomputation/v2/challenges",
        json={"purpose": "auth"},
    )
    assert r.status_code == 401
