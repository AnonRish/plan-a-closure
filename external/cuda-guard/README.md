# cuda_guard — AI 2040 Compute Verification (real-evidence implementation pass)

This repository implements the currently-real, currently-testable portions
of the AI 2040 Plan A compute-verification architecture, following the
five-layer Trust Architecture (`docs/` in the prior single-file prototype)
and the evidence-honesty rules in `docs/STATUS_REPORT.md`.

**Start here:** `docs/STATUS_REPORT.md` for what's real vs. hardware-gated
vs. not implemented. `docs/PHASE0_AUDIT.md` for what was inspected before
anything was changed. `docs/THREAT_MODEL.md` and `docs/LIMITATIONS.md` for
what an adversary can and cannot defeat.

## Install

```bash
pip install -e .
# or, for development:
pip install -e ".[dev]"
```

## Run the tests (41 real tests, no design-intent assertions)

```bash
pytest tests/ -v
```

## Try the CLI

```bash
python -m cuda_guard.cli status
python -m cuda_guard.cli hardware-inspect
python -m cuda_guard.cli attestation-run
python -m cuda_guard.cli ledger-verify
python -m cuda_guard.cli capabilities-show
```

## Package layout

```text
cuda_guard/
  evidence.py             # Phase 1: typed evidence model, shared by everything below
  ledger.py                # Phase 3: tamper-evident hash-chained audit ledger
  self_audit.py             # Phase 4/5: backward/optimizer interception, NCCL auditor, FLOP ledger
  driver_interceptor.py      # Phase 10: real LD_PRELOAD CUDA driver interception
  hardware.py                # Phase 6-9/18: device discovery, real attestation, registry, model identity
  network_evidence.py         # Phase 11/19/20: PCAP ingestion, flow statistics
  reproducibility.py           # Phase 12/13/21: determinism, sampled recomputation, signing
  external_evidence.py          # Phase 14/15/24/25: power, memory-wipe, external evidence API
  verdict.py                     # Phase 2/16/28: the governance verdict engine
  capability_registry.py          # Phase 32: machine-readable capability matrix
  diagnostics.py                   # Phase 33: environment self-diagnostics
  cli.py                            # Phase 34: the CLI
tests/                                # real, re-runnable pytest suite (41 tests)
docs/                                  # PHASE0_AUDIT, THREAT_MODEL, LIMITATIONS, STATUS_REPORT
```

## The one rule everything else follows

Absence of evidence, evidence of failure, and evidence of success are three
different things (`cuda_guard.evidence.EpistemicClass`). Nothing in this
repository collapses them, in code, in tests, or in this README.
