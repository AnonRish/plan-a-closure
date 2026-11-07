"""
verification.py

Two independent ways to catch under-reporting, with very different
scaling properties -- which is the actual point of building both instead
of picking one:

AGGREGATE CHECK -- compare the analytically declared_flops() total against
the sum of every node's REPORTED total. Cheap (no auditing needed), but a
single lying node's shortfall gets diluted by every honest node's correct
report as cluster size grows -- see run_evaluation.py for exactly how fast.

SPOT-CHECK AUDIT -- demand a random subset of nodes reveal their full
detailed log. Check (a) the log actually hashes to what was committed
earlier (catches swapping in a fabricated log after the fact) and (b) the
log's own sum matches what the node originally reported (catches a node
that committed an honest log but reported a dishonest summary -- exactly
the attack modeled in cluster.py). Detection probability here depends only
on the audit rate and number of rounds, NOT on cluster size.
"""

from dataclasses import dataclass
from .cluster import _log_hash


def aggregate_discrepancy(graph, reports, tolerance=0.02):
    declared = graph.declared_flops()
    reported_total = sum(r.reported_flops for r in reports)
    relative_gap = (declared - reported_total) / declared if declared else 0.0
    return {
        "declared_flops": declared,
        "reported_total": reported_total,
        "relative_gap": relative_gap,
        "flagged": abs(relative_gap) > tolerance,
    }


@dataclass
class AuditResult:
    node_id: str
    hash_consistent: bool
    summary_consistent: bool
    caught: bool  # true if EITHER check fails -- a lie was detected


def audit_node(report):
    """A real audit: recompute the hash from the revealed log, and check the
    revealed log's own sum against what was originally reported."""
    hash_consistent = _log_hash(report.detailed_log) == report.reported_log_hash
    true_sum = sum(f for _, f in report.detailed_log)
    summary_consistent = true_sum == report.reported_flops
    return AuditResult(
        node_id=report.node_id,
        hash_consistent=hash_consistent,
        summary_consistent=summary_consistent,
        caught=not (hash_consistent and summary_consistent),
    )


def spot_check_round(reports, audit_rate, rng):
    """Audit a random subset of nodes this round; return which Byzantine
    nodes were caught (and confirm no honest node is ever falsely caught --
    tested explicitly in test_compute_accounting.py)."""
    audited = [r for r in reports if rng.random() < audit_rate]
    results = [audit_node(r) for r in audited]
    caught_byzantine = [res.node_id for res, r in zip(results, audited) if res.caught and r.is_byzantine]
    false_positives = [res.node_id for res, r in zip(results, audited) if res.caught and not r.is_byzantine]
    return {
        "audited_count": len(audited),
        "caught_byzantine": caught_byzantine,
        "false_positives": false_positives,
    }


def detection_probability_over_rounds(byzantine_present, audit_rate, n_rounds):
    """A specific Byzantine node's chance of being audited at least once in
    n_rounds independent rounds, each with independent probability
    audit_rate -- plain geometric probability, exact, not simulated."""
    if not byzantine_present:
        return 0.0
    return 1 - (1 - audit_rate) ** n_rounds
