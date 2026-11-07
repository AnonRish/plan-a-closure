from __future__ import annotations
import hashlib, json, os, platform, subprocess, sys
from pathlib import Path

EXCLUDED_NAMES = frozenset({
    "replication_manifest.json",
    "benchmark_result.json",
    "adversarial_results.json",
    "capture_benchmark_result.json",
    "retrofit_readiness_report.json",
    "capture_fixture.pcap",
    "release_attestation.json",
})

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def build_manifest(root: Path) -> dict:
    try:
        git = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip()
    except Exception:
        git = os.environ.get("GITHUB_SHA", "UNKNOWN")
    files = sorted(
        p for p in root.rglob("*")
        if p.is_file()
        and ".git" not in p.parts
        and "__pycache__" not in p.parts
        and p.name not in EXCLUDED_NAMES
        and p.stat().st_size < 50 * 1024 * 1024
    )
    artifacts = {
        str(p.relative_to(root)).replace("\\", "/"): sha256_file(p)
        for p in files
    }
    return {
        "schema_version": 2,
        "git_commit": git,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "exclusions": sorted(EXCLUDED_NAMES),
        "artifacts": artifacts,
    }

def main() -> None:
    root = Path.cwd()
    manifest = build_manifest(root)
    Path("replication_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "git_commit": manifest["git_commit"],
        "artifact_count": len(manifest["artifacts"]),
        "self_excluded": "replication_manifest.json" in manifest["exclusions"],
    }, indent=2))

if __name__ == "__main__":
    main()
