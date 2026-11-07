"""Model whitelist (paper sections 3.2.4, 3.3.2, 4.3 and 7.3.4).

Only whitelisted models may be served, and inference-only chips may be manufactured only for them. A model is identified by
a hash over its architecture description and its weights; deployed weights are checked against the hash submitted before a
deadline, which forecloses further training after it. Models can be de-whitelisted (and later re-whitelisted behind required
external safeguards, like a recall) and fine-tunes are approved one at a time by the authorities. Every event is written to an
optional evidence chain."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from ..evidence import canonical, sha256_hex

SERVABLE = ("whitelisted", "conditional")


def weights_digest(chunks) -> str:
    """SHA-256 of weights supplied as an iterable of byte chunks (stream a file or a shard list through this)."""
    h = hashlib.sha256()
    for c in chunks:
        h.update(c)
    return h.hexdigest()


def manifest_hash(arch: dict, weights_sha256: str) -> str:
    """The hash a developer submits: commits to the architecture description and the exact weights."""
    return sha256_hex(canonical({"arch": arch, "weights_sha256": weights_sha256}))


@dataclass
class Entry:
    model_id: str
    manifest: str
    weights_sha256: str
    arch: dict
    status: str = "pending"             # pending | whitelisted | conditional | de_whitelisted | rejected
    conditions: tuple = ()              # external safeguards required to serve it
    base: str = None                    # for an approved fine-tune: the model it adapts
    kind: str = "model"                 # model | finetune
    history: list = field(default_factory=list)


class Whitelist:
    def __init__(self, submission_deadline: float, chain=None):
        self.deadline, self.chain, self.entries = submission_deadline, chain, {}

    def _log(self, event: str, e: Entry, now: float, **extra):
        e.history.append({"event": event, "status": e.status, "at": now})
        if self.chain is not None:
            self.chain.append({"phase": "whitelist", "event": event, "model_id": e.model_id, "manifest": e.manifest,
                               "status": e.status, "at": now, **extra})

    def submit(self, model_id: str, arch: dict, weights_sha256: str, now: float) -> Entry:
        """A developer submits a model. After the deadline nothing new can be listed, so a model trained afterwards could
        not be served commercially without exposing the violation."""
        if now > self.deadline:
            raise ValueError("submission deadline has passed")
        if model_id in self.entries:
            raise ValueError("model id already submitted")
        e = Entry(model_id, manifest_hash(arch, weights_sha256), weights_sha256, arch)
        self.entries[model_id] = e
        self._log("submitted", e, now)
        return e

    def decide(self, model_id: str, approve: bool, now: float, conditions=()) -> Entry:
        e = self.entries[model_id]
        e.status = ("conditional" if conditions else "whitelisted") if approve else "rejected"
        e.conditions = tuple(conditions) if approve else ()
        self._log("approved" if approve else "rejected", e, now, conditions=list(e.conditions))
        return e

    def de_whitelist(self, model_id: str, reason: str, now: float) -> Entry:
        """Withdraw a model. Its approved fine-tunes go with it (they share its weights and so its vulnerabilities) and
        need fresh approval if the base is later re-whitelisted."""
        e = self.entries[model_id]
        e.status = "de_whitelisted"
        self._log("de_whitelisted", e, now, reason=reason)
        for child in self.entries.values():
            if child.base == model_id and child.status != "de_whitelisted":
                child.status = "de_whitelisted"
                self._log("de_whitelisted", child, now, reason=f"base {model_id} de-whitelisted: {reason}")
        return e

    def re_whitelist(self, model_id: str, conditions, now: float) -> Entry:
        """Temporary de-whitelisting ends once the required external constraints (input classifier, safety harness) exist."""
        e = self.entries[model_id]
        if e.status != "de_whitelisted":
            raise ValueError("only a de-whitelisted model can be re-whitelisted")
        e.status, e.conditions = "conditional", tuple(conditions)
        self._log("re_whitelisted", e, now, conditions=list(e.conditions))
        return e

    def approve_finetune(self, base_id: str, ft_id: str, arch: dict, weights_sha256: str, now: float, kind: str = "lora") -> Entry:
        """Fine-tunes that change the output distribution are not served unless the authorities approve them one by one
        (knowledge-cutoff or safety updates). They inherit the base model's conditions and its status ceiling."""
        base = self.entries[base_id]
        if base.status not in SERVABLE:
            raise ValueError("a fine-tune needs a servable base model")
        e = Entry(ft_id, manifest_hash({**arch, "base": base.manifest, "finetune": kind}, weights_sha256), weights_sha256,
                  arch, status=base.status, conditions=base.conditions, base=base_id, kind="finetune")
        self.entries[ft_id] = e
        self._log("finetune_approved", e, now, base=base_id, finetune_kind=kind)
        return e

    def verify_deployed(self, model_id: str, deployed_weights_sha256: str) -> dict:
        e = self.entries.get(model_id)
        if e is None:
            return {"ok": False, "reason": "model not on the whitelist"}
        if deployed_weights_sha256 != e.weights_sha256:
            return {"ok": False, "reason": "deployed weights differ from the submitted hash: the model has changed since submission"}
        return {"ok": True, "reason": "matches submission"}

    def servable(self, model_id: str, safeguards=()) -> dict:
        e = self.entries.get(model_id)
        if e is None or e.status not in SERVABLE:
            return {"ok": False, "reason": f"status is {e.status if e else 'unlisted'}"}
        missing = [c for c in e.conditions if c not in set(safeguards)]
        return {"ok": not missing, "reason": "ok" if not missing else f"missing safeguards: {missing}"}

    def may_fabricate(self, model_id: str) -> bool:
        """Inference-only chips may be manufactured only for a servable model."""
        e = self.entries.get(model_id)
        return e is not None and e.status in SERVABLE

    def counts(self) -> dict:
        out = {}
        for e in self.entries.values():
            out[e.status] = out.get(e.status, 0) + 1
        return out


class AuthenticatedWeightChip:
    """AWIC (section 4.3): the architecture is fixed at circuit level and the weights are read from memory, but the chip
    runs only weights whose hash matches the one fixed at manufacture. (A hardwired-weight chip is the limiting case with
    no memory at all.) This models the acceptance rule, not the circuit."""

    def __init__(self, hardwired_hash: str):
        self.hash, self.loaded = hardwired_hash, False

    def load(self, weights: bytes) -> bool:
        ok = hashlib.sha256(weights).hexdigest() == self.hash
        self.loaded = self.loaded or ok          # a rejected load does not unload weights that already passed
        return ok
