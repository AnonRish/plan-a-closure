# Verify it yourself

You should not have to take anyone's word for what this repository does. This page lists what you can see or run,
cheapest first, and says for each what it shows and what it cannot show. Nothing here needs an account, a key or a
conversation, and nothing is sent anywhere.

| | what you do | time | needs | what it shows | what it cannot show |
| --- | --- | --- | --- | --- | --- |
| 0 | **Look.** Open the [CI page](https://github.com/AnonRish/plan-a-closure/actions/workflows/ci.yml), pick the latest run and read its Summary; or read [results/README.md](../results/README.md) | 5 min | a browser | the table of every hardware run, re-derived on GitHub's machine from the published bundles; the tests passing on Python 3.10 to 3.13; the pilot run end to end on a simulated GPU | anything you have not run yourself |
| 1 | **Re-derive the published results** (below) | 10 min | Python 3.10+ | the bundles are the files whose hashes the documents give; their hash chains, signatures and commitments verify; the signed results and every number the documents quote follow from the raw data | that the raw data are true: see "what a bundle proves" |
| 2 | **Run the pipeline**: `bash scripts/run_anywhere.sh` | 3 min | Python 3.10+ | the code installs and runs every step on your machine, on a simulated GPU, and its evidence verifies | anything about a real GPU |
| 3 | **Ask your machine**: `bash scripts/run_anywhere.sh --check` | 1 min | any machine | which pilot steps would run on each GPU you have, and why not where not (`closure doctor`) | nothing is measured |
| 4 | **Run it on your GPU**: `bash scripts/run_anywhere.sh --hardware` | 2 h 20 min (smoke), 5 h 40 min (medium), 11 h (long) | Linux, an NVIDIA GPU with an NVML energy counter, exclusive use of it | an independent replication on your hardware, by you, whatever it shows. On anything but a T4 it is the first run of its kind | a Plan A claim: that needs an independent power meter (level 5) |
| 5 | **The registered trial** ([RUNBOOK_HARDWARE.md](RUNBOOK_HARDWARE.md)) | days | H100-class GPUs and a DC-bus power meter | what the pre-registration says it decides | what Plan A needs beyond this one leg |

## Level 1: re-derive the published results

```bash
git clone https://github.com/AnonRish/plan-a-closure && cd plan-a-closure
python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[test]"
pytest -q tests/test_runs_on_record.py        # every bundle: hash, verify, and the numbers the documents quote
python results/record.py                      # the table in results/README.md, computed here
python results/reread.py results/shakedown-2026-11-11-kaggle-t4-runs6-7   # one folder in full, from its bundles
python results/slack_left.py                  # results/SLACK_LEFT.md: where the slack comes from, rule by rule
```

By hand, for one bundle, with nothing but the commands a run prints at its end:

```bash
mkdir /tmp/run6 && tar xzf results/shakedown-2026-11-11-kaggle-t4-runs6-7/gpu0-tier0_bundle.tar.gz -C /tmp/run6
sha256sum results/shakedown-2026-11-11-kaggle-t4-runs6-7/gpu0-tier0_bundle.tar.gz    # compare with docs/DEVIATIONS.md
closure verify /tmp/run6/*/T1-long             # hash chain, Ed25519 signature, schedule and order commitments
closure reanalyze --run /tmp/run6/*/T1-long    # the signed results again, from raw.npz
closure criteria --run /tmp/run6/*/T1-long     # the pre-registered rules, read off the results
closure physics --run /tmp/run6/*/T1-long      # what the GPU did at each load level
closure slack-left --run /tmp/run6/*/T1-long   # the slack left if a regime fixed clocks, the stack or the data
```

**What a bundle proves.** That these results follow from these data; that the analysis, the thresholds, the seed and
the committed schedule of hidden loads were fixed in `prereg.json` before the audit data existed (its hash is in the
signed chain, and from run 5 on it carries an OpenTimestamps proof, pending at public calendars when the bundle was
written, which `ots upgrade` and `ots verify` complete); and that the code was the commit named in it (since the history was re-dated to UTC on 15 November 2026, the
commit [COMMIT_HISTORY.md](COMMIT_HISTORY.md) maps it to; its source hash, `code.src_sha256`, checks the code either
way). **What it does not prove.** That the data came from the GPU as described. Every run so far reads
the GPU's own NVML counters, which whoever runs the machine could falsify, and every run so far was run by the
author. The pre-registration says so (assumption A6), every report is labelled "NVML energy counter; spoofable", and
the two things that would change it are an independent power meter and a run by someone else. Level 4 is the second.

## Level 4: your GPU

```bash
git clone https://github.com/AnonRish/plan-a-closure && cd plan-a-closure
bash scripts/run_anywhere.sh --check                      # what would run here, in a minute
bash scripts/run_anywhere.sh --hardware                   # the smoke pilot: 2 h 20 min
bash scripts/run_anywhere.sh --hardware --profile medium  # about 5 h 40 min: large enough to read rules H1.1 to H1.4
```

The script makes `./.venv`, installs the package with PyTorch, prints what `closure doctor` reads, and runs
`closure tier0 --confirm-hardware`, the same command the Colab and Kaggle notebooks run. It uses the GPU exclusively
until it finishes, restores the clocks and power limit it found, and leaves `SUMMARY.md` and `tier0_bundle.tar.gz`.
As root (or with passwordless sudo) the probe also tries clock and power-limit settings; without, those variants are
dropped and noted, as in Kaggle's container. [OPERATOR_TIER0.md](OPERATOR_TIER0.md) describes every step.

Which GPUs. The pilot needs Linux, an NVIDIA driver whose NVML reports total energy (NVIDIA documents the counter
for Volta and newer; a P100 lacks it), PyTorch with CUDA, and MIG off. The unit of work is sized to the GPU at the
start of each run, and the power limit and idle power are read from the device, so nothing is tuned to one model. On
every GPU the probe sweeps the precisions the device has (half precision, TF32, int8, and fp8 from compute capability
8.9), a second kernel library, three operand patterns, and clock and power-limit settings where the machine allows
them.

| GPU family | CUDA compute capability | fp8 variant | hardware runs on record |
| --- | --- | --- | --- |
| T4 (Turing) | 7.5 | no | 8, on at least 7 different GPUs (7 bundles published; run 2's was lost with its session) |
| A100, A10, RTX 30 (Ampere) | 8.0, 8.6 | no | none |
| L4, L40S, RTX 40 (Ada Lovelace) | 8.9 | yes | none |
| H100, H200 (Hopper) | 9.0 | yes | none: the target of the registered trial |
| B200, B300 (Blackwell), RTX 50 | 10.0, 10.3, 12.0 | yes | none |
| AMD and Intel GPUs | | | none, and none possible yet: the measured path reads NVML. `closure doctor` lists the power, energy and busy-time counters the kernel exposes for them; no reader for them is written |

A run on any row marked "none" is new information, and the fp8 path in particular has only ever run on a CPU in
the tests. If it stops, the bundle is still written and says where; that is a result too. To add your run to the
record, open an issue at https://github.com/AnonRish/plan-a-closure/issues and attach `tier0_bundle.tar.gz`. It
leaves out the run's private key (`signing_key.bin`) on purpose. Every run is published whatever it shows.

No GPU at hand: any cloud that rents an NVIDIA GPU by the hour with a shell will do. A virtual machine gives root, so
the whole probe runs; a container usually refuses clock changes, and the pilot then runs as it does on Kaggle. For free
or nearly, [GPU_ACCESS.md](GPU_ACCESS.md) lists the routes: Modal's free monthly credit covers a smoke pilot on an H100,
H200, B200 or B300 from your own computer (`modal run --detach scripts/modal_tier0.py --gpu H100`), and
`scripts/slurm_tier0.sh` runs it as a batch job on a Slurm cluster's H100.

## What has been shown, and what has not

Shown, on Tesla T4s in Colab and Kaggle sessions with NVML as the only meter (eight runs on at least seven
different GPUs, [DEVIATIONS.md](DEVIATIONS.md)):

- The pilot runs unattended for up to ten hours, restores the GPU, and its evidence verifies.
- With the analysis, thresholds, seeds and campaign fixed and published beforehand, two nine-hour trials read as one
  campaign gave 3 false alarms in 408 clean blocks, detected 210 of 210 hidden loads of 5% of capacity or more and 285
  of 290 of 2% or more, and bounded the hidden load's time in 321 of 321 blocks.
- The same analysis on a shorter Colab trial missed 2 of 45 hidden loads at 5% or more, one in each of two classes,
  which fails that rule at that trial's size. The clock lock it used did not hold at full load.
- On every T4 the pre-registered outcome is FAIL. The probe measured an efficiency slack of 8 to 14% on these GPUs:
  the same verified work can cost that much less energy on another allowed setting, and at the trials' load that adds
  6 to 8% of capacity to the gap by itself. The outcome rule allows 5% for the detection gap and the slack together.
- A physical finding: at its power limit a GPU's hidden work adds no energy and displaces verified work, so energy
  accounting alone is blind there, and the time channel and the displaced work carry the signal.

Not shown:

- **Any GPU other than a T4.** No H100, H200, B200, A100, L4 or consumer-card run exists. Whether the detection gap
  and, above all, the efficiency slack are small enough on H100-class hardware for the 5% rule is the open question
  the registered trial exists to answer. On T4s the slack alone is too large.
- **An independent meter.** Every run reads the GPU's own counters.
- **An independent operator.** Every run so far is the author's.
- **A deliberate adversary.** The hidden loads are synthetic and scheduled blind; nobody has yet tried to beat the
  detector with knowledge of it, beyond the energy-neutral `slack` class the design reports as its blind spot.
- **Served models, many-GPU nodes, real network taps.** T1b, T3 and the gateway run on simulators and toy models.
- **Other makers' GPUs**, as in the table above.
- **Plan A as a whole.** This repository works on one leg of it, the completeness of inference-only verification,
  and makes the arithmetic of the plan and of related treaty proposals executable. Whether states adopt it, whether
  chips can be tracked, whether hardware can be trusted: none of that is software, and none of it is claimed here.
