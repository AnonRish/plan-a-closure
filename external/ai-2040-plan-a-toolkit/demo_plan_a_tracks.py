#!/usr/bin/env python3
"""Small end-to-end software demo for Track 1 and Track 4."""
from embedded_audit.audit import AuditRound, build_audit_receipt, run_audit_round
from plan_a_protocol.protocol import Signer, generate_keypair, verify_receipt
from plan_a_protocol.workload import WorkloadManifest, verify_workload


def main():
    audit = AuditRound.create("demo-t1", "demo-company", ["compute-log", "access-log"])
    run_audit_round(audit, artifacts={"compute-log": b"compute-v1", "access-log": b"access-v1"})
    akey, apub = generate_keypair()
    bkey, bpub = generate_keypair()
    receipt = build_audit_receipt(
        audit,
        [
            (Signer("auditor-a", "embedded-auditor", apub, "org-a"), akey),
            (Signer("auditor-b", "review-auditor", bpub, "org-b"), bkey),
        ],
        quorum=2,
    )
    ok, errors = verify_receipt(receipt)
    assert ok, errors

    manifest = WorkloadManifest(
        workload_id="demo-t4",
        code_digest="code-v1",
        model_digest="model-v1",
        dataset_digest="data-v1",
        runtime_digest="runtime-v1",
        compiler_digest="compiler-v1",
        allowed_operations=["matmul", "relu"],
        required_operations=["matmul"],
        prohibited_operations=["network_write"],
        resource_limits={"h100e_hours": 100},
        proof_mode="SAMPLED_RECOMPUTATION",
    )
    workload = verify_workload(
        manifest,
        observed_operations=["matmul", "relu"],
        observed_resources={"h100e_hours": 12},
        observed_artifacts={
            "code_digest": "code-v1",
            "model_digest": "model-v1",
            "dataset_digest": "data-v1",
            "runtime_digest": "runtime-v1",
            "compiler_digest": "compiler-v1",
        },
    )
    assert workload["status"] == "PASS"
    print("Track 1:", audit.evaluate()["status"], "receipt verified")
    print("Track 4:", workload["status"], "manifest", workload["manifest_digest"][:16] + "...")


if __name__ == "__main__":
    main()
