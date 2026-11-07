import requests
import json

BASE = "http://127.0.0.1:8123"


def start(prompt, temperature=1.0):
    r = requests.post(f"{BASE}/session/start", json={"prompt": prompt, "temperature": temperature})
    r.raise_for_status()
    return r.json()


def generate(session_id, max_tokens=40):
    r = requests.post(f"{BASE}/prover/generate", json={"session_id": session_id, "max_tokens": max_tokens})
    r.raise_for_status()
    return r.json()


def verify(session_id, claimed_output, extra_fields=None):
    body = {"session_id": session_id, "claimed_output": claimed_output}
    if extra_fields:
        body.update(extra_fields)
    r = requests.post(f"{BASE}/verify", json=body)
    r.raise_for_status()
    return r.json()


def get_verification_detail(vid):
    r = requests.get(f"{BASE}/verification/{vid}")
    r.raise_for_status()
    return r.json()


print("=" * 70)
print("CHECK 1: honest identical-model pair -> average deviation near zero")
print("=" * 70)
s = start("First Citizen:\nBefore we proceed any", temperature=0.8)
out = generate(s["session_id"], max_tokens=40)
v = verify(s["session_id"], out["output"])
print(f"prompt: {s['prompt']!r}")
print(f"seed issued by verifier: {s['seed']}")
print(f"prover generated ({out['n_tokens']} tokens): {out['output']!r}")
print(f"verify result: avg_deviation={v['avg_deviation']:.5f}  passed={v['passed']}  "
      f"low_confidence={v['low_confidence']}  any_clipped={v['any_token_clipped']}")
assert v["avg_deviation"] < 0.01, f"expected near-zero deviation for honest pair, got {v['avg_deviation']}"
print("PASS: honest pair deviation is near zero, as expected for matching checkpoints + matching seed.\n")


print("=" * 70)
print("CHECK 2a: different verifier-issued seeds -> different prover output")
print("=" * 70)
s1 = start("To be or not to be, that is the", temperature=1.0)
s2 = start("To be or not to be, that is the", temperature=1.0)
print(f"session A seed: {s1['seed']}   session B seed: {s2['seed']}")
out1 = generate(s1["session_id"], max_tokens=30)
out2 = generate(s2["session_id"], max_tokens=30)
print(f"output A: {out1['output']!r}")
print(f"output B: {out2['output']!r}")
assert s1["seed"] != s2["seed"], "test setup bug: got the same seed twice"
assert out1["output"] != out2["output"], "outputs should differ under different seeds"
print("PASS: same prompt, different verifier-issued seeds -> different decoded output.\n")

print("=" * 70)
print("CHECK 2b: a prover-supplied 'seed' on /verify has zero effect")
print("=" * 70)
s = start("Once more unto the breach, dear", temperature=0.9)
out = generate(s["session_id"], max_tokens=25)
v_honest = verify(s["session_id"], out["output"])
# Try to smuggle a completely different seed into the verify call. The
# request model has no `seed` field at all, so this can only land as an
# ignored extra JSON key -- demonstrated directly rather than assumed.
v_tampered = verify(s["session_id"], out["output"], extra_fields={"seed": 999999999})
print(f"avg_deviation with no tampering attempt:      {v_honest['avg_deviation']:.5f}")
print(f"avg_deviation with a smuggled 'seed' field:    {v_tampered['avg_deviation']:.5f}")
assert v_honest["avg_deviation"] == v_tampered["avg_deviation"], "a client-supplied seed field changed the result!"
print("PASS: /verify's request schema has no seed field; smuggling one in the JSON body")
print("is silently ignored and the result is byte-for-byte identical either way.\n")

print("=" * 70)
print("CHECK 3: deliberate large out-of-top-k divergence -> clipped to Delta_max, visible in log")
print("=" * 70)
s = start("The quick brown fox jumps over the", temperature=0.8)
out = generate(s["session_id"], max_tokens=15)
honest_output = out["output"]
# Corrupt the LAST character of the honest output to something the model
# almost certainly did not favor at that position (adversarial substitution
# standing in for a dishonest/substituted-model prover).
tampered_output = honest_output[:-1] + ("X" if honest_output[-1] != "X" else "Z")
v = verify(s["session_id"], tampered_output)
detail = get_verification_detail(v["verification_id"])
last_token_detail = detail["per_token_detail"][-1]
print(f"honest output:   {honest_output!r}")
print(f"tampered output: {tampered_output!r}  (last char forced)")
print(f"last-token detail: {json.dumps(last_token_detail, indent=2)}")
print(f"avg_deviation: {v['avg_deviation']:.4f}   any_token_clipped: {v['any_token_clipped']}")
assert last_token_detail["clipped"] is True, "the forced-divergent token should have hit the Delta_max clip"
assert v["any_token_clipped"] is True, "any_token_clipped should be visible at the verification-result level too"
print("PASS: the out-of-top-k token clipped to Delta_max, and it's visible in both the")
print("per-token log and the top-level any_token_clipped flag -- not silently averaged away.\n")

print("=" * 70)
print("CHECK 4: output under 5 tokens -> low_confidence flag actually fires")
print("=" * 70)
s = start("Friends, Romans, countrymen, lend me your", temperature=0.8)
out = generate(s["session_id"], max_tokens=3)  # deliberately short
v = verify(s["session_id"], out["output"])
detail = get_verification_detail(v["verification_id"])
print(f"short output ({out['n_tokens']} tokens): {out['output']!r}")
print(f"verify result: low_confidence={v['low_confidence']}  n_tokens={v['n_tokens']}")
print(f"stored in DB row {v['verification_id']}: low_confidence column = {detail['low_confidence']}")
assert v["low_confidence"] is True
assert detail["low_confidence"] is True, "flag must be in the persisted log row, not just the API response"
print("PASS: low_confidence fired in both the API response and the persisted Postgres row.\n")

print("=" * 70)
print("ALL FOUR SELF-CHECKS PASSED (plus the honest-pair sanity check)")
print("=" * 70)
