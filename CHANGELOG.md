# Changelog

## 0.6.2

- **The notebook cannot lose a run.** `notebooks/tier0_colab.ipynb` runs with Runtime > Run all. One cell runs Tier 0,
  then the mock training run, then copies the bundle, `SUMMARY.md` and `drill.json` to Google Drive (optional) and
  downloads them. Nothing waits on a later cell that a dropped session could break, as run 2's download did. The
  setup cell fails fast without a GPU, checks out an exact ref (`REF`, `main` by default), prints the commit, and sets
  persistence mode. `tests/test_notebook.py` checks this structure.
- **Which code ran.** `closure tier0` prints the git commit it runs from (and whether tracked files differ) and puts it
  in `SUMMARY.md`; a version number alone does not pin the code.
- **Drift is reported.** `closure drift --run <trial folder>` compares audit blocks without hidden energy with the
  calibration blocks (mean shift, spread, idle power, energy per unit), and `SUMMARY.md` shows it with the trial's SM
  clock. It is a diagnostic of assumption A2, not a criterion; on run 3 it flags the drift found by hand
  (shift -1.30 calibration SDs, spread 3.08x).

## 0.6.1

After Colab T4 runs 2 and 3 (8 November 2026), which went through every step (`docs/DEVIATIONS.md` sections 2 and 3;
run 3's bundle and a drift analysis in `results/shakedown-2026-11-08-colab-t4-run3/`).

- **hw-state reaches its own target.** With 8 of 32 blocks parked, an 8-block challenge touches a parked block at
  most 93.0% of the time, so the registered 99% was out of reach (run 3: 94.0%). The challenge size is now chosen
  from the hypergeometric so that sampling alone reaches 99.9% (17 of 32 blocks), and the result reports the parked
  count, the sampling limit, and detection among the challenges that touched a parked block. Criterion unchanged.
- **The trial runs at one clock.** `hw-trial` and `hw-selftest` take `--lock-clock-mhz`, lock the SM clocks for the
  run, record the lock in `prereg.json` and unlock afterwards. `closure tier0` picks the highest clock `probe.json`
  shows the GPU holding at full load under its power limit (1110 MHz on run 3's T4), because run 3's unlocked energy
  model drifted between calibration and audit. Pre-registration amendment v0.4.
- **The notebook survives a restarted session.** The summary, download and mock-run cells find the newest run folder
  when the session has forgotten it (run 2's bundle was lost this way), and the notebook says to download straight
  away.

## 0.6.0

Treaty mechanisms: what the halt and treaty proposals need from verification, made concrete enough to compute, test or
run (`src/closure/treaty/`, `closure treaty ...`, `docs/TREATY_COVERAGE.md`).

- `thresholds`: the compute thresholds the proposals name, with their sources, and how many days a fleet needs to run
  a threshold-sized training run in secret at the hidden rate a trial measured (`covert-days --run <trial folder>`).
- `deterrence`: per-period and winner-take-all deterrence conditions, and a CUSUM over block residuals against the
  time a sustained hidden load needs to reach a threshold run. Closed forms are checked against simulation.
- `coalition`: the middle-powers agreement's activation threshold on bundled World Bank GDP and population data, the
  smallest activating coalitions, Shapley-Shubik power, and its redline ladder with the six-month persistence rule,
  leak escalation and the risk-averse presumption.
- `mockrun`: A Narrow Path's mock training run on CPU or one GPU. The provider stops the job when energy divided by the
  device's energy floor reaches the budget, and checks the job's starting weights against its seed.
- `geoloc`: delay-based chip location over TCP (the chip connects out, so NAT is fine), with Ed25519-signed challenges.
- `inspection`, `beacon`, `quorum`: inspection sample sizes and unpredictable samples, commit-reveal randomness and
  sortition, and k-of-n approval of critical actions.
- New tests: `tests/test_treaty.py`, and `tests/test_treaty_torch.py` (the FLOP formula against torch's own counter,
  and the drill on CPU).

## 0.5.5

After the first run on real hardware: a Colab T4 shakedown (8 November 2026) that stopped at `hw-selftest`
(`docs/DEVIATIONS.md` section 1, the bundle and logs in `results/shakedown-2026-11-08-colab-t4/`).

- **The unit of work fits the GPU.** It was a fixed 8192 x 8192 bf16 GEMM plus a 1 GiB pass, 2 to 3 ms on an H100 but
  about 0.54 s on a T4, five times the 100 ms slot, so every load level above zero ran flat out and energy had no varying
  work to track. `TorchLoad` and the probe's `TorchRig` now halve the size from 8192 until one unit takes at most a fifth
  of a slot (`hw/workloads.py: size_unit`), and run in the device's native half precision: bf16 from compute capability
  8.0, fp16 before it (V100, T4), where bf16 has no tensor cores. On an H100 nothing changes.
- **Units are counted as they finish**, not at the end of each slot.
- **Capacity is the GPU's own.** `p_max` was a fixed 700 W; hardware commands now read the power limit from NVML and
  measure idle power at start, and `hw-trial` records both, with the unit of work, in `prereg.json` (`cfg.p_max_w`,
  `cfg.workload`). With 700 W a T4 trial would have labelled each hidden load with about 15 times the energy injected.
- **`hw-selftest` checks that the load levels differ** (the units at 25% load under 80% of those at 100%), prints the
  units and power per level and the unit of work, and explains a failure. The r2 > 0.9 threshold is unchanged.
  Pre-registration amendment v0.3 (`docs/PREREGISTRATION.md`), made before any audit data exist.
- **`closure tier0` passes hw-selftest's unit on** to `hw-probe` and `hw-trial` (`--dim`, `--mem-elems`, new on both
  and on `hw-selftest`), and `SUMMARY.md` reports the hw-selftest result.
- `notebooks/tier0_colab.ipynb` (with `docs/OPERATOR_TIER0.md`): the Tier 0 pilot on a free Colab GPU as a labelled
  shakedown; it prints the installed version and writes each run to a fresh folder.
- New tests: `tests/test_unit_size.py` (sizing, precision choice, idle measurement, the self-test's checks and
  diagnoses, the tier0 hand-off); in `tests/test_torch_cpu.py` a time-scaled copy of the T4 run that fails on the old
  load generator and passes on the new one; probe auto-sizing in `tests/test_probe.py`.

## 0.5.4

- compute-ledger, packet-forge and tap-logger-rtl now have their code on GitHub, with the same trees as the vendored
  copies. `external/MANIFEST.json` points at those repositories and commits, and `external/README.md` no longer says
  they are empty.

## 0.5.3

For operators who run the pilot without sudo.

- **A run without root ends cleanly.** Its final `hw-restore` was refused just as every earlier clock or power change
  was, so the summary listed it as failed although nothing on the GPU had been changed. `hw-restore --same-user`, which
  `tier0` passes, now reports "nothing to restore" in that case. Run on its own, a refused `hw-restore` still fails and
  says to use root, because it cannot know who ran the probe; any other failure still shows as one.
- `docs/OPERATOR_TIER0.md` installs by cloning the public repository and says what a run without root covers;
  `docs/PUBLISH.md` says how to update the published repository to a new release.
- New tests: the refused restore in `test_gpu_identity.py`, and a whole `tier0` run without root in
  `test_hw_rehearsal.py`.

## 0.5.2

Hardening for whoever lends the GPU. Found by rehearsing the hardware path end to end against a fake NVML and a fake
nvidia-smi.

- **The right GPU, always.** `--gpu N` was used as the NVML and nvidia-smi index too, but NVML ignores
  `CUDA_VISIBLE_DEVICES` and numbers GPUs in PCI order. Under a scheduler that hands a job physical GPU 3 as `cuda:0`,
  the probe would have read GPU 0's energy counter and locked GPU 0's clocks, which may be someone else's job.
  `hw/gpu.py` now matches the CUDA device to its NVML GPU by UUID (or PCI address), refuses to guess when it cannot, and
  passes the UUID to every `nvidia-smi -i`. `hw-selftest` and `hw-trial` read NVML for the same GPUs that torch loads.
  `preflight --gpu N` prints the match and fails without one. CUDA devices are numbered in PCI order unless the
  environment chose otherwise.
- **The GPU is put back on SIGTERM, Ctrl-C and SIGHUP**, not only on a normal exit. A scheduler time limit used to kill
  `hw-probe` with clocks locked. Now the first such signal restores clocks and power limit before exiting, and further
  signals are held off while the restore runs. `tier0` passes a signal to the running step instead of killing it, skips
  the rest, and still writes the summary and the bundle. `tier0` ends with a new step, `hw-restore`, that always runs
  and sets the power limit back to the value it found. `closure hw-restore --gpu N` does the same by hand after a
  SIGKILL.
- **Without root the probe degrades instead of aborting.** Clock and power variants are dropped and noted ("needs
  root"); precisions and operand patterns are still measured.
- **Locks and caps are checked, not trusted.** A clock lock the GPU does not report, or a power limit NVML does not
  show, drops that variant ("was not applied"). Some virtual machines accept `nvidia-smi -lgc` and change nothing.
- **Bounded run time.** A slot that takes five times its length skips its remaining units; the variant is infeasible
  anyway, and energy per FLOP counts the units actually run. A pathologically slow variant can no longer eat the
  allocation.
- Power caps are fractions of the GPU's default limit; after each variant the limit goes back to the value it had at the
  start.
- New tests: `test_gpu_identity.py`, and `test_hw_rehearsal.py`, which runs `closure tier0 --confirm-hardware` end to end
  on CPU torch against `tests/fakegpu/` (NVML and nvidia-smi fakes), including SIGTERM mid-probe, SIGKILL followed by
  `hw-restore`, no root, and no-op clock locks. CI installs CPU torch on Python 3.12 so these run on every push. A
  rehearsal is labelled `REHEARSAL` everywhere and is refused as input to a hardware trial. Tests: 229 -> 237, plus 11
  with torch installed (was 5).

## 0.5.1

- **CI** (`.github/workflows/ci.yml`) now also runs `closure external check` and the Tier 0 pilot on a simulated GPU,
  on Python 3.10 to 3.13, and keeps going on other versions when one fails. A manual run (Actions, "Run workflow", tick
  the box) also runs the 13 vendored suites. README shows the CI badge.
- **`.gitattributes`** turns off line-ending conversion, so a Windows checkout keeps every file byte for byte and the
  vendored trees still match their hashes in `external/MANIFEST.json`.
- `docs/PUBLISH.md`: push as the pseudonymous account even when Git already has another account's credentials, and
  check that every file in the archive was committed.

## 0.5.0

- **The other AnonRish repositories are in the archive.** `external/` carries 13 of them (fides, weight-diode,
  covert-timing-warden, cuda-guard, frontier-verify, ai-2040-verification, ai-2040-plan-a-toolkit, assurance-curves,
  aisecurity-rfds, continental-load-registry, compute-ledger, packet-forge, tap-logger-rtl), each with its own code, tests,
  README and licence. `external/MANIFEST.json` pins each tree by hash and records its source commit, every difference
  from that commit, and its own test suite's result as run here. `closure external test` runs each suite in its own
  pytest process (own configuration, own `src/` on the path, counts from JUnit XML); `closure external check` fails if a
  tree changed after it was tested or a cited test did not pass. The `external` extra installs what the suites need.
- **Coverage rows point into that code.** `closure coverage` accepts `external/<repo>/<file>.py::<name>` and checks it by
  parsing the file (no import, so a repository's own dependencies are not needed to validate the matrix). Plan A matrix:
  implemented 21 -> 27, hardware-gated 16 -> 22, external 11 -> 0, partial 10 -> 11, not started 2 -> 0. Rows that moved,
  with what still keeps a row partial written in its note: VP-0.3, VP-2.3, GI-WS-05, GI-WS-08, GI-OP.5 to implemented;
  VP-IO.3, VP-2.14, GI-WS-04, GI-WS-11, GI-WS-16, GI-OP.6 to hardware-gated; VP-IO.8b, VP-3.8, GI-T3, GI-OP.2, GI-OP.3
  from external to partial; GI-WS-07 and GI-WS-09 from not started to partial. Hardwired-pause matrix: HP-3.3.3f to
  hardware-gated, HP-3.3.4e to partial; external 2 -> 0.
- **Evaluation metrics** (`metrics.py`, `closure metrics`; VP-2.8 partial -> implemented): the plan's six metrics as typed
  scorecards with the plan's wording. The assurance curve is computed from the plan's formula; execution difficulty,
  preparation, privacy, economic cost and scope are recorded judgments, each with a basis, and out-of-range cards are
  refused.
- **Recomputation for newer architectures** (`frontier.py`; GI-WS-09 not started -> partial): a mixture-of-experts check
  that accepts a different routing only when router scores are tied within a stated tolerance and reports when it did,
  and speculative decoding checked against the target model alone, exact under sampling with a committed seed (Gumbel-max,
  the DiFR idea). Toy models.
- `pytest` no longer recurses into `external/` or `runs/`. `START_HERE.md` tells someone who received the archive what
  to run without a GPU (about 15 minutes) and with one (Tier 0). The operator guide starts from the zip and adds an
  optional run of the vendored suites on the node, as an ordinary user.
- Vendored suites as recorded here: 2,708 passed, 72 skipped (68 aisecurity-rfds placeholders for RFDs it has not
  started, 4 frontier-verify tests that need a confidential-computing GPU), none failed; all 34 cited tests passed.
- Tests: 212 -> 229, plus 5 torch-on-CPU tests. New: `test_external_manifest.py`, `test_metrics.py`, `test_frontier.py`,
  and README checks that keep the status table and the vendored-run table equal to the matrix and the manifest.

## 0.4.0

- **Runs on more GPUs as shipped.** `hw-probe --clocks auto` (the default) picks six SM clocks the device actually supports
  (NVML's supported-clock list, just below the maximum down to a quarter of it), and `--power-caps auto` raises 0.7 and 0.5
  of the default limit to the device's settable minimum, so no variant is spent on a clock or cap the GPU refuses;
  `probe.json` records where both came from. `preflight` adds warnings (never failures) for root, MIG, persistence mode,
  other processes on the GPU, the clock and power-limit ranges, the GPU model and compute capability, int8 and fp8 support,
  and free memory. The hardware extra installs `nvidia-ml-py` (the `pynvml` package is deprecated).
- **The torch code runs on CPU for testing.** `TorchRig` and `TorchLoad` take a `device` (and `TorchRig` a `control`
  switch), synchronise only on CUDA, and `tests/test_torch_cpu.py` runs the probe rig (activation patterns, int8 via
  `torch._int_mm`, fp8 via `torch._scaled_mm`), the load generator, the residency prover and the reproducibility check on
  CPU torch 2.15. Skipped where torch is absent. CUDA timing, NVML and clock control remain hardware-gated.
- **Secure network gateway** (`gateway.py`, `closure redteam`): Plan A's gateway upgrade and RFD 017's SNG/SRC as a
  protocol: boot whitelist, hash-chained I/O log, keyed sampling committed before serving and revealed after,
  recomputation within a conformal tolerance, and a red team (LoRA delta, requantised weights, another model, tampered
  outputs). Plan A rows VP-IO.7 and GI-WS-02 move from external to hardware-gated; GI-WS-10 to implemented.
- **Hashing tap** (`taphash.py`, `closure tap-commit`, `closure tap-compare`): fixed-size group digests with
  position-bound Merkle leaves, openings and nonce-derived challenges (Cankaya's tap design). GI-WS-03: partial ->
  hardware-gated. `traffic.iter_pcap(..., with_payload=True)` and `write_pcap(..., payloads=...)` carry payload bytes.
- **Tap presence** (`tapwatch.py`): keyed canaries at unpredictable times with ciphertext-like payloads; missing, late and
  replayed canaries are reported. GI-WS-12: partial -> hardware-gated.
- **Training-cadence detector** (`cadence.py`, `closure cadence-check`): defence in depth for the hardwired pause's 3.3.3,
  calibrated on null traces by a conformal quantile, refusing traces below 2 Hz. HP-3.3.3h: not started -> hardware-gated.
- Sources re-checked on 6 November 2026: the Get Involved page (updated 9 July 2026) still matches every SITREP status in the
  matrix; `scripts/crosscheck_upstream.py` agrees with the pause authors' current repositories.
- Tests: 190 -> 212, plus 5 torch-on-CPU tests. `test_hp_matrix_does_not_overclaim` now checks that the cadence row is
  labelled defence in depth instead of requiring a not-started row.

## 0.3.0

- **The probe now measures where a matched-energy attack hides.** Kimpson, Baker and Graham (arXiv 2610.07476) hide at
  least 0.41 of an A100's capacity by running the declared work on cheap operands and spending the saved energy on covert
  int8 work. `hw-probe` now runs activation patterns on the reference stack (`--operands sparse90,lowent,zeros`; weights
  stay Gaussian) and reports their saving as `s_operand`, exempt from the numerics gate because their outputs differ by
  construction; `s_max` is the larger of `s_stack` and `s_operand`. int8 (`torch._int_mm`) and fp8 (`torch._scaled_mm`)
  join the default floor sweep and are dropped with a note where the GPU or torch cannot run them; activation patterns never
  set the floor. The probe also reports the declared-work band (`declared_band_j_per_flop`) and `band_over_floor`, the first
  term of their Eq. 18. Hardware-gated: the logic is tested on the fake rig and the dispatch on a fake torch.
- **`closure tier0` runs the whole one-GPU pilot unattended.** Unit tests, `selftest`, `preflight`, `hw-selftest`,
  `hw-probe`, `hw-state`, a smoke T1 with the probe bound in, and `verify`; each step's command, output, exit status and
  duration are logged; `SUMMARY.md` collects the headline numbers; `tier0_bundle.tar.gz` holds everything except
  `signing_key.bin`. `docs/OPERATOR_TIER0.md` is the operator's guide. `hw-trial --stamp-prereg` stamps the pre-registration
  with `ots` when installed and logs its hash, without waiting for Enter.
- Pre-registration v0.2, amended before any audit data exist: `s_max` includes operand slack, the floor sweep includes int8
  and fp8, and `--stamp-prereg` is accepted.
- README: credits Kimpson et al.; the Rahman and Tajdari sentence now says what that paper measured (1 Hz NVML, 98%,
  counters assumed untampered, white-box LoRA the hardest case); the hardwired-pause numbers are marked as checked against
  v1.0.1 (v1.0.2 followed on 26 October 2026).
- Tests: 181 -> 190 (9 new).

## 0.2.1

- **Efficiency slack and energy floor are now measurable.** `closure hw-probe` (`hw/probe.py`) measures the pre-registered H1.6
  slack (`s_max`) and H1.7 energy floor (`e_floor`) with duty-cycled windows at fixed work rates, and writes a sealed
  `probe.json`. `hw-trial --probe` and `sim-trial --probe` bind its sha256 into `prereg.json`; the report gains the
  slack-inflated gap (or says plainly that slack was not measured); `closure verify` checks the probe hash; the hardwired-pause
  `bridge` charges the slack-inflated gap when it exists. Hardware-gated: the torch rig has not been run on a GPU; the logic is
  tested on a fake rig and its control flow on a virtual clock.
- **The independent meter must be absolute power.** `dcbus-analyze` now rejects traces that look AC-coupled (no DC level, many
  negative samples), reports a bus-to-NVML energy ratio, and accepts `--scale` and `--ts-unit`. New `dcbus-decimate` reduces very
  large traces in constant memory.
- **Traffic closure no longer drops frames silently.** The pcap reader streams in constant memory, parses IPv6 as well as IPv4,
  and counts frames it cannot attribute to a TCP/UDP flow (ARP, ICMP, fragments, extension headers, truncated files) as unexplained
  wire bytes; `traffic-check` fails on them unless `--unparsed-tol-bytes` accepts them. pcapng is refused with an explanation.
- `prereg.json` records a hash of the package source (`code.src_sha256`), so the code is pinned even when it is run from a zip.
- Hardware and docs: `HARDWARE_CONFIG.md` rewritten as a request with tiers (a one-GPU pilot and the full pass) and questions for
  the operator; `RUNBOOK_HARDWARE.md` and `PREREGISTRATION.md` describe the probe, the meter requirement and unparsed traffic; the
  README credits the workload-classification papers accurately.
- Hardware commands that need `pynvml` or `torch` now stop with the install command instead of a traceback; the upstream
  cross-check says which requirements to install; `requires-python` is now `>=3.10`, matching the tested versions.
- Found by the end-to-end verification drill: `hw-probe --out`, `dcbus-decimate` and `coverage --write` now create missing output
  directories (`closure hw-probe --out runs/probe.json` used to crash in a fresh checkout); the private `signing_key.bin` in a run
  directory is called out when it is created and in the runbook (never publish it); `pytest -v` prints one line per test (the repo
  config no longer forces `-q`).
- Tests: 152 -> 181 (29 new; the 82 hardwired-pause tests are unchanged).

## 0.2.0

Closure core, Plan A modules, hardware scaffolding, and the hardwired-pause layer.
