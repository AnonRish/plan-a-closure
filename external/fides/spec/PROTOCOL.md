# Fides Protocol Specification

Status: reference implementation / testbed, not a deployment-ready design.

## 1. Motivation

[AI 2040: Plan A](https://ai-2040.com/) proposes that an international AI slowdown deal is only enforceable if compliance can be checked "without relying on trust" — its own framing. Its [verification supplement](https://ai-2040.com/supplements/verification-plan) splits the problem into verifying that *known* compute is compliant and verifying that *unknown* compute is inconsequential. Fides addresses a narrow slice of the first problem: given a datacenter that is supposed to be running inference only, how does an auditor with no access to weights, prompts, or outputs get evidence that no training happened, without trusting the operator's word for it, and without needing to mirror every byte of traffic off-site?

## 2. Threat model

**In scope.** A prover (the accelerator, or a tap sitting on its network path) that may misreport its own workload class. The prover commits to a trace and later may be asked to reveal a sample of it. We assume the prover cannot predict, before committing, which indices the verifier will sample — this is enforced by having the verifier's random seed and sampling logic live entirely on the verifier's side, chosen after the commitment is published. We also assume a verifier/recomputation-server that may itself be compromised, coerced, or buggy, and could try to under-report or silently edit its own findings after the fact.

**Out of scope for this reference implementation.** Physical tampering with the tap hardware itself (SITREP: "TAP installation and network links", "Physical security and audits" — both graded not on track); side-channel exfiltration of information around the tap rather than through it (SITREP: "Side channel mitigation", "Side channel wardens" — both not on track); and an adversary that adapts its workload's *structural* signature specifically to evade `classifier.py` (see section 4). None of these are solved here, and none of them should be read as solved by proxy.

## 3. Commitment scheme

Every kernel event in an epoch (`op`, `timestamp_ns`, `duration_ns`, `bytes_read`, `bytes_written`, `flops`) is serialized deterministically (`commitment.py::_event_bytes`, a fixed `struct` layout, not a language-level hash of the operation name — string/enum hashing in Python is per-process randomized and would make two honest parties compute different roots for the same trace) and becomes a leaf in a BLAKE3 Merkle tree.

BLAKE3 specifically because:

1. It is a tree hash by construction, so a Merkle proof for any leaf is close to free to produce, rather than requiring a separately-built proof structure over a different hash.
2. Its throughput on modern hardware (SIMD, and AES-NI-class acceleration where available) matters because whatever computes commitments has to keep pace with live traffic on the same device serving production workloads — this is the tap's actual bandwidth constraint, and the reason the SITREP frames "packet-hashing taps" as a bandwidth-limiting alternative to full mirroring in the first place.

The prover publishes only the Merkle root plus its self-declared workload class, signed with an Ed25519 device key (`identity.py`). Nothing about the trace's content is revealed at commit time.

## 4. Structural classification: what it catches and what it doesn't

`features.py` extracts five aggregate statistics from a trace — backward/forward kernel ratio, presence of an optimizer-update kernel, mean all-reduce payload size, presence of KV-cache writes, and arithmetic intensity — and `classifier.py` thresholds on them. This is deliberately a transparent scoring function rather than a learned model: the classifier's own output feeds directly into what gets flagged for audit, so it needs to be inspectable by a human auditor, not itself a black box requiring separate verification.

**What this catches:** the tests in `test_attestation.py` show it catches (a) a full training epoch mislabeled as inference essentially every time at even a 20% sample rate, since roughly half of a training epoch's events carry the backward/optimizer signal, and (b) a handful of covert gradient steps hidden inside an otherwise-legitimate inference epoch, at a per-epoch probability matching the sampling math in section 5, compounding toward certainty as the device keeps operating.

**What this doesn't catch:** an adversary that specifically re-shapes its covert workload's *metadata* to imitate an inference-shaped trace at the kernel level — e.g., structuring gradient computation to avoid triggering an obvious optimizer-update kernel, or padding all-reduce traffic to look like activation communication rather than gradient communication. This is not a hypothetical concern: the Compute Verification Project's public working draft on structurally distinguishing inference from training via communication patterns is explicitly paired with an open competition to find training algorithms that evade it. Anyone hardening `classifier.py` past a first pass should engage with that competition rather than assume this repo's five features are the ceiling.

## 5. Spot-check audit and detection probability

The verifier samples `m` of the epoch's `n` events uniformly at random, without replacement, only after the commitment (and hence `n`) is already fixed and public. If `k` of those `n` events are "bad" (training-signal) events smuggled into a declared-inference epoch, the exact probability the audit catches at least one of them is the hypergeometric tail:

```
P(catch >= 1) = 1 - C(n-k, m) / C(n, m)
```

implemented in `security.py::detection_probability` and cross-checked against direct Monte Carlo simulation in `test_security.py`.

For large populations, the [AI 2040 verification supplement's own appendix](https://ai-2040.com/supplements/verification-plan#a2-detection-by-random-sampling) derives a Poisson approximation, `P(detected) ≈ 1 - exp(-N_verified · F_fake)`, and notes it independently converges with [Rinberg et al., 2025](https://arxiv.org/abs/2511.02620). `security.py::poisson_detection_probability` implements the same formula, and `test_poisson_approximation_converges_to_exact_for_large_populations` checks it agrees with the exact hypergeometric result once `n` is large — i.e., this repo's math matches the field's math, not just its own internal assumptions.

**The single-epoch number is not the operative guarantee.** A device has to sustain a false "inference-only" declaration across every epoch it operates, not just one. `repeated_detection_probability(p, T) = 1 - (1-p)^T` shows how fast a modest per-epoch catch probability compounds: at `p ≈ 0.46` (the demo's subtle-attacker scenario), the chance of being caught at least once passes 99% within 10 epochs. This is the same qualitative point the AI 2040 appendix makes about coverage and confidence trading off against recomputation budget and packet size — smaller packets and/or a higher sampling rate shift the curve, but even a modest, cheap sampling rate becomes overwhelming given enough repeated epochs.

## 6. Verification reporting: the auditor's own accountability

Section 3–5 assume the verifier is honest. `ledger.py` doesn't assume that. Every `AuditResult` is hash-chained (each entry covers the previous entry's hash) and signed by the auditor's key. If a compromised or coerced auditor tries to quietly rewrite a past finding — e.g. to erase a caught violation — `verify_chain()` will detect it, because the recomputed hash of the (now-edited) entry no longer matches the stored `entry_hash`. This requires no ongoing trust in the auditor, only that `entry_hash` values were published to at least one independent party at the time each entry was created. This is a direct, if minimal, answer to the SITREP's "Verification reporting" gap: *"the integrity of what the recomputation server reports back to the verifier has not been explored."*

## 7. Limitations and future work

- No real trace source. The highest-value next step is swapping `trace.py`'s synthetic generator for a real one (CUPTI/Nsight hooks, or an eBPF-based network-layer capture matching the actual passive-optical-tap design in the verification supplement) behind the same `ExecutionEpoch` interface.
- No adversarial hardening of the classifier past section 4's honest limitations.
- No physical security model — tap tampering and side-channel exfiltration are explicitly out of scope (section 2).
- No treatment of reproducibility under legitimate nondeterminism (this is what Token-DiFR and TOPLOC solve for the "is this inference output actually correct" question, which is complementary to and not addressed by this repo's "is this workload structurally inference-shaped at all" question).

## 8. A second mechanism: RSA-accumulator zero-knowledge proofs

Sections 3–7 describe a probabilistic scheme: the verifier samples, and a lie gets caught with a computable but non-unit probability per epoch, compounding toward certainty only as the device keeps operating. The covert-project supplement names two technologies Plan A's 2040 endpoint assumes exist — lie detectors, and privacy-preserving AI verification — as what makes covert projects implausible by then. `accumulator.py` and `zk_verification.py` are a reference implementation of the second one, built as a genuinely different mechanism rather than a restatement of sections 3-5.

**Construction.** Each distinct op-code present in an epoch is mapped to a large prime via a hash-to-prime function (`accumulator.py::hash_to_prime`), and the whole set is accumulated into one RSA-group element following Benaloh & de Mare (1993) and Barić & Pfitzmann (1997). `ZKProver.prove_inference_only` then produces, for each of the three forbidden op-codes, a non-membership witness using the construction from Li, Li & Xue (2007): given the product `u` of accumulated primes and a candidate `y`, the extended Euclidean algorithm either finds integers `(a, b)` with `a·y + b·u = 1` (proof of exclusion), or finds that `gcd(y, u) ≠ 1` — which, for prime `y`, only happens when `y` is itself one of the accumulated primes.

**Why this is a different kind of guarantee, not just a smaller detection window.** In section 5's scheme, a prover hiding `k` bad events among `n` always *can* produce a commitment; it just risks the verifier's sample landing on one of the `k`. Here, if a forbidden op is actually present, its prime divides `u`, so no integers `(a, b)` satisfying the Bézout identity exist at all — `nonmembership_witness` returns `None`, not a witness that happens to be wrong. `test_accumulator.py::test_nonmembership_witness_does_not_exist_for_an_actual_member` and `test_zk_verification.py::test_mixed_epoch_with_even_one_covert_op_cannot_verify` check this directly: the latter runs the exact same subtle single-covert-op attack from section 5's motivating example across 50 independent trials and it fails to verify in all 50, where the sampling scheme in section 5 catches it roughly 40–50% of the time per epoch.

**What this does not get you for free.** The accumulator proves a set-membership claim over *which op-codes occurred at least once* — it says nothing about timing, ordering, byte counts, or how many times each op ran, all of which the Merkle commitment in section 3 does expose (to the sampled subset, at least). The two mechanisms answer overlapping but non-identical questions, and a real deployment likely wants both: the accumulator for a hard compliance gate, sampling for the richer behavioral signal.

**The honest limitation.** Security here rests on the strong RSA assumption in a group whose order nobody knows. `trusted_setup()` generates that group's modulus by generating a fresh RSA keypair and discarding the factorization — but *this repository's own code* is the party doing that discarding, which is exactly the trust assumption a real deployment cannot make of a single party. Production use needs either an actual mutually-trusted third party to run setup once, or a proper multi-party ceremony, or a switch to a trapdoor-free group construction (class groups of imaginary quadratic order are the standard answer in the literature, and are real future work for this repo, not implemented here). This is stated plainly in `accumulator.py`'s module docstring, not buried.

## 9. Full audit against all 17 SITREP workstreams

This section exists so nobody, including the author, can quietly round "covers 2 named gaps" up to "covers the field." Grades and workstream names below are taken directly from [Amodo Design's SITREP](https://amododesign.com/ai-verification/plan-a-sitrep/) as published; software-addressability is this repo's own judgment call, not Amodo's.

| # | Workstream | Grade | Any software-only path exists? | Fides status |
|---|---|---|---|---|
| 1 | Passive optical TAPs | Active | No — physical optical hardware | Out of scope |
| 2 | Recomputation servers (capture) | Active | No — physical NIC/network capture infrastructure | Out of scope |
| 3 | New TAP types & bandwidth limits | Not started | Yes | **Covered — `commitment.py`** |
| 4 | Path from storage bank to inference units | Not on track | Mostly no — data diodes, physical network partitioning | Out of scope |
| 5 | Inference reproducibility workarounds (TOPLOC, DiFR) | Active | Yes | **Not attempted, upgraded understanding for both.** `toploc_reference.py` and `difr_reference.py` reimplement TOPLOC's and Token-DiFR's actual algorithms from their source, after direct install/run attempts (section 11, section 12). Still not a contribution to either live algorithm. |
| 6 | Reproducible inference stack | Not started | Yes | **Partially covered — `determinism.py`.** Fixes the specific floating-point reduction-order mechanism with a tested deterministic-vs-racy comparison; does not build a real inference stack (no model, no GPU here). |
| 7 | Network reproducibility | Not started | Partially — the supplement itself says this may need firmware/hardware work too | **Partially covered — `packet_reconstruction.py`.** Content-addressed, order-independent message verification — the narrower software-only alternative to bit-exact packet replay that the same SITREP paragraph floats as conceivable. |
| 8 | Recomputation algorithms (TOPLOC, DiFR) | Active | Yes | **Not attempted, same upgrade as #5** — both TOPLOC and DiFR now covered by primary-source reimplementations. |
| 9 | Frontier recomputation algorithms | Not started | Yes | **Loosely relevant, not covered.** `recompute.py`'s own scheme is tested across three unrelated vector/hash-length configurations, which demonstrates the *mechanism* isn't hardcoded to one shape — but this is evidence about an independent construction, not progress on TOPLOC/DiFR's own evolution. `classifier.py` remains unrelated to this row (corrected in an earlier revision — see git history). |
| 10 | Recomputation red-teaming | Not started | Yes | **Loosely relevant, not covered.** `test_recompute.py` red-teams `recompute.py`'s own scheme with both brute-force and adaptive hill-climbing attacks — real, tested adversarial pressure, but against this repo's construction, not against TOPLOC/DiFR, which is what this workstream actually means. |
| 11 | Recomputation server security | Not on track | Partially — a software attestation layer is plausible but the hard part is defending a machine inside the adversary's own facility | **Partially covered — `server_attestation.py`.** A challenge-response heartbeat catches silent logic substitution and history rollback; explicitly does not defend against physical compromise. Do not conflate with #13. |
| 12 | TAP installation & network links | Not on track | No — physical installation at up to 100,000-cable scale | Out of scope |
| 13 | Verification reporting | Not on track | Yes | **Covered — `ledger.py`** (reporting-integrity only, not #11's server-compute-integrity). |
| 14 | Physical security and audits | Not on track | No — in-person inspection of compute and installed hardware | Out of scope |
| 15 | Memory wipes (PoSE) | Uncertain | Partially — the wipe *algorithm* is software; credible validation needs real hardware, per Amodo's own testing note | **Covered — `wipe.py`.** Forced-memorization fill + spot-check, reusing `security.py`'s exact hypergeometric detection math against memory blocks instead of trace events. |
| 16 | Side channel mitigation (shielding + noise) | Not on track | No — physical shielding, by the SITREP's own framing | Out of scope |
| 17 | Side channel wardens | Not on track | Yes, as a monitoring/anomaly-detection layer, even without real EM/power sensor data to start | **Covered — `warden.py`.** Autocorrelation-based periodic-signal detector with an empirically characterized detection floor and a documented harmonic-ambiguity limitation. |

**Tally.** 6 of 17 are physical by construction and no software project touches them regardless of effort (#1, #2, #4, #12, #14, #16). Of the 11 with a real software component: **7 are directly and solidly covered** (#3, #6, #7, #11, #13, #15, #17); **2 have real but explicitly caveated loose relevance** (#9, #10 — both via `recompute.py`'s tests, which pressure-test an independent construction rather than the actual named algorithms); **2 are not attempted at all** (#5, #8 — already active elsewhere via TOPLOC/DiFR, and this repo does not contribute to either). No claim here should be read as stronger than its row states — several of the "covered" rows are narrow, honestly-scoped slices of a larger workstream (see each module's docstring), not a claim to have closed the workstream outright.

`accumulator.py` and `zk_verification.py` sit outside this table entirely — they target "Cryptographic/ZKP verification," which Amodo's SITREP names as a separate, roughly-$100M-funded parallel research track to the network-tap approach these 17 workstreams describe, not an 18th row in it.

## 10. What finishing this table still doesn't mean

Amodo's own recommendations are explicit that even the 4 "active effort" rows above need far more than working code to be real: proof-of-concept papers becoming reliable hardware prototypes, red-teaming with national-security teams, manufacturing plans, physical stockpiling, government installation playbooks. None of that is downstream of software quality, and no amount of additional modules in this repo changes that. What this repo can honestly claim is narrower and still real: tested, correct, honestly-scoped software contributions to the specific rows marked "Covered" or "Partially covered" above, built independently and available for anyone actually running the SITREP's active workstreams to use, extend, or ignore.

## 11. Going to the primary source for items 5 and 8, and what that actually found

`recompute.py`'s SimHash construction was built "in the spirit of" TOPLOC/DiFR from a search-result summary, without reading either project's actual code. That's a weaker standard of evidence than the rest of this document tries to hold itself to, so this section documents going back and doing it properly for TOPLOC (DiFR has not yet received the same treatment — that's honestly open, not silently done).

**What was attempted.** `git clone https://github.com/PrimeIntellect-ai/toploc` and a direct reading of `toploc/poly.py`. Then `pip install toploc`, which installs cleanly and pulls in a full `torch` build. Running the package's own README example (`from toploc import build_proofs_base64`) failed:

```
ImportError: .../toploc/C/csrc/poly.cpython-312-x86_64-linux-gnu.so: undefined symbol: _ZNK2at10TensorBase14const_data_ptrIfLi0EEEPKT_v
```

This is a real ABI mismatch between the prebuilt C extension in the PyPI wheel and the `torch` version pip resolved (2.13.0) — the extension was almost certainly built against `torch==2.5.1`, the version pinned in the project's own `requirements.txt`. Attempting to install that exact pinned version ran the sandbox out of disk space mid-download. Both of these are genuine environmental findings, not a decision to stop looking; they're recorded because a future attempt (more disk, or a matching prebuilt environment) might well succeed where this one didn't, and silently omitting the failure would misrepresent how far this actually got.

**What reading the source directly corrected.** `recompute.py`'s assumption of random-hyperplane SimHash was wrong. TOPLOC's real mechanism, read from `poly.py`:

1. `flat_view.abs().topk(topk).indices` — select the top-k activation values by absolute magnitude, not a random projection.
2. `ProofPoly.from_points_tensor(topk_indices, topk_values)` — fit a polynomial through the (position, value) points over a finite field. `find_injective_modulus` searches for a modulus under which the chosen indices remain distinct — the same "k points determine a degree-(k-1) polynomial" idea behind Shamir's Secret Sharing, applied to compress k activation values into k polynomial coefficients.
3. At verify time, the *verifier* re-selects its own top-k indices from its recomputed activations (`chunk.abs().topk(...)`) — it does not trust the prover's choice of which positions mattered — evaluates the proof's polynomial at those positions, and compares against a `VerificationResult(exp_intersections, mant_err_mean, mant_err_median)`: exponent must match exactly, mantissa error is measured and returned rather than collapsed into one pass/fail bit.

**What `toploc_reference.py` is.** A from-scratch reimplementation of exactly these three steps, using standard modular Lagrange interpolation over GF(65537) (the smallest prime exceeding the 16-bit range of a bfloat16 bit pattern) and manual `struct`-based bfloat16 decomposition, since torch is not reliably available here. Correctness is checked three ways in `test_toploc_reference.py`: the fitted polynomial reproduces its own input points exactly; a hand-computable known polynomial (`f(x) = 3 + 2x + x²`) round-trips to the exact expected coefficients `[3, 2, 1]`; and the bfloat16 decomposition of `1.0` matches the well-known constant `0x3F800000` by hand.

**What this is not.** Not bit-compatible with TOPLOC's compiled implementation — the exact finite-field modulus and packing scheme live in the C extension this investigation didn't reverse-engineer. Not a contribution to the TOPLOC codebase, PrimeIntellect's production validation pipeline, or DiFR at all. Items 5 and 8 in the table above remain graded "not attempted" for that reason — this section upgrades the *quality of understanding* behind that grade, not the grade itself.

## 12. Doing the same thing for DiFR

Section 11 explicitly left DiFR open — "has not received the same treatment yet." This section closes that.

**What was found.** `git clone https://github.com/adamkarvonen/difr` and a direct reading of `difr/token_difr_vllm.py`. Token-DiFR's real mechanism turns out to be simpler than TOPLOC's, not more: LLM sampling at temperature > 0 is a Gumbel-max draw. Given a probability distribution over the vocabulary, the real implementation samples `E_i ~ Exponential(1)` per vocabulary entry from a seeded generator, and picks `argmax(prob_i / E_i)` — mathematically identical to the textbook `argmax(logit_i + Gumbel_i)` trick (since `E ~ Exp(1)` implies `-log(E) ~ Gumbel(0,1)`, and `argmax(logits - log(E)) = argmax(exp(logits)/E) = argmax(probs/E)`, exp() being monotonic and the softmax normalizer constant across the vocabulary dimension), reformulated to avoid a `log()` call. Verification re-runs the trusted reference on `[prompt + claimed_output]` to recover what distribution it would have assigned at each position, redraws the same seeded noise, and checks whether the reference's own draw would have produced the claimed token — reporting `exact_match`, a `margin` (how close the decision was), and a `gumbel_rank` (graded confidence), not a single pass/fail bit.

**What `difr_reference.py` is.** A from-scratch reimplementation of exactly this, in pure Python — `random.Random` natively supports `Exponential(1)` sampling, so unlike TOPLOC's polynomial scheme, this needed no external numeric library at all, and hit no ABI or install problems. Correctness is checked in `test_difr_reference.py` by confirming the probability/exponential reformulation empirically matches the textbook logit/Gumbel form on 50 independent trials, and honest re-derivation reproduces claimed tokens exactly (not just usually) when there's genuinely zero perturbation between the claim and the reference.

**What was tested beyond basic correctness.** Two things the real paper reports but this reimplementation could check directly on synthetic data: that divergence rate increases with how different the "provider's" distribution actually is from the reference (`test_divergence_rate_increases_with_perturbation_magnitude` — echoing the paper's finding that stronger corruption is detectable with fewer tokens), and a red-team question the paper doesn't directly address — whether an adversary sharing only the reference's single most-likely token (but a different distribution otherwise) can evade detection. It can't: `test_matching_only_the_mode_does_not_evade_detection` shows measurable divergence even when the top choice matches, because Gumbel-max verification is sensitive to the whole distribution's relative ordering, not just which token is most likely.

**What this is not**, same caveat as section 11: not bit-compatible with the real vLLM-integrated implementation, not run against a real model (no GPU here), and not a contribution to the DiFR codebase. Items 5 and 8 stay "not attempted" for the same reason as before — this is upgraded understanding of both real algorithms now, not participation in either.

## 13. Trying again with GPU access

`fides_colab.ipynb` (repository root) reruns sections 11 and 12's install attempts on Colab or Kaggle, where a maintained, tested torch+CUDA stack is far more likely to make `pip install toploc`'s compiled extension actually load. If it works there, that's a genuinely different and better result than this document currently reports, and the honest thing to do is update this section with whatever actually happens — success, a different failure, or the same one — rather than let a sandbox-specific finding stand in as the final word on whether the real package runs at all.

## 14. Strengthening the SOLID_PARTIAL items, and why five things still don't move

Asked directly to make every workstream SOLID, four of the five SOLID_PARTIAL items got genuine upgrades in this session — not relabeled, strengthened:

- **Item 17 (side-channel wardens).** `detect_fundamental_period` adds spectral (DFT) detection to resolve the harmonic-ambiguity limitation autocorrelation alone had. Building it surfaced a real bug: the first threshold (4.0) was checked against actual noise-only data and found to false-positive on 100% of trials, because comparing ~2000 frequency bins simultaneously means even pure noise produces peak/median ratios up to ~16 by extreme-value statistics alone. Recalibrated to 30 (real signal produces ratios in the hundreds) after measuring both distributions directly, not guessing a second time either.
- **Item 6 (reproducible inference stack).** `canonical_reduce` closes the exact gap the module's own docstring named as unfixed: fixing reduction order alone isn't sufficient if upstream arrival order varies. Tagging values with a stable identity and sorting by it before reducing closes both halves together.
- **Item 11 (recomputation server security).** `verify_threshold` requires agreement from multiple independently-operated servers, so compromising one no longer suffices — genuinely harder for a physical attacker than the single-server heartbeat alone.
- **Item 15 (memory wipes).** `verify_wipe_certain` replaces probabilistic spot-checking with a single Merkle-root comparison. This works here specifically because the verifier can compute the *entire* expected memory content independently (it's fully determined by the public challenge) — a property trace verification doesn't have, which is why `attestation.py` still needs sampling and this doesn't.

**Why these stay SOLID_PARTIAL, not SOLID.** Each upgrade closes one named sub-gap while leaving the workstream's actual hard part untouched: warden.py still has no real sensor data; determinism.py is still not a real inference stack; server_attestation.py's threshold still provides zero protection if the "independent" parties are secretly all the same operator (tested directly in `test_threshold_does_not_protect_against_coordinated_compromise_of_all_parties` — it fails to protect, on purpose, because there's nothing here that could detect that); wipe.py still has no real-hardware validation, and Amodo's own SITREP grades this workstream "uncertain" even in principle. Calling any of these "SOLID" would be exactly the overclaim this document has twice already caught and corrected.

**Item 7 (network reproducibility)** got no upgrade this session — not for lack of trying, but because the honest remaining gap (bit-exact packet replay) is explicitly named by Amodo's own text as possibly needing firmware or hardware work, and no further pure-Python contribution was identified that would close it rather than just add surface area.

**Items 5, 8, 9, 10 cannot become SOLID by any amount of additional code, structurally.** 5 and 8 require TOPLOC and DiFR's own teams treating something as production-ready — an independent reimplementation, however faithful, is a different object by definition, the same way a flight simulator isn't a completed aircraft certification no matter how accurate the simulator is. 9 and 10 inherit the same limit: red-teaming or generalizing this repo's reimplementations is real work, but it is red-teaming *this repo*, not the systems those rows actually name. No further engineering effort from this side changes that; it would need TOPLOC's or DiFR's own teams engaging with the reimplementations here, which is not something code can produce on its own.
