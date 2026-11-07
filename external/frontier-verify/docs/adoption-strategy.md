# Adoption Strategy

## Reframing the goal

The source specification's adoption sections (9, 35, 44, 62, 81) describe
an end state where frontier labs, cloud providers, hardware vendors,
governments, and standards bodies all adopt compatible verification
evidence, and this repository becomes a leading reference implementation
within that ecosystem. That is a legitimate long-term goal for the *field*
of AI verification. It is not something a single-author, Phase 1,
pre-alpha repository can manufacture by writing better code. Organizational
trust, legal agreements, regulatory mandates, and industry consensus are
not engineering problems, and no amount of clean architecture substitutes
for them. Section 62 of the source spec makes exactly this point --
"stars are not the objective" -- and it's worth taking that at face value
rather than skipping straight to the parts of the spec that assume adoption
is already underway.

## What's actually real to build on

The one specific external claim in the source spec worth checking was in
section 31: a reference to a June 2026 initiative called Appia. That
checked out. <cite index="24-1">Google, Microsoft, OpenAI, Arm, Mastercard,
Siemens, and other companies have joined the Appia Foundation, hosted by
the Linux Foundation and launched in mid-2026, to create common
specifications and assessment frameworks organizations can use to
demonstrate AI systems meet emerging safety, trust, and compliance
requirements.</cite> <cite index="22-1">Appia aims to develop open, modular
specifications translating international standards into practical
assessment criteria across the AI value chain, building a trust layer
through which third parties check conformity.</cite>

That's a real, credible, well-backed effort already doing the
organizational work this project cannot do alone. The right relationship
is: design Frontier Verify's evidence and receipt formats so they *could*
feed into a trust layer like Appia's if and when it defines one relevant to
compute verification -- not to compete with it, and not to assume it will
adopt this specific repository. Concretely, that means keeping the evidence
schema (`schemas/evidence.schema.json`) and receipt schema
(`schemas/receipt.schema.json`) as clean, independent, machine-readable
artifacts that don't hard-depend on this repository's own API or storage
choices -- which Phase 1 already does, incidentally, since both schemas are
plain JSON Schema with no Frontier-Verify-specific extensions.

## A realistic staged path, not a checklist of world adoption

1. **Be genuinely useful as a reference implementation for people studying
   this problem.** Researchers, not labs, are the realistic first audience.
   A correct, honestly-labeled Phase 1 core that answers the adversarial
   questions in `threat-model.md` without flinching is worth more to that
   audience than a longer feature list with weaker honesty.
2. **Get technically literate feedback and survive it.** Section 43 of the
   source spec calls this red-teaming before strong claims; it applies
   before claiming any adoption momentum too, not just before claiming
   security.
3. **Publish the schemas as standalone artifacts early**, independent of
   whether anyone adopts the reference implementation itself -- a schema
   that outlives this specific codebase is a more realistic adoption
   vector than the codebase is.
4. **Track efforts like Appia as they mature**, and revisit whether mapping
   Frontier Verify's assurance levels (`assurance-model.md`) onto an
   external framework is possible -- not before such a framework exists in
   enough detail to map to honestly.
5. **Treat "labs and governments adopt this" as a multi-year, contingent
   aspiration**, not a Phase 1-11 execution checklist outcome. It depends on
   factors (regulatory mandates, industry consensus, litigation exposure,
   insurance markets) that no amount of good engineering directly controls.

## What this document deliberately does not do

It does not promise pilot programs, does not name prospective adopters,
and does not project timelines for external validation. Those would be
exactly the kind of claims section 4 of the source spec prohibits: stating
functionality -- in this case, *organizational* functionality -- that
doesn't exist yet.

## Adoption barriers, analyzed against what actually exists (Phase 2)

A frontier AI company evaluating this repository today faces these
concrete barriers, each checked against what's real rather than assumed:

| Barrier | Real severity today | Why |
|---|---|---|
| Engineering effort | Low for `audit-only` mode | The generic Python wrapper (`examples/integration/generic_python_service/`) requires zero changes to an existing inference function; vLLM/Triton integration is real design work, not yet a drop-in adapter (`docs/integrations/`) |
| Latency overhead | Unknown for real inference; near-zero for the verification layer itself | Ed25519 signing/verification is sub-millisecond (`docs/performance.md`); real inference overhead is UNMEASURED, no GPU available to measure it |
| GPU overhead | Unknown | Same reason -- honestly unmeasured, not claimed zero |
| Network overhead | Unknown for real deployments | The asynchronous-submission design (`AsyncEvidenceSubmitter`) specifically exists so network overhead can't leak into the inference hot path even before it's measured -- see `docs/performance.md` |
| Privacy / model IP exposure | Low, by design | The evidence schema uses digests and structured metadata, never raw weights or raw prompts (`docs/evidence-model.md`) -- this was a Phase 1 design decision, unchanged |
| Operational complexity | Real, and currently underserved | No Kubernetes deployment, no managed hosting story exists yet (`docs/protocol-roadmap.md`, Phase 5) |
| False positives | Not directly applicable yet | Nothing in this system currently BLOCKS real traffic (`audit-only` only) -- see `docs/integrations/vllm.md`, "Modes" |
| Reliability | The verifier itself is a single process with no HA story | No load balancing, no failover, no persistence guarantee beyond `FV_DATA_DIR` being set correctly -- real gaps, not addressed this phase |
| Compliance | Genuinely useful signal, not a compliance answer | See `docs/ecosystem-interoperability.md` -- this system is evidence that could feed a compliance program (NIST AI RMF, ISO 42001), not a substitute for one |
| Trust in the verifier itself | The biggest unresolved barrier | A company adopting this has to trust either its OWN verifier deployment (in which case "independent" verification is self-verification) or a genuinely separate operator it doesn't yet have a reason to trust -- see `docs/trust-boundaries.md` |
| Interoperability | Early but real | RATS-aligned architecture (`docs/ecosystem-interoperability.md`), a standalone verifier proving receipts are checkable without this codebase (`tools/standalone-verifier/`) |
| Vendor lock-in | Low, by design | `AttestationProvider` is vendor-neutral (`docs/architecture.md`); the one hardware backend attempted (NVIDIA) is isolated behind that interface |

## What this means for the "reduce barriers" design goal

The barriers with the clearest path to reduction are engineering effort
(generic wrapper already achieves this) and vendor lock-in (already
achieved by the interface design). The barriers that are NOT close to
reduced -- trust in the verifier, operational reliability, real-world
performance overhead -- are the ones worth being honest about rather than
designing marketing copy around. A frontier lab reading this table should
come away knowing exactly which barriers this project has actually lowered
and which ones remain exactly as high as they were before this repository
existed.
