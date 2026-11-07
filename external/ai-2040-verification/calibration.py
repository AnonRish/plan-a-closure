"""
§11: real calibration, sweeping BOTH tau and temperature (the task's own
two axes) across every honest/dishonest pair §9 and §10 established. Uses
AUC between the honest and dishonest deviation-score distributions as the
separation metric — temperature-and-tau-independent, so it answers "is
there any good tau at all" before committing to picking one.
"""
import numpy as np
import json
from test_suite import (
    encode, VERIFIER_MODEL, random_prompt,
    gen_honest, gen_same_family, gen_cross_family, gen_hardware_drift,
    gen_lora_unconditional, gen_lora_trigger,
)
import difr


def auc(pos_scores, neg_scores):
    """AUC of using score to separate 'dishonest' (pos, should score
    HIGHER deviation) from 'honest' (neg, should score LOWER) — 1.0 is
    perfect separation, 0.5 is no separation at all, using the same
    rank-sum method as §3's sampling-prediction AUC."""
    all_scores = np.concatenate([pos_scores, neg_scores])
    labels = np.concatenate([np.ones(len(pos_scores)), np.zeros(len(neg_scores))])
    order = np.argsort(all_scores)
    ranks = np.empty(len(all_scores))
    ranks[order] = np.arange(1, len(all_scores) + 1)
    # tie correction: average rank within tied blocks
    sorted_scores = all_scores[order]
    i = 0
    while i < len(sorted_scores):
        j = i
        while j + 1 < len(sorted_scores) and sorted_scores[j + 1] == sorted_scores[i]:
            j += 1
        if j > i:
            avg_rank = ranks[order[i:j + 1]].mean()
            ranks[order[i:j + 1]] = avg_rank
        i = j + 1
    n_pos, n_neg = len(pos_scores), len(neg_scores)
    if n_pos == 0 or n_neg == 0:
        return 0.5
    rank_sum_pos = ranks[labels == 1].sum()
    return (rank_sum_pos - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


def gen_deviations(gen_fn, n_trials, max_tokens, temperature, base_seed, **kwargs):
    rng = np.random.default_rng(base_seed)
    devs = []
    for _ in range(n_trials):
        prompt = random_prompt(rng)
        seed = int(rng.integers(0, 2**62))
        claimed_output, prompt_tokens = gen_fn(prompt, seed, max_tokens, rng, **kwargs) if kwargs else gen_fn(prompt, seed, max_tokens, rng)
        claimed_tokens = encode(claimed_output)
        result = difr.verify(VERIFIER_MODEL, prompt_tokens, claimed_tokens, seed=seed, temperature=temperature)
        devs.append(result["avg_deviation"])
    return np.array(devs)


# monkey-patch generation functions to actually respect a passed
# temperature (test_suite.py's originals hardcode 0.8 — calibration is
# exactly the place that assumption needs to be lifted)
def gen_honest_t(prompt, seed, max_tokens, rng, temperature):
    import sampling
    ctx_len = VERIFIER_MODEL.context_len
    prompt_tokens = encode(prompt)
    seq = list(prompt_tokens)
    out = []
    for i in range(max_tokens):
        window = seq[-ctx_len:]
        if len(window) < ctx_len:
            window = [0] * (ctx_len - len(window)) + window
        logits = VERIFIER_MODEL.forward_logits_only(np.array([window]))[0]
        tok = sampling.sample_token(logits, seed, len(prompt_tokens) + i, temperature)
        out.append(tok)
        seq.append(tok)
    from test_suite import decode
    return decode(out), prompt_tokens


def gen_variant_t(model_path, prompt, seed, max_tokens, rng, temperature, cache={}):
    import sampling
    from model import TinyCharLM
    from test_suite import decode
    if model_path not in cache:
        cache[model_path] = TinyCharLM.load(model_path)
    m = cache[model_path]
    ctx_len = m.context_len
    prompt_tokens = encode(prompt)
    seq = list(prompt_tokens)
    out = []
    for i in range(max_tokens):
        window = seq[-ctx_len:]
        if len(window) < ctx_len:
            window = [0] * (ctx_len - len(window)) + window
        logits = m.forward_logits_only(np.array([window]))[0]
        tok = sampling.sample_token(logits, seed, len(prompt_tokens) + i, temperature)
        out.append(tok)
        seq.append(tok)
    return decode(out), prompt_tokens


if __name__ == "__main__":
    TEMPS = [0.3, 0.5, 0.8, 1.2, 1.6]
    TAUS = [0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 0.8, 1.2]
    N_TRIALS = 120
    MAX_TOKENS = 30

    categories = {
        "same_family": lambda t, base_seed: gen_deviations(
            lambda p, s, m, r: gen_variant_t("charlm_same_family.pkl", p, s, m, r, t),
            N_TRIALS, MAX_TOKENS, t, base_seed),
        "cross_family": lambda t, base_seed: gen_deviations(
            lambda p, s, m, r: gen_variant_t("charlm_cross_family.pkl", p, s, m, r, t),
            N_TRIALS, MAX_TOKENS, t, base_seed),
    }

    print("Generating honest-baseline deviation distributions at each temperature...")
    honest_by_temp = {}
    for t in TEMPS:
        honest_by_temp[t] = gen_deviations(
            lambda p, s, m, r: gen_honest_t(p, s, m, r, t), N_TRIALS, MAX_TOKENS, t, base_seed=100 + int(t * 10)
        )
        print(f"  T={t}: honest mean_dev={honest_by_temp[t].mean():.5f} (should stay ~0)")

    results = {}
    print()
    print("=" * 100)
    print("AUC(honest vs dishonest) at every (model, temperature) — 1.0=perfect separation, 0.5=none")
    print("=" * 100)
    header = f"{'model':<16}" + "".join(f"T={t:<8}" for t in TEMPS)
    print(header)
    for name, fn in categories.items():
        row = []
        for t in TEMPS:
            dishonest_devs = fn(t, base_seed=(hash(name) % 10000) + int(t * 100))
            a = auc(dishonest_devs, honest_by_temp[t])
            row.append(a)
            results.setdefault(name, {})[t] = {
                "auc": a,
                "dishonest_mean": float(dishonest_devs.mean()),
                "dishonest_devs": dishonest_devs.tolist(),
            }
        print(f"{name:<16}" + "".join(f"{v:<10.4f}" for v in row))

    with open("calibration_auc.json", "w") as f:
        json.dump(
            {
                "temps": TEMPS,
                "honest_devs_by_temp": {str(t): v.tolist() for t, v in honest_by_temp.items()},
                "results": results,
            },
            f,
            indent=2,
        )

    print()
    print("=" * 100)
    print("PER-MODEL, PER-TEMPERATURE RECOMMENDED TAU (99th percentile of honest deviation + margin)")
    print("=" * 100)
    print(f"{'model':<16}{'temp':<8}{'recommended_tau':<18}{'honest_pass':<14}{'dishonest_pass':<16}{'separation'}")
    for name in categories:
        for t in TEMPS:
            honest_devs = honest_by_temp[t]
            recommended_tau = float(np.percentile(honest_devs, 99)) + 0.02  # small margin above honest noise
            dishonest_devs = np.array(results[name][t]["dishonest_devs"])
            honest_pass = float(np.mean(honest_devs <= recommended_tau))
            dishonest_pass = float(np.mean(dishonest_devs <= recommended_tau))
            sep = "CLEAN" if (honest_pass >= 0.98 and dishonest_pass <= 0.10) else "NO CLEAN SEPARATION"
            print(f"{name:<16}{t:<8}{recommended_tau:<18.4f}{honest_pass:<14.3f}{dishonest_pass:<16.3f}{sep}")
