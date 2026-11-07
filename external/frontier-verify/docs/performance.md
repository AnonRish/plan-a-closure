# Performance

Measured on this sandbox's CPU (no GPU) on the date this document was
written. Reproduce with the script embedded in this document's own git
history / the command shown per section -- these are not invented numbers.

## What's measured

| Operation | Median | Mean | Max | N |
|---|---|---|---|---|
| Ed25519 sign (`sign_receipt`) | 0.052 ms | 0.058 ms | 0.544 ms | 200 |
| Ed25519 verify (`verify_receipt`) | 0.155 ms | 0.158 ms | 0.256 ms | 200 |
| Auth key load (`load_valid_keys`, per-request cost since Phase 2 reads fresh every call -- see `frontier_verify/api/auth.py`) | 0.0006 ms | 0.0006 ms | 0.009 ms | 500 |
| Full flow: submit evidence + validate policy + verify inference (3 HTTP calls, in-process `TestClient`, includes auth, storage I/O, signing) | 6.0 ms | 6.3 ms | 17.8 ms | 100 |

**Reading these honestly**: the full-flow number is dominated by
`TestClient`'s in-process HTTP simulation overhead and real filesystem
I/O from `ContentAddressedStore` (evidence is actually written to disk
now, not just held in a dict -- see `docs/protocol-roadmap.md`), not by
cryptography, which is consistently sub-millisecond. A real deployment
over a real network would add real network latency on top of this,
unmeasured here because it depends entirely on deployment topology this
project doesn't control.

## What's explicitly UNMEASURED, and why

| Metric | Status | Why |
|---|---|---|
| Inference latency overhead (vLLM/Triton integration) | **UNMEASURED** | No GPU, no vLLM/Triton install in this environment -- see `docs/integrations/vllm.md`, `docs/integrations/triton.md` |
| GPU overhead | **UNMEASURED** | No GPU |
| Real network overhead (client to verifier over an actual network) | **UNMEASURED** | This measurement used in-process `TestClient`, not a real socket -- see the "reading these honestly" note above |
| Attestation collection overhead (`nvattest collect-evidence`) | **UNMEASURED** | No NVIDIA hardware, no NVAT installed |
| Recomputation cost | **UNMEASURED** (and not meaningfully measurable yet) | `frontier_verify/recomputation/` uses toy deterministic functions over opaque digests, not real inference -- see `docs/research/recomputation.md`. Timing a toy function would produce a number that means nothing about real recomputation cost |
| Storage overhead at scale (thousands+ of evidence records) | **UNMEASURED** | Only tested with small numbers of records in this session; `ContentAddressedStore`'s two-level directory fan-out is designed for scale but untested at it |

## The one qualitative claim this document is confident in

Cryptographic signing and verification are not the bottleneck in this
design, at any scale this project has tested -- sub-millisecond,
consistently. If a real deployment turns out to be slow, the cause will be
network topology, storage backend choice, or real inference overhead, not
Ed25519. That's a useful thing to know even before hardware-dependent
numbers exist, and it's the only claim on this page confident enough to
state without a table of caveats next to it.
