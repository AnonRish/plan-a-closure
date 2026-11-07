# Toward Real Recomputation

`frontier_verify/recomputation/` (Phases 2-3) has real, tested sampling
unpredictability and comparison logic -- entirely over a toy deterministic
function on opaque digests. This document is explicit about the distance
between that and actual ML workload recomputation, and lays out the
staged path section 18 of the Phase 3 brief asks for. Nothing in this
document is implemented; it is a map, not a milestone.

## Why real recomputation is hard, specifically

- **Floating-point nondeterminism**: the same model, same input, same
  weights can produce bit-different outputs across different hardware,
  different batch compositions, different kernel implementations, or even
  different runs on identical hardware, depending on reduction order in
  parallel operations. Exact digest matching (this project's current
  comparison method) would flag every one of these as a "mismatch" --
  false positives at a rate that would make the whole mechanism useless.
- **RNG state**: sampling-based generation depends on random state that
  must be captured and replayed exactly, or "recomputation" trivially
  diverges for reasons having nothing to do with honesty.
- **Distributed execution and communication ordering**: multi-GPU/multi-
  node inference has ordering-dependent floating-point accumulation
  (all-reduce operations aren't strictly associative in floating point) --
  the same logical computation can legitimately produce different bits
  depending on scheduling that isn't a violation of anything.
- **Checkpointing and intermediate commitments**: for recomputation to be
  cheaper than full re-inference, it needs to restart from some
  intermediate state, not the beginning -- which requires the ORIGINAL
  execution to have produced checkpoints in the first place, adding real
  overhead to the very system being verified.

## A staged roadmap, each stage with its own honest requirements

| Stage | Workload | Hardware | Reproducibility requirement | Expected overhead | Open problem at this stage |
|---|---|---|---|---|---|
| 0 (done) | Toy deterministic function over digests | None | Exact match | Negligible | None -- deliberately not real |
| 1 | Small neural network, single forward pass, fixed seed | CPU or single GPU | Exact match achievable with fixed seeds and deterministic kernel flags | Low -- small model | Establishing whether "deterministic mode" flags (available in most frameworks) hold up under sampling-based re-execution, not just re-running the same process |
| 2 | Single-GPU inference, realistic model size | Single GPU, deterministic kernels | Exact or tight-tolerance match | Real GPU-time cost, still bounded | Numerical tolerance window design (see attack #7 in `docs/adversarial-results.md`) -- how loose can matching be before it stops catching real fabrication? |
| 3 | Multi-GPU inference, single node | Multi-GPU, NVLink/similar | Tolerance-based match, wider than stage 2 | Meaningfully higher -- multiple GPUs' worth of recomputation | Non-associative floating-point reduction across GPUs -- may need architecture-aware tolerance, not a single global constant |
| 4 | Distributed inference, multi-node | Multi-node cluster | Tolerance-based, likely widest | High -- network + multi-node compute | Communication ordering nondeterminism; checkpoint/restart design so recomputation doesn't require replaying the entire distributed execution from scratch |
| 5 | Sampled frontier-scale workload verification | Frontier-scale cluster | Statistical, not exact -- confidence intervals over sampled chunks, not per-chunk certainty | The genuinely open economic question: is ANY sampling rate that catches fabrication with useful confidence still cheap enough to be worth running | Everything above, plus the economic/game-theoretic question `docs/research/recomputation.md` already names as unsolved by commit-reveal alone |

**Do not skip stages** -- per the brief's own instruction. Stage 2's
tolerance-window design directly informs stage 3's wider tolerance;
skipping to stage 5 without stages 1-4 having established what "tolerance"
even means for this project's specific comparison logic would mean
inventing a number with no empirical basis, which is worse than not
having one.

## What would need to change in this project's code at each stage

- **Comparison logic** (`frontier_verify/recomputation/experiment.py`):
  currently `matched=(recomputed == chunk.claimed_output_digest)`, exact
  equality. Stage 2+ needs a tolerance-aware comparison, which changes
  `MismatchResult`'s meaning from a boolean to something that can express
  "matched within tolerance T" -- a real schema change, not a parameter
  tweak.
- **`WorkloadChunk`**: currently `input_digest`/`claimed_output_digest`
  as opaque strings. Real workloads need actual tensor/activation
  references, likely via `ContentAddressedStore` extended to handle
  binary (not just JSON-dict) content -- noted as a gap in
  `docs/research/recomputation.md`, not fixed there either.
- **`recompute_fn`**: currently caller-supplied and toy. Stage 1+ needs
  this to be a real model-serving call, with all the checkpoint/restart
  machinery stage 4 requires eventually built around it.

None of this is built. This document exists so the next person who picks
up this workstream has a map instead of a blank page.
