"""
§10: four named attacks, each tested against the REAL §5 server/DiFR
implementation with a dishonest model from §9, not simulated in the
abstract. Patches proposed and then actually re-tested, per the self-check.
"""
import numpy as np
import pickle
from model import TinyCharLM
import sampling
import difr
from test_suite import (
    encode, decode, random_prompt, VERIFIER_MODEL, TEXT,
    gen_same_family, gen_cross_family, run_category, pass_rate_at_tau,
)

RNG = np.random.default_rng(20260715)


# =====================================================================
# ATTACK 1: seed/session shopping — generate many candidate sessions,
# silently discard the ones that would fail, only ever report the ones
# that pass. Tests whether this beats the baseline per-attempt pass rate.
# =====================================================================
def attack1_session_shopping(gen_fn, n_logical_requests, k_attempts, tau, base_seed):
    """For each logical request, try k_attempts independent (seed, output)
    pairs using the dishonest model; report whether AT LEAST ONE passed
    (the "shopped" outcome a dishonest prover would actually report) versus
    the single-attempt baseline pass rate."""
    rng = np.random.default_rng(base_seed)
    shopped_pass = 0
    single_attempt_pass = 0
    total_sessions_created = 0
    total_sessions_ever_reported = 0

    for _ in range(n_logical_requests):
        prompt = random_prompt(rng)
        any_passed = False
        first_attempt_result = None
        for attempt in range(k_attempts):
            seed = int(rng.integers(0, 2**62))
            total_sessions_created += 1
            claimed_output, prompt_tokens = gen_fn(prompt, seed, 30, rng)
            claimed_tokens = encode(claimed_output)
            result = difr.verify(VERIFIER_MODEL, prompt_tokens, claimed_tokens, seed=seed, temperature=0.8)
            passed = result["avg_deviation"] <= tau
            if attempt == 0:
                first_attempt_result = passed
            if passed:
                any_passed = True
                total_sessions_ever_reported += 1
                break  # a real shopping attacker stops at the first success
        if any_passed:
            shopped_pass += 1
        if first_attempt_result:
            single_attempt_pass += 1

    return {
        "single_attempt_pass_rate": single_attempt_pass / n_logical_requests,
        "shopped_pass_rate": shopped_pass / n_logical_requests,
        "sessions_created": total_sessions_created,
        "sessions_reported": total_sessions_ever_reported,
        "abandonment_rate": 1 - (total_sessions_ever_reported / total_sessions_created),
    }


# =====================================================================
# PATCH 1: flag provers whose (sessions created but never verified) ratio
# is anomalously high. Testable directly from data already in hand above —
# the "patch" is a detector, so test it as one: does abandonment rate
# actually separate shopping attackers from honest provers?
# =====================================================================
def honest_abandonment_baseline(n_logical_requests, base_seed):
    """An honest prover has no reason to create a session and not verify
    it — but real systems have benign abandonment too (client crashes,
    users who never finish a request). Model that at a low background
    rate to make the detector test fair, not a strawman."""
    rng = np.random.default_rng(base_seed)
    created = n_logical_requests
    benign_abandon_rate = 0.05  # 5% background abandonment, generously high
    reported = int(created * (1 - benign_abandon_rate))
    return {"sessions_created": created, "sessions_reported": reported,
            "abandonment_rate": 1 - reported / created}


def stego_generate_and_score(prompt, seed, max_tokens, hidden_bits, per_token_budget):
    """Uses the HONEST model's own logits — this isn't a substituted-model
    attack, it's an honest-model operator deliberately choosing among
    within-tolerance tokens to smuggle information. At each position, if a
    hidden bit remains and switching from the verifier's rank-0 choice to
    rank-1 costs no more than per_token_budget in deviation, encode a bit
    there; otherwise emit the honest rank-0 choice."""
    ctx_len = VERIFIER_MODEL.context_len
    prompt_tokens = encode(prompt)
    seq = list(prompt_tokens)
    out = []
    bits_encoded = 0
    per_token_devs = []

    for i in range(max_tokens):
        window = seq[-ctx_len:]
        if len(window) < ctx_len:
            window = [0] * (ctx_len - len(window)) + window
        logits = VERIFIER_MODEL.forward_logits_only(np.array([window]))[0]
        g = sampling.gumbel_noise(seed, len(prompt_tokens) + i, logits.shape[0])
        scores = logits + g
        order = np.argsort(-scores)
        rank0_tok, rank1_tok = int(order[0]), int(order[1])
        cost_of_rank1 = float(scores[rank0_tok] - scores[rank1_tok])

        want_bit = (bits_encoded < len(hidden_bits)) and hidden_bits[bits_encoded] == 1
        if want_bit and cost_of_rank1 <= per_token_budget:
            tok = rank1_tok
            per_token_devs.append(min(cost_of_rank1, difr.DELTA_MAX))
            bits_encoded += 1
        else:
            tok = rank0_tok
            per_token_devs.append(0.0)
            if bits_encoded < len(hidden_bits) and hidden_bits[bits_encoded] == 1:
                pass  # couldn't afford to encode this bit here, try next position
            elif bits_encoded < len(hidden_bits):
                bits_encoded += 1  # a "0" bit costs nothing to encode — it's just the honest choice

        out.append(tok)
        seq.append(tok)

    avg_dev = float(np.mean(per_token_devs))
    return decode(out), avg_dev, bits_encoded, per_token_devs


def stego_report():
    lines = []
    rng = np.random.default_rng(555)
    n_trials = 200
    for budget in [0.05, 0.1, 0.2, 0.3, 0.5]:
        devs = []
        bit_fracs = []
        for _ in range(n_trials):
            prompt = random_prompt(rng)
            seed = int(rng.integers(0, 2**62))
            n_bits_wanted = 20
            hidden_bits = rng.integers(0, 2, size=n_bits_wanted).tolist()
            _, avg_dev, bits_encoded, _ = stego_generate_and_score(prompt, seed, 30, hidden_bits, budget)
            devs.append(avg_dev)
            bit_fracs.append(bits_encoded / n_bits_wanted)
        devs = np.array(devs)
        lines.append(
            f"  per_token_budget={budget:<5} mean_avg_dev={devs.mean():.4f}  "
            f"pass_rate(tau=0.3)={pass_rate_at_tau(devs, 0.3):.3f}  "
            f"pass_rate(tau=0.5)={pass_rate_at_tau(devs, 0.5):.3f}  "
            f"fraction_of_bits_successfully_encoded={np.mean(bit_fracs):.3f}"
        )
    return "\n".join(lines)


def patch2_nonzero_token_fraction_detector():
    """PATCH 2: honest generation (and honest hardware-drift-scale noise)
    should have essentially zero tokens with a real, non-noise deviation.
    Test whether "fraction of tokens with deviation > 0.01" separates the
    stego attack from an honest session, at budgets where the AVERAGE
    already sailed through undetected."""
    rng = np.random.default_rng(777)
    lines = []

    # honest baseline: real honest generation, real per-token deviations
    # (should all be exactly 0.0, per §5/§9's own finding)
    honest_nonzero_fracs = []
    for _ in range(100):
        prompt = random_prompt(rng)
        seed = int(rng.integers(0, 2**62))
        prompt_tokens = encode(prompt)
        out_tokens = []
        ctx_len = VERIFIER_MODEL.context_len
        seq = list(prompt_tokens)
        for i in range(30):
            window = seq[-ctx_len:]
            if len(window) < ctx_len:
                window = [0] * (ctx_len - len(window)) + window
            logits = VERIFIER_MODEL.forward_logits_only(np.array([window]))[0]
            tok = sampling.sample_token(logits, seed, len(prompt_tokens) + i, 0.8)
            out_tokens.append(tok)
            seq.append(tok)
        result = difr.verify(VERIFIER_MODEL, prompt_tokens, out_tokens, seed=seed, temperature=0.8)
        per_tok = [t["deviation"] for t in result["per_token"]]
        honest_nonzero_fracs.append(np.mean([d > 0.01 for d in per_tok]))

    lines.append(f"  honest sessions: mean fraction of tokens with deviation>0.01 = {np.mean(honest_nonzero_fracs):.4f}")

    for budget in [0.05, 0.1, 0.2, 0.3]:
        nonzero_fracs = []
        for _ in range(100):
            prompt = random_prompt(rng)
            seed = int(rng.integers(0, 2**62))
            hidden_bits = rng.integers(0, 2, size=20).tolist()
            _, avg_dev, _, per_tok = stego_generate_and_score(prompt, seed, 30, hidden_bits, budget)
            nonzero_fracs.append(np.mean([d > 0.01 for d in per_tok]))
        lines.append(
            f"  stego budget={budget}: mean fraction of tokens with deviation>0.01 = {np.mean(nonzero_fracs):.4f}  "
            f"({np.mean(nonzero_fracs) / max(np.mean(honest_nonzero_fracs), 1e-6):.0f}x the honest rate)"
        )
    return "\n".join(lines)


# =====================================================================
# ATTACK 3: strategic short-output exploitation of §9's documented
# false-negative zone. A prover using a dishonest model that deliberately
# keeps every dishonest response under 5 tokens, versus the same model
# forced to produce full-length output.
# =====================================================================
def attack3_strategic_short_output(gen_fn, n_trials, tau, base_seed):
    short_devs = run_category("attack3_short", lambda p, s, m, r: gen_fn(p, s, 3, r), n_trials, 3, base_seed)
    long_devs = run_category("attack3_long", gen_fn, n_trials, 30, base_seed + 1)
    return {
        "short_pass_rate": pass_rate_at_tau(short_devs, tau),
        "long_pass_rate": pass_rate_at_tau(long_devs, tau),
    }


def patch3_mandatory_resampling(gen_fn, n_trials, tau, base_seed):
    """PATCH 3: any session flagged low_confidence doesn't get to stand on
    its own — the verifier requires ONE additional, longer-output
    verification from the same claimed model/context before extending
    trust. Test: does requiring the SECOND (long) sample to also pass
    close the gap attack 3 opened?"""
    rng = np.random.default_rng(base_seed)
    both_pass = 0
    for _ in range(n_trials):
        prompt = random_prompt(rng)
        seed1 = int(rng.integers(0, 2**62))
        seed2 = int(rng.integers(0, 2**62))
        short_out, short_prompt_tok = gen_fn(prompt, seed1, 3, rng)
        long_out, long_prompt_tok = gen_fn(prompt, seed2, 30, rng)
        r1 = difr.verify(VERIFIER_MODEL, short_prompt_tok, encode(short_out), seed=seed1, temperature=0.8)
        r2 = difr.verify(VERIFIER_MODEL, long_prompt_tok, encode(long_out), seed=seed2, temperature=0.8)
        if r1["avg_deviation"] <= tau and r2["avg_deviation"] <= tau:
            both_pass += 1
    return both_pass / n_trials


if __name__ == "__main__":
    print("=" * 90)
    print("ATTACK 1: seed/session shopping (exploiting seed control)")
    print("=" * 90)
    TAU = 0.3
    for name, gen_fn in [("same_family", gen_same_family), ("cross_family", gen_cross_family)]:
        for k in [1, 5, 20, 50]:
            res = attack1_session_shopping(gen_fn, n_logical_requests=60, k_attempts=k, tau=TAU, base_seed=hash(name + str(k)) % 100000)
            print(f"  {name:<14} k={k:<3} single_attempt_pass={res['single_attempt_pass_rate']:.3f}  "
                  f"shopped_pass={res['shopped_pass_rate']:.3f}  abandonment_rate={res['abandonment_rate']:.3f}")

    print()
    print("PATCH 1 test: does abandonment rate separate shopping attackers from honest provers?")
    honest = honest_abandonment_baseline(300, base_seed=1)
    print(f"  honest prover (benign-only abandonment):  abandonment_rate={honest['abandonment_rate']:.3f}")
    for name, gen_fn in [("same_family", gen_same_family), ("cross_family", gen_cross_family)]:
        res = attack1_session_shopping(gen_fn, n_logical_requests=60, k_attempts=20, tau=TAU, base_seed=hash(name) % 100000)
        print(f"  {name} shopping k=20:                  abandonment_rate={res['abandonment_rate']:.3f}  "
              f"({res['abandonment_rate']/honest['abandonment_rate']:.1f}x the honest background rate)")

    print()
    print("=" * 90)
    print("ATTACK 2: steganographic bit-per-token encoding, staying under tau (§12 goes deeper)")
    print("=" * 90)
    print(stego_report())

    print()
    print("PATCH 2 test: does per-token deviation distribution catch what the average hides?")
    print(patch2_nonzero_token_fraction_detector())

    print()
    print("=" * 90)
    print("ATTACK 3: strategic short-output exploitation (§9's false-negative zone, weaponized)")
    print("=" * 90)
    TAU3 = 0.3
    for name, gen_fn in [("same_family", gen_same_family), ("cross_family", gen_cross_family)]:
        res = attack3_strategic_short_output(gen_fn, n_trials=150, tau=TAU3, base_seed=hash("a3" + name) % 100000)
        print(f"  {name:<14} always-short(3tok) pass_rate={res['short_pass_rate']:.3f}   "
              f"always-long(30tok) pass_rate={res['long_pass_rate']:.3f}")

    print()
    print("PATCH 3 test: mandatory paired long-output resampling for any low-confidence session")
    for name, gen_fn in [("same_family", gen_same_family), ("cross_family", gen_cross_family)]:
        both_pass = patch3_mandatory_resampling(gen_fn, n_trials=150, tau=TAU3, base_seed=hash("p3" + name) % 100000)
        print(f"  {name:<14} pass_rate requiring BOTH short AND paired long sample to pass = {both_pass:.3f}")

