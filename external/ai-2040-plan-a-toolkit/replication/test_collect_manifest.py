from pathlib import Path
from replication.collect_manifest import build_manifest, EXCLUDED_NAMES

def test_manifest_excludes_itself_and_generated_artifacts(tmp_path):
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    (tmp_path / "replication_manifest.json").write_text("old", encoding="utf-8")
    (tmp_path / "benchmark_result.json").write_text("generated", encoding="utf-8")
    manifest = build_manifest(tmp_path)
    assert "a.txt" in manifest["artifacts"]
    assert "replication_manifest.json" not in manifest["artifacts"]
    assert "benchmark_result.json" not in manifest["artifacts"]
    assert set(manifest["exclusions"]) == set(EXCLUDED_NAMES)

def test_manifest_artifact_order_is_stable(tmp_path):
    (tmp_path / "z.txt").write_text("z", encoding="utf-8")
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    manifest = build_manifest(tmp_path)
    assert list(manifest["artifacts"]) == ["a.txt", "z.txt"]
