# plan-a-closure

[![ci](https://github.com/AnonRish/plan-a-closure/actions/workflows/ci.yml/badge.svg)](https://github.com/AnonRish/plan-a-closure/actions/workflows/ci.yml)
(tests, re-derived claims, coverage, vendored-tree check and the Tier 0 pilot on a simulated GPU, Python 3.10 to 3.13, every push)

**Compute material-balance accounting for inference-only AI verification (AI 2040 "Plan A").**
Every joule, packet byte and byte of memory on an enrolled cluster must be *explained* by verified work.
What is left over (the residual) upper-bounds hidden compute, hidden exfiltration and hidden persistent state.

> **Status: v0.12.0. The software is tested; the physical claim is not yet demonstrated.** Eight shakedown runs on
> Tesla T4s in Colab and Kaggle sessions (8 to 12 November 2026, the GPU's own NVML counters as the only meter) are
> published whatever they showed: [results/README.md](results/README.md) is the table, generated from the bundles, and
> [docs/DEVIATIONS.md](docs/DEVIATIONS.md) is the account.
>
> - **Runs 1 to 5** found what was wrong: a unit of work sized for an H100, calibration drift, and, on the first
>   nine-hour trial, the registered analysis failing its own false-alarm rule (11 false alarms in 204 clean blocks).
>   Its raw data showed why: a straight-line energy model on a power-limited GPU, a threshold that had silently fallen
>   back to a Gaussian, hidden-load labels that understated the load, and a physical finding: at its power limit a
>   GPU's hidden work adds no energy and displaces verified work, so energy accounting alone is blind there.
>   Amendment v0.6 of [docs/PREREGISTRATION.md](docs/PREREGISTRATION.md) answered each point before any further run.
> - **Runs 6 and 7** were its first prospective test: two nine-hour trials on two GPUs, declared one campaign
>   beforehand. **Every rule the trial decides held**: 3 false alarms in 408 clean blocks, 210 of 210 hidden loads of
>   5% of capacity or more detected, 285 of 290 of 2% or more, and the hidden load's time bounded in 321 of 321 blocks.
> - **Run 8**, a shorter trial on Colab, **failed the detection rule by one block in each of two classes** (43 of 45 at
>   5% or more). Its clock lock did not hold at full load; amendment v0.7 changes the lock rule before the next run.
> - **On every T4 the pre-registered outcome is FAIL**, and was predicted to be. The probe measured an efficiency slack
>   of 8 to 14% on these GPUs (the same verified work can cost that much less energy on another allowed setting), which
>   at the trials' load adds 6 to 8% of capacity to the gap by itself; the outcome rule allows 5% in all.
> - **Where that slack comes from**, read from the same bundles rule by rule ([results/SLACK_LEFT.md](results/SLACK_LEFT.md);
>   descriptive, it decides nothing). Two savings are measured, not just bounded: all-zero activations on the
>   reference stack save 4.9 to 7.2% at half load on every GPU, and a low clock lock 6.0 to 10.0% where clocks could
>   be locked. Pinning the whole software stack leaves the data saving; predicting energy from the data leaves the
>   stack's; only both together leave nothing the probe tried. In treaty terms, energy accounting needs both. And with
>   three rounds the bound is partly noise: a setting with no effect got 6.8 to 9.0%. Amendment v0.8 adds a null twin
>   to every probe and doubles its rounds before the next run.
>
> None of this is a claim about Plan A. A T4 is not the target device, NVML can be spoofed by whoever runs the machine,
> and every run so far is the author's. Each claim is decided by the pre-registered trial on instrumented H100-class
> hardware with an independent power meter. The software itself: 438 tests (`pytest`), plus 23 that run the torch code
> on CPU where torch is installed, 10 of them rehearsing the whole GPU path against a fake NVML and nvidia-smi; the 13
> vendored repositories under `external/` add their own suites (2,708 tests passed here, `closure external test`). A
> report whose status says `SIMULATED` validates the estimators only.

## Check it yourself

[docs/VERIFY_IT_YOURSELF.md](docs/VERIFY_IT_YOURSELF.md) lists what you can see or run, what each step shows, and
what has not been shown by anyone yet.

```bash
git clone https://github.com/AnonRish/plan-a-closure && cd plan-a-closure
bash scripts/run_anywhere.sh               # 3 minutes, no GPU: the whole pilot on a simulated GPU, evidence verified
bash scripts/run_anywhere.sh --check       # 1 minute: which steps would run on each GPU of this machine, and why
bash scripts/run_anywhere.sh --hardware    # 2 h 20 min on an NVIDIA GPU: the pilot for real, and a bundle to send back
.venv/bin/python -m pytest -q tests/test_runs_on_record.py   # every published bundle re-read: hashes, signatures, numbers
```

**Before `--hardware` on your own GPU:** everything it does to the machine is listed in
[What it changes on the machine](docs/OPERATOR_TIER0.md#what-it-changes-on-the-machine). In short:

- It uses only the GPU you name (`--gpu N`, matched by UUID) and needs that GPU to itself until the run ends. No other
  GPU is read or changed.
- With root, it locks clocks and sets power limits one variant at a time, and puts both back after each variant and on
  exit, including after Ctrl-C or a scheduler's time limit. After a `kill -9`,
  `sudo .venv/bin/python -m closure.cli hw-restore --gpu N` puts them back. Without root, those variants are skipped and
  noted.
- It installs into `./.venv` (PyTorch included, about 3 GB, for `--hardware`), writes only to its output folder, and
  uses no network after installation unless you add `--stamp`. Nothing is sent anywhere.
- It leaves one file to send back, `tier0_bundle.tar.gz`. The run's private signing key stays with you.
- `--check` shows what would run on each GPU without running anything on it, and Ctrl-C stops a run at any point.

The pilot is one unattended command underneath, `closure tier0` ([operator guide](docs/OPERATOR_TIER0.md)).
[notebooks/tier0_colab.ipynb](notebooks/tier0_colab.ipynb)
([open in Colab](https://colab.research.google.com/github/AnonRish/plan-a-closure/blob/main/notebooks/tier0_colab.ipynb))
runs it on a free Colab GPU, and [notebooks/tier0_kaggle.ipynb](notebooks/tier0_kaggle.ipynb) runs a nine-hour trial
on each of a Kaggle session's two GPUs, declared one campaign beforehand and read together (`closure pool`). A run on
any GPU other than a T4 would be the first of its kind, and the most useful thing a reader can add.

**On an H100, H200, B200 or B300, for free or nearly** ([docs/GPU_ACCESS.md](docs/GPU_ACCESS.md)): Modal's free Starter
plan includes $30 of compute a month, which covers a smoke pilot on any of them, run from your own computer in your own
account; Side Channel Cloud gives open-source projects free bare-metal H100s and H200s with an instrumented DC bus; and
a Slurm cluster's H100 takes one batch job.

```bash
pip install modal && modal setup                               # once
python scripts/modal_tier0.py --estimate                       # what each GPU and profile costs; no Modal call
modal run scripts/modal_tier0.py --gpu H100 --check            # a minute or two: does NVML's energy counter read there?
modal run --detach scripts/modal_tier0.py --gpu H100           # the smoke pilot, about 2 h 20 min
sbatch --account=<account> scripts/slurm_tier0.sh              # a Slurm cluster (bash scripts/slurm_tier0.sh --setup first)
```

## The gap this targets

Plan A's inference-only retrofit checks *correctness* with passive taps and partial recomputation. For *completeness*
the plan says it does not verify that spare compute is unused; it relies on side-channel mitigation and periodic
memory wipes. The Get Involved SITREP rates side-channel work "not on track". Workload classifiers built on physical or
telemetry signals are signature-based. Gargiulo and Kulp (arXiv 2609.00309, measured on an H200 NVL hosted by Amodo Design
with an AC-coupled current probe) reach 97% accuracy, with diluted LoRA the hardest evasion case. Rahman and Tajdari
(arXiv 2606.19262) classify from 1 Hz NVML telemetry at 98% accuracy, assume the counters cannot be tampered with, and
find white-box LoRA the hardest case (42.6% detection). Kimpson, Baker and Graham (arXiv 2610.07476) bound hidden compute
from power on A100s, reading NVML's energy counter as a trusted instrument: a matched-energy attack (declared work on
cheap operands, the saved energy spent on covert int8 work) hides at least 0.41 of capacity, the bound from the meter
alone is 1.16, and only re-execution at an observed clock plus further restrictions bring it down to 0.059. Closure's
slack-inflated gap plays the same role, measured rather than derived, which is why the probe sweeps operand cost and
int8/fp8. Closure is **signature-independent accounting**: whatever hidden work does, it costs joules,
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
| independent meter | can the prover's own NVML be cross-checked? | absolute-power CSV import (AC-coupled traces are rejected), unit conversion, constant-memory decimation of very large traces, PowerSensor3 dumps read directly and recorded with absolute times (`closure dcbus-import`, `closure meter-log`), clock alignment, re-analysis of the same run | `dcbus.py` |
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
Barnett and Thiergart on what evaluations can and cannot do, CBPAI's *Deal of the Century*, MIRI's draft agreement and
FLI's Draft Articles) rest on verification this repository builds. [docs/TREATY_COVERAGE.md](docs/TREATY_COVERAGE.md) maps every mechanism they name to code, to a
GPU or cluster step, or to "not code", and states what the computations show.

| module | what it makes concrete | command |
| --- | --- | --- |
| `treaty/thresholds.py` | the named compute thresholds (1e25 FLOP and 1e17 FLOP/s licences, a 1e26 draft) and the days a fleet needs to run a threshold-sized covert run at the hidden rate a trial measured | `closure treaty covert-days` |
| `treaty/deterrence.py` | when detection deters: per-period and winner-take-all conditions, and a CUSUM over block residuals against the time to a threshold run, each checked by simulation | `closure treaty deterrence`, `race` |
| `treaty/coalition.py` | the middle-powers agreement: activation at 20% of world GDP and population (World Bank data), smallest coalitions with a proof that none is smaller, Shapley-Shubik power, the redline ladder with its persistence and leak rules | `closure treaty coalition`, `redlines` |
| `treaty/mockrun.py` | A Narrow Path's mock training run: a provider that sees only an energy meter stops a training job at its FLOP budget, and the job's starting weights are checked against its seed | `closure treaty mock-run` |
| `treaty/geoloc.py` | delay-based chip location: timed, signed challenges from landmarks bound how far a chip can be from its declared site | `closure treaty geo-landmark`, `geo-chip`, `geo-check` |
| `treaty/inspection.py`, `beacon.py`, `quorum.py` | inspection samples nobody can predict, lot-selected witnesses, a draw the last party to reveal cannot steer, and k-of-n approval of critical actions | `closure treaty inspect-plan`, `beacon-commit`, `beacon-seed`, `sortition`, `quorum-verify` |
| `treaty/clauses.py` | suspended enforcement clauses: in force only for an unexpired finding that k of n panel members signed | `closure treaty clause` |
| `treaty/bandwidth.py` | interconnect limits: the link rate that training across pods needs, the slowdown a cap forces, and what inference needs | `closure treaty bandwidth` |
| `treaty/asi_agreement.py` | MIRI's draft agreement (arXiv 2511.10783): FLOP counting, H100e and TPP, the three thresholds, covered chip clusters, declared runs approved by both sides' inspectors, Council consensus and vetoes, 30-day emergency changes, the register, transfers, certified destruction, challenge inspections, and its Tables 1 and 2 | `closure treaty asi-run`, `asi-cluster`, `asi-crosssite`, `asi-tables`, `asi-off` |
| `treaty/fli_articles.py`, `chipauth.py` | FLI's Draft Articles: the catastrophic-risk test, certificates and evaluator licences, challenges, the Conference's simple and contribution-weighted majorities, amendments, and Annex C's chip authorization (signed, used once, renewed every few minutes, withheld after a violation) | `closure treaty fli-weighted`, `chip-auth` |
| `treaty/obligations.py`, `coverage.py` | both texts' deadlines against a log of dated events, and their article-by-article matrix | `closure treaty obligations`, `coverage` |

## Plan A coverage (checked against the AI 2040 pages)

`docs/PLAN_A_COVERAGE.md` maps 79 requirements from the Verification Plan and its Get Involved page (every phase, all
17 SITREP workstreams, the four tracks, the open problems) to code and tests in this archive, including the vendored
repositories under `external/`. `closure coverage` fails if a row points at code or a test that does not exist, and
`closure external check` fails if a vendored test that a row cites did not pass in the recorded run. On 14 November 2026
all 17 SITREP statuses, the 7 open problems and the 4 tracks still matched the live Get Involved page (last updated
9 July 2026).

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
Training" (Working Group on AI Pause Feasibility, Berkeley; checked in full against v1.0.1, October 2026; in v1.0.2 of
26 October 2026, 35 of the 114 numbers below were looked up and all were unchanged, and its footnotes from 21 on are
numbered one higher, [docs/HARDWIRED_PAUSE.md](docs/HARDWIRED_PAUSE.md)) executable: treaty thresholds, covert-evasion
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
  Neither repository had changed by 14 November 2026.
- Telemetry-based workload classification (3.3.3) is here only as defence in depth (`cadence.py`), never as a bound.
- `bridge.py` turns a closure trial's measured detection gap into a ledger line for transitional inference service, replacing an
  assumed covert discount with a measured one on the audited share of a fleet. It is descriptive, not pre-registered, and only as
  good as the trial behind it.

Items that are inspections, seals, treaties or chip manufacturing are marked `policy` or `physical` and are not counted as
covered. `gemm_audit.py` is a design-time screen, not the physical audit the paper requires.

## Two draft agreements, article by article

MIRI's draft agreement (Scher, Abecassis, Barnett and Abeyta, arXiv 2511.10783) and FLI's Draft Articles on the Safe
Development and Diffusion of Artificial Intelligence (2026) are written as treaty text, so
[docs/AGREEMENTS_COVERAGE.md](docs/AGREEMENTS_COVERAGE.md) gives every article and annex of both a row, generated by
`closure treaty coverage`, which fails if a row points at code or a test that does not exist.

| status | rows |
| --- | --- |
| implemented (code and tests here) | 49 |
| hardware-gated (code here; measured on hardware) | 8 |
| partial | 4 |
| physical (outside software) | 5 |
| policy (outside software) | 33 |

Every one of the 61 software rows has code and a test. What the computations show is in
[docs/TREATY_COVERAGE.md](docs/TREATY_COVERAGE.md): FLI's chip authorizations, as Annex C describes them, can be held
back and used after renewal stops (30 days of run-on after 30 days of use, with renewals every 5 minutes worth 10), and
binding each one to a nonce the chip has just made bounds that to about one renewal period; two 16-H100e sets on MIRI's
25 Gbit/s line are no covered cluster yet can train together with no slowdown; on the plain reading of MIRI's Article X,
a Council member can refuse a challenge inspection of its own territory; and FLI's contribution-weighted votes, with GDP
as a stand-in, put the verification and enforcement mechanisms in the hands of four economies.

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
pytest                                  # 438 tests (461 with torch installed)
closure selftest                        # end-to-end simulated trial, PASS/FAIL
closure doctor                          # what the pilot can do on this machine, and why not where not
closure tier0 --mock --out runs/tier0   # the whole one-GPU pilot on fake hardware: logs, SUMMARY.md, bundle
python results/record.py                # every hardware run on record, re-derived from the published bundles
closure redteam                         # gateway sampling + recomputation against substituted models (toy model)
closure pause claims                    # the hardwired-pause paper's numbers, re-derived
closure metrics                         # the plan's evaluation metrics, scored per mechanism
closure external check                  # vendored repositories: trees match external/MANIFEST.json
pip install -e ".[hw,external]" && closure external test --install   # their own suites (external/README.md)
closure sim-trial --out runs/sim        # writes results.md, chain.jsonl, signature.json, prereg.json, raw.npz
closure verify runs/sim                 # chain, signature, commitment, prereg and results hashes
closure criteria --run runs/sim         # the pre-registered decision rules H1.1 to H1.4, read off the run
closure sim-trial --profile long --out runs/long   # the long design: interleaved calibration, balanced schedule
closure physics --run runs/long         # work, power and busy time by load level, and what hidden load did to them
closure reanalyze --run runs/long --analysis linear   # another analysis on the same raw data, labelled POST HOC
closure hw-probe --mock --out runs/probe.json                  # efficiency slack and energy floor on a fake rig
closure sim-trial --out runs/sim2 --probe runs/probe.json      # binds the probe into the pre-registration and the report
closure slack-left --run runs/sim2      # the slack left if a regime fixed clocks, the stack or the data (decides nothing)
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

**Run on real GPUs as shakedowns (eight runs on T4s in cloud sessions, NVML only; [docs/DEVIATIONS.md](docs/DEVIATIONS.md)).**
The whole pilot runs unattended for up to ten hours, restores the GPU, and its evidence verifies. `TorchLoad`,
`TorchProver` and `TorchRig` run on a GPU; clock locking and power capping work where the platform allows them (Colab
does, Kaggle's container does not); energy tracks verified work (r2 = 0.93 to 0.97); device-versus-host memory
separates by the time of a challenge's slowest block (2,999 of 3,000 parked provers caught in runs 6 to 8, with 21
false alarms in 6,000 honest challenges, inside both registered thresholds); the mock training run was stopped by its
meter inside the budget on four GPUs. The straight-line analysis failed its false-alarm rule on the first run large
enough to decide it (run 5). Its pre-registered replacement then held every rule the trial decides on a two-GPU
campaign (runs 6 and 7) and failed the detection rule by one block in each of two classes on a shorter Colab trial
(run 8). On every T4 the outcome is FAIL on the measured efficiency slack. None of this is a claim: there is no
independent meter, a T4 is not the target device, and every run is the author's.

**Hardware-gated (not yet demonstrated).** Everything the registered trial decides: the false-alarm rate and the
closure gap under amendments v0.6 to v0.8, bound validity, the J/FLOP floor and the efficiency slack on an H100 or
H200, where no run of any kind exists yet (`closure doctor` says which steps would run on a given machine);
DC-bus clock alignment and the independent meter; TAP capture; the gateway, hashing tap and canaries on real network
hardware; the cadence detector on real telemetry.

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

`src/closure/`: closure core (`conformal.py` `residual.py` `link.py` `energy.py` `sim.py` `trial.py` `criteria.py`
`drift.py` `physics.py` `compose.py` `traffic.py` `state.py` `evidence.py` `dcbus.py` `tier0.py` `doctor.py` `cli.py`), Plan A modules (`claims.py` `ledger.py` `retrofit.py` `assurance.py` `repro.py`
`gateway.py` `taphash.py` `tapwatch.py` `cadence.py` `metrics.py` `frontier.py`
`approval.py` `captrade.py` `coverage.py` `external.py`), `hw/` (`nvml.py` `workloads.py` `source.py` `probe.py` `gpu.py`) and `pause/` (`thresholds.py`
`treaty_ledger.py` `census.py` `inference_only.py` `gemm_audit.py` `fab.py` `whitelist.py` `registry.py` `supply_chain.py` `transition.py`
`msic_econ.py` `pausegame.py` `bridge.py` `paper_claims.py` `coverage.py` `cli.py`), and `treaty/` (`thresholds.py` `deterrence.py`
`coalition.py` `mockrun.py` `geoloc.py` `inspection.py` `beacon.py` `quorum.py` `clauses.py` `bandwidth.py`
`asi_agreement.py` `fli_articles.py` `chipauth.py` `obligations.py` `coverage.py` `cli.py`). `tests/`, `scripts/`
(`run_anywhere.sh`, `modal_tier0.py`, `slurm_tier0.sh`, `sim_study.py`, `crosscheck_upstream.py`), `results/` (every hardware run's bundle, `record.py`, `reread.py`), `docs/`
(`VERIFY_IT_YOURSELF.md`, `GPU_ACCESS.md`, `DEVIATIONS.md`, `HARDWARE_CONFIG.md`, `OPERATOR_TIER0.md`, `PREREGISTRATION.md`, `RUNBOOK_HARDWARE.md`, `PLAN_A_COVERAGE.md`, `TREATY_COVERAGE.md`, `AGREEMENTS_COVERAGE.md`,
`SIM_STUDY.md`, `HARDWIRED_PAUSE.md`, `HARDWIRED_PAUSE_COVERAGE.md`), `CHANGELOG.md`, and `external/` (13
vendored repositories, `MANIFEST.json`, `README.md`).

plan-a-closure is Apache-2.0. The vendored repositories keep their own licences (external/README.md).
