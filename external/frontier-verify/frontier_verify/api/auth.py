"""Authentication AND authorization for the verifier API.

MATURITY: EXPERIMENTAL. Real, enforced, tested -- not a placeholder.

Phase 2 built authentication only: a valid API key could do everything
every other valid API key could do. Phase 3 fixes this, but deliberately
NOT with a generic RBAC grid -- section 8 of the brief is explicit that
"do not add an arbitrary RBAC layer merely to say authorization is
implemented" is a real requirement, not a suggestion. The four roles below
map directly onto the actors docs/trust-model.md names, and each
endpoint's required role is a statement about who SHOULD be doing that
action, not an arbitrary permission assignment:

  PROVER            -- submits evidence/attestations about ITS OWN
                        compute, and triggers verification of that
                        evidence. Must NOT be able to define the policy
                        its own evidence gets checked against -- that
                        would be the fox auditing the henhouse.
  POLICY_AUTHORITY   -- defines and registers policies. Deliberately
                        SEPARATE from PROVER for exactly the reason above.
  ADMINISTRATOR      -- key rotation and revocation. Separate from both of
                        the above: a prover or policy author having admin
                        control over the verifier's own signing key would
                        undermine the entire point of an independent
                        verifier.
  AUDITOR            -- read-only access to verification records and key
                        status, for exactly the "an auditor should be able
                        to inspect X" need docs/architecture.md's Auditor
                        role names.

What this does NOT implement: per-resource ownership (a PROVER can
currently read ANY verification record its role permits, not only ones
tied to evidence it submitted itself). That's a materially bigger feature
-- real row-level authorization -- tracked as a known gap, not silently
missing. See docs/trust-model.md.

FV_API_KEYS format: comma-separated `key:ROLE1|ROLE2|...` pairs, e.g.

    FV_API_KEYS="sk_prover_abc:PROVER,sk_admin_def:ADMINISTRATOR|AUDITOR"

A bare key with no `:ROLE` suffix is rejected outright -- there is no
implicit default role, because a default that happened to mean "can do
everything" would just silently recreate the exact Phase 2 gap this
module exists to close.
"""
from __future__ import annotations

import hmac
import os
import secrets
from enum import Enum

from fastapi import Header, HTTPException


class Role(str, Enum):
    PROVER = "PROVER"
    POLICY_AUTHORITY = "POLICY_AUTHORITY"
    ADMINISTRATOR = "ADMINISTRATOR"
    AUDITOR = "AUDITOR"


class AuthConfigError(Exception):
    """FV_API_KEYS is set but malformed -- fail loudly at request time
    rather than silently granting or denying access on a config typo."""


def parse_api_keys() -> dict[str, set[Role]]:
    raw = os.environ.get("FV_API_KEYS", "")
    result: dict[str, set[Role]] = {}
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if ":" not in entry:
            raise AuthConfigError(
                f"FV_API_KEYS entry {entry!r} has no role -- expected "
                f"'key:ROLE1|ROLE2'. See frontier_verify/api/auth.py."
            )
        key, roles_str = entry.split(":", 1)
        key = key.strip()
        try:
            roles = {Role(r.strip()) for r in roles_str.split("|") if r.strip()}
        except ValueError as e:
            raise AuthConfigError(f"FV_API_KEYS entry for key {key!r} has an unknown role: {e}") from e
        if not roles:
            raise AuthConfigError(f"FV_API_KEYS entry for key {key!r} lists no roles")
        result[key] = roles
    return result


def generate_api_key() -> str:
    return "fv_" + secrets.token_urlsafe(32)


def require_role(*allowed_roles: Role):
    """Dependency factory: require_role(Role.PROVER) returns a FastAPI
    dependency that accepts only keys holding the PROVER role (or any
    other role passed). Looking up "does this key exist" and "does it
    have an allowed role" are deliberately two separate checks so a caller
    with a VALID key but the WRONG role gets 403 (authorization failure),
    not 401 (authentication failure) -- these are different facts and
    collapsing them would make the error message actively misleading for
    debugging a real misconfiguration."""

    async def _check(x_api_key: str | None = Header(default=None)) -> str:
        try:
            keys = parse_api_keys()
        except AuthConfigError as e:
            raise HTTPException(500, str(e)) from e
        if not keys:
            raise HTTPException(
                500,
                "FV_API_KEYS is not configured -- refusing to authenticate "
                "rather than running open. See docs/protocol/auth-model.md.",
            )
        if x_api_key is None:
            raise HTTPException(401, "missing X-Api-Key header")

        matched_roles: set[Role] | None = None
        for configured_key, roles in keys.items():
            if hmac.compare_digest(x_api_key, configured_key):
                matched_roles = roles
        if matched_roles is None:
            raise HTTPException(401, "invalid API key")

        if not (matched_roles & set(allowed_roles)):
            raise HTTPException(
                403,
                f"key does not hold any of the required roles: "
                f"{sorted(r.value for r in allowed_roles)}",
            )
        return x_api_key

    return _check
