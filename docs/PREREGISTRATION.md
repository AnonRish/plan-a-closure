# Pre-registration v0.2 (freeze and timestamp BEFORE any audit data exist)

Freeze procedure: commit this file and the analysis code; timestamp this file (`ots stamp docs/PREREGISTRATION.md`); run
`closure hw-probe` first (section 3, H1.6 and H1.7); record the git commit and a hash of the package source in the run's
`prereg.json` (`code.git_commit`, `code.src_sha256`; the source hash pins the code even when it is run from a zip); the probe's
sha256 is bound into `prereg.json` as well (`cfg.probe_sha256`); run with `--pause-after-prereg` and timestamp `prereg.json`
(e.g. `ots stamp`) when prompted, or with `--stamp-prereg` (used by `closure tier0`), which stamps it with `ots` when
installed and logs its hash either way, without waiting for input.
Any deviation is appended to `docs/DEVIATIONS.md` with a timestamp and reason; the original analysis is still reported.

Amendments. v0.2 (6 November 2026), made before any audit data existed (no hardware run has taken place): `s_max` also
covers operand slack, the energy-floor sweep adds int8 and fp8, and `--stamp-prereg` is accepted. Reason: Kimpson, Baker and
Graham (arXiv 2610.07476) hide compute on an A100 with a matched-energy attack that uses exactly these two places, cheap
operands for the declared work and int8 for the covert work.

## 1. Definitions

- **Window** `dt`=1 s. **Block** `L` windows. **Cluster capacity** per block = `n_gpu × p_max × L × dt`.
- **Hidden fraction** = hidden energy in a block / cluster capacity energy of that block.
- **Detected** = the combined test (energy OR busy-time, each at alpha/2) flags the block.
- **f95** = smallest log-binned hidden fraction from which every populated bin is detected >= 95%.
- **Closure gap** = pooled f95 over non-slack classes (combined channels).
- **Slack-inflated gap** = closure gap + `s_max × (mean predicted block energy / block capacity)`, where `s_max`
  is the larger of two measured energy savings relative to the calibration stack at the same verified work rate: `s_stack`,
  over allowed software stack variants, and `s_operand`, over activation patterns run on the calibration stack (90% zeros,
  values in {-1, 0, 1}, all zeros; the weight operand stays Gaussian, as a whitelisted model's would).
  Measured by `closure hw-probe`: the saving is `1 - P_variant / P_reference` in mean power at the same verified work rate,
  taken as the one-sided 95% upper confidence value, maximised over the counted variants and over the work rates measured
  (idle included). A stack variant is *allowed* if it keeps up with the work rate and its numerics are at least as accurate
  as the calibration stack's within `rel_tol` (0.5%). An activation pattern must keep up with the work rate; it is exempt
  from the numerics check because its outputs differ by construction. `s_max` is a share of total power but multiplies
  total predicted energy, and the maximum over rates is used, so the inflation is conservative. If `s_max` was not measured
  the report says NOT MEASURED and no slack-inflated gap is claimed.

## 2. Threat model

The breaker knows the verifier code, thresholds and calibration summary (Kerckhoffs), controls the hidden
workload (class, intensity, timing, software stack), and does **not** know the audit schedule or random seeds.
Classes: `constant`, `idle_gap` (only when verified load < 20%), `duty` (20 s period, 50%), `dilute` (small
fraction on few GPUs), plus the measured-not-injected `slack` probe. Out of scope: tampering with or colluding with
the independent meter, hardware modification, physical access, attacks on the verifier host.

## 3. T1: energy and busy-time closure (flagship)

Design. Verified load: synthetic GEMM + memory-bound passes at levels {0, .1, .2, .3, .5, .7, .9, 1.0} (T1a), then a
served model with tap-derived token counts (T1b). Profile `hw-full`: 360 reference blocks, 720 audit blocks,
`L`=120 windows, `alpha`=0.01, 3 regimes (36 h at 1 s windows); `hw-short` for a first pass (12 h). NVML run first, then
re-analysis with the DC-bus meter on the **same** run (`dcbus-analyze`). The independent channel must be absolute power in
watts, DC-coupled and calibrated: an AC-coupled current probe has no DC response and cannot give energy, and `dcbus-analyze`
rejects such traces (a forced run is labelled METER UNVERIFIED and does not support H1.5).

| id | hypothesis | decision rule |
| --- | --- | --- |
| H1.1 | calibration is valid | per regime: Jarque-Bera p >= 0.01 and `n_eff` >= 15; otherwise the run is reported UNDERPOWERED and no false-alarm claim is made |
| H1.2 | false alarms are controlled | on >= 200 null audit blocks, observed combined FPR <= 3 × alpha |
| H1.3 | sensitivity | non-slack classes: detection >= 95% at hidden fraction >= 5% (primary) or 2% (stretch), per class |
| H1.4 | bound validity | `H_ub` >= measured hidden energy in >= 95% of non-slack hidden blocks (hidden energy characterised in solo runs) |
| H1.5 | independent channel | DC-bus closure gap <= 1.5 × NVML closure gap, and DC-bus FPR satisfies H1.2 |
| H1.6 | slack | `closure hw-probe` measures `s_max` over >= 3 allowed stack variants (clock cap, power cap, precision, kernel library) and the activation patterns (operand slack, reported as `s_operand`); the sealed `probe.json` is bound into `prereg.json` before the audit; report the slack-inflated gap, `s_stack`, `s_operand` and `band_over_floor` |
| H1.7 | physics anchor | `closure hw-probe` measures `e_floor`: the lowest *dynamic* (above-idle) J/FLOP over the swept clocks, power caps, precisions (int8 and fp8 included where the device runs them; integer operations count as FLOPs) and kernel libraries at the probe's GEMM shape (one shape per probe: bind the probe with the lowest floor and report what was swept; activation patterns never set the floor); report hidden FLOPs and H100-hours per week at the gap. An empirical floor, not a proof of a physical limit |

Overall T1 outcome. **PASS-primary**: H1.1, H1.2, H1.4 hold and slack-inflated gap <= 5%. **PASS-stretch**: also gap <= 2%.
Otherwise **FAIL**: published in full. A FAIL with a measured gap is itself the result Plan A needs.

## 4. T2: state closure

Device memory and host DRAM filled with the verifier's AES-CTR stream (block >= 64 MB). Challenge `k` random blocks
with a fresh digest key.

| id | hypothesis | decision rule |
| --- | --- | --- |
| H2.1 | honest prover passes | false alarm <= 1% over >= 1,000 challenges |
| H2.2 | dropped stream is caught | digest mismatch with probability `1-(1-f)^k`; choose `k` for 99%: f=10% -> 44, 5% -> 90, 1% -> 459, 0.5% -> 919 |
| H2.3 | host parking is caught by time | 25% of blocks parked in host DRAM, detection >= 99% at false alarm <= 1% (`closure hw-state`) |

Not covered: persistent storage, NIC/DPU memory. Reported as limits.

## 5. T3: traffic closure

Tap capture beside a served model. H3.1 honest unexplained bytes within tolerance over >= 1 h. H3.2 injected unverified
flows at >= 1 kbit/s flagged within 60 s. H3.3 with a release-grid warden, >= 99.9% of releases on grid and the
capacity bound `rate × log2(1 + floor(D/g))` reported. Frames the parser cannot attribute to a TCP/UDP flow over IPv4 or IPv6
(ARP, ICMP, fragments, extension headers, other encapsulation) are unexplained wire bytes and count against H3.1 unless a
tolerance was stated before the run.

## 6. Analysis plan

Code frozen at the recorded commit. No optional stopping, no post-hoc removal of classes or blocks, no change of
alpha after the schedule reveal. Clopper-Pearson 95% bounds for all rates. Combined test uses Bonferroni
(alpha/2 per channel). Multiple classes are reported separately, never averaged into a headline.

## 7. Reporting

Publish `results.*`, `chain.jsonl`, `signature.json`, `raw.npz`, `prereg.json`, `schedule_reveal.json`, the hardware
configuration below and this file within 30 days of the run, whatever the outcome. Any weakness found in another
group's system is disclosed to them first and held for 30 days. Ask the cluster operator to repeat the run
independently with `closure hw-trial`; an independent replication is what converts a result into evidence.

## 8. Hardware configuration

Record the fields in docs/HARDWARE_CONFIG.md section D before the run; request the configuration in section B (tiers in
section A, questions for the operator in section C).
