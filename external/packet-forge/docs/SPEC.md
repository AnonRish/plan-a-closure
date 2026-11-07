# Specification

Definitions used by the reassembler, the corpus and the reports.

## Streams and claims

A capture is split into **flow directions** (src ip, src port, dst ip, dst port). Each direction has a **stream**:
offset 0 is the first byte after the SYN (SYN consumes one sequence number). A **claim** is one captured segment's
payload placed at a stream offset: `(arrival, start, data, frame, acked_at_arrival, flags)`. Sequence numbers are
unwrapped against the highest offset seen, so wrap-around and streams beyond 4 GiB are handled; claims that start
before offset 0 are trimmed and reported as `before-isn`. Without a SYN the stream start is the lowest offset seen
(`midstream`).

## Conflicts

Two claims **conflict** on a byte when they cover the same offset with different values. Conflicts are
policy-independent: they are computed by a dedicated pass and reported as maximal ranges, with every claim that covers
the range (frame, extent, short hash of its bytes there), the number of distinct values at the first offset, and
`late_after_ack`: frames of claims that arrived after the peer had cumulatively ACKed the range start. A 1-byte
conflict carries a `hint` that it is shaped like a keep-alive probe (RFC 1122 §4.2.3.6), the one known honest source.
A flow can be ambiguous even when all policies reassemble the same stream (`ov-aba-*`: A, B, A).

## Policies

A policy is a ranking of claims (lower key wins an overlapped byte), a **freeze** flag (bytes already delivered in
order are never replaced; snapshot taken before each arrival is applied) and `drop_flags` (claims carrying these
annotations are ignored by that policy only).

| name | key | freeze | drop |
| --- | --- | --- | --- |
| `first` | arrival | no | - |
| `last` | -arrival | no | - |
| `lowseq` | (start, arrival) | no | - |
| `linux` | (start, -end, arrival) | yes | `syn-data` |

Two independent implementations exist: `oracle.py` (per byte, dictionary of incumbents) and `assembler.py`
(sorted non-overlapping intervals). `tests/test_assembler_vs_oracle.py` requires identical canonical content,
conflict ranges and delivered watermark.

## Capture handling

* Segments whose IP-header or TCP checksum is wrong are excluded (`bad-checksum`), as every conforming endpoint
  discards them; `--no-checksum` accepts them. Captures truncated by snaplen are marked `truncated` and their
  checksum is unverifiable.
* Payload length comes from the IP header, never from the frame length (Ethernet pads to 60 bytes).
* IPv4 and IPv6 fragments are not reassembled: reported as `ip-fragment` (frame-level).
* Payload on a SYN is a claim (`syn-data`); on RST it is ignored (`rst-with-data`).
* The stream ends at the **earliest** FIN offset; claims extending past it are `data-after-fin`; different FIN
  offsets are `conflicting-fin`. Whether late data is delivered depends on arrival order at the endpoint, which is why
  it is flagged rather than resolved.
* Linktypes: Ethernet (up to 4 VLAN tags) and raw IP; classic pcap only (microsecond/nanosecond, either byte order).

## Exit status

`packet-forge check`: 0 clean, 1 if any conflict or any anomaly in `FAIL_KINDS` (`syn-data`, `data-after-fin`,
`conflicting-fin`, `conflicting-syn`, `bad-checksum`, `ip-fragment`, `before-isn`, `truncated`, `rst-with-data`;
override with `--fail-on`), 2 on usage or I/O errors. `midstream` is informational.

## Report (`check --json`)

`{frames, tcp_segments, checksum_mode, frame_notes[], directions[]}`; each direction: `flow, base_seq, syn_seen,
claims, bytes_claimed, stream_end, fin_offset, holes[[a,b]], conflicts[{start,end,claims[],distinct_values,
late_after_ack[],hint}], anomalies[{kind,frames[],detail}], streams{policy:{length,sha256,complete,hex?}},
policy_divergent`.

## Corpus encoding

Client `192.0.2.1:40000+i` (IPv6 `2001:db8::1`), server `...2:80`; client ISN and server ISN fixed per case; MSS
option on SYN/SYN-ACK; 1 ms between frames; frames padded to 60 bytes. `manifest.json` holds, per case, the abstract
events and the expected conflict ranges, anomalies and per-policy streams, derived by the oracle from the events and
never from the pcap. `SHA256SUMS` covers every generated file; `packet-forge verify-corpus` regenerates and compares.

## Kernel replay

A TUN device gives the kernel `10.99.0.1` and a listening socket; the process plays `10.99.0.2`, completes the
handshake with hand-built packets, injects the case's segments in arrival order, then reads the accepted socket.
Observed bytes, EOF and reset are recorded with the kernel release.
