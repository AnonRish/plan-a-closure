"""
trust_composition.py

A checker for a specific, narrow question that AI-verification architectures
keep asserting without proof: "the conclusion holds unless at least k of our
n trust roots are simultaneously compromised."

That's an independence claim. It's true only if there's no small set of
*shared* resources -- a vendor, a library, a certificate authority, a vetting
process -- whose compromise would take out k of the roots at once. If such a
set exists and is smaller than k, the roots aren't actually independent, and
the architecture's real fault tolerance is weaker than advertised.

This module answers one question precisely: given a stated dependency model,
what is the smallest set of resources whose compromise defeats a claimed
threshold? It does NOT verify that the stated dependency model is complete or
accurate -- that's a separate, harder, non-formal problem. See README.md,
"What this does not do."
"""

from dataclasses import dataclass, field
from itertools import combinations


@dataclass(frozen=True)
class TrustRoot:
    """One claimed-independent mechanism in a verification architecture."""
    name: str
    depends_on: frozenset  # names of atomic resources this root's integrity relies on

    def __init__(self, name, depends_on):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "depends_on", frozenset(depends_on))


def universe_of(trust_roots):
    """All distinct resources referenced by any trust root."""
    u = set()
    for tr in trust_roots:
        u |= tr.depends_on
    return sorted(u)


def resource_fanout(trust_roots):
    """resource -> how many trust roots depend on it."""
    u = universe_of(trust_roots)
    return {r: sum(1 for tr in trust_roots if r in tr.depends_on) for r in u}


def min_attack(trust_roots, threshold, max_search=None):
    """
    Smallest set of resources whose simultaneous compromise compromises
    >= threshold trust roots.

    Returns (size, resource_set). Returns (None, None) if no such set exists
    within max_search (which defaults to `threshold`; a set of size
    `threshold` -- one resource from each of `threshold` distinct roots --
    is always sufficient when threshold <= len(trust_roots), so the search
    never needs to go further than that to find *an* answer).

    Brute force over increasing subset size. This is set-cover-shaped and
    NP-hard in general, but real verification architectures have single-digit
    to low-double-digit trust roots and dependencies -- brute force at that
    scale is instant. This is a research tool for auditing a design on paper,
    not a component meant to run on architectures with thousands of parts.
    """
    n = len(trust_roots)
    if n == 0 or threshold <= 0:
        return None, None
    if max_search is None:
        max_search = min(threshold, n)

    u = universe_of(trust_roots)
    for size in range(1, max_search + 1):
        for combo in combinations(u, size):
            combo_set = set(combo)
            hit = sum(1 for tr in trust_roots if tr.depends_on & combo_set)
            if hit >= threshold:
                return size, combo_set
    return None, None


def analyze(trust_roots, claimed_threshold, label=""):
    """Run the check and print a human-readable report. Returns the raw result dict."""
    n = len(trust_roots)
    fanout = resource_fanout(trust_roots)
    size, hazard_set = min_attack(trust_roots, claimed_threshold)

    lines = []
    lines.append(f"\n=== {label} ===")
    lines.append(
        f"{n} trust roots, claimed threshold k={claimed_threshold} "
        f'("secure unless >= {claimed_threshold} of {n} are independently compromised")'
    )
    lines.append("Resource fan-out (how many trust roots each resource touches):")
    for r, count in sorted(fanout.items(), key=lambda x: -x[1]):
        flag = "  <-- reaches the claimed threshold alone" if count >= claimed_threshold else ""
        lines.append(f"  {r:36s} {count}{flag}")

    if size is not None and size < claimed_threshold:
        lines.append(
            f"\nVIOLATION: compromising {size} resource(s) -- {sorted(hazard_set)} -- "
            f"takes out >= {claimed_threshold} of {n} trust roots."
        )
        lines.append(
            f"The real number of independent things an adversary must break is {size}, "
            f"not the claimed {claimed_threshold}."
        )
        verdict = "violation"
    elif size == claimed_threshold:
        lines.append(
            f"\nHOLDS: the smallest resource set reaching the threshold has size {size}, "
            f"matching the claim exactly -- no shortcut through a shared dependency."
        )
        verdict = "holds"
    else:
        lines.append(
            f"\nHOLDS (vacuously or with margin): no shared-resource shortcut found "
            f"reaching the threshold in fewer than {claimed_threshold} compromises."
        )
        verdict = "holds"

    report = "\n".join(lines)
    print(report)
    return {
        "label": label, "n": n, "k": claimed_threshold, "fanout": fanout,
        "min_attack_size": size, "min_attack_set": hazard_set,
        "verdict": verdict, "report": report,
    }
