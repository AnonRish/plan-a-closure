"""
§12, part 1: an actual computed bit-capacity bound, not an assertion.

At each real generated position, the cost of choosing the k-th ranked token
instead of the verifier's top choice is known exactly (same ranking DiFR
itself uses: logits/T + seeded Gumbel noise). Given a total average-cost
budget of N*tau across N positions, the capacity-maximizing allocation is a
water-filling problem: spend budget where it buys the most bits per unit
cost, position by position, until the budget runs out. This is the same
family of problem as capacity-under-a-power-constraint in classical
information theory; it's solved here by real greedy allocation over real
per-position cost curves from the real model, not assumed analytically.
"""
import numpy as np
from model import TinyCharLM
import sampling
from test_suite import random_prompt, encode

VERIFIER_MODEL = TinyCharLM.load("charlm.pkl")
MAX_K = 12  # consider up to the top-12 ranked tokens as candidate encoding alternatives


def cost_curve_at_position(logits, seed, position, temperature, max_k):
    """Cost (in DiFR's own units) of choosing each of the top max_k ranked
    tokens instead of rank-0, at one real position."""
    g = sampling.gumbel_noise(seed, position, logits.shape[0])
    scores = logits / temperature + g
    order = np.argsort(-scores)
    top_scores = scores[order[:max_k]]
    return top_scores[0] - top_scores  # cost[0] = 0 by construction


def gather_cost_curves(n_positions, temperature, base_seed):
    """Real cost curves from real generated positions — honest generation,
    walking forward token by token exactly as §5's prover would."""
    rng = np.random.default_rng(base_seed)
    curves = []
    prompt = random_prompt(rng)
    seed = int(rng.integers(0, 2**62))
    ctx_len = VERIFIER_MODEL.context_len
    prompt_tokens = encode(prompt)
    seq = list(prompt_tokens)
    for i in range(n_positions):
        window = seq[-ctx_len:]
        if len(window) < ctx_len:
            window = [0] * (ctx_len - len(window)) + window
        logits = VERIFIER_MODEL.forward_logits_only(np.array([window]))[0]
        curve = cost_curve_at_position(logits, seed, len(prompt_tokens) + i, temperature, MAX_K)
        curves.append(curve)
        tok = sampling.sample_token(logits, seed, len(prompt_tokens) + i, temperature)
        seq.append(tok)
    return curves


def water_fill_capacity(curves, tau):
    """Greedy water-filling: at each step, find the (position, k->k+1)
    expansion with the lowest marginal cost per additional bit, and take
    it, until the total budget (len(curves) * tau) is exhausted. Returns
    total bits and total cost actually spent."""
    n = len(curves)
    budget = n * tau
    current_k = [1] * n  # everyone starts at k=1 (rank-0 only, 0 bits, 0 cost)
    total_bits = 0.0
    total_cost = 0.0

    while True:
        best_ratio = None
        best_i = None
        for i in range(n):
            k = current_k[i]
            if k >= len(curves[i]):
                continue
            marginal_cost = float(np.mean(curves[i][:k + 1]) * (k + 1) - np.mean(curves[i][:k]) * k) if k > 0 else float(curves[i][k])
            # expected cost of encoding uniformly among top-(k+1) minus
            # expected cost among top-k, weighted correctly by probability
            # mass — computed directly below instead, this line kept only
            # as an early candidate filter
            expected_cost_k = float(np.mean(curves[i][:k]))
            expected_cost_k1 = float(np.mean(curves[i][:k + 1]))
            marginal_cost = (expected_cost_k1 * (k + 1) - expected_cost_k * k)
            marginal_bits = np.log2(k + 1) - np.log2(k)
            if marginal_cost <= 0:
                ratio = -1.0  # free or negative-cost bits, always take first
            else:
                ratio = marginal_cost / marginal_bits
            if best_ratio is None or ratio < best_ratio:
                best_ratio = ratio
                best_i = i

        if best_i is None:
            break  # every position maxed out at MAX_K

        i = best_i
        k = current_k[i]
        expected_cost_k = float(np.mean(curves[i][:k])) if k > 0 else 0.0
        expected_cost_k1 = float(np.mean(curves[i][:k + 1]))
        added_cost = expected_cost_k1 * (k + 1) - expected_cost_k * k
        added_bits = np.log2(k + 1) - np.log2(k)

        if total_cost + added_cost > budget:
            break

        current_k[i] += 1
        total_cost += added_cost
        total_bits += added_bits

    return total_bits, total_cost, current_k


if __name__ == "__main__":
    TEMPS = [0.5, 0.8, 1.2]
    TAUS = [0.02, 0.05, 0.1, 0.2, 0.3]
    N_POSITIONS = 200

    print("Real per-position cost curves gathered from actual generation (not synthetic).")
    print()
    print(f"{'temp':<8}{'tau':<8}{'bits/token (water-fill)':<26}{'total_cost_spent':<20}{'budget':<10}")
    for t in TEMPS:
        curves = gather_cost_curves(N_POSITIONS, t, base_seed=int(t * 1000))
        for tau in TAUS:
            bits, cost, ks = water_fill_capacity(curves, tau)
            bits_per_token = bits / N_POSITIONS
            print(f"{t:<8}{tau:<8}{bits_per_token:<26.4f}{cost:<20.4f}{N_POSITIONS*tau:<10.2f}")
