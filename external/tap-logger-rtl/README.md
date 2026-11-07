# tap-logger-rtl

A Verilog SHA-256 **hash-chain frame logger**, with the Python reference and verifier it is checked against.

A passive network tap copies traffic to a recomputation server. For anyone later to rely on that copy, the server
needs a way to show that the frames it holds are exactly the frames the tap saw, in order, with none dropped,
reordered or altered. A hash chain over the frames does that: every digest depends on the previous one, so changing
anything changes everything after it, and one published chain head pins the whole history. This repository is the
hardware-description side of that step (frame bytes in, chain digests out) plus the software that checks it.

```
D(-1) = GENESIS
D(i)  = SHA-256( D(i-1) || be64(i) || be64(ts_i) || frame_i )          docs/FORMAT.md
```

It does one thing and says what it does not do. It does not sign the head, keep time, store frames, or run at line
rate (see Throughput).

## Contents

| path | what |
| --- | --- |
| `rtl/sha256_core.v` | SHA-256 compression function, one round per clock, 67 cycles per block |
| `rtl/tap_logger.v` | framing, header injection, padding, chain update, record handshake |
| `rtl/sha256_consts.vh` | FIPS 180-4 constants, generated from their definition by `tools/gen_consts.py` |
| `tb/` | Verilog testbenches: core vs whole padded messages; logger with random stalls, back-pressure, reset |
| `tlref/` | Python reference chain, verifier, pcap reader, simulation and synthesis harness, `tap-log-verify` CLI |
| `tests/` | 44 tests: reference, RTL in two simulators, synthesis, gate level |
| `tools/mutate_rtl.py` | injects 24 hardware bugs, one at a time; the simulation suite must catch each |
| `docs/FORMAT.md` | exact byte format, worked example with literal digests, port list |

## Quick start

```bash
pip install -e ".[dev]"          # needs iverilog, verilator, yosys, g++ for the RTL tests
make test                        # 44 tests: reference, RTL (Icarus and Verilator), synthesis, gate level
make lint                        # verilator -Wall and iverilog -Wall, both clean
make mutate                      # 24 injected hardware bugs, all caught

tap-log-verify make-log capture.pcap > log.jsonl            # reference log of a capture
tap-log-verify verify capture.pcap log.jsonl --head <hex>   # exit 1 and the first bad record if anything differs
tap-log-verify sim capture.pcap                             # run the capture through the RTL in simulation
```

Every pcap record is one frame and its timestamp (nanoseconds) is the 64-bit timestamp, so any capture works as
input, including the corpus of [`packet-forge`](https://github.com/AnonRish/packet-forge):

```
$ tap-log-verify sim packet-forge/corpus/all-cases.pcap
RTL (iverilog): 376 frames, 23259 bytes, 101135 cycles; testbench errors=0; independent re-verification: OK
$ tap-log-verify make-log packet-forge/corpus/all-cases.pcap > log.jsonl
$ tap-log-verify verify packet-forge/corpus/all-cases.pcap log.jsonl --head cd1d8fe3b75b9ba717263cc230d0e5bb24d853bc8e5b8c902237aa89e6423adc
OK: 376 records verified, head cd1d8fe3b75b9ba717263cc230d0e5bb24d853bc8e5b8c902237aa89e6423adc
```

## Interface

One byte per beat in (`s_tdata`, `s_tvalid`, `s_tlast`, `s_tready`, with `ts_in` held for the frame), a record out
(`log_index`, `log_len`, `log_ts`, `log_digest`, `log_valid`/`log_ready`) and the running `chain_head`. Parameters
`TS_EN` (hash the timestamp; default 1) and `GENESIS`. The next frame is not accepted until the previous record is
taken; a consumer stalled for far longer than a frame takes to hash cannot cause a record to be lost (tested, and
the property a mutant that removed it was caught on). Full port list in `docs/FORMAT.md`.

## Throughput (measured in simulation)

A hash chain is serial by construction: the first block of frame *i* contains `D(i-1)`, so frame *i* cannot start
hashing before frame *i-1* finishes. This design also has a single block buffer, so a 64-byte block is first shifted
in (64 cycles) and then compressed (67 cycles), without overlap.

| frame | cycles per frame | bytes per cycle |
| --- | --- | --- |
| 64 B | 266 | 0.24 |
| 128 B | 398 | 0.32 |
| 512 B | 1189 | 0.43 |
| 1500 B | 3301 | 0.45 |
| 9000 B | 18739 | 0.48 |

Cycle counts are exact for no stalls and are asserted by `tests/test_rtl.py`. Whether the design closes timing at
any clock is **not** established (no place-and-route or timing analysis was run), so there is no Gb/s figure here;
for scale, at an assumed 100 MHz it would log about 30,000 frames a second of 1500 bytes, well under 1 Gb/s.
**This is a correctness-first reference, not a line-rate logger.** The natural scaling path is a two-level chain:
hash each frame independently (parallelisable across many cores) and chain only the 32-byte leaf digests
(`D(i) = SHA-256(D(i-1) || be64(i) || leaf_i)`, two blocks per frame). That changes the format and has not been built.

## Synthesis

Yosys 0.33 generic `synth` (no technology mapping), `check -assert` clean (no latches, loops or undriven nets):
9,645 cells, of which 2,468 flip-flops; the core alone is 6,913 cells and 1,065 flip-flops. No area or timing on any
target device. The synthesised
netlist is re-simulated with the same testbench (below).

## Verification

`VERIFICATION_LOG.md` lists every defect found, what each check is independent of, and what is not established. In
short:

* the core against hashlib on the FIPS examples, 11 lengths around the padding boundaries, a 768-byte message and 40
  random messages; the logger against the reference chain on **every frame length from 1 to 300 bytes**, with and
  without timestamps and with a custom genesis, under random source stalls and consumer back-pressure, with a
  mid-run reset, a consumer stalled for 1,500 cycles, and frames up to 70,000 bytes;
* what the hardware *emitted* is re-verified in Python with `verify_chain`, independently of the testbench's own
  comparison, and the reference is checked against coreutils' `sha256sum`;
* the testbench is shown able to fail (wrong digest, timestamp or genesis are reported);
* Icarus Verilog and Verilator agree record for record and cycle for cycle; the yosys netlist, for two parameter
  sets, matches the reference at gate level;
* constants are generated from the FIPS definition, not typed in, and regenerate identically;
* 24 injected hardware bugs (wrong rotate, constant, padding boundary, byte order, lost records under
  back-pressure, ...) are all caught.

## Limits

* Simulation and synthesis only. Nothing ran on an FPGA or ASIC, and there is no timing result.
* The SHA-256 core was checked by simulation, not formally proven, and is not hardened against side channels.
* One 8-bit stream, frames of 1 to 2^29 bytes. No frame-error or abort signalling: a frame is whatever arrives
  between `s_tlast` markers. Reset discards a frame in flight.
* No signing, no time source (`ts_in` comes from outside), no storage. Tail truncation of a log is invisible
  without a separately published head.
* One clock domain; no clock-crossing logic.

## Overlap with existing repositories

None found. Related, at other layers: `ai-2040-verification/tamper_log.py` (a software log with JSON entries and
Ed25519 signatures) and `tap_reader`'s commitments (Rust, BLAKE3). Neither shares this format or hash, and nothing
here is interchangeable with them; a signed checkpoint of `chain_head` would be the natural join.

Apache-2.0, copyright AnonRish.
