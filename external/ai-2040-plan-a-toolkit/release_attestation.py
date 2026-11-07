from __future__ import annotations
import json, os, platform, subprocess, sys
from pathlib import Path
from adversary.model import coverage_report
from assurance.statistical_bounds import finite_population_detection_probability
from verification_lab.workstream_matrix import build_matrix

def git_commit() -> str:
    try:
        return subprocess.check_output(["git","rev-parse","HEAD"], text=True).strip()
    except Exception:
        return os.environ.get("GITHUB_SHA","UNKNOWN")

def build_attestation() -> dict:
    matrix = build_matrix()
    attack = coverage_report()
    return {
        "schema_version": 1,
        "protocol": "RVP-1",
        "git_commit": git_commit(),
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "software_gates": {
            "adversary_catalog_status": attack["status"],
            "adversary_case_count": attack["attack_count"],
            "workstream_count": matrix["count"],
            "all_17_workstreams_modeled": matrix["count"] == 17,
        },
        "statistical_sanity": {
            "example_population": {"N": 1000, "rogues": 10, "sample": 258},
            "exact_detection_probability": finite_population_detection_probability(1000,10,258),
        },
        "evidence_promotion_rule": "No physical, field, independent-replication, or international claim is promoted from software tests alone.",
        "external_gates": [
            "real 400/800/1600GbE capture measurement",
            "production accelerator memory-wipe measurement",
            "live side-channel characterization",
            "authorized physical inspection",
            "closed global compute population",
            "independent replication",
        ],
    }

def main() -> None:
    result = build_attestation()
    Path("release_attestation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
