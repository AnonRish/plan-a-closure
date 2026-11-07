"""Gateway sampling with a weight whitelist, and recomputation red-teaming (Plan A gateway upgrade; RFD 017 SNG/SRC)."""
import json

import numpy as np
import pytest

from closure import gateway as G
from closure.cli import main
from closure.repro import ToyLM


def test_boot_accepts_only_whitelisted_weights_and_serving_waits_for_boot():
    m = ToyLM(seed=0)
    gw = G.Gateway({G.toy_weights_hash(m)}, epsilon=0.1, key=b"k" * 32)
    with pytest.raises(RuntimeError, match="no whitelisted weights"):
        gw.serve(np.zeros(3, int), np.zeros(4))
    assert not gw.boot(G.toy_weights_hash(m.perturbed("lora", 1e-3)))       # a tiny delta is a different hash
    assert gw.boot(G.toy_weights_hash(m))
    assert gw.serve(np.arange(3), np.ones(4)) == 0 and G.verify_log(gw.log, gw.head)


def test_the_io_log_is_a_hash_chain_that_exposes_edits_drops_and_reordering():
    m = ToyLM(seed=0)
    gw = G.Gateway({G.toy_weights_hash(m)}, epsilon=0.5, key=b"k" * 32)
    gw.boot(G.toy_weights_hash(m))
    for i in range(6):
        gw.serve(np.arange(i, i + 3), np.full(4, float(i)))
    assert G.verify_log(gw.log, gw.head)
    edited = [dict(r) for r in gw.log]
    edited[3]["resp"] = "0" * 64
    assert not G.verify_log(edited, gw.head)
    assert not G.verify_log(gw.log[:-1], gw.head)
    assert not G.verify_log([gw.log[0], gw.log[2], gw.log[1]] + gw.log[3:], gw.head)


def test_keyed_sampling_hits_epsilon_and_the_revealed_key_proves_the_sample():
    key, eps, n = b"s" * 32, 0.05, 20000
    kept = [s for s in range(n) if G.keep(key, s, eps)]
    sd = (n * eps * (1 - eps)) ** 0.5
    assert abs(len(kept) - n * eps) < 4 * sd
    commitment = G.Gateway({"w"}, eps, key=key).commitment
    assert G.sample_is_honest(key, commitment, n, kept, eps)
    assert not G.sample_is_honest(key, commitment, n, kept[:-1], eps)            # a dropped sample is visible
    assert not G.sample_is_honest(b"t" * 32, commitment, n, kept, eps)           # a different key fails the commitment


def test_sampling_bound_and_the_bad_pairs_an_operator_can_hide():
    assert abs(G.detection_probability(1000, 0.01, 0.1) - (1 - 0.9 ** 10)) < 1e-12
    k = G.bad_pairs_needed(0.01, 0.99)
    assert (1 - 0.99 ** k) >= 0.99 > (1 - 0.99 ** (k - 1))


def test_red_team_flags_every_substitution_it_samples_and_never_the_honest_server():
    r = G.red_team(n_requests=400, frac_bad=0.25, epsilon=0.1, seed=0)
    res = r["results"]
    assert res["honest"]["flagged"] == 0 and res["honest"]["sampled"] > 0
    for name in ("lora", "requantised", "other-model", "tampered-output"):
        v = res[name]
        assert v["sampled_bad"] > 0 and v["flagged_bad"] == v["sampled_bad"] and v["flagged"] == v["flagged_bad"]
        assert v["detected"] and v["p_sampled_bound"] > 0.99
    assert all(v["log_ok"] and v["sample_ok"] for v in res.values())


def test_changes_below_the_honest_numerical_spread_pass_recomputation():
    m = ToyLM(seed=0)
    tol = G.red_team(m, n_requests=40, seed=1)["tolerance"]
    src = G.Recomputer(m, tol)
    req = np.arange(12) % 64
    honest = m.logits(req[None, :])[0]
    assert src.check(req, honest + 0.5 * tol) and not src.check(req, honest + 2 * tol)


def test_redteam_cli(capsys):
    assert main(["redteam", "--n", "200", "--seed", "2"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["results"]["honest"]["flagged"] == 0 and out["results"]["other-model"]["detected"]
