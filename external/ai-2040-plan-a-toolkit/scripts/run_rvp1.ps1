$ErrorActionPreference = "Stop"

python -m pip install -r requirements-rvp1-lock.txt
python -m pip install -e .
python -m repository_gate
python -m pytest -q
python -m benchmarks.benchmark
python -m hostile_prover.run_benchmark
python -m capture_benchmark.harness
python -m verification_lab.run_report
python -m release_attestation
python -m replication.collect_manifest

Write-Host ""
Write-Host "RVP-1 research package completed. Review:"
Write-Host "  benchmark_result.json"
Write-Host "  adversarial_results.json"
Write-Host "  capture_benchmark_result.json"
Write-Host "  retrofit_readiness_report.json"
Write-Host "  replication_manifest.json"
Write-Host "  release_attestation.json"
