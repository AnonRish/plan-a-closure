# packet-forge

A corpus of adversarial TCP segment overlaps, a pcap generator, and a normalising reassembler that flags
conflicting overlaps. It exists to test **passive network taps**: the tap and the endpoint it is watching must
agree on what bytes crossed the wire, and TCP lets a sender make them disagree.

The thing a tap sees is segments; the thing an endpoint reads is a stream. When two segments cover the same
sequence numbers with different bytes, which bytes "win" is up to the receiver's stack. A sender that controls
the segments controls which stream a tap reconstructs versus which one the endpoint acts on. For AI-compute
verification (AI 2040, Plan A) the tap is how a recomputation server learns what a model was asked and what it
answered, so a tap that silently picks one reading can be steered.

packet-forge gives you:

* **59 cases** (`corpus/*.pcap`, `corpus/manifest.json`): 8 benign controls, 43 overlap geometries and orderings,
  2 insertion tricks, 6 protocol anomalies. Each has a written description and an expected outcome per policy.
* **A reassembler** that never silently chooses. It reports every byte range on which two segments disagree
  (whatever the policy), the frames involved, whether the later copy arrived after the peer had ACKed the range,
  and the stream each policy would deliver. `packet-forge check` exits non-zero on ambiguity.
* **Ground truth from a live Linux kernel**: `packet-forge kernel-verify` replays every case into the kernel's own
  TCP stack through a TUN device and records the bytes the application reads.
* **A scorer** for any tap, a normaliser that rewrites a capture so overlaps agree, and an adapter that runs the
  corpus through the `tap_reader` Rust crate in [`ai-2040-verification`](https://github.com/AnonRish/ai-2040-verification).

## Quick start

```bash
pip install -e ".[dev]"                     # Python >= 3.10; the library itself has no dependencies
packet-forge list                           # the cases
packet-forge show ov-head-ooo-pq            # one case: description, events, expected streams
packet-forge check corpus/ov-tail-inorder.pcap
packet-forge check my-capture.pcap --json   # exit 0 clean, 1 ambiguous, 2 error
packet-forge generate out/ --ipv6 --vlan 100  # the corpus as IPv6 / VLAN / raw-IP / nanosecond pcaps
packet-forge normalize in.pcap out.pcap --policy first
packet-forge taps --kernel corpus/kernel_observed.json   # built-in reference and flawed taps
sudo packet-forge kernel-verify --out kernel.json --permutations --fuzz 1500   # needs root and /dev/net/tun
packet-forge tap-reader                     # needs cargo; runs the corpus through tap_reader
python -m pytest                            # 86 tests; kernel tests skip without root, Rust tests without cargo
```

Example (real output):

```
$ packet-forge check corpus/ov-tail-inorder.pcap
capture corpus/ov-tail-inorder.pcap: 7 frame(s), 7 TCP segment(s), checksums: verify
flow 192.0.2.1:40026>192.0.2.2:80  claims=3 bytes=30 syn=yes fin=- holes=none
  stream[first ]    25 B  sha256=610086c3d6e78944 complete
  stream[last  ]    25 B  sha256=ac71fb41c7e538dc complete
  stream[lowseq]    25 B  sha256=610086c3d6e78944 complete
  stream[linux ]    25 B  sha256=610086c3d6e78944 complete
  policies DISAGREE: the reassembled stream depends on the receiver's overlap rules
  CONFLICT stream bytes [15,20): 2 distinct value(s), claims from frames 5,7 late-after-ACK frames=7
verdict: AMBIGUOUS
```

## Policies

A policy decides which claim owns an overlapped byte. Four are shipped; conflicts do not depend on the policy.

| policy | rule | reproduces the Linux receiver on |
| --- | --- | --- |
| `first` | earliest captured wins | 996 / 1500 random scenarios |
| `last` | latest captured wins (naive overwrite-on-retransmit) | 954 / 1500 |
| `lowseq` | lowest start offset wins, ties to earlier | 1429 / 1500 |
| `linux` | lowest start, then longer, then earlier; delivered bytes frozen; SYN payload ignored | **1490 / 1500**, 57 / 58 corpus cases |

Measured against kernel 6.18.44 (seed 20261002). `linux` is a model of one kernel version, not the kernel; it is
known to be wrong in two documented ways (see `VERIFICATION_LOG.md`). The recorded kernel bytes for every case are
in `corpus/kernel_observed.json`, so the ground truth does not depend on the model.

## What the corpus covers

Overlap geometry (11 shapes: tail, head, contained, covering, same start/end longer/shorter, same range,
one-byte tail/head) in three contexts (bytes already delivered and ACKed; buffered beyond a hole, original first;
buffered beyond a hole, contradiction first), plus: chains of three, one-over-three, A-B-A, 32-bit sequence wrap,
retransmission before/after the ACK, a keep-alive probe with a garbage octet, a bad-checksum decoy (overlapping
and hole-filling), SYN payload, data after FIN, two FINs, IP-fragmented segment, mid-stream capture, a segment
before the ISN, and benign controls (reordering, exact and re-segmented retransmission, one-byte segments).
Benign cases matter as much as hostile ones: a tap that flags honest retransmission is unusable.

## Testing a tap

Anything that turns a capture into `(client->server stream, flagged?)` can be scored:

```bash
packet-forge score results.json --kernel corpus/kernel_observed.json     # {"case-id": {"stream_hex": "..", "flagged": false}}
```

A case passes when the tap flags it exactly when it is ambiguous (and, on unambiguous cases, reassembles the one
correct stream). Fidelity (does the stream equal what Linux delivered?) is reported separately. Built-in taps show
the corpus discriminates: the reference tap passes 59/59; a checksum-blind tap fails the hole-filling decoy; silent
taps (no conflict flag) pass only the 9 non-ambiguous cases; a tap that concatenates payloads passes 4.

## The tap_reader result

Run against `tap_reader` at the commit pinned in `adapters/tap_reader/Cargo.toml`, with the kernel as reference:
**0/58 as-is** (its frame parser delivers Ethernet padding as payload) and **34/58 with padding trimmed**, so that
only `ReorderBuffer` is measured. Both leads from the previous report reproduce. Details, causes and reproduction
in [`docs/FINDINGS-tap_reader.md`](docs/FINDINGS-tap_reader.md).

## Verification

[`VERIFICATION_LOG.md`](VERIFICATION_LOG.md) lists every defect found while building this, what each check is
independent of, and what is not established. In short: builder and parser agree with scapy and tshark; the interval
assembler agrees with a per-byte oracle on thousands of random scenarios; hand-computed expectations; tcpdump and
tshark referee checksums and benign reassembly; the live kernel referees the rest; and 17 injected bugs are all
caught by the tests.

## Limits

* One endpoint stack is modelled against live evidence (Linux 6.18.44, default sysctls, no SACK/timestamps/Fast Open).
  Other operating systems differ and are not tested; the generic policies are mechanisms, not claims about them.
* IPv4/IPv6 fragments are flagged, not reassembled. TCP options are parsed past but not interpreted (no PAWS/SACK).
* One stream per 4-tuple per capture. The whole capture is held in memory.
* All traffic is synthetic; nothing here has seen a real tap, switch or inference server.

## Overlap with existing repositories

Nothing found. The closest relation is deliberate: `ai-2040-verification/tap_reader` is the code this tests. The
sibling `recompute-sim`, `fides`, `verification-ledger` and `tamper_log.py` do not touch TCP reassembly.

## Layout

`src/packet_forge/` library and CLI · `corpus/` generated cases, manifest, SHA256SUMS, recorded kernel bytes ·
`tests/` · `adapters/tap_reader/` Rust adapter and the report's two leads as Rust tests · `tools/mutation_check.py` ·
`docs/SPEC.md` definitions and report schema.

Apache-2.0, copyright AnonRish.
