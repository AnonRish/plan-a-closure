from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from frontier_verify.api.auth import Role, require_role
from frontier_verify.core.canonical import digest as canonical_digest
from frontier_verify.recomputation.chunk import WorkloadChunk
from frontier_verify.recomputation.pure_python_kernel import DeterministicKernel
from frontier_verify.recomputation.sampler import Challenge, commit_challenge, select_sample
from frontier_verify.recomputation.metrics import measure, sampled_work
from frontier_verify.receipts.models import Receipt
from frontier_verify.receipts.signing import sign_receipt


class RecomputeChallengeRequest(BaseModel):
    purpose: str = Field(min_length=1)
    sample_rate: float = Field(default=0.10, ge=0.0, le=1.0)


class RecomputeSubmissionRequest(BaseModel):
    challenge_id: str
    workload_id: str
    chunks: list[WorkloadChunk]
    inputs: dict[str, dict]
    metadata: dict = Field(default_factory=dict)


class RecomputeCheckRequest(BaseModel):
    challenge_id: str
    submission_id: str
    sample_rate: float = Field(default=0.10, ge=0.0, le=1.0)


def create_router(store, key_provider):
    router = APIRouter(prefix="/v1/recomputation/v2", tags=["experimental-recomputation"])
    challenges: dict[str, dict] = {}
    submissions: dict[str, dict] = {}
    kernel = DeterministicKernel()

    @router.post("/challenges", dependencies=[Depends(require_role(Role.AUDITOR))])
    def create_challenge(req: RecomputeChallengeRequest):
        challenge_id = str(uuid.uuid4())
        challenge = commit_challenge()
        challenges[challenge_id] = {
            "challenge": challenge,
            "purpose": req.purpose,
            "submission_id": None,
            "revealed": False,
            "sample_rate_default": req.sample_rate,
        }
        return {
            "challenge_id": challenge_id,
            "commitment_hex": challenge.commitment_hex,
            "sample_rate_default": req.sample_rate,
            "status": "COMMITTED_WAITING_FOR_FULL_SUBMISSION",
        }

    @router.post("/submissions", dependencies=[Depends(require_role(Role.PROVER))])
    def submit(req: RecomputeSubmissionRequest):
        state = challenges.get(req.challenge_id)
        if state is None:
            raise HTTPException(404, "unknown recomputation challenge")
        if state["revealed"]:
            raise HTTPException(409, "challenge already revealed")
        if state["submission_id"] is not None:
            raise HTTPException(409, "challenge already has a locked submission")

        ids = [c.chunk_id for c in req.chunks]
        if len(ids) != len(set(ids)):
            raise HTTPException(400, "duplicate chunk_id values are not allowed")
        if set(ids) != set(req.inputs):
            raise HTTPException(400, "inputs must contain exactly one object per claimed chunk")

        stored = {}
        for chunk in req.chunks:
            observed_digest = store.put_recomputation_input(req.inputs[chunk.chunk_id])
            if observed_digest != chunk.input_digest:
                raise HTTPException(400, f"input digest mismatch for chunk {chunk.chunk_id}")
            stored[chunk.chunk_id] = observed_digest

        claim_set_digest = canonical_digest({
            "workload_id": req.workload_id,
            "chunks": [c.model_dump(mode="json") for c in sorted(req.chunks, key=lambda x: x.chunk_id)],
        })
        submission_id = str(uuid.uuid4())
        submissions[submission_id] = {
            "challenge_id": req.challenge_id,
            "workload_id": req.workload_id,
            "chunks": [c.model_dump(mode="json") for c in req.chunks],
            "inputs": stored,
            "metadata": req.metadata,
            "claim_set_digest": claim_set_digest,
            "locked": True,
        }
        state["submission_id"] = submission_id
        return {
            "submission_id": submission_id,
            "claim_set_digest": claim_set_digest,
            "chunk_count": len(ids),
            "status": "LOCKED_BEFORE_SEED_REVEAL",
        }

    @router.post("/check", dependencies=[Depends(require_role(Role.AUDITOR))])
    def check(req: RecomputeCheckRequest):
        state = challenges.get(req.challenge_id)
        submission = submissions.get(req.submission_id)
        if state is None or submission is None:
            raise HTTPException(404, "challenge or submission not found")
        if submission["challenge_id"] != req.challenge_id or state["submission_id"] != req.submission_id:
            raise HTTPException(409, "submission is not bound to this challenge")
        if state["revealed"]:
            raise HTTPException(409, "challenge has already been revealed")

        challenge: Challenge = state["challenge"]
        chunks = [WorkloadChunk.model_validate(x) for x in submission["chunks"]]
        selected = select_sample(
            [c.chunk_id for c in chunks],
            challenge.secret_seed,
            challenge.commitment_hex,
            req.sample_rate,
        )
        by_id = {c.chunk_id: c for c in chunks}
        mismatches = []
        total_elapsed_ns = 0
        for chunk_id in selected:
            chunk = by_id[chunk_id]
            try:
                input_data = store.get_recomputation_input(chunk.input_digest)
            except (KeyError, ValueError) as exc:
                raise HTTPException(409, f"recomputation input unavailable for {chunk_id}") from exc
            measurement = measure(lambda: kernel.recompute_digest(input_data))
            total_elapsed_ns += measurement.elapsed_ns
            recomputed = measurement.value
            if recomputed != chunk.claimed_output_digest:
                mismatches.append({
                    "chunk_id": chunk_id,
                    "matched": False,
                    "claimed_output_digest": chunk.claimed_output_digest,
                    "recomputed_output_digest": recomputed,
                    "elapsed_ns": measurement.elapsed_ns,
                })

        passed = bool(selected) and not mismatches
        status = "PASS" if passed else ("UNKNOWN" if not selected else "FAIL")
        verification_id = str(uuid.uuid4())
        key_id, signing_key = key_provider.get_signing_key()
        metadata = submission["metadata"]
        receipt = Receipt(
            verification_id=verification_id,
            verifier_key_id=key_id,
            model_identity_digest=metadata.get("model_identity_digest", "UNKNOWN"),
            runtime_identity_digest=metadata.get("runtime_identity_digest", "UNKNOWN"),
            hardware_evidence_digest=metadata.get("hardware_evidence_digest", "UNKNOWN"),
            policy_id=metadata.get("policy_id", "TRACK2-EXPERIMENTAL"),
            policy_version=metadata.get("policy_version", "1"),
            assurance_level="EXPERIMENTAL_RECOMPUTATION",
            result=passed,
            limitations=[
                "Experimental software-only recomputation kernel; not frontier-scale inference.",
                "Commit-reveal addresses adaptive sample prediction, not the full economics of partial detection.",
                "No physical tap, real NIC, GPU, memory-wipe or organizational independence is validated here.",
            ],
        )
        receipt = sign_receipt(receipt, signing_key)
        store.receipts[verification_id] = receipt
        report = {
            "verification_id": verification_id,
            "challenge_id": req.challenge_id,
            "submission_id": req.submission_id,
            "workload_id": submission["workload_id"],
            "sampling_commitment": challenge.commitment_hex,
            "sample_rate": req.sample_rate,
            "total_chunks": len(chunks),
            "sampled_chunks": len(selected),
            "selected_chunk_ids": selected,
            "work_accounting": sampled_work(len(chunks), len(selected)),
            "verifier_elapsed_ns": total_elapsed_ns,
            "mismatches": mismatches,
            "status": status,
            "passed": passed,
            "claim_set_digest": submission["claim_set_digest"],
            "receipt": receipt.model_dump(mode="json"),
        }
        submissions[req.submission_id]["report"] = report
        state["revealed"] = True
        return report

    return router
