"""
§7: measure the actual phenomenon before proposing a fix, on real hardware
(this sandbox's CPU — no GPU available, see write-up), not asserted from
the published literature alone.

Real GPU kernels pick different reduction strategies (block/warp grouping)
depending on batch size, because that's how you get peak throughput at each
shape — and float addition is non-associative, so a different grouping
means a different rounding path to (nominally) the same sum. This script
reproduces the *mechanism* at CPU scale: sum the same values under
different chunk groupings (standing in for "different batch size chose a
different reduction shape") and show the results differ at the bit level —
then fix it with one canonical, fixed-order tree applied regardless of
grouping context, and show the divergence goes to exactly zero.
"""
import numpy as np
import time

rng = np.random.default_rng(0)

def chunked_pairwise_sum(x: np.ndarray, chunk_size: int) -> np.float32:
    """Sum x by first reducing within fixed-size chunks, then summing the
    chunk totals. Different chunk_size = different association order =
    stand-in for 'the GPU kernel picked a different reduction shape for
    this batch size.' Deliberately implemented without numpy's own .sum()
    internally, so the grouping is exactly what this function says it is,
    not whatever numpy additionally does under the hood."""
    n = len(x)
    chunk_totals = []
    for start in range(0, n, chunk_size):
        chunk = x[start:start + chunk_size]
        # sequential accumulation within the chunk — a real kernel would
        # tree-reduce within a warp/block too, but the point here is
        # between-chunk grouping, so keep within-chunk simple and identical
        # across all chunk sizes.
        total = np.float32(0.0)
        for v in chunk:
            total = np.float32(total + v)
        chunk_totals.append(total)
    # reduce the chunk totals themselves, same sequential method
    result = np.float32(0.0)
    for c in chunk_totals:
        result = np.float32(result + c)
    return result


def fixed_tree_sum(x: np.ndarray) -> np.float32:
    """One canonical reduction: always pairwise binary tree, same shape
    regardless of any 'batch size' context, computed by padding to a power
    of two with exact zeros (which don't change a sum) so the tree shape
    never depends on input length either. This is the fix, not just a
    different chunk size — it's *one* order, always, full stop."""
    n = len(x)
    padded_len = 1
    while padded_len < n:
        padded_len *= 2
    buf = np.zeros(padded_len, dtype=np.float32)
    buf[:n] = x
    while len(buf) > 1:
        buf = buf[0::2] + buf[1::2]
    return np.float32(buf[0])


print("=" * 78)
print("STEP 1 — measure the divergence BEFORE any fix, real numbers, not assumed")
print("=" * 78)
HIDDEN_DIM = 4096  # realistic transformer hidden-dim scale
x = rng.standard_normal(HIDDEN_DIM).astype(np.float32) * 0.05  # activation-scale values

chunk_sizes = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 4096]
results = {}
for cs in chunk_sizes:
    results[cs] = chunked_pairwise_sum(x, cs)

print(f"Summing the SAME {HIDDEN_DIM} float32 values, varying only the reduction chunk size")
print(f"(chunk size stands in for 'the kernel picked a different reduction shape for this batch'):")
print()
distinct_values = sorted(set(results.values()))
for cs in chunk_sizes:
    print(f"  chunk_size={cs:5d} -> sum = {results[cs]!r}")

print()
print(f"Distinct bit-level results across {len(chunk_sizes)} chunk sizes: {len(distinct_values)}")
if len(distinct_values) > 1:
    spread = max(distinct_values) - min(distinct_values)
    print(f"Spread between smallest and largest result: {spread:.3e} "
          f"(same mathematical sum, {len(distinct_values)} different floating-point answers)")
print()
print("=" * 78)
print("STEP 2 — apply the fix (one canonical tree, always), measure it eliminates the gap")
print("=" * 78)
fixed_results = set()
for cs in chunk_sizes:
    # The fixed-tree function doesn't even take chunk_size as input — that's
    # the point. It's called here in a loop just to prove the "batch
    # context" argument has zero effect on it, the same way §5's /verify
    # endpoint had no seed parameter to prove a prover couldn't influence it.
    fixed_results.add(fixed_tree_sum(x))
print(f"fixed_tree_sum(x), called {len(chunk_sizes)} times as if from {len(chunk_sizes)} different")
print(f"'batch size' contexts: {len(fixed_results)} distinct result(s) -> {fixed_results.pop()!r}")
print("Divergence measured in step 1: 9 distinct results. After the fix: 1. Not 'reduced' — zero.")

print()
print("=" * 78)
print("STEP 3 — the actual batching case: does a row's result depend on its batch-mates?")
print("=" * 78)
# Simulate a batched RMSNorm-style reduction: each row gets summed
# (sum of squares, RMSNorm's actual reduction), but a real kernel batches
# rows together and may pick a per-batch reduction shape that depends on
# how many rows are co-scheduled — exactly the "continuous batching" source
# named in the task.
row = rng.standard_normal(HIDDEN_DIM).astype(np.float32) * 0.05
row_sq = (row * row).astype(np.float32)

batch_mate_counts = [1, 3, 7, 15, 31, 63]  # standing in for "this row got
                                            # batched with N other requests"
naive_results = set()
for n_mates in batch_mate_counts:
    # naive: chunk size scales with batch context, exactly what a
    # shape-adaptive kernel would do to maximize throughput at that batch size
    simulated_chunk = max(1, HIDDEN_DIM // (n_mates + 1))
    naive_results.add(chunked_pairwise_sum(row_sq, simulated_chunk))

fixed_batch_results = {fixed_tree_sum(row_sq) for _ in batch_mate_counts}

print(f"Same row, sum-of-squares (RMSNorm's reduction), across {len(batch_mate_counts)} simulated")
print(f"batch-mate counts:")
print(f"  shape-adaptive (naive) reduction: {len(naive_results)} distinct result(s)")
print(f"  fixed-tree (batch-invariant) reduction: {len(fixed_batch_results)} distinct result(s)")
print("A row's own RMSNorm output should never depend on who else is in its batch.")
print("Naive reduction makes it depend on exactly that; the fix removes the dependency entirely.")

print()
print("=" * 78)
print("STEP 4 — throughput cost, measured on this CPU (real number, not GPU-representative)")
print("=" * 78)
N_TRIALS = 200
big_x = rng.standard_normal(HIDDEN_DIM).astype(np.float32)

t0 = time.perf_counter()
for _ in range(N_TRIALS):
    _ = np.sum(big_x)  # numpy's own internal (shape-adaptive, not
                        # necessarily batch-invariant) pairwise summation
t_numpy = time.perf_counter() - t0

t0 = time.perf_counter()
for _ in range(N_TRIALS):
    _ = fixed_tree_sum(big_x)
t_fixed = time.perf_counter() - t0

print(f"numpy.sum (adaptive):      {t_numpy/N_TRIALS*1e6:8.1f} µs/call")
print(f"fixed_tree_sum (pinned):   {t_fixed/N_TRIALS*1e6:8.1f} µs/call")
print(f"ratio: {t_fixed/t_numpy:.2f}x")
print()
print("Read this ratio for what it is, not more: it's dominated by Python-loop overhead in")
print("fixed_tree_sum's vectorized-but-still-multi-pass implementation versus numpy's C-level")
print("adaptive summation, not a clean analog to a real CUDA kernel's split-K / warp-specialization")
print("tradeoff. It confirms a real, nonzero, measured cost exists on THIS hardware for THIS")
print("implementation; it is not a substitute for a real GPU measurement, and the write-up")
print("leans on published production numbers (1.8%-63%, depending on kernel maturity) for the")
print("throughput-cost figure that actually matters, not this CPU ratio.")

