# Verification log

Defects found while building and testing this repository, in order, including the ones in the tests.
Nothing here was fixed quietly.

## 1. Protocol flaw found by the first end-to-end smoke test: symbols before the first manifest were discarded

A single-pass transfer at 15 % random loss finished only 8 of 13 blocks. Cause: the first manifest datagram was dropped, and
the receiver (correctly) refuses symbols until it has an accepted manifest, so 55 of 312 symbols, the whole burst before the
next periodic manifest, were thrown away. That is an extra, *correlated* loss of about 18 % at the start of every pass.
Fix: every pass now begins with `preamble = 3` copies of the manifest (and the manifest still repeats every 32 packets so a
receiver can join late). After the fix: 20 of 20 seeds complete in one pass at 15 % loss with zero symbols dropped for lack of a
manifest.

## 1b. Real receiver DoS: one corrupted manifest datagram permanently blocked the genuine manifest

Found while designing the corruption scenario, then reproduced deterministically before fixing
(`tests/test_manifest_dos.py`, both tests failed: the good copy came back `manifest_duplicate`, and a full transfer finished
with `result() is None`).

The receiver cached rejected manifests by `manifest_id`, but the id is `SHA-256(manifest bytes)[:8]` and does not cover the
signature. So a copy with one flipped signature bit has the same id as the genuine manifest; it was rejected for its bad
signature, its id went into the rejected cache, and every later genuine copy hit the cache and was ignored. Anyone able to inject
a single datagram on the one-way link could stop a transfer forever, and so could an ordinary bit error in the wrong 64 bytes.

Fix: verdicts that depend on the manifest bytes alone (structure, limits, whitelist, serial) stay cached by id; the signature
verdict is cached by `(id, digest of the signature)`, so a corrupted copy can only ever block itself. A header id that does not
match the manifest bytes is rejected without being cached at all, because that id is unproven attacker input.

## 1c. Scaling bug: `wire_overhead` was O(N) and never finished at terabyte scale

Found by running `examples/benchmark.py`, whose last section asks for the overhead of 1 TB of weights: everything before it
ran in seconds and that call had not returned after 150 s (the first attempt hit the 300 s limit). `wire_overhead` summed
`proof_length` over every leaf with a Python loop; a 1 TB file at 1 KiB symbols has 1.2 billion leaves. The same loop was in
`Encoder.wire_bytes_per_pass`, and the `overhead` CLI command would have hung the same way at realistic sizes. The tests only used
kilobyte-to-megabyte files, so nothing had exercised it.

Fix: a leaf's proof has one element per ancestor split, so the total over all leaves is the external path length of the RFC 6962
tree, `E(1) = 0`, `E(n) = E(k) + E(n-k) + n` with `k` the largest power of two below `n` and a perfect subtree of `2^m` leaves
contributing `m 2^m`. `merkle.total_proof_length` computes it in O(log n) and is checked against the brute-force sum for every
n below 600, six larger sizes, and 200 random sizes up to 20,000; a scale test confirms 1.2 billion leaves takes under 10 ms.

## 2. Test-side errors

* `test_decode_input_validation`: the test built its input with `coded[99]` before calling `decode`, so it raised in the test,
  not in the library. Rebuilt with a valid array behind the bad index.
* A large-code test contained a garbled expression that evaluated to the same subset three times. Rewritten as four named
  adversarial subsets plus 40 random ones.
* `test_agrees_with_an_independent_third_party_implementation` demanded `checked > 5000`; the correct count is
  `sum(1..99) + 4 * 10 = 4,990` (all comparisons had passed). It now asserts the exact number.
* `test_wrong_leaf_index_size_length_or_root_is_rejected` asserted that a proof from a 13-leaf tree is rejected under a claimed
  size of 14. It is accepted, and correctly so: RFC 6962 audit paths only fix the *shape* of the path, and for index 5 the shape
  is identical for every size from 9 to 16. The proof does not authenticate the tree size. The protocol is unaffected because
  the wire format has no size field and the receiver takes `tree_size` only from the signed manifest, but that dependency is now
  pinned by `test_a_proof_does_not_authenticate_the_tree_size...` and stated in the README.

## 3. Independent cross-checks that passed

* Merkle roots for sizes 0 to 8 against the Certificate Transparency test roots, written down from memory before the code was run
  against them: 9 of 9 matched.
* Roots and inclusion proofs against `pymerkle` 6.1.0 (a separate RFC 6962 implementation): trees of size 1 to 129, 255, 256, 257
  and 511; 8,433 proofs compared; 0 differ.
* GF(256) multiplication table against a shift-and-xor multiplier that shares no code with it, on all 65,536 pairs; field axioms
  (commutativity, associativity, distributivity) over all 16.7 million triples.
* The Reed-Solomon code is MDS: every k-subset of every codeword decodes, exhaustively for six (k, r) up to (6, 6), which is 924
  subsets for the largest.
