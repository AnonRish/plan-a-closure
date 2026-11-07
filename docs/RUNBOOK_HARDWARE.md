# Runbook: running the trial on real hardware

Everything below is **untested on a GPU** until you run it; `closure hw-selftest` is the first gate. The hardware request
(tiers, configuration, questions for the operator) is in [HARDWARE_CONFIG.md](HARDWARE_CONFIG.md).

## 0. Access

| cluster | route | notes |
| --- | --- | --- |
| Amodo Side Channel Cloud | the sign-up form at https://sidechannel.cloud/ | free for open-source and non-profit work; opens in hardware waves |
| Verifiable Compute Foundation (operated by Lucid) | the Research Access Program interest form on https://verifiablecompute.ai/ | free access for verification research; beta at the time of writing |
| Compute Verification Project | the "Get in touch" link under its entry on the Get Involved page of the Verification Plan | runs a competition against its inference-versus-training protocol |

Clusters are normally scheduled (for example with Slurm): ask for an exclusive, whole-node allocation for the full duration,
and for the permissions listed in HARDWARE_CONFIG.md section B.

## 0b. Tier 0 in one command

```bash
closure tier0 --confirm-hardware --gpu 0 --out runs/tier0      # about 2 h on one GPU, unattended
```

It runs sections 1 to 5 below on one GPU (unit tests, `selftest`, `preflight`, `hw-selftest`, `hw-probe`, `hw-state`, a
smoke T1 with the probe bound in and the pre-registration stamped by `ots` if installed, `verify`), logs every step, and
writes `runs/tier0/SUMMARY.md` and `runs/tier0/tier0_bundle.tar.gz` without the private key. An operator can run it alone:
[OPERATOR_TIER0.md](OPERATOR_TIER0.md) is their guide. `closure tier0 --mock` rehearses the sequence on fake hardware. The
sections below are the same steps by hand, plus the Tier 1 run.

## 1. Setup (on the node)

```bash
git clone https://github.com/AnonRish/plan-a-closure && cd plan-a-closure
python -m venv .venv && . .venv/bin/activate       # Python 3.10 or newer
pip install -e ".[test,hw]"             # hw = pynvml + torch (use the CUDA build your node needs)
pytest -q && closure selftest           # must pass before anything else
export CLOSURE_IFACE=<tap-nic>          # only for TAP capture checks
closure preflight                       # NVML, energy counter, torch.cuda, NTP, tcpdump, interface
```

Fix every `FAIL`. If the NVML energy counter is unreadable the run aborts; it never falls back silently. Hardware commands
run without the `hw` extra stop with a message that says what to install. `WARN` lines do not stop a run but say what will
be weaker: not root (no clock or power variants), MIG on, persistence off, other processes on the GPU, no fp8 below compute
capability 8.9, less than 8 GB free.

## 2. Gate: does the evidence chain look sane?

```bash
closure hw-selftest --gpus 0,1,2,3,4,5,6,7 --windows 30 > selftest.json
```

Expect `r2 > 0.9`, `idle_power_w` near the node's idle draw, `pass: true`. Send `selftest.json` to the operator.

## 3. Slack and energy floor (pre-registered H1.6 and H1.7)

```bash
closure hw-probe --confirm-hardware --gpu 0 --out runs/probe.json        # as root: it locks clocks and sets the power limit
```

It runs the same duty-cycled GEMM + memory-pass work at several rates ("levels", a share of the reference stack's measured
capacity) under the reference stack and under allowed variants (clock caps, power caps, precision, kernel library), plus
int8 and fp8 GEMMs for the floor and cheap activation patterns on the reference stack (`--operands sparse90,lowent,zeros`;
weights stay Gaussian). It reads the NVML energy counter and writes a sealed `probe.json`:

- `s_max`: the larger of `s_stack`, the largest one-sided 95% upper-confidence energy saving of an *allowed* stack variant (it
  keeps up with the work rate and is at least as accurate as the reference within `--rel-tol`), and `s_operand`, the same for
  the activation patterns (exempt from the accuracy check, because their outputs differ by construction), over all levels
  including idle. Noise inflates it, never shrinks it. Operand slack is the room a matched-energy attack uses (Kimpson, Baker
  and Graham, arXiv 2610.07476): declared work on cheap data, the saved energy spent on covert work.
- `e_floor_j_per_flop`: the lowest dynamic (above-idle) joules per FLOP over everything swept, int8 and fp8 included (integer
  operations count as FLOPs; fp8 needs compute capability 8.9 or newer and is dropped with a note elsewhere). Activation
  patterns never set the floor. It is an empirical floor over the swept space; widen the sweep (`--clocks`, `--power-caps`,
  `--precisions`, another `--dim`) before relying on it, and bind the probe with the lowest floor.
- `declared_band_j_per_flop` and `band_over_floor`: the measured range of declared-work joules per FLOP and
  (hi - lo) / e_floor, the first term of Kimpson et al.'s Eq. 18 per unit of declared utilisation.
- exit status 0 only if at least three allowed stack variants were measurable and a floor was found; `notes` explain any
  dropped variant (unsupported clock, missing library, a precision the device cannot run).
- clocks and power caps: `--clocks auto` (default) picks six SM clocks from the device's own supported list and
  `--power-caps auto` keeps every cap at or above the settable minimum; `settings` in `probe.json` records the choice.

About 40 minutes per GPU with the defaults. Clocks and the power limit are restored on exit; check with
`nvidia-smi -q -d CLOCK,POWER` if it was interrupted. `--mock` runs the same logic on a fake rig. To probe a served-model stack for
T1b, subclass `closure.hw.probe.TorchRig` (or any object with `prepare`, `measure`, `reset`, `info`).

## 4. State closure on device memory

```bash
closure hw-state --device cuda:0 --block-mb 64 --blocks 32 --k 8 --trials 200 --park-frac 0.25
```

`pass: true` means host-parked blocks are caught by time at <= 1% false alarms. Otherwise raise `--block-mb`.

## 5. T1 (NVML channel)

```bash
closure hw-trial --confirm-hardware --profile smoke --gpus 0 --probe runs/probe.json \
                 --pause-after-prereg --out runs/T1-smoke           # 1 h pilot
closure hw-trial --confirm-hardware --profile hw-full --gpus 0,1,2,3,4,5,6,7 --probe runs/probe.json \
                 --pause-after-prereg --out runs/T1-nvml            # registered sample sizes, 36 h
```

It calibrates, writes `prereg.json` (which pins the probe's sha256, the git commit and a hash of the package source), **stops**
so you can timestamp it (`ots stamp runs/T1-nvml/prereg.json`), then runs the blind audit with hidden-load injections. This
stresses the GPUs: use a reserved node, stay inside power and thermal limits, and follow the operator's policy. `hw-short`
(12 h) is a shorter first pass. `--probe` puts the measured energy floor and slack into the report: the headline then includes
the **slack-inflated gap**, and without it the report says plainly that slack was not measured. A `--mock` probe is refused for
a hardware trial.

## 6. T1 (independent power channel)

The channel must be **absolute power in watts**: DC-coupled and calibrated. Export it as `timestamp_s,power_w` (UNIX epoch
seconds, NTP/PTP-synced clock), then:

```bash
closure dcbus-decimate bus_raw.csv bus.csv --window-ms 1               # only if the raw trace is huge (10 MHz is ~9e11 rows a day)
closure dcbus-analyze --run runs/T1-nvml --csv bus.csv                 # estimates the clock offset, re-fits, re-audits
closure dcbus-analyze --run runs/T1-nvml --csv bus_mw.csv --scale 0.001 --ts-unit ms    # unit conversion if needed
```

Writes `results_dcbus.json` (status `HARDWARE+DCBUS`) with a `meter_check` block. The command **refuses** a trace that looks
AC-coupled (mostly zero-mean, or many negative samples): such a probe carries no DC level, so it cannot give joules.
`--force-meter` labels the report `METER UNVERIFIED` instead. A bus-to-NVML energy ratio far from 1 is flagged: check units
(`--scale`) and which rails the meter covers. Only the `HARDWARE+DCBUS` report supports a claim that does not rely on the
prover's own driver.

## 7. Verify and publish

```bash
closure verify runs/T1-nvml        # chain, signature, commitment, prereg, results and probe hashes
```

Before the first audit also timestamp the protocol itself (`ots stamp docs/PREREGISTRATION.md`) and tag the commit. Publish the
run directory (with `probe.json`) **except `signing_key.bin`**, the private signing key: anyone holding it can forge the chain.
`.gitignore` already excludes it, so `git add` is safe, but a hand-made zip or tarball is not. Add the hardware configuration
(docs/PREREGISTRATION.md section 8). Report FAILs.

## 8. Traffic closure

```bash
sudo tcpdump -i $CLOSURE_IFACE -s 96 -w tap.pcap
closure traffic-check tap.pcap verified.json     # verified.json: {"6|10.0.0.1:5000|10.0.0.2:443": payload_bytes}
```

The verified byte counts must come from the verified request/response evidence, not from the prover. The pcap is streamed in
constant memory; IPv4 and IPv6 (`"6|2001:db8::1:5000|2001:db8::2:443"`) over TCP or UDP, with at most one VLAN tag, are
attributed to flows. **Everything else on the wire counts**: ARP, ICMP, IP fragments, IPv6 extension headers and other
encapsulations are reported as unparsed wire bytes by reason, and the check fails unless `--unparsed-tol-bytes` explicitly
accepts them (state the tolerance before the run). pcapng is not supported: capture with `tcpdump -w` or convert with
`editcap -F pcap`.

## What can go wrong

| symptom | likely cause | action |
| --- | --- | --- |
| `underpowered: true` | drift is slow; too few independent blocks | longer reference run (`hw-full`), lock clocks, fix cooling |
| calibration `normal_p` < 0.01 | non-Gaussian residuals | more regimes, longer blocks, or use the conformal path with more data |
| FPR above 3 x alpha | non-stationary hardware state | recalibrate in the same session; log firmware, clocks, temperature |
| DC-bus gap much worse than NVML | NVML under-reports or the bus meter is noisy | report both; do not claim the NVML number |
| `slack` evades | expected: that is assumption A4 | `hw-probe` measures `s_max`; the report prints the slack-inflated gap. If it is large the energy bound is weak, and that is the result |
| `hw-probe` exits 1 | fewer than three allowed variants, or no floor | read `notes`: unsupported clocks are dropped; without root, clock and power variants are dropped (`needs root`); locks that did not take effect are dropped (`was not applied`); widen the sweep |
| `dcbus-analyze` refuses the trace | AC-coupled or sign-inverted channel | get a DC-coupled, calibrated channel (shunt, Hall sensor, PSU/PDU meter) |
| `traffic-check` fails on unparsed bytes | frames that are not TCP/UDP over IP | account for them, filter them at capture and say so, or tolerate them explicitly |
