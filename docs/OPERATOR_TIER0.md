# Tier 0 pilot: guide for the cluster operator

This page is for whoever runs plan-a-closure on a host cluster. Tier 0 is one GPU for about two hours of exclusive time.
The whole pilot is one command. It needs no meeting and never waits for keyboard input. It leaves one file to send back.

## What it does

`closure tier0` runs these steps in order and logs each one's exact command, output, exit status and duration:

| step | what it checks | time on hardware |
| --- | --- | --- |
| unit tests | the package works on this host | about 2 min |
| `selftest` | estimators, signature and commitments, end to end on simulated data | under 1 min |
| `preflight` | NVML, the GPU energy counter, torch with CUDA, clock sync; warnings for root, MIG, persistence mode, other processes, int8 and fp8 support and free memory | seconds |
| `hw-selftest` | the GPU's energy tracks the verified work (r2 > 0.9) and the load levels do different work; sizes the unit of work to the GPU and passes it on to `hw-probe` and `hw-trial` | about 3 min |
| `hw-probe` | efficiency slack over clock caps, power caps, precisions (tf32, fp16, int8, fp8) and activation patterns; the lowest joules per FLOP | about 40 min |
| `hw-state` | device memory holds the verifier's data; blocks moved to host memory are caught by timing | a few minutes |
| `hw-trial` | 30 min reference and a 30 min blind audit with synthetic hidden load injected on the same GPU | about 1 h |
| `verify` | hash chain, Ed25519 signature, schedule commitment, pre-registration, results and probe hashes | seconds |
| `hw-restore` | always runs last, even after a failure or a signal: SM clocks unlocked, power limit set back to what it was | seconds |

The run stops early if `selftest`, `preflight`, `hw-selftest` or `hw-trial` fails, and still writes the summary and the
bundle so the failure can be diagnosed from the logs.

The whole hardware path (GPU identity, NVML reads, nvidia-smi control, restoring, signals, the bundle) is rehearsed on
every push against a fake NVML library and a fake nvidia-smi (`tests/test_hw_rehearsal.py`). What only this run can check
is CUDA itself: kernels, timing and energy on a real GPU.

## What it changes on the machine

- **Which GPU.** `--gpu N` is the N-th GPU this process sees through CUDA, so `CUDA_VISIBLE_DEVICES` from your scheduler
  applies. NVML and nvidia-smi number GPUs differently, so the tool matches the same physical GPU by UUID (or PCI
  address) and passes that UUID to every `nvidia-smi -i` call; no other GPU is read or changed. `preflight` prints the
  match and stops the run if it cannot make one.
- **Clocks and power limit.** `hw-probe` locks SM clocks (`nvidia-smi -lgc`) and sets power limits (`nvidia-smi -pl`)
  one variant at a time, and puts both back after every variant and on exit (`-rgc`, the limit as found). It uses only
  clocks the GPU lists as supported, never sets a limit below the GPU's minimum, and checks that each lock and cap took
  effect (some virtual machines accept the command and change nothing; such variants are dropped and noted).
- **Interruptions.** Ctrl-C, a closed terminal or a scheduler's SIGTERM (a time limit) makes the running step restore the
  GPU before it exits; the remaining steps are skipped, `hw-restore` still runs, and the summary and bundle are still
  written. Only SIGKILL cannot be caught: after one, run `sudo -E env PATH="$PATH" closure hw-restore --gpu 0`.
- **Without root.** Clock and power variants cannot be applied; they are dropped and noted, and the probe still measures
  precisions and operand patterns, so the slack it reports covers less. The final `hw-restore` then reports that there
  was nothing to restore.
- **Sustained load.** Dense GEMMs and memory passes at up to 90% of the GPU's capacity, within its power and thermal
  limits.
- **Hidden load.** The "hidden" work is the same synthetic GEMM load, run on the same GPU on a schedule committed before
  the audit. Nothing leaves the machine.
- **Memory.** `hw-state` fills a few GB of device memory, and part of it again in host memory.
- **Files.** Only the output folder you choose. No network access is needed after installation.

## Run it

```bash
git clone https://github.com/AnonRish/plan-a-closure && cd plan-a-closure   # or unzip plan-a-closure.zip
python -m venv .venv && . .venv/bin/activate          # Python 3.10 or newer
pip install -e ".[test,hw]"                           # hw = pynvml + torch: install the CUDA build of torch your node needs
closure tier0 --mock --out runs/rehearsal             # optional rehearsal on fake hardware, about 2 minutes
sudo -E env PATH="$PATH" closure tier0 --confirm-hardware --gpu 0 --out runs/tier0
```

Root is needed only for clock and power-limit control; without `sudo` the run still completes, minus those variants.
Use an exclusive allocation for the whole run (for example Slurm
`--exclusive`). If the OpenTimestamps client `ots` is installed, the pre-registration is timestamped automatically before
any audit data exist; otherwise its hash is logged and kept in the signed chain.

## What to send back

- `runs/tier0/tier0_bundle.tar.gz`: every log, the probe, the trial's evidence and `SUMMARY.md`.
- **Do not send `signing_key.bin`.** It is the run's private key and is deliberately left out of the bundle. Keep it or
  delete it. The public key is in `T1-smoke/signature.json`.
- If an independent power meter logged during the trial, export it as `timestamp_s,power_w` and run
  `closure dcbus-analyze --run runs/tier0/T1-smoke --csv bus.csv`. Send `results_dcbus.json` as well. The meter must be
  DC-coupled and report absolute watts; an AC-coupled probe cannot give energy and the command refuses it.

## Optional, if the allocation has time left

The archive also carries 13 related repositories under `external/` with their own test suites (about ten minutes, CPU
only; nothing in them changes clocks or power limits). Running them on the node is a check that they install and pass
there; cuda-guard's device discovery then sees the real GPU instead of its emulated fallback. Run them as an ordinary
user, not with sudo: as root, four packet-forge tests create a temporary TUN interface (10.99.0.1/24) to replay traffic
through the kernel; without root they skip.

```bash
pip install -e ".[external]"
closure external test --install                       # logs in runs/external/
```

Send `runs/external/` with the bundle if you run it.

## No H100 yet: a shakedown on a cloud or Colab GPU

Tier 0 has no hard dependency on the GPU model. Precisions the device lacks (TF32 before Ampere, fp8 before compute
capability 8.9) and clock or power controls a virtual machine refuses are dropped and noted, as described above, and the
NVML energy counter it needs exists on Volta and newer GPUs (`preflight` stops the run if it is missing). So the same
command runs on a rented cloud GPU or on a free Colab T4, which checks the pipeline, the NVML energy tracking, the
residency timing and the blind smoke trial on a real device.

- **Colab:** open `notebooks/tier0_colab.ipynb` in Google Colab
  ([direct link](https://colab.research.google.com/github/AnonRish/plan-a-closure/blob/main/notebooks/tier0_colab.ipynb)),
  choose a GPU runtime and run the cells (about two hours; keep the tab open).
- **A cloud VM with one GPU and a root shell:** the commands under "Run it" above, unchanged.

Such a run is an engineering shakedown on a non-target device: inside a VM, without an independent meter (assumption A6
does not hold), and usually without clock or power control. It is not the registered trial. Record it in
`docs/DEVIATIONS.md` (date, device, environment, what was dropped, the bundle's SHA-256) and publish it whatever it
shows; the registered numbers still come from Tier 1 on instrumented H100/H200 hardware.

The first one (a Colab T4, 8 November 2026, on 0.5.4) stopped at `hw-selftest`: a unit of work sized for an H100 took
half a second on the T4, so every load level ran flat out ([DEVIATIONS.md](DEVIATIONS.md) section 1). Since 0.5.5 the
unit is sized to the GPU and runs in fp16 on GPUs older than compute capability 8.0, capacity is the GPU's own power
limit, and `hw-selftest` checks that the load levels do different work. On a small GPU, look at the `unit of work:` line
at the top of the `hw-selftest` log: on a T4 expect about 4096 x 4096 float16 and a few milliseconds per unit.

## What it does not claim

Tier 0 checks that the pipeline, the probe and the meter alignment work on this device. Its smoke trial has small samples.
The registered T1 numbers come from Tier 1 (one 8-GPU node, about 46 hours; `docs/HARDWARE_CONFIG.md`). Results are
published within 30 days of the run, whatever the outcome.
