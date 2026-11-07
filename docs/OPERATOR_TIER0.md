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
| `hw-selftest` | the GPU's energy tracks the verified work (r2 > 0.9) | about 3 min |
| `hw-probe` | efficiency slack over clock caps, power caps, precisions (tf32, fp16, int8, fp8) and activation patterns; the lowest joules per FLOP | about 40 min |
| `hw-state` | device memory holds the verifier's data; blocks moved to host memory are caught by timing | a few minutes |
| `hw-trial` | 30 min reference and a 30 min blind audit with synthetic hidden load injected on the same GPU | about 1 h |
| `verify` | hash chain, Ed25519 signature, schedule commitment, pre-registration, results and probe hashes | seconds |

The run stops early if `selftest`, `preflight`, `hw-selftest` or `hw-trial` fails, and still writes the summary and the
bundle so the failure can be diagnosed from the logs.

## What it changes on the machine

- **Clocks and power limit.** `hw-probe` locks SM clocks (`nvidia-smi -lgc`) and sets power limits (`nvidia-smi -pl`)
  one variant at a time, and restores both on exit (`-rgc`, default limit). It uses only clocks the GPU lists as supported
  and never sets a limit below the GPU's minimum. If it is interrupted, check with `nvidia-smi -q -d CLOCK,POWER`.
- **Sustained load.** Dense GEMMs and memory passes at up to 90% of the GPU's capacity, within its power and thermal
  limits.
- **Hidden load.** The "hidden" work is the same synthetic GEMM load, run on the same GPU on a schedule committed before
  the audit. Nothing leaves the machine.
- **Memory.** `hw-state` fills a few GB of device memory, and part of it again in host memory.
- **Files.** Only the output folder you choose. No network access is needed after installation.

## Run it

```bash
unzip plan-a-closure.zip && cd plan-a-closure       # or clone it, once the repository is public
python -m venv .venv && . .venv/bin/activate          # Python 3.10 or newer
pip install -e ".[test,hw]"                           # hw = pynvml + torch: install the CUDA build of torch your node needs
closure tier0 --mock --out runs/rehearsal             # optional rehearsal on fake hardware, about 2 minutes
sudo -E env PATH="$PATH" closure tier0 --confirm-hardware --gpu 0 --out runs/tier0
```

Root is needed only for clock and power-limit control. Use an exclusive allocation for the whole run (for example Slurm
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

## What it does not claim

Tier 0 checks that the pipeline, the probe and the meter alignment work on this device. Its smoke trial has small samples.
The registered T1 numbers come from Tier 1 (one 8-GPU node, about 46 hours; `docs/HARDWARE_CONFIG.md`). Results are
published within 30 days of the run, whatever the outcome.
