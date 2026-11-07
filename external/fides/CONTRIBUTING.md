# Contributing

Fides is a software-only testbed built by one person with no GPU or datacenter access. It's honestly scoped on purpose — see `spec/PROTOCOL.md` section 9 for a full audit of what it does and doesn't cover against the AI 2040 Plan A verification SITREP. Contributions that extend real coverage are more valuable than contributions that make existing claims sound bigger.

## Where help is most useful right now

- **A real trace source.** `trace.py` simulates kernel-level events. Swapping in CUPTI/Nsight hooks, or an eBPF-based network capture matching the passive-optical-tap design in the verification supplement, behind the same `ExecutionEpoch` interface is the highest-value single contribution.
- **Running `toploc_reference.py` and `difr_reference.py` against real model activations.** Both were built by reading TOPLOC's and Token-DiFR's source directly, but neither has been validated against a real model — no GPU in the original environment. `fides_colab.ipynb` is a starting point for anyone with GPU access to close that loop.
- **DiFR's Activation-DiFR variant.** Only Token-DiFR (the seed-synchronized Gumbel-max scheme) got the primary-source treatment. The paper also describes an activation-based variant with lower communication overhead that hasn't been examined at the same depth.
- **Adversarial hardening of `classifier.py`.** The Compute Verification Project (contact via the AI 2040 verification get-involved page) is running an open competition on structurally distinguishing inference from training via communication patterns — that's the actual state of the art on this question, not this repo.
- **A trapdoor-free accumulator.** `accumulator.py`'s RSA construction needs a trusted third party or an MPC ceremony for `trusted_setup()` in any real deployment. Class-group constructions avoid this; implementing one correctly is real, valuable, and harder than anything else in this repo.
- **Physical-layer work this repo cannot do at all.** Passive optical taps, tap installation, physical security and audits, and side-channel shielding are permanently out of software's reach — if you have hardware access, that's where the SITREP's actual bottleneck is, not more Python.

## Ground rules

1. **Test everything.** Every module in this repo has tests that were actually run, not just written — `pytest tests/ -v` should stay green, and CI (`.github/workflows/tests.yml`) enforces this on every PR.
2. **Cite what you're building against.** If a module claims to relate to a SITREP row, a paper, or another project's algorithm, link the specific source and be precise about what's faithfully reimplemented versus independently constructed. Section 11 of `spec/PROTOCOL.md` is the model to follow: what was actually read, what actually ran, what actually failed.
3. **Don't round up.** "Loosely relevant" and "directly covered" are different claims — this repo's own history includes two overclaims that got caught and corrected before or shortly after being committed (see git log). If you're not sure which category new work falls into, say so explicitly rather than picking the more flattering one.
4. **Simulated data should say so.** If a test uses synthetic activations, traces, or telemetry instead of something real, the module docstring should make that unambiguous.

## Getting started

```bash
git clone <this-repo>
cd fides
pip install -e ".[dev]"
pytest tests/ -v
python examples/demo.py
```

Issues and PRs welcome. If you're specifically working on AI 2040 Plan A verification and want to compare notes, the [get-involved page](https://ai-2040.com/supplements/verification-plan/get-involved) has an expression-of-interest form connecting people to funders, collaborators, and companies (Amodo Design, Lucid Computing) actively hiring for exactly this kind of work.
