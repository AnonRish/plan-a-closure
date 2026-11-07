# tap_reader

Real, tested Rust — the parts of §2b's ingestion pipeline that are testable
without DPDK-capable hardware: frame parsing, three candidate frame-hash
functions, HTTP-chunked/SSE stream reassembly, and a lock-free evidence
ring buffer. Built and benchmarked on a **1-logical-CPU** sandbox — see
`ai-2040-verification.md` §2 for what that does and doesn't tell you about
real multi-core / real-NIC throughput.

## Run it

```
cargo build --release
cargo test --release          # correctness: frame parsing, hashing, reassembly under fragmentation
./target/release/bench_hash        # BLAKE3 vs SipHash-1-3-128 vs AES-128-GMAC, at frame sizes
./target/release/bench_pipeline    # parse + hash + ring-push, 64B-9000B frames
./target/release/bench_ring        # ring buffer throughput, 1/2/4/8 producers
./target/release/test_reassembly   # HTTP-chunked/SSE reassembly under adversarial fragmentation
```

Requires a Rust toolchain (built and tested against 1.75, installed via
`apt install rustc cargo` rather than rustup, since rustup's download host
wasn't reachable from the sandbox this was built in — a plain `rustup`
install should work fine elsewhere and will happily use a newer toolchain).

## What's real vs. not

**Real, tested here:** frame parsing correctness; hash throughput at 10B/46B/1446B/8946B
payload sizes; HTTP-chunked+SSE reassembly correctness under byte-at-a-time and
random fragmentation (including a real bug the fragmentation tests caught and
that got fixed — see the comment on `ChunkedDecoder`); ring buffer correctness
and throughput under 1/2/4/8 concurrent producer threads.

**Not real, not attempted here:** anything involving an actual NIC, DPDK's EAL,
RSS in hardware, or PCIe/DMA throughput. This sandbox has no DPDK-capable
hardware. `bench_pipeline` measures the CPU-bound software ceiling only —
how fast this code could process frames if a NIC handed them over instantly —
which is necessary but not sufficient for a real throughput number.
