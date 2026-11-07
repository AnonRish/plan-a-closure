# Vendored repositories

These are the AnonRish repositories that cover parts of AI 2040 Plan A and the hardwired-pause paper that plan-a-closure
does not, copied in so that one archive carries all of it. Each keeps its own code, tests, README and licence. Nothing in
plan-a-closure imports them: the coverage matrices (docs/PLAN_A_COVERAGE.md, docs/HARDWIRED_PAUSE_COVERAGE.md) point at
their files by path, and `closure coverage` checks those paths by parsing the files.

| repository | what it is |
| --- | --- |
| ai-2040-plan-a-toolkit | Reproducible verification research package for AI 2040 Plan A |
| ai-2040-verification | Pieces of the Plan A architecture as experiments: DiFR, Freivalds checks, steganographic capacity, workload approval, proof of learning, trust-root composition |
| aisecurity-rfds | Reference implementations, simulations and design analyses for the AI Security Forum RFDs |
| assurance-curves | Exact and Poisson detection math for random-sampling verification |
| compute-ledger | Chip-stock accounting and declared-versus-estimated reconciliation, checked against the Plan A compute figures |
| continental-load-registry | Large-load interconnection registry over public grid data, with the Track 3 residual-compute bound and tail audit |
| covert-timing-warden | Timing covert channels on tapped inference clusters: detectors, Blahut-Arimoto capacity bounds, mitigation |
| cuda-guard | Evidence classes, verdicts and a tamper-evident ledger for GPU-side verification |
| fides | Packet-hashing inference-only verification tap, with TOPLOC and DiFR reference implementations |
| frontier-verify | Phase 1 verification fabric: evidence, quorum and recomputation services |
| packet-forge | Adversarial TCP overlap corpus, pcap generator and normalising reassembler for testing taps |
| tap-logger-rtl | SHA-256 hash-chain frame logger in Verilog, with the Python reference it is checked against |
| weight-diode | One-way weight transport: Reed-Solomon carousel, Merkle proofs against a signed manifest, no reverse path |

`closure external list` shows the source, commit, licence and recorded test result of each.

## Running their tests

```
pip install -e ".[hw,external]"       # hw brings torch, which cuda-guard's tests import; CPU torch is enough
closure external test --install       # every suite, each in its own pytest process; about ten minutes on a laptop
closure external check                # the trees are the ones in MANIFEST.json and every cited test passed
```

`--install` runs `pip install --no-deps -e` on each repository first, because some tests call their console scripts.
A few tests need tools pip cannot install, and skip without them: 29 in tap-logger-rtl need Icarus Verilog, Verilator and
yosys; in packet-forge two need tshark and tcpdump, the tap-reader tests build a Rust adapter with cargo (which fetches
its crates), and four replay traffic through the kernel. On Debian or Ubuntu: `apt-get install iverilog verilator yosys tshark tcpdump iproute2`. The kernel-replay
tests run only as root, because they create a temporary TUN interface (10.99.0.1/24); run the suites as an ordinary user
on a shared machine and they skip. MANIFEST.json lists the skip reasons of the recorded run.

## Provenance and changes

MANIFEST.json gives, for each repository, the GitHub source and the commit that was copied, a hash of the vendored tree,
and every difference from that commit:

* compute-ledger, packet-forge and tap-logger-rtl were first copied from `anonrish-verification-repos-2.zip`. Their
  GitHub repositories now hold the same trees (the tree hashes match), so MANIFEST.json points at those.
* continental-load-registry is vendored without its data/ directory (389 MB) and two PDFs, except the two small files in
  data/track3/ that its tests read. Its pipeline and dashboard need the rest of data/, which is in the GitHub repository.
* fides: the LICENSE names AnonRish as the copyright holder.

## Licences

Apache-2.0, except fides (MIT). aisecurity-rfds and cuda-guard have no licence file upstream, so no one else has
permission to reuse them until their owner adds one.

## After changing vendored code

`closure external check` fails until the change is tested: run `closure external test --record` (all suites, or name the
repositories you changed), which rewrites the hashes and test results in MANIFEST.json.
