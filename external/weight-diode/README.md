# weight-diode

One-way transport for model weights. A sender pushes a signed, erasure-coded carousel of datagrams; a receiver verifies every
symbol, rebuilds the file, and checks it against an allowlist. **The receiver cannot transmit: it has no socket, no reply
path, no acknowledgements and no retransmission requests.** That is what a hardware data diode needs from the protocol on top
of it.

It addresses *Path from the storage bank to the inference units* on the
[Plan A get-involved page](https://ai-2040.com/supplements/verification-plan/get-involved), graded **not on track**:
moving weights into verified inference units likely needs partitioned networks and data diodes, and the page reports no work
seen. The diode itself is hardware. This repository is the software half: framing, loss tolerance, integrity and
authorisation with nothing flowing back.

Python 3.10+, NumPy, `cryptography`. 158 tests. No real diode or network isolation was involved; the "link" is loopback UDP and
an in-memory impairment model.

```
pip install .            # console script: weight-diode
```

## How it works

1. **Code.** The file is cut into blocks of `k` symbols and each block gains `r` parity symbols from a systematic Cauchy
   Reed-Solomon code over GF(256). Any `k` of the `n = k + r` symbols rebuild the block (MDS; checked exhaustively).
2. **Commit.** Every coded symbol is a leaf of one RFC 6962 Merkle tree. The root, file size, file SHA-256, code parameters, a
   serial number and a label form a **manifest**, signed with Ed25519.
3. **Carousel.** Datagrams are sent in interleaved order (symbol `j` of every block, then `j + 1`), so a burst of `L`
   consecutive losses costs each block at most `ceil(L / blocks)` symbols. The manifest leads each pass three times and repeats
   every 32 packets, so a receiver can join at any time and losing one copy costs nothing.
4. **Receive.** A symbol is believed only if its Merkle proof verifies against the signed root **at its exact position**. A
   manifest is believed only if it parses strictly, fits the configured limits, carries a signature from a trusted key, is on the
   whitelist of approved file hashes (if one is set) and is not below `min_serial`. At the end the assembled file must match the
   signed SHA-256 or nothing is released.

## Numbers

**Overhead and loss tolerance for 1 TB of weights** (`weight-diode overhead`, closed form, exact byte accounting):

| symbol | k | r | blocks | wire / file | proofs share of wire | P(file completes), 5 % loss, one pass |
| --- | --- | --- | --- | --- | --- | --- |
| 1 KiB | 32 | 8 | 30.5 M | 2.48x | 48.5 % | 0.000000 |
| 8 KiB | 200 | 55 | 610 k | 1.42x | 9.7 % | 1.000000 |
| 8 KiB | 100 | 28 | 1.22 M | 1.42x | 9.7 % | 0.999992 |

Two lessons. Proofs cost `32 * log2(#symbols)` bytes per datagram, so small symbols waste half the link. And loss tolerance has
to be judged at file scale: 30 million blocks each with a tiny failure probability is a certain failure, which is why
`min_redundancy` and multi-pass carousels exist.

**Datagram size matters.** At 1 TB and 8 KiB symbols the largest datagram is 9,110 bytes, which overflows even a 9,000-byte
jumbo frame; IP fragmentation would multiply the effective loss. The largest symbol that fits is 8,054 bytes
(`analysis.max_symbol_size`, `overhead --mtu`).

**Real loopback UDP transfer** (`examples/benchmark.py`): 1 MiB, 20 % of datagrams dropped before sending, 3 passes: complete in
0.1 s; receiver saw 1,023 accepted symbols, 668 duplicates, 59 duplicate manifests.

**Throughput of this reference implementation** (pure NumPy, one sandbox core; yours will differ): encode including hashing
and signing about 20 to 27 MiB/s; receive including proof verification about 45 MiB/s; Reed-Solomon with k = 200, r = 55 encodes
at about 4 to 5 MiB/s and decodes at about 4.7 MiB/s when 55 data symbols are missing (560 MiB/s when none are). **That is
roughly three orders of magnitude below a 10 Gbps link.** Production erasure coding uses SIMD table lookups at gigabytes per
second per core. The protocol and its checks are the point here, not the speed.

## Use

```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from weight_diode import Encoder, Receiver, LossyLink

key = Ed25519PrivateKey.generate()                       # the verifier's approval key
enc = Encoder(weights_bytes, key, symbol_size=8000, k=200, r=55, serial=12, label="model-v12")
rx = Receiver([key.public_key()], whitelist=[approved_sha256_hex], min_serial=12)
for datagram in LossyLink(0.1).transmit(enc.stream(passes=3)):
    rx.feed(datagram)                                     # returns an event label, e.g. "symbol_accepted", "complete"
weights = rx.result(enc.manifest_id)                      # None unless complete AND hash-verified
```

CLI: `keygen`, `hash`, `overhead`, `send --file --key --to host:port`, `recv --port --pubkey [--whitelist] [--min-serial] --out`.

## What it does and does not protect

* **Integrity and authorisation.** Only a file whose hash is on the whitelist and whose manifest a trusted key signed can be
  released. Forged, replayed-at-another-position, cross-manifest and bit-flipped symbols are rejected individually and the
  transfer still completes from the good ones.
* **Rollback.** `min_serial` blocks an older validly signed manifest. It is only as good as whoever persists that number.
* **A lying signer releases nothing.** If the signed hash does not match the signed contents, the receiver refuses the file.
* **Not confidentiality.** Weights travel in the clear. Not sender identity either: the signature proves approval of the
  manifest, not who sent the datagrams.
* **Not availability.** Anyone who can inject datagrams can waste the receiver's time (proof checks, signature checks on
  manifests; the rejected-manifest cache is bounded at 1,024 entries), but cannot make it accept bad data.
* **One-wayness is not enforced by software.** This code never transmits from the receiver (checked structurally and at runtime),
  but only a hardware diode makes that physical.

## How it was verified

* **Code.** GF(256) table against an independent shift-and-xor multiplier on all 65,536 pairs, and the field axioms over all
  16.7 M triples. The code is MDS: every `k`-subset decodes, exhaustively for six `(k, r)` up to `(6, 6)` (924 subsets), random
  and adversarial subsets at `(200, 55)`, and `n = 256`.
* **Merkle.** The nine RFC 6962 test roots for sizes 0 to 8, which were written down from memory before being compared, all
  matched. Against the separate `pymerkle` implementation: 8,433 inclusion proofs across trees of size 1 to 511, none differing.
  Every single-bit flip in a proof is rejected.
* **Theory against the real thing.** The binomial formulas for block and file success are checked against the actual decoder
  (it decodes exactly when at least `k` symbols survive, 3,000 patterns) and against 500 complete `Encoder` to `Receiver`
  transfers at 30 % loss, within 5 sigma. Byte accounting is exact against what the encoder emits, and the closed-form proof
  total against a brute-force sum.
* **Attacks**, each with a negative control that disables the check and shows the attack then succeeds: random forged symbols,
  symbols from an attacker's own valid tree, position replay, cross-manifest replay, untrusted signer, non-whitelisted file,
  rollback, a signer who lies about the hash, resource limits, and 6,000 fuzzed datagrams that never raised and never corrupted
  the result.
* **Real sockets.** A UDP loopback transfer with a runtime spy confirming the receiver's socket never calls `send*`, an AST check
  that the receiver module imports no networking and the receive loop only binds and receives, and a CLI round trip including a
  wrong-key run that receives nothing.

Defects found along the way are in [`VERIFICATION_LOG.md`](VERIFICATION_LOG.md): a protocol flaw (symbols before the first
manifest were discarded), a **denial of service in my own receiver** (one corrupted manifest datagram blocked the genuine one
for good), and an O(N) overhead routine that never finished at terabyte scale.

## Limits, stated plainly

* **Reference implementation, not a streaming one.** The file, every coded symbol and the whole Merkle tree live in memory
  (the tree keeps every level: about 64 bytes of hashes per symbol before Python object overhead, so roughly 10 GB for 1 TB at 8 KiB symbols). A TB-scale sender needs an external-memory tree or
  per-block subtrees.
* **Speed**, as above.
* **Loss model.** The closed forms assume independent loss. Real links lose in bursts; interleaving defends against a burst of up
  to roughly `blocks * r` consecutive datagrams, and the tests check bursts and a Gilbert-Elliott channel, but the formulas are
  optimistic for correlated loss.
* **Blocks are at most 256 symbols** (GF(256)). Larger `n` needs a different field or a different code.
* **The 16-byte header's `flags` and `reserved` bytes are not authenticated** and carry nothing.
* **No key management, clock or persistence.** The trusted keys, whitelist and `min_serial` come from you.
* The code and tests share an author and have had no external review.

Related: `AnonRish/ai-2040-verification` has `weight_transport.py` (the approval-manifest chain for moved weights) and
`wipe_reload_cycle.py` (reload-time arithmetic that uses a diode bandwidth figure). This repository is the transport underneath
those: use its measured overhead in place of a raw bandwidth figure.

## References

Cauchy Reed-Solomon codes: Roth and Lempel, *On MDS codes via Cauchy matrices* (1989); Blomer et al., *An XOR-based
erasure-resilient coding scheme* (1995). RFC 6962 and RFC 9162 (Merkle audit paths); Ed25519 (RFC 8032). Plan A get-involved page, ai-2040.com (July 2026).

## License

Apache-2.0. Copyright 2026 AnonRish.
