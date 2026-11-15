# Running it on the GPUs that matter, for free or nearly

Every hardware run so far is on a Tesla T4 (`results/README.md`). The question the registered trial asks, whether the
detection gap and the efficiency slack are small enough for the 5% rule, is about H100-class GPUs, and it is decided only
with an independent, absolute power meter (`docs/PREREGISTRATION.md`, assumption A6). This page lists the ways to get
there that cost nothing or very little, what each one can and cannot show, and the command for each.

Terms and prices below are as each provider's own page gave them on 14 November 2026. They change: check the page
before relying on a row.

## What each kind of run adds

| run | what it adds | what it cannot show |
| --- | --- | --- |
| any GPU but a T4, NVML only | the first measurement of the efficiency slack, the energy floor and the residency timing on that architecture; fp8 on a real GPU (it has only run on a CPU so far) | anything an operator could falsify: NVML can be spoofed by whoever runs the machine |
| the same, run by someone other than the author | an independent replication: the code, not its author, produced the result | the meter is still the GPU's own |
| with a DC-coupled, absolute meter on the same GPU (`closure dcbus-analyze`) | the first test of the claim itself: energy closure against a channel the prover does not control | a Plan A claim on its own; that needs the registered Tier 1 trial and its replication (`docs/HARDWARE_CONFIG.md`) |

## The routes

| route | GPUs | cost | root (clock and power-limit variants) | independent meter | what you need |
| --- | --- | --- | --- | --- | --- |
| [Side Channel Cloud](https://sidechannel.cloud/), operated by Amodo Design | H100 and H200 | free for open-source and non-profit projects (its funders pay) | bare-metal access with GPU hardware counters | the DC bus feeding its H200s is instrumented; network taps can be placed anywhere on its network | the sign-up form on its page; access opens in hardware waves; published work has to acknowledge it |
| [Modal](https://modal.com/pricing): `scripts/modal_tier0.py` | H100, H200, B200, B300, RTX PRO 6000, A100, L40S, L4, T4 | $30 of compute a month on the free Starter plan: one smoke pilot on a B300 or B200, two on an H200 or H100, or one medium pilot on an H200 or H100 (`--estimate` prints the table) | a gVisor sandbox: Modal's documentation does not say whether clock changes are allowed; if refused, the probe drops those variants and says so, as on Kaggle | none | a Modal account (`pip install modal`, `modal setup`). Modal also lists up to $10,000 of credits for graduate students, labs and researchers at modal.com/academics |
| a university or national research computing cluster that schedules with Slurm: `scripts/slurm_tier0.sh` | often H100s | free to researchers at many universities and national services, and to students through a sponsoring faculty member | none (batch jobs): clock and power variants dropped and noted | none | an account; the institution's research computing service says how |
| Verifiable Compute Foundation, operated by Lucid: the Research Access Program form on [verifiablecompute.ai](https://verifiablecompute.ai/) | not stated on a page we could read | free access for verification research, in beta (as read in early November; the page did not render for this check) | ? | ? | the form |
| Google Colab with compute units | L4, A100, H100, RTX PRO 6000 (paid tiers; the free tier gives a T4) | pay as you go, $9.99 for 100 compute units; the A100 80 GB uses roughly 7.5 units an hour and the RTX PRO 6000 roughly 8.7 (third-party estimates), so a medium pilot is about 43 to 50 units | Colab let the T4 runs lock clocks | none | `notebooks/tier0_colab.ipynb`, choosing that GPU in Runtime > Change runtime type |
| a GPU rented by the hour as a virtual machine | whatever the provider has | roughly $2 to $4 an hour for an H100, so under $10 for a smoke pilot | yes, on a VM with GPU passthrough: the whole probe runs | none, unless the provider gives rack or PSU metering | `bash scripts/run_anywhere.sh --hardware` |
| Colab's free tier and Kaggle | T4 (and a P100 on Kaggle, which has no NVML energy counter) | free | Colab yes, Kaggle no | none | the notebooks; eight runs exist already |

Side Channel Cloud is the one route that has, in one place, the target GPUs, bare metal and an instrumented DC bus. Its
only published work so far (Gargiulo and Kulp, arXiv 2609.00309) clamped an AC-coupled Rogowski probe (no DC response,
34 Hz to 30 MHz) around the PCIe auxiliary supply of one H200 NVL. That channel suits workload signatures and cannot give
energy; closure needs a DC-coupled channel on the same conductors (a Hall-effect or shunt sensor, a DC current clamp on
the same scope, or the PSU's or PDU's own metering), exported as `timestamp_s,power_w`. Ask for it when you apply.

## Commands

### Modal, from your own computer

```bash
pip install modal && modal setup                                  # once
python scripts/modal_tier0.py --estimate                          # costs; does not contact Modal
modal run scripts/modal_tier0.py --rehearse                       # the pilot on a simulated GPU, in a CPU container
modal run scripts/modal_tier0.py --gpu H100 --check               # a minute or two: what doctor and preflight read there
modal run --detach scripts/modal_tier0.py --gpu H100              # the smoke pilot, about 2 h 20 min
modal run --detach scripts/modal_tier0.py --gpu B200 --profile medium
modal volume get plan-a-closure-runs <run> runs/modal/            # fetch a run later, whatever happened to the terminal
modal app logs plan-a-closure-tier0 -f                            # follow a detached run's output
modal app stop plan-a-closure-tier0                               # stop it (and its billing) early
```

Run `--check` first: it reads the NVML energy counter through Modal's sandbox, which the whole pilot needs, for a few
cents. Before the first GPU run, set a Workspace budget or spend limit on Modal's Usage & Billing page, so that a run
that goes wrong stops at the free credit instead of charging a card. Anyone can run these commands in their own account, which makes a run there a replication by someone other than
the author. Each pre-empted and restarted attempt is kept in its own `attempt-<n>` folder.

### A Slurm cluster

```bash
bash scripts/slurm_tier0.sh --setup                                          # once, on a login node
sbatch --account=<account> scripts/slurm_tier0.sh                            # smoke, about 2 h 20 min
sbatch --account=<account> --time=0-08:00 scripts/slurm_tier0.sh --profile medium
```

The job asks for one whole H100 (`--gpus=h100:1`, in your cluster's GPU type name; a MIG slice has no energy counter of
its own) and refuses to start if its time limit is shorter than the profile needs.

### A machine you have a shell on

```bash
bash scripts/run_anywhere.sh --check        # one minute: which steps would run on each GPU here
bash scripts/run_anywhere.sh --hardware     # the pilot; --profile medium or long for the decision rules
```

## An independent meter for a PCIe GPU

[PowerSensor3](https://github.com/nlesc-recruit/PowerSensor3) (ASTRON and the Netherlands eScience Center; open hardware
and an Apache-2.0 host library) measures the power a PCIe card draws through its slot and auxiliary cables with
Hall-effect current sensors and isolated voltage sensors, about 20,000 times a second; its authors give a complete
unit with three sensor boards as under 100 euros in components (van der Vlugt et al., ISPASS 2025, arXiv 2504.17883).
That is a DC-coupled, absolute channel outside the GPU, where its sensor boards fit the card's power connectors. This
kit reads it directly:

```bash
closure meter-log --device /dev/ttyACM0 --out runs/bus.ps3.txt & LOG=$!   # start before the pilot (absolute Unix times)
bash scripts/run_anywhere.sh --hardware --out runs/tier0
kill $LOG; wait $LOG                                                     # stops the log and writes runs/bus.ps3.csv
closure dcbus-analyze --run runs/tier0/T1-smoke --csv runs/bus.ps3.csv
```

`closure meter-log` needs PowerSensor3's Python binding (built with `-DPYTHON_BINDINGS=ON`). Without it,
`psrun -f dump.txt -- sleep <seconds>` records the same trace with relative times, and
`closure dcbus-import dump.txt bus.csv --t0 <Unix time at its start>` converts it; times rounded to six significant
figures in long relative dumps are spread back out evenly, so each window's energy lands where it was drawn.

## Asking someone to run it

The pilot needs no meeting and no one present: [OPERATOR_TIER0.md](OPERATOR_TIER0.md) is the operator's page, and
[HARDWARE_CONFIG.md](HARDWARE_CONFIG.md) section C lists the questions a host can answer in writing. A useful request
is short: one GPU of the target class for about 2 h 20 min (smoke) or 5 h 40 min (medium) of exclusive time; root if
possible; a DC-coupled absolute power channel on the same GPU if they have one; the bundle sent back, and the result
published whatever it shows within 30 days of the run.
