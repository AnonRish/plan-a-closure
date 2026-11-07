# Track 3 completion gate

Updated: 2026-09-28

## Closed at the repository engineering layer

The public repository now has:

- 93 canonical Epoch reference sites.
- 1,395 / 1,395 defined site × domain cells in terminal evidence-accounting states.
- A successful latest Track 3 automated pipeline.
- Successful latest public-interface validation.
- Zero failed source adapters in the latest adapter run.
- 454 retained public-web evidence records.
- 631 retained derived remote-sensing observations across 92 reference sites.
- 2 defensible site-specific queue IDs.
- Grid state: 88 sites with site-level evidence, 3 documented researched-no-public-record outcomes, and 2 verified site-specific queue IDs.
- 214 effective publisher-field research tasks remain, plus 24 separate observation-acquisition tasks (18 cooling, 6 power telemetry).
- Explicit provenance, entity-resolution, research-backlog, physical-observation, claim-level, API, and validation artifacts.

## What the repository does not claim

The engineering closure above is not a claim that secret compute has been shown absent.

The unresolved items that cannot be fabricated or completed solely from public web data are:

1. Globally complete transaction-level production, sales, resale and transfer accounting.
2. Authorized physical inspection and chain-of-custody evidence.
3. Global serial-number continuity.
4. Independently verified decommissioning/recycling.
5. A closed statistical sampling population and realized audit outcomes.
6. Intelligence capable of discovering deliberately concealed facilities outside public-data visibility.
7. Independent verification governance, access, disputes and enforcement.

## Engineering-closure handoff artifacts

The repository now has explicit machine-readable contracts for the remaining external capabilities:

- `data/track3/external_capability_handoff_2026-09-28.json` — external evidence acceptance contracts.
- `data/track3/interval_power_telemetry_protocol.json` — interval-meter intake boundary; no site-level telemetry is fabricated.
- `data/track3/physical_target_leads.json` — lead-only treatment of the unresolved OpenAI Stargate UAE physical target.
- `build_track3_engineering_closure.py` — reproducible engineering-closure builder.
- `data/track3/engineering_closure_2026-09-28.json` — machine-readable zero-untracked-gap register.
- `validate_track3_release.py` — release-consistency validator.

These artifacts close the software/data contract for what the public repository can define and validate; they do not manufacture the missing external evidence.

## One explicit site-level physical boundary

OpenAI Stargate UAE remains the one canonical Epoch reference site without a defensible site-specific public physical target in the retained registry evidence. The registry does not fabricate a parcel coordinate. Its physical-observation modalities therefore remain an explicit source-available/unresolved-target state rather than a false observation.

## Operational semantics

A publisher health-check failure is not automatically an ingestion failure. The control plane now distinguishes a hard source failure from a degraded live health check when a retained repository snapshot exists or the publisher endpoint is blocked, rate-limited, redirected or otherwise unavailable. This prevents transient web-access conditions from masquerading as missing research data.

## Release wording

Describe this project as **Track 3 research infrastructure / public-evidence accounting**, not as a completed international verification system. That distinction is part of the audit trail.

The machine-readable gate is `data/track3/completion_gate.json`; the engineering-closure register is `data/track3/engineering_closure_2026-09-28.json`. The latest committed public-evidence snapshot is 93 sites, 631 derived remote-sensing observations across 92 sites, 454 public-web evidence records, and 1,395/1,395 terminal site-domain cells.
