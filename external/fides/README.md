# Fides

[![tests](https://github.com/AnonRish/fides/actions/workflows/tests.yml/badge.svg)](https://github.com/AnonRish/fides/actions/workflows/tests.yml)

**A reference implementation of a packet-hashing inference-only verification tap, built against the AI 2040: Plan A verification agenda.**

[AI 2040: Plan A](https://ai-2040.com/) is the AI Futures Project's (the team behind [AI 2027](https://ai-2027.com/)) recommendation for how the US and China could verifiably slow down the race to superintelligence. The plan's [verification supplement](https://ai-2040.com/supplements/verification-plan) argues the whole deal is only as strong as the ability to check compliance without relying on trust. Amodo Design, the hardware firm prototyping the plan's network-tap-and-recomputation approach, published a [SITREP](https://amododesign.com/ai-verification/plan-a-sitrep/) grading the 17 engineering workstreams that approach needs: 4 active, 5 not started, 7 not on track, and one (memory wipes) graded uncertain.

Fides is a from-scratch, tested, open-source testbed. Of the 11 workstreams with any software-only path at all, it directly addresses **7** (2 solidly, 5 as narrow partial slices; `python verify_claims.py` prints the breakdown), has a real but honestly-caveated partial connection to **2** more, and does not touch **2**:

| Workstream (SITREP grade) | What Fides does about it |
|---|---|
| **New TAP types & bandwidth limits** (not started) | `commitment.py`: BLAKE3 Merkle-tree packet-hashing tap — commit locally and cheaply, reveal only a small auditor-chosen sample. |
| **Verification reporting** (not on track) | `ledger.py`: hash-chained, signed audit log — a compromised auditor can't quietly rewrite a past finding without breaking the chain. |
| **Reproducible inference stack** (not started) | `determinism.py`: fixed-order deterministic reduction vs. a schedule-dependent one — fixes the specific, well-documented floating-point-reduction-order mechanism, not a full inference stack. |
| **Network reproducibility** (not started) | `packet_reconstruction.py`: content-addressed, order-independent verification that a message was delivered completely and correctly regardless of packet arrival order — the narrower alternative Amodo's own text floats, not bit-exact packet replay. |
| **Recomputation server security** (not on track) | `server_attestation.py`: a challenge-response software heartbeat catching silent logic substitution and history rollback — explicitly a partial mitigation, not a defense against physical compromise. |
| **Memory wipes** (uncertain) | `wipe.py`: forced-memorization wipe with spot-check verification, reusing `security.py`'s exact detection-probability math against a different object (memory blocks instead of trace events). |
| **Side channel wardens** (not on track) | `warden.py`: autocorrelation-based detection of injected periodic signals, with an empirically characterized detection floor and an honestly-documented harmonic-ambiguity limitation. |

**Real but caveated (2):** `recompute.py` (an earlier, less accurate SimHash guess) and `toploc_reference.py` (the corrected, source-grounded reimplementation) both have generalization tests across unrelated configurations, relevant to the *spirit* of **Frontier recomputation algorithms** — and both have red-team tests (brute-force, adaptive hill-climbing) relevant to the *spirit* of **Recomputation red-teaming**, now run against the accurate reimplementation specifically, not only the earlier guess. `difr_reference.py` adds a third angle on item 10: a test showing that matching only the reference's single most-likely token isn't sufficient to evade detection, since Gumbel-max verification is sensitive to the whole distribution's shape. None of this attacks TOPLOC or DiFR's actual production systems, which is what these workstreams actually mean — read as "the principle is testable and holds up," not "progress on those two items."

**Not attempted at all (2, but both now have primary-source-grounded reimplementations — see below):** **Inference reproducibility workarounds** and **Recomputation algorithms**, both currently active elsewhere via TOPLOC and DiFR specifically. `toploc_reference.py` and `difr_reference.py` are from-scratch reimplementations of TOPLOC's and Token-DiFR's actual algorithms — built by cloning both repositories and reading their real source (`poly.py` and `token_difr_vllm.py`), not by working from paper summaries. `pip install toploc` hit a real ABI mismatch in this environment (documented in `spec/PROTOCOL.md` section 11); `difr_reference.py`'s core math needs no GPU or torch at all and runs identically anywhere. Neither reimplementation is bit-compatible with or a contribution to the live codebases, and this README does not claim otherwise — see `fides_colab.ipynb` for an attempt to close that gap on a platform with working GPU/torch access.

`accumulator.py` + `zk_verification.py` sit outside this table entirely — see "Two verification mechanisms" below. The 6 fully physical workstreams (passive optical TAPs, recomputation-server traffic capture, the storage-bank-to-inference-unit path, TAP installation, physical security and audits, side-channel shielding) are out of scope for any software project, this repo included. See `spec/PROTOCOL.md` section 9 for the complete, item-by-item audit.

## How it fits together

```mermaid
flowchart LR
    subgraph Device["Accelerator / host"]
        K["Kernel-level trace\n(op, timing, bytes — no weights, no tokens)"] --> F["Feature extraction\n(features.py)"]
        F --> C["Classifier\ndeclares inference / training\n(classifier.py)"]
        K --> M["BLAKE3 Merkle commitment\n— the packet-hashing tap\n(commitment.py)"]
        M --> S["Ed25519 signature\n(identity.py)"]
        C --> S
    end
    S --> R[("Registry\npublished commitments")]
    R --> V{"Verifier"}
    V -- "spot-check sample\n(chosen after commitment)" --> Device
    Device -- "revealed leaves +\nMerkle proofs" --> V
    V --> AR["Audit result:\nconsistent / caught"]
    AR --> L[("AuditLedger\nhash-chained, signed\n— tamper-evident reporting")]
```

The prover (device/tap) never reveals the full trace by default — only the small sample the verifier asks for, chosen *after* the commitment is published, so the prover can't predict and hide the bad ones. This mirrors the "packet-based verification" appendix in the [AI 2040 verification supplement](https://ai-2040.com/supplements/verification-plan#appendix-packet-based-verification), which derives the same detection-probability math this repo implements and tests against.

## Two verification mechanisms, not one

`attestation.py` and `zk_verification.py` answer the same question — does the declared workload match what actually ran? — with two different, complementary guarantees:

| | `attestation.py` (Merkle + spot-check) | `zk_verification.py` (RSA accumulator) |
|---|---|---|
| Guarantee | Bounded detection **probability** per epoch, compounding toward certainty over repeated epochs (`security.py`) | Detection **certainty**: a forbidden op's non-membership witness provably cannot be constructed if the op is present |
| What's revealed | A small random sample of raw events, chosen after commitment | Only the accumulator value and non-membership witnesses — no event ever leaves the device |
| Cost | Cheap per epoch; needs many epochs for confidence | One accumulator + 3 witnesses per epoch; RSA exponentiation cost, no sampling |
| What it can express | Anything visible in the revealed sample (timing, byte counts, ordering) | Only set-membership claims ("no forbidden op occurred") over the accumulated set |

Running `examples/demo.py` section [6] reproduces the same subtle covert-training attack from section [3] and catches it 20/20 independent trials under the accumulator, against roughly 40-50% per epoch under sampling — not because one implementation is better than the other, but because they're different kinds of guarantee. See `spec/PROTOCOL.md` section 8 for when you'd actually want each.

## Quickstart

```bash
pip install -e ".[dev]"
python examples/demo.py     # honest device, a blatant liar, a subtle attacker, and a tampered ledger
pytest tests/ -v             # 108 tests
```

The demo runs a device sneaking one covert training step into otherwise-legitimate inference epochs while declaring everything "inference." In a real run it gets caught at epoch 3 out of 15 — consistent with the model's own prediction that a single epoch at this attack size has roughly a 46% catch probability, compounding to >99.7% by epoch 10 (see `examples/demo.py` section 5, and `spec/PROTOCOL.md` section 5).

## What's real here and what isn't

This is a **software testbed**, not hardware, and it should be read that way:

- `trace.py` **simulates** kernel-level execution traces with the statistical shape training and inference workloads are documented to have (backward-pass kernels, optimizer writes, KV-cache growth, gradient vs. activation all-reduce patterns). It does not hook into a real profiler (CUPTI/Nsight) or real GPU traffic. Swapping in a real trace source behind the same `ExecutionEpoch` interface is the natural next step and is the actual "not started" engineering work.
- The commitment, signature, spot-check, and ledger logic are real, tested, and not simplified toy versions of the cryptography — BLAKE3 Merkle proofs and Ed25519 signatures work exactly as they would in a production system, just running in-process instead of on tap hardware sitting inside a datacenter.
- The RSA accumulator in `accumulator.py` is likewise real, tested cryptography, not a simulation of one — but it has a genuine, named limitation: `trusted_setup()` generates the RSA modulus itself, and whoever runs that step could in principle know its factorization and forge proofs. A real deployment needs an actual trusted third party or a multi-party ceremony for that one step; this repo is honest about not solving it, in the same docstring that explains the rest of the math.
- The classifier is intentionally simple and interpretable, not adversarially robust. Section 4 of `spec/PROTOCOL.md` is explicit about what it would take to beat it, and points at the Compute Verification Project's open competition on exactly this problem.

## Repository layout

```
src/fides/
  trace.py         synthetic kernel-event trace generator (training / inference / mixed)
  features.py      privacy-preserving statistical fingerprint of a trace
  classifier.py     interpretable inference-vs-training classifier
  commitment.py     BLAKE3 Merkle commitment + proofs — the packet-hashing tap (#3)
  identity.py       Ed25519 device identity (signing / verification)
  attestation.py    Prover / Verifier: commit, spot-check reveal, audit
  ledger.py         hash-chained, signed audit ledger — verification reporting (#13)
  security.py       detection-probability math (exact + Poisson approximation)
  accumulator.py    RSA accumulator: membership / non-membership proofs (ZK track, outside the 17)
  zk_verification.py ZKProver / ZKVerifier: certainty-based compliance proof (ZK track, outside the 17)
  determinism.py    deterministic vs. racy reduction — reproducible inference stack (#6)
  packet_reconstruction.py  order-independent message verification — network reproducibility (#7)
  recompute.py      SimHash recomputation-verification construction — spirit of #9/#10
  server_attestation.py  challenge-response software heartbeat — recomputation server security (#11)
  wipe.py           forced-memorization memory wipe + spot-check — memory wipes (#15)
  warden.py         autocorrelation-based covert-signal detection — side-channel wardens (#17)
  toploc_reference.py  faithful reimplementation of TOPLOC's real algorithm, read from its source (#5/#8, see honest caveat above)
  difr_reference.py    faithful reimplementation of Token-DiFR's seed-synchronized Gumbel-max scheme, read from its source (#5/#8, same caveat)
  protocol.py       Tap: wires prover + verifier + registry + ledger together
spec/PROTOCOL.md     RFC-style writeup: threat model, math, limitations, full 17-item audit
docs/ARCHITECTURE.md  the diagram above plus a walk through each module
examples/demo.py      end-to-end runnable demo (sampling vs. ZK mechanisms)
fides_colab.ipynb     runs everything above in Colab/Kaggle, and attempts pip install toploc on a real GPU/torch stack (see section 11)
CONTRIBUTING.md        where help is actually useful, and the ground rules for not overclaiming
.github/workflows/tests.yml  CI: full suite + demo, Python 3.10-3.12, on every push and PR
tests/                108 tests, all passing
```

## Try it without installing anything

`fides_colab.ipynb` runs the full test suite, the demo, and both TOPLOC/DiFR reimplementations in Colab or Kaggle — no local setup. It also retries the real `pip install toploc` from section 11 on a platform with a working GPU/torch stack, which this repo's original development environment didn't have. Upload it to [Colab](https://colab.research.google.com/) or a new Kaggle notebook, paste in your repo URL after pushing, and run top to bottom.

## References

- Shavit, 2023. [What does it take to catch a Chinchilla?](https://arxiv.org/abs/2303.11341)
- Wasil et al., 2024. [Verification Methods for International AI Agreements](https://arxiv.org/abs/2408.16074)
- Baker et al., 2025 (RAND). [Verifying International Agreements on AI](https://www.rand.org/pubs/working_papers/WRA4077-1.html)
- Petrie et al., 2025. [Flexible Hardware-Enabled Guarantees (flexHEG)](https://arxiv.org/abs/2506.15093)
- Scher & Thiergart, 2025. [Mechanisms to Verify International Agreements About AI Development](https://arxiv.org/abs/2506.15867)
- Harack et al., 2025 (Oxford AIGI). [Verification for International AI Governance](https://aigi.ox.ac.uk/publications/verification-for-international-ai-governance/)
- Rinberg et al., 2025. [Verifying LLM Inference to Detect Model Weight Exfiltration](https://arxiv.org/abs/2511.02620) — `security.py`'s Poisson approximation is tested against this derivation.
- Ong et al., 2025. [TOPLOC: A Locality Sensitive Hashing Scheme for Trustless Verifiable Inference](https://arxiv.org/abs/2501.16007) ([code](https://github.com/PrimeIntellect-ai/toploc))
- Karvonen et al., 2025. [DiFR: Inference Verification Despite Nondeterminism](https://arxiv.org/abs/2511.20621) — the "Token-DiFR" recomputation scheme referenced in the AI 2040 SITREP.
- Karvonen et al., 2025. [DiFR: Inference Verification Despite Nondeterminism](https://arxiv.org/abs/2511.20621) ([code](https://github.com/adamkarvonen/difr)) — the "Token-DiFR" scheme `difr_reference.py` reimplements from source.
- Cankaya, 2026. [Bit-Exact AI Inference Verification Without Performance Tradeoffs](https://arxiv.org/abs/2606.00279)
- [AI 2040: Plan A — Verification Plan](https://ai-2040.com/supplements/verification-plan)
- [Amodo Design — AI 2040 Plan A Verification SITREP](https://amododesign.com/ai-verification/plan-a-sitrep/)
- Benaloh & de Mare, 1993. One-Way Accumulators: A Decentralized Alternative to Digital Signatures. EUROCRYPT '93.
- Barić & Pfitzmann, 1997. Collision-Free Accumulators and Fail-Stop Signature Schemes Without Trees. EUROCRYPT '97.
- Li, Li & Xue, 2007. Universal Accumulators with Efficient Nonmembership Proofs. ACNS 2007 — `accumulator.py`'s non-membership witness construction.

## Contributing

See `CONTRIBUTING.md` for where help is actually useful right now, and the ground rules this repo tries to hold itself to about not overclaiming coverage.

## License

MIT — see `LICENSE`.
