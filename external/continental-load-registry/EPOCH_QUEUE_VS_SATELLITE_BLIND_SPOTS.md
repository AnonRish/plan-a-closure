# Interconnection Queues vs. Satellite / Permit Mapping: Complementary Blind Spots

Updated: 2026-09-27

## Purpose

This note defines the specific empirical niche of the Continental Large-Load Interconnection & Telemetry Registry relative to Epoch AI's AI data-center mapping.

The point is not that one method replaces the other. The useful question is:

> **What does public interconnection-queue evidence reveal that satellite / permit mapping does not, what does satellite / permit mapping reveal that queues do not, and what becomes visible when the two are cross-referenced?**

## 1. Two different observation layers

### Interconnection / connection records

A queue or connection record is an **electrical-system observation**. Depending on the market, public records can expose some combination of requested capacity, project/request identity, point of interconnection, study status, dates, developer/applicant fields, and transmission or distribution relationships.

The key timing advantage is that an interconnection request can exist **before physical construction is visible**. That means a public electrical filing can sometimes reveal a large-load project while it is still an intent / study / planning object rather than a finished physical campus.

But the queue has a hard boundary: it only sees projects that enter the public connection process represented by that source. It can miss:

- new compute built on already-available capacity;
- behind-the-meter or privately supplied generation;
- projects using existing service arrangements without a new public request;
- facilities whose public records do not identify the customer clearly;
- projects that are cancelled, deferred, renamed, or otherwise remain ambiguous;
- jurisdictions where the relevant connection process is not publicly exposed at useful granularity.

A queue row therefore should not be treated as proof that a physical AI facility exists, is operating, or contains a particular amount of AI compute.

### Satellite imagery / permits / physical mapping

Satellite and permit evidence is a **physical-construction observation**. It can reveal land clearing, building shells, roof completion, substations, cooling equipment, turbines, batteries, roads, parking, construction sequencing and other visible infrastructure. Permit records can add building, mechanical, electrical and construction documentation.

The key advantage is that this layer can distinguish **physical realization** from a project that exists only as a paper request.

But physical mapping has a different blind spot: intent can exist before there is a visible structure. It also cannot directly establish every hidden relationship, such as the exact tenant, current hardware population, or whether an apparently complete building is actually running frontier training workloads.

## 2. The timing distinction

The most important complementary property is temporal:

**Queue / connection evidence**
→ project request / electrical intent
→ study / approval / service process
→ construction may follow later

**Satellite / permit evidence**
→ land / construction / equipment appears
→ commissioning
→ physical operation becomes observable

The intervals are project- and market-specific. An interconnection record can therefore provide an **earlier signal** than imagery for some projects, while imagery can provide a **later physical confirmation** of what the electrical record represented.

This is why neither layer should be collapsed into a single “facility found” field.

## 3. The overlap is more informative than either list alone

The registry currently preserves the complete September 2026 Epoch AI site snapshot as a separate evidence layer: **93 sites**, with **545 dated timeline observations** and **227 chip-quantity observations** in the preserved Epoch datasets.

The current registry also maintains a conservative connection crosswalk for all 93 Epoch sites. As of the current build:

- all 93 Epoch sites have a grid / connection-system jurisdiction;
- 2 have a site-specific public queue ID;
- the remainder retain either site-level evidence or a researched no-public-record disposition rather than an invented queue match.

That creates a useful four-way comparison:

| Relationship | Interpretation |
|---|---|
| Queue evidence + physical evidence | Public electrical intent and physical realization point to the same project/site; still requires careful identity matching. |
| Queue evidence without physical evidence | Could indicate an earlier-stage project, a delayed/cancelled project, a non-public physical realization, or an identity/geography problem. |
| Physical evidence without queue evidence | Could indicate existing-capacity expansion, a different connection pathway, private generation, insufficient public queue coverage, or unresolved identity. |
| Neither | **No public signal in these layers**, not evidence that no project or compute exists. |

The third and second categories are especially useful research targets because the discrepancy itself is informative.

## 4. Why the Epoch cross-reference is useful

Epoch AI describes its AI-data-center database as public research built from high-resolution satellite imagery, permits and public documents, with site timelines and estimates of IT power, compute and cost. Its September 24, 2026 update reports **93 sites** and **13.5 GW of IT power** across those sites.

The Continental registry's connection layer is a different observation stream: it starts from public electrical-system records and tries to resolve the project/entity/site relationship without assuming that queue MW and AI-data-center IT MW are the same thing.

The practical research question is therefore not “which map is correct?”

It is:

> **Where do the two methods agree, where do they disagree, and what does each disagreement tell us to investigate next?**

That is a substantially stronger research object than a second independent list of facilities.

## 5. Relation to Naci Cankaya's work

Cankaya's 2024 BlueDot project, *Are you secretly training AI?*, was explicitly a feasibility-oriented theoretical exploration of detecting large-scale AI training from physical signatures including power consumption, cooling requirements and computational hardware characteristics. The project description says participants worked on their projects for four weeks and emphasizes that the result was a theoretical exploration rather than empirical data.

The registry is a different kind of contribution: it applies one of those physical-signature ideas at scale to **nine real North American organized-market public interconnection/connection systems**, with entity resolution, preserved source records, dated captures, and an explicit ambiguous tier.

The strongest description is not “I solved covert-compute detection.”

It is:

> **You sketched a detection category from unavoidable physical signatures; I built a public-data implementation of the grid-interconnection slice of that idea at nine-market scale.**

Cankaya's subsequent 2026 work on datacenter network taps makes the comparison even more useful: his current work addresses evidence capture and network-level verification inside or around a datacenter, while this registry addresses the earlier and more external question of what the public electrical system says about prospective large compute facilities.

## 6. Relation to AI 2040 / Plan A

This registry should be treated as a **supporting observability layer**, not as the international verification regime itself.

Its strongest direct contribution is the Phase 1-style accounting question:

> **What large compute/load is publicly evidenced, and who is associated with it?**

It does not by itself provide bilateral U.S.–China coverage, treaty-grade inspection, hardware attestation, workload verification, or a method for discovering facilities intentionally designed to leave no public signal.

The defensible capability claim is:

> **raise the cost of hiding and map the ambiguous middle**

—not “find every secret facility.”

## 7. The two hard limits

### Geographic limit

The main interconnection registry is North American. It therefore cannot by itself perform the U.S.–China bilateral visibility that a mature international Track 3 verification system would require.

The preserved Epoch layer is global in its own separate 93-site dataset, but that does not turn the registry's North American public interconnection coverage into a global connection census.

### Disclosure limit

The registry is built from public evidence. A genuinely covert project would have an incentive to avoid public queue, permit, utility and other disclosure signals.

Therefore:

**absence of a public signal is an unresolved evidence state, not evidence of absence.**

This is why the registry preserves explicit states such as UNKNOWN, PENDING_RESEARCH, RESEARCHED_NO_PUBLIC_RECORD, SOURCE_AVAILABLE_NOT_INGESTED, and NOT_INGESTED.

## 8. The research question created by the combination

The highest-value future work is not simply “add more facilities.”

It is to systematically measure the **disagreement set** between electrical, physical, and other independent signals:

1. queue request appears first;
2. physical evidence appears later;
3. identity and capacity are reconciled;
4. divergences are retained as explicit research targets;
5. independent evidence is added where available;
6. unresolved cases remain unresolved rather than being silently promoted.

That produces a reproducible bridge from public infrastructure records toward future verification research without claiming that public observation alone is sufficient for treaty-grade assurance.

## Sources

- Epoch AI, [AI data centers](https://epoch.ai/data/ai-data-centers), updated September 24, 2026.
- Epoch AI, [AI data centers documentation — Records](https://epoch.ai/data/data-centers-documentation/records).
- Naci Cankaya, [Are you secretly training AI?](https://blog.bluedot.org/p/are-you-secretly-training-ai-methods-for-uncovering-covert-ai-training-a-framework-for-feasibility-and-future-research), December 17, 2024.
- Naci Cankaya, [Research Note: The Fundamentals and Feasibility of Secure Network Taps for Verifying AI Datacenter Use](https://nacicankaya.substack.com/p/research-note-the-fundamentals-and).
- AI 2040, [Get Involved in Verification](https://ai-2040.com/supplements/verification-plan/get-involved).
- Repository artifacts: `data/large_load_scope.json`, `data/external/epoch_ai/manifest.json`, `data/external/epoch_ai/queue_crosswalk.json`, `data/track3/summary.json`, and `data/track3/research_backlog_summary.json`.