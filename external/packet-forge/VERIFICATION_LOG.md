# Verification log

Every defect found while building packet-forge, with the evidence, then what each check is independent of, then
what is not established. Defects are listed, not just fixed: the fix is in the history of the code, the evidence is here.

## Defects in my own work

| # | defect | how it was found | evidence | fix and guard |
| --- | --- | --- | --- | --- |
| 1 | `analyze._report_direction` raised `IndexError` building a conflict report when a covering claim began after the conflict range | first run of the generated corpus through the pipeline | traceback at the first conflicting case | look up the value only among claims covering the first conflicting byte; every corpus case now runs through `analyze` in `tests/test_corpus.py` |
| 2 | Conflicts were taken from whichever policy was listed first; with `linux` first (it ignores SYN payload) the conflict on `anom-syn-data` would vanish | code review while adding `drop_flags`; no test was failing | `test_conflicts_do_not_depend_on_which_policy_is_listed_first` fails on the reverted code (shown by mutation) | dedicated policy-independent conflict pass |
| 3 | The stream's FIN offset was "the first FIN to arrive", so `data-after-fin` depended on arrival order | all-arrival-orders pipeline test, case `anom-conflicting-fin~p021` | `{'conflicting-fin'} != {'conflicting-fin','data-after-fin'}` | earliest FIN offset in both the analyser and the expectation builder |
| 4 | The checksum-blind tap passed the whole corpus: no case had a bad-checksum decoy that did not also overlap real data | tap scoreboard (`packet-forge taps`) | `checksum-blind 59/59` before, `58/59` after | added `ins-bad-checksum-fills-hole`; `test_every_flawed_tap_is_caught` asserts the exact failing set |
| 5 | A hand-computed expectation was wrong: I assumed `SYNDATA!!!` and `REALDATA!!` differ on all 10 bytes; the last two (`!!`) agree | the test failed while oracle and pipeline agreed with each other | `[[0, 8]] == [[0, 10]]` | expectation corrected to `[0,8)`; the code was right |
| 6 | The scapy cross-check failed on an empty payload: scapy keeps Ethernet padding in the payload chain | hypothesis shrank to `payload=b''` | 6 zero bytes where none were sent | test strips scapy's `Padding` layer. This is the same trap as `tap_reader` finding 1, reproduced independently in a third implementation |
| 7 | Vacuous test code: an `... or True` assertion and a no-op loop standing in for a checksum check | re-reading the tests | both read as passing | replaced by a real scapy checksum recomputation on every rewritten frame |
| 8 | `case_frames` would have built a nonsense "IPv6 fragment" by calling the IPv4 fragmenter | review, before any run | none: caught by reading | raises `ValueError`; IPv6 corpora omit fragment cases (`test_ipv6_manifest_and_generation`) |
| 9 | My first oracle mutant (`<` to `<=` in the freeze guard) survived | mutation check | 15/16 killed | analysed: the guard is only evaluated when an incumbent exists, and the byte at the delivered watermark never has one, so the mutant is equivalent. Replaced by a killable boundary mutant (`< frozen_below - 1`); the equivalent one is kept and required to survive |
| 10 | **My first mutation tool edited `src/` in place** and restored it in a `finally`; a hard kill would have left a mutated file behind. The same design did exactly that in tap-logger-rtl, which is how I noticed | reviewing the tool after the failure in the sibling repo | a mutated `tap_logger.v` and its `.orig` backup left on disk | the tool now mutates a temporary copy imported through `PYTHONPATH` and refuses to run unless the unmutated copy passes |
| 11 | Documentation claims I had not checked: a README example typed from memory (wrong port and byte count), "every benign case matches" in the tap_reader findings (6 of 8 do), `assembler.py` "about 150 lines" (179), "91 tests" and "16 bugs" (86 and 17) | checking each against fresh tool output before committing | the regenerated outputs | the example is now verbatim output; the findings sentence names the two benign failures; the counts are the measured ones |

Model errors found by the kernel (the `linux` policy was written from reading `tcp_input.c`; the kernel corrected it):

| # | deviation | size | explanation |
| --- | --- | --- | --- |
| K1 | consistent with out-of-order coalescing: on `ov-chain-three-ooo` the kernel's output is exactly what appending a segment to a buffered one that ends where it starts predicts (it inherits that segment's start offset and beats B) | corpus `ov-chain-three-ooo`; 10 / 1500 random scenarios; 2 / 610 corpus permutations | the model ranks every segment by its own start. **The mechanism is inferred** from the kernel's output and from my memory of `tcp_input.c`; I did not read the kernel source here and did not verify each of the 10 misses individually. Supporting evidence: all 10 misses contain a segment that starts exactly where another ends, which holds in only 22.9% of the scenarios (chance of 10 of 10 if unrelated: about 4e-7). Whether the kernel coalesces would depend on its queue's internal structure, which is not modelled. Asserted by `test_recorded_observations_vs_model` (the corpus deviation must keep deviating) |
| K2 | FIN versus data ordering: whether data past a FIN is delivered depends on which arrived first | 8 / 610 corpus permutations (`anom-data-after-fin`, `anom-conflicting-fin`) | endpoint-defined; the reassembler flags `data-after-fin` / `conflicting-fin` instead of resolving it |

Divergences that are the point of a case, not model errors: SYN payload (kernel ignores it without Fast Open) and
IP fragments (kernel reassembles them, a tap that does not never sees the bytes).

## What was checked, and what each check is independent of

| check | against | result |
| --- | --- | --- |
| frame builder and parser | scapy: parses the same bytes, and recomputes IP/TCP checksums from scratch | 300 random frames (IPv4/IPv6, 0-2 VLAN tags, options); all equal |
| frame fields and checksum status | tshark `-T fields` on the whole corpus in IPv4, IPv6, VLAN and raw-IP encodings | every TCP segment (over 300 each) equal; IP fragments skipped because tshark reassembles them |
| bad checksums | tcpdump `-vv` | 2 incorrect, equal to the 2 decoy cases |
| benign reassembly | Wireshark Follow-Stream (`tcp.reassemble_out_of_order`) | 8 / 8 benign cases equal; on the 43 overlap cases it lands on one of our policies every time and equals the kernel on 40 |
| interval assembler | per-byte oracle written differently | 400 hypothesis examples and 3,000 dense overlap scenarios per policy, identical runs, conflicts and watermark |
| pipeline (pcap to report) | oracle expectations derived from the abstract events | 59 cases x 6 encodings, plus every arrival order of every case with up to 5 segments |
| expectations | worked out by hand | 14 tests, one of which exposed my own arithmetic error (#5) |
| endpoint behaviour | live Linux 6.18.44 TCP stack through a TUN device | 57 / 58 corpus cases, 600 / 610 permutations, 1490 / 1500 random scenarios (seed 20261002) for `linux`; `lowseq` 1429, `first` 996, `last` 954 |
| the tests themselves | mutation: 17 injected bugs, each in a temporary copy of the sources; the unmutated copy must pass first | 17 killed; 1 further mutant shown equivalent and required to survive |
| normaliser | re-analysis of its output | no conflicts, one stream for every policy, equals the input's stream under the chosen policy; idempotent; checksums valid per scapy |
| `tap_reader` | live kernel as reference, plus the two leads as Rust tests | `docs/FINDINGS-tap_reader.md` |
| fresh clone | `git clone` into a new virtualenv, full test run | 86 pytest tests and 4 Rust tests pass (kernel and Rust-adapter tests included); the mutation check there: 17 of 17 killed, and the equivalent mutant confirmed |

The corpus expectations come from the oracle, the oracle is validated by hand-computed cases and by the kernel, and
the kernel observations are recorded in `corpus/kernel_observed.json` so they can be re-checked without a kernel.

## What this does not establish

* The code, oracle and tests share one author and have had no outside review; the independent referees (scapy,
  tshark, tcpdump, the kernel) are independent of the code, not of my reading of TCP.
* The `linux` policy models one kernel version in one configuration (6.18.44 in a Firecracker guest, default sysctls,
  no SACK, timestamps or Fast Open). It is wrong in the ways listed above and has not been compared with any other
  operating system. `first`, `last` and `lowseq` are mechanisms, not claims about any stack.
* Fuzz scenarios have 2 to 5 segments and offsets under 40; larger or longer-lived flows, window limits, memory
  pressure and TCP options were not exercised.
* No real tap, switch, optical hardware or inference server was involved; all traffic is synthetic.
* The GitHub Actions workflow was written from commands run locally and has not run on GitHub.
