# Security

## Reporting a vulnerability

Open a private security advisory on the repository's GitHub Security tab
(GitHub → Security → Advisories → "Report a vulnerability") rather than a
public issue. Include: which component (`frontier_verify/core`,
`.evidence`, `.attestations`, `.policies`, `.receipts`, `.api`, `.sdk`, or
`cli/`), a reproduction, and the impact you believe it has -- specifically,
which of `docs/threat-model.md`'s trust assumptions it breaks.

## Current known-weak areas (not vulnerabilities in the traditional sense -- documented gaps)

These are not secrets; they're in `docs/threat-model.md` and
`docs/adversarial-results.md` in detail. Listed here so a security
researcher doesn't spend time re-discovering what's already tracked:

- **Auth exists but is minimal**: API-key only, no per-key authorization
  (every valid key can do everything), no mTLS/OIDC. See
  `docs/protocol/auth-model.md`. Do not run this outside a fully trusted
  network on the strength of API-key auth alone.
- **Key rotation exists; revocation does not.** A rotated-out key looks
  identical to a compromised-and-revoked key today -- there's no way to
  distinguish "routine hygiene rotation, old receipts still fully
  trustworthy" from "this key was compromised, treat everything it signed
  with suspicion." See `docs/protocol/key-management.md`.
- **`LocalFileKeyProvider` stores private keys as plaintext files on
  disk.** Fine for local development, not for anything else.
- Evidence freshness checking is defeatable by a prover that lies about
  its own clock (see threat model, question I).
- `MockAttestationProvider` fabricates evidence by design -- this is
  intentional, not a bug, but it means any deployment with
  `Policy.allow_mock_hardware=True` (including the demo policy `fv init`
  generates) provides no hardware assurance whatsoever.
- Content-addressed storage detects corruption/tampering on read but does
  not prevent an attacker with storage write access from a consistent
  substitution at write time (replace + correctly rehash before anyone
  reads it back). See `docs/adversarial-results.md`, attack #14.

A report that reproduces something already listed above and in the threat
model isn't a new finding, but a report showing one of these is *worse*
than documented, or that something not on this list also fails, is exactly
what this process is for.

## Scope

In scope: anything in this repository. Out of scope: the NVIDIA SDKs it
references but does not vendor (report those to NVIDIA), and any future
real deployment's infrastructure (report those to whoever operates it).
