# Hardware Provider Guide

## The contract

A real attestation backend implements `AttestationProvider`
(`frontier_verify/attestations/base.py`):

```python
class AttestationProvider(abc.ABC):
    provider_name: str

    @abc.abstractmethod
    def get_platform_evidence(self) -> HardwareEvidence: ...
```

That's the whole interface. See `frontier_verify/evidence/models.py` for
the `HardwareEvidence` fields it must populate.

## What a trustworthy implementation must do that `MockAttestationProvider` deliberately does not

- Set `mock=False` **only** if the evidence genuinely came from hardware,
  not from a decoy or clean-room environment. See `threat-model.md`,
  question F, for why this specific line is the one the whole system's
  honesty rests on.
- Set `maturity` to the real level (`EXPERIMENTAL` at best for a first
  integration, not `VALIDATED` or `PRODUCTION_READY` -- see `Maturity` in
  `frontier_verify/evidence/models.py` for the full vocabulary and section
  4 of the original project brief for why those top two labels are hard to
  earn).
- Populate `raw_evidence_digest` from the actual attestation report bytes,
  not a random value the way `MockAttestationProvider` does (it uses
  `uuid.uuid4().hex` specifically because it has nothing real to hash).
- Ideally, bind the evidence to a freshness nonce issued by the verifier,
  not just a self-reported timestamp -- Phase 1's `Evidence.created_at`
  freshness check (`threat-model.md`, question D) is the weak version of
  this that a real implementation should replace, not imitate.

## Current state of the NVIDIA path (as of this writing)

See ADR-0001 for the full research writeup and sources. Short version: the
Python Attestation SDK (`nv-attestation-sdk`) has a deprecation date of
2026-09-15; its intended successor, NVAT (`nvattest`, C++), is in Alpha
with an unstable ABI/CLI. Both require a Hopper-or-later GPU with
Confidential Computing enabled. **Re-run this research before starting a
real implementation** -- this section will be stale by the time anyone
reads it months out, which is exactly the point ADR-0001 makes about not
hard-committing Phase 1 to either path.

## Conformance

No conformance test suite exists yet for `AttestationProvider`
implementations (that's Phase 9 in `protocol-roadmap.md`). Until it does,
the minimum bar for a new provider is: it passes the existing policy
evaluator tests unmodified when substituted for `MockAttestationProvider`
in a test double, and a reviewer who is not its author can read
`get_platform_evidence()` and confirm every field traces back to a real
measurement, not a literal or a placeholder.
