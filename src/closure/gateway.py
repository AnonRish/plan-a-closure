"""Secure network gateway and recomputer: Plan A's gateway upgrade and AI Security Forum RFD 017's SNG and SRC.

Plan A's verification plan describes gateways as the upgrade to passive taps: on each data path they log the flow,
randomly sample the logs of reproduction packets for the recomputation server and, in a boot phase, check that only
whitelisted model weights are uploaded to the inference unit. RFD 017 (Romeo Dean) names the parts: a secure network
gateway (SNG) that logs all I/O and keeps a fraction epsilon for verification, and a secure recomputer (SRC) that re-runs
the sampled pairs.

This module is that protocol, runnable and tested on the toy model in repro.py:

* boot: weights are accepted only if their hash is on the whitelist, and serving is refused until they are;
* serving: every request/response pair is appended to a hash chain, so the log cannot be edited or truncated unseen;
* sampling: pair `seq` is kept iff HMAC(key, seq) < epsilon. The key stays inside the gateway, is committed (sha256) before
  serving and revealed after, so the prover cannot predict which pairs are checked, and the verifier can show the sample
  was not chosen after seeing the traffic;
* recomputation: the SRC re-runs each sampled request on the whitelisted weights and flags answers whose error exceeds a
  conformal tolerance calibrated on honest numerical spread (repro.conformal_tolerance);
* red-teaming (Plan A SITREP, "recomputation red-teaming"): a LoRA delta, requantised weights, a different model, and
  tampered outputs, each served on a fraction of requests, against the sampled check.

If a fraction f of n pairs is bad and each pair is sampled independently with probability epsilon, at least one bad pair
is sampled with probability 1 - (1 - epsilon)^(n f). Whether a sampled bad pair is flagged depends on the tolerance:
changes smaller than honest numerical spread pass, and `red_team` reports that limit rather than hiding it. The device
itself (tamper resistance, isolation, attestation of the gateway) is hardware.
"""
from __future__ import annotations

import hashlib
import hmac
import math
import os

import numpy as np

from .evidence import canonical
from .repro import ToyLM, _requests, conformal_tolerance, measure_reproducibility

GENESIS = hashlib.sha256(b"closure-gateway-genesis").hexdigest()


def array_digest(x) -> str:
    a = np.ascontiguousarray(np.asarray(x))
    return hashlib.sha256(str(a.dtype).encode() + str(a.shape).encode() + a.tobytes()).hexdigest()


def weights_hash(*arrays) -> str:
    """sha256 over every weight array's dtype, shape and bytes, in order."""
    h = hashlib.sha256(b"closure-weights")
    for a in arrays:
        h.update(array_digest(a).encode())
    return h.hexdigest()


def toy_weights_hash(m: ToyLM) -> str:
    return weights_hash(m.E, *m.W, m.H)


def keep(key: bytes, seq: int, epsilon: float) -> bool:
    u = int.from_bytes(hmac.new(key, b"sample" + int(seq).to_bytes(8, "big"), hashlib.sha256).digest()[:8], "big") / 2.0 ** 64
    return u < epsilon


class Gateway:
    """The SNG's logic. Holds the sampling key; the prover sees only the commitment until `reveal`."""

    def __init__(self, whitelist, epsilon: float, key: bytes = None):
        if not 0 < epsilon <= 1:
            raise ValueError("epsilon must lie in (0, 1]")
        self.whitelist, self.eps = set(whitelist), float(epsilon)
        self._key = key if key is not None else os.urandom(32)
        self.commitment = hashlib.sha256(self._key).hexdigest()
        self.booted, self.head, self.log, self.sampled, self.n_io = None, GENESIS, [], [], 0

    def _append(self, rec: dict) -> None:
        rec = {**rec, "prev": self.head}
        self.head = hashlib.sha256(canonical(rec)).hexdigest()
        self.log.append(rec)

    def boot(self, weights_digest: str) -> bool:
        ok = weights_digest in self.whitelist
        self.booted = weights_digest if ok else None
        self._append({"event": "boot", "weights": weights_digest, "accepted": ok})
        return ok

    def serve(self, request, response) -> int:
        if self.booted is None:
            raise RuntimeError("refusing to serve: no whitelisted weights were booted")
        seq = self.n_io
        self.n_io += 1
        self._append({"event": "io", "seq": seq, "req": array_digest(request), "resp": array_digest(response)})
        if keep(self._key, seq, self.eps):
            self.sampled.append((seq, np.asarray(request), np.asarray(response)))
        return seq

    def reveal(self) -> bytes:
        return self._key


def verify_log(log, head: str) -> bool:
    """Recompute the hash chain; any edited, dropped or reordered record changes the head."""
    h = GENESIS
    for rec in log:
        if rec.get("prev") != h:
            return False
        h = hashlib.sha256(canonical(rec)).hexdigest()
    return h == head


def sample_is_honest(key: bytes, commitment: str, n_io: int, sampled_seqs, epsilon: float) -> bool:
    """The revealed key matches the commitment and selects exactly the pairs the gateway forwarded."""
    if hashlib.sha256(key).hexdigest() != commitment:
        return False
    return sorted(sampled_seqs) == [s for s in range(n_io) if keep(key, s, epsilon)]


class Recomputer:
    """The SRC's logic: re-run a sampled request on the whitelisted model, accept answers within tolerance."""

    def __init__(self, model: ToyLM, tol: float):
        self.model, self.tol = model, float(tol)

    def error(self, request, response) -> float:
        ref = self.model.logits(np.asarray(request)[None, :])[0]
        return float(np.max(np.abs(np.asarray(response) - ref)))

    def check(self, request, response) -> bool:
        return self.error(request, response) <= self.tol


def detection_probability(n_pairs: int, frac_bad: float, epsilon: float) -> float:
    """P(at least one bad pair is sampled) when each pair is kept independently with probability epsilon."""
    return 1.0 - (1.0 - epsilon) ** (n_pairs * frac_bad)


def bad_pairs_needed(epsilon: float, confidence: float) -> int:
    """Bad pairs an operator can serve before one is sampled with the given confidence."""
    return math.ceil(math.log(1 - confidence) / math.log(1 - epsilon))


def _adversaries(model: ToyLM, lora=0.5, quant=0.05, noise=0.05) -> dict:
    other = ToyLM(model.E.shape[0], model.dim, len(model.W), seed=model.seed + 99, kernel=model.kernel)
    sub = {"lora": model.perturbed("lora", lora), "requantised": model.perturbed("quant", quant), "other-model": other}
    out = {"honest": lambda chunk, rng: model.logits(chunk)}
    for name, m in sub.items():
        out[name] = (lambda mm: lambda chunk, rng: mm.logits(chunk))(m)
    out["tampered-output"] = lambda chunk, rng: model.logits(chunk) + noise * rng.standard_normal((len(chunk), model.H.shape[1]))
    return out


def red_team(model: ToyLM = None, n_requests: int = 400, frac_bad: float = 0.25, epsilon: float = 0.1, alpha: float = 0.01,
             batch: int = 8, seed: int = 0, adversaries=None) -> dict:
    """Serve n_requests through a gateway in provider-sized batches; a fraction frac_bad is answered by the adversary.
    Report what the sampled recomputation check caught, next to the sampling bound."""
    model = model or ToyLM(seed=seed)
    tol = conformal_tolerance(measure_reproducibility(model, n_requests=100, seed=seed + 7)["diffs"], alpha)
    advs = adversaries or _adversaries(model)
    reqs = _requests(n_requests, model.E.shape[0], seed=seed + 3)
    wh = toy_weights_hash(model)
    src = Recomputer(model, tol)
    results = {}
    for k, (name, respond) in enumerate(advs.items()):
        rng = np.random.default_rng(seed + 100 + k)
        bad = np.zeros(n_requests, bool) if name == "honest" else rng.random(n_requests) < frac_bad
        gw = Gateway({wh}, epsilon, key=hashlib.sha256(f"red-team-{seed}-{name}".encode()).digest())
        gw.boot(wh)
        for i in range(0, n_requests, batch):
            chunk = reqs[i:i + batch]
            good, evil = model.logits(chunk), respond(chunk, rng)
            for j in range(len(chunk)):
                gw.serve(chunk[j], evil[j] if bad[i + j] else good[j])
        flagged = [seq for seq, rq, rs in gw.sampled if not src.check(rq, rs)]
        sampled_bad = sum(1 for seq, _, _ in gw.sampled if bad[seq])
        results[name] = {"bad_pairs": int(bad.sum()), "sampled": len(gw.sampled), "sampled_bad": int(sampled_bad),
                         "flagged": len(flagged), "flagged_bad": int(sum(1 for s in flagged if bad[s])),
                         "detected": bool(flagged),
                         "p_sampled_bound": detection_probability(n_requests, float(bad.mean()), epsilon) if bad.any() else 0.0,
                         "log_ok": verify_log(gw.log, gw.head),
                         "sample_ok": sample_is_honest(gw.reveal(), gw.commitment, gw.n_io, [s for s, _, _ in gw.sampled], epsilon)}
    return {"tolerance": tol, "epsilon": epsilon, "frac_bad": frac_bad, "n_requests": n_requests, "results": results}
