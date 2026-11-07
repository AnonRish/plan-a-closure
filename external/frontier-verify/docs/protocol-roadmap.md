# Protocol Roadmap

Phase numbering matches the source specification's sections 64-75. This
document was substantially rewritten for Phase 2 -- the status of several
phases genuinely changed, not just accumulated additions.

## Done

**Phase 0 -- Discovery.** Environment inspected each phase (no
GPU/CUDA/Docker, confirmed via `bash`, not assumed). Current-state
research re-done for Phase 2 rather than trusted from Phase 1 -- and it
found Phase 1's own ADR-0001 conclusion about NVAT's stability was already
stale two months later (`docs/hardware/nvidia-attestation.md`). All Phase
0 docs written and, for Phase 2, substantially expanded.

**Phase 1 -- Core verification fabric.** Evidence schema, canonical
encoding, model/runtime identity, signed receipts, policy objects,
verification engine, REST API, CLI, Python SDK, tests, working local demo.
Unchanged in substance this phase, though several of its files (API,
store, receipt verification) were extended, not rewritten, in Phase 2.

**Phase 2 -- Hardware attestation: PARTIAL, honestly scoped.** Real
GPU attestation remains NOT_IMPLEMENTED -- still no GPU available.
What IS real: `NvidiaAttestationProvider.parse_nvat_evidence()` parses
NVAT's actual documented evidence JSON shape into the portable
`HardwareEvidence` schema, tested against a clearly-labeled synthetic
fixture (`tests/conformance/test_nvidia_evidence_parsing.py`). This is a
narrower claim than "Phase 2 is done" -- see
`docs/hardware/nvidia-attestation.md` and
`docs/attestation-conformance.md` for exactly where the line sits.

**Security/interoperability infrastructure the brief asked for ahead of
schedule, because Phase 1's own report flagged them as urgent**: real
API-key authentication (`docs/protocol/auth-model.md`), a real
`KeyProvider` with rotation and key-id-based lookup so old receipts stay
verifiable (`docs/protocol/key-management.md`), content-addressed evidence
storage with integrity checking (`frontier_verify/storage/`),
evidence-id-collision rejection, and a standalone, dependency-minimal
receipt verifier proven (not just claimed) to agree with the reference
implementation (`tools/standalone-verifier/`,
`tests/conformance/test_standalone_verifier_agrees.py`).

**Phase 9 -- Protocol/conformance: PARTIAL.** A real conformance test
suite exists (`tests/conformance/`, 20+ tests) covering schema
compatibility, unknown-field forward-compatibility, content-addressed
storage integrity, NVIDIA evidence parsing, recomputation sampling, and
cross-implementation receipt verification. No formal test-vector export
format yet, and no SECOND full verifier implementation (the standalone
verifier proves receipt-checking specifically, not the whole pipeline).

## Explicitly not started, or only mapped rather than built

- **Phase 3 -- Inference integration.** vLLM's `stat_logger_plugins` and
  Triton's OpenTelemetry trace export identified as the least-invasive
  real integration points via fresh research (`docs/integrations/`), with
  illustrative adapter code -- neither tested against a live install (no
  GPU, heavy dependencies). The ONE integration example that IS real and
  tested: `examples/integration/generic_python_service/`, a plain-Python
  async wrapper with 5 passing tests including a concrete latency-isolation
  proof.
- **Phase 4 -- Independent verification.** A second FULL verifier
  implementation (not just receipt-checking) still doesn't exist.
- **Phase 5 -- Kubernetes.** Still not attempted -- no cluster to validate
  manifests against.
- **Phase 6 -- AI-2040 recomputation.** Real recomputation of actual
  inference remains NOT_IMPLEMENTED and genuinely open research. What
  moved: sampling UNPREDICTABILITY is now real, tested, and adversarially
  demonstrated (`docs/research/recomputation.md`,
  `frontier_verify/recomputation/`) -- a first, honestly-bounded piece of
  a much larger unsolved problem. The API endpoints remain `501`.
- **Phase 7 -- Network/physical verification foundation.** Still no code
  -- `docs/network-evidence-protocol.md` (new this phase) defines the
  abstraction in writing, explicitly without a Python class or schema, for
  the same reason ADR-0001 gave in Phase 1: a stub with zero real capacity
  behind it would overstate progress.
- **Phase 8 -- Adversarial research.** Substantially expanded --
  `docs/adversarial-results.md` scores all 15 attacks the Phase 2 brief
  named, with real tests behind every "detected" claim. Most attacks
  remain undetected, honestly, because they require infrastructure
  (Phase 2 hardware, Phase 6 recomputation, Phase 7 network evidence) that
  doesn't exist yet -- see that document's own "patterns worth naming"
  section.
- **Phase 10 -- Ecosystem/pilots.** No pilot package. `docs/ecosystem-interoperability.md`
  (new this phase) maps Frontier Verify onto IETF RATS (RFC 9334) --
  confirmed to be exactly the vocabulary NVIDIA's own tooling already
  uses -- and explicitly distinguishes this project's actual niche from
  NIST AI RMF / ISO 42001, which operate one layer up.
- **Phase 11 -- Production hardening.** Not applicable.

## Immediate next steps, in order, revised for what's now true

1. **Real hardware attestation** is still the highest-value blocked item,
   now specifically scoped: target NVAT/`nvattest` (confirmed stabilized
   to 1.2.0, not the expiring Python SDK), and re-verify this finding
   again before starting, since it will be stale by then too.
2. **Authorization**, not just authentication -- every API key can
   currently do everything every other key can do. See
   `docs/protocol/auth-model.md`'s explicit gap statement.
3. **A real Triton OpenTelemetry adapter** -- unlike vLLM/GPU work, this
   is buildable without hardware (an OTel collector and Triton's trace
   format can be tested without live inference) and wasn't reached this
   phase.
4. **Key revocation**, distinct from rotation -- `docs/protocol/key-management.md`
   flags this as a real, currently-unaddressed gap now that rotation
   itself works.
