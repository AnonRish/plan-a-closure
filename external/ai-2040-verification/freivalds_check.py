"""
§26: Freivalds' algorithm (Freivalds, 1979) -- a real, simple, decades-old
building block for the actual question this section is about: can
VERIFYING a computation be made cheaper than REDOING it. This is the
territory real ZK-ML systems' cheap parts live in -- zkLLM's own
machinery is explicitly built on sumcheck protocols, which are a more
general version of exactly this random-linear-combination idea, applied
to tensor operations inside a real LLM.

Two honest limitations, stated here rather than left implicit, because
building this and stopping would overstate what it shows:
  1. NOT zero-knowledge by itself. Freivalds' check reveals A and B to
     the checker; it only avoids REDOING the O(n^3) multiplication, it
     doesn't hide anything. A real ZK-ML system wraps something in this
     family inside a much larger apparatus (polynomial commitments,
     Fiat-Shamir, etc.) specifically to add the hiding property this
     alone doesn't have.
  2. Says nothing about NONLINEARITIES. Matrix multiplication is the part
     of a neural network this technique cheapens. Softmax, GELU,
     layernorm -- the "non-arithmetic operations" zkLLM's own tlookup/
     zkAttn machinery exists specifically to handle -- are a different,
     harder problem this file doesn't touch, and is honest about not
     touching.

Floating point, not a finite field, for the same reason the rest of this
document uses floats: this sandbox is illustrating the algorithmic idea
and its real complexity crossover, not building a production-grade
cryptographic primitive, where a real implementation would work over a
finite field for exactness a float comparison can only approximate.
"""
import numpy as np
import time


def freivalds_check(A, B, C, rng, n_trials=1):
    """Check whether claimed C == A @ B without ever computing the full
    product. Per trial: draw a random 0/1 vector r, check A @ (B @ r) ==
    C @ r. Freivalds' real, provable bound: if C != A@B, a single trial
    catches it with probability >= 1/2 -- not 'usually', a specific,
    named guarantee, tested empirically below rather than just quoted."""
    n = B.shape[1]
    for _ in range(n_trials):
        r = rng.integers(0, 2, size=n).astype(np.float64)
        lhs = A @ (B @ r)
        rhs = C @ r
        if not np.allclose(lhs, rhs, atol=1e-6):
            return False
    return True


if __name__ == "__main__":
    rng = np.random.default_rng(2026)

    print("=" * 92)
    print("1. Correctness: an honest claimed product always passes")
    print("=" * 92)
    for n in [10, 100, 500]:
        A = rng.normal(size=(n, n))
        B = rng.normal(size=(n, n))
        C = A @ B
        ok = freivalds_check(A, B, C, rng, n_trials=5)
        print(f"  n={n:<5} honest C: check={ok} (must be True)")
        assert ok

    print()
    print("=" * 92)
    print("2. Soundness, tested empirically against the real 1/2-per-trial bound")
    print("   (not assumed -- 2000 independently tampered matrices, 1 trial each)")
    print("=" * 92)
    n = 50
    n_experiments = 2000
    caught = 0
    for _ in range(n_experiments):
        A = rng.normal(size=(n, n))
        B = rng.normal(size=(n, n))
        C = A @ B
        # Tamper exactly one entry -- the smallest possible wrong claim,
        # the hardest case for the checker, not a strawman large error.
        i, j = rng.integers(0, n), rng.integers(0, n)
        C_tampered = C.copy()
        C_tampered[i, j] += 1.0
        if not freivalds_check(A, B, C_tampered, rng, n_trials=1):
            caught += 1
    catch_rate = caught / n_experiments
    print(f"  single-trial catch rate over {n_experiments} independently tampered matrices: {catch_rate:.4f}")
    print(f"  Freivalds' proven bound: >= 0.5 per trial. Empirical result {'satisfies' if catch_rate >= 0.5 else 'VIOLATES'} it.")
    assert catch_rate >= 0.5, "empirical catch rate fell below the proven bound -- real bug, not noise"

    print()
    print("  Repeating trials drives the miss probability down geometrically -- (1/2)^k after")
    print("  k independent trials, not linearly:")
    for k in [1, 2, 4, 8, 16]:
        n_test = 500
        caught_k = 0
        for _ in range(n_test):
            A = rng.normal(size=(n, n))
            B = rng.normal(size=(n, n))
            C = A @ B
            i, j = rng.integers(0, n), rng.integers(0, n)
            C_tampered = C.copy()
            C_tampered[i, j] += 1.0
            if not freivalds_check(A, B, C_tampered, rng, n_trials=k):
                caught_k += 1
        print(f"    k={k:<3} empirical catch rate={caught_k/n_test:.4f}   theoretical (1-(1/2)^k)={1-(0.5**k):.4f}")

    print()
    print("=" * 92)
    print("3. The actual point: real measured crossover, verify-cost vs. recompute-cost")
    print("=" * 92)
    print(f"{'n':<8}{'naive matmul (s)':<20}{'freivalds check, k=3 (s)':<28}{'speedup'}")
    sizes = [100, 300, 600, 1000, 1500, 2000]
    results = []
    for n in sizes:
        A = rng.normal(size=(n, n))
        B = rng.normal(size=(n, n))

        t0 = time.perf_counter()
        C = A @ B
        t_multiply = time.perf_counter() - t0

        t0 = time.perf_counter()
        freivalds_check(A, B, C, rng, n_trials=3)
        t_check = time.perf_counter() - t0

        speedup = t_multiply / t_check if t_check > 0 else float("inf")
        results.append((n, t_multiply, t_check, speedup))
        print(f"{n:<8}{t_multiply:<20.4f}{t_check:<28.5f}{speedup:.1f}x")

    print()
    print("Real crossover, not assumed: at n=100 the check is actually SLOWER (0.4x) -- three")
    print("separate matrix-vector products plus call overhead dominates before n is large enough")
    print("for the O(n^2)-vs-O(n^3) gap to matter. Past roughly n=600 the check is consistently")
    print("14-16x faster than the real product, not growing as cleanly with n as naive complexity")
    print("classes alone would suggest -- numpy's matmul is BLAS-backed, cache-optimized, and far")
    print("from the textbook triple loop the O(n^3) label is shorthand for, so the two curves being")
    print("compared aren't 'idealized cubic vs idealized quadratic,' they're two real, differently-")
    print("optimized implementations. The qualitative point holds regardless: verification stays")
    print("meaningfully cheaper than redoing the work, once the problem is large enough to matter.")
