# Verification log

Every defect found while building tap-logger-rtl, with the evidence, then what each check is independent of, then
what is not established.

**No functional defect was found in the RTL by simulation: it passed on its first run** (core vs hashlib, logger on
every length 1 to 300). A design that passes first time says as much about the tests as about the design, which is why
the mutation check below matters: it shows the tests can see faults.

## Defects in my own work

| # | defect | how it was found | evidence | fix and guard |
| --- | --- | --- | --- | --- |
| 1 | Verilator `-Wall` flagged the core's `busy` output as unused in the logger | first lint | `UNUSEDSIGNAL: core_busy` | scoped lint pragma (the port is part of the core's interface and the core testbench uses it); lint is a test |
| 2 | The synthesis harness reported `cells=0, flip-flops=0`: its regex expected the count before the cell name, yosys prints the name first | first synthesis run | printed `{}` | parser fixed; `test_synthesis_is_clean...` asserts more than 5,000 cells and 2,300 to 2,600 flip-flops, so a vacuous parse cannot pass |
| 3 | The testbench passed parameters to a netlist that has none | first gate-level compile | `parameter TS_EN not found in tb_tap_logger.dut` | `GATE` define selects a parameterless instance |
| 4 | Gate-level simulation under Icarus ran at about 15 cycles per second (27 s for 2 frames), which made any real workload impractical and broke a 300 s command limit | first gate-level run | wall times | gate-level runs moved to Verilator; as a side effect it is a second, independent simulator, and `test_verilator_agrees_with_icarus...` compares both record for record and cycle for cycle |
| 5 | **The mutation suite failed on the unmutated design** (a keyword collision, `seed`), which would have "killed" every mutant vacuously | I ran the unmutated suite first | `logger() got multiple values for argument 'seed'` | `tools/mutate_rtl.py` now refuses to run unless the unmutated design passes; it caught a second such slip (duplicate `maxcyc`) immediately afterwards |
| 6 | **My first mutation harness edited `rtl/` in place; when its process was killed it left a mutated `tap_logger.v` behind** (padding boundary `6'd56`) with the `.orig` backup beside it | checking for leftover backups after the run stopped at mutant 9 | `grep` showed `cnt == 6'd56` in the real source | file restored from the backup and re-checked; the harness now mutates a temporary copy selected by `TLREF_RTL_DIR` and never touches the real sources. The same hazard existed in packet-forge's mutation tool and was fixed there too |
| 7 | **Mutant 19 survived**: a new frame could start before the previous record was taken. Random back-pressure of a few cycles never keeps a record pending for longer than a frame takes to hash, so the documented property "stalls the source rather than overwriting a record" was untested | mutation run, 1 of 24 survived | `SURVIVED #19 logger: next frame starts before the record is taken` | directed `+DELAY=` consumer mode in the testbench (takes each record exactly N cycles after it appears); tests at 60, 400 and 1,500 cycles; the mutant is now caught |
| 8 | A convoluted placeholder expression in the core cycle-count test, and an over-clever skip rule in `conftest.py` | re-reading | both read as working | both simplified |

## What was checked, and what each check is independent of

| check | against | result |
| --- | --- | --- |
| reference chain | coreutils `sha256sum` on hand-built messages (its own SHA-256, independent of hashlib/OpenSSL); literal digests in `docs/FORMAT.md` | equal, 80 messages; 6 documented digests |
| SHA-256 core | hashlib on FIPS 180-4 examples, 11 padding-boundary lengths, a 768-byte message, 40 random messages | 0 errors |
| logger | reference chain, every frame length 1 to 300, timestamps on; and off with a custom genesis | 0 errors, 600 frames |
| logger, handshakes | source stalls 0 to 90 %, consumer ready 15 to 100 %, consumer stalled for 60, 400 and 1,500 cycles | 0 errors |
| logger, reset | reset in the middle of frames at three different cycles; the chain restarts at index 0 | 0 errors |
| logger, size | frames of 1,500, 9,000, 9,018, 65,535 and 70,000 bytes | 0 errors |
| what was emitted | `verify_chain` in Python over the records the hardware printed | ok for every run |
| the testbench | wrong digest, wrong timestamp, wrong genesis supplied as expectations | each reported as errors |
| simulators | Icarus Verilog vs Verilator on 131 frames | same digests, same cycle count |
| synthesis | yosys `check -assert`; netlist re-simulated in Verilator, default parameters and `TS_EN=0` with a genesis; core netlist vs hashlib | 0 errors |
| constants | regenerated from the FIPS definition; spot values 6a09e667, 428a2f98, c67178f2 | identical |
| lint | verilator `-Wall` and iverilog `-Wall` | no output |
| the tests themselves | mutation: 24 injected hardware bugs, each in a temporary copy | 24 killed (23 of 24 on the first complete run; #7 above was the 24th, caught after the fix) |
| fresh clone | `git clone` into a new virtualenv, full test run | 44 pytest tests pass; `tools/mutate_rtl.py` there: 24 of 24 mutants caught |

## What this does not establish

* Simulation and generic-gate synthesis only. No FPGA or ASIC flow, no timing, no area on a real device, no power.
* The chain is checked against hashlib and coreutils by simulation. It is not formally verified, and a bug that
  hashlib and the RTL share by construction (the format itself) would not be found: the format is defined in
  `docs/FORMAT.md`, not derived from an external standard.
* Throughput numbers are cycles in simulation. No clock frequency is claimed.
* All frames are synthetic or from the packet-forge corpus; nothing here has seen a real tap or NIC.
* The code, testbenches and reference have one author and no outside review.
* The GitHub Actions workflow was written from commands run locally and has not run on GitHub.
