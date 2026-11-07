# Plan A track integration status

This repository is the detailed experimental engineering notebook for the AI Futures Project AI 2040 verification architecture.

## Unified RVP-1 package

The repositories now share a common research package contract:

Observation -> Evidence -> Claim -> Verification procedure -> Result -> Attestation -> Receipt

The main reusable protocol package is AnonRish/ai-2040-plan-a-toolkit, which now includes the RVP-1 formal model, 17-workstream verification lab, raw-frame processor, hostile-prover benchmark, interval compute accounting, active-gateway model, hardware measurement harness, provenance gate, and independent replication protocol.

- Track 1 (company auditing): toolkit/embedded_audit provides challenged evidence collection, hash-chain evidence, multi-signer receipts and red-team tests.
- Track 2 (initial international verification): frontier-verify provides the experimental recomputation v2 path; toolkit/frame_processor and toolkit/gateway model the physical-link observation and policy boundary.
- Track 3 (absence of secret compute): continental-load-registry provides the evidence registry and conservative residual-compute engine; toolkit/compute_accounting adds interval-valued flow reconciliation and refuses unsupported closed-world conclusions.
- Track 4 (full workload verification): toolkit/plan_a_protocol provides workload manifests, policy/resource checks and signed receipts; toolkit/formal provides a state-machine specification and toolkit/benchmarks provides reproducibility and head-to-head measurement machinery.

## What is actually demonstrated

Software CI demonstrates protocol and parser behavior, adversarial simulation, evidence provenance rules, and deterministic benchmark generation. It does not establish physical or international assurance.

External gates remain:
- measured line-rate hardware;
- independent hardware replication;
- hardware-rooted trust and anti-tamper validation;
- frontier-scale recomputation;
- complete global compute accounting;
- intelligence/field validation;
- international institutional authority.

The project deliberately keeps those claims UNKNOWN until real evidence is supplied.
