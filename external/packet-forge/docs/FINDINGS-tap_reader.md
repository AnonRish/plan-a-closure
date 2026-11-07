# Findings: `tap_reader` against the packet-forge corpus

Subject: `tap_reader` in [`AnonRish/ai-2040-verification`](https://github.com/AnonRish/ai-2040-verification) at commit
`0199a4bd0411d682a3d02286148bdbf0e44d1e1d` (pinned in `adapters/tap_reader/Cargo.toml`). Reference for "what an
endpoint receives": the bytes the Linux 6.18.44 TCP stack delivered to a listening socket for the same segments
(`corpus/kernel_observed.json`). Nothing in `tap_reader` was modified.

These are behaviours, not blame. `frame.rs` describes itself as a benchmark parser rather than a general one, and
`reorder.rs` documents the wraparound simplification in a comment (lines 47-49). The point is what a tap built on
them would additionally need before it can be trusted to verify traffic from an adversarial sender.

## Result

| mode | what is fed to `ReorderBuffer` | stream equals the Linux receiver's on |
| --- | --- | --- |
| `asis` | exactly what `frame::parse` returns | **0 / 58** |
| `trim` | the same, cut to the IPv4 total length first | **34 / 58** |

`trim` exists so that finding 1 does not mask everything else. 58 = the cases that have a TCP handshake to replay.
`tap_reader` has no way to flag a case, so on the 50 ambiguous cases its detection score is zero by construction.

## The two leads from the previous report

Both reproduce, as Rust tests run verbatim (`adapters/tap_reader/tests/leads.rs`, `cargo test --release`):

1. **Wraparound.** `out_of_order_segment_across_the_sequence_wrap` fails exactly as predicted: `WORLD` is discarded as a
   duplicate (`0 < 0xFFFFFFF6` at line 45), `duplicates_dropped == 1`, nothing is pending, so nothing can repair it.
   The test is marked `should_panic` so that a fix makes it fail loudly. A consequence that was only a reading in the
   report is now run: after the wrap, an honest retransmission of already-delivered pre-wrap bytes is *not* `<
   next_expected`, so it is parked in `pending` forever (`stale_retransmission_after_the_wrap_is_parked_forever`).
2. **Conflicting retransmissions are invisible.** `conflicting_retransmission_is_silently_ignored` passes as written:
   `AAAA` is kept and `duplicates_dropped == 1`, identical to an honest duplicate.

## Findings

| # | behaviour | where | cases (kernel differs) | example: tap_reader vs kernel |
| --- | --- | --- | --- | --- |
| 1 | Ethernet padding is delivered as payload: the payload is sliced from the frame length, not the IP total length, so the 6 pad bytes of the handshake ACK arrive as stream data | `frame.rs` payload slice | all 58 as-is | first 6 bytes of every stream are `00` |
| 2 | Sequence wraparound: plain `<` against a wrapping counter | `reorder.rs:45,56` | `ok-wrap-out-of-order`, `ov-wrap-conflict-ooo` | `0123456789` vs `0123456789WORLD` |
| 3 | A segment starting below `next_expected` is dropped whole, including bytes beyond it | `reorder.rs:45-52` | `ok-resegmented-retransmit`, `ov-tail-inorder`, `ov-covering-inorder`, `ov-same-start-longer-inorder`, `ov-one-byte-tail-inorder` | `...PPPPPPPPPP` vs `...PPPPPPPPPPQQQQQ`; honest re-segmented retransmission loses 5 bytes |
| 4 | `pending` is keyed by start sequence and only an exact key match drains, so a buffered segment that begins before the delivered point never drains: its tail is lost and `gap_open()` stays true | `reorder.rs:64,71` | `ov-tail-ooo-*`, `ov-head-ooo-*`, `ov-one-byte-tail-ooo-*`, `ov-one-byte-head-ooo-*` (8) | `01234QQQQQQQQQQ` vs `01234QQQQQQQQQQPPPPP` |
| 5 | Two buffered segments with the same start: the later overwrites the earlier, even if shorter | `reorder.rs:64` | `ov-same-range-ooo-pq/qp`, `ov-same-start-shorter-ooo-pq`, `ov-same-start-longer-ooo-qp` | 10-byte `P` replaced by 5-byte `Q`: `...QQQQQ` vs `...PPPPPPPPPP` |
| 6 | No byte comparison, no conflict signal (lead 2) | `reorder.rs:45-50` | all 43 overlap cases | `duplicates_dropped` counts honest and hostile duplicates alike |
| 7 | No protocol awareness: bytes before the ISN, FIN, TCP checksum, IP fragments | `frame.rs`, `reorder.rs` | `anom-before-isn`, `anom-data-after-fin`, `anom-conflicting-fin`, `ins-bad-checksum-fills-hole`, `anom-ip-fragment` | decoy bytes with a bad checksum are spliced into the stream; data after FIN is delivered |

34 cases match: 6 of the 8 benign cases (in-order, reordered, exact duplicate, hole fill, one-byte segments,
wrap in order) and overlaps where the first-arrived bytes happen to win. The two benign failures are the honest
ones that matter most: re-segmented retransmission (finding 3) and an out-of-order segment past the wrap (finding 2).

## What passing this corpus would take

Not a patch, a requirement list: unwrap 32-bit sequence numbers against the highest offset seen; keep pending data
as intervals, trim each arrival against what is delivered and buffered, and keep the new tail; compare the bytes of
every overlap and count conflicts separately from honest duplicates (`ov-before-ack` and `ov-keepalive-garbage-byte`
mark the two places honest traffic can look hostile); take payload length from the IP header; stop at FIN; verify
the TCP checksum; surface IP fragments instead of misparsing them. `packet-forge`'s own reassembler does these and
is under 200 lines (`assembler.py`) if a reference is useful.

## Reproduce

```bash
cd adapters/tap_reader && cargo test --release     # the leads, verbatim
cd ../.. && packet-forge tap-reader                # the corpus, both modes, against the recorded kernel bytes
python -m pytest tests/test_tap_reader.py          # asserts the exact failure set above
```

If `tap_reader` is fixed the failure-set test fails by design; update `KNOWN_FAILURES` and this page.
