"""Throughput of the reference implementation (pure Python + NumPy, one core) and a lossy loopback transfer."""
import socket
import threading
import time

import numpy as np
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from weight_diode import Encoder, LossyLink, Receiver, analysis, udp_receive, udp_send
from weight_diode.rs import CauchyRS

key = Ed25519PrivateKey.generate()
rng = np.random.default_rng(0)
MB = 1 << 20


def timed(f):
    t = time.perf_counter()
    r = f()
    return r, time.perf_counter() - t


print("== throughput, 4 MiB file, symbol 1024 B, k=32 r=8 ==")
data = rng.integers(0, 256, 4 * MB, dtype=np.uint8).tobytes()
enc, t_enc = timed(lambda: Encoder(data, key, symbol_size=1024, k=32, r=8))
pkts, t_pk = timed(lambda: list(enc.stream(passes=1)))
rx = Receiver([key.public_key()])
_, t_rx = timed(lambda: [rx.feed(p) for p in pkts])
assert rx.result(enc.manifest_id) == data
print(f"encode (Reed-Solomon + hash every symbol + Merkle tree + sign): {4 / t_enc:6.2f} MiB/s of file")
print(f"packetise (proofs, headers):                                    {4 / t_pk:6.2f} MiB/s of file")
print(f"receive (parse + verify proof + decode + final hash):           {4 / t_rx:6.2f} MiB/s of file")

print("\n== Reed-Solomon alone (k=200, r=55, symbol 1024 B, one block of 200 KiB) ==")
rs = CauchyRS(200, 55)
blk = rng.integers(0, 256, (200, 1024), dtype=np.uint8)
coded = np.vstack([blk, rs.encode(blk)])
_, t_e = timed(lambda: rs.encode(blk))
print(f"  encode:                      {200 * 1024 / MB / t_e:6.2f} MiB/s of block")
for lost in (0, 10, 55):
    keep = {i: coded[i] for i in range(lost, 255)}
    keep = dict(list(keep.items())[:200])
    out, t_d = timed(lambda: rs.decode(keep))
    assert np.array_equal(out, blk)
    print(f"  decode, {lost:2d} data symbols missing: {200 * 1024 / MB / t_d:8.2f} MiB/s of block")

print("\n== real UDP loopback transfer, 1 MiB, 20 % of datagrams dropped before sending, 3 passes ==")
d2 = rng.integers(0, 256, MB, dtype=np.uint8).tobytes()
e2 = Encoder(d2, key, symbol_size=1024, k=32, r=8, serial=7, label="demo")
rx2 = Receiver([key.public_key()])
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as tmp:
    tmp.bind(("127.0.0.1", 0))
    port = tmp.getsockname()[1]
ready = threading.Event()
th = threading.Thread(target=udp_receive, args=(rx2, "127.0.0.1", port), kwargs=dict(timeout=60, ready=ready))
th.start()
ready.wait()
t0 = time.perf_counter()
sent = udp_send(LossyLink(0.20, seed=3).transmit(e2.stream(passes=3)), ("127.0.0.1", port))
th.join()
print(f"  complete={rx2.result(e2.manifest_id) == d2}  datagrams sent after loss={sent}  wall={time.perf_counter() - t0:.1f}s")
print("  receiver events:", dict(sorted(rx2.stats.items())))

print("\n== overhead and loss tolerance for 1 TB of weights (closed form) ==")
for S, k, r in ((1024, 32, 8), (8192, 200, 55), (8192, 100, 28)):
    o = analysis.wire_overhead(10**12, S, k, r)
    print(f"  symbol {S:5d} B, k={k:3d}, r={r:2d}: blocks {o['n_blocks']:>9,}  wire/file {o['overhead_vs_file']:.3f}x  "
          f"proofs {100 * o['proof_bytes'] / o['wire_bytes_per_pass']:4.1f}% of wire  "
          f"P(file) at 5% loss: {analysis.file_success_probability(o['n_blocks'], k, r, 0.05):.6f}")
