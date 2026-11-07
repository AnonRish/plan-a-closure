from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from .protocol import canonical_json


@dataclass
class WorkloadManifest:
    workload_id: str
    code_digest: str
    model_digest: str
    dataset_digest: str
    runtime_digest: str
    compiler_digest: str | None = None
    allowed_operations: list[str] = field(default_factory=list)
    required_operations: list[str] = field(default_factory=list)
    prohibited_operations: list[str] = field(default_factory=list)
    resource_limits: dict[str, float] = field(default_factory=dict)
    network_policy: dict[str, Any] = field(default_factory=dict)
    memory_policy: dict[str, Any] = field(default_factory=dict)
    proof_mode: str = "DECLARATION"

    def as_dict(self) -> dict[str, Any]:
        return {
            "workload_id": self.workload_id,
            "code_digest": self.code_digest,
            "model_digest": self.model_digest,
            "dataset_digest": self.dataset_digest,
            "runtime_digest": self.runtime_digest,
            "compiler_digest": self.compiler_digest,
            "allowed_operations": sorted(self.allowed_operations),
            "required_operations": sorted(self.required_operations),
            "prohibited_operations": sorted(self.prohibited_operations),
            "resource_limits": self.resource_limits,
            "network_policy": self.network_policy,
            "memory_policy": self.memory_policy,
            "proof_mode": self.proof_mode,
        }

    def digest(self) -> str:
        return hashlib.sha256(canonical_json(self.as_dict())).hexdigest()


def verify_workload(
    manifest: WorkloadManifest,
    *,
    observed_operations: list[str],
    observed_resources: dict[str, float],
    observed_artifacts: dict[str, str],
) -> dict[str, Any]:
    reasons: list[str] = []
    status = "PASS"
    observed = set(observed_operations)
    allowed = set(manifest.allowed_operations)
    prohibited = set(manifest.prohibited_operations)
    required = set(manifest.required_operations)

    unexpected = observed - allowed if allowed else set()
    banned = observed & prohibited
    missing = required - observed

    if banned:
        status = "FAIL"
        reasons.append(f"prohibited operations observed: {sorted(banned)}")
    if unexpected:
        status = "FAIL"
        reasons.append(f"operations outside declared allow-list: {sorted(unexpected)}")
    if missing:
        status = "FAIL"
        reasons.append(f"required operations missing from observed execution: {sorted(missing)}")

    for key, cap in manifest.resource_limits.items():
        actual = observed_resources.get(key)
        if actual is None:
            if status == "PASS":
                status = "UNKNOWN"
            reasons.append(f"required resource measurement missing: {key}")
        elif actual > cap:
            status = "FAIL"
            reasons.append(f"resource cap exceeded: {key}={actual} > {cap}")

    expected_artifacts = {
        "code_digest": manifest.code_digest,
        "model_digest": manifest.model_digest,
        "dataset_digest": manifest.dataset_digest,
        "runtime_digest": manifest.runtime_digest,
    }
    if manifest.compiler_digest:
        expected_artifacts["compiler_digest"] = manifest.compiler_digest

    for key, expected in expected_artifacts.items():
        actual = observed_artifacts.get(key)
        if actual is None:
            if status == "PASS":
                status = "UNKNOWN"
            reasons.append(f"required artifact digest missing: {key}")
        elif actual != expected:
            status = "FAIL"
            reasons.append(f"artifact digest mismatch: {key}")

    return {
        "status": status,
        "workload_id": manifest.workload_id,
        "manifest_digest": manifest.digest(),
        "proof_mode": manifest.proof_mode,
        "reasons": reasons or ["all declared checks satisfied"],
    }
