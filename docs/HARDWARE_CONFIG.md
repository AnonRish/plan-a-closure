# Hardware configuration

What the plan-a-closure trial needs from a host cluster, written so that an operator can answer it in writing, and the record
to fill in for the report. Items marked **(operator)** can only be supplied by the operator. Nothing here assumes a particular
cluster: where a cluster has less hardware, the request scales down to tier 0.

## A. Request tiers

| tier | what | what it decides | exclusive time |
| --- | --- | --- | --- |
| 0, pilot | one GPU (H100, H200 or B300), bare-metal root, the NVML energy counter, and one independent **absolute-power** channel for that GPU | whether the pipeline, the meter alignment and the slack/floor probe work on the device: `preflight`, `hw-selftest`, `hw-probe`, a `smoke` T1 (1 h), `hw-state` | about 3 h |
| 1, registered pass | one 8-GPU node, absolute power per GPU or per baseboard, a TAP on one frontend NIC with a separate capture host, a separate verifier host | the registered T1 (`hw-full`), T2 and T3 | about 46 h: 4 gates + 12 reference + 24 blind audit + 6 for T2 and T3 |
| 2, replication | the same on a second node or on another day | independent replication, which is what turns a result into evidence | as tier 1 |

Trial profiles at 1 s windows: `smoke` 1 h (30 + 30 min), `hw-short` 12 h (6 + 6), `hw-full` 36 h (12 h reference + 24 h audit).
A first request can be tier 0 alone; its output tells both sides whether tier 1 is worth the machine time. Tier 0 is one
unattended command, `closure tier0 --confirm-hardware --gpu 0`, that an operator can run without the requester present:
[OPERATOR_TIER0.md](OPERATOR_TIER0.md) explains what it does to the machine and what to send back.

## B. Configuration to request

| item | minimum | preferred | why |
| --- | --- | --- | --- |
| compute node | tier 0: one GPU. Tier 1: one bare-metal 8 x H200 or H100 SXM node, root, Ubuntu 22.04 or 24.04 | a second identical node | T1 calibration and blind audit |
| driver, CUDA, Python | a production driver exposing the NVML energy counter, CUDA 12.x, PyTorch 2.x (CUDA build), Python >= 3.10 | same, versions frozen and recorded | `closure preflight` fails without the energy counter |
| GPU control (root) | `nvidia-smi -pm 1`; permission to lock SM clocks (`-lgc`, `-rgc`) and to set the power limit (`-pl`) | same | `hw-probe` sweeps clocks it reads from the GPU's supported list, and caps at or above its minimum, and restores both afterwards; calibration needs stable clocks |
| independent power | **absolute power in watts**, DC-coupled and calibrated (shunt, Hall-effect sensor, or PSU/PDU outlet metering), per GPU or baseboard, >= 1 kHz, exported as `timestamp_s,power_w` | >= 10 kHz, per rail; scope-rate traces reduced with `closure dcbus-decimate` | assumption A6: a meter the prover cannot spoof. An AC-coupled current probe (a Rogowski coil, say) has no DC response, so it cannot give energy: it suits workload signatures, not closure. `dcbus-analyze` rejects such traces |
| time sync | NTP, offset recorded | PTP to < 1 ms | `dcbus-analyze` estimates residual skew, but a good clock helps |
| network (T3) | one frontend NIC mirrored through a passive optical TAP to a capture host; classic pcap (`tcpdump -w`) | 100G TAP, capture host with a 100G NIC and >= 2 TB NVMe, headers only (`-s 96`) | traffic closure and tap-loss check. At full line rate of 1500-byte frames, header-only capture fills 2 TB in about 35 minutes: capture the served rate, not the link rate |
| verifier host | separate CPU host on the TAP'd link, >= 16 cores, >= 64 GB RAM | same, holds the signing key | verifier independent of the prover |
| memory (T2) | >= 256 GB host RAM, full device HBM | same | the residency challenge fills device and host memory |
| environment | inlet and outlet temperature, fan power if available | NVML temperature and clocks at 1 Hz | explain drift (assumption A2) |
| scheduling | an exclusive, whole-node allocation for the full duration (Slurm `--exclusive` or equivalent) | repeat on another day | sample sizes in the pre-registration |
| approvals | written permission for sustained high power, clock locking and hidden-load injection | an operator on call during the audit | the audit and the probe deliberately stress the GPUs |

## C. Questions for the operator

Answers in writing are enough; each fills a field in section D.

1. **Accelerators and topology.** Model, count, SXM or PCIe/NVL, interconnect, per node; which are free for exclusive use; which are instrumented.
2. **Independent power.** Instrument model; measurement point (PSU, baseboard bus, per-GPU rail, PCIe auxiliary); sensor type; **whether the channel is DC-coupled and reports absolute watts**; calibration method and uncertainty; sample rate; export format.
3. **Time.** NTP or PTP; the measured offset between the meter host and the compute node.
4. **Network.** TAP model and line rate; capture host NIC and storage; which NIC is mirrored; whether that link carries IPv6, VXLAN or other encapsulation.
5. **Software and control.** Driver, CUDA and kernel versions; container policy; whether clocks and power limits can be changed; BMC and BIOS access.
6. **Scheduling.** Allocation form, longest continuous reservation, earliest start date, how to reserve the exclusive window.
7. **Environment.** Cooling type; whether inlet and outlet temperature or fan power are logged.
8. **Policy.** Permission for sustained load and hidden-load injection; the conditions for publishing results (the plan is full publication within 30 days of the run, whatever the outcome).

## D. Record to fill in (pre-registration section 8)

| field | value | source |
| --- | --- | --- |
| cluster, node, date | | operator |
| GPU model, count, SM clocks, power limits | | `closure hw-selftest`, operator |
| driver, CUDA, PyTorch versions | | `closure preflight` |
| energy counter available | | `closure preflight` |
| meter model, measurement point, sample rate, calibration | | operator |
| meter is DC-coupled and absolute | | operator; `meter_check` in `results_dcbus.json` |
| clock source and measured offset | | `closure dcbus-analyze` output |
| TAP model, line rate, capture host | | operator |
| cooling and ambient notes | | operator |
| slack and energy floor (`probe.json` sha256) | | `closure hw-probe` |
| inference stack and versions (T1b) | | the person running the trial |
| git commit, source hash, profile, seed | | `prereg.json` (`code.git_commit`, `code.src_sha256`) |
