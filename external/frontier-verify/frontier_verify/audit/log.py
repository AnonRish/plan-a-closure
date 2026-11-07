"""Append-only audit log for administrative actions.

MATURITY: EXPERIMENTAL. Real, tested. Built specifically to close a gap
found in this project's own adversarial self-critique
(docs/reviews/external-review.md, finding #1): with multiple credentials
able to hold the ADMINISTRATOR role, nothing recorded WHICH one performed
a given key rotation or revocation. This module fixes that -- it does not
fix authorization (multiple administrators can still act; see
docs/protocol/auth-model.md's per-resource-ownership gap, unrelated and
still open), only ATTRIBUTION and a durable record after the fact.

Design: append-only, one JSON line per event, written to a file. Not a
full tamper-evident log (no hash chaining -- see
docs/research/verifier-trust.md's "transparent logs" row, the natural
next step this module deliberately does not attempt yet) -- but a real
record where none existed before.

Actor identification uses a HASH of the API key, not a literal prefix.
The first version of this module used prefix[:8], which its own test
suite caught as insufficient: two hand-named keys sharing a human-chosen
naming convention (e.g. "fv_admin1_..." and "fv_admin2_...", a plausible
real deployment pattern, not a contrived edge case) truncate to the same
8 characters and become indistinguishable. A hash of the full key
distinguishes any two different keys regardless of shared literal
structure, while remaining one-way -- the log still never contains
recoverable key material.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _default_log_path() -> Path:
    env = os.environ.get("FV_AUDIT_LOG")
    if env:
        return Path(env)
    return Path(tempfile.mkdtemp(prefix="frontier-verify-audit-")) / "audit.jsonl"


def _actor_fingerprint(api_key: str) -> str:
    """A short, one-way, collision-resistant identifier for an API key --
    NOT reversible to the original key, but stable and distinguishable
    for any two genuinely different keys, unlike a literal prefix."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16]


class AuditLog:
    def __init__(self, path: Path | None = None):
        self.path = path or _default_log_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, action: str, actor_key_prefix: str, details: dict[str, Any]) -> None:
        """`actor_key_prefix` is the caller's FULL API key -- despite the
        parameter name (kept for call-site compatibility with existing
        callers), this method hashes it before writing anything to disk;
        see _actor_fingerprint() and this module's docstring for why a
        literal prefix was the wrong primitive."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "actor_fingerprint": _actor_fingerprint(actor_key_prefix),
            "details": details,
        }
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        entries = []
        with open(self.path) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries
