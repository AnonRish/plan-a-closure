<div align="center">

# AI 2040 Verification

**A working implementation of pieces of the compute-governance verification architecture proposed in the AI Futures Project's [*AI 2040: Plan A*](https://ai-2040.com).**

Real trained model. Real server. Real red-team attacks against that real server. Real bugs, found and reported, not quietly fixed and left out.

[![Status](https://img.shields.io/badge/status-all%2030%20sections%20drafted-brightgreen)](#progress)
[![Progress](https://img.shields.io/badge/sections-30%2F30-blue)](#progress)
[![CI](https://github.com/AnonRish/ai-2040-verification/actions/workflows/ci.yml/badge.svg)](https://github.com/AnonRish/ai-2040-verification/actions/workflows/ci.yml)
[![Rust](https://img.shields.io/badge/rust-tap__reader-CE422B?logo=rust&logoColor=white)](./tap_reader)
[![Python](https://img.shields.io/badge/python-DiFR%20server-3776AB?logo=python&logoColor=white)](#repository-layout)
[![C](https://img.shields.io/badge/C-memory%20wipe%20daemon-00599C?logo=c&logoColor=white)](./wipe_daemon.c)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](#license)

</div>

---

This is not a slide deck describing what a verification system *would* do. It's an attempt to actually build the pieces that are buildable in a sandbox with no GPU and one CPU core: a small but genuinely trained character-level language model, a real FastAPI + PostgreSQL inference-verification server, a real Rust packet-capture and hashing pipeline, real LoRA backdoor adapters, real red-team scripts run against the real server above, and a real tamper-evident log with real signature verification.

**Status: all 30 planned sections are drafted.** "Drafted" is the operative word — every section has real, tested code and a stated self-check, but this is a first complete pass, not an externally reviewed or polished final document. See [Progress](#progress) below, or the authoritative table at the top of [`ai-2040-verification.md`](./ai-2040-verification.md).

## Table of Contents

- [Why This Exists](#why-this-exists)
- [What's Actually Here](#whats-actually-here)
- [Architecture](#architecture)
- [Notable Findings](#notable-findings)
- [Progress](#progress)
- [Repository Layout](#repository-layout)
- [Getting Started](#getting-started)
- [Known Limitations](#known-limitations)
- [Sources and Prior Work](#sources-and-prior-work)
- [License](#license)

## Why This Exists

The AI Futures Project's *AI 2040: Plan A* — specifically its [Verification Plan supplement](https://ai-2040.com/supplements/verification-plan) (Romeo Dean, July 2026) — sketches a compute-governance regime modeled loosely on arms-control treaty inspection: passive taps on datacenter networks, statistical recomputation of sampled inference requests, verifier-issued randomness so a prover can't game what gets checked, periodic memory wipes, and physical-security auditing modeled on IAEA safeguards concepts (Significant Quantity, Detection Probability, conversion time).

That's a design document. This repo is an attempt to find out how much of it survives contact with an actual sandbox: what's genuinely buildable and testable today, where the real bottlenecks are (a link-budget problem that has no COTS solution yet; a disk-write collapse that shows up on three independently-measured storage systems; a detection scheme with a real, quantified blind spot), and what has to stay an honest design estimate because the hardware to test it doesn't exist here.

## What's Actually Here

Every section of [`ai-2040-verification.md`](./ai-2040-verification.md) follows the same discipline: a technical write-up, a working and tested code artifact, and a **Self-check** that states plainly what was demonstrated versus what's still a design estimate. A few things that discipline actually caught, rather than papered over:

- A stream-reassembly bug where a CRLF split exactly across a TCP segment boundary hung the parser — caught by a byte-at-a-time fragmentation test, fixed, documented.
- A distillation run that used hard-label gradients where soft KL-divergence against the teacher was required — a real bug in an early training pass, not a modeling choice.
- A `-O2` optimization that silently dead-code-eliminated the very fields a "certificate" mechanism was supposed to be certifying, letting two *differently declared* workloads compile to bit-identical binaries.
- A separate AI-generated document's "512-bit RSA" implementation that, when actually run, produced `Baseline Check: False` on its very first entry — the modulus was 79 bits, not 512, and `p × q` didn't equal the stated `n`.
- A composition bug in this project's *own* prior code, caught by later auditing it against its own stated principles: one signing key was reused across two decisions meant to be independent (training-workload approval and release approval), so compromising it defeated both at once. Fixed in the shipped file, not just noted.

Sandbox constraints (no GPU, no reachable path to pretrained weights, one logical CPU, ~5GB free disk) are stated explicitly wherever they bound a result, rather than smoothed over.

## Related repository: infrastructure and physical evidence

[`AnonRish/continental-load-registry`](https://github.com/AnonRish/continental-load-registry) is a complementary public-data research repository. It focuses on the infrastructure/accounting side of the problem: large-load and interconnection records, Epoch AI data-center cross-references, physical/remote-sensing observations, and explicit research/provenance workflows. This repository focuses on concrete verification mechanisms such as inference recomputation, passive network observation, red-teaming, and operational trust. Neither repository by itself constitutes an international verification system or a certification of Plan A.

## Architecture

<img src="./docs/architecture.svg" alt="System topology: storage bank, inference units, passive optical splitter, trust boundary, recomputation server" width="620">

A prover's facility (storage bank, inference units, a passive optical splitter with no logic, firmware, or state) mirrors frontend traffic across a one-way trust boundary into a verifier-controlled recomputation server, which re-runs sampled requests under a verifier-issued seed and scores deviation against a per-model calibrated threshold, logged to a hash-chained, signed record. `§` references in the diagram point to the section of `ai-2040-verification.md` that builds and tests that piece.

## Notable Findings

Six results that came out of actually running things, not from reasoning about them in the abstract:

| Finding | Section |
|---|---|
| A trigger-conditional LoRA backdoor is **completely invisible** to output-level verification while dormant (100% pass rate, indistinguishable from honest) — and collapses to the maximum deviation ceiling (~7.98 of 8.0) the instant the trigger appears. | [§9](./ai-2040-verification.md) |
| Summing the same 4,096 float32 values under 12 different reduction groupings — standing in for a GPU kernel picking different shapes per batch size — produced **9 distinct bit-level results** from one canonical mathematical sum. A single fixed reduction tree collapsed that to exactly 1, reproducing at CPU scale the mechanism Thinking Machines Lab found on real GPUs. | [§7](./ai-2040-verification.md) |
| An aggregate AUC above 0.99 across every tested temperature *looked* like clean separation — but the actually-defensible threshold showed cross-family leakage climbing from 7.5% at T=0.3 to 17.5% at T=1.6. Temperature turned out to be a real detectability lever, not just a decoding parameter. | [§11](./ai-2040-verification.md) |
| A steganographic attacker spending up to half its tolerance budget per token smuggled ~75% of a 20-bit hidden payload through a 30-token output while passing every deviation check at 100% — caught only by a secondary, per-token distribution check running at roughly 124,000× the honest baseline rate. | [§10](./ai-2040-verification.md) |
| Every attacker tested against the sampling gateway's keyed PRF — including a logistic regression trained on 480,000 labeled examples — stayed within 0.005 of an uninformative AUC of 0.5. An oracle handed the actual key scored a perfect 1.0. The unpredictability holds because of key secrecy, not algorithm secrecy, demonstrated rather than assumed. | [§3](./ai-2040-verification.md) |
| A real disk-write collapse-after-burst was independently reproduced on **three different storage systems** — this sandbox's own cloud block storage, a second AI system's separate sandbox, and cited real NVMe hardware — at three different magnitudes but the same qualitative shape, which is worth more than any single number in the comparison. | [§15](./ai-2040-verification.md) |
| Modeling how many physical network taps to install, rack-granularity and server-granularity tapping turned out to land on **nearly identical campaign-detection probability** (0.242 vs. 0.242 at one tested scale) despite one needing 6× as many bypass events as the other — because in an inspector-throughput-limited regime, going finer multiplies required events by exactly the factor it divides each event's catch rate by. What actually mattered wasn't granularity at all, but whether facility-level tapping broke out of that regime entirely (it did, and stayed at a flat ~3% detection probability regardless of how much of the facility a campaign covered). | [§22](./ai-2040-verification.md) |
| Testing whether output-level verification catches a model that behaves differently once it detects it's being evaluated split into two genuinely different cases with different answers: a bolted-on adapter that activates on an eval-like cue is real and catchable (mean deviation 7.97 vs. 0.00, exactly §9's backdoor pattern re-confirmed on live checkpoints) — but if that conditional behavior is *learned into the declared, correctly-served weights themselves*, there is no deviation of any size for any threshold to catch, because every output is genuinely faithful to what was declared. Not a sampling-luck gap like the others — a structural one. | [§24](./ai-2040-verification.md) |
| Building a toy Proof-of-Learning replay check (train in logged segments, verifier independently replays a sampled one) surfaced a real, non-adversarial tension rather than just a security property: a *second, honestly-trained* run spending the exact same real compute on the exact same data, differing only in random data order, produces a completely different checkpoint hash — full legitimate work that a naive exact-match verifier would reject as fraud. Distinguished carefully from the actual published vulnerability in this space (Fang et al.'s spoofing attack, which this toy scale can't faithfully reproduce) rather than let the simpler demo imply broader coverage than it has. | [§25](./ai-2040-verification.md) |
| Real zero-knowledge-proof-of-training benchmarks (zkLoRA, 2025) measure ~122–249 seconds to prove a single training step at the smallest possible batch size — one data sample. Extrapolated under a clearly labeled, deliberately conservative assumption (50,000 steps, nowhere near real frontier pretraining scale), that's **70 to 144 days of proving alone**, sequentially, before counting real production batch sizes or the training itself. Inference-side ZK proving is genuinely closing in on practical (a 13B-parameter model's full inference proof now takes under 15 minutes); training-side isn't within the same order of magnitude yet, and the field's own current papers say why: it's a research gap, not an engineering backlog. | [§26](./ai-2040-verification.md) |
| Auditing this document's *own* prior code for the "do trust roots stay independent" question turned up a real instance, not a hypothetical: §24's release-authority code reused one signing key across two decisions the document's own narrative wants independent (training-workload approval and release approval). One compromised key defeated both. Fixed directly in the shipped file — two independent keys — confirmed the fix cost nothing (all 5 of §24's original tests still pass) and genuinely contained a simulated compromise to just the role whose key was actually stolen. | [§27](./ai-2040-verification.md) |
| Mapping this document's own real verification outputs into legal compliance categories (COMPLIANT / MINOR_DEVIATION / MATERIAL_BREACH) made §11's calibration finding suddenly much higher-stakes: run through an uncalibrated τ=0.3 (used illustratively in earlier sections), a genuinely dishonest cross-family model reads as **96–99% legally COMPLIANT**. Run through §11's own actually-recommended τ=0.02, that flips to just 7.5–17.5% compliant, with the rest MATERIAL_BREACH. Same real per-trial data, same model, same schema — the only variable was which threshold got fed in, which is exactly the point: a conformity-assessment layer is only as meaningful as the calibration work done before it. | [§28](./ai-2040-verification.md) |
| Red-teaming the claim that "embedded auditors... might reach sufficient assurance" without any purpose-built hardware, by re-running §22's own Poisson-process detection math with only the auditor-cadence input changed: monthly embedded review cuts expected discovery time from 912 days (§22's quarterly international-sampling baseline) to 30 — a real, ~30x improvement from cadence alone. But the same test made the honest limit unmissable: that math assumes an auditor's presence converts directly into a real chance of catching something, true by physical construction for §2's passive tap, and not automatically true for a human who only sees what they're shown. | [§29](./ai-2040-verification.md) |
| Closing the whole document on the hardest-sounding problem — undeclared compute nobody knows exists — by verifying two real, checkable claims rather than taking them on faith: the source material's "90% of chip fabs are new every 2 years" figure computes to 88.9% under sustained 3x/yr growth (with a clean closed form, 1 − 3⁻² = 8/9, confirming it's a real property of exponential growth, not an estimate); and reusing §20's own power-envelope function against a real, demonstrated satellite thermal-detection capability (SatVu resolved a real 700MW datacenter's heat signature from orbit, Dec 2025) showed the source's own median dark-compute estimate, if concentrated in one facility, would draw *more* power than that already-detected case — which is exactly why the source's own point about it being spread thin, not concentrated, is load-bearing. | [§30](./ai-2040-verification.md) |

## Progress

<!-- Keep in sync with the table at the top of ai-2040-verification.md -->

| Part | Sections | Status |
|---|---|---|
| I — Architecture | §1 | ✅ Drafted |
| II — Correctness | §2–§14 | ✅ Drafted |
| III — Completeness | §15–§18 | ✅ Drafted |
| IV — Physical & Operational Trust | §19–§23 | ✅ Drafted |
| V — Beyond Inference-Only | §24–§25 | ✅ Drafted |
| VI — The Frontier | §26 | ✅ Drafted |
| VII — Holding Together | §27–§28 | ✅ Drafted |
| VIII — Other Tracks | §29–§30 | ✅ Drafted |

Full section-by-section detail (each with its own **Self-check** and **Sources used**) lives in [`ai-2040-verification.md`](./ai-2040-verification.md).

## Repository Layout

```
ai-2040-verification.md   The document. Every drafted section: write-up, self-check, sources.
docs/
  architecture.svg          The topology diagram embedded above.
*.py                       DiFR verification server, the trained character-LM, LoRA backdoor
                           adapters, the red-team suite, calibration sweeps, tamper-evident log.
*.json                     Real output from actual runs of the scripts above.
wipe_daemon.c               Memory-wipe daemon (§15) — AES-NI DAG labeling + full overwrite.
                           verifier.py independently re-checks its output with a maintained
                           crypto library rather than sharing code with the daemon.
tap_reader/                 Rust crate: passive-tap parsing, hashing, HTTP chunked/SSE stream
                           reassembly, a lock-free evidence ring buffer, the sampling gateway,
                           and Merkle/epoch commitments (§2–§4). Has its own README.
```

## Getting Started

**Rust (`tap_reader/`)** is fully self-contained:

```bash
cd tap_reader
cargo build --release
cargo test --release      # 17/17 unit tests
```

See [`tap_reader/README.md`](./tap_reader/README.md) for the individual benchmark binaries.

**Python** needs `pip install -r requirements.txt`. A few scripts depend on artifacts generated by *other* scripts rather than checked in here — consistent with not committing large binaries:

1. `train.py` needs `shakespeare.txt` (the tiny-shakespeare corpus: `curl -sSL -o shakespeare.txt https://raw.githubusercontent.com/karpathy/char-rnn/master/data/tinyshakespeare/input.txt`) and produces `charlm.pkl` + `vocab.pkl`.
2. `train_variants.py` (needs `charlm.pkl`) produces the same-family and cross-family checkpoints used throughout the red-team and calibration sections.
3. `lora.py` (needs `charlm.pkl` + `vocab.pkl`) produces the backdoor adapters.

Run those three, in that order, before anything that loads a `.pkl` checkpoint (`server.py`, `test_suite.py`, `redteam.py`, `calibration.py`, and others). `db.py` expects a local PostgreSQL instance matching the DSN at the top of that file.

**One command:** `make test` downloads the corpus, runs the three steps above, runs the experiment suite, and asserts the README's headline findings (`tests/test_headline_invariants.py`). About a minute on one CPU core; needs no GPU and no PostgreSQL.

## Known Limitations

Stated here the same way they're stated throughout the document, not softened:

- **No GPU, anywhere.** The "trained language model" is a small NumPy character-level model (8-character context, 65-token vocabulary) — real weights, real backprop, real learned structure, and nowhere near a frontier model's capability. Every claim in the document is about the *verification protocol*, never about this standing in for a frontier model.
- **One logical CPU, no DPDK-capable NIC.** Rust throughput numbers are a measured software ceiling on this container, not a real-NIC/real-DMA capture number — stated explicitly at every point the document uses them.
- **A known, unclosed detection gap.** §9 found and §10 confirmed that a dormant trigger-conditional backdoor is structurally invisible to output-level statistical verification. This isn't hidden — it's the reason §10 (red-team) and §12 (anti-steganography) exist.
- **Several named gaps stay open on purpose.** §13's raw-instruction bypass, §26's training-scale ZK-proving cost, §27's "does the whole system compose soundly" question, and §30's real sensor-noise-floor gap are each stated as unresolved rather than papered over — the document's own position throughout is that naming a limitation precisely is worth more than a mechanism that doesn't actually close it.
- **"Drafted" means a real first pass, not a finished document.** All 30 sections have working code and a stated self-check, but none of it has had independent external review — the same caveat the document applies to its own sandbox measurements applies to the document as a whole.

## Sources and Prior Work

- AI Futures Project, [*AI 2040: Plan A*](https://ai-2040.com) — Verification Plan supplement (Romeo Dean), July 2026.
- Karvonen, Reuter, Rinberg, Marks, Garriga-Alonso, Warr, ["DiFR: Inference Verification Despite Nondeterminism,"](https://arxiv.org/abs/2511.20621) arXiv:2511.20621.
- He et al. (Thinking Machines Lab), "Defeating Nondeterminism in LLM Inference," Sep 2025 — the batch-invariant-kernels finding §7 reproduces at CPU scale.
- Bursuc, Gil-Pons, Mauw, Trujillo-Rasua, ["Software-Based Memory Erasure with Relaxed Isolation Requirements,"](https://arxiv.org/abs/2401.06626) arXiv:2401.06626, CSF 2024 — the memory-wipe daemon's security argument.
- `karpathy/char-rnn` (tiny-shakespeare corpus) — training data for the stand-in language model.

Every drafted section names its own sources in full at the point it uses them — this list is the recurring ones, not the complete bibliography.

## License

Apache-2.0 — see [`LICENSE`](./LICENSE). This covers the code and the write-up (`ai-2040-verification.md`).

## Current Plan A track integration

The detailed 30-section research notebook is now connected to executable track-specific prototypes in the companion repositories. See PLAN_A_TRACK_INTEGRATION.md for the current cross-repository map and the exact software-vs-external validation boundary.
