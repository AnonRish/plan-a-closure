from plan_a_protocol.workload import WorkloadManifest, verify_workload


def manifest():
    return WorkloadManifest(
        workload_id="w1",
        code_digest="code",
        model_digest="model",
        dataset_digest="data",
        runtime_digest="runtime",
        compiler_digest="compiler",
        allowed_operations=["matmul", "relu"],
        required_operations=["matmul"],
        prohibited_operations=["network_write"],
        resource_limits={"h100e_hours": 100},
        proof_mode="SAMPLED_RECOMPUTATION",
    )


def artifacts():
    return {"code_digest": "code", "model_digest": "model", "dataset_digest": "data", "runtime_digest": "runtime", "compiler_digest": "compiler"}


def test_clean_workload_passes():
    result = verify_workload(manifest(), observed_operations=["matmul", "relu"], observed_resources={"h100e_hours": 40}, observed_artifacts=artifacts())
    assert result["status"] == "PASS"


def test_prohibited_operation_fails():
    result = verify_workload(manifest(), observed_operations=["matmul", "network_write"], observed_resources={"h100e_hours": 40}, observed_artifacts=artifacts())
    assert result["status"] == "FAIL"


def test_missing_measurement_is_unknown():
    result = verify_workload(manifest(), observed_operations=["matmul"], observed_resources={}, observed_artifacts=artifacts())
    assert result["status"] == "UNKNOWN"


def test_digest_changes_when_policy_changes():
    a = manifest().digest()
    b = manifest()
    b.allowed_operations.append("softmax")
    assert a != b.digest()
