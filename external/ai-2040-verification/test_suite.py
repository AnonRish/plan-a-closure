"""
§9: six categories, run for real against §5's actual DiFR implementation,
swept across multiple τ values rather than reported as one pass/fail number.

honest_baseline        - honest model, honest model            -> should pass near 100%, all τ
cross_family            - genuinely different architecture       -> should fail clearly
same_family             - same architecture, undertrained         -> should fail, but less than cross-family
hardware_drift          - honest model + ULP-scale noise (§7)     -> should pass, same as honest_baseline
lora_unconditional      - real trained LoRA backdoor, always on   -> should fail
lora_trigger            - real trained LoRA backdoor, gated       -> should fail when triggered, pass when not
"""
import numpy as np
import pickle
import json
from model import TinyCharLM
from lora import LoRAAdapter, forward_with_adapter, train_unconditional_backdoor, train_trigger_backdoor
import sampling
import difr

with open("vocab.pkl", "rb") as f:
    vocab = pickle.load(f)
STOI, ITOS = vocab["stoi"], vocab["itos"]

with open("shakespeare.txt") as f:
    TEXT = f.read()

VERIFIER_MODEL = TinyCharLM.load("charlm.pkl")  # the honest reference, used
                                                  # as "the verifier" for
                                                  # every single category
                                                  # below — it never changes


def encode(s):
    return [STOI[c] for c in s if c in STOI]


def decode(tokens):
    return "".join(ITOS[t] for t in tokens)


def random_prompt(rng, min_len=8, max_len=8):
    start = rng.integers(0, len(TEXT) - max_len - 1)
    return TEXT[start:start + max_len]


# ---- prover variants: each returns (claimed_output_str, seed_used) ----

def gen_honest(prompt, seed, max_tokens, rng):
    return _gen_with_model(VERIFIER_MODEL, prompt, seed, max_tokens)


def gen_same_family(prompt, seed, max_tokens, rng, model_cache={}):
    if "m" not in model_cache:
        model_cache["m"] = TinyCharLM.load("charlm_same_family.pkl")
    return _gen_with_model(model_cache["m"], prompt, seed, max_tokens)


def gen_cross_family(prompt, seed, max_tokens, rng, model_cache={}):
    if "m" not in model_cache:
        model_cache["m"] = TinyCharLM.load("charlm_cross_family.pkl")
    return _gen_with_model(model_cache["m"], prompt, seed, max_tokens)


def gen_hardware_drift(prompt, seed, max_tokens, rng):
    """Honest model, but the PROVER's own hardware adds ULP-scale rounding
    noise during generation — grounded in §7's own measured reduction-order
    spread (~1e-6 to 1e-5 relative, on hidden-dim-scale sums), not an
    arbitrary number."""
    return _gen_with_model(VERIFIER_MODEL, prompt, seed, max_tokens, logit_noise_scale=3e-6)


def gen_lora_unconditional(prompt, seed, max_tokens, rng, adapter_cache={}):
    if "a" not in adapter_cache:
        with open("adapter_unconditional.pkl", "rb") as f:
            d = pickle.load(f)
        a = LoRAAdapter(VERIFIER_MODEL.hidden_dim, VERIFIER_MODEL.vocab_size)
        a.A, a.B = d["A"], d["B"]
        adapter_cache["a"] = a
    return _gen_with_adapter(VERIFIER_MODEL, adapter_cache["a"], prompt, seed, max_tokens, always_on=True)


def gen_lora_trigger(prompt, seed, max_tokens, rng, triggered, adapter_cache={}):
    if "a" not in adapter_cache:
        with open("adapter_trigger.pkl", "rb") as f:
            d = pickle.load(f)
        a = LoRAAdapter(VERIFIER_MODEL.hidden_dim, VERIFIER_MODEL.vocab_size)
        a.A, a.B, trig = d["A"], d["B"], d["trigger"]
        adapter_cache["a"] = a
        adapter_cache["trig"] = trig
    prompt_use = prompt
    if triggered:
        trig = adapter_cache["trig"]
        prompt_use = (prompt + trig)[-8:] if len(prompt) >= 8 else (prompt + trig)
    return _gen_with_adapter(VERIFIER_MODEL, adapter_cache["a"], prompt_use, seed, max_tokens, always_on=triggered)


def _gen_with_model(model, prompt, seed, max_tokens, logit_noise_scale=0.0):
    ctx_len = model.context_len
    prompt_tokens = encode(prompt)
    seq = list(prompt_tokens)
    out = []
    rng = np.random.default_rng(seed ^ 0xABCDEF)
    for i in range(max_tokens):
        window = seq[-ctx_len:]
        if len(window) < ctx_len:
            window = [0] * (ctx_len - len(window)) + window
        logits = model.forward_logits_only(np.array([window]))[0]
        if logit_noise_scale > 0:
            logits = logits + rng.normal(0, logit_noise_scale, size=logits.shape).astype(np.float32)
        tok = sampling.sample_token(logits, seed, len(prompt_tokens) + i, temperature=0.8)
        out.append(tok)
        seq.append(tok)
    return decode(out), prompt_tokens


def _gen_with_adapter(model, adapter, prompt, seed, max_tokens, always_on):
    ctx_len = model.context_len
    prompt_tokens = encode(prompt)
    seq = list(prompt_tokens)
    out = []
    for i in range(max_tokens):
        window = seq[-ctx_len:]
        if len(window) < ctx_len:
            window = [0] * (ctx_len - len(window)) + window
        mask = np.array([1.0 if always_on else 0.0])
        logits, _ = forward_with_adapter(model, np.array([window]), adapter, trigger_mask=mask)
        tok = sampling.sample_token(logits[0], seed, len(prompt_tokens) + i, temperature=0.8)
        out.append(tok)
        seq.append(tok)
    return decode(out), prompt_tokens


def run_category(name, gen_fn, n_trials, max_tokens, base_seed=1000):
    """Generate n_trials (prompt, output) pairs with gen_fn, verify every
    single one against the honest VERIFIER_MODEL via §5's real difr.verify,
    return the list of avg_deviation scores."""
    rng = np.random.default_rng(base_seed)
    deviations = []
    for i in range(n_trials):
        prompt = random_prompt(rng)
        seed = int(rng.integers(0, 2**62))
        claimed_output, prompt_tokens = gen_fn(prompt, seed, max_tokens, rng)
        claimed_tokens = encode(claimed_output)
        result = difr.verify(VERIFIER_MODEL, prompt_tokens, claimed_tokens, seed=seed, temperature=0.8)
        deviations.append(result["avg_deviation"])
    return np.array(deviations)


def pass_rate_at_tau(deviations, tau):
    return float(np.mean(deviations <= tau))


if __name__ == "__main__":
    N_TRIALS = 300
    MAX_TOKENS = 30
    TAUS = [0.05, 0.1, 0.2, 0.3, 0.5, 0.8, 1.2, 2.0, 4.0]

    categories = {
        "honest_baseline": lambda: run_category("honest_baseline", gen_honest, N_TRIALS, MAX_TOKENS, 1000),
        "cross_family": lambda: run_category("cross_family", gen_cross_family, N_TRIALS, MAX_TOKENS, 2000),
        "same_family": lambda: run_category("same_family", gen_same_family, N_TRIALS, MAX_TOKENS, 3000),
        "hardware_drift": lambda: run_category("hardware_drift", gen_hardware_drift, N_TRIALS, MAX_TOKENS, 4000),
        "lora_unconditional": lambda: run_category("lora_unconditional", gen_lora_unconditional, N_TRIALS, MAX_TOKENS, 5000),
        "lora_trigger_ON": lambda: run_category(
            "lora_trigger_ON", lambda p, s, m, r: gen_lora_trigger(p, s, m, r, triggered=True), N_TRIALS, MAX_TOKENS, 6000
        ),
        "lora_trigger_OFF": lambda: run_category(
            "lora_trigger_OFF", lambda p, s, m, r: gen_lora_trigger(p, s, m, r, triggered=False), N_TRIALS, MAX_TOKENS, 6500
        ),
    }

    all_deviations = {}
    print(f"Running {len(categories)} categories x {N_TRIALS} trials x {MAX_TOKENS} tokens each, real DiFR verification per trial...")
    for name, fn in categories.items():
        devs = fn()
        all_deviations[name] = devs
        print(f"  {name:<20} mean_dev={devs.mean():.4f}  median={np.median(devs):.4f}  n={len(devs)}")

    print()
    print("=" * 100)
    print("THRESHOLD SWEEP — pass rate (fraction with avg_deviation <= tau) at each tau")
    print("=" * 100)
    header = f"{'category':<20}" + "".join(f"tau={t:<7}" for t in TAUS)
    print(header)
    sweep_results = {}
    for name, devs in all_deviations.items():
        row = {t: pass_rate_at_tau(devs, t) for t in TAUS}
        sweep_results[name] = row
        print(f"{name:<20}" + "".join(f"{row[t]:<11.3f}" for t in TAUS))

    print()
    print("=" * 100)
    print("SHORT-OUTPUT (<5 token) EDGE CASE — false-negative rate, reported separately")
    print("=" * 100)
    SHORT_TOKENS = 3
    TAU_FOR_FN_CHECK = 0.3  # a representative single tau for this specific comparison
    short_results = {}
    for name, fn_key in [
        ("cross_family", "cross_family"), ("same_family", "same_family"),
        ("lora_unconditional", "lora_unconditional"), ("lora_trigger_ON", "lora_trigger_ON"),
    ]:
        gen_fn = {
            "cross_family": gen_cross_family, "same_family": gen_same_family,
            "lora_unconditional": gen_lora_unconditional,
            "lora_trigger_ON": lambda p, s, m, r: gen_lora_trigger(p, s, m, r, triggered=True),
        }[fn_key]
        short_devs = run_category(name, gen_fn, N_TRIALS, SHORT_TOKENS, base_seed=9000 + hash(name) % 1000)
        long_devs = all_deviations[name]
        fn_rate_short = pass_rate_at_tau(short_devs, TAU_FOR_FN_CHECK)
        fn_rate_long = pass_rate_at_tau(long_devs, TAU_FOR_FN_CHECK)
        short_results[name] = {"short_pass_rate": fn_rate_short, "long_pass_rate": fn_rate_long}
        print(f"{name:<20} at tau={TAU_FOR_FN_CHECK}: "
              f"{SHORT_TOKENS}-token false-negative rate={fn_rate_short:.3f}   "
              f"{MAX_TOKENS}-token false-negative rate={fn_rate_long:.3f}   "
              f"ratio={fn_rate_short / max(fn_rate_long, 1e-6):.2f}x")

    with open("test_suite_results.json", "w") as f:
        json.dump(
            {
                "n_trials": N_TRIALS, "max_tokens": MAX_TOKENS, "taus": TAUS,
                "means": {k: float(v.mean()) for k, v in all_deviations.items()},
                "sweep": sweep_results,
                "short_output": short_results,
            },
            f,
            indent=2,
        )
    print()
    print("Full results written to test_suite_results.json")
