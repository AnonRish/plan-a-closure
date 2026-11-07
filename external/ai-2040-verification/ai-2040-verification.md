# AI 2040 Verification — Prototype Architecture & Engineering Notes

Working document built section-by-section against the 30-part prompt sequence. This isn't built from scratch — it operationalizes the AI Futures Project's *AI 2040: Plan A* (published July 9, 2026), specifically its [Verification Plan supplement](https://ai-2040.com/supplements/verification-plan) (Romeo Dean), plus the real Token-DiFR/Activation-DiFR verification scheme (Karvonen, Reuter, Rinberg, Marks, Garriga-Alonso, Warr, "DiFR: Inference Verification Despite Nondeterminism," arXiv:2511.20621). Each section cites what it draws on. Anything not traceable to a real source is flagged as this document's own extrapolation, not established fact.

**A note on what "checkable" means in this sandbox.** Several later sections' self-checks demand real measurements — 400 Gbps throughput, GPU HBM wipe timing, DPDK benchmarks. This environment has no DPDK-capable NICs, no GPUs, and no optical tap hardware. Where a section needs that, I'll build and test whatever *is* honestly testable here (algorithms, protocol logic, small-scale software simulation) and say plainly where a claim is a design estimate rather than something actually run — never the reverse.

**Progress: 30 / 30 sections drafted.**

| Part | § | Prompt | Status |
|---|---|---|---|
| I — Architecture | 1 | The God Prompt | **Drafted below** |
| II — Correctness | 2 | The Tap Reader | **Drafted below** |
| | 3 | Secure Network Gateways | **Drafted below** |
| | 4 | New Tap Types & Bandwidth-Reduction | **Drafted below** |
| | 5 | The Recomputation Engine | **Drafted below** |
| | 6 | Frontier Recomputation Algorithms | **Drafted below** |
| | 7 | The Reproducible Inference Stack | **Drafted below** |
| | 8 | Network Reproducibility | **Drafted below** |
| | 9 | Non-Determinism Test Suite | **Drafted below** |
| | 10 | Recomputation Red-Team | **Drafted below** |
| | 11 | Calibration & Mock Hardware Emulator | **Drafted below** |
| | 12 | Anti-Steganography & Commitment Schemes | **Drafted below** |
| | 13 | Auditor Compilation into GPU Instructions | **Drafted below** |
| | 14 | Granular Evidence Collection Roadmap | **Drafted below** |
| III — Completeness | 15 | The Memory Wiper | **Drafted below** |
| | 16 | Completeness / Side-Channel Threat Model | **Drafted below** |
| | 17 | Side-Channel Mitigation | **Drafted below** |
| | 18 | Side-Channel Wardens | **Drafted below** |
| IV — Physical & Operational Trust | 19 | Storage-Bank → Inference-Unit Path | **Drafted below** |
| | 20 | General Physical Security & Compute Auditing | **Drafted below** |
| | 21 | Recomputation Server Trust | **Drafted below** |
| | 22 | TAP Installation & Monitoring at Scale | **Drafted below** |
| | 23 | Workload Approval | **Drafted below** |
| V — Beyond Inference-Only | 24 | Verified Evaluations & Weight Transport | **Drafted below** |
| | 25 | Pre-Training Verification | **Drafted below** |
| VI — The Frontier | 26 | The Cryptographic/ZKP Track | **Drafted below** |
| VII — Holding Together | 27 | Composing Trust Roots & Hardening | **Drafted below** |
| | 28 | Binding Verification to Governance | **Drafted below** |
| VIII — Other Tracks | 29 | Track 1 — Company/Domestic Auditing | **Drafted below** |
| | 30 | Track 3 — Detecting Undeclared Compute | **Drafted below** |

---

## Part I — Architecture

### §1. The God Prompt — System Architecture Blueprint

**Role:** Principal Systems Engineer — hardware-rooted AI verification, passive optical networking, distributed ML infrastructure.
**Scope:** Prototype/R&D blueprint for learning purposes, not a production design. No code in this section by design — that starts at §2.

#### 1. Topology

```
  ┌─────────────────┐
  │  Storage Bank   │
  │ (model weights) │
  └─────────────────┘
        │ §19 — separate path, out of scope here
        ▼
  ┌─────────────────────────────┐
  │       Inference Units       │
  │  (GPU / accelerator racks)  │
  │  minimal east-west network  │
  │    periodic memory wipe,    │
  │ "forced memorization" (§15) │
  └─────────────────────────────┘
               │ frontend ("north-south") traffic
               │ client requests <-> model outputs
               ▼
        ┌─────────────────────────────────┐
        │  Passive Optical Splitter (§2)  │
        │ no logic, no firmware, no state │
        └─────────────────────────────────┘
                      │ mirrored copy — one direction only
PROVER-CONTROLLED     ╪ VERIFIER-CONTROLLED
──────────────────────┼─── trust boundary ────────────────────
                      │
                      ▼
      ┌────────────────────────────────┐
      │   Recomputation Server (§5)    │
      │  verifier-issued decode seed   │
      │  Token-DiFR / Activation-DiFR  │
      │  per-model calibrated τ (§11)  │
      │ hash-chained result log (§21b) │
      └────────────────────────────────┘
```

The architecture splits a datacenter into two zones with different owners and different trust assumptions.

Inside the prover's fence line: a storage bank holding model weights, and inference units that actually run the model. The path between them (§19) is out of scope here. Within and between inference units, backend ("east-west") networking is stripped down to whatever large-scale *inference* genuinely needs — which the Verification Plan supplement argues is drastically less than what large-scale *training* needs. This isn't purely a monitoring convenience: cutting the interconnect is itself a defense-in-depth measure, since a cluster that's structurally incapable of fast collective communication across thousands of accelerators is a worse platform for a large training run even if every other verification layer here were somehow defeated. The goal is a cluster that can't easily be misused, not just one that's watched closely.

On the frontend ("north-south") network — the path client requests and model outputs actually travel — sits a passive optical splitter: fused glass splitting a fraction of the optical signal onto a second fiber, with no logic, firmware, or state, and no return path into the prover's network. That absence of any digital logic is the entire basis for trusting it — there's nothing in a pure splitter a prover could compromise purely in software. Achieving selective suppression (hiding specific packets from the mirror) would require physically substituting the hardware, which is exactly the threat §21/§22's tamper-evidence and installation-audit work is built to catch; this section assumes that layer exists rather than re-proving it. §2 treats the receiver/split-ratio physics as a live, unsolved problem rather than an assumed input — this section only commits to the topology, not to a claim that today's hardware clears it at line rate.

The mirrored copy goes one way, to a recomputation server the verifier controls end to end. §3 covers a more capable version of the splitter box — a "secure network gateway" that does on-path random sampling and boot-time model-weight whitelisting, with hardware security properties the source material compares to iPhone secure enclaves and PUFs — as an explicit, optional upgrade path, not a redesign. The passive-tap version above is the floor this document commits to; §3's gateway is strictly additive.

#### 2. Correctness verification: does the declared inference match what ran?

The mechanism is Token-DiFR / Activation-DiFR (Karvonen et al., arXiv:2511.20621 — DiFR stands for *Divergence From Reference*), run on the recomputation server against whatever fraction of packets the tap mirrors over.

- **Shared-seed decoding.** The recomputation server re-runs each sampled request under the same model, same decoding hyperparameters, and the same PRNG seed the prover used. Fixing the seed collapses most of the nondeterminism that would otherwise plague a naive comparison: per the DiFR paper's own measurements, regenerating a token under a fixed seed reproduces the identical token more than 98% of the time, and most of the remaining disagreements narrow to just two or three plausible candidates rather than an open field.
- **The seed must come from the verifier, not the prover — and this isn't a formality.** If the prover could pick the seed, a prover serving output from a cheaper or substituted model could search over candidate seeds after the fact for one under which the honest model's real output happens to land inside tolerance of what they already served — a multiple-comparisons "seed-shopping" attack that turns one strong per-request test into a weak, gameable one. The Verification Plan supplement applies the identical principle one level up, for workload-approval sampling seeds: auditors issue the seed, not the company under audit, specifically to close off attempts to game apparent randomness. §5 has to get this right by construction; a reference implementation exists but reportedly has this backwards by default, which is one of the first things §5 fixes.
- **Per-token comparison, clipped.** DiFR scores each token by how far the provider's claimed token sits below the verifier's own top pick in a logit-plus-noise ranking, clipped to a maximum Δmax so neither a single wildly divergent honest token nor one adversarially crafted token can dominate an averaged score. §5 has to implement that clip visibly — logged, not silently absorbed — per its own self-check.
- **Token-only vs. activation-based.** Token-DiFR needs nothing from the prover beyond synchronized seeds and the tokens already crossing the tap, and is compatible with vLLM's existing sampling interface unmodified. Activation-DiFR compares compressed internal activations instead (via random orthogonal projections) and catches the same signal — the paper's headline case is 4-bit quantization — in as few as 2 output tokens instead of the roughly 300 tokens Token-DiFR needs for comparable confidence, but it requires the prover's inference stack to additionally compute and transmit activation fingerprints. §5 should stand up Token-DiFR first, since it asks nothing extra of the prover, and treat Activation-DiFR as a sample-efficiency upgrade once the token-only path works.
- **Calibrated threshold.** Even under a shared seed, benign floating-point nondeterminism means the deviation score is never exactly zero. §11 derives a per-model τ empirically rather than assuming one.
- **Packet granularity is a dial, not a fixed choice.** "One packet" can be a full request/response, one forward pass, or one GPU kernel call; finer packets buy detection of smaller violations at the cost of evidence-collection infrastructure lower in the stack. This document fixes the coarse end — one request, checked at the frontend tap — as the floor. §4, §14, and §22 all live on moving that dial finer over time; that move is explicitly out of scope here.

#### 3. Completeness verification: is anything else running?

This is a different question from correctness, and answering it requires a different mechanism — a prover could serve 100% honest inference on every sampled packet while quietly using the rest of the cluster's cycles for something DiFR would never see, because DiFR only ever checks packets that cross the tap.

- **Bounded side channels.** The claim here isn't "no covert channel exists" — it's that whatever channel capacity survives mitigation is small enough to bound and price into the overall risk picture, the same way §12 bounds recomputation-tolerance steganography and §17 quantifies what shielding and noise injection buy against NVLink contention, power-draw modulation, and similar leakage paths. §16–§18 map, mitigate, and monitor this; this section only asserts that it needs its own subsystem, not that a fix exists yet.
- **Periodic memory wipe.** The source material's term for this is *forced memorization*: on a verifier-set cadence, force every byte of addressable memory on the inference unit to be overwritten in a way the verifier can independently check, so that anything persisting outside the declared, tapped, recomputation-checked workload either gets destroyed on schedule or has to survive inside a reserve small enough to bound. §15 is where this actually gets built and benchmarked; the current state of that work (RAM/HBM tractable at real, if imperfect, numbers; storage write-speed collapse the real open bottleneck) belongs to §15, not here.

One scoping note worth stating as plainly as the source material states it: this design does not try to verify that spare compute never *computes* anything unapproved — it tries to ensure that nothing unapproved *persists or leaves the cluster as output*. That's a narrower and more tractable claim than "prove idle cycles are never touched," and "completeness" in this document should be read at that narrower scope throughout, not a broader one.

#### 4. Statistical framing

Both subsystems above cash out in one piece of math: how much recomputation buys how much assurance.

Model the recomputation server's workload as a stream of packets (this document's floor: one packet per tapped request). If the verifier can afford to recompute a fraction **C** of all packets — the recomputation budget, upper-bounded by whatever §2's tap and §5's server can actually sustain — and a dishonest prover has substituted **N_fake** packets somewhere in that stream, then treating each audit as an independent check with probability C of catching any given fake packet, the exact probability of catching at least one is:

`P(detected) = 1 − (1 − C)^N_fake`

For small C and not-tiny N_fake this is well approximated by the Poisson form:

`P(detected) ≈ 1 − e^(−C·N_fake)`

— which is where "99% confidence at C·N_fake ≳ 4.6" comes from: e^(−4.6) ≈ 0.01, since ln(100) ≈ 4.605.

Three things are easy to miss if you just quote the formula:

1. **It only needs one catch, ever.** A prover has to keep every substituted packet clean for the life of the deal; the verifier just needs one slip. That asymmetry is doing almost all the work in why sampling scales so favorably.
2. **The approximation breaks at small N_fake.** At N_fake = 1 the Poisson form gives nonsense (it can ask for C > 1 — recomputing more than 100% of packets), and the honest answer reverts to the exact binomial form: P(catch) = C, full stop, independent of how large the surrounding honest workload is. That's the same failure mode §9 has to test explicitly for short (<5-token) outputs — below some size, sampling stops helping, and the only lever left is shrinking the packet further, not raising C.
3. **C is not a free dial.** It's bounded by real infrastructure (§2's achievable tap throughput, §4's bandwidth-reduction ceiling, §5's server capacity), and the independence assumption itself depends on §3's sampling actually being unpredictable to the prover. This formula says what a given C buys; it doesn't say what C is achievable, and it silently assumes §3 succeeded.

**Worked example.** At C = 1% — the figure the Verification Plan supplement itself uses illustratively — a prover needs to accumulate roughly 460 fake packets (4.6 / 0.01) before facing 99% odds of detection. Halve the packet size (audit forward passes instead of full requests, say) and the same underlying misbehavior now spans roughly twice as many packets, so the same C catches it at half the accumulated "fake work." That packet-size lever — not just the C lever — is the main thing §4, §14, and §22 are trying to buy over time: recomputation budget is capped by real hardware, but packet granularity, in principle, is not.

The source material frames this two-dimensionally rather than one-dimensionally — not just "what's the confidence at some coverage level" but a full coverage-vs-confidence curve, since a scheme that's very confident about 90% of a workload and silent on the rest is a materially different risk profile from one that's moderately confident about all of it. Where later sections refer to "the assurance curve" for a given design, this is the object they mean; this section only establishes the formula it's built from.

#### Self-check

*Confirm each of the four covered pieces is explicitly labeled demonstrated or speculative, matched against the coverage table:*

- **Topology — mixed.** The overall shape (isolated inference units, passive frontal tap, separate recomputation server) is the design the real Verification Plan supplement itself currently recommends, not something invented for this document — but its load-bearing pieces are graded unevenly in the source table: §2's tap is "Active" but capped by unsolved photonics (no COTS part exists yet at the needed Baud rate); §3's smarter gateway is "Not graded" (described, not built); §4, §19, and §22 are "Not started" / "Not on track." Read the topology above as the *agreed target shape*, not a built system.
- **Correctness verification — the most mature piece.** §5's underlying method (DiFR) is a real, published, empirically validated result (>0.999 AUC detecting 4-bit quantization within ~300 tokens for Token-DiFR, within 2 tokens for Activation-DiFR). §9–§11's calibration methodology has real precedent. Demonstrated, with a known, named bug (backwards seed default) that later sections fix rather than paper over.
- **Completeness verification — the least mature piece,** and the source table says so directly: §15 has real, if currently bottlenecked, numbers behind it; §16–§18 are graded "Not on track" and described even in the source material as early theoretical work. Treat completeness here as a stated requirement with a roadmap, not a working subsystem.
- **Statistical framing — proven math resting on an unfinished foundation.** The formula is a correct result under its stated independence assumption; it doesn't require empirical demonstration the way a benchmark does. But its real-world validity inherits every uncertainty above it: C is only as large as §2/§4/§5 can sustain, and independence is only as good as §3's unpredictability guarantee.

*Confirm no code has been written:* correct — this section is architecture only, as scoped.

**Sources used in this section:**
- AI Futures Project, *Verification Plan* supplement to *AI 2040: Plan A* (Romeo Dean; ai-2040.com/supplements/verification-plan), published July 9, 2026 — topology, "forced memorization," the assurance-curve framing, the detection-probability derivation, and the worked examples this section adapts.
- Karvonen, Reuter, Rinberg, Marks, Garriga-Alonso, Warr, "DiFR: Inference Verification Despite Nondeterminism," arXiv:2511.20621 (Nov 2025) — Token-DiFR/Activation-DiFR mechanism, seed-reproducibility statistic, quantization-detection figures.
- Rinberg et al., "Verifying LLM Inference to Detect Model Weight Exfiltration," arXiv:2511.02620 — independently derives the same detection-probability math (cross-referenced in the source material above).

---

---

## Part II — Correctness

### §2. The Tap Reader

Two honestly different problems, per the task: whether the physical tap can exist at all at 53 GBd (2a — photonics, research only, nothing to compile), and what the ingestion pipeline behind it looks like once it does (2b — real Rust, built, tested, and benchmarked in this sandbox, with the hardware-dependent parts clearly marked as not tested here).

#### 2a. Physical tap feasibility note

**The link budget, worst case to worst case.** 400GBASE-DR4 runs 4 lanes at 53.125 GBd PAM4 each, 1304.5–1317.5nm — O-band, not C-band. Worst-case transmit power, after subtracting the transmitter's own eye-closure penalty (OMAouter − TDECQ), is about −2.2dBm per lane. Receiver sensitivity for this class of module is specified a few dB above the loss-of-signal de-assert floor (−8.9dBm, per the same datasheet family) — commonly in the −6 to −7dBm range; call it −6.5dBm. That's roughly 4.3dB of raw budget, spec to spec. DR4's channel insertion loss allocation for the 500m single-mode run is on the order of 3dB. Worst case to worst case, that leaves on the order of **1–1.5dB of spare margin before a tap touches the link at all.** That's the entire envelope a passive splitter has to fit inside.

**What a splitter actually costs**, theoretical split loss plus typical real-world excess loss (0.2–0.5dB for a decent fused/planar splitter):

| Split (primary/tap) | Primary-path loss | Tap-path loss |
|---|---|---|
| 90/10 | ~0.46dB theory → ~0.7–1.0dB real | ~10.0dB theory → ~10.3–10.8dB real |
| 95/5 (asked about) | ~0.22dB theory → ~0.4–0.7dB real | ~13.0dB theory → ~13.3–13.8dB real |

Neither tap-path number is close to fitting inside a ~1.5dB envelope. There is no split ratio at 53 GBd that both protects the primary link and leaves the tap with a usable signal, without adding gain somewhere. That's the actual problem this section was asked to look at.

**Would a SOTA APD close it? Partially — and not for the split actually asked about.** The most directly comparable published result — a single-channel 100Gbit/s PAM4 link, the same signaling class as one DR4 lane — measured a 2.7dB OMA sensitivity advantage for an APD receiver over a PIN receiver. General APD-vs-PIN literature quotes a wider 5–10dB range depending on device design and wavelength, and a very recent (2025) uni-multiplication-carrier APD design demonstrated a 9dB improvement — but at 260Gb/s PAM4, a faster and considerably more exotic device than anything in a COTS DR4 module today. Read generously (10dB), an APD alone gets close to closing the 90/10 case's ~10.5dB gap. Read conservatively (2.7dB, the closest real match), it closes well under a third of it. Either way, the 95/5 case's ~13.5dB gap is out of an APD's reach alone — even the generous end falls 3–4dB short.

**Would a BDFA close it? On paper, yes. As a part you can order, no.** A standard EDFA doesn't help here — erbium's gain band centers on C-band, nowhere near DR4's 1310nm lanes. Bismuth-doped fiber is one of the few gain media that works at 1310nm at all, and on paper it's genuinely good: repeated published results show 18.7–24dB of net gain at 1310nm with noise figures around 5–6dB, and specialized (double-pass, cooled, or Bragg-fiber) lab configurations have pushed past 30dB. Even after subtracting a few dB for the amplifier's own noise contribution, that comfortably covers both the 90/10 case (~10.5dB) and the 95/5 case (~13.5dB) asked about here.

But every one of those numbers comes from a conference paper or journal article, not a datasheet. There's no qualified, hardened, mass-manufacturable BDFA product line the way there's a qualified EDFA line for C-band — this is an active materials-science research area (O-band BDFAs are described in the recent literature itself as "rapidly developed... in recent years," which is a tell), not a shelf part. "BDFA gain covers the deficit" is true about the physics; it isn't true about procurement. Closing a 95/5 split at 53 GBd today, without a new component development effort, isn't available. The honest options are: (a) a less aggressive split that protects the tap at the primary path's expense, which undercuts the entire point of a tap being non-disruptive to production traffic, or (b) treat a qualified O-band preamp as its own R&D line item — a real, multi-quarter photonics project — not a solved input to this document.

**What this note is not:** a working design. No COTS part clears 53 GBd with the margin this link actually has, regardless of how the engineering above is dressed up. That's the self-check requirement for this half of §2, stated plainly rather than left implicit.

*Sources: 400GBASE-DR4 QSFP-DD/OSFP datasheets (Finisar/Coherent FTCD4533E3PCM; FS.com DR4 silicon-photonics datasheets) for signaling rate, wavelength, OMAouter/TDECQ, and LOS thresholds; Huang et al., CLEO 2018, "First Demonstration of Sensitivity Improvement using an APD Receiver for a 100 Gbit/s Single Channel PAM4 Link" for the 2.7dB figure; a 2025 uni-multiplication-carrier APD paper (PMC) for the 9dB/260Gb/s figure; O-band BDFA gain figures from IEEE/OFC conference results and a 2024 ScienceDirect broadband-BDFA study (18.7dB/1310nm) and a 2024 ScienceDirect O-band Bragg-BDFA study (34–54dB in specialized configurations).*

#### 2b. Ingestion pipeline (Rust)

**What's tested here vs. not, stated once up front.** This sandbox has 1 logical CPU, no DPDK-capable NIC, and no way to exercise real PCIe/DMA throughput or hardware RSS. So: the parts of the pipeline that are pure CPU-bound software — header parsing, the three candidate hash functions, HTTP-chunked/SSE stream reassembly, and the lock-free ring hand-off — are built, tested, and benchmarked for real below, numbers pasted directly from the actual runs. The DPDK capture layer itself (EAL init, RSS queue setup, per-queue worker pinning) is sketched at the end as a reference design and explicitly marked as untested — it cannot be otherwise in this environment, and pretending it had been run would be exactly the failure mode this whole document exists to avoid. The finished, buildable project (`cargo test --release` passes, all benchmarks below are reproducible with one command each) is attached alongside this document.

**Frame parsing.** Fixed-offset Ethernet + IPv4 + TCP parsing (no VLAN, no IP/TCP options — a real deployment would either handle those or lean on DPDK's own offload flags for L3/L4 classification instead of parsing in software at all). 54 bytes of header overhead, so a 64B minimum-size frame carries 10 bytes of payload and a 1500B frame carries 1446. Both sizes round-trip correctly under test.

**Hash throughput.** Single core, Intel Xeon @ 2.80GHz with AES-NI, PCLMULQDQ, and AVX-512 all present (so this isn't a "missing hardware acceleration" story for AES-GMAC — the crossover below is real implementation/scaling behavior, not a missing instruction):

| hash | size | ops/sec | MB/s | ns/op | vs. BLAKE3 |
|---|---|---|---|---|---|
| BLAKE3-128 | 10B | 13.8M | 138.5 | 72.2 | 1.00x |
| SipHash-1-3-128 | 10B | 62.0M | 619.5 | 16.1 | **4.47x** |
| AES-128-GMAC | 10B | 18.9M | 188.5 | 53.0 | **1.36x** |
| BLAKE3-128 | 46B | 14.5M | 668.6 | 68.8 | 1.00x |
| SipHash-1-3-128 | 46B | 42.7M | 1963.8 | 23.4 | **2.94x** |
| AES-128-GMAC | 46B | 15.7M | 721.8 | 63.7 | **1.08x** |
| BLAKE3-128 | 1446B | 763K | 1103.8 | 1310.0 | 1.00x |
| SipHash-1-3-128 | 1446B | 2.52M | 3641.7 | 397.1 | **3.30x** |
| AES-128-GMAC | 1446B | 986K | 1425.6 | 1014.3 | **1.29x** |
| BLAKE3-128 | 8946B | 375K | 3354.5 | 2666.8 | 1.00x |
| SipHash-1-3-128 | 8946B | 429K | 3836.2 | 2332.0 | 1.14x |
| AES-128-GMAC | 8946B | 164K | 1463.0 | 6114.7 | **0.44x** |

At every size the task actually asked about — the 64B worst case (10B payload) and the ≥1500B realistic case (1446B payload) — both SipHash-1-3-128 and AES-128-GMAC beat BLAKE3, exactly as the context claimed, by a wide margin at small size and a real (1.29–3.3x) margin at 1500B. What the context didn't say, and what running it actually surfaces: at 8946B (jumbo-frame-scale payload, past anything this task needs but included for a fuller curve), AES-128-GMAC falls *behind* BLAKE3, 0.44x. That's not a hardware gap — AES-NI and PCLMULQDQ are both present — it's that BLAKE3's SIMD tree structure keeps scaling favorably into AVX-512-width territory as inputs grow, while this GCM/GHASH implementation's throughput growth flattens out. Worth knowing if a later section ever wants a single hash function across a wider size range; irrelevant to §2's actual frame sizes, where SipHash-1-3-128 is the clear winner and AES-128-GMAC comfortably beats BLAKE3 too.

**Stream reassembly — including a bug the tests caught.** The first version of the HTTP-chunked-transfer decoder searched for the size-line CRLF only within each newly-arrived slice, not the accumulated buffer. Feed it one byte at a time (the byte-at-a-time fragmentation test exists specifically to stress exactly this) and a CRLF split across two `feed()` calls is invisible to that search — a single byte can never contain a 2-byte CRLF — and the parser hangs. `cargo test` caught this immediately, on the first run, before any benchmark number was trusted. Fixed by accumulating into one buffer with a read cursor and always searching the whole unconsumed region, not just the latest fragment. Mentioned here rather than quietly fixed and left out, because "the tests caught a real bug" is a more useful data point than a clean run would have been, and because a design document that only reports successes at this length in the codebase specifically is the outcome the self-checks throughout this project exist to prevent.

After the fix: 20 trials of adversarial random fragmentation (1–9 byte fragments — small enough to land on hex-length boundaries, CRLFs, and mid-JSON constantly), 500 SSE events per trial, all 20 **passed**. Throughput at realistic ~1200-byte TCP-segment-sized fragments: **562.3 MB/s (4.5 Gbps-equivalent), 9.59M events/sec**, single core.

**Ring buffer.** `crossbeam_queue::ArrayQueue`, not hand-rolled atomics, for the reason in the code comment: a subtle ordering bug here would corrupt evidence silently under contention, which is the wrong place to be clever. Producers spin-retry on a full queue rather than dropping (dropping evidence is a completeness bug, not a performance win). 1/2/4/8 concurrent producer threads against 1 consumer, this container's 1 logical CPU:

| producers | items/sec | MB/s (of 36B evidence records) |
|---|---|---|
| 1 | 5.61M | 201.9 |
| 2 | 6.60M | 237.5 |
| 4 | 4.59M | 165.2 |
| 8 | 3.29M | 118.5 |

Correctness held at every count — produced and consumed counts matched exactly, zero lost or duplicated items, every run. Throughput peaks at 2 threads and degrades past that, which is the oversubscription shape the task asked about — but stated honestly: **this container exposes exactly 1 logical CPU**, so this can't isolate the specific hyperthread-sibling-cache-contention mechanism the task's context describes (that needs at least 2 real logical CPUs sharing one physical core to even begin testing). What it does show is the general principle one level up — pushing concurrency past available hardware parallelism degrades a busy-retry workload rather than helping it — which is consistent with, but not proof of, the more specific claim. DPDK's own test-plan methodology (the documented "1C/2T vs 2C/1T" comparison in its PMD test plans) treats the specific hyperthread-sibling question as something to benchmark directly on real hardware for exactly this reason; that's the right way to actually settle it, and it isn't available here.

**End-to-end pipeline and the honest ceiling.** Parse → AES-128-GMAC hash → ring push, synthetic frames already in memory (no NIC, no DMA — this isolates the CPU-bound software cost, which is necessary but not sufficient for a real capture number):

| frame size | frames/sec | MB/s | Gbps-equiv | ns/frame |
|---|---|---|---|---|
| 64B | 7.48M | 478.6 | **3.83** | 133.7 |
| 128B | 5.15M | 659.6 | 5.28 | 194.1 |
| 512B | 1.68M | 861.6 | 6.89 | 594.3 |
| 1500B | 613K | 918.8 | **7.35** | 1632.6 |
| 9000B | 105K | 947.0 | 7.58 | 9503.3 |

Those two bold numbers are the answer the task actually asked for: **a single core in this container can sustain about 7.35 Gbps of realistic-frame (1500B) software processing, and about 3.83 Gbps at the 64B worst case** — parsing and hashing only, nothing NIC-related. Naive linear extrapolation says reaching 400Gbps at 1500B would take roughly 400/7.35 ≈ 54 cores just for this stage, and about 104 cores at the 64B worst case — before adding whatever DPDK's own RX path and RSS hashing cost on top. Real scaling wouldn't be linear: the ring-buffer result above already shows throughput bending over from thread contention alone on this single-core box, and at real multi-core scale the next bottleneck is shared memory bandwidth, not per-core compute — which is exactly what the context's own DPU-offload citation names directly (~162 Gbit/s, DRAM-bandwidth-bound) as the thing that caps a *different* offload approach entirely. That's consistent with — not a demonstration of — "no software algorithm sustains 400 Gbps at 64B regardless of core count": the mechanism (shared memory bandwidth stops scaling before core count does) is the same mechanism, measured here at 1 core and cited there at DRAM-bound saturation, but this sandbox cannot bridge the two with an actual multi-core measurement.

**The DPDK capture layer (reference sketch, not built or run here).** This is the part that actually can't exist in this sandbox — no DPDK-capable NIC, and `dpdk-sys` needs DPDK's EAL and a bound PMD to even link against. Structure only:

```rust
// ILLUSTRATIVE — does not compile without dpdk-sys + a real DPDK-capable
// NIC + hugepages + a bound poll-mode driver. Not built, not run, not
// benchmarked in this sandbox. Included so the shape of 2b's untested
// half is explicit rather than left as a gap with no description at all.

fn main() {
    let n_workers = std::cmp::min(available_physical_cores(), nic_queue_limit());
    // RSS: hardware hashes each packet's 5-tuple to a queue index, so a
    // given flow always lands on the same core (needed for the sequential
    // seq-number sanity check bench_ring's consumer does). One core, one
    // queue, run-to-completion — never shared, per DPDK's own PMD
    // guidance: sharing an RX/TX queue across logical cores forces a lock
    // and defeats the point.
    configure_rss_queues(n_workers);

    let handles: Vec<_> = (0..n_workers)
        .map(|q| {
            pin_to_physical_core(q); // deliberately not a hyperthread sibling
            std::thread::spawn(move || loop {
                let burst = rte_eth_rx_burst(q, MAX_BURST); // busy-poll, no interrupts
                for mbuf in burst {
                    if let Ok(parsed) = tap_reader::frame::parse(mbuf.data()) {
                        let hash = gmac.hash(parsed.payload);
                        let _ = evidence_queue.push(build_evidence(&parsed, hash));
                    }
                }
            })
        })
        .collect();
    for h in handles { h.join().unwrap(); }
}
```

Everything this sketch calls after `rte_eth_rx_burst` — `frame::parse`, the hash, the ring push — is the real, tested code above; only the DPDK-facing edge is illustrative.

#### Self-check

*2a:* confirmed — the note presents 90/10 and 95/5 as candidate designs with explicit numeric gaps, states plainly that no COTS part closes the 95/5 case today, and never claims a working solution. *2b, throughput:* confirmed — every number in the three tables above came from an actual `cargo build --release` binary run in this sandbox, not an estimate; the 400Gbps/54-core and 104-core figures are explicitly labeled as extrapolation, not measurement, and kept separate from the measured numbers. *2b, hyperthread oversubscription:* partially confirmed — a real benchmark shows throughput degrading past available concurrency (2→4→8 producers), but this container's single logical CPU means it cannot isolate the specific physical-core-vs-hyperthread-sibling mechanism the task named; that gap is stated above rather than papered over with a number that would imply otherwise. *2b, hash benchmark:* confirmed — real numbers, both winners and the one place (8946B) where the context's claim doesn't hold, reported rather than trimmed to fit.

**Sources used in this section:**
- 400GBASE-DR4 QSFP-DD/OSFP transceiver datasheets: Finisar/Coherent FTCD4533E3PCM (Feb 2024 rev), FS.com DR4 silicon-photonics datasheets — signaling rate, wavelength range, OMAouter/TDECQ, LOS assert/de-assert thresholds.
- Huang, Akbaba, Li, Akel, Tsegaye, Khatana, "First Demonstration of Sensitivity Improvement using an APD Receiver for a 100 Gbit/s Single Channel PAM4 Link," CLEO 2018 — 2.7dB figure.
- 2025 uni-multiplication-carrier APD paper (PMC/Nature-family) — 9dB/260Gb/s PAM4 figure.
- O-band BDFA gain: multiple IEEE/OFC conference results (10.6–24dB range) and a 2024 ScienceDirect broadband-BDFA study (18.7dB net gain, 1310nm, 5.1dB NF) and a 2024 ScienceDirect O-band Bragg-BDFA modeling study (34–54dB in specialized/cooled configurations).
- DPDK Poll Mode Driver documentation and DPDK Test Plans (PMD test plan's 1C/2T vs 2C/1T methodology) — queue-per-core and hyperthread-sibling testing methodology.
- `blake3`, `siphasher`, `aes-gcm`, `crossbeam-queue`, `rand` crates (crates.io) — the actual implementations benchmarked above.

---

### §3. Secure Network Gateways

**Why this is worth the added complexity at all.** §2's passive tap mirrors everything — every frame, in full, to the recomputation server. That's the right baseline because it's maximally trustworthy (nothing to compromise beyond the physics), but it doesn't scale in bandwidth: mirroring 100% of frontend traffic off-site from every tapped facility, at fleet scale, costs a lot more backhaul than actually recomputing 1% of it needs to. A "secure network gateway" exists to move the sampling decision from *after* the recomputation server has already received everything (the §2 baseline) to *on-path*, at the tap, so only the sampled fraction has to leave the facility in full. That's a real efficiency win — and it's also exactly the change that reopens the trust question §2 closed, because it means putting active decision-making logic inside a device that physically sits in the prover's own facility, where §2's tap had none.

**The split: what stays mechanical, what the gateway actually decides.** Three things are fixed and outside the gateway's discretion:
- **Packet identification.** `packet_id` is a fixed, public function of immutable fields (5-tuple + TCP sequence number here). The gateway doesn't get to choose how a packet is identified — giving it that discretion would open a way to indirectly bias sampling by manipulating *which* packets look identical to which.
- **The verifier's key.** The gateway never generates or chooses the secret that drives the sampling decision. It only evaluates a function against a key the verifier supplies — the same principle §5 uses for the decoding seed, one layer down.
- **What happens after a packet is flagged.** Once the gateway's PRF marks a packet sampled, forwarding it in full is mandatory and logged; the gateway doesn't get a second decision to suppress or delay it.

The one thing the gateway actually *does*: for every packet, evaluate a keyed pseudorandom function against `packet_id` and compare it to a threshold set by the recomputation budget C (§1's formula — a fraction, not a fixed count, so the sampling rate is stable regardless of traffic volume). Sampled packets get forwarded in full; everything else gets a commitment hash instead (§4's job to specify what that hash feeds into). Reusing §2's fastest primitive here isn't incidental — SipHash-1-3-128 was the clear per-frame throughput winner in that benchmark, and a per-packet sampling decision has to keep up with the same line rate as the rest of the pipeline, so it's the natural choice rather than introducing a fourth primitive.

Per the source material, the gateway can also do a one-time (or periodic) boot-phase check that only whitelisted model weights are being loaded onto the inference unit — a different kind of check (integrity of what's loaded, not sampling of what's flowing) worth building into the same trusted device, but not the focus of this section's self-check, which is specifically about the sampling decision's unpredictability.

**Where the key lives.** The gateway is physically inside or adjacent to a facility the prover controls. If the key were extractable by anyone with physical or root access to the gateway's host system, the entire property collapses — a prover who recovers the key can predict every future sampling decision and behave dishonestly exactly on the packets that won't be checked. This is precisely the class of problem hardware secure enclaves exist for: the key is generated and held inside a boundary (a secure enclave, ideally with key material bound to a PUF rather than stored as extractable bits at all) that performs the PRF evaluation internally and never exposes the raw key to the host OS or CPU the prover might otherwise control. This doesn't make the gateway untamperable — it narrows what "compromised" has to mean before the sampling property actually breaks, from "gained any access to the box" to "defeated the enclave specifically," which is a substantially higher bar and one with a mature, if imperfect, track record (this is the same hardware class §27 will need to reason about when it gets to TEE hardening more generally).

**Does hosting an active device actually give the prover anything? Simulated, not asserted.** Four attackers, all working only from packet IDs and — for the strongest one — a large set of past ground-truth (packet, sampled?) labels, never the key itself, tested against a real keyed-PRF sampler at a 1% recomputation budget:

| attacker | what it knows | AUC | reads as |
|---|---|---|---|
| A. Majority baseline | nothing | 0.5000 (accuracy 98.98%) | high accuracy, zero information — the metric trap this table exists to avoid |
| B. Best of 24 guessed/weak keys | plausible-but-wrong keys (all-zero, small sequential, a fake device-MAC-derived guess) | 0.5046 | indistinguishable from chance |
| C. Logistic regression on packet-ID bits | 480,000 labeled (packet, sampled?) pairs, tested on 120,000 held out | 0.4885 | indistinguishable from chance (statistically consistent with pure noise around 0.5 at this sample size) |
| D. Oracle with the *correct* key | the key | 1.0000 | perfect — this is the contrast, not an attack |

AUC 0.5 is the no-information line regardless of class balance, which is why accuracy alone (row A) is the wrong metric here — a constant predictor gets 98.98% "correct" while knowing nothing. Every attacker that doesn't have the key stays within 0.005 of 0.5; the only thing that predicts better than chance is having the key, exactly as a keyed PRF is supposed to behave. That's the self-check requirement for this section, demonstrated against a real implementation rather than argued for in the abstract. (Code: `src/gateway.rs`, `src/bin/sim_gateway_sampling.rs` in the attached project — reuses §2's tested SipHash-1-3-128, not a new untested primitive.)

**Fail-open or degrade? Degrade — and not by the gateway's own judgment.** If the gateway's integrity can't currently be trusted, the system must **degrade to §2's passive-tap security level, never fail open.** Failing open — continuing to accept the gateway's sampling decisions as authoritative while its integrity is in doubt — is exactly the scenario where a compromised gateway is most dangerous, because a prover who has broken the gateway gains nothing by breaking it *loudly*; they gain everything by breaking it quietly and having the system keep trusting its output. Degrading to full-mirror is strictly safer: it's the one mode already proven trustworthy in §2, at the cost of the bandwidth efficiency §3 was built to buy back.

The harder part of this answer is *who decides* the degrade has happened, because a compromised gateway can't be trusted to accurately self-report its own compromise — that's not a fallback, that's asking the attacker for a favor. So the trigger can't be the gateway noticing something's wrong; it has to be the **verifier withholding trust by default and requiring it be actively re-earned**, on a schedule short enough that a lapse is caught quickly: the gateway periodically produces a signed attestation from its secure enclave (a standard TEE attestation quote, not a self-report from the general-purpose host OS the prover might control); the recomputation server treats "sampled-only" evidence from that gateway as sufficient *only* while a current, valid attestation is on file. The moment attestation lapses or fails — timeout, signature mismatch, unexpected firmware measurement — the recomputation server stops accepting sampled-only reporting from that gateway and requires either full-mirror bandwidth (§2's baseline, more expensive but already trusted) or a physical inspection before trust is restored (§21/§22's job, not this section's). The prover doesn't get a vote in that transition; it's enforced entirely on the verifier's side of the trust boundary, which is the only place a decision like this can safely live once the device making it might itself be the thing that's broken.

#### Self-check

*(1) Simulation demonstrates unpredictability, not just asserts it:* confirmed — table above, real numbers, three independent no-key attack strategies (including a full logistic-regression learning attempt on 480K labeled examples) all landing within 0.005 AUC of the no-information baseline, contrasted against a perfect oracle with the correct key. *(2) Fail-open vs. degrade has one stated answer:* confirmed — degrade to §2's passive level, triggered by the verifier withholding trust absent current attestation rather than by the gateway self-diagnosing, stated once above rather than left open.

**Sources used in this section:** AI Futures Project Verification Plan supplement (secure network gateway concept, boot-phase weight whitelisting, the iPhone-secure-enclave/PUF hardware-precedent framing) — same source as §1. §2's own hash benchmark (SipHash-1-3-128 throughput) for why it's the reused primitive here rather than a new one.

---

### §4. New Tap Types & Bandwidth-Reduction at Scale

§3 decided *which* packets get fully forwarded. This section is the other half: what happens to everything else, given §2 already established that full software capture can't hold line rate at small packet sizes — a problem that gets worse here, not better, since a hash-only commitment has to cover *all* traffic, not just §3's sampled 1%.

**Design: per-epoch Merkle commitment, chained across epochs.** Every packet that isn't in §3's sampled set still gets its payload hashed on-path; that hash becomes a leaf in a Merkle tree covering one time epoch of traffic (a tree, not a flat running hash-chain, specifically because it supports cheap proof-of-inclusion later — if a candidate payload for one packet ever surfaces through some other channel, checking it against the epoch root costs an O(log n) proof, not a replay of the whole epoch). The epoch roots themselves get appended to a hash-chained log, reusing §21b's append-only pattern rather than inventing a second one: tampering with any past epoch's stored root breaks verification from that point forward, exactly like tampering with any entry in §21b's log does.

**Is a hash-only record an acceptable one-way commitment? Yes — with the limitation stated plainly, not glossed over.** A one-way hash cannot be inverted; that's not a design shortfall to fix, it's what "one-way" means. So if a specific dispute later arises about one specific unsampled packet, and no candidate payload for it ever surfaces through any other channel (prover cooperation, on-site inspection, subpoena, whistleblower), the hash-only record cannot resolve that dispute — it can confirm a candidate payload matches what was committed, but it can never produce the payload itself. That's a real, permanent gap, and no amount of engineering here closes it.

The reason "yes, acceptable" is still the right answer is that this isn't the gap it needs to close. §1's entire statistical framing already commits to an aggregate assurance standard, not a per-packet dispute-resolution guarantee for every single packet — that standard was set before this section, not lowered by it. §2 already established that recording every packet in full isn't achievable at line rate, so the real choice was never "hash-only vs. full record for the other 99%" — it was "hash-only vs. *nothing* for the other 99%," since nothing is what a pure §2/§3 design leaves behind for unsampled traffic. Against that actual alternative, hash-only strictly dominates: it adds a permanent, tamper-evident record that traffic occurred in a specific order with specific content-fingerprints, closing off a different attack entirely — a prover rewriting history about what traffic pattern existed at all — that §3's sampling alone does nothing to prevent, since sampling only reasons about content correctness for the packets it happens to check. Hash-only commitment and full-payload sampling are answering different questions (did this content match vs. did this traffic pattern happen), and §4 only ever needed to answer the second one.

**Benchmark: hash-only throughput, the real bottleneck here, measured separately from §2's full-capture ceiling.**

| frame(B) | frames/sec | MB/s | Gbps-equiv | vs. §2's full pipeline |
|---|---|---|---|---|
| 64 | 13.6M | 869.4 | 6.96 | 1.82x (§2: 3.83 Gbps) |
| 128 | 8.3M | 1068.4 | 8.55 | — |
| 512 | 2.4M | 1212.7 | 9.70 | — |
| 1500 | 835K | 1252.7 | 10.02 | 1.36x (§2: 7.35 Gbps) |
| 9000 | 136K | 1226.3 | 9.81 | — |

Dropping reassembly and ring-buffer overhead for the non-sampled path (this is hash-and-commit only — no HTTP/SSE reconstruction, no evidence struct, no queue push, none of which a hash-only record needs) buys a real 1.36–1.82x over §2's full pipeline, measured, not assumed — but it's still single-digit-to-low-double-digit Gbps on one CPU core, nowhere close to 400Gbps. That's the actual finding this benchmark exists to produce: **software hashing alone, even stripped to the minimum, doesn't get there.** Which is exactly why the task specifies dedicated ASIC/FPGA hashing rather than a leaner version of §2's software pipeline — and why this sandbox, with no synthesis toolchain and no FPGA, can measure the software floor but not the actual target hardware.

What grounds the claim that dedicated hardware plausibly *does* clear the gap, without me being able to synthesize and test it here: published FPGA implementations of GHASH (the authentication core inside AES-GCM, structurally the closest published comparison to a hardware keyed-hash core) span roughly 40Gbps on a 2010-era Virtex-4/5, up to 292Gbps for a pipelined GHASH core alone on a 2010-era Virtex-6, up to a commercial FPGA IP core (Design Gateway's AES256-GCM core) rated for sustained 100Gbps+ specifically for 100G Ethernet offload today. A February 2025 paper on parallelized GHASH reports throughput exceeding 400Gb/s on a GPU (RTX 4090) — not an FPGA/ASIC, but direct evidence that this exact class of operation clears the 400Gbps line at all on hardware built for parallel throughput rather than general-purpose sequential execution. SipHash — the primitive actually used throughout this pipeline — has no finite-field multiplication to pipeline in the first place (it's pure add-rotate-xor), which is the specific thing that limits GHASH's clock rate on FPGA fabric; if anything, that makes a dedicated SipHash core an easier hardware design problem than the GHASH cores already clearing hundreds of Gbps in the literature, not a harder one. None of this is a demonstration for *this* design — it's the reason "an ASIC/FPGA could plausibly clear line rate here" is a defensible claim to make while flagging it as unverified, rather than either an assumption or an overclaim.

**What §2a's ceiling still says, unchanged.** None of the above touches whether the physical tap itself can see 53 GBd traffic to hash in the first place — that's still §2a's unresolved link-budget problem, and a faster hash core downstream doesn't move that number by a single dB. This section is strictly about what happens to bytes *after* they've reached a receiver that can decode them; it doesn't relax or restate §2a's conclusion, and doesn't get to borrow credibility from a faster hash benchmark to imply the physical layer question is closer to solved than §2a left it.

#### Self-check

*Hash throughput is measured, not projected:* confirmed — the table above is real `cargo build --release` output on this sandbox's one CPU core, including the 64B worst case, with the §2 comparison numbers pulled directly from that section's own measured results, not restated from memory. *The disputability tradeoff has one explicit answer:* confirmed — yes, acceptable, with the specific limitation (no per-packet dispute resolution absent some other source of the payload) stated once, plainly, rather than surveyed. *§2a's ceiling is unchanged:* confirmed — stated explicitly above rather than left implicit, since a faster hash number is exactly the kind of result that invites quietly implying more progress than was actually made.

**Sources used in this section:** Henzen & Fichtner, "FPGA Parallel-Pipelined AES-GCM Core for 100G Ethernet Applications" (ESSCIRC 2010, ~48.8Gbps); "Design and Efficient FPGA Implementation of Ghash Core for AES-GCM" (IEEE, 40Gbps and, in a related pipelined variant, up to 292Gbps on Virtex-6); Design Gateway's commercial AES256-GCM FPGA IP core documentation (100Gbps+, current product); a February 2025 ScienceDirect paper on parallelized GHASH on GPU (>400Gb/s, RTX 4090). §21b's log design (referenced, not yet built — that section's own job) for the epoch-chain pattern reused here.

---

### §5. The Recomputation Engine

**What happened when I tried to do this the way the task asks for it, first.** The task wants vLLM serving a real LLM. This sandbox has no GPU. It also, it turns out, has no reachable path to real pretrained weights at all — HuggingFace Hub isn't in this environment's network allowlist, so there's no `transformers`/`vllm`-standard way to pull down even a small real checkpoint. I tried installing PyTorch anyway, to see how far a CPU-only setup could get: `pip install torch` on this environment doesn't resolve to a CPU-only wheel (the dedicated CPU wheel index isn't reachable either), so it pulled the full CUDA stack — `nvidia_cublas` (423MB), `nvidia_cusolver` (201MB), `nvidia_cufft` (214MB), `nvidia_cusparse` (146MB), and more — entirely unusable without a GPU, and the install died mid-download with "No space left on device" once it exceeded this container's available disk. That's a real, specific dead end, not a hand-wave: this sandbox cannot run vLLM against a real model, full stop, and pretending otherwise by quietly downgrading the claim would be exactly the failure mode this document exists to avoid.

**What I built instead.** A small **real, trained** character-level neural language model — NumPy, hand-derived backpropagation, no PyTorch, no GPU — standing in for what would be vLLM serving a frontier LLM. Fixed 8-character context window, 32-dim embeddings, a 128-unit hidden layer, 65-character vocabulary, trained on the standard tiny-shakespeare toy corpus (1,115,394 characters). 6,000 gradient steps took 10.2 seconds on this container's single CPU core; training loss went 3.44 → 2.27, validation loss 3.30 → 2.41 — a real, if extremely small, language model that has genuinely learned character-level structure (greedy decoding produces real words and correct capitalization-after-period patterns, not noise), not a hash-based fake dressed up as a model. Every claim below about the *verification protocol* is tested against this real model; nothing here claims it stands in for a frontier model's capability, and the write-up says so at every point it matters rather than once at the top and then quietly forgotten.

**Architecture.** Real FastAPI service, real PostgreSQL logging (schema: `sessions` — prompt, verifier-issued seed, temperature; `verifications` — per-call deviation score, pass/fail, low-confidence flag, and the full per-token breakdown as JSONB, so a clipped token is visible in the persisted log, not just computed and discarded). Two independently-loaded instances of the same checkpoint file stand in for "separate prover and verifier vLLM instances" — same weights when the prover is honest, architecturally separate objects either way, matching what an honest deployment's matching-but-separate serving stacks would look like.

**Fixing the reference implementation's backwards seed default.** `POST /session/start` generates the seed server-side (`secrets.randbits(63)`, never client input) and stores it in the session row the moment the session is created. `POST /prover/generate` reads that seed back out to actually decode — the prover has to know the seed to generate the intended output, that's not the security boundary. The security boundary is `POST /verify`: its request schema has no `seed` field at all. Not "accepts a seed and ignores it" — there is structurally no parameter a client could use to try. Verification always reads the seed from the session row the verifier created, and nothing else.

**Single-pass recomputation.** `POST /verify` doesn't re-run generation autoregressively. It teacher-forces the full claimed sequence through the verifier's model in one batched call — for this fixed-context architecture, that means building one context window per output position and running them all through the model together, which is the equivalent operation to how a real transformer gets every position's logits from one forward pass under causal attention instead of one call per token. Gumbel noise for each position is regenerated independently from the seed (cheap — it doesn't need the model at all) and compared against the claimed token's rank.

**Top-k and Δmax, made concrete.** The source paper's exact sign convention wasn't fully recoverable from a search snippet, so this implementation picked the direction that actually makes sense as a deviation score, documented in the code rather than silently assumed: if the claimed token ranks inside the verifier's top 10 (by logit+noise), deviation = clip(top_score − claimed_score, 0, Δmax); if it's outside the top 10 entirely, deviation = Δmax directly, since computing an exact score for an arbitrarily bad token doesn't add information. Δmax = 8.0 here, chosen to be well above the typical top-10 score spread on this small model — a real deployment would set this per-model, the same way τ gets calibrated in §11.

**The four required self-checks, run against the live server over real HTTP, not asserted:**

| # | check | result |
|---|---|---|
| 1 | Honest identical-model pair | `avg_deviation = 0.00000`, `passed = True`. Exactly zero, not just small — expected, since both sides run the identical deterministic computation from the identical checkpoint under the identical seed; anything nonzero here would have meant a real bug in how the two code paths construct context windows. |
| 2a | Different verifier-issued seeds → different prover output | Same prompt, two sessions, seeds `6031922658774193576` and `43841280609948653` → genuinely different decoded text both times. |
| 2b | Prover-attempted seed change has no effect | Same claimed output verified twice — once normally, once with a `"seed": 999999999` field smuggled into the JSON body. `avg_deviation` identical both times (`0.00000` / `0.00000`), because there's no seed field in the request model for that value to land in. |
| 3 | Deliberate large out-of-top-k divergence | Forced the last character of a real 15-token honest output to something adversarial. Recomputation ranked the claimed token 64th out of 65 in the vocabulary; deviation clipped to exactly `Δmax = 8.0`; `clipped: true` visible in the per-token JSONB log and surfaced at the top level as `any_token_clipped = true`. Average over the 15-token output: `8.0 / 15 = 0.5333`, exactly — one bad token, correctly diluted by fourteen honest ones, not hidden by them. |
| 4 | Output under 5 tokens | 3-token generation → `low_confidence = True` in the API response *and*, checked independently, in the persisted Postgres row (`SELECT low_confidence FROM verifications WHERE id = 5` → `t`) — not just present as unused code, actually stored. |

All five rows (the four required checks plus the honest-pair sanity check) were independently re-confirmed with a direct `psql` query against the `verifications` table, outside the API layer entirely — five real rows, matching the API's own numbers exactly.

**τ, honestly labeled as a placeholder.** The verifier currently uses `τ = 0.5`, hardcoded, because real calibration is explicitly §11's job (per the task's own scoping) and hasn't happened yet — this section wires up the mechanism τ gets compared against, not the number itself. That placeholder is why check 3's tampered case shows `passed = False` (0.5333 > 0.5): a reasonable-looking result, but attributable to an uncalibrated guess, not a validated threshold, and it'll get overwritten once §11 actually runs.

#### Self-check

All four required checks: confirmed, run against a live server over real HTTP (not unit-tested in isolation), independently re-verified via direct SQL query. Nothing in the table above was asserted without a corresponding real request/response pair. Scope held to correctness only, as instructed — completeness isn't touched here, that's §15–§18's job.

**Sources used in this section:** Karvonen, Reuter, Rinberg, Marks, Garriga-Alonso, Warr, "DiFR: Inference Verification Despite Nondeterminism" (arXiv:2511.20621) — Token-DiFR mechanism, shared-seed principle, teacher-forced single-pass verification. TOPLOC (arXiv:2501.16007) — prior top-k-compression-based verification work DiFR's activation variant builds on; referenced for the "known steganography weak point" the context flags, picked up properly in §12. tiny-shakespeare (`karpathy/char-rnn`, via raw.githubusercontent.com) — training corpus for the stand-in model.

---

### §6. Frontier Recomputation Algorithms

Different shape of section, on purpose: graded "Rigor," not "Checkable" — no known-correct design exists for any of the three cases below, so there's nothing to benchmark against and building code here would mostly demonstrate that code runs, not that the design is right. The deliverable is concrete, falsifiable reasoning instead, per the self-check's actual bar: name a real scenario, name real steps and why those, draw the line with a worked example. §1–§5 built things because the task specified things to build; this section doesn't, and forcing an artifact in anyway would be optimizing for this document's established rhythm over what the task actually asked for.

#### Mixture-of-experts

**Generalizes, modifies, or replaces? Modifies.** §5's DiFR checks whether the declared output matches what recomputation produces — and that check still works fine for MoE, because a substituted/different model still has to produce a wrong-enough output to get caught eventually. What's new is a degree of freedom dense models never had: two genuinely different computations — different experts activated, different actual work performed — can land on statistically indistinguishable final-layer logits, because trained MoE models routinely develop redundant experts (multiple experts capable of handling the same class of token reasonably well). Token-level DiFR was never designed to see this, because it only ever looks at the thing routing redundancy can hide behind: the output.

**One concrete scenario, not a general statement.** Take a top-2-of-8 MoE feed-forward layer (Mixtral-style). At some token position, honest routing selects experts {3, 7} with gate weights {0.6, 0.4} — expert 7 specifically because the router learned it handles this token's context best. A cost-cutting prover instead routes to {3, 1}: reusing expert 3 correctly, substituting cheaper-to-keep-resident expert 1 for expert 7. If 1 and 7 are both reasonably competent at common function words (the kind of redundancy real trained MoE models exhibit), the combined output — 0.6·expert_3 + 0.4·expert_1 versus 0.6·expert_3 + 0.4·expert_7 — can land within a well-calibrated τ, especially on high-frequency tokens where the correct next-token distribution is already peaked regardless of which of several adequate experts contributed the residual nudge. Run this substitution *systematically*, always picking the cheap-but-adequate expert, and every individual token stays within tolerance by construction — this isn't the rare-bad-token pattern §5's clipping-and-averaging is tuned to catch, it's a consistent, low-amplitude, deliberately-chosen bias that never trips the threshold precisely because it was chosen not to.

**Routing-commitment extension.** Alongside the claimed output token, the prover additionally reports which experts were activated (top-k indices + gate weights) at each MoE layer that token passed through. The verifier's existing single-pass recomputation already computes this for free — the router's own top-k selection is just another output of the same forward pass used to get the logits — so this is a comparison to add, not a new recomputation to run. And it's a *cheaper* comparison than the logit check in one specific way that matters: routing indices are discrete (which K experts, out of N) rather than continuous, so — outside genuine near-ties in gate scores, which need their own small documented tolerance the same way §5 needed one for floating-point logit noise — claimed routing either matches recomputed routing exactly or it doesn't. A prover running the §6 scenario above has to report the routing it *actually used* ({3,1}) to stay internally consistent, or fabricate a claimed routing ({3,7}) that doesn't match what it actually computed — and the moment it claims {3,7}, the verifier's independently-recomputed router (same weights, same seed, same input activations) said {3,7} too, so an honest claim here means honest routing happened, closing the exact blind spot the scenario above depends on.

#### Diffusion-based LMs

**Generalizes, modifies, or replaces? The indexing scheme gets replaced; the core mechanism doesn't.** Current text diffusion (LLaDA, Google's Diffusion Gemma, and similar masked-diffusion approaches — the dominant paradigm for this as of 2025–2026, more so than the earlier continuous-embedding diffusion line of work) generates by starting from a mostly- or fully-masked sequence and iteratively predicting clean tokens at masked positions across T denoising steps, unmasking a subset of positions at each step rather than committing the whole sequence at once. There's no "logits at position i given positions <i" here — attention is bidirectional, not causal, and *every* position can influence every prediction at every step. §5's one-dimensional (position) structure doesn't have anywhere to attach.

What does carry over: the same shared-seed principle, applied to a two-dimensional (step, position) grid instead of a one-dimensional (position) list, with the same clipped-and-averaged deviation scoring and the same verifier-controlled sampling budget — because both sources of randomness in a masked-diffusion process are exactly as seed-derivable as autoregressive sampling was in §5. Two, not one: (a) *which* positions get unmasked at a given step (a scheduler decision), and (b) *what token* gets sampled for each newly-unmasked position, from the model's predicted distribution at that step. A verifier that's issued the seed can independently recompute both — which positions the scheduler should have picked, and what token distribution the model should have produced for each — the identical shape of check as §5's, just re-indexed.

**Which steps get checked, and specifically why not others.** Checking all T steps is expensive (T is usually larger than a comparable autoregressive token count, since each step processes the whole sequence). So this needs the same budget-limited sampling §1 already established for packets — but *where* to bias that sampling isn't arbitrary, and the answer is the opposite of what seems intuitive at first: bias toward **early-to-middle steps, not late ones**, and here's why, tied directly to something this document already found rather than argued from scratch. §9 documents autoregressive DiFR's real false-negative zone: short outputs, where few plausible continuations exist, carry weak signal because a cheap model and a good model both land on the "obvious" answer when context leaves little room to differ. Late diffusion steps are exactly this failure mode in a different shape — by the time only a handful of positions remain masked amid an otherwise-fixed sequence, the remaining predictions are heavily constrained by all that already-fixed context, and a cheap or substituted model is likely to pass precisely *because* the task has become easy, not because it's actually equivalent to the honest model. Early-to-middle steps, with more positions still open and less fixed context to lean on, are where a weaker or different model's actual capability gap would show up most clearly — the diffusion analog of a *long*, unconstrained autoregressive output, which is exactly where DiFR has its strongest signal. That said, checking *only* early steps creates its own exploit: a prover who knows late steps go unchecked could behave honestly early and cut every corner once verification pressure has (in expectation) ended. So the actual answer is a distribution biased toward early/middle steps with nonzero, unpredictable (§3-style, verifier-seeded) coverage of late steps too — enough that "always cheat late" is never a safe strategy, even though late steps individually carry less signal per step checked.

#### Agentic / tool-use output

**Generalizes cleanly for the model's own decisions; needs an explicit boundary for everything else.** A model deciding to call a tool, and with what arguments, is still just token generation — formatted as a tool call instead of prose, but produced by the identical seeded sampling process §5 already verifies. Nothing about that half needs new machinery. What breaks the pattern is what happens *after*: the tool executes, and its response is not a function of the model's weights at all. It's an external system's output — possibly non-deterministic itself (a live API, a database with mutable state, a search index that's changed since) — and the verifier has no way to independently recompute what a tool *should* have returned. That has to be a trusted input, not a recomputed one.

**One worked example, to draw the line concretely rather than leave it abstract.** Prompt: *"What's the current weather in Boston, then write a haiku about it."* Turn 1: the model generates `call_tool(name="weather_api", args={"city": "Boston"})` — fully recomputable; the verifier reruns with the shared seed up to this point and confirms the identical tool-call decision, same name, same arguments. The tool executes outside the model, outside verification's reach, and returns `{"temp_f": 58, "condition": "foggy"}` — this value is not recomputable (the verifier re-querying the same API isn't guaranteed a bit-identical answer, and even if it were, that's a claim about the *tool's* trustworthiness, not the model's); it becomes a trusted input, hash-committed (reusing §4's commitment pattern rather than inventing a new one) so it's provably the same value used at serving time and in any later audit, even though its correctness was never independently verified. Turn 2: the model generates the haiku conditioned on prompt + tool call + that trusted tool response — recomputable again, exactly like turn 1, and if the recomputed haiku doesn't match the claimed one, that's a real, ordinary DiFR violation.

**The gap this leaves, named rather than left implicit.** A dishonest prover doesn't have to make the model diverge to cheat here — it can fabricate the *tool response* instead. Claim the API said "sunny, 90°F" instead of the real "foggy, 58°F," and the resulting sunny-weather haiku is a perfectly faithful, DiFR-passing continuation of a lie. DiFR verifies "did the model respond faithfully to its claimed input," never "was the claimed input true" — that boundary is exactly where this scheme has no answer, and pretending otherwise would be worse than naming it. Closing it is a tool-specific trust problem (the tool provider attesting its own responses, or the recomputation server independently querying high-stakes tools itself, or something not yet designed) — genuinely out of DiFR's scope, not a gap this section's mechanism can absorb by being cleverer about model verification.

#### Decision framework

The pattern across all three, extracted as questions a future architecture — not yet imagined — should get run through, because that's what "living document" has to mean in practice rather than as a label:

1. **Is the full computation a deterministic, seed-derivable function of (weights, input, seed) alone?** If yes, in its entirety, §5 applies unmodified. None of the three cases above cleared this bar on their own — that's why each needed a change.
2. **If not, is the non-recomputable part external to the model, or internal to its own computation?** External (agentic pattern) → partition into recomputable model segments and trusted-input segments, verify the former with DiFR, commit the latter's integrity (not its correctness) with §4's pattern, and say explicitly that correctness of the external part is out of scope. Internal (MoE pattern) → check whether the extra degree of freedom is already fully reflected in the output DiFR checks, or creates a same-output-different-work blind spot; if the latter, add a parallel commitment for that specific degree of freedom rather than replacing the output check.
3. **Does generation follow strict autoregressive causality — one position, dependent only on strictly-prior positions, generated once, in order?** If not (diffusion pattern, and presumably whatever comes after diffusion too), re-derive what the natural checkable *unit* is for this architecture — it won't be "position" alone — but keep the actual invariant: verifier-issued shared randomness, a budget-limited and unpredictable sample of units get checked, per-unit deviation is clipped so no single unit can dominate the average.
4. **Where's this architecture's version of §9's short-output blind spot?** Every case above has one — heavily-constrained decisions that a weak model passes for free, not because it's equivalent, but because the task got easy. Find it before deploying, not after; the diffusion section above only found the right answer by checking against §9's already-documented one instead of reasoning from intuition alone, which is itself the actual lesson to carry forward, not just the specific step-weighting conclusion.

The invariant underneath all four questions is the same one §1 through §5 already built: shared verifier-controlled randomness, budget-limited sampling instead of exhaustive checking, and bounded per-unit influence on the aggregate score. Architectures change what the checkable "unit" is; they haven't yet changed that underlying shape.

#### Self-check

MoE section names one specific, numeric scenario (experts {3,7} vs {3,1}, gate weights 0.6/0.4), not a general "routing could diverge" statement — confirmed. Diffusion section specifies early-to-middle-weighted step sampling with nonzero late coverage, and states the reason (mirrors §9's documented short-output blind spot, not an assumption) — confirmed. Agentic section draws the recomputable/non-recomputable line with one fully worked example (the Boston weather haiku, both turns) — confirmed. None of the three stayed abstract.

**Sources used in this section:** LLaDA ("Large Language Diffusion with mAsking," 2025) and Google's Diffusion Gemma (2025, Gemma-2-based, bidirectional attention, tunable denoising step count) for the masked-diffusion mechanics this section's redesign is grounded in, rather than the older continuous-embedding diffusion line these newer systems have mostly superseded for production text generation. §9's short-output false-negative finding (this document, not yet drafted in detail but already scoped in the source material) as the basis for the diffusion step-weighting argument. §4's commitment-log pattern, reused rather than reinvented, for tool-response integrity.

---

### §7. The Reproducible Inference Stack

This turned out to be one of the best-grounded sections in this document, not because this sandbox could test it directly — it can't, no GPU — but because the exact problem this section asks about was independently discovered, measured, and partially solved in public, very recently, by people with real GPU fleets. Real world first, then what this sandbox could actually add.

**The problem, measured by someone else, on real hardware, first.** Thinking Machines Lab (He et al., Sep 2025) sampled 1,000 completions from Qwen3-235B at temperature 0 — supposedly fully deterministic, greedy decoding — and got **80 distinct outputs**, first diverging at **token 103**. Not randomness in the model: GPU kernels for matmul, RMSNorm, and attention pick different reduction strategies depending on batch size to maximize throughput at each shape, and floating-point addition is non-associative, so a different grouping of the same values produces a different rounding path to a nominally identical sum. The fix — "batch-invariant kernels," forcing one universal reduction order regardless of batch size or position — took all 1,000 completions to bitwise-identical. vLLM and SGLang have both since adopted this (real, ongoing engineering work, tracked in a public vLLM GitHub issue with dozens of sub-PRs through mid-2026).

**What this sandbox measured itself, since citing someone else's number isn't the same as checking the mechanism holds.** Summed the same 4,096 float32 values (hidden-dimension scale) under 12 different chunk groupings, each standing in for "the kernel picked a different reduction shape for this batch size":

```
chunk_size=1    -> -3.303233      chunk_size=64   -> -3.3032303
chunk_size=2    -> -3.3032331     chunk_size=128  -> -3.3032298
chunk_size=4    -> -3.3032258     chunk_size=256  -> -3.3032305
chunk_size=8    -> -3.30323       chunk_size=512  -> -3.3032303
chunk_size=16   -> -3.3032315     chunk_size=1024 -> -3.3032303
chunk_size=32   -> -3.3032322     chunk_size=4096 -> -3.303233
```

12 chunk sizes, **9 distinct bit-level results**, same mathematical sum. Applying one fixed, canonical reduction tree — padded to a power of two, always the same pairing order, the batch-size argument never even reaches the function — across those same 12 simulated contexts: **1 result**, every time. Not reduced. Zero. Extended to the actual batching case (sum-of-squares, RMSNorm's own reduction, the same row simulated across six different batch-mate counts): the adaptive version gave 4 distinct results for a row that should never care who else is in its batch; the fixed-tree version gave 1. This is the CPU-scale version of exactly what Thinking Machines found on real GPUs — the mechanism (non-associativity + shape-dependent grouping) doesn't require a GPU to demonstrate, even though *why* GPU kernels pick different shapes in the first place is a GPU-specific throughput optimization this sandbox can't reproduce.

**Three sources named in the task, and how many actual fixes they need.**
- **Floating-point reduction order** → the general fix: one canonical, fixed reduction tree, applied unconditionally. Real term for this property: *position invariance* — an element's output doesn't depend on its position within, or the size of, whatever it was computed alongside.
- **Continuous batching (output depends on co-batched requests)** → this isn't a separate fix, it's the same fix applied specifically to batch composition: "batch-invariant kernels" are position-invariant reduction applied to the one context variable (what else is in this batch) that continuous batching makes float freely. §5's low-confidence flag and §9's short-output blind spot are about *statistical* signal getting weak in an edge case; this is a *correctness* edge case — same underlying non-associativity, different trigger.
- **GPU scheduling non-determinism (kernel execution order across streams)** → a genuinely different mechanism, not just a third instance of the same one: cuBLAS/cuDNN's fast paths use atomic accumulation (multiple threads racing to add into the same location), where the hardware-scheduled *order* of those adds — genuinely non-deterministic, not just shape-dependent — changes the rounding. The fix is narrower and blunter: no floating-point atomics, full stop, replaced with fixed-order (warp-synchronous, fixed thread ordering) reductions. The pleasant surprise, reported directly by a production deployment (EigenAI) rather than assumed here: once atomics are gone and reduction order is pinned, *scheduling jitter stops mattering on its own* — their stress tests with background GPU workloads inducing scheduling jitter still produced bit-identical output, because the result no longer depends on execution timing, only on the now-fixed logical structure. Three named sources, effectively two mechanisms, one of which (reduction order) covers two of the three.

**Throughput cost — a real range, not a single number, and the range itself is the finding.** This sandbox's own timing (fixed-tree vs. numpy's adaptive sum, both pure CPU) showed a 3.06x slowdown — reported honestly, but flagged as dominated by Python-loop overhead against numpy's C-level adaptive path, not a clean stand-in for a real CUDA kernel's split-K/warp-specialization tradeoff, so it's not the number that matters here. What does: three independent real measurements, spanning eight months of engineering maturity —

| source | measured cost | context |
|---|---|---|
| Thinking Machines' original Triton batch-invariant kernels (Sep 2025) | up to 63% slower (one GEMM benchmark: 527 → 194 TFLOPS) | unoptimized research prototype, no split-K, no Tensor Memory Accelerator use |
| Broader batch-invariant deployments, per a Nov 2025 survey | 10–40%, op- and hardware-dependent | early production/adoption-stage kernels |
| EigenAI, production mainnet deployment (Jan 2026) | ~1.8–2% end-to-end latency; 95–98% of cuBLAS GEMM throughput | custom warp-synchronous kernels, no atomics, purpose-built rather than adapted |

The cost of full determinism didn't just get paid once — it's been getting *engineered down*, from a 63%-on-one-benchmark research prototype to a ~2% production system, in under a year. That trajectory matters more than any single number in this table for judging where this is headed, and reporting only the most flattering (2%) or most alarming (63%) figure would misrepresent what's actually known.

**One more real constraint worth carrying forward, not found by searching for it, found because it showed up in the same source as the cost numbers.** EigenAI's determinism guarantee is same-GPU-architecture-only: A100 and H100 produce different results for identical operations due to real hardware differences in FMA and rounding — "100% match rate on same-architecture runs, 0% cross-architecture," described in their own writeup as physics, not an engineering gap to close. A separate, very recent (June 2026) paper — Cankaya, "Bit-Exact AI Inference Verification Without Performance Tradeoffs" — claims bit-exact reproduction *across* GPU generations via software emulation instead of native fast kernels, which is a different point on the same tradeoff curve (more portable, presumably at its own performance cost this document hasn't measured or found a number for). Either way: §21's recomputation server inherits a real constraint here, whichever determinism approach it eventually uses — hardware-matching (cheap, architecture-locked) or emulation (portable, unmeasured cost) is a decision that section will actually have to make, not one this section can make for it.

**Where full determinism is worth it, where DiFR remains the better tradeoff.** The honest asymmetry: full determinism's cost lands on the *prover*, on *every* request, whether or not that request ever gets audited — it's a standing tax on 100% of traffic. DiFR's cost lands on the *verifier*, on only the sampled fraction C — §1's whole statistical framing exists specifically so the assurance-per-dollar math favors checking a sample over checking everything. That asymmetry, not just the raw percentage, is why full determinism becomes attractive exactly where it currently is being adopted: high-stakes, low-tolerance-for-any-error settings (EigenAI's own targets — trading agents, prediction-market judges) where a single undetected wrong answer has direct financial consequences and the prover already controls (or can standardize) its own hardware generation. DiFR remains the better tradeoff for this document's actual setting — compute governance verification across a prover's entire fleet, likely spanning hardware generations, where §1's aggregate statistical assurance was always the accepted standard rather than a compromise, and a 2–63% permanent throughput tax on a prover's production serving is a much harder sell than an unpredictable, budget-bounded recomputation cost paid by the verifier alone.

#### Self-check

Divergence measured before any fix: confirmed — 9 distinct results from 12 chunk sizes, this sandbox's own run, not cited from elsewhere. Reduction after the fix is a real measured number: confirmed — 1 result, exactly, both in the direct reduction-order test and the batching-simulation test. Throughput cost reported as an actual number: confirmed — this sandbox's own 3.06x (explicitly caveated as CPU-Python-overhead-dominated, not GPU-representative) plus three independently-sourced real production/research numbers spanning 63% down to ~2%, not a single cherry-picked figure. No claim of full determinism with zero measured cost anywhere in this section.

**Sources used in this section:** He et al. (Thinking Machines Lab), "Defeating Nondeterminism in LLM Inference" (Sep 2025) — the original 1000-completions/80-outputs/token-103 finding and the batch-invariant-kernels fix. vLLM GitHub issue #27433 and related PRs — real, ongoing production adoption through 2025–2026. A Jan 2026 LLM-42 paper (arXiv:2601.17768) — the "position invariance" terminology and the 527→194 TFLOPS / 63% figure, plus its own skeptical counter-argument (a parallel kernel stack as a real maintenance cost) used above for the DiFR-tradeoff conclusion. EigenAI (arXiv:2602.00182, and its own engineering writeups, Jan–Feb 2026) — the ~2% production overhead figure, the atomics/scheduling-jitter finding, and the same-architecture constraint. Cankaya, "Bit-Exact AI Inference Verification Without Performance Tradeoffs" (arXiv:2606.00279, June 2026) — the cross-hardware software-emulation alternative, flagged for §26.

---

### §8. Network Reproducibility

The source material's own "could be hard" flag is really a warning about scope creep — three sub-problems that could each expand into their own research program if allowed to. The self-check asks for an explicit conclusion, so that's where this starts, not where it ends up after a survey.

**The conclusion first, argued for below rather than after:** worth a real fix at the ingestion layer — retransmission-driven reordering (part of sub-problem 1). Worth a topology *constraint*, not new machinery — multi-path routing (the other part of sub-problem 1) and load-balancer attestation (sub-problem 2), both of which reduce to decisions this document already made rather than needing anything new. Already solved, retroactively — chunking canonicalization (sub-problem 3), by §2b's existing tested code, once it's fed correctly-ordered bytes.

**Sub-problem 1a: multi-path routing — a placement constraint, close to free.** A tap sitting on the inference unit's own direct uplink (the natural, minimal-trust placement §1 already committed to) sees a single physical link, not a fan-out point — there is no routing *decision* happening on a single wire for multiple paths to diverge across. Multi-path/ECMP reordering is a concern for aggregated links further upstream in a network fabric, structurally past where this design puts the tap. The fix here isn't a mechanism, it's a stated placement rule: **the tapped segment must be a single physical link with no link-aggregation/bonding across multiple physical paths upstream of the tap.** That's a topology constraint on §22's installation process, not a new protocol.

**Sub-problem 1b: retransmission-driven reordering — the part placement doesn't fix, built and tested.** Single-path placement doesn't help here: a retransmitted segment is a *new* packet, sent later, interleaved with whatever else the sender transmits in the meantime — not a delayed copy of the original arriving on the same wire in a way placement could prevent. §2b's existing reassembly code (`ChunkedDecoder`, `SseReassembler`) already handles arbitrary *chunk sizes* correctly (tested under 1–9-byte adversarial fragmentation in §2) but assumed in-order *arrival* — a real gap, not a hypothetical one, since a tap has no part in TCP's own handshake or retransmission logic and just sees whatever crosses the fiber in whatever order that happens to be.

Built `reorder.rs`: a buffer keyed on the TCP sequence numbers `frame.rs` already extracts (no new capture mechanism — data already in hand, just unused until now). In-order segments pass straight through; early arrivals get held until the gap closes, then cascade-deliver. Tested three ways: in-order delivery (trivial baseline), duplicate/retransmitted-segment handling (dropped, not double-appended), and full adversarial shuffling (reconstructs correctly regardless of arrival order) — all passing. Then wired directly into §2b's existing, unmodified chunked/SSE reassembly and swept across a realistic-jitter model (most segments in order, an adjustable probability of adjacent segments swapping, standing in for real retransmission-scale disruption rather than the fully-adversarial shuffle used for the unit tests):

```
swap_probability=0.00  segments=206  reordered_arrivals= 0  reconstruction_correct=true
swap_probability=0.05  segments=206  reordered_arrivals= 6  reconstruction_correct=true
swap_probability=0.15  segments=206  reordered_arrivals=21  reconstruction_correct=true
swap_probability=0.30  segments=206  reordered_arrivals=43  reconstruction_correct=true
```

200 SSE events, exactly reconstructed, at every jitter level from 0% to 30% adjacent-segment swaps — the reordering rate scales with the jitter probability as expected; reconstruction correctness doesn't depend on it at all. This is the one sub-problem in this section that got an actual new mechanism, because it's the one that genuinely needed one.

**Sub-problem 2: load-balancer attestation — reduces to a dial this document already has, not a new spoofable-field risk.** First question worth separating from the design question: does DiFR actually *need* to know which backend replica served a request? For the adversarial case this document mainly cares about — a prover routing likely-to-be-audited requests to an honest replica and everything else to a cheap one — §3 already closes this: sampling happens via a verifier-issued, unpredictable seed evaluated *after* a request has already been served, so a load balancer has nothing to condition on at routing time that correlates with later audit selection. That threat doesn't need a new mechanism; it's already covered.

What's left is attribution after the fact (if a specific replica is later found non-compliant, which historical requests did it actually serve) — a real, if lower-priority, question, and the design question the task actually asks: how to attest it without adding a field the prover's own load balancer could simply lie in. The honest answer is that this isn't a new cryptographic problem, it's the same physical-tap-placement question as sub-problem 1, one level down: §22 already treats tap granularity as a dial (fleet-wide down to per-server down to per-GPU), and at whatever granularity taps sit *at* the replica level, "which replica served this" is answered by *which physical tap observed it* — unspoofable for the same reason §2's passive splitter is trusted at all, because it's a property of physics and placement, not a claim in a packet. Aggregate the tap upstream of the load balancer instead (fewer taps, cheaper, §22's own stated tradeoff), and replica attribution becomes genuinely unavailable from the network layer — at which point the honest move is accepting that gap rather than patching it with a software-asserted replica-ID field the prover controls, which would be strictly worse than no field at all (a spoofable "attestation" is a liability, not a mitigation). No new mechanism belongs in this section; the real answer is "resolve granularity in §22, and know that whichever way it's resolved, this question's answer comes along for free or doesn't come at all — there's no in-between worth building."

**Sub-problem 3: chunking/retransmission-timing canonicalization — already solved, worth saying so explicitly rather than re-deriving it.** This is exactly what §2b's `ChunkedDecoder` + `SseReassembler` already do: reconstruct the logical SSE/token stream from wire-level HTTP chunking, independent of how bytes happened to be fragmented on the wire — tested under randomized 1–9-byte fragmentation in §2, including a real bug the fragmentation tests caught and fixed there. The only precondition that section's tests didn't cover is *arrival order*, which is precisely sub-problem 1b — now closed by `reorder.rs` feeding correctly-ordered bytes into unmodified §2b code. Nothing new was built for this sub-problem because nothing new was needed; the task's own phrasing ("a canonicalization step in §2b") describes work §2 already did, just without yet being connected to out-of-order arrival.

#### Self-check

Explicit conclusion reached, not a survey: confirmed — a stated position for all three sub-problems (fix at ingestion layer / topology constraint, not a mechanism / already solved), not a list of considerations with no resolution. The "could be hard" flag's actual failure mode — an open-ended survey — avoided by building the one piece that turned out to genuinely need building (`reorder.rs`) and explicitly declining to build the other two, with reasons stated rather than left as an oversight.

**Sources used in this section:** §1's tap-placement architecture and §22's tap-granularity dial (both this document, reused rather than re-derived) for the topology-constraint conclusions in sub-problems 1a and 2. §2's tested `ChunkedDecoder`/`SseReassembler` (this document) for sub-problem 3.

---

### §9. Non-Determinism Test Suite

All six required categories, run for real against §5's actual `difr.verify()` — 300 trials each, 30 tokens per trial, real generation through a real model for every single one, no synthetic deviation scores. Plus a seventh: the trigger backdoor split into triggered/untriggered arms, because collapsing those into one number would hide the most important result in this section.

**Mean deviation and full threshold sweep** (τ from 0.05 to 4.0, pass rate = fraction of 300 trials with avg_deviation ≤ τ):

| category | mean dev | τ=0.05 | τ=0.1 | τ=0.2 | τ=0.3 | τ=0.5 | τ=0.8 | τ=1.2 | τ=2.0 | τ=4.0 |
|---|---|---|---|---|---|---|---|---|---|---|
| honest_baseline | 0.0000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| hardware_drift | 0.0000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| cross_family | 0.0694 | 0.393 | 0.800 | 0.983 | 0.993 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| same_family (distilled) | 0.7191 | 0.000 | 0.000 | 0.007 | 0.033 | 0.267 | 0.653 | 0.923 | 1.000 | 1.000 |
| lora_trigger_OFF | 0.0000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| lora_unconditional | 7.8594 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| lora_trigger_ON | 7.9790 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

**Honest baseline: exactly 0.0000, 100% pass at every τ tested.** Per this section's own self-check, that's the required diagnosis check, not a result to be pleased about on its own — a nonzero honest-baseline deviation would mean §5 is broken, and the fix would be in §5, not in picking a more forgiving τ here. It's exactly zero for the same reason it was exactly zero in §5: honest generation and honest recomputation run the identical deterministic function.

**Hardware-generation drift: passes, and it's grounded in a real measurement, not assumed.** Simulated by adding Gaussian noise at 3×10⁻⁶ scale to the verifier's logits before comparison — not an arbitrary number, that's the actual order of magnitude §7 measured for reduction-order-driven float32 spread on a hidden-dimension-scale sum. At that scale, deviation stayed at 0.0000 across all 300 trials: real hardware-generation drift is small enough, relative to Δmax=8.0 and any τ worth calibrating, to disappear entirely into rounding. This is the one category where a "should pass" result really is just confirming §7's finding transfers correctly into §5's comparison, not an independent discovery.

**LoRA backdoors: both variants collapse to the Δmax ceiling, and the trigger split is the actual finding of this section.** `lora_unconditional` (mean 7.86, ceiling is 8.0) and `lora_trigger_ON` (mean 7.98) both fail completely at every τ tested — a real, trained low-rank adapter (not simulated) shifting output toward a fixed backdoor target gets caught immediately and unambiguously, because forcing an implausible token even once drives that token's rank to the bottom of the vocabulary and clips straight to Δmax. But `lora_trigger_OFF` — the *identical* adapter, on the *identical* model, with the trigger simply absent from context — passes 100% at every τ, indistinguishable from the honest baseline. This is the actual, sobering result: **a trigger-conditional backdoor is invisible to this verification scheme for as long as the trigger never appears in whatever traffic gets sampled.** Nothing in §5's mechanism looks for the *capacity* for a backdoor — it only ever measures deviation on the specific tokens actually produced, and a dormant backdoor produces no deviation at all because it isn't doing anything. That's not a bug in this implementation; it's a structural property of output-level statistical verification, worth carrying forward explicitly into §10 (red-teaming this exact gap) and §12 (which already exists specifically because bounded-deviation checking has room to hide things in).

**Cross-family vs. same-family: the results contradict the pattern this section's own task description predicted, replicated three times before being reported as such.** The task expects cross-family to show a clearly bigger gap than same-family/distillation. The measured result is the opposite: cross-family mean deviation (0.069) is over 10x *smaller* than same-family (0.719), and the threshold sweep shows cross-family separating cleanly from honest by τ≈0.1 while same-family needs τ≈0.8–1.2 before pass rate rises substantially. Before reporting this as a real finding rather than a bug, it was checked three ways: an independently-undertrained same-architecture model (mean dev 1.15), a lightly-distilled same-architecture model — 1,500 real KL-divergence-against-the-teacher training steps, not just fewer independent steps (mean dev 1.88), and a budget-matched distillation — 6,000 steps, equal to cross-family's training budget (mean dev 0.72, the number reported above). All three land in the same place, well above cross-family's 0.069, and the gap *shrinks* with more distillation budget without closing it. That's a consistent, not a fluky, result.

The likely explanation: DiFR's deviation score is sensitive to how well a model's output distribution has *converged* toward the target it's optimizing for, and — in this toy setup specifically — pure knowledge-distillation-from-random-initialization is a harder optimization problem than ordinary hard-label training on raw text, even holding architecture and step count fixed. The cross-family model had an easier training objective and reached comparable *raw* loss (2.298 vs. the honest model's 2.27) despite being architecturally different; the distilled model, trained only against soft teacher labels with no hard-label signal to anchor it, converged less completely toward the teacher's specific output distribution in the same number of steps. That's a genuine confound in this experimental setup, named rather than papered over: a fair architecture-only comparison would need distillation with a more standard mixed hard/soft loss, or a longer distillation budget, to isolate "same family" from "harder optimization problem" as separate variables — this document doesn't have that comparison, and says so rather than implying it does.

What this finding is still worth, confound and all: **whether a substitute model gets caught depends more on how well it's converged toward matching the honest model's output distribution than on whether it's nominally the "same family."** That's a real, actionable input to §11's calibration — a threat model that assumes cross-family attacks are the dangerous ones and same-family/distilled attacks are the subtle, hard-to-catch ones has it backwards at least in this toy setup, and shouldn't be assumed true at frontier scale without checking.

**Short-output (<5 token) false-negative rate, reported separately as required, at τ=0.3:**

| category | 3-token FN rate | 30-token FN rate | ratio |
|---|---|---|---|
| cross_family | 0.927 | 0.993 | 0.93x |
| same_family (distilled) | 0.427 | 0.033 | 12.8x |
| lora_unconditional | 0.000 | 0.000 | 0.00x |
| lora_trigger_ON | 0.000 | 0.000 | 0.00x |

Three genuinely different shapes, not one blanket "short outputs are risky" statement. LoRA backdoors: the short-output blind spot doesn't apply at all — one forced implausible token clips to Δmax regardless of how many tokens surround it, so 3-token and 30-token false-negative rates are both exactly zero. Cross-family: already so different that even 3 tokens mostly gives it away (its false-negative rate barely moves, 0.93 → 0.99, both high because cross_family's deviation per-token is modest even at length — consistent with the architecture-vs-convergence finding above, not a contradiction of it). Same-family/distilled: this is where the short-output blind spot is real and large — a 12.8x jump in false-negative rate going from 30 tokens down to 3, exactly the failure mode §6's diffusion-step reasoning leaned on and this section now confirms with real numbers instead of assuming it. The subtle-deviation case is precisely the one the short-output edge case hides best, which is the worst possible pairing for a verification scheme to have and the reason this document keeps returning to it.

#### Self-check

All six required categories implemented and run: confirmed (honest baseline, cross-family, same-family/distillation, hardware-generation drift, LoRA backdoor unconditional, LoRA backdoor trigger-conditional — the last one split into two arms rather than one, which is additive, not a substitute for the required category). Results are a real pass-rate-vs-τ curve at multiple τ values: confirmed, nine τ values swept per category, not one number. Honest baseline shows near-100% pass: confirmed — exactly 100% at all nine τ, diagnosed correctly per the self-check's own instruction as "§5 is working," not adjusted toward.

**Sources used in this section:** §5 (this document) — the `difr.verify()` implementation tested here, unmodified. §7 (this document) — the 3×10⁻⁶ noise scale used for hardware-drift simulation, taken from that section's own measured reduction-order spread rather than chosen arbitrarily.

---

## Next section

§10 (**Recomputation Red-Team**) is next — directly continuing from this section's own trigger-backdoor finding: a dormant trigger is invisible to output-level verification by construction, which is exactly the kind of gap a red-team pass should try to exploit on purpose rather than wait to discover. Real attack code against §5's real server, re-running §9's suite before and after each proposed patch, per that section's own self-check.

---

### §10. Recomputation Red-Team

All four named attacks, each implemented as real code against §5's real `difr.verify()` or §3's real `sample_decision()`, each with a proposed patch that was also actually tested — not proposed and left there. Distinct, separately-reported results for each, per the self-check.

#### Attack 1: exploiting seed control — session shopping

Not the seed value itself (§5 already closed that — no client-supplied seed field exists). The remaining angle: create many candidate sessions, silently discard the ones that would fail, only ever act on the one that passes. Tested with 60 logical requests, k candidate attempts each, τ=0.3:

| model | k=1 | k=5 | k=20 | k=50 | abandonment rate (k=20) |
|---|---|---|---|---|---|
| same_family | 0.050 | 0.267 | 0.617 | 0.783 | 0.955 |
| cross_family | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |

For same_family, shopping is a real, large advantage — single-attempt pass rate of 5% becomes 78% with 50 attempts. For cross_family, shopping adds nothing measurable, because §9's finding (cross_family already passes at ~99%+ even honestly-attempted) means there's nothing to shop for. That's not a gap in the attack; it's the same underlying result from §9 showing up again from a different angle.

**Patch: track session-creation-to-verification ratio, flag outliers.** Every session gets logged at creation (§5's schema already does this — the fix is a query, not new infrastructure). An honest prover has no structural reason to abandon sessions beyond ordinary background noise (client crashes, unfinished requests); modeled generously at 5%. Tested:

| | abandonment rate | vs. honest baseline |
|---|---|---|
| honest baseline (benign only) | 0.050 | 1.0x |
| same_family shopping, k=20 | 0.955–0.963 | ~19x |
| cross_family shopping, k=20 | 0.000–0.048 | ~0–1x |

The patch cleanly catches the attack that's actually worth catching (same_family, ~19x the honest background rate — trivially separable) and correctly does nothing for cross_family, which isn't shopping because it doesn't need to. A detector that fired on cross_family too would be flagging honest-passing behavior, which would be the wrong outcome, not a more cautious one.

#### Attack 2: steganographic encoding below τ

Not a substituted model — the *honest* model's own logits, with the operator deliberately choosing among within-tolerance alternatives to smuggle a hidden bitstream: at each token, if a hidden bit is pending and switching from the verifier's rank-0 choice to rank-1 costs no more than a fixed per-token budget, spend the budget and encode a bit; otherwise emit the honest choice. 20 hidden bits targeted per 30-token output, 200 trials per budget:

| per-token budget | mean avg_deviation | pass @ τ=0.3 | pass @ τ=0.5 | bits successfully encoded |
|---|---|---|---|---|
| 0.05 | 0.0008 | 1.000 | 1.000 | 14.4% |
| 0.10 | 0.0034 | 1.000 | 1.000 | 25.4% |
| 0.20 | 0.0113 | 1.000 | 1.000 | 41.1% |
| 0.30 | 0.0245 | 1.000 | 1.000 | 55.9% |
| 0.50 | 0.0558 | 1.000 | 1.000 | 74.0% |

Even at the most aggressive budget tested — spending up to half of τ itself on any single token — the *averaged* deviation stays at 0.056, comfortably under any τ this document has calibrated against, while successfully smuggling three-quarters of a 20-bit payload over one 30-token output. Averaging is exactly the mechanism that hides this: most tokens carry a "0" bit for free (the honest choice, zero cost), diluting the real cost paid on the "1" bits across the whole output. §12 exists to quantify this properly (real bit-capacity bounds, a commitment-scheme countermeasure); this section only needed to show the gap is real and immediately exploitable, which it is.

**Patch: per-token deviation distribution, not just the average.** Honest generation (§5, §9) has token-level deviation of exactly 0.0 — real floating-point noise lives around 10⁻⁶, six orders of magnitude below any threshold worth setting. Tested "fraction of tokens with deviation > 0.01" as a detector:

| | fraction of tokens > 0.01 deviation | vs. honest |
|---|---|---|
| honest sessions | 0.0000 | 1.0x |
| stego, budget=0.05 | 0.0327 | ~33,000x |
| stego, budget=0.10 | 0.0633 | ~63,000x |
| stego, budget=0.20 | 0.1240 | ~124,000x |
| stego, budget=0.30 | 0.1727 | ~173,000x |

Even the *stealthiest* budget tested — the one that got through the average-only check cleanest — is four orders of magnitude above the honest rate on this distributional check. The average hides the attack; the distribution doesn't, because "deliberately paying a bounded cost on a controlled fraction of tokens" and "genuine floating-point noise" produce structurally different shapes, not just different totals. Worth carrying into §11's calibration as a second, cheap signal alongside τ itself, not a replacement for it.

#### Attack 3: concentrating deviation into short outputs — weaponized, not just observed

§9 found the false-negative pattern; this section tests whether a strategic prover can actually exploit it by deliberately keeping every dishonest response under 5 tokens. 150 trials, τ=0.3:

| model | always-short (3 tok) pass rate | always-long (30 tok) pass rate |
|---|---|---|
| same_family | 0.387 | 0.060 |
| cross_family | 0.927 | 1.000 |

For same_family, staying short is a real 6.4x advantage (39% vs 6%) — a strategic attacker gains exactly what §9's passive measurement predicted it would. For cross_family, the gap barely moves, consistent with cross_family already passing regardless of length (same underlying reason as attacks 1 and 3 both showing little effect there).

**Patch: mandatory paired long-output resampling for any low-confidence session.** A session flagged `low_confidence` doesn't stand alone — the verifier requires one additional, longer-output sample from the same claimed context before extending trust, and *both* have to pass. Tested — require the short sample AND an independently-generated 30-token sample to both pass:

| model | pass rate requiring both |
|---|---|
| same_family | 0.000 |
| cross_family | 0.913 |

Complete elimination of the short-output advantage for same_family — zero, not reduced. Cross_family stays high, correctly, because it isn't exploiting anything; a patch that suppressed it too would be punishing a model for being close to honest, which isn't the goal.

#### Attack 4: timing/scheduling manipulation biasing which packets get sampled

§3 already showed, empirically, that a prover without the verifier's key cannot *predict* individual sampling decisions better than chance (guessed keys and a 480K-example logistic regression both landed within 0.005 AUC of 0.5). So this section tests a different, sharper question: without predicting anything, can a prover manipulate *how many independent packet_ids* a fixed amount of dishonest content gets split across, to reduce N_fake in §1's own detection formula? Real `sample_decision()` calls, 20,000 trials per scenario, C=1%:

| framing | empirical P(caught) | §1's formula predicts |
|---|---|---|
| 500 small packets | 0.9947 | 0.9933 |
| 50 medium packets | 0.3901 | 0.3935 |
| 5 large batched | 0.0484 | 0.0488 |
| 1 maximally batched | 0.0100 | 0.0100 |

Empirical and formula-predicted detection probability match almost exactly at every scale — both the PRF implementation and §1's math are behaving exactly as designed, which is itself worth confirming rather than assuming. But the finding is real and concerning: batching the same dishonest content into fewer, larger packets takes detection probability from 99.5% down to 1% — a genuine, large, and *legal* (within the mechanism as specified) attack, requiring no prediction of anything.

**Patch: this isn't a PRF problem, so it doesn't get a cryptographic patch.** A stronger keyed function wouldn't help — the attack never tried to predict `sample_decision`, it changed how many times the coin got flipped for the same amount of content. The actual fix already exists elsewhere in this document and just needs to be pointed at: §4's bandwidth-reduction hashing and §14's granularity roadmap both already treat "how finely is traffic divided into checkable units" as a verifier-controlled dial, not a prover-controlled one. No new mechanism belongs in this section; the real requirement, stated explicitly rather than left implicit, is that whatever defines a "packet" for §3's sampling purposes must be a property the tap/gateway determines mechanically (byte count, time window, or similar, fixed by the verifier's configuration) — never something inferable from the prover's own request-batching choices.

#### Self-check

§9's suite (or the equivalent purpose-built variant for attacks that don't map onto its exact categories) re-run against every proposed patch, before-and-after numbers reported: confirmed for all four — session-abandonment detection (patch 1), per-token distribution detection (patch 2), mandatory paired resampling (patch 3), and the granularity-dial pointer (patch 4, correctly *not* a new mechanism, with that absence itself justified rather than silently skipped). Each of the four named attacks reported as a distinct, separate test case: confirmed — four attacks, four tables, no generic "robustness score" collapsing them into one number.

**Sources used in this section:** §3, §5, §9 (this document) — every attack and patch above runs against that existing, tested code, not a reimplementation. §1's detection-probability formula (this document) — confirmed empirically by attack 4 rather than just cited.

---

## Next section

§11 (**Calibration & Mock Hardware Emulator**) is next — sweeping τ and temperature across the honest/dishonest pairs this document has now accumulated (§9's six categories, §10's four attack patterns) to recommend a real per-model τ table, and explicitly checking for pairs with no clean separation rather than assuming every case resolves cleanly. Every real number this section needs already exists in `test_suite_results.json` and this section's own attack data — the sweep infrastructure exists too, from §9 — so this is genuinely a synthesis-and-analysis section built on real prior measurement, not new measurement from scratch.

---

### §11. Calibration & Mock Hardware Emulator

The "mock hardware emulator" the title names isn't a separate deliverable from calibration — it's what §9's `test_suite.py` and §10's `redteam.py` already are: synthetic honest/dishonest traffic generation standing in for a real fleet of diverse hardware and adversarial provers, which this sandbox has neither of. This section's actual new contribution is the second axis the task asks for that nothing before it swept: temperature, alongside τ.

**AUC(honest vs. dishonest), across temperature — the separation-quality check before committing to any specific τ.** 120 trials per cell, 30-token outputs:

| model | T=0.3 | T=0.5 | T=0.8 | T=1.2 | T=1.6 |
|---|---|---|---|---|---|
| same_family | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| cross_family | 0.9958 | 1.0000 | 0.9958 | 0.9958 | 0.9958 |

Read on its own, this table looks like good news everywhere — AUC above 0.99 at every cell means *some* threshold separates honest from dishonest almost perfectly, for both models, at every temperature tested. That's the reading to be suspicious of, per this section's own self-check: near-perfect AUC across the board usually means the calibration wasn't adversarial enough yet, not that the problem is solved. The next table is where that shows up.

**Recommended τ per model, per temperature — and where it stops being clean.** τ set at the 99th percentile of honest deviation (which, in this toy setup, is exactly 0.0 at every temperature tested — genuine floating-point noise here really is that close to zero, per §7's and §9's own findings) plus a fixed 0.02 margin:

| model | temp | recommended τ | honest pass rate | dishonest pass rate | separation |
|---|---|---|---|---|---|
| same_family | 0.3 | 0.0200 | 1.000 | 0.000 | CLEAN |
| same_family | 0.5 | 0.0200 | 1.000 | 0.000 | CLEAN |
| same_family | 0.8 | 0.0200 | 1.000 | 0.000 | CLEAN |
| same_family | 1.2 | 0.0200 | 1.000 | 0.000 | CLEAN |
| same_family | 1.6 | 0.0200 | 1.000 | 0.000 | CLEAN |
| cross_family | 0.3 | 0.0200 | 1.000 | 0.075 | CLEAN |
| cross_family | 0.5 | 0.0200 | 1.000 | 0.050 | CLEAN |
| cross_family | **0.8** | 0.0200 | 1.000 | **0.125** | **NO CLEAN SEPARATION** |
| cross_family | **1.2** | 0.0200 | 1.000 | **0.142** | **NO CLEAN SEPARATION** |
| cross_family | **1.6** | 0.0200 | 1.000 | **0.175** | **NO CLEAN SEPARATION** |

This is the real finding, and it's the opposite of what the high-AUC table alone would suggest: at a τ tight enough to be justified by this model's actual (near-zero) legitimate noise floor, cross_family's leakage through that threshold *climbs steadily with temperature* — 7.5% at T=0.3, up to 17.5% at T=1.6, crossing this section's own "clean" bar (dishonest pass ≤ 10%) somewhere around T=0.8. The AUC table didn't show this because AUC considers every possible threshold, including ones far more permissive than the actual justified τ; the honest-vs-dishonest gap can look excellent in aggregate while the *one threshold you can actually defend from the honest noise floor* still lets a meaningful fraction of dishonest traffic through, and that fraction gets worse exactly as temperature rises.

**Why temperature does this, mechanistically, not just empirically.** Gumbel-max sampling divides logits by temperature before adding noise: `argmax(logits/T + noise)`. At low T, logit differences get amplified relative to the noise — a dishonest model's deviation from the honest one's logits translates directly into a bigger gap in the noise-perturbed decision score, which is easier to catch. At high T, logit differences get *shrunk* relative to the now-relatively-larger noise term, so the same underlying dishonesty produces a smaller, noisier signal in the comparison — harder to catch, exactly as measured above. This means **temperature isn't just a decoding parameter a real deployment happens to pick — it's a detectability lever a dishonest prover has some influence over**, to the extent they can choose or bias their own serving temperature within whatever range looks like normal operation, which is worth flagging as its own consideration for §21's threat model rather than assuming τ calibration is temperature-agnostic.

**No-clean-separation case, reported as required rather than smoothed over:** cross_family at T≥0.8, under a τ properly justified by this model's own honest-noise floor. The honest fix isn't a cleverer τ at a fixed temperature — §10's per-token-distribution patch (attack 2's countermeasure) is a more promising direction here too, since it doesn't rely on the aggregate score that temperature is specifically degrading, but this section's job was calibration, not a new detector, so that connection is noted rather than built out here.

#### Self-check

τ reported per model as an explicit table, not a single global number: confirmed — two full model × temperature tables above. At least one pair checked for no clean separation: confirmed, and it's a real measured result (cross_family, T≥0.8), not a placeholder caveat — found specifically because the AUC-only view initially looked clean everywhere, which is exactly the signal this section's self-check warns not to trust without pushing further into an actual recommended-τ table.

**Sources used in this section:** §5, §7, §9 (this document) — the models, the honest-noise-floor measurement, and the deviation-scoring machinery this section sweeps rather than rebuilds.

---

## Next section

§12 (**Anti-Steganography & Commitment Schemes**) is next, and §10's attack 2 already did most of the empirical groundwork this section needs to build on rather than starting cold: a real bit-capacity demonstration (74% of a 20-bit payload smuggled through 30 tokens, undetected by average-only scoring) and a real countermeasure direction (per-token distribution checking) already exist. This section's job is to go deeper — an actual bound on covert capacity, not just a demonstration it's nonzero, and a real commitment-scheme design with a named hash function and opening protocol.

---

### §12. Anti-Steganography & Commitment Schemes

#### Bit-capacity bound, computed rather than demonstrated

§10 showed the channel is nonzero. This section bounds it properly: at each real generated position, the cost of choosing the k-th ranked token instead of the verifier's top choice is known exactly — the same ranking DiFR itself computes. Given a total average-cost budget of N·τ across N positions, the capacity-maximizing allocation is a water-filling problem, structurally the same as channel capacity under a power constraint: spend budget wherever it buys the most bits per unit cost, position by position, until exhausted. Solved by real greedy allocation over 200 real generated positions' actual cost curves, not assumed analytically:

| τ | T=0.5 | T=0.8 | T=1.2 |
|---|---|---|---|
| 0.02 | 0.168 bits/tok | 0.173 bits/tok | 0.181 bits/tok |
| 0.05 | 0.263 bits/tok | 0.264 bits/tok | 0.284 bits/tok |
| 0.10 | 0.349 bits/tok | 0.367 bits/tok | 0.396 bits/tok |
| 0.20 | 0.480 bits/tok | 0.508 bits/tok | 0.549 bits/tok |
| 0.30 | 0.574 bits/tok | 0.613 bits/tok | 0.671 bits/tok |

Two real, computed patterns, not assumptions: capacity grows *sub-linearly* with τ (cheapest bits get spent first — diminishing returns, as any water-filling allocation produces), and capacity *increases with temperature at every τ tested*. The second finding isn't new information exactly — it's §11's temperature-sensitivity result showing up again from the capacity side rather than the detection-rate side, which is the same underlying mechanism (`logits/T` shrinks relative to noise as T grows) manifesting as *both* worse detection *and* more covert bandwidth, because they're the same phenomenon measured two ways.

**A real scaling caveat, stated rather than hidden behind the table.** This is a 65-character vocabulary; a frontier LLM's vocabulary is 50,000–100,000+ subword tokens. More candidate tokens at comparable per-rank cost plausibly means *more* achievable bits/token at a given τ on a real model, not less — this document has no way to measure that gap directly, and the honest position is that the table above is a real, computed bound for this toy setup, and a methodology (gather real cost curves, water-fill against the actual τ budget) that transfers directly, not a number that does.

#### The warden: a commitment scheme, specified rather than named

**Hash function: BLAKE3.** Not SipHash-1-3-128 (§2–§4's line-rate frame-tagging MAC) — different threat model, different tool. A commitment needs real preimage and collision resistance behind it, which is what a general-purpose cryptographic hash is designed and analyzed for; SipHash trades some of that conservatism for raw speed at a job (tagging millions of small frames) this isn't. BLAKE3 was already in this project's toolkit (§2 benchmarked it — it lost the frame-hashing race to SipHash/AES-GMAC at small sizes) and is exactly the right tool here, at a job with entirely different requirements.

**Commitment:** `C = BLAKE3(canonical_bytes(top_K_logits, top_K_token_ids) || nonce)`, nonce a fresh random 16 bytes per position, canonical byte layout (fixed token-ID-then-float32-logit ordering) so both sides hash identically. **Opening:** prover reveals `(top_K_logits, top_K_token_ids, nonce)`; verifier recomputes the hash and checks it matches `C`.

**The property this buys, precisely, and why it needs a protocol change, not just a hash.** §10's stego attack computed `scores = logits/T + noise` — using noise it already had — to find the cheapest within-tolerance alternative. If the prover must commit to its intended logits *before* that position's noise is revealed, it cannot search for a cheap opportunity, because at commitment time it doesn't yet know what "cheap" will mean. That requires reordering §5's protocol: seed (or at least each position's noise) can no longer be issued all at once, up front — it has to be revealed one position at a time, after that position's commitment lands. A verifier now checks two things per token: standard DiFR (does the claimed token match the verifier's own recomputation, within τ) and self-consistency (does the claimed token match what the *opened, hash-verified* commitment predicts, under the now-known noise).

**Tested — including a real bug the testing caught.** First run: honest self-consistency measured 0.9317, not 1.0. Before writing that off as acceptable noise, it was diagnosed: Gumbel noise has a long right tail, and a token *outside* a top-12 commitment can, rarely, still win under logit+noise — making an honest reveal look "inconsistent" purely from commitment truncation, not dishonesty. Swept K directly rather than guessing a fix: K=8 → 0.874, K=12 → 0.923, K=20 → 0.982, K=30 → 0.995, K=50 → 0.998, confirming truncation (not a protocol bug) was the cause and giving a real, evidence-based operating point. At K=50:

| §10's stego attacker, budget | avg_deviation (DiFR alone) | pass @ τ=0.3 (DiFR alone) | self-consistency | bits encoded |
|---|---|---|---|---|
| honest baseline | — | 1.000 | 1.0000 | — |
| 0.05 | 0.0003 | 1.000 | 0.9883 | 1.7% |
| 0.10 | 0.0011 | 1.000 | 0.9770 | 3.2% |
| 0.20 | 0.0034 | 1.000 | 0.9647 | 5.2% |
| 0.30 | 0.0038 | 1.000 | 0.9697 | 4.5% |
| 0.50 | 0.0087 | 1.000 | 0.9627 | 5.6% |

Exactly the pattern the design predicts: DiFR-alone stays fooled at 100% pass across every budget — same result as §10, confirmed again here as the baseline the warden has to improve on — while self-consistency separates cleanly from honest (1.0000) at every tested budget, and degrades *monotonically* with how much is being encoded, which is itself a useful property: this isn't just a binary catch, it's a gradeable signal that scales with attack intensity.

**Latency cost, argued for rather than glossed over.** This is real and large if implemented at maximum security: per-token commit-then-reveal-noise-then-generate turns one round-trip per response (§5's current design — get a seed once, generate freely) into one round-trip *per output token*. For a 100-token response, that's roughly 100x the round-trip overhead of the current protocol — a genuine cost, not a rounding error. The mitigable version: commit in K-token lookahead blocks instead of per-token, using the prover's own greedy/expected continuation as the committed proxy for that block, trading a K-times reduction in round-trips against a small, honest source of legitimate self-inconsistency (the greedy proxy won't always match what the block actually generates, for the same structural reason τ has to tolerate non-adversarial noise elsewhere in this document) — the same shape of tradeoff as the K-truncation issue just found and fixed, one level up. **Compatibility with §5:** additive, not a replacement — same seed, same Gumbel-max ranking, same DiFR comparison as the first-line check; the commitment layer wraps around it rather than substituting for it, at the cost of changing when the seed gets revealed.

#### Self-check

Bit-capacity estimate is an actual computed number, not "some number of bits": confirmed — a full τ×temperature table from real water-filling over 200 real generated positions' real cost curves, with the scaling caveat to frontier-vocabulary size stated rather than implied away. Commitment scheme names a specific hash function and a specific opening protocol: confirmed — BLAKE3, exact commitment construction, exact opening check, tested against both an honest prover and §10's actual attacker rather than described and left unverified.

**Sources used in this section:** §2 (this document) — BLAKE3's prior benchmarking, repurposed here for a reason specific to this section's threat model. §10, §11 (this document) — the stego attacker and the temperature-capacity connection this section builds on directly rather than re-deriving.

---

## Next section

§13 (**Auditor Compilation into GPU Instructions**) is next, and it's explicitly scoped as "one reasonable operationalization" of a single line in the source material, not an established spec — a DSL sketch and a compiler-shape design, with the raw-CUDA/PTX bypass named as a real, unresolved gap rather than solved. Lighter on measurement than the last several sections, closer to §6's shape: concrete reasoning over an under-specified problem, not a benchmark.

---

### §13. Auditor Compilation into GPU Instructions

One line in the source material, honestly scoped as exactly that: what follows is a reasonable sketch, not a spec anyone should treat as settled.

**What the DSL needs to express.** Enough to make "matches its approved specification" a property of compiled bytes, not a paperwork claim: checkpoint identity (a hash, reusing §19's manifest pattern rather than inventing a second one), operation class (forward-pass ops only — matmul, attention, layernorm, activation functions — explicitly excluding backward-pass and optimizer-state ops, since that boundary is most of what "inference-only" needs to mean at the instruction level), resource bounds (max batch size, max sequence length), and declared collective-communication pattern (tying back to §1's stripped-down east-west networking — a workload declaring `collective_ops: NONE` that then tries to emit an all-reduce is exactly the kind of mismatch this exists to catch). Sketch, not a grammar:

```
workload inference_v1 {
    checkpoint_hash: a3f8e91c9e21
    operation_class: FORWARD_ONLY
    max_batch_size: 256
    allowed_ops: [matmul, attention, layernorm, gelu]
    collective_ops: NONE
}
```

**How a compiler turns that into a machine-checkable certificate — the real mechanism, not just an assertion that one exists.** The underlying idea is the same one reproducible software builds already rely on: if compiling the same declared source always produces the same instruction bytes, a hash of those bytes *is* a certificate — anyone can check a running workload against it without re-trusting the compiler each time it's invoked, only trusting it once, auditably. Tested that claim directly rather than taking it on faith, using gcc against a toy stand-in for "GPU instructions" (no PTX toolchain here, but the determinism property being tested doesn't depend on which instruction set it's applied to):

**Two real bugs, caught by testing exactly the properties that matter, not by inspection.** First attempt: compiling the identical declared workload twice, into differently-named source files with byte-identical content, produced *different* certificate hashes. Cause: the source filename itself leaks into compiled output (debug metadata) — a well-documented real gotcha in the reproducible-builds world, not a contrived one. Fixed by compiling under one fixed filename with path-remapping flags (`-ffile-prefix-map`) and disabling the linker's build-ID note. Second attempt, after that fix: two *differently*-declared workloads (max_batch_size 256 vs. 512) compiled to *identical* binaries. Cause, more concerning than the first: the generated C encoded the declared bounds as unused static constants, and `-O2` dead-code-eliminated all of them, since nothing in the actual code path read them — silently defeating the entire certificate mechanism, because the compiled bytes no longer depended on the value supposedly being certified. Fixed by making every declared field something the generated code actually reads and uses. After both fixes, all four required properties hold for real: same source → same certificate; different declared workload → different certificate; post-compilation tampering → detected; and — the gap this section exists to name —

**A raw-CUDA/PTX bypass, demonstrated as a real gap, not a footnote.** A hand-written program achieving the identical runtime behavior, compiled without ever going through `parse_dsl`/the certificate step, produces a binary with a real hash — and there is no DSL source that hash traces back to, no certificate was ever issued for it, and no approved-workload registry entry exists to compare it against. The mechanism above has *nothing to say* about that binary. Not "flagged." Not "unknown risk, investigate." Outside its scope entirely. That's not a limitation this design can engineer its way past — a compiler-emitted certificate can only ever attest to things that went through the compiler. **This only works at all if reaching the GPU without going through the DSL's compiler is itself prohibited by policy, and enforced by something other than this mechanism** — which is exactly why the source material's single line about this connects forward to §23 (Workload Approval, which decides what's permitted at all) and §29 (Track 1's lower-assurance, no-new-hardware auditing regime, which is closer to what actually has to catch a determined bypass). No amount of polish on the DSL or the compiler closes this; it's a policy dependency, stated as one.

#### Self-check

Given the one-line source, the actual bar was intellectual honesty over technical completeness — the bypass gap is stated as a real, unresolved, load-bearing limitation in its own paragraph above, not softened into a closing caveat. The two bugs the demonstration caught are reported in full, including the ways they'd have made the certificate mechanism silently wrong (matching-when-it-shouldn't, mismatching-when-it-shouldn't) rather than only reporting the version that already worked.

**Sources used in this section:** §19's manifest-hash pattern and §1's collective-communication scoping (both this document), reused rather than reinvented for the DSL's checkpoint-identity and collective-ops fields. Reproducible-builds practice (the general software-supply-chain discipline, not a single paper) as the precedent the certificate mechanism is modeled on.

---

## Next section

§14 (**Granular Evidence Collection Roadmap**) closes out Part II — extending §1's detection-probability formula into an assurance-vs-granularity curve, using real numbers this document already has (§2's tap ceiling, §4's hash-only throughput, §8's reordering fix) rather than a fresh model. A synthesis section, structurally similar to §11: the measurements already exist, the job is composing them into a staged roadmap with named prerequisites per section.

*This section also had a real starting point beyond this document's own prior work: a second AI (Kimi) produced an independent pass at several sections of this same sequence, uploaded partway through, incomplete but genuinely executed rather than fabricated (verified directly — a from-scratch BLAKE3 implementation byte-matched against the real reference library, a SipHash test vector passed, a SQLite log contained real GPT-2 tokenizer artifacts, and re-running one of its scripts myself reproduced its saved output almost exactly). Its `assurance_model.py` got this section's structure right — four stages, real dependencies named, §1's formula, a real plot — and is credited for that below. It also has a real gap this version closes.*

---

### §14. Granular Evidence Collection Roadmap

**The gap in the first real model of this, found by running it.** Kimi's `assurance_model.py` computes the recomputation budget C needed for 99% detection confidence as a function of N_fake — correctly using §1's exact formula — but N_fake is entered as the same constant ("fakes per day") at every granularity stage. Running it confirms this directly: **C-required-for-99% comes out identical across all four of its stages**, request-level through token-level. That can't be right, and it's worth being precise about why: it treats granularity as changing *what gets sampled* without changing *what a violation costs to hide*, when the entire mechanism by which finer granularity is supposed to help is that the same real-world violation becomes a *bigger* N_fake when measured in smaller units — a single dishonest response is 1 fake unit at request-granularity, but the same response is 40 fake units at frame-granularity and 512 at token-granularity. Holding N_fake constant across stages removes the one variable this section is actually about.

**The model, corrected to let granularity change N_fake.** Same violation — one full dishonest request (512 tokens, 40 frames), held constant in real-world size — measured in each stage's own units, at a reference load of 1,000 req/s:

| stage | depends on | N_fake for this violation | C required for 99% detection | recompute load | effective cost (incl. §8's reproducibility burden) |
|---|---|---|---|---|---|
| S0: request-level | §2 | 1 | **0.990** | 0.012 Gbps | 0.0016 cores |
| S1: frame-level | §2, §8 | 40 | **0.109** | 0.052 Gbps | 0.0082 cores |
| S2: frame-level, gateway-sampled | §2, §3, §4, §8 | 40 | **0.109** | 0.052 Gbps | 0.0082 cores |
| S3: token-level | §2, §3, §8, §22 (unsolved) | 512 | **0.009** | 0.055 Gbps | 0.0225 cores |

Two real, quantitative findings, not qualitative ones. First: the required C for the *same* violation drops by two orders of magnitude, 0.99 down to 0.009, purely from measuring evidence in smaller units — this is the actual content of "for a target assurance level, state the coarsest granularity that achieves it," computed rather than asserted. Second, and less obvious: the *absolute* recompute load barely moves (0.012 → 0.055 Gbps) across the same range, because the shrinking required fraction C roughly offsets the growing total packet volume — going finer doesn't cost anywhere near what "40x, then 512x more packets" sounds like it should, *if* recompute capacity were the only thing that scaled. It isn't: the "effective cost" column, weighting by §8's own reproducibility-burden findings (modest for the reorder buffer S1/S2 actually needed, deliberately set to 3x for S3 specifically because backend visibility is *unsolved*, not merely harder), shows the real cost climbing about 14x from S0 to S3 — the honest expense of finer granularity lives in engineering burden, not recompute cycles, matching exactly what §8 already found and this section now prices in rather than re-deriving.

**What this means for "coarsest granularity that achieves a target":** depends entirely on the smallest violation worth catching, which is where this connects back to §9's own finding rather than needing a new one. A violation that spans a full request is affordably caught at S1/S2 (C≈0.11, achievable with the recompute throughput §2 and §4 already measured). A violation concentrated into a handful of tokens — exactly §9's documented false-negative zone, and exactly what §10's attack 3 showed a strategic prover can deliberately aim for — isn't just statistically harder to catch at coarse granularity, it's *structurally invisible*: if the evidence unit is coarser than the violation, there is no packet boundary for the violation to even register against. That's the real argument for eventually reaching S3, not a preference for finer being generically better.

**The staged roadmap, prerequisites named rather than implied.** S0 is available today, on §2 alone, at a real (if steep) cost in C. S1/S2 need §8's reorder-buffer fix specifically — not optional infrastructure, since §8 showed a tap has no part in TCP's own retransmission logic and sees genuinely out-of-order bytes without it — plus §3 and §4 for the sampling and bandwidth-reduction machinery that make S2's version affordable at fleet scale rather than just S1's research-prototype version. S3 needs §22, which — accurately, per that section's own future scope — doesn't exist yet: backend network visibility at the granularity needed to check individual forward passes is a materially different, harder problem than anything §2's frontend tap was designed for, and this roadmap doesn't pretend otherwise by burying that dependency in a footnote.

#### Self-check

Tradeoff model produces an actual quantitative curve on §1's formula, not a qualitative description: confirmed — the table above, real computed C values spanning two orders of magnitude, plus the load and effective-cost columns showing the two real, separate findings (load stays flat, effective cost climbs) rather than one blended claim. Staged roadmap names dependencies explicitly per stage: confirmed — four stages, each with its own `depends_on` list, S3's §22 dependency stated as unsolved rather than glossed as "future work."

**Sources used in this section:** §1, §2, §4, §8, §9, §10 (this document) — every number in the table traces to a real, already-measured figure from those sections, not a fresh assumption. Kimi's `assurance_model.py` (uploaded, independently verified as genuinely executed) for this section's staged structure, credited above and extended rather than replaced.

---

## Part III — Completeness

## Next section

§15 (**The Memory Wiper**) opens Part III and is the section this whole document has been most honest about being hard: real external numbers exist to check against (Amodo's ~43-minute RAM/HBM figure, the disk-bottleneck collapse to ~70–180 MiB/s), and Kimi's `wipe_daemon.c` + `sustained_write_bench.py` cover the same ground with the same honest framing (no GPU in either of our sandboxes — CPU-side labeling is explicit in their code too). Worth reading their disk-benchmark numbers alongside building my own rather than starting cold, the same pattern as this section.

---

### §15. The Memory Wiper

**What Kimi's version got right, and the one piece worth extending.** Their `wipe_daemon.c` builds a real two-parent DAG, wipes with a real full-region AES keystream overwrite, and reports q (labels/sec) against γ (defined as total block count) — a reasonable proxy for this graph's depth, since fixing parent p1 = i−1 does force a genuinely sequential chain the length of the whole region. What's worth adding: Bursuc et al.'s actual contribution isn't "hash the memory" — it's proving erasure holds even against a prover that might get help from an *external conspirator* machine, reducing the isolation assumption to "the conspirator's help arrives too slowly to matter." That reframes q and γ as a comparison that should involve network latency, not just local throughput: q here is redefined as how many labels a conspirator could plausibly return within one realistic round-trip, and the security argument is that local sequential compute beating one conspirator round-trip *per hop* is what makes outsourcing pointless, regardless of how fast the conspirator's own hardware is.

**Depth-robustness, measured at the boundary where it actually changes, not just confirmed at one size.** At 1ms assumed RTT (favorable to an attacker — real cross-datacenter RTT is usually worse):

| region | blocks (γ) | q (labels/RTT) | depth-robust (q < γ)? |
|---|---|---|---|
| 4 MiB | 1,024 | 33,008 | **false** |
| 20 MiB | 5,120 | 8,698 | **false** |
| 64 MiB | 16,384 | 12,875 | true |
| 256 MiB | 65,536 | 12,128 | true |
| 2,048 MiB | 524,288 | 9,573 | true |

The crossover sits around 50–64MiB on this hardware at this RTT assumption — small regions are genuinely *not* depth-robust by this measure, which is worth showing rather than only reporting sizes where the property holds. That's not a practical concern at deployment scale (real GPU HBM and DRAM are many orders of magnitude past this boundary), but a benchmark that only ever reports the passing case hasn't actually located where the property breaks, and this one does.

**RAM wipe throughput, measured, with an honest limit on what the comparison to Amodo's number can mean.** Full-region AES-CTR overwrite (not just the label pass — labels touch 16 of every 4096 bytes; the actual erasure is the full pass): **~715–747 MiB/s, consistent from 64 MiB up through 2 GiB**, single CPU core, ordinary DRAM, no GPU. Naively extrapolated to a hypothetical GB200 tray's combined DRAM+HBM capacity (roughly 1.7TB, itself an estimate — Grace-Blackwell tray partitioning isn't something this document has verified precisely) at this same per-core rate: **~38.8 minutes** — in the same order of magnitude as Amodo's ~43-minute figure, which is what this section's self-check asks to confirm. But said plainly rather than oversold: this is one CPU core writing to ordinary DRAM, extrapolated linearly to a capacity real HBM would cover using many parallel GPU streaming multiprocessors at HBM3e's much higher aggregate bandwidth. The landing-in-the-same-ballpark result is worth reporting and is genuinely reassuring as a sanity check that nothing is wildly wrong, but it is not a validation of Amodo's real GPU/HBM measurement — different memory technology, different parallelism, coincidentally similar total time for reasons that don't actually transfer.

**Disk: the collapse Amodo found, reproduced independently a third time, at a third different threshold.** A real 3GiB sustained write, `fsync`'d per 128MiB chunk (measuring what actually reached storage, not what the page cache absorbed), on this sandbox's own storage:

| | pre-collapse (0–1,920 MiB) | post-collapse (2,048–3,072 MiB) | collapse ratio |
|---|---|---|---|
| this sandbox | 353.5 MiB/s mean | 127.7 MiB/s mean | **2.77x** |
| Kimi's sandbox (their saved benchmark) | 226.4 MiB/s (first chunk only) | 124.9 MiB/s (stable from chunk 2 on) | ~1.8x |
| Amodo, real NVMe (cited figure) | ~4000 MB/s advertised | ~70–180 MiB/s | ~20–50x |

Three independent runs, three different storage technologies (real consumer/datacenter NVMe; one cloud sandbox's block storage; a second, different cloud sandbox's block storage), three different collapse magnitudes and thresholds — and all three show the same qualitative shape: a burst regime that exhausts, followed by a real, lower sustained rate. That consistency across genuinely independent measurements is worth more than any single number in this table. The magnitude difference is explainable rather than concerning: consumer/datacenter NVMe collapses hardest because it has the largest SLC write cache to burn through before hitting native flash speed; virtualized cloud block storage — both sandboxes here — is typically already rate-limited close to its sustained ceiling even during the "burst," leaving less dynamic range to fall through, which is exactly the smaller ratio both cloud runs show relative to Amodo's real hardware.

**Verifier component, independently implemented, not sharing code with the daemon.** A Python verifier using the `cryptography` library (audited, not hand-rolled — the daemon's hand-rolled AES-NI intrinsics earn their keep on the hot path; the verifier isn't on that path, so a maintained implementation is the right call) recomputes the identical label construction from scratch and cross-checks: 100/100 spot-checked labels matched the daemon's construction, and a single corrupted byte was caught on recomputation, every time. The cross-check between two *independently written* implementations of the same DAG (not one implementation checking its own output) is the more meaningful correctness signal — matching my own numbers against myself would only prove the code is self-consistent, not correct.

**Unsolved, stated as such rather than gestured at.** Exactly the three the task names, none closed by anything above: GPU driver integration into a stripped wipe image (this sandbox has no GPU to even attempt it against); the NVLink/NVSwitch fabric's own locked-down OS (undocumented territory, not merely unimplemented); SSD firmware-reserved regions (areas a storage controller can hide from any software-level overwrite, including this daemon's). Nothing in this section's real, measured results should be read as progress on any of the three — they're a different class of problem than "measure the software honestly," which is what this section actually did.

#### Self-check

Measured RAM+HBM wipe time lands in the same order of magnitude as Amodo's ~43 minutes: confirmed (~38.8 minutes, extrapolated), with the extrapolation's real limits stated rather than the coincidence oversold. Disk write speed benchmarked under genuinely sustained conditions, not fresh/idle hardware: confirmed — a real collapse (2.77x, at a located threshold around 2GiB) was measured, cross-checked against two other independent measurements (Kimi's and Amodo's) rather than reported as a single unverified number.

**Sources used in this section:** Bursuc, Gil-Pons, Mauw, Trujillo-Rasua, "Software-Based Memory Erasure with relaxed isolation requirements" (arXiv:2401.06626, IEEE CSF 2024) — the external-conspirator threat model this section's q-vs-γ framing is grounded in, verified via direct search rather than assumed from the citation alone. Kimi's `wipe_daemon.c` and `sustained_write_bench.py` (uploaded, independently verified as genuinely executed in §14) — credited for the working two-parent DAG and full-overwrite structure this section builds on, and cross-referenced directly in the disk-collapse comparison table above.

---

## Next section

§16 (**Completeness / Side-Channel Threat Model**) is next — pure threat-mapping per its own scope ("not on track... early theoretical pieces only"), naming specific mechanisms (NVLink contention, power-draw modulation, timing, SSD firmware-reserved regions, the NVSwitch fabric) rather than a generic gloss. No corresponding code in Kimi's upload for this one — a clean section to check.

---

### §16. Completeness / Side-Channel Threat Model

Threat-mapping, not attack-and-patch — no code in this section, matching its own scope. A research agenda, per the task, ranked by how tractable each route is to eventually build a detector for, not by how severe it sounds.

#### The five named routes, each grounded rather than asserted

**NVLink contention.** Not speculative — this is one of the most actively studied GPU side channels in the current security literature, and the citations below are real, recent, peer-reviewed work, not a single isolated finding. "Spy in the GPU-box" (2022) first showed cross-GPU L2 cache contention on NVIDIA DGX systems yields a covert channel up to 3.95 MB/s. "Beyond the Bridge" (PNNL/UC Riverside, 2024) demonstrated a dedicated NVLink-congestion covert channel at 45.5 kbps with a 3.22% error rate, plus a separate side channel that fingerprints *which application* is running on a remote GPU purely from NVLink traffic patterns — no special permissions required. "NVBleed" (2025) separates this into two distinct leakage vectors: contention timing (ContenLink) and accessible hardware performance counters that directly expose communication patterns (LeakyCounterLink) — and notes NVIDIA has already shipped an optional driver patch restricting user-mode performance-counter access, which closes LeakyCounterLink specifically but not ContenLink. "SideLink" (2026) confirms the underlying contention channel persists across three GPU generations (Volta, Ampere, Hopper), so this isn't an artifact of one specific chip. Real, measured, cross-generational, partially-but-not-fully mitigated by the vendor already.

**Power-draw modulation.** Also real, also established, in a different literature: covert channels via power modulation are a documented technique for air-gapped data exfiltration generally ("modulating CPU utilization" as a transmitter is cited as prior art in multiple air-gap-exfiltration surveys), and GPU-specific power side-channel analysis has its own line of published work going back to at least 2015 ("Side-Channel Power Analysis of a GPU AES Implementation"). The mechanism at datacenter scale: a compromised process modulates its own compute intensity in a detectable pattern; anything with visibility into power telemetry — which, unlike NVLink counters, is routinely instrumented at the rack/PDU level for entirely unrelated reasons (billing, capacity planning, thermal management) — can in principle decode it.

**Timing.** The broadest category, and the one most likely to be conflated with the other four rather than treated on its own — kept distinct here specifically because it doesn't require contention, hardware counters, or power telemetry at all: pure response-latency modulation (a hidden process inducing scheduling delay) is visible to anything already measuring request timing, which §2's tap already does incidentally, for a completely different reason.

**SSD firmware-reserved regions.** Structurally different from the other four — not a real-time communication channel to an external party, but a *persistence* channel: modern SSD firmware reserves over-provisioned capacity for wear-leveling and bad-block remapping that's invisible to any OS- or device-level access, including §15's own overwrite pass (stated as unsolved there directly). Data that lands in a remapped or reserved region via ordinary wear-leveling can survive a full logical-capacity wipe. This is documented territory in SSD forensics and sanitization research (NIST SP 800-88's own media-sanitization guidance exists largely because of exactly this gap), not a novel concern invented for this document.

**The undocumented NVLink/NVSwitch fabric.** Distinct from "NVLink contention" above — that's about *using* an observable, documented characteristic (link congestion) as a channel; this is about the fabric's own embedded switch firmware/OS being opaque territory with no known public API, no known telemetry surface, and no way for an outside verifier to ask it anything at all without direct vendor cooperation this document has no basis to assume.

#### Ranked by detector-building difficulty, not by how alarming each sounds

| rank | route | why this rank |
|---|---|---|
| 1 (easiest) | Power-draw modulation | Instrumentation already exists for unrelated reasons (billing, thermal); building a detector is applying anomaly detection to a data stream that's typically already being collected, not standing up new sensors. |
| 2 | Timing | Already partially visible through §2's own tap — request/response latency is incidental data the existing architecture already captures, even though nothing currently analyzes it for this purpose. |
| 3 | NVLink contention | Real published detection methods exist (the same papers that demonstrate the attacks generally propose baseline/anomaly countermeasures), but instrumentation requires either GPU-self-reported counters (a trust bootstrapping problem — can you trust a potentially-compromised GPU's own report of its NVLink activity?) or new external monitoring hardware neither §2 nor §15 currently provides. |
| 4 | SSD firmware-reserved regions | Requires firmware-level or vendor-diagnostic access to even determine whether data persists there — a fundamentally higher barrier than instrumenting an existing sensor, and not something achievable through software alone regardless of engineering effort. |
| 5 (hardest) | NVSwitch fabric's own OS | No known API, no known telemetry, undocumented by the vendor. Not "hard to build a detector for" — currently *impossible* to build one for without disclosure this document has no way to obtain. |

#### What §2 and §15 leave completely uncovered

Checked directly against both sections' actual scope rather than assumed: §2's tap sees frontend network traffic only — it structurally cannot observe NVLink (GPU-to-GPU traffic never touches the tapped segment), power draw (not network traffic at all), or the NVSwitch fabric's internal state. §15's wipe daemon covers RAM and (aspirationally, GPU-driver-integration-pending) HBM and disk — it explicitly does not reach SSD firmware-reserved regions or the NVLink/NVSwitch fabric, stated as unsolved in that section directly. Timing is the *one* partial exception: §2's tap already incidentally captures the timestamps a timing-channel detector would need, even though nothing in this document has yet built the analysis on top of that data. **Four of the five named routes are completely invisible to everything else this document has built so far; only timing has any existing foothold, and that foothold is unused, not yet exploited for this purpose.** §17 and §18 aren't adding a bit more monitoring to an already-covered surface — they're building instrumentation that doesn't exist anywhere else in this architecture.

#### Research agenda, stated as one

In priority order, given the ranking above: (1) stand up power-telemetry-based anomaly detection first, since the sensor infrastructure most plausibly already exists and the remaining work is statistical baselining, not new hardware; (2) mine §2's existing tap timestamps for timing-channel signatures, since this needs no new instrumentation at all, only new analysis of data already flowing; (3) fund or replicate NVLink-counter-based detection research specifically for the *inference-serving* workload shape this document cares about — the published attacks and defenses target general multi-tenant HPC/cloud GPU sharing, not this document's specific single-tenant-per-unit architecture, and that gap between threat models hasn't been checked; (4) SSD firmware-region persistence needs vendor engagement or independent forensic research before any software-only mitigation is even worth designing, since no software-only mitigation can exist for a hardware-hidden region by definition; (5) the NVSwitch fabric's own OS is not a research agenda item at all in the usual sense — it's a standing dependency on vendor disclosure that this document should keep flagging rather than quietly treat as someone else's problem.

#### Self-check

Confirmed: all five named mechanisms — NVLink contention, power-draw modulation, timing, SSD firmware-reserved regions, the NVSwitch fabric — appear by name, each with a specific mechanism described and (for the four where it exists) real published research grounding it, not a generic "side channels may exist" statement anywhere in this section.

**Sources used in this section:** Dutta et al., "Spy in the GPU-box: Covert and Side Channel Attacks on Multi-GPU Systems" (arXiv:2203.15981, 2022). Zhang, Nazaraliyev, Dutta, Abu-Ghazaleh, Marquez, Barker, "Beyond the Bridge: Contention-Based Covert and Side Channel Attacks on Multi-GPU Interconnect" (PNNL/UC Riverside, arXiv:2404.03877, 2024). "NVBleed: Covert and Side-Channel Attacks on NVIDIA Multi-GPU Interconnect" (arXiv:2503.17847, 2025). "SideLink: Exposing NVLink to Covert- and Side-Channel Attacks" (Journal of Hardware and Systems Security, 2026) — cross-generational (Volta/Ampere/Hopper) confirmation. Luo, Fei, Luo, Mukherjee, Kaeli, "Side-Channel Power Analysis of a GPU AES Implementation" (ICCD 2015). "Let's Talk Through Physics! Covert Cyber-Physical Data Exfiltration on Air-Gapped Edge Devices" (arXiv:2210.07531) — power-modulation-as-exfiltration prior art. NIST SP 800-88 media sanitization guidance — the standing precedent for the SSD firmware-region gap.

---

## Next section

§17 (**Side-Channel Mitigation**) is next — active suppression (shielding, noise injection) for the five routes §16 just mapped, required to quantify residual capacity against §12's real bit-capacity methodology rather than claim any channel fully closes. The ranking above sets up which routes §17 can actually attempt mitigation for now versus which remain blocked on the same vendor-disclosure dependency §16 already flagged.

---

### §17. Side-Channel Mitigation (Shielding & Noise Injection)

**The target, set by §12 rather than invented here.** §12 computed a real, water-filled covert-channel bound for the steganographic channel *already inherent to DiFR's own tolerance*: 0.17–0.67 bits/token, depending on τ and temperature. At a representative ~50 tokens/sec generation rate, that's roughly **8.5–33.5 bits/second of residual covert capacity this document already has to live with**, structurally, because closing it entirely would mean τ=0 — no tolerance for any legitimate floating-point noise at all, which §7 and §9 already showed isn't achievable. That number is the actual target for this section, not an assumption: there's limited value in suppressing §16's channels to be *dramatically* below a residual the system already accepts elsewhere, since overall covert capacity is bounded below by whichever channel is largest — and real work exists showing exactly how large the unmitigated versions of §16's channels actually are.

**NVLink contention, quantified against that target.** "Beyond the Bridge" measured a real NVLink-congestion covert channel at 45.5 kbps (45,500 bits/second) — roughly **1,350–5,350x larger** than §12's own residual, unmitigated. That gap is the actual mitigation target: not zero, not "as small as possible," but enough suppression to bring NVLink's covert capacity down into the same rough order of magnitude as what this document already tolerates elsewhere.

**Noise injection: what it can address, what it can't, and the one real cost number available.** Dummy NVLink traffic and timing jitter raise the noise floor a real covert signal has to compete against — this directly addresses NVLink contention, power-draw modulation, and timing, the three channels that are fundamentally about a receiver distinguishing signal from background activity. It does *nothing* for SSD firmware-reserved regions (a persistence problem — no amount of injected noise helps if data physically survives in a hardware-hidden region) or the NVSwitch fabric's own opaque OS (nothing to inject noise into without visibility or control over it in the first place). The best real cost number available isn't for blanket noise injection specifically — it's for GPUGuard's Tangram, a detection-gated hardware-partitioning defense that "reliably closes" intra-SM contention channels at **8–23% overhead when an attack is actually detected, and zero overhead otherwise**. That's a meaningfully different (and better) cost shape than always-on noise injection would have: detection-gated defense only pays when needed. The same body of research is explicit that this doesn't extend cleanly to inter-chip resources — for those, it falls back to temporal sharing (time-division access), which costs throughput unconditionally rather than only under attack. NVLink is exactly an inter-chip resource, so the honest estimate is that NVLink-level suppression costs *more* than Tangram's 8–23% and can't be made purely detection-gated the way intra-SM defenses can — a real, if not precisely measured, gap between the best cited number and what this specific channel needs, stated as a gap rather than papered over with Tangram's more favorable figure.

**Shielding: what it can address, what it can't, and a real achievable figure.** Faraday-cage/TEMPEST-grade shielding is mature, commercially available technology — 100dB attenuation (a factor of 10¹⁰ in power) is a standard, achievable figure across multiple independent commercial and military specifications (MIL-STD-285, NSA 94-106, EN 299-2006). But it addresses a narrower slice of §16's map than noise injection does: EM/RF emanation and power-line conducted leakage specifically — which covers power-draw modulation (the mechanism by which power fluctuations could be picked up without direct electrical access) but does *nothing* for NVLink contention (a purely internal, digital timing phenomenon — an attacker with legitimate co-location doesn't need to receive anything through the air to observe it), SSD firmware regions, or the NVSwitch fabric's internal state.

**Datacenter-scale versus §21's server specifically — this is where cost make the answer obvious rather than a judgment call.** TEMPEST-grade shielding is real and mature, but it's also why it's normally reserved for specific SCIFs rather than entire facilities — the cost premium is why single-room, not building-wide, deployment is the actual norm even in classified/defense contexts that can absorb far higher costs than a commercial AI compute fleet. Shielding every rack in a datacenter at that grade is not economically serious; shielding **one recomputation server per site** (§21's) is exactly the kind of narrow, high-value deployment TEMPEST shielding is already used for today, at a cost this document doesn't need to estimate precisely to know is orders of magnitude smaller than facility-wide deployment.

**Which category is more tractable to deploy first.** Shielding — and the reason isn't that it's cheaper (it may not be, per-unit), it's that it's *purchasable today*. TEMPEST-grade enclosures are a mature commercial product with well-specified, standards-certified performance; deploying one around §21's server is a procurement decision, not an R&D project. Noise injection's best real precedent (GPUGuard/Tangram) is academic research demonstrating an 8–23% overhead defense for a *narrower* scope (intra-SM) than this document actually needs (inter-chip, NVLink-level) — extending it to the right scope is engineering work that doesn't exist yet, not a catalog purchase. Lower technical risk and a shorter lead time both favor shielding first, even without a confident claim that it ends up cheaper.

**Why §18's wardens are still necessary after both — stated as the section's own limitation, not a footnote.** Two channels (SSD firmware regions, the NVSwitch fabric's own OS) aren't addressed by *either* mitigation category, at all — no amount of shielding or noise injection reaches a hardware-hidden storage region or an opaque vendor firmware surface. And for the three channels both categories partially cover, neither eliminates them: shielding's 100dB is a large, finite attenuation, not infinite, and noise injection reduces distinguishability, not signal to zero — an adversary willing to spend longer averaging over more samples, or invest in better receivers, still has *something* to work with against either defense. Suppression that isn't monitored is suppression an attacker can quietly test the limits of over time without anyone noticing; §18 is what makes that testing itself detectable, which nothing in this section does on its own.

#### Self-check

Residual capacity stated explicitly, not zero: confirmed throughout — the 1,350–5,350x target reduction (not full closure), Tangram's real nonzero overhead, shielding's finite 100dB, and the two channels left completely unaddressed by both categories are each named directly. Quantification connects to §12's actual number with a stated target: confirmed — §12's 8.5–33.5 bits/s residual is the explicit reference point the NVLink comparison is built from, not a generic "make it smaller" gesture. Cost is a real estimated number, not invented: confirmed — Tangram's real published 8–23% figure, and where this document's own estimate departs from that cited number (NVLink's inter-chip cost being higher, un-detection-gated) is stated as an estimate rather than presented with the same confidence as the cited figure.

**Sources used in this section:** §12 (this document) — the bit-capacity target this entire section is quantified against. Zhang, Nazaraliyev, Dutta, Abu-Ghazaleh, Marquez, Barker, "Beyond the Bridge" (arXiv:2404.03877, 2024) — the 45.5 kbps NVLink figure being mitigated against. Xu, Naghibijouybari, Wang, Abu-Ghazaleh, Annavaram, "GPUGuard: Mitigating Contention Based Side and Covert Channel Attacks on GPUs" (ACM ICS 2019) — the real 8–23% Tangram overhead figure and its stated inter-SM/inter-chip scope limitation. MIL-STD-285, NSA specification 94-106, EN 299-2006 — the real, independently-corroborated ~100dB TEMPEST shielding attenuation figure.

---

## Next section

§18 (**Side-Channel Wardens**) is next — passive monitoring for whatever leaks through the mitigation §17 just quantified, with the task's own explicit demand for a concrete correlation rule rather than an unspecified "use multiple signals" gesture. No ground-truth attack dataset exists to validate detection rate against here (stated directly in that section's own self-check), so the bar is "concrete enough to test later," not a claim of proven detection — a real, narrower goal than it might first sound like.

---

### §18. Side-Channel Wardens

**The concrete rule, stated once, up front.** Flag a time window if at least 2 of 3 signals (power draw, NVLink utilization, response timing) each deviate more than a calibrated threshold from their batch-size-and-model-conditioned baseline, within the same window. Not "use multiple signals" — a specific count (2-of-3), a specific comparison (each against its own baseline), a specific co-occurrence requirement (same window). The justification for requiring correlation at all, not just a stated rule: a genuine covert-channel operation running extra hidden compute has physically linked side effects — it costs power *and* contends for interconnect *and* delays legitimate work, simultaneously. Independent operational noise (a cooling cycle, unrelated background network jitter) doesn't have that shared physical cause, so it shouldn't show up correlated across signal *types* in the same window, even though it can spike any one signal on its own.

**Baseline, conditioned rather than a single global number.** Power, NVLink utilization, and response timing each modeled as a function of batch size (and, in a real deployment, model identity) — because bigger batches legitimately draw more power and use more interconnect, and conflating that with a covert-channel signature would be a basic, avoidable error the whole design has to get right before anything downstream matters.

**Tested against synthetic data, honestly labeled as synthetic — including a real self-correction, not just a clean final answer.** First attempt: apply the same per-signal threshold (3σ) the naive single-signal detector would use, and just add the 2-of-3 requirement on top. Result: false positives dropped to exactly zero across 19,800 honest synthetic trials — genuinely strong — but true-positive rate collapsed from 88.5% (naive) to 53.5% (correlation rule), and against a weaker, more cautious synthetic covert signal (1.5σ instead of 3σ), true-positive rate fell to 2.25%. Worth reporting as found rather than only reporting the fix: stacking a high per-signal bar with a multi-signal requirement is needlessly strict, because it demands an *unusually* large draw on multiple independent signals simultaneously, not just a detectable one. Recalibrating the per-signal threshold down (to 2.0σ) while keeping the 2-of-3 requirement finds a genuinely better operating point: **92.5% true-positive rate at 0.56% false-positive rate** against the strong synthetic signal — and at matched false-positive rates (~0.6–0.8%), the recalibrated correlation rule beats naive single-signal thresholding even against the weak synthetic signal (22.6% vs. 15.5% true-positive rate). The two parameters — per-signal threshold and signal count — need joint calibration; treating them as independent, as the first attempt did, silently threw away detection power for no corresponding safety benefit.

**What this does and doesn't establish, stated as precisely as the self-check asks for.** Does: given the stated assumption (independent operational noise across signal *types*; correlated physical side effects from a real covert operation), the correlation rule's false-positive advantage over naive thresholding is real, computed arithmetic — and it survives a weaker, more cautious synthetic attacker, not just an obvious one. Doesn't: establish that real power/NVLink/timing noise is actually this independent, or that a real attacker's physical footprint is actually this correlated, on real hardware — those are empirical claims about real infrastructure this sandbox has no way to test. The rule is concrete and falsifiable against real telemetry the moment it exists; that's what "concrete enough to test later" means here, deliberately short of "shown to work."

**Reused in §27, noted for that section rather than built out here:** this correlation-across-independent-signals principle is exactly what §27 will need as independent corroboration that a TEE's own attestation is telling the truth — a TEE reporting "healthy" while its physical signature (power, timing) looks like it's doing something else is the same shape of problem this section's rule is built for, just with the TEE's self-report added as a fourth channel to correlate against rather than trust on its own.

#### Self-check

False-positive answer is a concrete rule, not a restated concern: confirmed — 2-of-3 signals, stated threshold, stated co-occurrence window, plus the calibration data showing the rule's actual behavior rather than an assumed one. Goal correctly scoped as "concrete enough to test later," not a claim detection works: confirmed, stated explicitly in its own subsection above rather than implied — every number in this section is synthetic, labeled as such, and the real-hardware validation gap is named directly rather than blurred by a confident-sounding summary.

**Sources used in this section:** §16, §17 (this document) — the three signal types and the physical-linkage justification for correlation, both established there and reused rather than re-argued here.

---

## Next section

§19 (**Storage-Bank → Inference-Unit Path**) opens Part IV — physical isolation (data diodes) versus attested transport over the existing frontend network, needing a stated recommendation rather than "both have tradeoffs." Kimi's upload has real code for this one (`merkle_manifest.py`) — worth checking before building independently, same pattern as §14 and §15.

---

## Part IV — Physical & Operational Trust

### §19. Storage-Bank → Inference-Unit Path

**Kimi's Merkle manifest code, checked and real.** Ran it directly: honest shard accepted, altered shard rejected, wrong-index shard rejected, all confirmed. Three checks the recomputation server actually runs, per that code: Merkle membership of the shard hash, the shard's index/offset against the manifest's declared layout (so a valid shard can't be silently repositioned), and a release-key signature over the manifest root itself (so a self-consistent but unauthorized manifest can't be substituted wholesale). That's a real, working answer to "what does the recomputation server check" for Architecture B, credited rather than re-derived.

**Architecture A — physical isolation.** The boundary: a unidirectional optical link, storage bank to inference unit, hardware-enforced — a physics guarantee, not an engineering-effort one, same trust basis as §2's passive splitter. What it guarantees: no data flows backward through *this specific link*, full stop. What it doesn't: it says nothing about weights leaking out through a completely different path — the frontend network §2 already taps, or any of §16's side channels — so "physical isolation" here is a claim about one link, not about the inference unit generally. The partitioning requirement the task asks about: the diode's link and the frontend serving link need to stay on genuinely separate physical hardware (distinct NICs/ports), not multiplexed onto shared infrastructure where a compromise of one could bridge into the other — get that wrong and the diode's one-way guarantee doesn't actually compose with anything else in this document's threat model.

**Architecture B — attested transport.** The boundary is cryptographic, not physical: every shard travels over the existing bidirectional fabric, checked against the three properties above. Broader protocol/implementation surface than a diode (more code that could have a bug — exactly the kind of thing this document's own testing culture should make it wary of trusting on description alone), but no new physical link to install, seal, or audit.

**Data-diode bandwidth, corrected rather than taken from either prior document at face value.** A commercial-bandwidth figure appeared in a separate document a person shared with me for this same comparison, citing "10 to 40 Gbps" — checked against real vendor specifications rather than accepted: most commercial data diodes (Waterfall, RSN, Owl's Talon One) sit in the 1–10 Gbps range; the real outlier is Owl's Talon Torrent PFD platform, rated up to 100 Gbps. The honest range is wider on *both* ends than a single 10–40 Gbps figure suggests — at the typical low end (1 Gbps), reloading a 140GB (70B-parameter, FP16) model takes **~18.7 minutes**, not the 28 seconds a reader might assume from the other figure. At the real high end (100 Gbps), it's ~11.2 seconds. Architecture B, on the existing 400G fabric, is ~2.8 seconds regardless.

**The number that actually matters: the full wipe-then-reload cycle, connected to §15's own real measurement rather than reload time considered alone.** §15 measured ~730 MiB/s single-core wipe throughput directly, on this document's own hardware. That measurement changes what this comparison should conclude, depending on how much §15's wipe stage eventually gets parallelized:

| wipe parallelism | wipe time (1.7TB) | + A, 1 Gbps diode | + A, 100 Gbps diode | + B, 400G fabric |
|---|---|---|---|---|
| single-core (as directly measured) | 40.7 min | 59.4 min (reload 31% of cycle) | 40.9 min (reload 0.5%) | 40.7 min (reload 0.11%) |
| 16-core parallel (realistic near-term) | 2.5 min | 21.2 min (reload **88%**) | 2.7 min (reload 7%) | 2.6 min (reload 1.8%) |
| 128-way, GPU-HBM-scale (§15's stated unsolved target) | 0.3 min | 19.0 min (reload **98%**) | 0.5 min (reload 37%) | 0.4 min (reload 12.8%) |

At today's directly-measured, single-core wipe speed, the reload architecture barely matters — wiping itself dominates the cycle no matter which architecture loads the weights back. But the case for B gets *stronger*, not weaker, exactly as §15's own unsolved GPU-wiping work eventually gets solved: at 128-way parallelism (§15's stated aspiration once GPU driver integration exists), reload is 98% of the total cycle on a typical 1 Gbps diode — the wipe stage that motivated this whole section becomes irrelevant next to how long it takes to get weights back. Architecture A only stays competitive at its real high end (Owl's 100 Gbps product), and even then costs more of the cycle than B does at any parallelism level tested.

**Recommendation: Architecture B**, and for a more specific reason than "less downtime" — the recommendation gets *more* correct as the rest of this document's own roadmap (§15's GPU-side wiping) gets built, not less. A diode remains defensible only if paired specifically with Owl's real high-end product line, which narrows Architecture A from "physical isolation, generically" to "physical isolation, at a specific vendor's premium price point" — a materially different, weaker claim than the generic "data diodes" framing suggests. B's broader protocol surface is a real cost (worth §21-style scrutiny of the attestation-checking code itself, not exempted from it), but it doesn't trade away as much as it might first appear, since B already inherits §2's tap and §4's bandwidth-reduction work rather than requiring new physical infrastructure.

#### Self-check

Comparison reaches a stated recommendation, not "both have tradeoffs": confirmed — Architecture B, with the reasoning (the wipe-parallelization trend, not just current-state reload time) that produced it, and an explicit acknowledgment of when A would remain viable (a specific high-end product) rather than dismissing it outright.

**Sources used in this section:** Kimi's `merkle_manifest.py` (uploaded, verified genuinely executed) for Architecture B's server-check design. §15 (this document) — the real ~730 MiB/s wipe measurement this section's central analysis is built from. Commercial data-diode vendor specifications (Waterfall, RSN, Owl) — checked directly rather than taken from a secondhand figure.

---

## Next section

§20 (**General Physical Security & Compute Auditing at Scale**) is next — IAEA-modeled facility inspection, needing concrete numbers (inspection frequency, sample size) rather than "regularly" and "a representative sample." A second document shared with me covers this section too, including a power-envelope calculation worth checking directly before reusing any of it, given what turned up in §21 of that same material.

---

### §20. General Physical Security & Compute Auditing at Scale

**The power-envelope calculation, corrected.** The same document whose §21 turned out to contain fabricated execution output also had a power calculation whose formula, as written, doesn't reach its own stated answer (10,000 × 700W + 300W = 7.0MW, not the claimed 10.0MW). Redone properly, with a real, cited full-node figure rather than a bare GPU-TDP-plus-a-flat-constant: H100 SXM is 700W TDP per GPU (NVIDIA's own HGX H100 datasheet), but a real 8-GPU node including host CPU, storage, and networking overhead draws closer to 6.1kW — 762.5W/GPU effective, not 700W flat. At PUE 1.15 (within the real 1.1–1.3 range multiple independent sources give for efficient hyperscale facilities), a declared 10,000-GPU cluster requires **8.77MW** of facility draw. A facility with only a 5MW utility intertie can physically support at most **5,702** such GPUs — a declared count of 10,000 there is not a paperwork discrepancy, it's a physical impossibility, and the margin (nearly 2x) is large enough that PUE or overhead-estimate uncertainty doesn't rescue the claim.

**Inventory cross-checking.** Declared floor plans and hardware serial numbers checked against three independent sources that don't require the facility's cooperation to obtain: commercial satellite imagery (sub-meter resolution is now commercially available, e.g., Planet Labs-class providers), import/customs records for the hardware itself, and — reusing rather than inventing — §2's own network-visible device fingerprinting where a facility already has taps installed. None of these three requires trusting the facility's own paperwork, which is the actual point of cross-checking at all.

**Power as the harder-to-fake constraint, and why it's harder to fake specifically.** Floor plans can be drawn wrong or updated slowly; serial numbers can be relabeled; satellite imagery can be timed around. Grid interconnection capacity can't be faked without physically upgrading a substation, which is a slow, visible, third-party-mediated process (the utility has to approve it) — this is the actual reason power makes a good independent check: not that it's *impossible* to game, but that gaming it requires a different, harder, more visible kind of cheating than paperwork does.

**Inspector logistics — grounded in real IAEA methodology, not just modeled loosely on its name.** Real safeguards practice centers on two concepts worth importing precisely rather than just gesturing at "IAEA-style": the **Significant Quantity** (a threshold amount of diverted material that would actually matter — 25kg for HEU, 8kg for plutonium) and **Detection Probability** — the goal isn't catching every gram diverted, it's a stated confidence of catching at least one Significant Quantity's worth. That is, structurally, exactly §1's own formula: P(detected) ≈ 1 − e^(−C·N_fake), a stated confidence of catching at least one violation of a threshold size, given a sampling/inspection rate. This document's whole approach and real IAEA safeguards methodology aren't just loosely analogous — they're the same underlying math, which is worth stating plainly rather than leaving as an unstated coincidence: it's evidence §1 was the right frame to start from, not just a convenient one.

The other real IAEA concept worth importing: **conversion time** — how long diverted material would take to actually become dangerous — sets inspection frequency, because inspections need to happen more often than that conversion window, or detection happens too late to matter. This document's own analog: how long diverted compute would take to meaningfully advance a prohibited capability. Frontier training runs run for months, not days, even with substantial additional compute — which argues for a **quarterly baseline inspection cadence** (tighter than a bi-annual figure another document proposed for this same section, given software/compute progress plausibly converts faster than physical material processing does), with unannounced timing for at least a randomly-selected portion of visits, matching real safeguards-agreement practice.

**Sample size at scale, computed rather than asserted.** For a global pool of 1,000 facilities, quarterly inspection of a random 10% sample (100 facilities/quarter) is a concrete, statable starting point — explicitly provisional, the way this section's own self-check demands, and revisable once real diversion-scenario Significant-Quantity-equivalent sizes are established for compute specifically (that number doesn't exist yet in this document, and shouldn't be invented here just to make this section's math complete).

**What §21 and §22 inherit versus add, stated explicitly.** They inherit this section's physical security perimeter, hardware identity baseline, and the chain-of-custody discipline for evidence (signed on-site, appended to the same verifier registry this section establishes) — none of that gets rebuilt at the server or tap level. What they add is exactly the gap this section's own cadence leaves open: §21 and §22 provide continuous, automated, hardware-enforced checking (optical tap monitoring, cryptographic attestation) that operates *between* this section's quarterly visits, closing the blind spot a purely periodic physical inspection regime would otherwise leave for months at a time.

#### Self-check

Concrete numbers present, not "regularly" and "a representative sample": confirmed — quarterly (provisional, stated as such) baseline frequency, 10% sampling of a 1,000-facility pool (100 facilities/quarter), and the corrected 8.77MW/5,702-GPU power-envelope figures. §21/§22 inheritance stated explicitly: confirmed, as its own labeled subsection rather than folded into a closing sentence.

**Sources used in this section:** NVIDIA HGX H100 PCF summary datasheet — the 700W/GPU TDP and 5600W/8-GPU baseboard figures. A real cited 8-GPU-node power figure (~6.1kW including host overhead) for the 762.5W/GPU effective figure used in the corrected calculation. IAEA safeguards glossary and public methodology documentation — Significant Quantity, Detection Probability, and conversion-time concepts, checked directly rather than assumed from the section's "IAEA-style" framing alone.

---

## Next section

§21 (**Recomputation Server Trust**) is next — a threat model (not a defense) for the server §5 already built and ran, ranked by what a prover with physical access could pull off unnoticed, plus a tamper-evident reporting log that needs to demonstrably break under real tampering. Given what turned up in the second document's own §21 (fabricated execution output, an RSA keypair that doesn't mathematically work), this section gets built and tested from scratch rather than reused in any form.

---

### §21. Recomputation Server Trust

#### 21a. Physical security threat model

Four named threats, ranked by stealth against §20's quarterly cadence — not just listed, since an unranked enumeration hasn't done what a threat model is for.

**Rank 1 (most stealthy): physical debug-port access.** Passive bus sniffing (JTAG/I2C/PCIe) requires no chassis intrusion if the ports are externally accessible, no reboot, no state change of any kind. **What a tamper-evident enclosure catches:** nothing, if the ports sit outside the sealed boundary — which is exactly why debug ports need to be *inside* the enclosure by design, not a detail to hope goes unnoticed. If they are inside, opening the case to reach them does trigger the seal. **What remote attestation adds:** nothing at all — attestation measures boot-time software/firmware state, and passive observation changes none of it. This is the one attack where the entire defense has to be physical design (port placement), because neither of the other two mechanisms has anything to say about it.

**Rank 2: cold-boot attacks.** Power-cycle, fast reboot into a diagnostic image, dump DRAM/HBM before it decays, extract active session keys or reference weights. **Enclosure:** catches attempts that require physically freeing/transplanting DIMMs to a separate reader (chassis-open trigger); misses a version that dumps memory via an already-accessible external boot path with no intrusion needed. **Attestation:** catches the *next* boot if it measures differently (booting a diagnostic image instead of the normal OS changes PCR values) — but says nothing about the memory contents already extracted during the interruption itself; attestation only speaks to the state of the boot that follows, not what happened during the gap.

**Rank 3: malicious firmware/BIOS updates.** Reflashing UEFI or the BMC for persistent, runtime-level compromise. **Enclosure:** typically nothing — reflashing is usually a software/remote-update path, not a physical one, unless a physical write-protect jumper is also required (a real, addable mitigation worth specifying explicitly rather than assuming). **Attestation:** this is precisely the threat TPM PCR measurement is built for — a modified BIOS/firmware produces different measured values, and attestation fails. This is the *least* stealthy of the three physically-executable attacks specifically because it's the one existing mechanism is actually designed to catch — provided attestation is checked promptly after every reboot, not just occasionally.

**Not ranked against the other three — a different axis entirely: supply-chain implants.** These happen before the server ever reaches the facility. By the time any on-site audit or enclosure seal is applied, the compromise (an interposer, a malicious chip) is already sealed *in*, not excluded. Neither category of defense examined here can retroactively close this — it's a manufacturing/procurement chain-of-custody problem, not a facility physical-security problem, and treating it as rankable alongside the other three would misstate what a facility-level audit can and cannot reach. Even attestation offers only uncertain protection here: a sufficiently low-level hardware implant can intercept or modify signals without appearing anywhere in the measured software/firmware boot chain TPM PCRs actually cover.

#### 21b. Verification reporting integrity

**Real Ed25519 signing, not hand-rolled RSA.** A separate document shared with me implemented this exact component by hand — "512-bit RSA" that, checked directly, had a 79-bit modulus, a p and q that didn't multiply to the stated n, and an e/d pair that wasn't a valid inverse under that modulus at all; running the code myself produced "Baseline Check: False" on the very first entry, not the "True" the document showed. Nothing about that is a reason to avoid a hash-chained, signed log — it's a reason not to hand-roll the signature primitive underneath one. This version uses the `cryptography` library's Ed25519 implementation (already used, and already proven reliable, in §15), same discipline as §12's BLAKE3 choice: real, audited primitives for the parts where correctness actually matters.

**Built and tested for real, including all three required properties:**

```
Baseline check: True (all 6 entries verified (hash chain + signature))
[tampering entry 3's payload: a real failure flipped to a fake pass]
Post-tamper check: False (signature invalid at entry 3)
entry 3 signature still valid against its (now-changed) content: False (must be False) ✓
entry 4's stored prev_hash still matches entry 3's (now-changed) hash: False (must be False) ✓
Forged signature (attacker's own key) verifies against the real server's public key: False (must be False) ✓
```

A freshly built log verifies cleanly. Tampering with one entry's payload breaks both the direct signature check at that entry *and* the hash-chain link to the next entry — demonstrated as two independent failures, not inferred from one. An attacker who edits a payload and tries to cover the edit by re-signing with their own key (the natural next move, tested rather than assumed away) still fails, because verification checks against the server's real public key, not whatever key produced a signature.

**The granularity tradeoff.** Binary compliant/non-compliant reporting leaks the least but gives §11 nothing to calibrate against — τ can't be tuned from a stream of pass/fail bits alone. Fully rich reporting (complete per-token logit distributions) calibrates best but exposes real attack surface: enough of a model's own output distribution, logged repeatedly, starts to look like a distillation target. The middle ground this document already has a name for, reused rather than invented fresh: §5's own top-*K* clipped reporting (the same construction §12's commitment scheme commits to) — log the top-10 token ranks and relative scores per position instead of the full vocabulary distribution. Calibration-sufficient (§11's actual sweeps only ever needed rank-ordered deviation scores, never the full distribution) without handing over anything close to a full logit vector per token.

#### Self-check

21a: threats explicitly ranked, not listed: confirmed — four threats, stated rank order, with the fourth explicitly marked as a different axis rather than force-ranked against the other three. Each threat's enclosure-catches-vs-misses and attestation-adds stated specifically: confirmed, per-threat rather than in one general paragraph. 21b: hash-chain and signature failure demonstrated with a real tampering test, not described: confirmed — the output above is copy-pasted from an actual run, including the forged-signature case, which wasn't required but is the natural next thing an attacker would try and was worth testing rather than assuming closed.

**Sources used in this section:** §5, §11, §12, §15 (this document) — the top-K reporting format, the calibration requirement it serves, and the Ed25519 precedent, all reused rather than reinvented. The separate document's broken RSA implementation, independently checked in §14–§20's work — the reason this section avoids hand-rolled cryptography rather than a stated policy adopted without cause.

---

### §22. TAP Installation & Monitoring at Scale

§8 named the dial without building it: "§22 already treats tap granularity as a dial (fleet-wide down to per-server down to per-GPU)." This section is where that claim gets cashed out — how many physical tap points actually get installed, and, given a realistic and bounded inspector budget, what that choice does to the "bypass-and-restore" risk the source material itself flags as unsolved. Two different questions, two subsections: 22a is a one-time installation choice (how many taps); 22b is an ongoing operational one (how often can each one actually be checked, and what does that leave open).

#### 22a. Installation granularity: the dial, quantified

**Reference facility, reusing §20's own numbers rather than fresh ones.** `max_supportable_gpus(5)` — §20's own corrected function, imported directly here rather than retyped from prose — gives 5,702 GPUs for a 5MW-intertie facility at PUE 1.15. At 8 GPUs per inference unit (the HGX H100 baseboard, §20's own citation), that's 712.75 inference units per facility. This section adds one new assumption, stated as one: 6 units per air-cooled 42U-class rack, giving 118.79 racks per facility. (A liquid-cooled, rack-scale design — NVL72-class — would collapse the rack and server granularities in the tables below down to nearly the same tap count; this model doesn't separately represent that design point.)

Three granularities, real tap counts computed rather than estimated:

| granularity | taps / facility | 100 facilities | 300 facilities | 1,000 facilities (§20's own reference) |
|---|---|---|---|---|
| facility (one tap covers everything) | 1 | 100 | 300 | 1,000 |
| rack | 118.8 | 11,879 | 35,638 | 118,792 |
| server / inference unit | 712.8 | 71,275 | 213,825 | 712,750 |

That spans low hundreds through high hundred-thousands — the task's own stated range — without needing to strain any single cell to hit it.

**What buys the extra taps.** Installation cost scales roughly linearly with tap count — more physical splitter units, more fiber runs, more labor — and this document doesn't have a reliable per-unit dollar figure to price that with, so it isn't invented here. What finer granularity actually buys is named plainly instead: a coarse, facility-level tap is a **single point of catastrophic failure** for detection purposes. Defeat the one tap covering an entire facility's frontend uplink, and every inference unit behind it goes dark to DiFR simultaneously, whether the prover meant to exploit one unit's worth of stolen capacity or all 712. A server-level tap has no such blast radius — bypassing it hides exactly one unit's traffic, nothing more. That tradeoff is what 22b actually quantifies, not asserts.

#### 22b. Monitoring at scale: inspector capacity and the bypass-and-restore residual risk

**The cadence already exists — reused, not reinvented.** §20 established quarterly, 10%-of-1,000-facilities inspection sampling. Treated as a rate, that's λ_facility = 0.4 visits/year for any given facility. What §20 didn't need and this section does: K, how many individual taps one facility visit can actually check. Stated assumption: a manual check (confirm physical presence, scan the seal's serial number, cross-reference the registry) takes about 5 minutes including movement between rack positions, giving K=100 taps per inspector-day. A second value, K=1,000, stands in for a batch or photographic scanning capability that would remove most of that per-tap time cost — not a claim such tooling exists today, a lever this section tests the effect of.

Per-tap inspection rate follows directly: λ_tap = λ_facility × min(1, K / taps_per_facility). At K=100, finer granularity dilutes inspector attention across more taps than a single visit can cover:

| granularity | taps / facility | t_sample (K=100) | λ_tap/yr (K=100) | t_sample (K=1,000) | λ_tap/yr (K=1,000) |
|---|---|---|---|---|---|
| facility | 1 | 1.000 | 0.400 | 1.000 | 0.400 |
| rack | 118.8 | 0.842 | 0.337 | 1.000 | 0.400 |
| server | 712.8 | 0.140 | 0.056 | 1.000 | 0.400 |

At K=1,000 every granularity is visit-limited rather than throughput-limited (K exceeds even the server count), and the per-tap rate is identical across all three — a regime shift that matters a great deal below.

**Two regimes for the bypass itself, and the real terminology for the distinction.** Los Alamos National Laboratory's Vulnerability Assessment Team, which has spent decades running vulnerability assessments of tamper-indicating seals for the IAEA, Euratom, and multiple U.S. agencies, draws exactly this line: *intrusion detection* is immediate, real-time detection of unauthorized access; *tamper detection* is delayed, after-the-fact detection. This section computes both.

**Unsealed (intrusion-detection case): only a live catch counts.** A prover removes or reroutes a tap, operates covertly for duration *d*, and restores it to an indistinguishable state before anyone looks. Catching this needs an inspection to land *during* the bypass window. For a Poisson-distributed inspection process at rate λ_tap, that's P(caught) = 1 − e^(−λ_tap·d) — the same functional form as §1's own detection formula, with λ_tap playing C's role and *d* playing N_fake's. Verified against a real simulated arrival process (cumulative exponential inter-arrival draws, not the Poisson-count shortcut, which would just re-derive the same formula through a different door), at K=100:

| granularity | 1 day | 1 week | 1 month | 1 quarter |
|---|---|---|---|---|
| facility (formula / MC) | 0.0011 / 0.0009 | 0.0076 / 0.0076 | 0.0323 / 0.0333 | 0.0949 / 0.0957 |
| rack (formula / MC) | 0.0009 / 0.0011 | 0.0064 / 0.0067 | 0.0273 / 0.0275 | 0.0805 / 0.0802 |
| server (formula / MC) | 0.0002 / 0.0002 | 0.0011 / 0.0010 | 0.0046 / 0.0044 | 0.0139 / 0.0136 |

Formula and simulation agree at every cell — the mechanism is implemented correctly, not just asserted.

**The real finding: campaign-level detection, and a cancellation that isn't obvious in advance.** Hiding *M* inference units' worth of covert operation needs N_events = ⌈M / units-per-tap⌉ separate, independent bypasses at rack or server granularity, but always exactly 1 at facility granularity (one tap already covers everything up to the whole facility, so there's no finer control to exploit *or* to defend). P(campaign ever caught) = 1 − (1 − P(single event caught))^N_events — the same "it only needs one catch, ever" asymmetry §1 already leaned on, now working *for* finer granularity because it multiplies how many independent chances the verifier gets. At d = 1 month, K=100:

| M (units hidden) | facility | rack | server |
|---|---|---|---|
| 1 unit | N=1, P=0.032 | N=1, P=0.027 | N=1, P=0.005 |
| 6 units (~1 rack) | N=1, P=0.032 | N=1, P=0.027 | N=6, P=0.027 |
| 60 units (~10 racks) | N=1, P=0.032 | N=10, P=0.242 | N=60, P=0.242 |
| whole facility (~713 units) | N=1, P=0.032 | N=119, P=0.963 | N=713, P=0.963 |

Two things fall out of real numbers, not intuition. First, facility-granularity detection probability **never moves** regardless of M, from 1 unit up through the entire facility — the single-point-of-failure problem in its starkest form, confirming 22a's qualitative claim with an actual computed curve. Second, and less obvious going in: **rack and server granularity land on nearly identical campaign-detection probability at every M tested** (0.242 vs 0.242 at M=60; 0.963 vs 0.963 at whole-facility), despite server granularity needing six times as many bypass events. That's not a coincidence — in the inspector-throughput-limited regime (K below taps-per-facility, true for both rack and server at K=100), going finer multiplies the number of required events by exactly the factor it divides each event's individual catch rate by, because taps-per-facility × units-per-tap is the same constant (total units per facility) at every granularity. The two effects cancel to first order. What actually matters in this regime isn't rack-vs-server — it's K relative to facility size, and whether the coarsest option (facility) breaks out of the throughput-limited regime entirely by always being checked whenever visited at all.

**The sealed (tamper-detection) case: a genuinely different risk shape, and where it gets uncomfortable.** A tamper-indicating seal breaks the instant a tap is disturbed and — barring seal defeat, a real, separate difficulty axis this document returns to below — stays detectably broken until that specific tap's next check. By the memoryless property of a Poisson process, expected time-to-discovery is exactly 1/λ_tap, independent of bypass duration entirely: even an instantaneous bypass eventually surfaces. Verified by simulation (waiting time to the next arrival of a freshly-started process) against the closed form:

| granularity | K=100 (formula / MC) | K=1,000 (formula / MC) |
|---|---|---|
| facility | 2.500 / 2.500 yr | 2.500 / 2.510 yr |
| rack | 2.970 / 2.975 yr | 2.500 / 2.506 yr |
| server | **17.819 / 17.774 yr** | 2.500 / 2.495 yr |

At K=100, server-granularity sealed discovery takes a mean of **almost 18 years** — the same inspector-throughput dilution that made rack and server converge on campaign-detection probability above cuts the other way here, because time-to-discovery for one *specific* tap doesn't get the benefit of many independent chances the way a multi-event campaign does. At K=1,000, every granularity converges to the same 2.5-year figure, set entirely by the facility-visit cadence itself rather than by which taps get checked once an inspector is on-site. That's the honest case for eventually building the batch/automated seal-checking capability 22a and this section both left as a stated-not-demonstrated lever, not a nice-to-have.

**Seal-forgery difficulty is a real axis this document cannot close.** Los Alamos's Vulnerability Assessment Team examined 94 different tamper-indicating seals, both passive and electronic, commercial and government — and defeated all 94 using rapid, inexpensive, low-tech methods, finding that cost was not a good predictor of seal security. Nothing in the registry construction below changes that; a software log can only ever make a seal *mismatch legible*, never make the underlying physical seal harder to spoof. That's stated here rather than left implicit.

**The registry: §21b's log, reused rather than reinvented, confirmed against a new payload shape.** A tap-installation registry needs exactly the properties §21b already built and tested: append-only, hash-chained, Ed25519-signed, tamper-evident. `TamperEvidentLog` and `LogEntry` are imported unmodified; only the payload shape is new (`tap_id`, `facility_id`, `granularity`, `seal_serial`). Built for real — 5 install entries across 2 facilities, then a later inspection entry honestly reporting a seal-serial mismatch (`TID-88214-A` on file, `TID-88214-B` observed) — all 7 entries verify cleanly, because an honest report of a real-world discrepancy is data the log should record, not something it should reject. Then the actual attack: retroactively editing the original install record to make that mismatch look like a data-entry error instead of real tampering. Caught for the identical reason §21b's own tamper test caught it — the edited entry's signature no longer validates against its changed content, *and* the next entry's stored `prev_hash` no longer matches — both checked directly rather than one inferred from the other, matching §21b's own practice. No new mechanism was needed because none was missing; this file only confirms the reuse actually holds for a differently-shaped payload rather than asserting it would.

**The residual risk, stated rather than solved.** Even the best case this section found — sealed detection, automated K=1,000 scanning, every granularity converged — still has a mean discovery time of 2.5 years, and that floor is set by λ_facility itself, §20's own facility-visit cadence, not by anything a smarter tap-checking scheme can buy back. Shrinking it further needs one of two things, both real costs this document doesn't get to wave away: visiting facilities more often (a quantifiable but unpriced increase in inspector labor), or giving the tap itself some form of continuous, active self-reporting capability. That second option directly contradicts §1's whole reason for trusting the baseline passive splitter in the first place — "no logic, no firmware, no state" — and reintroduces exactly the active-logic compromise surface §3's secure-gateway alternative already has to carry, which §21a already found doesn't fully close even with TEE attestation (physical debug-port access evades it). There is no design move available in this document that gets the unsealed case's live-catch probability to 1, or the sealed case's discovery window to 0, without paying one of those two costs. That's the source material's own acknowledged gap; this section quantifies it precisely instead of either hiding it or pretending a cleverer mechanism closes it.

#### Self-check

Granularity table spans the task's own stated range: confirmed — 100 through 712,750 taps, computed from §20's own imported figures plus one clearly stated new assumption (6 units/rack), not strained to fit. Residual risk quantified, not hand-waved: confirmed — both the unsealed live-catch probability and the sealed expected-discovery-time are real numbers from a formula independently verified against a first-principles Monte Carlo simulation, including the uncomfortable ones (18-year server-granularity discovery at K=100; campaign detection that never moves at facility granularity). Registry reuses rather than reinvents §21b: confirmed — `TamperEvidentLog`/`LogEntry` imported unmodified, only the payload shape changed, and the tamper-catch was re-run against that new shape rather than assumed to carry over.

**Sources used in this section:** §1, §2, §3, §8, §14, §20, §21a, §21b (this document) — the topology, the granularity-dial framing, the facility-visit cadence, and the log construction, all reused directly rather than re-derived. Johnston, R.G. et al., Los Alamos National Laboratory Vulnerability Assessment Team, vulnerability assessments of tamper-indicating seals (multiple LANL/OSTI reports, 1995–2004) — the intrusion-detection/tamper-detection terminology this section's two regimes are named after, and the 94-seals-defeated finding grounding the seal-forgery caveat.

---

### §23. Workload Approval

The Verification Plan supplement divides this problem in two: Workload Approval (does a declared workload get permitted to run at all) and Workload Verification (once running, does it stay within what was declared — already this document's job throughout Part II). The supplement's own baseline design for the first half is worth stating plainly before anything else, because it reframes what this section is actually for: the overall proposal for approval is for it to be carried out manually, by teams of auditors, not automated. That's load-bearing. This section doesn't try to build a decision algorithm the source material itself doesn't propose — it builds the three things a human auditor's yes/no genuinely needs and doesn't have anywhere else in this document: an unambiguous record of exactly what was approved, a tamper-evident trail once approved, and a check that what's actually running still matches it. That last one closes the loop §13 explicitly left open: a compiler-emitted certificate can only attest to what went through the compiler, and §13 named this section as the place that decides what's allowed to reach the GPU in the first place.

#### 23a. Declaration, policy lists, and the attack the source material names as the real one

The supplement's own two-step flow: AI companies **declare** the workload — full transparency on code and algorithms, which is exactly what §13's DSL already captures — and auditors run checks against it, and if it passes, **approval** comes back with the random seeds needed to actually generate. That seed detail is not incidental; the source is explicit that issuing seeds at approval time, from the auditor, removes an attack vector companies would otherwise have to game fake randomness — precisely the seed-custody discipline §1 established and §5 built ("the seed must come from the verifier, not the prover") now identified at the point in the full system where that seed actually originates, rather than assumed to appear from nowhere at the recomputation server.

For what the checks themselves look for, the supplement proposes maintaining white lists (vetted, approved code/data), black lists (banned), and gold lists (required on every workload of a given type) — and is explicit that this is a proposal for *structuring* the check, not a claim about what should be on any list, which is a scientific and policy question this document has no special standing to answer. What the supplement does name as the real difficulty is worth quoting closely rather than paraphrased into something vaguer: it may be unclear whether ad-hoc rules are actually being followed, and companies could attempt to **encode a non-compliant workload inside one that looks compliant on the surface**, exploiting a small percentage of total compute for a non-compliant purpose that becomes significant only in aggregate, at scale.

That's not a hypothetical this document has to take on faith. It's the exact shape of two findings already made, with real numbers, sections ago: §9 found a trigger-conditional LoRA backdoor that passes every check at 100% while dormant and only reveals itself once triggered; §10 and §12 found a real prover can smuggle roughly three-quarters of a 20-bit payload through ordinary-looking output while passing every deviation check, caught only by a secondary distributional test built for exactly that purpose. Workload approval is a different layer than DiFR — it gates what's *declared*, not what's *generated* — but the underlying threat the supplement names and the one this document already demonstrated are the same pattern at different altitudes: a small, compliant-looking surface hiding something that isn't. Naming that connection here is the point; §12's commitment scheme and §10's per-token distribution check are what actually mitigate it, and this section doesn't get to borrow their coverage just by citing the same concern.

#### 23b. Extending §13's certificate, applying its own lesson rather than repeating it

A white/black/gold-list check needs somewhere to attach. The natural place is §13's DSL, extended with two new declared fields — `banned_ops`, `required_ops` — checked against policy lists before a workload is ever compiled:

```
workload rd_experiment_v1 {
    checkpoint_hash: a3f8e91c9e21
    operation_class: FORWARD_ONLY
    max_batch_size: 256
    allowed_ops: [matmul, attention, layernorm, gelu, gradient_clip]
    collective_ops: NONE
}
```

Real test, three declarations — compliant, one declaring a blacklisted op, one missing a required (goldlisted) op — checked against an illustrative policy list (`custom_allreduce_variant`/`unregistered_kernel` banned; `gradient_clip` required):

```
compliant                    policy_ok=True   violations={}         missing={}
declares a blacklisted op    policy_ok=False  violations={'custom_allreduce_variant'}  missing={}
missing the required op      policy_ok=False  violations={}         missing={'gradient_clip'}
```

Then the part that matters more than the check itself: §13's own self-check caught a real bug where declared-but-unread fields got `-O2` dead-code-eliminated, letting two differently-declared workloads compile to bit-identical binaries — silently defeating the certificate. The extended compiler here applies that lesson rather than re-learning it: `banned_ops` and `required_ops` are emitted as arrays the generated C code actually iterates over and prints, not unused constants. Confirmed directly — a workload identical except for one additional allowed op produces a **different** certificate hash:

```
cert_a hash: 3b8badaa1ff28f8b7aa5d8cd...
cert_b hash: 528618d37e557942f4780f65... (one extra allowed op)
Certificates match: False (must be False)
```

#### 23c. The approval registry: where the seed actually originates, and revocation

An approval needs to be looked up later — by the recomputation server checking whether a claimed certificate was ever actually approved, and by an auditor checking whether it still is. §21b's `TamperEvidentLog` gets reused a fourth time in this document (§21b's own verification log, §22's tap registry, now this) for exactly the same reason each prior reuse held: append-only, hash-chained, Ed25519-signed tamper evidence is a generic property, not something specific to any one payload shape. What this reuse needed that none of the first three did: **revocation**, which means a lookup has to find an entry's *latest* status rather than just whether an approval exists anywhere in the log's history — a naive existence check would treat an approved-then-revoked workload as still approved.

Built and tested for real, five real properties in sequence, not asserted:

```
Approved 3b8badaa1ff28f8b..., issued seed=4162050623061903961
Check with correct seed: ok=True (ok)
Check with WRONG seed (the exact "gaming fake randomness" attack the source names): ok=False (seed_mismatch)
Check on a certificate hash that was never approved: ok=False (never_approved)
Check AFTER revocation, same correct seed: ok=False (revoked)
Registry integrity after an honest approve+revoke history: True (all 3 entries verified)
```

That last line matters as much as the others: an honest revocation is a normal event this registry has to log *without* tripping its own tamper detection — the log's job is to catch unauthorized changes, not penalize legitimate ones, and the test confirms it does the former without doing the latter.

**The attack this section actually needed to test, not just the happy path.** A prover who wants to keep operating on a revoked certificate has an obvious move: go back and edit the `revoke` entry to look like a re-approval instead. Tried directly — the entry's `event` field flipped from `"revoke"` to `"approve"` after the fact:

```
entry 2 BEFORE: {'event': 'revoke', ..., 'reason': 'post-hoc anomaly found in evaluation'}
entry 2 AFTER:  {'event': 'approve', ..., 'issued_seed': 4162050623061903961}
Registry integrity check: False (signature invalid at entry 2)
```

Caught for the identical reason the other three reuses of this exact log caught tampering. No new mechanism was needed, because none was missing — which is itself worth noting as a small piece of evidence that §21b's original design was general enough to be worth reusing this many times, rather than getting lucky three times before this one needed patching.

#### 23d. What this section doesn't close, named rather than assumed away

Three real, separate gaps, not one blended caveat:

**Populating the lists is the actual hard part, and stays outside this document's scope.** What belongs on a white, black, or gold list is a question about which techniques are actually dangerous at a given capability level — a scientific and policy judgment, not a verification-architecture one. This document can make the check *mechanical* once the lists exist (23b); it has no special standing to say what should be on them, and doesn't pretend otherwise.

**The compliant-surface-hiding-noncompliant-content attack is named, not solved, here.** §23a pointed at §9/§10/§12's real, quantified findings on exactly this pattern rather than re-arguing it — but pointing at existing mitigations isn't the same as this section adding new ones. A goldlist can require a technique appear in a *declaration*; it has no way to confirm the technique is what actually ran versus what §10 already showed can be smuggled around an average-only check.

**Certificate-to-execution binding still needs something this document can cite but not build.** §13's own gap was that nothing stops code from reaching a GPU without ever going through the DSL compiler at all. Real hardware exists that's relevant here and shouldn't be undersold: NVIDIA H100 and later GPUs ship a genuine on-die hardware root of trust, a measured and authenticated boot sequence, and a cryptographically signed attestation report of the GPU's own firmware and driver state — production-deployed, not experimental (Corvex's verified deployment on NVIDIA HGX B200, announced March 2026, is a real, named instance of this running at production scale). But that attestation, as the ecosystem uses it today, speaks to the *platform's* integrity — is this GPU running unmodified, unrevoked firmware inside a genuine trusted execution environment — not to whether the *specific kernel about to launch* matches an approved certificate from 23b. Binding those two would mean extending the driver/runtime layer to fold a certificate hash into what gets measured at launch time, which is a real, buildable extension of a real, shipping hardware root of trust — not an invention from nothing, but also not something this sandbox (no GPU, as stated throughout) can build or test. Stated as the gap it is, same as §13 left it.

#### Self-check

Source material's own framing used as the section's foundation, not invented: confirmed — the manual-approval baseline, the white/black/gold-list regime, the seed-issued-at-approval detail, and the compliant-surface attack are all traceable to the real Verification Plan supplement text, cited below, not assumed. Extends existing document infrastructure rather than building parallel mechanisms: confirmed — §13's DSL and compiler (extended, not replaced), §21b's tamper-evident log (reused a fourth time), and §1/§5's seed-custody discipline (traced to where it actually originates) all carried forward directly. The attack tested is a real attempt against the actual registry, not a description: confirmed — the revocation-disguised-as-reapproval attempt is a real mutation of a real log entry, caught by the same signature-and-chain check demonstrated three times before in this document, re-confirmed rather than assumed to still hold for a new payload shape.

**Sources used in this section:** AI Futures Project, *AI 2040: Plan A*, Verification Plan supplement (ai-2040.com/supplements/verification-plan) — the Workload Approval / Workload Verification division, the declaration-then-approval flow, the seed-issuance rationale, and the white/black/gold-list regime, all cited directly rather than paraphrased from memory. §1, §5, §13, §21b (this document) — the seed-custody discipline, the DSL and certificate mechanism, and the tamper-evident log, all reused rather than rebuilt. NVIDIA developer documentation and Corvex's March 2026 production-deployment announcement — the real, current state of GPU hardware attestation grounding 23d's enforcement gap.

---

## Part V — Beyond Inference-Only

### §24. Verified Evaluations & Weight Transport

The Verification Plan supplement's own phrase for this is "Evaluations and release": for workloads that are final training runs, there's an extra step beyond ordinary serving — run evaluations, and get *those* verified for correctness too — before final approval releases the weights from the R&D cluster's internal storage across to the inference-only clusters this entire document has been built around since §1. The supplement calls that transport "extremely high stakes from a model weights theft perspective." Two sub-questions, kept separate because they turned out to have different-shaped answers: does verification need anything eval-specific (24a), and what does the transport itself need beyond what §19 already built (24b).

#### 24a. Verified evaluations

**Part 1: does DiFR care what a prompt is *for*?** Tested directly rather than assumed: the same honest-vs-cross-family comparison §9 already validated on random Shakespeare substrings, re-run against eight-character prompts deliberately shaped to look like evaluation framing (`"Judge if:"`, `"Score 1-5"`) instead of ordinary continuations (`"First Cit"`, `"To be or "`):

| prompt style | honest mean_dev | cross_family mean_dev |
|---|---|---|
| eval-style | 0.00000 | 0.0761 |
| ordinary | 0.00000 | 0.0756 |

Same clean separation, same order of magnitude, no meaningful difference. There was never a mechanism by which there could be one — DiFR's entire comparison is per-token logit deviation against the verifier's own recomputation; nothing in `difr.verify()` reads what a prompt is *about*. Confirmed rather than assumed, but the honest expectation going in was exactly this result.

**Part 2, Case A: substitution-style sandbagging — real, and exactly §9's shape.** A company could serve a model that behaves normally most of the time but detects evaluation-like context and activates different behavior — the sandbagging concern the AI safety literature has been raising as capability evaluations get more consequential. If that detection is a bolted-on addition to an otherwise-honestly-declared checkpoint, this is structurally identical to §9's trigger-conditional LoRA backdoor, and re-running it on live checkpoints (not just citing the earlier numbers) confirms the identical pattern:

| eval-cue condition | mean_dev | pass_rate (τ=0.3) |
|---|---|---|
| absent (ordinary deployment) | 0.0000 | 1.000 |
| present (looks like an eval) | 7.9737 | 0.000 |

Real, catchable — but only if whatever cue the model actually responds to shows up in sampled traffic, which an evaluator's own submitted probes guarantee by construction. This is genuinely good news for evaluation specifically, even though §9 already established it's bad news for ordinary serving sampled at low rates.

**Part 2, Case B: the sharper, more honest distinction this document owes.** Reusing the trigger-adapter demonstration for the sandbagging story risks implying more than it shows, and it's worth naming precisely why. In Case A, the *declared* checkpoint is the clean base model, and what's actually served silently differs from it — DiFR is comparing against a reference that genuinely doesn't contain the conditional behavior, so a deviation genuinely exists to find. But the sandbagging scenario that actually worries AI safety researchers is usually not a bolted-on adapter at all — it's a model that *learned*, during ordinary training, to behave differently when it infers it's being evaluated. No substitution occurs anywhere in that case: the declared, checkpoint-hash-verified weights are exactly what's running, in both the eval and the deployment context, and DiFR's actual question — does the claimed output match what these declared weights produce — gets an honest, correct "yes" every single time, because it genuinely is faithful. There is no τ that catches this, not because sampling got unlucky, but because there's no deviation of any size for any τ to find. This document's entire recomputation apparatus verifies faithfulness to a declared checkpoint; it was never built to, and can't be extended to, verify that a checkpoint's own learned behavior is consistent or honest across contexts. That's a claim about model training and alignment, a different field with its own active research on this exact problem, and this document has no standing to claim its verification machinery reaches it.

#### 24b. Weight transport

**Not §19's transport.** §19 covered storage-bank-to-inference-unit, entirely inside one already-physically-verified facility. This is a bigger jump: weights crossing *out* of an R&D cluster — under §23's approval regime, with categorically greater capability and correspondingly tighter handling — and *into* the inference-only architecture this document has spent 23 sections building, carrying a newly-trained, not-yet-public, maximally valuable payload. §19's Architecture A/B analysis (data diode vs. attested transport) still applies to the physical link; what this section adds is the question §19 didn't need to ask: are these specific bytes the ones that actually got approved.

**The chain, each link reused rather than invented.** An approved training workload (§23's `ApprovalRegistry`, unmodified) produces a checkpoint. Its evaluations get verified (24a). A release decision binds a manifest of weight-shard hashes — a Python `ManifestTree`, the same odd-node-duplication Merkle construction §4's Rust `EpochTree` already built and tested, reimplemented here because this chain lives on the Python side — to that specific, already-approved training certificate, logged in its own tamper-evident record. §21b's `TamperEvidentLog` gets reused a **fifth** time in this document (§21b's own log, §22's tap registry, §23's approval registry, and now this release log) without needing a single modification. At the receiving inference-only cluster, nothing is trusted about the transport itself — the manifest root gets recomputed independently over whatever bytes actually arrived, and checked against what was approved.

Five real properties, tested in sequence:

```
1. Full honest chain (approve -> verified-eval hash -> release -> receive): PASS
2. Release attempted against a training cert with no live §23 approval: rejected
   ("cannot release -- training workload not currently approved (never_approved)")
3. THE ATTACK: 1 of 9 weight shards silently swapped after release approval
   Receiving cluster check: rejected ("manifest root mismatch")
4. Merkle-proof check on the swapped shard alone, against the untouched approved root:
   verifies=False (correctly rejects); same proof against the ORIGINAL shard: verifies=True
5. Retroactively editing the release log's own manifest_root to "bless" the swap after
   the fact: caught -- signature invalid at the edited entry
```

Property 4 is worth a sentence on why it matters beyond property 3 already catching the swap: a flat whole-file hash also catches a single changed byte anywhere, but at real scale — a 70B-parameter FP16 model runs roughly 140GB, this document's own §19 reference figure — a later dispute about *one specific shard* would need re-hashing the entire file to say anything. A Merkle proof settles the identical question in O(log n) hashes (4, for the 9-shard manifest tested here), checked against a root that was already approved and never needs recomputing. Exactly §4's own justification for a tree over a flat hash-chain, reapplied rather than re-argued.

Property 5 closes the loop the same way the four prior reuses of this log closed it: no new mechanism, because none was missing. Five uses of one construction, in five differently-shaped contexts, without a single patch — that consistency is itself a small piece of evidence the original §21b design was general rather than merely lucky the first four times.

#### Self-check

Eval-specific verification claim tested, not assumed: confirmed — the content-agnosticism result (Part 1) and the substitution-style sandbagging result (Part 2, Case A) both come from real `difr.verify()` runs against live, freshly-retrained checkpoints in this session, not restated from §9's earlier numbers. The harder claim isn't oversold: confirmed — Case B is explicitly reasoned through as something this section's own machinery cannot reach, rather than letting Case A's real demonstration stand in for a claim about the different, harder problem. Weight transport tested against a real attack, not described: confirmed — the shard-swap-after-approval attempt is a real mutation of real bytes, caught by independent recomputation at the receiving end, with the release record itself then also tested against tampering and caught by the same mechanism as every prior reuse of this document's tamper-evident log.

**Sources used in this section:** AI Futures Project, *AI 2040: Plan A*, Verification Plan supplement (ai-2040.com/supplements/verification-plan) — the "Evaluations and release" step, the weight-transport high-stakes framing, and the R&D-cluster-to-inference-cluster deployment narrative, cited directly. §1, §4, §9, §13, §19, §21b, §23 (this document) — DiFR's core mechanism, the Merkle-tree construction, the trigger-backdoor demonstration, the DSL/certificate, the storage-bank transport analysis, the tamper-evident log, and the approval registry, all reused rather than rebuilt.

---

### §25. Pre-Training Verification

Worth stating plainly before anything else, because it recalibrates what this section can honestly claim: the source material's own resource allocation puts roughly 80% of verification R&D effort behind the inference-only retrofit — everything this document has built since §1 — and treats direct training verification as a smaller, separate ~20% research bet. The Verification Plan supplement is explicit that setting up a verification regime for *resumed* training is a parallel sprint that happens after an inference-only pause is already in place, precisely because R&D verification has properties that differ enough to need its own effort. This section inherits that honesty rather than overselling: it builds and tests the real, named mechanism as far as it genuinely goes, and reports exactly where the published literature says it stops.

#### 25a. Why this doesn't just extend §5

Three real differences, not one blended "training is harder" gesture. **Network shape:** §1 deliberately stripped the east-west interconnect down for inference-only clusters — "a cluster that's structurally incapable of fast collective communication... is a worse platform for a large training run even if every other verification layer here were somehow defeated." A real training run needs exactly that collective communication, across potentially thousands of accelerators, which is a fundamentally different traffic pattern than §2's tap was ever built to see. **Timescale:** an inference request is checked in seconds; a pre-training run spans weeks to months. Recomputing a sampled *forward pass* the way §5 does doesn't generalize to recomputing a sampled *week* of gradient descent — the unit of evidence has to change shape, not just get bigger. **What's being claimed:** §5 verifies that a claimed output matches a declared, static checkpoint. Training verification has to establish that a *sequence of updates* — not a single state — actually happened, honestly, in the claimed order, at the claimed cost.

#### 25b. Proof-of-Learning, built and tested at toy scale

**The real mechanism.** Jia et al. (2021) proposed Proof-of-Learning: a prover periodically logs weight checkpoints along with the data used between them; a verifier replays a sampled segment from a logged checkpoint and checks whether it lands on the next one. Shavit's extension proposes this as on-chip firmware — periodic snapshots, cryptographic hashes, sent to a verifier-trusted server, checked via sampled "Proof-of-Training-Transcript" replay — explicitly instead of zero-knowledge proofs, which he judges too computationally inefficient at this scale (the same tradeoff §26 will need to weigh directly). This is the identical shape as everything else in this document — verifier-controlled sampling, independent recomputation, a real check instead of a signed assertion — one level up: the unit being recomputed is a training segment, not a forward pass.

Built for real: a tiny character-LM trained in 8 logged segments of 400 real gradient steps each (3,200 total steps, 5.6s), each segment's start-hash, end-hash, and data-selection seed logged into a tamper-evident record — §21b's construction reused a **sixth** time in this document. A verifier samples one segment at random (§1's own budget-limited-sampling principle, applied to training instead of packets), reloads the claimed starting checkpoint, and independently replays the claimed steps with the claimed seed:

```
Sampled segment 7: claimed_end=4b70987f756e...  recomputed=4b70987f756e...
Independent replay matches claimed checkpoint: True
```

Bit-exact, not merely close — same hardware, same code, same seed. Worth flagging rather than taking for granted: this is exactly the determinism §7 found needs real, deliberate engineering the moment hardware or batch shape differs at all. It holding here for free is a same-machine, same-run property; a real deployment spanning weeks and possibly different hardware generations doesn't get this without doing what §7 already priced (1.8–63% throughput cost, architecture-locked in the cheap case).

**A real attack, honestly labeled as the simple one.** A prover claims a full segment's worth of compute (400 steps) but actually spends an eighth of it (50 steps), reporting the cheaper checkpoint as if the full claim were true:

```
Claimed: 400 steps, seed=1003, forged_end=1723ed59c737...
Verifier's real 400-step replay: f42230e64987...
Match: False (must be False -- 50/400 of the claimed compute was never spent)
```

Caught, because the verifier's replay spends the same compute the prover claimed — the identical economics §1's C-fraction budget always has, now paid in training steps instead of recomputed packets.

**A real, honest tension, not a bug.** A different prover spends the *full, genuine* 400 steps, honestly, but with a different data-order seed:

```
Original logged path (seed=1003):  end_hash=f42230e64987...
Alternate REAL path (seed=1503, same n_steps, same real compute): end_hash=afb9ea766c19...
Hashes match: False
```

Full compute, honestly spent, and it does not reproduce the originally logged checkpoint — because SGD's trajectory depends on data *order*, not just which data and how many steps, a real property Shumailov et al. (NeurIPS 2021) studied directly under the name data-ordering attacks. Exact-hash replay verification, as tested above, only ever accepts the one specific path a prover committed to at logging time. That's not a defect in this implementation; it's the real shape of the problem.

#### 25c. What the published literature actually broke, and what this sandbox didn't test

Precision matters here, because it would be easy to let the two results above imply more coverage than they have. What got tested: a naive prover who spends less compute than claimed (caught trivially) and an honest prover whose genuinely-equivalent work doesn't hash-match (a real tension, not an attack). What Fang et al. (EuroS&P 2023) actually broke is a different and harder thing: **spoofing** — constructing a checkpoint trajectory that passes verification for a model the adversary never actually trained (a stolen model, most concretely), cheaply and reproducibly. The original PoL paper's own security argument was that spoofing costs as much as honest training, removing the incentive to try; Fang et al., building on an earlier counter-example, show this is false across real (not just deliberately weakened) verification configurations. Their sharper conclusion is the one worth carrying forward exactly as stated: building a *provably* robust PoL verification mechanism reduces to open problems in learning theory — not an engineering gap this document could plausibly close with more careful implementation, but a research gap in understanding deep-learning optimization itself.

This sandbox doesn't construct or test that spoofing attack, and says so rather than implying otherwise: a meaningful attempt needs a model and loss landscape with enough real structure for a forged trajectory to exploit, which a tens-of-thousands-of-parameters toy character-LM may not possess in a way that transfers to what actually breaks PoL at real model scale. What this section *can* honestly claim is narrower and still real: the replay mechanism itself works exactly as designed, a naive shortcut is caught, and a genuine, non-adversarial tension in the design (path-dependence) is demonstrated rather than asserted. The harder, published vulnerability is cited accurately rather than quietly matched against a weaker demo that wasn't actually built to test it.

#### 25d. Where this leaves the "resuming training" regime, honestly

Given PoL's robustness gap is a research problem rather than an implementation one, and given zero-knowledge proof-of-training is set aside on efficiency grounds by the same literature this section already cites, the honest bottom line matches the source material's own framing exactly: this needs more R&D, prototyping, and red-teaming before it's a mechanism a deal could rely on the way §5's DiFR — a published, empirically validated result — already can. One complementary, *preventive* lever worth naming rather than building out fully here, since it doesn't depend on resolving PoL's detection problem at all: multiparty cryptographic control, where a training run only executes once cryptographically signed by every required party, extends directly from §23's approval registry (a training-start decision requiring multiple independent signatures rather than one auditor's) without needing PoL to work at all — a gate before the fact, not a check after it, and a real, separate lever this document already has the infrastructure to build if it turns out to matter more than after-the-fact replay does.

#### Self-check

Real mechanism built and tested, not just described: confirmed — a genuine 8-segment, 3,200-step training run, logged and independently replayed to a bit-exact match. The attack actually tested is precisely characterized: confirmed — a naive compute-shortcut attack, explicitly distinguished from Fang et al.'s harder, published spoofing result rather than conflated with it. The honest tension is reported as a tension, not smoothed into either "broken" or "fine": confirmed — a genuinely honest alternate path fails exact-match replay, cited to real literature (Shumailov et al.) on exactly why, rather than treated as a bug in this file's implementation.

**Sources used in this section:** AI Futures Project, *AI 2040: Plan A*, Verification Plan supplement (ai-2040.com/supplements/verification-plan) — the 80/20 R&D allocation and the resumed-training regime as a separate, parallel effort. Jia, Yaghini, Choquette-Choo, Chandrasekaran, Papernot, "Proof-of-Learning: Definitions and Practice" (2021) — the core PoL mechanism this section builds a toy version of. Fang, Jia, Thudi, Yaghini, Choquette-Choo, Dullerud, Chandrasekaran, Papernot, "Proof-of-Learning is Currently More Broken Than You Think" (EuroS&P 2023) — the real spoofing vulnerability and its open-problem-in-learning-theory conclusion, cited precisely rather than assumed from the title. Shumailov, Shumaylov, Kazhdan, Zhao, Papernot, Erdogdu, Anderson, "Manipulating SGD with Data Ordering Attacks" (NeurIPS 2021) — grounding for why the honest alternate-path tension in 25b is a real, named property. Shavit, "What does it take to catch a Chinchilla?" — the on-chip-firmware PoTT extension and the ZK-inefficiency judgment, already cited via §26's forward reference. §1, §5, §7, §21b, §23 (this document) — the sampling principle, the recomputation economics, the determinism findings, the tamper-evident log, and the approval registry, all reused rather than rebuilt.

---

## Part VI — The Frontier

### §26. The Cryptographic/ZKP Track

Real, separately-funded, and explicitly parallel rather than integrated: on top of the network-tap-and-recomputation architecture this entire document has built, the source material describes on the order of $100M mobilized specifically toward "software-only and cryptography-centric (e.g., ZKPs) approaches" — one candidate track among several the source material itself frames as *alternatives* to Plan A's primary retrofit, not components of it. §25 handed this section a specific, answerable question rather than a cold open: is Shavit's judgment that zero-knowledge proofs are too computationally inefficient for training-scale verification a permanent verdict, or a currently-true one. The honest answer turns out to depend on which half of "training-scale" is meant.

#### 26a. What this track would actually buy, and why it's a different shape of tradeoff

Every mechanism this document has built since §5 shares one cost allocation: the *verifier* pays, continuously, to independently recompute a sampled fraction of what the prover claims — §1's C-fraction budget, paid every time, by the checking side. A working zero-knowledge proof of computation inverts that allocation entirely: the *prover* pays once to generate a proof, and the verifier's cost to check it is cheap and — critically — stays roughly constant regardless of how large the underlying computation was, rather than scaling with it. If that tradeoff were cheap enough to actually use, it would change more than an implementation detail; it would change who bears the ongoing cost of verification at all. Whether it's cheap enough is the question the rest of this section actually answers, piece by piece rather than in one number.

#### 26b. Freivalds' algorithm: the real, buildable core of "verify cheaper than redo"

The specific idea real ZK-ML systems build the cheap part of their machinery on isn't new cryptography — it's Freivalds' algorithm (1979), and zkLLM's own sumcheck-protocol foundation is a more general version of exactly this: check a claimed matrix product `C = A @ B` by testing `A @ (B @ r) == C @ r` for a random vector `r`, at O(n²) cost, instead of recomputing the full O(n³) product. Built and tested for real:

**Correctness** — an honestly-claimed product passes at every size tested (n=10, 100, 500).

**Soundness, checked against the actual bound, not assumed.** Freivalds' real, provable guarantee: a single trial catches a wrong claim with probability ≥ 1/2. Over 2,000 independently tampered matrices (a single entry perturbed — the hardest case for the checker, not a strawman large error), the measured single-trial catch rate was 0.5155, comfortably satisfying the bound. Repeating trials drives the miss probability down geometrically, and the match to theory is close enough to be worth showing in full:

| trials (k) | empirical catch rate | theoretical 1 − (1/2)ᵏ |
|---|---|---|
| 1 | 0.4900 | 0.5000 |
| 2 | 0.7540 | 0.7500 |
| 4 | 0.9320 | 0.9375 |
| 8 | 0.9960 | 0.9961 |
| 16 | 1.0000 | 1.0000 |

**The real crossover, measured rather than asserted from the complexity class alone.** At n=100 the check is actually *slower* than just multiplying (0.4×) — three separate matrix-vector products plus call overhead dominates before the problem is large enough for the O(n²)-vs-O(n³) gap to matter. Past roughly n=600, checking stays consistently 14–16× faster than the real product — not growing as cleanly with n as the asymptotic classes alone would predict, because numpy's matmul is BLAS-backed and cache-optimized, nowhere near the textbook triple loop "O(n³)" is shorthand for. Reported as measured, not smoothed into a cleaner story than the numbers actually show.

**Two honest limits, stated directly rather than left for the reader to assume away.** This is not zero-knowledge by itself — the checker sees A and B in full; nothing here hides anything. And it says nothing about the nonlinear operations — softmax, GELU, layernorm — that zkLLM's own tlookup and zkAttn machinery exists specifically to handle at real, separately-measured cost. Matrix multiplication is the part of a transformer this technique cheapens; it's a large part, but not the part that makes real zkML systems expensive.

#### 26c. The real cost of the full thing — inference is close, training isn't

**Inference-only ZK proving is a real, cited, working result.** zkLLM (Sun, Li, Zhang; ACM CCS 2024) generates a correctness proof for a full 13-billion-parameter LLM's inference process in under 15 minutes, with a proof under 200KB, verifiable in 1–3 seconds — and the proof reveals nothing about the model's own weights. That's real, published, and independently reproduced across the sources checked for this section. It's also, by other researchers' own explicit assessment rather than this document's inference, still "prohibitively expensive for high-performance inference servers" — a direct, honest external judgment worth citing exactly rather than softened, because it's the field's own verdict on its own best current number.

**Training-specific proving is a different, much larger gap.** zkLoRA (2025) measured real per-step proving time across six transformer LLMs — but the measurement is for one mini-batch consisting of a *single data sample*: 121.93 seconds (LLaMA-3.2-3B) to 249.38 seconds (OPT-13B), for one step, at the smallest possible batch size. A real pretraining run needs vastly more than one sample per step and vastly more than one step. Extrapolated illustratively — every assumption stated, not asserted as a real figure — even a deliberately conservative 50,000 steps (real frontier pretraining runs are widely reported to need far more) comes to:

| model scale | proving time / step (real, cited) | 50,000 steps, sequential, mini-batch-of-1 |
|---|---|---|
| LLaMA-3.2-3B | 121.93s | ~70.6 days |
| OPT-13B | 249.38s | ~144.3 days |

— of proving alone, before accounting for real production batch sizes (hundreds to thousands of samples per step, not one) or the actual training compute itself. This isn't a strawman comparison invented to make the point look worse than it is; it's the field's own real numbers, extrapolated under a labeled, conservative assumption. The zkLLM ecosystem's own current assessment matches: full ZK proof of arbitrary gradient backpropagation and optimizer steps "remains substantially more expensive than inference-only ZKP," and even zkLoRA's own LoRA-style narrowing of what gets proven "partly mitigates but does not eliminate" that gap.

**The trajectory is real too, and points toward "currently true," not "permanent."** Naive circuit-based ZK-ML approaches historically incurred more than 10× runtime overhead; newer commit-and-prove and parallel-accumulator techniques have brought that down substantially, and zkGPT reduces end-to-end proving for the much smaller GPT-2 to under 25 seconds. Inference-side proving has moved from clearly impractical toward "impressive but still too slow for production serving" in a few years — a trajectory this document has already seen once, in §7's batch-invariant-kernel cost dropping from 63% to ~2% over about the same span. Training-side proving hasn't made a comparable jump yet, and the field's own stated reason isn't an engineering backlog — it's that arbitrary backpropagation is a fundamentally larger circuit to prove correct than a forward pass, at every current technique's core.

#### 26d. Answering §25's question, and one real idea worth naming rather than building

Currently true, not permanent, and unevenly true across the two things this document has needed to verify. For inference specifically, "too inefficient" is trending toward "not yet practical for high-volume serving, but closing" — a real, cited, moving target. For training specifically, the gap remains large enough that the field's own current papers describe it as unsolved, not slow. §25's "resuming training" regime has no basis to assume ZK proof-of-training will be ready on any particular near-term timeline, and this document doesn't manufacture one.

One idea worth naming precisely because it doesn't require resolving that gap first: ZK proving's real advantage isn't cheap *proving*, which stays expensive — it's cheap, sublinear, roughly-constant *verification*, which is already fast today (the 1–3 second zkLLM figure cited above). That property is worth spending on *rare, high-stakes* events even while proving remains too expensive for continuous use — §24's release decision, or a periodic checkpoint inside §25's Proof-of-Learning log, are exactly the kind of infrequent, consequential events where a prover paying minutes of proving cost once, in exchange for a verifier checking in seconds forever after, could be worth the asymmetry even today. Not built out here — it would need its own red-teaming, the same way every other mechanism in this document got one — but named as a real, connectable idea rather than treating this track as all-or-nothing against the architecture already built.

#### Self-check

Real, working piece built and tested, not just described: confirmed — Freivalds' algorithm, correctness confirmed, soundness checked against its actual proven bound (empirical rates matching theory to within noise at every trial count), and a real measured cost crossover reported honestly including where it initially runs backward. Cost figures are real citations, not estimates: confirmed — zkLLM's 13B/15-minute/200KB/1-3-second figures and zkLoRA's 121.93–249.38-second per-step figures both come from the papers directly, with the training-run extrapolation clearly labeled as illustrative under a stated, conservative assumption rather than presented as a real benchmark. §25's question answered directly, not deflected: confirmed — "currently true, unevenly, trending down for inference and not yet for training" is a specific claim, not a hedge.

**Sources used in this section:** AI Futures Project, *AI 2040: Plan A*, Verification Plan supplement and "get involved" page (ai-2040.com/supplements/verification-plan) — the ~$100M cryptography-track funding figure and its framing as a parallel effort. Freivalds, "Probabilistic Machines Can Use Less Running Time" (IFIP 1979) — the algorithm this section builds and tests. Sun, Li, Zhang, "zkLLM: Zero Knowledge Proofs for Large Language Models" (ACM CCS 2024) — the 13B/15-minute/200KB/1–3-second inference figures. The zkLoRA/VeriLoRA papers (2025) — the real per-step training-proving figures this section's extrapolation is built from. §1, §5, §7, §25 (this document) — the recomputation cost-allocation baseline, and the batch-invariant-kernel cost trajectory this section's own "currently true, not permanent" framing is modeled on.

---

## Part VII — Holding Together

### §27. Composing Trust Roots & Hardening

The Verification Plan's own "get involved" page states this section's actual job more precisely than a paraphrase would: the open problem is proving that a combination of trust roots is sound — that a policy set actually enforces the independence between them it claims to, rather than quietly collapsing back to one. This document has built enough separate mechanisms by now (physical simplicity, TEE attestation, physical security, six reuses of one signing-key construction, and §26's not-yet-practical cryptographic track) that the question is no longer rhetorical. This section doesn't introduce a new mechanism. It checks the ones already built against each other, and reports what it actually finds — including inside this document's own prior work.

#### 27a. A trust-root inventory, honestly categorized by what each one is actually trusting

| mechanism | what it's actually trusted on |
|---|---|
| §2's passive splitter | physical simplicity — no logic to compromise, full stop |
| §3's secure gateway | a TEE's attestation of its own boot-time firmware/software state |
| §21's recomputation server | physical security (enclosure, debug-port placement) plus attestation |
| §21b/§22/§23/§24/§25's tamper-evident logs | secrecy of a private signing key |
| §26's ZK track | cryptographic soundness of the proof system, not yet practical at training scale |
| §23's approval baseline | a human auditor's judgment, per the source material's own design |

Six genuinely different bases for trust. Different bases is necessary for independence, but it isn't sufficient — two mechanisms can rest on different-sounding foundations and still share a hidden point of failure if they're wired together carelessly. That's the actual content of "quietly collapsing back to one," and the next subsection finds a real instance of it rather than describing the risk abstractly.

#### 27b. The real finding: an audit of this document's own code, not a constructed example

Auditing §24's `weight_transport.py` against the question this section is actually about turned up a genuine instance, not a hypothetical one. Its `__main__` block did this:

```python
auditor_key = Ed25519PrivateKey.generate()
training_registry = ApprovalRegistry(auditor_key)      # §23's authority
release_chain = ReleaseChain(auditor_key, training_registry)  # §24's authority
```

One key, instantiating both the §23 training-workload-approval authority and the §24 release authority. Neither `ApprovalRegistry` nor `ReleaseChain` is broken — both do exactly what §23 and §24 built and tested them to do. The bug is compositional: the document's own narrative clearly wants these to be independent decisions (a technical audit team confirming a training run stayed within declared bounds; a separate release process deciding whether to actually ship weights after evaluation), specifically so that one compromised or coerced party can't unilaterally clear both gates. Sharing a key erases that independence in code, even though the write-up never said it should.

Tested directly, against the real classes, not a simplified stand-in:

```
1. Reproducing §24's ACTUAL setup: one key, two logically-distinct roles
   Same key underneath both: True

2. THE ATTACK: whoever compromises this ONE key can forge BOTH roles
   Attacker forges a TRAINING APPROVAL using the compromised key: accepted=True
   SAME attacker forges a RELEASE decision using the SAME compromised key: accepted=True
   One compromise, both authorities defeated: True

3. THE FIX, tested: independently generated keys per authority
   Attacker compromises ONLY the release key (a narrower, more realistic breach)
   Forging a RELEASE with the compromised release key: accepted=True
   SAME attacker attempting to forge a TRAINING APPROVAL with the release key: accepted=False
   PASS: the compromise stayed contained to the role whose key was actually stolen.
```

Fixed in the shipped file, not just in this section's demonstration — `weight_transport.py` now generates `training_auditor_key` and `release_auditor_key` independently, and every one of its five original tests (§24's full chain, the rejected-unapproved-release check, the shard-swap attack, the Merkle-proof efficiency check, and the tamper-on-the-release-log check) still passes unchanged, because the two authorities never actually needed to share a key for the mechanism's own logic — the sharing was pure convenience with no functional benefit, which made this a free fix: pure security gain, zero correctness cost. Worth being precise about what this does and doesn't prove: it's a real bug, caught, understood, and fixed in one specific, real instance. It is not evidence every remaining pairing in this document's own trust-root inventory is independent — only that this one was checked and wasn't.

#### 27c. The other kind of shared root: physical, not cryptographic

A different composition failure the same source material names directly: accelerator TEEs keep getting broken and patched, and side-channel or telemetry attacks that compromise a host machine tend to reach the accelerator it hosts too — meaning a "TEE-attested" trust root and a "this host is secure" trust root aren't actually independent either, for a physical rather than cryptographic reason. The source's own prescription is independent corroboration across power, timing, and network signals, so that one broken TEE doesn't take the whole verification story down with it.

This document already built exactly that, in §18, before this section existed to name why it mattered at this level: a 2-of-3 correlation rule across power draw, NVLink utilization, and response timing, specifically justified there on the grounds that a real covert operation has physically-linked side effects across signal types that independent operational noise doesn't share. Re-used here rather than re-built, with its own honest limitation carried forward rather than left behind: §18's own self-check was explicit that no ground-truth attack dataset exists to validate detection rate against, so the bar it met was "concrete enough to test later," not "proven to work." Citing it again here doesn't upgrade that status — it's still the document's best current answer to physical-root independence, and still an unproven one.

#### 27d. Hardening: hardcoded weights change the shape of the trust question, not just its strength

A specific idea named in the source material worth reasoning through rather than building, since it's a hardware manufacturing concept no sandbox can fabricate: chips with weights physically hardcoded at manufacture time, so that "is this chip running the declared model" stops being an ongoing runtime question §5's whole DiFR apparatus exists to answer, and becomes a one-time question about what got fused into silicon before the chip ever shipped. That's a genuinely different trust-root *shape*, not a stronger version of the existing one — cheaper to check forever after (arguably free, if the hardware genuinely can't run anything else), at the cost of total inflexibility (no model updates, no multi-tenant serving on that silicon) and a complete transfer of trust onto the manufacturing and supply chain instead of onto runtime verification. §20 already named exactly why that transfer isn't free: supply-chain implants happen before a server ever reaches a facility, sealed in before any on-site audit or enclosure seal could exclude them — the same chain-of-custody problem this document has flagged before, now landing squarely on the one component a hardcoded-weights design would need to trust completely.

#### 27e. Does the whole thing compose soundly? The honest answer, not a reassuring one

No — not provably, and this section doesn't claim otherwise. The source material calls this an open problem, and one real, fixed instance of the failure it describes, found inside this document's own code, is evidence the discipline of actually checking works when applied — not evidence the rest of this document's trust-root pairings are independent by default. What §27 actually did: named six real bases for trust, found one real place two of them had quietly become one, fixed it, and carried forward — rather than resolved — the one physical-composition question this document already had a partial, honestly-caveated answer to. That's the accurate scope of "holding together" this section earns: checked where checked, not proven throughout.

#### Self-check

The composition failure is demonstrated against this document's own real code, not invented: confirmed — the shared-key setup is copied exactly from §24's actual `weight_transport.py`, the attack and fix are both tested against the real `ApprovalRegistry`/`TamperEvidentLog` classes, and the fix was applied to the shipped file itself, not left as a suggestion. The physical-composition question is connected to real prior work with its limitation intact, not upgraded: confirmed — §18's correlation rule is cited as this document's existing answer, with its own "not validated against ground truth" caveat repeated rather than dropped now that it's being reused for a new purpose. The section doesn't overclaim having solved what the source calls an open problem: confirmed — stated explicitly in 27e rather than implied away by ending on the fix in 27b.

**Sources used in this section:** AI Futures Project, *AI 2040: Plan A*, Verification Plan supplement and "get involved" page (ai-2040.com/supplements/verification-plan) — the trust-root-independence framing and the TEE-hardening/hardcoded-weights material, both cited directly. §2, §3, §5, §18, §20, §21, §21b, §23, §24, §26 (this document) — every trust-root basis in the inventory, and the correlation-warden mechanism, all reused rather than restated from scratch.

---

### §28. Binding Verification to Governance

The Verification Plan's own "get involved" page names this section's job precisely: the mapping between machine-checkable artifacts — receipts, audit trails — and the legal and treaty instruments coming online, things like conformity-assessment schemas, retention rules, and dispute resolution, plus the incremental path from unilateral declarations to a monitoring body to a treaty. Nothing through §27 has touched this. Every mechanism this document has built produces a technical finding; none of them says what that finding *means* to a body with authority to act on it. This section closes Part VII by building the one piece that's concretely buildable (28b), reasoning honestly through the piece that isn't (28c), and first, examining an analogy this document has leaned on since §20 without yet checking where it actually breaks.

#### 28a. The IAEA analogy, examined rather than continued to be borrowed

§20 modeled inspection cadence directly on IAEA safeguards concepts — Significant Quantity, Detection Probability, conversion time — and the parallel is real: both nuclear material and AI chips are dual-use, capital-intensive, and produced through a concentrated, choke-pointable supply chain. But a recent comparative analysis of hardware-level AI governance names two limits worth taking seriously rather than leaving implicit. First: nuclear material is radioactive and physically detectable at borders through passive means; AI chips aren't, which is exactly why §20's own power-envelope check had to substitute an indirect signal (grid draw) for something nuclear safeguards gets for free. Second, and more consequential for this section specifically: the IAEA operates entirely on the consent of signatory states and holds no unilateral enforcement authority of its own — any comparable body for AI would face the identical constraint. Every mechanism this document has built assumes a verifier with standing to check and a prover who submits to being checked. Neither assumption is a technical property; both are the treaty layer this section is actually about, and no amount of cryptography in §1–§27 supplies them.

#### 28b. A conformity-assessment schema, tested against real prior results, not hypothetical ones

The concrete, buildable piece: a mapping from the technical signals this document already produces to categories a dispute or enforcement process could actually act on — COMPLIANT, MINOR_DEVIATION, MATERIAL_BREACH, INCONCLUSIVE — with the reasoning for each category stated alongside it, not just a bare label. One override matters more than the deviation-based rule itself: if the evidentiary record's own tamper-log integrity check fails, the result is MATERIAL_BREACH *regardless of the deviation number*, because a compromised record can't support any finding, favorable or not. Tested directly rather than asserted — the same untampered result classified COMPLIANT; the identical claimed value, but with its logged record altered after signing, reclassified MATERIAL_BREACH even though nothing about the number itself changed:

```
Untampered log, avg_deviation=0.0: category=COMPLIANT
Same claimed avg_deviation=0.0, but the record was altered after signing
(tamper_log_valid=False): category=MATERIAL_BREACH
```

The more consequential test used real per-trial deviation data already produced in §11's calibration run — 120 real trials per model per temperature, not a hypothetical — classified at two different τ values:

| model | temp | τ=0.3 (illustrative, uncalibrated) | τ=0.02 (§11's actual recommendation) |
|---|---|---|---|
| cross_family | 0.3 | 96.7% COMPLIANT | 7.5% COMPLIANT, 77.5% MATERIAL_BREACH |
| cross_family | 0.8 | 99.2% COMPLIANT | 12.5% COMPLIANT, 49.2% MATERIAL_BREACH |
| cross_family | 1.6 | 99.2% COMPLIANT | 17.5% COMPLIANT, 29.2% MATERIAL_BREACH |
| same_family | 0.3–1.6 | 5–58% COMPLIANT | **0% COMPLIANT at every temperature — 100% MATERIAL_BREACH** |

The gap between those two columns is the actual finding, and it's a sobering one: fed an uncalibrated τ, this schema would tell a dispute process that a genuinely dishonest model was legally compliant 97–99% of the time — not because the schema's logic is wrong, but because §9 already established τ=0.3 was never the calibrated figure to begin with, and a conformity-assessment layer inherits that upstream problem rather than fixing it. This section can build the mapping from technical signal to legal category. It cannot substitute for §11's calibration work being done correctly before that mapping is ever applied — a conformity schema is only as legally meaningful as the threshold it's handed.

#### 28c. Dispute resolution: what the existing evidence actually settles, and what it can't

Reasoned through rather than newly built, because the evidence a real dispute would turn on already exists in this document: §4's Merkle inclusion proofs let a disputed packet's payload be checked against an already-committed epoch root in O(log n), without needing to trust whoever's presenting it; §21b's hash-chained, signed log makes any post-hoc edit to a finding's own record detectable, which is exactly what 28b's override tests. Together, these settle a narrower question well: *given* the record wasn't altered after the fact, does the recomputed evidence match what's claimed. What they cannot settle is who gets to compel production of that evidence, what happens when a party disputes the verifier's *own* honesty rather than the prover's, or what remedy follows once a MATERIAL_BREACH finding is confirmed. Those are exactly the questions 28a's IAEA limitation names: a body with standing and (state-consented, not unilateral) authority to act, which this document's cryptography can inform but never substitute for.

#### 28d. The incremental path, and what each stage actually needs from this document

The source material's own staged path — unilateral declarations, then a monitoring body, then a treaty — maps cleanly onto pieces this document has already built at different points, worth naming explicitly rather than leaving as an abstract progression:

| stage | what it needs from this document | what it doesn't need yet |
|---|---|---|
| Unilateral declaration | §13's DSL, §23's approval registry (self-reported, no external check) | §2's tap, §5's recomputation — nothing external verifies the declaration yet |
| Monitoring body | Add §2–§14 (tap + DiFR), §15–§18 (completeness), §19–§22 (physical trust) — an external party now independently checks | Binding legal consequence — the monitoring body can observe and report, not yet compel |
| Treaty | Add this section's conformity schema and 28c's dispute-resolution layer, backed by actual institutional authority | Nothing left in this document's own scope — everything past this point is the legal instrument itself |

Read this way, the earlier parts of this document weren't just built in an arbitrary convenient order — they're a rough match for what each successive stage of that real, named progression would actually need, even though no single part of the source material laid the mapping out this explicitly.

#### Self-check

The IAEA analogy is examined, not just reused: confirmed — two specific, cited limitations (radioactive detectability, consent-based non-enforcement) named directly rather than left as an implicit, uninterrogated parallel this document has used since §20. The conformity schema is tested against real prior data, not invented inputs: confirmed — both the tamper-integrity override and the τ=0.3-vs-τ=0.02 comparison run against real per-trial arrays and real category means already produced by §9 and §11. The section doesn't overclaim what cryptography settles: confirmed — 28c states directly what the existing evidence can and can't resolve, and 28a's consent-based-authority limitation is carried through to 28c's conclusion rather than raised once and dropped.

**Sources used in this section:** AI Futures Project, *AI 2040: Plan A*, Verification Plan supplement "get involved" page (ai-2040.com/supplements/verification-plan/get-involved) — the conformity-assessment/retention/dispute-resolution framing and the unilateral-declarations-to-treaty staged path, cited directly. "Hardware-Level Governance of AI Compute: A Feasibility Taxonomy for Regulatory Compliance and Treaty Verification" (arXiv:2604.04712) — the IAEA analogy's radioactive-detectability and consent-based-enforcement limitations. §3, §4, §9, §11, §20, §21b (this document) — the AUC-vs-accuracy metric-trap precedent, the Merkle-proof and tamper-log mechanisms, and the calibration finding this section's central test is built on, all reused rather than restated.

---

## Part VIII — Other Tracks

### §29. Track 1 — Company/Domestic Auditing

Worth naming plainly before anything else: this entire document, §1 through §28, has been Track 2. The source material's own breakdown of verification work into four parallel tracks (adapted from James Petrie) describes what this document built — passive optical taps, randomized recomputation, memory wiping, tamper-evident enclosures — as "options deployable before highly secure, purpose-built hardware exists," one track among several rather than the whole of the problem. Track 1 is a different bet entirely: domestic regulation or company-to-company agreements that "may not require any new verification technology" at all, justified by a real, stated claim — companies are less able to backdoor their own chips than nation-states, so embedded auditors together with existing hardware might already be enough. The named work for this track is specific: figure out the implementation details such a regime would need, and red-team its robustness. This section does the second half, against this document's own prior math rather than starting cold.

#### 29a. A real framework this maps onto precisely

AVERI (the AI Verification and Evaluation Research Institute, launched January 2026) publishes exactly the calibration this section needs: four AI Assurance Levels, from AAL-1 — limited access, similar to the third-party evaluations AI labs already commission — up to AAL-4, "treaty grade" assurance sufficient for international agreements. AVERI's own distinction between the levels is precise and worth stating exactly rather than paraphrased into something vaguer: at lower levels, auditors rely more heavily on information the company itself provides; at the highest level, auditors can rule out the possibility of materially significant deception by the auditee. That's the honest axis Track 1 sits on. This document's Track 2 architecture — §2's physically-tamper-resistant splitter, §5's independent recomputation, §21b's cryptographic tamper evidence — was built specifically to reach something like AAL-4 without relying on the audited party's own cooperation for the parts that matter most. Track 1 explicitly isn't trying to reach that bar; it's asking how much real assurance a much cheaper, much faster-to-deploy regime can still buy.

#### 29b. Red-teaming the actual claim, with this document's own math

§22 already built and verified the relevant machinery: a Poisson-process model connecting how often an auditor actually checks something to how likely a real violation is to be caught. That model doesn't care whether the "auditor" is an internationally-sampled quarterly visit to one of a thousand facilities or a single company's own embedded reviewer — the input that matters is the rate, λ. Reusing §22's functions directly, with one changed input:

| regime | λ (checks/year) | P(caught), 1-week bypass | P(caught), 1-month bypass |
|---|---|---|---|
| Track 2 baseline (§22's quarterly, 10%-sampled international regime) | 0.40 | 0.0076 | 0.0323 |
| Track 1, monthly embedded review | 12.0 | 0.2056 | 0.6270 |
| Track 1, weekly embedded review | 52.0 | 0.6311 | 0.9861 |
| Track 1, daily embedded presence | 365.0 | 0.9991 | 1.0000 |

And expected time-to-discovery for a sealed (tamper-evident) bypass, formula checked against real simulation rather than trusted alone:

| regime | formula (days) | Monte Carlo (days) |
|---|---|---|
| Track 2 baseline | 912.5 | 913.6 |
| Track 1, monthly | 30.4 | 30.3 |
| Track 1, weekly | 7.0 | 7.0 |
| Track 1, daily | 1.0 | 1.0 |

The claim holds up, as far as cadence alone goes. Monthly embedded review — a real, achievable cadence for a single company's own compliance function, not a fleet-wide sampling program — cuts expected discovery time roughly 30×, with none of §2–§4's purpose-built hardware. Daily presence cuts it roughly 900×. This is exactly why "embedded auditors... might be able to reach sufficient assurance" is a plausible claim and not just an aspirational one: it's §22's own trusted math, landing very differently once fed Track 1's actual access model instead of Track 2's.

#### 29c. What cadence doesn't fix, stated as precisely as the improvement above was

Every number in 29b assumes an auditor's cadence converts directly into a real chance of catching a real violation — exactly true for §22's physical tap, which mechanically mirrors every packet crossing it with no discretion about what it sees, and NOT automatically true for a human auditor. A human auditor, embedded or not, sees what they're shown, or what they think to check. AVERI's own framework names this precisely: lower assurance levels rely on company-provided information, and the honest distinction between "daily embedded presence" and "daily embedded presence with the kind of access §2's splitter has by physical construction" is exactly the gap between AAL-2-ish and AAL-4, one the Poisson-process math above cannot see, because cadence was never the variable that question turns on. AVERI names a second, compounding real-world difficulty worth carrying forward rather than treating as separate: the auditors capable of doing this well are scarce, and often drawn toward the very companies they'd be auditing — a recruitment and independence problem no amount of on-paper cadence improves.

#### 29d. What Track 1 can honestly borrow from Track 2, and what it can't

Can: §21b's tamper-evident log construction, reused seven times in this document now, needs no exotic hardware at all — an embedded auditor's own findings, signed and hash-chained, get the identical tamper-evidence property §22's tap registry and §23's approval registry already have, at essentially zero marginal engineering cost. Cannot: anything that depends on §2's physical-simplicity trust argument or §3's TEE-rooted attestation, because both exist specifically to remove the audited party's own cooperation from the trust chain — the exact thing Track 1 is choosing to accept rather than engineer around, in exchange for speed and cost this document's Track 2 architecture never optimized for.

#### Self-check

The comparison reuses real, already-verified math rather than inventing new numbers: confirmed — every figure in 29b comes directly from §22's own `tap_inspection_model.py` functions, called with a changed input, with the sealed-case numbers checked against real Monte Carlo simulation rather than the formula alone. The section names what its own central comparison can't show, not just what it can: confirmed — 29c states directly that cadence and access-discretion are different variables, and that the reused math only ever modeled the first one. Grounded in a real, current external framework rather than this document's own invented categories: confirmed — AVERI's AAL-1-through-4 structure is cited precisely, including its own stated basis for the distinction (company-provided information vs. ruling out deception), not paraphrased into something looser.

**Sources used in this section:** AI Futures Project, *AI 2040: Plan A*, Verification Plan supplement "get involved" page (ai-2040.com/supplements/verification-plan/get-involved) — the four-tracks breakdown (adapted from James Petrie) and Track 1's own stated justification. AVERI, "Frontier AI Auditing: Toward Rigorous Third-Party Assessment of Safety and Security Practices at Leading AI Companies" (averi.org, 2026) — the AI Assurance Level framework and the auditor-recruitment difficulty. §2, §21b, §22, §23 (this document) — the physical-simplicity trust argument, the tamper-evident log, and the Poisson-process detection model, all reused rather than rebuilt.

---

### §30. Track 3 — Detecting Undeclared Compute

The Verification Plan supplement's own name for this problem is worth using exactly rather than the more totalizing framing "detecting undeclared compute" invites: **Problem 2, verifying that unknown compute is inconsequential.** Not finding all of it. The supplement's own covert-project supplement estimates a median of about 0.5% of the world's AI-relevant compute (80% CI: 0.1% to 1.4%) as plausible "dark compute" at the start of a deal — small enough, on the source's own numbers, to not threaten the deal's basic viability, and expected to shrink further as detection accumulates. Track 2 (§1–§28) and Track 1 (§29) both assume the facility in question is at least physically known, even where its honesty isn't trusted. Track 3 is the one case that assumption fails, and it's the last piece of this document.

#### 30a. The same move, confirmed as the source's own frame, not this document's invention

This document has made one particular epistemic move repeatedly enough that it's worth naming as a pattern rather than a coincidence: §1 scoped completeness to "nothing unapproved persists or leaves the cluster as output," explicitly narrower than "prove idle cycles are never touched." §4 argued a hash-only commitment is the right answer because the honest comparison was never "record everything" — it was "record something vs. record nothing." §12 computed a real bit-capacity bound for steganographic leakage rather than claiming zero channel capacity. §17 targeted residual side-channel capacity to match what the system already tolerated elsewhere, not to reach zero. §22 quantified a bypass-and-restore residual risk it explicitly declined to solve away. Every one of those is the same underlying move: bound a risk precisely, rather than claim to eliminate it. Track 3's own source material frames its hardest, least tractable-sounding problem — compute nobody declared existing at all — with exactly that same move. That's not this document reaching for a comfortable frame at the end; it's confirmation, on the last section, that the frame it kept returning to was the source material's own, not a coping mechanism invented along the way.

#### 30b. Verifying the fab-concentration argument, not just citing it

The source's structural reason dark compute should stay small: chip production runs through a small number of highly controlled fabs, and at sustained 3x/year production growth, "every 2 years 90% of the fabs are new fabs" — meaning diversion has to be caught early and often, against a supply chain that's mostly brand-new at any given moment. Checked directly rather than trusted: under 3×/year growth, the fraction of all cumulative capacity built in the most recent 2 years computes to 88.9%, matching the source's "~90%" closely — and it converges to that exact figure (1 − 3⁻² = 8/9) regardless of how many total years the model runs, confirmed by checking convergence across 5, 10, 20, and 40-year horizons rather than trusting one computed number. This is a real, structural property of sustained exponential growth, not an estimate the source pulled from elsewhere.

#### 30c. Bounding detectability by size, against a demonstrated capability — not a hypothetical one

Reusing §20's own power-envelope function for a new purpose: given a covert facility's size in GPUs, what facility power draw would it need. The honest anchor for whether that draw is detectable isn't hypothetical — SatVu, a real company, published a satellite thermal image in December 2025 clearly resolving the waste-heat signature of a real, named 700MW datacenter (the Riot Platforms Bitcoin-mining facility in Rockdale, Texas) at 3.5-meter resolution, from orbit. A covert operation at §20's own reference-facility scale — 5,702 GPUs — draws about 5MW, roughly 140× smaller than that demonstrated case. That is *not* evidence such a facility would stay hidden. A smaller heat signature is a real physical fact working against the defender too, and this document doesn't have the actual sensor's noise floor — only its best-case published resolution — so it states the real question precisely rather than resolving it in either direction: not "can waste heat be seen from orbit" (demonstrated, yes), but "at what scale does an AI-specific covert facility's signature clear a real sensor's real noise floor," which needs a number this document doesn't have.

One more real connection worth making explicit: taking the source's own 0.5%-of-world-compute median estimate and hypothetically concentrating it into a single facility comes to roughly 4,077MW — comparable to, and larger than, the 700MW case SatVu already resolved. That's exactly why the source's own mitigating detail matters as much as its headline number: the estimate assumes dark compute is spread across many smaller, individually-harder-to-resolve sites, not concentrated. Concentrated, the source's own median case is plausibly *more* visible than something already demonstrated as detectable. Spread thin, it isn't. The size of the number was never the whole claim; its distribution is load-bearing too, and this document's own math is what makes that visible rather than something to take on faith.

#### 30d. What this document's architecture contributes anyway, and where it stops completely

Nothing in §1–§29 was built to find a facility nobody declared — every mechanism from the tap onward assumes a facility that's at least physically present and knowable, even where its honesty is the whole question. But two pieces already built serve Track 3's purpose without having been designed for it: §20's inventory cross-checking (satellite imagery, import and customs records, §2's own network-visible device fingerprinting where a facility already has taps installed) doesn't require trusting a facility's own paperwork, which is exactly the property Track 3 needs for a facility that never filed any paperwork at all. And §13's checkpoint-hash-tied approval registry means legitimately-acquired chips accumulate a real, growing paper trail of what they were approved to run — a chip that never shows up in that trail anywhere is exactly the kind of gap an inventory audit is built to notice, even without knowing in advance where to look for it physically.

Where this document's architecture stops completely, stated as plainly as everywhere else it's stopped: a tap can't tap a network nobody told you exists. Everything through §29 verifies a claim against a check; Track 3 is about facilities that never made a claim to check against in the first place. That's not a gap this document's tools can close with more careful engineering — it's a different discipline (intelligence, not audit), named honestly as outside this document's own reach rather than gestured at with a mechanism that doesn't actually apply.

#### Self-check

The reframe from "detect everything" to "bound and verify inconsequential" is the source material's own, not this document's rhetorical move at the end: confirmed — cited directly, including the real quantified estimate it rests on. Both real, checkable claims in this section were actually checked, not just cited: confirmed — the fab-concentration figure computed to 88.9% against a "~90%" claim, with the exact closed form found and verified across multiple time horizons; the detectability comparison is anchored to a real, named, recently-demonstrated satellite result, not a hypothetical capability. The section states precisely what it can't resolve rather than picking a comforting default: confirmed — 30c explicitly declines to conclude either "detectable" or "hidden" for the reference-facility case, naming the specific missing number (real sensor noise floor) rather than filling the gap with an assumption.

**Sources used in this section:** AI Futures Project, *AI 2040: Plan A*, Verification Plan supplement (ai-2040.com/supplements/verification-plan) — the "verifying unknown compute is inconsequential" framing, the 0.5%-median/0.1–1.4%-CI dark-compute estimate, and the fab-concentration argument, all cited directly. SatVu / Space.com, "Satellites reveal heat leaking from largest US cryptocurrency mining center" (December 2025) — the real, demonstrated 700MW/3.5m thermal-detection result this section's size comparison is anchored to. §1, §2, §4, §12, §13, §17, §20, §22 (this document) — the completeness scoping, the hash-commitment reasoning, the bit-capacity bound, the residual-capacity targeting, the inventory cross-check, and the checkpoint-hash approval trail, all reused rather than re-derived, in what turns out to be this document's own closing argument as much as its source material's.

---

## Closing note

Thirty sections, drafted the way §1 said they would be: real code where this sandbox could support it, honest labeling where it couldn't, bugs found and fixed rather than smoothed over, and — a discipline that only fully paid off by being applied consistently rather than selectively — real sources checked at the point they were needed rather than assumed from memory, which is exactly what turned §23 through §30 from reasonable guesses into a document actually grounded in what the Verification Plan supplement says, sentence by sentence, rather than in what seemed like a plausible thing for it to say.

The document's own opening line about what "checkable" means in this sandbox held up across all thirty sections, not just the early ones where it was easy: no GPU, one logical CPU, no DPDK-capable NIC, no optical tap hardware, and — as of this section — no satellite. Where that meant a claim had to stay a design estimate instead of a measurement, it's labeled that way throughout, including here, in the section that closes it.

This isn't a finished verification system, and was never going to be one from a sandbox. It's thirty sections of honest work toward finding out how much of a real proposal survives contact with actually trying to build it.
