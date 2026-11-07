"""
cluster.py

Simulates RFD 024's distributed FLOP counting: the declared graph's ops are
partitioned across N nodes. Each node "executes" its assigned ops (here,
that just means it knows the true FLOPs for them) and reports a count --
honestly, or, for a configurable fraction of Byzantine nodes, under-
reported by some fraction to hide real usage while looking compliant.

Each node's report comes with a hash commitment to its own per-op log --
same primitive as the registry/licensing pieces earlier in this set
(SHA-256), applied here to FLOP accounting instead of audit decisions or
license tokens. The commitment doesn't stop a node from lying about the
SUMMARY number; what it does is make a lie inconsistent with the detailed
log the node is separately on the hook for -- which is what
verification.py's spot-check catches: a node that fakes its total but
commits to (and is later asked to reveal) an honest detailed log gets
caught the moment anyone checks the two against each other.
"""

import hashlib
import json
from dataclasses import dataclass


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


@dataclass
class NodeReport:
    node_id: str
    true_flops: int
    reported_flops: int
    is_byzantine: bool
    detailed_log: list          # [(op_name, true_op_flops), ...] -- the honest record
    reported_log_hash: str      # commitment to that log


def partition_ops(graph, n_nodes, rng):
    """Round-robin assignment over a shuffled op list -- simple, and gives
    nodes uneven-but-comparable shares, which is realistic enough for
    testing the accounting layer without modeling a real scheduler."""
    ops = list(graph.ops)
    rng.shuffle(ops)
    assignment = {i: [] for i in range(n_nodes)}
    for idx, op in enumerate(ops):
        assignment[idx % n_nodes].append(op)
    return assignment


def _log_hash(detailed_log):
    payload = json.dumps(detailed_log, sort_keys=True)
    return sha256_hex(payload)


def run_cluster(graph, n_nodes, byzantine_fraction, underreport_fraction, rng, force_byzantine_ids=None):
    """Returns list[NodeReport]. A Byzantine node under-reports its SUMMARY
    total by underreport_fraction. Its committed detailed log stays honest
    in this model -- faking the log consistently with a false summary is a
    strictly harder attack (it means fabricating per-op numbers that still
    need to look plausible against known FLOP formulas for declared op
    shapes), and is exactly what a spot-check audit is positioned to catch;
    see verification.py, and README for the honest limits of that claim.

    force_byzantine_ids: if given, use this exact set of node indices as
    Byzantine instead of sampling each node independently at
    byzantine_fraction. Needed for any experiment that wants to hold the
    ABSOLUTE NUMBER of Byzantine nodes fixed while varying N -- with
    independent per-node sampling, byzantine_fraction=1/N only gives 1
    Byzantine node IN EXPECTATION, not for any specific realized run, and a
    single fixed seed can (and here, initially did) realize zero."""
    assignment = partition_ops(graph, n_nodes, rng)
    if force_byzantine_ids is not None:
        byzantine_ids = set(force_byzantine_ids)
    else:
        byzantine_ids = set(i for i in range(n_nodes) if rng.random() < byzantine_fraction)
    reports = []
    for node_id, ops in assignment.items():
        detailed_log = [(op.name, op.flops()) for op in ops]
        true_total = sum(f for _, f in detailed_log)
        is_byz = node_id in byzantine_ids
        reported_total = int(true_total * (1 - underreport_fraction)) if is_byz else true_total
        reports.append(NodeReport(
            node_id=f"node-{node_id}",
            true_flops=true_total,
            reported_flops=reported_total,
            is_byzantine=is_byz,
            detailed_log=detailed_log,
            reported_log_hash=_log_hash(detailed_log),
        ))
    return reports
