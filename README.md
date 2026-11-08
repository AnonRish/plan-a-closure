# plan-a-closure

[![ci](https://github.com/AnonRish/plan-a-closure/actions/workflows/ci.yml/badge.svg)](https://github.com/AnonRish/plan-a-closure/actions/workflows/ci.yml)
(tests, re-derived claims, coverage, vendored-tree check and the Tier 0 pilot on a simulated GPU, Python 3.10 to 3.13, every push)

**Compute material-balance accounting for inference-only AI verification (AI 2040 "Plan A").**
Every joule, packet byte and byte of memory on an enrolled cluster must be *explained* by verified work.
What is left over (the residual) upper-bounds hidden compute, hidden exfiltration and hidden persistent state.

> **Status: v0.6.0, simulation-tested, hardware-gated.** Estimators, evidence format and orchestration are tested
> (273 tests, `pytest`, plus 21 that run the torch code on CPU where torch is installed, 9 of them rehearsing the
> whole GPU path against a fake NVML and nvidia-smi). The 13 vendored repositories
> under `external/` add their own suites (2,708 tests passed here, `closure external test`). **No physical claim is
> demonstrated yet.** The first run on real hardware, a Colab T4 shakedown on 8 November 2026, stopped at
> `hw-selftest` because the unit of work was sized for an H100; that is fixed in 0.5.5, and the run, its bundle and a
> model that reproduces the failure are in [docs/DEVIATIONS.md](docs/DEVIATIONS.md). Each claim is decided by the
> pre-registered trial in
> [docs/PREREGISTRATION.md](docs/PREREGISTRATION.md) on instrumented hardware (Amodo's Side Channel Cloud, the
> Verifiable Compute Foundation cluster). A report whose status says `SIMULATED` validates the estimators only. The
> one-GPU pilot is one unattended command, `closure tier0` ([operator guide](docs/OPERATOR_TIER0.md)).
> Without an H100, [notebooks/tier0_colab.ipynb](notebooks/tier0_colab.ipynb)
> ([open in Colab](https://colab.research.google.com/github/AnonRish/plan-a-closure/blob/main/notebooks/tier0_colab.ipynb))
> runs the same pilot on a free Colab GPU as a labelled shakedown (no independent meter, so not the registered trial).

## The gap this targets

Plan A's inference-only retrofit checks *correctness* with passive taps and partial recomputation. For *completeness*
the plan says it does not verify that spare compute is unused; it relies on side-channel mitigation and periodic
memory wipes. The Get Involved SITREP rates side-channel work "not on track". Workload classifiers built on physical or
telemetry signals are signature-based. Gargiulo and Kulp (arXiv 2609.00309, measured on an H200 NVL hosted by Amodo Design
with an AC-coupled current probe) reach 97% accuracy, with diluted LoRA the hardest evasion case. Rahman and Tajdari
(arXiv 2606.19262) classify from 1 Hz NVML telemetry at 98% accuracy, assume the counters cannot be tampered with, and
find white-box LoRA the hardest case (42.6% detection). Kimpson, Baker and Graham (arXiv 2610.07476) bound hidden compute
from power analytically: on an A100 a matched-energy attack (declared work on cheap operands, the saved energy spent on
covert int8 work) hides at least 0.41 of capacity, and only re-execution at an observed clock plus further restrictions
bring the bound down to 0.059. Closure's slack-inflated gap plays the same role, measured rather than derived, which is
why the probe sweeps operand cost and int8/fp8. Closure is **signature-independent accounting**: whatever hidden work does, it costs joules,
busy-time, bytes or memory, and the verifier asks whether those are fully explained. It does not classify: it bounds
unexplained energy against a calibrated model of verified work, converts it to FLOPs with a measured energy floor, and needs
an independent *absolute-power* meter, because NVML can be spoofed (a point Gargiulo and Kulp also make) and an AC-coupled
probe carries no energy.

It is not a classifier, not a defence against hardware tampering or a colluding meter, and not a replacement for
tap-and-recompute. Its known blind spot (efficiency slack: an energy-neutral adversary) is *measured and reported*.

## What is in the box

| closure | question | method | module |
| --- | --- | --- | --- |
| energy / busy-time | is all energy and GPU time explained by verified work? | cross-fitted NNLS model, block-summed residuals per load regime, predictive thresholds with effective sample size, upper bound on hidden energy | `residual.py`, `trial.py` |
| traffic | is every payload byte on the tap explained by a verified exchange? | flow byte accounting from a streamed pcap (IPv4 and IPv6), unknown-flow and tap-loss detection, frames it cannot attribute counted as unexplained, release-grid capacity bound | `traffic.py` |
| state | does device memory hold only the verifier's stream? | AES-CTR stream, keyed digest challenges, bandwidth-bounded timing; honest, dropping and host-parking provers | `state.py` |
| evidence | can a stranger check what was run and when? | hash chain, Ed25519 signature, preregistration, commit-reveal of the breaker's schedule | `evidence.py` |
| independent meter | can the prover's own NVML be cross-checked? | absolute-power CSV import (AC-coupled traces are rejected), unit conversion, constant-memory decimation of very large traces, clock alignment, re-analysis of the same run | `dcbus.py` |
| efficiency slack and energy floor | does an allowed stack, clock or power cap, numerics choice, or cheap input data leave energy-neutral room for hidden work? what is the lowest joules per FLOP? | duty-cycled windows at fixed work rates, one-sided 95% upper saving of allowed stack variants (`s_stack`) and activation patterns (`s_operand`), dynamic J/FLOP floor with int8 and fp8, the declared-work band, sealed `probe.json` bound into the pre-registration | `hw/probe.py` |
| one-command pilot | can an operator run Tier 0 alone, without a meeting, and get the GPU back as it was? | `closure tier0`: every step logged with its command and exit status, `SUMMARY.md`, a bundle that leaves out the private key; the GPU matched across CUDA and NVML by UUID; clocks and power limit restored on exit, on SIGTERM and by a final `hw-restore` step; the whole hardware path rehearsed in CI against a fake NVML and nvidia-smi | `tier0.py` `hw/gpu.py` |

## The rest of the software-addressable plan

Closure covers one leg (completeness). The other modules implement or re-derive the software-checkable parts of the
Verification Plan, so each claim in it can be run, not just read.

| module | Plan A element | command |
| --- | --- | --- |
| `claims.py` | re-derives 56 numeric claims (Appendix A packet math, the Jan 2029 declaration, retrofit arithmetic, 2030s trajectory) | `closure claims` |
| `ledger.py` | chip-stock accounting with uncertainty, declaration reconciliation, audit sampling, size-bucket interventions, chip tiers | |
| `retrofit.py` | rollout arithmetic: 40% in month 1, 80% by month 3 | `closure retrofit` |
| `assurance.py` | assurance curve, packet-granularity schedule, composition of layers with independent and correlated bounds | `closure assurance` |
| `repro.py` | batch-invariance and recomputation-tolerance harness, substitution detection curve | `closure repro-check` |
| `approval.py` | white / black / gold lists, compute caps, titration stages | |
| `captrade.py` | permit ledger under a doubling cap, edge-compute cap, ZDR fleet caps | |
| `gateway.py` | secure network gateway (the plan's gateway upgrade; RFD 017's SNG and SRC): boot whitelist, hash-chained I/O log, keyed sampling committed before serving, recomputation within a conformal tolerance, and a red team of substituted models and tampered outputs | `closure redteam` |
| `taphash.py` | hashing taps (SITREP 3): group digests with position-bound Merkle leaves, openings, nonce-derived challenges, exact detection probability, 2048x less tap output at 64 KiB groups | `closure tap-commit`, `closure tap-compare` |
| `tapwatch.py` | tap presence (SITREP 12): keyed canaries at unpredictable times with ciphertext-like payloads; a removed or bypassed tap is caught within one gap | |
| `cadence.py` | defence-in-depth training-cadence detector (hardwired pause 3.3.3), threshold calibrated on null traces, refuses traces below 2 Hz | `closure cadence-check` |
| `metrics.py` | the plan's evaluation metrics (assurance curve, execution difficulty, preparation, privacy, economic cost, scope) as checked scorecards; only the assurance curve is a formula, the rest are judgments with a stated basis | `closure metrics` |
| `frontier.py` | recomputation rules for newer architectures (SITREP 9): mixture-of-experts routing near-ties, speculative decoding checked against the target model with a committed sampling seed (toy models) | |
| `external.py` | the 13 vendored AnonRish repositories: tree hashes, provenance, and each one's own test suite in its own process | `closure external` |

Findings from re-deriving the plan's numbers: 52 of 56 reproduce. Three hold only under a stated reading: the
"~99% of world AI-relevant compute" retrofit coverage is 98.8% of datacenter compute but 86.5% of the 289M total;
the 100B ZDR fleet cap exceeds the 60B 2034 world-compute figure; Appendix A.4.2 says 100B H100e while its figure uses
~33B, though the bound does not depend on pool size. One is inconsistent: the 2028 "uncertainty" is 2% for the US and
4% for China, which matches the full interval width for one and the half-width for the other.

## Treaty mechanisms (`closure treaty`)

The halt and treaty proposals (ControlAI's *A Narrow Path* and Direct Institutional Plan, the middle-powers paper at
asi-prevention.com, MIRI's *Mechanisms to Verify International Agreements* and *AI Governance to Avoid Extinction*,
Barnett and Thiergart on what evaluations can and cannot do, and CBPAI's *Deal of the Century*) rest on verification
this repository builds. [docs/TREATY_COVERAGE.md](docs/TREATY_COVERAGE.md) maps every mechanism they name to code, to a
GPU or cluster step, or to "not code", and states what the computations show.

| module | what it makes concrete | command |
| --- | --- | --- |
| `treaty/thresholds.py` | the named compute thresholds (1e25 FLOP and 1e17 FLOP/s licences, a 1e26 draft) and the days a fleet needs to run a threshold-sized covert run at the hidden rate a trial measured | `closure treaty covert-days` |
| `treaty/deterrence.py` | when detection deters: per-period and winner-take-all conditions, and a CUSUM over block residuals against the time to a threshold run, each checked by simulation | `closure treaty deterrence`, `race` |
| `treaty/coalition.py` | the middle-powers agreement: activation at 20% of world GDP and population (World Bank data), smallest coalitions, Shapley-Shubik power, the redline ladder with its persistence and leak rules | `closure treaty coalition`, `redlines` |
| `treaty/mockrun.py` | A Narrow Path's mock training run: a provider that sees only an energy meter stops a training job at its FLOP budget, and the job's starting weights are checked against its seed | `closure treaty mock-run` |
| `treaty/geoloc.py` | delay-based chip location: timed, signed challenges from landmarks bound how far a chip can be from its declared site | `closure treaty geo-landmark`, `geo-chip`, `geo-check` |
| `treaty/inspection.py`, `beacon.py`, `quorum.py` | inspection samples nobody can predict, lot-selected witnesses, and k-of-n approval of critical actions | `closure treaty inspect-plan`, `beacon-commit`, `sortition`, `quorum-verify` |

## Plan A coverage (checked against the pasted documents and the live pages)

`docs/PLAN_A_COVERAGE.md` maps 79 requirements from the Verification Plan and its Get Involved page (every phase, all
17 SITREP workstreams, the four tracks, the open problems) to code and tests in this archive, including the vendored
repositories under `external/`. `closure coverage` fails if a row points at code or a test that does not exist, and
`closure external check` fails if a vendored test that a row cites did not pass in the recorded run. On 6 November 2026
the SITREP statuses and open problems still matched the live Get Involved page (last updated 9 July 2026).

| status | rows |
| --- | --- |
| implemented (code and tests here) | 27 |
| hardware-gated (code here, needs a cluster) | 22 |
| partial | 11 |
| physical (outside software) | 12 |
| policy (outside software) | 7 |

All 60 software-addressable rows have code and tests in the archive; none points only at another repository and none is
unstarted. That is not completion. Nothing physical, diplomatic or manufacturing is counted as covered, 22 of the 60 still
need a real cluster, and 11 are partial, each with a note saying what is missing: zero-knowledge proofs of the computation
itself, a soundness proof for composed trust roots, verification of arbitrary training, compiling approved workloads to GPU
instructions, AI-assisted data filtering, formal verification, measured physical emanations, bit-reproducible packets from
the NIC (firmware), production architectures for the new recomputation rules, and the intelligence and sensing side of
finding covert compute.

## Vendored repositories (`external/`)

The other AnonRish repositories that cover parts of the plan are in the archive, each with its own code, tests, README
and licence ([external/README.md](external/README.md)). `external/MANIFEST.json` pins each tree by hash and records its
source commit, every change made when vendoring it, and its own test suite's result as run here. `closure external
check` fails if a vendored tree changed after it was tested, or if a test that a coverage row cites did not pass.

| repository | commit | own tests here (passed / skipped) | coverage rows that use it |
| --- | --- | --- | --- |
| ai-2040-plan-a-toolkit | `4b18af09b0a1` | 282 / 0 | VP-IO.3, GI-OP.4 |
| ai-2040-verification | `0199a4bd0411` | 4 / 0 | VP-1.3, VP-IO.7, VP-IO.8b, VP-2.12, VP-3.8, GI-WS-05, GI-WS-08, GI-WS-10, GI-T4, GI-OP.2, GI-OP.3, GI-OP.4, HP-3.3.4e |
| aisecurity-rfds | `00d44ecc5095` | 1443 / 68 | VP-2.12 |
| assurance-curves | `17cf95003a99` | 112 / 0 | VP-IO.4, VP-3.6, VP-A.2 |
| compute-ledger | `2e962e09b5d9` | 87 / 0 | VP-0.3, VP-1.1, VP-2.3, GI-T3 |
| continental-load-registry | `ad3292b47a76` | 84 / 0 | VP-0.3, VP-1.1, VP-3.8, GI-T3, HP-3.3.4e |
| covert-timing-warden | `b27c17c317cc` | 115 / 0 | VP-IO.6b, VP-2.12, GI-WS-16, GI-WS-17, GI-OP.2 |
| cuda-guard | `c16cba4bebba` | 41 / 0 | GI-WS-11, GI-OP.5, GI-OP.6, HP-3.3.2b, HP-3.3.3f |
| fides | `076cd765eaca` | 121 / 0 | VP-0.2, VP-1.3, VP-IO.2b, VP-IO.3, VP-IO.4, VP-IO.8b, GI-WS-02, GI-WS-03, GI-WS-05, GI-WS-07, GI-WS-08, GI-WS-11, GI-T2, GI-OP.3, GI-OP.5, HP-3.3.3f |
| frontier-verify | `3e6e0dbcb9b7` | 131 / 4 | VP-0.2, GI-WS-02, GI-WS-11, GI-WS-13 |
| packet-forge | `3d41d9a4bc16` | 86 / 0 | GI-WS-07, GI-OP.1 |
| tap-logger-rtl | `b04264d183ec` | 44 / 0 | GI-WS-03, GI-WS-12 |
| weight-diode | `f305a745e606` | 158 / 0 | VP-2.14, GI-WS-04 |

Recorded on 6 November 2026 (Python 3.13, Linux x86_64, CPU torch, with Icarus Verilog, Verilator, yosys, tshark and
tcpdump installed): 2,708 passed, 72 skipped, none failed. 68 of the skips are aisecurity-rfds placeholders for RFDs it
has not started; the other 4 are frontier-verify tests that need an NVIDIA GPU in confidential-computing mode. Every one
of the 34 vendored tests that a coverage row cites passed.

## The hardwired-pause layer

`src/closure/pause/` makes the quantitative parts of the working paper "The Feasibility of a Hardwired Pause of Frontier AI
Training" (Working Group on AI Pause Feasibility, Berkeley; checked against v1.0.1, October 2026; v1.0.2 followed on
26 October 2026 and has not been re-checked) executable: treaty thresholds, covert-evasion
and overt-breakout ledgers, the chip-census estimator, fab mass balance, a model whitelist, a screen for inference-only chip
designs, transition timing, chip economics, and the game-theoretic conditions for a stable pause. The guide is
[docs/HARDWIRED_PAUSE.md](docs/HARDWIRED_PAUSE.md); [docs/HARDWIRED_PAUSE_COVERAGE.md](docs/HARDWIRED_PAUSE_COVERAGE.md) maps
its 75 requirements to code, tests and repositories.

- `closure pause claims` re-derives 114 numbers the paper prints: 111 reproduce at its printed precision and 3 hold only under
  a stated reading; none are inconsistent. The readings are in the guide (one of them: the paper reads headroom line by line,
  while its ledger is a sum, and the two differ by up to about 0.4 orders of magnitude).
- The model is cross-checked against the authors' public code (`scripts/crosscheck_upstream.py`, not vendored): all 12 cells of
  their chip-economics figure are identical, and the fleet thresholds and census totals agree with their notebook. Re-run on
  6 November 2026 against their current repositories (the calculations supplement last changed on 10 October 2026): all agree.
- Telemetry-based workload classification (3.3.3) is here only as defence in depth (`cadence.py`), never as a bound.
- `bridge.py` turns a closure trial's measured detection gap into a ledger line for transitional inference service, replacing an
  assumed covert discount with a measured one on the audited share of a fleet. It is descriptive, not pre-registered, and only as
  good as the trial behind it.

Items that are inspections, seals, treaties or chip manufacturing are marked `policy` or `physical` and are not counted as
covered. `gemm_audit.py` is a design-time screen, not the physical audit the paper requires.

## Claim chain (what a HARDWARE report says)

1. Calibrate `energy ≈ θ · features(verified work)`, `θ ≥ 0`, cross-fitted over blocks of `L` windows.
2. Null residual sums per load regime; flag a block if its sum exceeds a predictive threshold computed with the
   *effective* number of independent calibration blocks (autocorrelation-corrected).
3. Hidden-energy upper bound per block: `H_ub = max(0, S − q_low)`.
4. Hidden FLOPs `≤ H_ub / e_floor`, where `e_floor` is the **measured** lowest dynamic J/FLOP of the chip (`closure hw-probe`).
   Until it is measured the report labels it `unmeasured-default`.
5. Add the measured efficiency slack of the allowed software stacks and of cheap input data: the report's **slack-inflated
   gap** (`hw-probe`, bound with `--probe`). If slack is not measured the report says so, and the bound is void against an
   energy-saving operator.

## Quickstart

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[test]"                # Python 3.10 or newer
pytest                                  # 273 tests (294 with torch installed)
closure selftest                        # end-to-end simulated trial, PASS/FAIL
closure tier0 --mock --out runs/tier0   # the whole one-GPU pilot on fake hardware: logs, SUMMARY.md, bundle
closure redteam                         # gateway sampling + recomputation against substituted models (toy model)
closure pause claims                    # the hardwired-pause paper's numbers, re-derived
closure metrics                         # the plan's evaluation metrics, scored per mechanism
closure external check                  # vendored repositories: trees match external/MANIFEST.json
pip install -e ".[hw,external]" && closure external test --install   # their own suites (external/README.md)
closure sim-trial --out runs/sim        # writes results.md, chain.jsonl, signature.json, prereg.json, raw.npz
closure verify runs/sim                 # chain, signature, commitment, prereg and results hashes
closure hw-probe --mock --out runs/probe.json                  # efficiency slack and energy floor on a fake rig
closure sim-trial --out runs/sim2 --probe runs/probe.json      # binds the probe into the pre-registration and the report
python scripts/sim_study.py 10          # the 10-seed simulation study (docs/SIM_STUDY.md)
```

On hardware: [docs/RUNBOOK_HARDWARE.md](docs/RUNBOOK_HARDWARE.md).

## Demonstrated, gated, speculative

**Demonstrated here (sandbox, no GPU).** Exact Student-t quantiles match published tables; conformal quantiles are
finite-sample valid in Monte Carlo; Clopper-Pearson bounds are exact. In a 10-seed simulation study
([docs/SIM_STUDY.md](docs/SIM_STUDY.md)): combined null false-positive rate averaged 0.19% (nominal 0.1%, max 0.53%),
non-slack hidden-energy bound coverage averaged 99.98%, and the energy-neutral `slack` adversary evades as designed
(coverage 36-47%). Tampering with a chain, signature, prereg or results file is detected. The hardware pipeline runs
end to end on a virtual-clock fake GPU, and the probe's control flow runs on a virtual clock and a fake rig. The torch
digest arithmetic equals the reference. `closure tier0 --mock` runs every pilot step, verifies the chain and bundles the
run without the private key. The torch code itself (the probe rig with its activation-pattern, int8 and fp8 variants, the
load generator, the residency prover and the reproducibility check) runs on CPU torch 2.15 in `tests/test_torch_cpu.py`,
which checks its API use, dtypes and shapes; int8 ran through `torch._int_mm` and fp8 through `torch._scaled_mm` there.

**Hardware-gated (not yet demonstrated).** NVML energy-counter quality; DC-bus clock alignment; energy-model fit and
residual noise on a real H200; the closure gap; the J/FLOP floor and the efficiency slack (`hw-probe` on a device:
CUDA timing, clock locking and power capping are untested); `TorchLoad`, `TorchProver` and `TorchRig` on a GPU;
HBM-versus-host timing separation; TAP capture; the independent meter; the gateway, hashing tap and canaries on real
network hardware; the cadence detector on real telemetry.

**Speculative.** That any of this is accepted as a Plan A completeness argument. Acceptance is earned by
pre-registered, adversarial, independently replicated hardware results, and is not something this repository can
promise.

## Assumptions and known failure modes (a failed assumption voids the claim)

- **A1 additivity**, **A2 exchangeability** (same stack, clocks, cooling, firmware), **A3 approximate normality**
  (Jarque-Bera diagnostic stored), **A4 no efficiency slack** (stack and operand slack measured by `hw-probe` and charged as
  the slack-inflated gap; unmeasured slack voids the bound), **A5 trustworthy verified-work features**, **A6 meter independent of the prover and
  absolute** (DC-coupled and calibrated; NVML-only runs are labelled spoofable, and AC-coupled traces are rejected).
- Time-correlated drift shrinks the effective calibration size; results are flagged `underpowered` below 15
  effective blocks per regime. Collect long reference runs.
- Hidden work that uses spare time still costs joules; that is why regimes are calibrated separately (idle-gap class).
- The synthetic workload is a proxy. T1b repeats the trial with a served model and tap-derived token counts.
- Traffic closure bounds *unexplained bytes*; modulation inside explained bytes needs a release-grid warden.
- State closure covers only the memories it fills (device, host). Persistent storage needs the weight-diode path.

## Evidence format and the breaker's role

A run directory holds `prereg.json` (config, code version and source hash, schedule commitment, probe hash), `chain.jsonl`
(calibration, prereg, audit-data digests, results), `signature.json` (Ed25519 over the chain head), `schedule_reveal.json`,
`raw.npz`, `results.json`, `results.md` and, when `--probe` is used, the sealed `probe.json`. The breaker commits `sha256({"nonce", "schedule"})` before the audit. The
schedule is a list of `null` or `{"kind": constant|idle_gap|duty|dilute, "frac": 0.01..0.2}` per block. The
verifier never sees it until analysis. Use `--pause-after-prereg` to timestamp `prereg.json` externally
(e.g. `ots stamp`) before any audit data exist.

## Layout

`src/closure/`: closure core (`conformal.py` `residual.py` `energy.py` `sim.py` `trial.py` `compose.py` `traffic.py`
`state.py` `evidence.py` `dcbus.py` `tier0.py` `cli.py`), Plan A modules (`claims.py` `ledger.py` `retrofit.py` `assurance.py` `repro.py`
`gateway.py` `taphash.py` `tapwatch.py` `cadence.py` `metrics.py` `frontier.py`
`approval.py` `captrade.py` `coverage.py` `external.py`), `hw/` (`nvml.py` `workloads.py` `source.py` `probe.py` `gpu.py`) and `pause/` (`thresholds.py`
`treaty_ledger.py` `census.py` `inference_only.py` `gemm_audit.py` `fab.py` `whitelist.py` `registry.py` `supply_chain.py` `transition.py`
`msic_econ.py` `pausegame.py` `bridge.py` `paper_claims.py` `coverage.py` `cli.py`). `tests/`, `scripts/` (`sim_study.py`,
`crosscheck_upstream.py`), `docs/` (`HARDWARE_CONFIG.md`, `OPERATOR_TIER0.md`, `PREREGISTRATION.md`, `RUNBOOK_HARDWARE.md`, `PLAN_A_COVERAGE.md`,
`SIM_STUDY.md`, `PUBLISH.md`, `HARDWIRED_PAUSE.md`, `HARDWIRED_PAUSE_COVERAGE.md`), `CHANGELOG.md`, and `external/` (13
vendored repositories, `MANIFEST.json`, `README.md`).

plan-a-closure is Apache-2.0. The vendored repositories keep their own licences (external/README.md).
