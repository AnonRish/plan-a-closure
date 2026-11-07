# Frontier Verify

**Status: Phase 4 -- experimental, pre-alpha.** Real, tested, running
code for tamper-evident record-keeping of self-reported AI compute
evidence, now with a tested multi-verifier quorum experiment, a real
(if tiny) numerical recomputation kernel, empirically-verified
reproducible builds, and audit-logged administrative actions. **Still
NOT independently reviewed by anyone who didn't write it, still NOT
tested against real hardware of any kind** -- see
[`docs/reviews/external-review.md`](docs/reviews/external-review.md) and
[`docs/hardware/nvidia-validation-report.md`](docs/hardware/nvidia-validation-report.md),
both honestly unexecuted. Read
[`docs/threat-model.md`](docs/threat-model.md) and
[`docs/adversarial-results.md`](docs/adversarial-results.md) before
trusting this for anything beyond local development.

## What this is

An open-source reference implementation working toward independent
verification of frontier AI computation and inference, in the spirit of
the AI-2040 verification agenda, architecturally aligned with IETF RATS
(RFC 9334) -- see [`docs/ecosystem-interoperability.md`](docs/ecosystem-interoperability.md).

See [`docs/ai2040-coverage-matrix.md`](docs/ai2040-coverage-matrix.md) for
a workstream-by-workstream honest status against the full AI-2040 agenda
-- most of it is still `NOT_IMPLEMENTED`, and that table says so plainly.

## Quickstart

```bash
git clone <this-repo> && cd frontier-verify
python3 -m pip install -e ".[dev,triton,recomputation-research]"

# run the full test suite (131 tests + 4 hardware tests that skip
# cleanly without a GPU: unit, security, adversarial, integration,
# conformance)
pytest

# run the local demo (mock attestation -> evidence -> verify -> signed
# receipt -> independent offline verification -> tamper check -> key
# rotation -> old receipt still verifiable)
python3 examples/local-demo/run_demo.py

# verify a receipt with NO dependency on this package at all
python3 tools/standalone-verifier/verify_receipt.py receipt.json <public_key_hex>
node tools/standalone-verifier/verify_receipt.js receipt.json <public_key_hex>  # genuine second-language implementation

# or drive the real server + CLI end to end
export FV_API_KEYS=dev-key:PROVER|POLICY_AUTHORITY|ADMINISTRATOR|AUDITOR
fv init
fv doctor
fv attest --out attestation.json
fv evidence build --model-digest sha256:... --attestation-file attestation.json --out evidence.json
uvicorn frontier_verify.api.main:app --reload &
# ... POST evidence.json + a policy to /v1/evidence and /v1/policies/validate\n# (with header X-Api-Key: dev-key), POST to /v1/inferences/verify, then:\n# Experimental Track 2: /v1/recomputation/v2/challenges -> submissions -> check
fv receipt verify receipt.json --public-key-hex <from GET /v1/verifier/public-key>
```

There is no `docker compose` demo. It was deliberately not built: this
repo's own development environment has no Docker, and a compose file no
one has run is worse than no compose file.

## Documentation

| Doc | What it covers |
|---|---|
| [`architecture.md`](docs/architecture.md) | Actors, data flow, component map |
| [`threat-model.md`](docs/threat-model.md) | The adversarial questions, answered honestly |
| [`trust-model.md`](docs/trust-model.md) | Role separation (Prover/Policy Authority/Administrator/Auditor) |
| [`research/verifier-trust.md`](docs/research/verifier-trust.md) | 11 proposed trust mitigations, evaluated honestly; quorum's real limit |
| [`ai2040-gap-analysis-phase4.md`](docs/ai2040-gap-analysis-phase4.md) | GREEN/YELLOW/RED rollup -- 0/6/19, explained |
| [`reviews/external-review.md`](docs/reviews/external-review.md) | No independent review obtained -- readiness package + labeled self-critique |
| [`research/reproducible-builds.md`](docs/research/reproducible-builds.md) | Empirically measured: not reproducible by default, fixed and confirmed |
| [`trust-boundaries.md`](docs/trust-boundaries.md) | Who controls what, in table form |
| [`adversarial-results.md`](docs/adversarial-results.md) | All 15 + 8 named attacks, scored against real tests |
| [`security-review-phase3.md`](docs/security-review-phase3.md) | Dedicated security pass -- 2 real findings, both fixed |
| [`assurance-model.md`](docs/assurance-model.md) | The L0-L5 ladder and why this still caps at L1 |
| [`evidence-model.md`](docs/evidence-model.md) | Schema and canonicalization details |
| [`receipt-specification.md`](docs/receipt-specification.md) | Signing, independent verification |
| [`api-design.md`](docs/api-design.md) | Endpoint-by-endpoint status, incl. per-endpoint role requirements |
| [`attestation-conformance.md`](docs/attestation-conformance.md) | What a hardware provider must supply |
| [`ai2040-coverage-matrix.md`](docs/ai2040-coverage-matrix.md) | All 25 AI-2040 workstreams, honestly scored |
| [`ecosystem-interoperability.md`](docs/ecosystem-interoperability.md) | RATS, NIST AI RMF, ISO 42001 |
| [`standards/appia-mapping.md`](docs/standards/appia-mapping.md) | Appia Foundation -- SUPPORTED/MAPPABLE/NOT_YET_MAPPED |
| [`adoption-strategy.md`](docs/adoption-strategy.md) | Realistic adoption path + a real barrier analysis |
| [`protocol-roadmap.md`](docs/protocol-roadmap.md) | What's done, deferred, and next |
| [`performance.md`](docs/performance.md) | Real measured numbers; hardware-dependent ones explicitly unmeasured |
| [`hardware/nvat-integration.md`](docs/hardware/nvat-integration.md) | Fresh NVAT research, incl. a real schema discrepancy found this phase |
| [`hardware/nvidia-attestation.md`](docs/hardware/nvidia-attestation.md) | Phase 2's research -- superseded, kept for the research trail |
| [`hardware/nvidia-real-test.md`](docs/hardware/nvidia-real-test.md) | Exact steps for someone with real GPU access |
| [`hardware/ci-design.md`](docs/hardware/ci-design.md) | Real-hardware CI design, marked NOT VERIFIED |
| [`hardware-provider-guide.md`](docs/hardware-provider-guide.md) | How to implement a real `AttestationProvider` |
| [`protocol/key-management.md`](docs/protocol/key-management.md) | Rotation vs. revocation, why lookup-by-id matters |
| [`protocol/auth-model.md`](docs/protocol/auth-model.md) | Roles, and what per-resource authorization would still need |
| [`protocol/independent-verification.md`](docs/protocol/independent-verification.md) | Honest common-mode-risk analysis of the 3-way verifier cross-check |
| [`integrations/`](docs/integrations/) | vLLM (research) and Triton (real OTel adapter, tested against real spans) |
| [`research/`](docs/research/) | Recomputation (+ staged roadmap), compute accounting, hidden computation |
| [`network-evidence-protocol.md`](docs/network-evidence-protocol.md) | The abstraction, deliberately without code -- see why inside |
| [`adr/`](docs/adr/) | Where and why this diverges from the original AI-2040 mechanisms |

## Tools

- [`tools/standalone-verifier/`](tools/standalone-verifier/) -- a single
  file that verifies a receipt with no dependency on this package,
  cross-checked against the reference implementation on every test run.
- [`examples/integration/generic_python_service/`](examples/integration/generic_python_service/) --
  a real, tested async evidence-submission wrapper for any Python
  inference function.

## License

Apache License 2.0 -- see [`LICENSE`](LICENSE).

## Contributing / Security

See [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`SECURITY.md`](SECURITY.md).
