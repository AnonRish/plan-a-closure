# Trust composition checker

A formal check for one specific claim that AI-verification architectures keep making
without proof: *"the conclusion holds unless at least k of our n trust roots are
simultaneously compromised."* That's what the AI Security Forum's open-problem list
calls "composing trust roots" — proving a policy set actually enforces the
independence it claims, rather than quietly collapsing back to a single point of
failure.

## The problem, formally

A verification architecture names a set of trust roots `R = {r_1, ..., r_n}` —
mechanisms (a physical tap, a recomputation server, a human auditor, a cryptographic
ledger) that are supposed to fail *independently*. The implicit claim is a threshold:
compromising fewer than `k` of them shouldn't be able to break the verification's
conclusion.

That claim is only as good as the independence it assumes. Each trust root actually
relies on some set of underlying resources — a vendor's firmware, a shared crypto
library, a certificate authority, a personnel-vetting process. If a *single* resource
is depended on by `k` or more trust roots, then one compromise — not `k` independent
ones — defeats the threshold. The roots were never really independent; they just
looked that way until someone drew the dependency graph.

**The check:** build the bipartite graph of trust roots → resources. Find the
smallest set of resources whose combined compromise reaches `k` trust roots
(`min_attack(k)`). If that set is smaller than `k`, the independence claim is false,
and the gap tells you by how much.

This is a set-cover-shaped problem (NP-hard in general), solved here by brute force
over increasing subset sizes — fine at the scale that's relevant, since a real
architecture has single- to low-double-digit trust roots, not thousands.

## What this does not do

It finds violations *given* a dependency model. It cannot verify the model is
complete — a resource omitted from the graph is invisible to the checker, same as a
vulnerability nobody's found yet is invisible to a code audit. Building an accurate
dependency model for a real system is an organizational and technical audit, not a
formal exercise; this tool is what you'd point at the *output* of that audit, not a
substitute for doing it.

## Two case studies

**Arbiter** (real, from its actual source — see `case_studies.py`): 4 trust roots
(licensing, workload review, audit statistics, ledger integrity), claimed threshold
`k=4`. Finding: `client_js_integrity` — the deployed browser code itself — is a
dependency of all four. `min_attack(4) = 1`. This is the formal version of the
caveat already in Arbiter's own footer: everything currently runs in one
unattested browser tab, so there's no real independence between its four
mechanisms yet. A production hardening pass should be aimed specifically at
getting licensing, review, statistics, and the ledger onto genuinely separate
infrastructure — not just "more security" in the abstract.

**A reconstructed AI-2040-style architecture** (illustrative — built from the public
Verification Plan, SITREP, and RFD board discussed earlier; not Amodo's actual,
partly-undisclosed internal dependency graph): 5 trust roots — optical tap,
recomputation server, side-channel warden, human auditor, verification ledger —
claimed threshold `k=3`. Finding: a shared `crypto_library` dependency (used by the
recomputation server, the side-channel warden, and the ledger) reaches the threshold
alone. `min_attack(3) = 1`. Whether this holds for the *real* architecture depends
on facts this model doesn't have — does the actual system genuinely use one shared
cryptographic implementation across those three components, or independently
sourced/audited ones? That's exactly the kind of question a real answer to this
open problem has to resolve architecture-by-architecture; what this exercise shows
is that it's the right *kind* of question to be asking, and gives a precise way to
ask it once you have real answers to plug in.

## Running it

```
pip install networkx matplotlib pytest
python3 -m pytest test_trust_composition.py -v   # 9 tests
python3 case_studies.py                           # prints both reports, writes
                                                    # arbiter_graph.png, plan_a_graph.png,
                                                    # results.json
```

## Extending this

- **Weighted resources.** Right now every resource is equally hard to compromise.
  A real version would weight edges by estimated compromise difficulty and solve a
  weighted min-cost hitting set instead of unweighted `min_attack`.
- **The governance-schema problem** (the other tractable item from the same list)
  is a natural next step from here: once a dependency model produces a verdict,
  the receipt schema is what makes that verdict — and the audit trail behind it —
  something a treaty or dispute-resolution process can actually reference.
- **Feed it real data.** The single highest-value next step isn't more algorithm —
  it's someone who actually knows a real architecture's dependency graph running
  it through this and seeing what comes out.
