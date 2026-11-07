
# Independent replication protocol (RVP-1)

This repository is intended to be independently reproducible without trusting
the author's machine.

## Rule 1 — freeze inputs

The external evaluator records the exact Git commit, Python version,
OS/kernel, package hashes, benchmark parameters, random seeds, and source
artifacts before running anything.

## Rule 2 — run blind

For adversarial experiments, the verifier should generate challenges after the
prover has committed its full claim set. The external evaluator should retain
the challenge seed separately until the claim-set digest is frozen.

## Rule 3 — reproduce software

Run the full CI test suite, then run the integrated retrofit report and the
benchmark suite. Compare machine-readable outputs, not screenshots.

## Rule 4 — reproduce hardware

Where hardware is available, attach actual TAP/capture/SSD/GPU measurements to
the existing evidence schemas. Record raw captures and hashes so a second lab
can rerun the parser independently.

## Rule 5 — independent adversarial run

A separate team should implement at least one hostile prover independently,
without reusing the simulator's strategy code, and test omission, packet
substitution, digest rebinding, adaptive cheating, timing anomalies, and
sampling starvation.

## Rule 6 — publication gate

A result may be promoted from SOFTWARE-TESTED to EXPERIMENTALLY-VALIDATED only
when an independent run reproduces the preregistered measurements. A physical
claim may not be promoted based on synthetic data.

## Required release bundle

commit.txt
environment.json
dependency-lock.txt
benchmark_result.json
adversarial_results.json
raw_capture.pcap (when hardware capture is used)
sha256sums.txt
independent_report.md
