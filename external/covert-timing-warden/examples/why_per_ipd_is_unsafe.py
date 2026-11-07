"""A per-inter-packet-delay capacity bound under-counts leakage when jitter is added to timestamps.

Naive analysis: the observer sees delays; jitter on two consecutive timestamps makes delay noise triangular
(difference of two uniforms); compute Blahut-Arimoto capacity of that memoryless channel. Reality: a receiver
with a shared clock decodes *cumulative* timestamps, where the noise on each packet does not accumulate.
"""
import math

import numpy as np

from covert_timing_warden import capacity as cap
from covert_timing_warden.mitigate import UniformJitter, lattice_roundtrip_jitter


def tri_cdf(z, w):
    z = np.asarray(z, float)
    return np.where(z <= -w, 0.0, np.where(z <= 0, (z + w) ** 2 / (2 * w * w), np.where(z < w, 1 - (w - z) ** 2 / (2 * w * w), 1.0)))


print(f"{'D/w':>4} {'naive per-IPD BA':>17} {'achieved (simulated)':>21} {'proven upper':>13} {'naive misses':>13}")
rng = np.random.default_rng(0)
w_ns = 1_000
for m in (1, 2, 3, 4, 8):
    h, w = 0.1, 1.0
    xs = np.arange(0, m * w + h / 2, h)
    edges = np.arange(-w - h / 2, m * w + w + 1.5 * h, h)
    naive = cap.blahut_arimoto(cap.additive_noise_channel(xs, edges, lambda z: tri_cdf(z, w)), tol_bits=1e-7).upper_bits
    M = m + 1
    sym = rng.integers(0, M, 400_000)
    ok = np.array_equal(lattice_roundtrip_jitter(sym, w_ns, w_ns, rng), sym)      # error-free => rate = log2(M) exactly
    achieved = math.log2(M) if ok else float("nan")
    upper = UniformJitter(1.0).capacity(m * 1.0).upper_bits
    print(f"{m:>4} {naive:>17.4f} {achieved:>21.4f} {upper:>13.4f} {100 * (1 - naive / achieved):>12.0f}%")
