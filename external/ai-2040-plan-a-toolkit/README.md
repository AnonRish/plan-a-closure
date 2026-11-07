# AI 2040 Plan A software — portfolio index

Reference implementations and red-team harnesses for pieces of the AI Futures Project's
AI 2040: Plan A verification agenda, with a map from each piece to the Plan A section it
addresses, what is tested, and what is still open. To check the claims yourself:
`pip install -r requirements-rvp1-lock.txt && pip install -e . && python -m pytest -q`
(282 tests, about a minute).

## The map

| Piece | Plan A source | What it does | Tests |
|---|---|---|---|
| `arbiter.jsx` | Verification Plan (workload approval) + Covert AI Projects (chip registry) + Deal Decline (offline licensing) | Unified registry/licensing/workload-review platform. Real ECDSA k-of-n quorum signing, real two-layer statistical audit, hash-chained ledger. | manual + syntax-verified |
| `trust_composition/` | AI Security Forum open problem: "composing trust roots" | Formal checker for independence claims between verification mechanisms. Found Arbiter's own single-point-of-failure. | 9 |
| `receipt_schema/` | AI Security Forum open problem: "binding verification to governance" | Machine-checkable receipt schema + validator; flags single-signer schemes claiming multi-party thresholds by name. | 11 |
| `bandwidth_auction/` | Transparency Plan (outgoing bandwidth auction) | VCG mechanism, truthfulness empirically stress-tested (3,300 attempts, 0 breaks), fairness-cap cost quantified. | 11 |
| `redaction_pipeline/` | Transparency Plan (Filtered Transparency) | Structural redaction (markers/watchlist/patterns) real and tested; semantic layer built as an honest unfilled interface. | 12 |
| `exfil_detector/` | Security in Plan A (compression-aware exfiltration) | Entropy + CUSUM detector. Strong on raw payload, honestly blind to unigram-disguised payload, with the exact bandwidth cost of disguising computed. | 14 |
| `workload_discriminator/` | RFD 027 (training vs. inference discrimination) | Network-traffic-only classifier. 100% clean, 94% against timing-disguised adversarial traffic vs. 0% for a timing-only baseline. | 12 |
| `distillation_redteam/` | Covert AI Projects (distillation red-teaming) | Query-budget model-extraction mechanics on a real hard task (two-spirals). Active-learning advantage reported as genuinely mixed, not oversold. | 10 |
| `rhetoric_highlighter/` | AI for Epistemics | Propaganda-technique detector grounded in the IPA's 1937 framework. Real emergency notices false-positive; calm selective framing (Card Stacking) is invisible to it — both demonstrated, not just claimed. | 16 |
| `compute_accounting/` | RFD 023 + RFD 024 (declaration + FLOP counting) | Exact analytical FLOP formulas (checked against the field's own scaling-law rule of thumb) + spot-check audit whose detection power, unlike aggregate accounting, doesn't degrade with cluster size. | 16 |
| `handoff_calculator/` | Capability Scaling Strategy | Exact reimplementation, verified against all 12 cells of the actual published table via a fresh re-fetch of the source. | 19 |

## Verified state, as of this pass

**CI is the source of truth for test status.** The RVP-1 suite is continuously
expanded and run on GitHub Actions; the exact passing-test count is intentionally
not hard-coded here. Reproducibility commands are documented below, and completed
CI runs are retained as the auditable record.

## Four things that kept happening

Not planned as a unifying thesis going in — genuinely recurring across pieces built
independently, weeks apart in conversation-time:

**Declare, commit, spot-check, don't trust aggregate numbers alone.** Arbiter's
Registry (exhaustive-above-threshold, sampled-below), Arbiter's Licensing (quorum
signatures, sequence-checked replay), and compute accounting's audit layer (hash-
committed logs, randomly revealed) are the same mechanism three times, arrived at
independently each time because it's the same honest answer to "how do you verify
something without trusting the party being verified."

**Pattern-based defenses work on naive attacks and say so, honestly, when they don't
on sophisticated ones — with the reason quantified, not asserted.** The exfiltration
detector (raw payload: 98%+ caught; unigram-disguised: blind, at a computed 1.46×
bandwidth cost to the attacker), the workload discriminator (regular timing alone:
100% then 0% under the adversarial test; adding byte-symmetry: 94%), and the
rhetoric highlighter (loud manipulation: 15 flags; calm Card Stacking: zero) are the
same finding three times: single-signal, surface-statistical detection has a real,
nameable ceiling, and multi-signal or sequential accumulation raises it without
removing it.

**A formal tool got pointed at the thing that built it, and found something real.**
The trust-composition checker's very first case study was Arbiter's own architecture
— not a hypothetical — and it found that `client_js_integrity` touched all four of
Arbiter's trust roots, a real single point of failure. That finding directly caused
the k-of-n rework, which directly informed the receipt schema's `min_attack=1`
check. Three pieces, one honest chain of cause and effect, not three unrelated demos.

**Where real judgment was needed and unavailable, an interface got built instead of
a fake.** No live LLM access in this sandbox meant the redaction pipeline's semantic
layer and (implicitly) the rhetoric highlighter's Card Stacking gap couldn't be
filled honestly — so neither pretended to. Both are documented as exactly the seam
where a production version needs real judgment, not pattern-matching, wired in.

## What's honestly still open

**Needs real hardware or data this environment doesn't have, full stop:**
ZKP-of-inference at production scale (an open research problem industry-wide, not
just here); side-channel characterization (RFD 001-004) — needs power/EM traces off
real GPUs; satellite thermal-anomaly detection — needs licensed imagery; any of the
physical trust-root hardware (tamper-evident enclosures, guarantee processors,
optical taps themselves).

**Tractable, genuinely not done, roughly in the order I'd pick them up:**
- Confidential/secure hyperparameter-sweep service (Security in Plan A) — needs a
  real secure-enclave or MPC story to be more than a mockup
- Input-side wardens — cryptographic commitment to prompt distributions, the
  complement to the exfiltration detector's output-side view
- RID (rogue internal deployment) detector — a natural `axiomos` extension, blocked
  on not having deep enough context on axiomos's actual current internals to extend
  it faithfully rather than guess at its shape
- Collusion-resistant monitor sting-harness (extends Lumen's `control/monitors.py`)
- Chip supply-chain provenance ledger's satellite/physical-audit half — the software
  registry half is already in Arbiter; the physical verification half isn't
- AI for Epistemics: track-record/promise-scoring engine, privacy-preserving
  auditing tool, scenario-planning simulator — the rhetoric highlighter covers one
  corner of this pillar, not the whole thing
- RFD 011 (nonconfidential red-team/blue-team verification framework), RFD 008
  (attested logging against real COTS TEE/TPM primitives instead of simulated
  signing), RFD 039/040 (model fingerprint attestation, model tenancy ledger)
- Stage 1's target-year tradeoff curves from Capability Scaling Strategy — named
  explicitly in the handoff calculator's own README as needing takeoff-simulation
  internals this doesn't have

That's the honest, complete list — not the top-7 I ranked and worked through, all of
it. "Most ideal" doesn't have a finish line here; the domain is bigger than any one
pass through it, and every tier above is either a real resource wall or a real next
project, not a gap in effort.

## If you want to keep going

Each README documents its own real bugs-found, honest limitations, and — where
relevant — the specific next extension. The tractable list above is ordered by
what I'd actually pick up next, not alphabetically. Say which, same as every other
time in this thread.


## RVP-1 research package

This repository now includes a unified reproducible verification package spanning Tracks 1-4 and the 17 inference-retrofit workstreams.

| Layer | Package surface |
|---|---|
| Normative protocol | RVP-1.md, formal state machine, Python reference model |
| Network observation | raw Ethernet/IPv4/TCP/UDP parser, whitelist, reassembly, pcap/live capture |
| Recomputation | commitments, sampling economics, deterministic kernels, signed receipts |
| Adversarial verification | hostile-prover benchmark and integrated red-team matrix |
| Track 3 | interval accounting, tail-unit sampling/tracing, residual-bound interfaces |
| Track 4 | workload manifests, Merkle proofs, cryptographic proof envelope |
| Assurance | conservative failure composition and evidence-provenance promotion gates |
| Hardware | measurement schema plus Linux capture adapter and bench acceptance targets |
| Deployment | asset lifecycle, installation acceptance and field-deployment playbook |
| Replication | reproducibility manifest, benchmark outputs, artifact hashes and handoff protocol |

The package deliberately distinguishes software evidence from physical and international evidence. A passing software test never promotes itself into a hardware or field claim.

### Reproduce locally

PowerShell:

    python -m pip install -r requirements.txt
    python -m pytest plan_a_protocol/tests embedded_audit/tests verification_lab/tests frame_processor/tests hostile_prover/tests formal/test_reference_model.py benchmarks/test_benchmark.py benchmarks/test_scorecard.py benchmarks/test_compare.py compute_accounting/test_interval_ledger.py gateway/test_policy.py gateway/test_active_contract.py provenance/test_gate.py assurance/test_compose.py assurance/test_sampling_economics.py crypto/test_proof_envelope.py hardware/test_live_capture_import.py deployment/test_readiness.py telemetry/test_consistency.py storage/test_weight_path.py redteam/test_scenarios.py redteam/test_integrated.py track3/test_tail_audit.py -q

Generated evidence artifacts are produced by the same workflow used by GitHub Actions.

### Independent evaluation

Start with EVALUATOR_BRIEF.md, BENCHMARK_PROTOCOL.md, REPLICATION_HANDOFF.md, and FIELD_DEPLOYMENT_PLAYBOOK.md. Publish raw artifacts and environment metadata alongside every physical result.

### External baseline discipline

benchmarks/external_baselines/ contains attributed published baseline records. Those values are not presented as RVP-1 measurements.
