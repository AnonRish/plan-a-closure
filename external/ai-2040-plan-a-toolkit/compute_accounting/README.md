# Compute-graph declaration + distributed FLOP accounting

RFD 023 (Compute Graph Declaration Protocol) and RFD 024 (Distributed FLOP
Counting) from the AI Security Forum board, built together because they're
naturally one system: a declaration gives an exact analytical FLOP count to
check distributed, possibly-dishonest execution against.

## The declaration half: exact, not estimated

Standard ML-systems FLOP formulas (2 FLOPs per multiply-accumulate) for matmul,
linear, attention, and conv2d layers. Sanity-checked against the field's own
rule of thumb, not just internally consistent: a GPT-2-small-shaped declared
graph (12 layers, d_model=768, seq_len=1024) comes out to 2.126×10¹¹ FLOPs;
the standard "2 × params × tokens" scaling-law estimate gives 2.54×10¹¹ —
same order of magnitude, consistent with the difference being embeddings and
norms this simplified graph doesn't declare. `test_transformer_graph_matches_known_scaling_rule_of_thumb`
checks this stays true, not just that the number is positive.

## The counting half: two mechanisms, deliberately different in kind

Full Byzantine-fault-tolerant consensus is its own deep field; building it from
scratch here would be the same mistake as pretending to solve ZKP-at-scale
earlier in this set. What's honestly buildable is grounded in the same
declare-commit-spot-check pattern the registry piece already established:
each node commits (SHA-256) to a detailed per-op log, and:

**Aggregate check** — compare declared_flops() against the sum of every node's
reported total. Free, no auditing needed.

**Spot-check audit** — demand a random subset of nodes reveal their full log,
check it hashes to the earlier commitment AND its own sum matches what was
originally reported. A node that committed an honest log (as modeled here) but
reported a dishonest summary gets caught the instant anyone checks the two
numbers against each other.

## The real finding: these two scale in opposite directions

Fixed: exactly one Byzantine node, under-reporting 30% of its true work.

| Cluster size | Aggregate relative gap | Flagged at 2% tolerance? |
|---|---|---|
| 4 | 7.77% | Yes |
| 16 | 2.59% | Yes |
| 64 | 1.07% | **No** |
| 256 | 0.36% | **No** |
| 1024 | 0.36% | **No** |

One lying node's shortfall gets diluted by every honest node's correct report.
Past roughly 20-30 nodes in this configuration, the aggregate check goes blind
— not because the lie got smaller, but because the cluster got bigger.

Spot-check detection probability doesn't care about cluster size at all — it's
exact geometric probability, `1-(1-audit_rate)^rounds`: 5% audits for 10 rounds
catches a given lying node 40.1% of the time; 10% audits for 20 rounds, 87.8%.
Confirmed empirically too, not just computed: across 30 rounds of 10% audits
against a 200-node cluster with 10 real Byzantine nodes, 608 total audits
performed, 28 Byzantine-catches, **zero false positives** on honest nodes —
the mechanism never cries wolf.

**The conclusion these two numbers force**: aggregate accounting is necessary
but not sufficient, and gets *less* sufficient exactly as clusters get bigger
— which is the direction real frontier training runs are actually moving.
Spot-checking has to be a standing part of the protocol, not a fallback for
when the aggregate check trips.

## A real bug this caught in its own design

First version of the cluster-size experiment set `byzantine_fraction = 1/N` per
node, expecting "exactly 1 Byzantine node." That's only true in expectation —
for a single seeded run at N=256 or N=1024, the independent per-node draws
realized **zero** Byzantine nodes, not one, silently invalidating the entire
comparison (every large-N row showed 0% gap for the wrong reason). Fixed by
adding `force_byzantine_ids` for exact, deterministic control, with a
regression test (`test_force_byzantine_ids_gives_exact_count_regardless_of_cluster_size`)
that would have caught this immediately. The corrected numbers above are from
that fix — the dilution trend is real, not an artifact of unluckily-drawn zeros.

## Running it

```
pip install numpy matplotlib pytest
python3 run_evaluation.py                        # all numbers above + detection_comparison.png
python3 -m pytest test_compute_accounting.py -v  # 16 tests
```

## What this does not do

The Byzantine node's detailed log stays honest in this model even while its
summary lies — a real attacker could try to fabricate a consistent fake log
too, which is a strictly harder attack this doesn't model or defend against
(a log claiming ops with dimensions that don't match the actual declared
graph, or that don't reflect real hardware-level counters, would need a
different check — hardware-rooted attestation, which is RFD 019/035 territory
and needs real hardware, same limitation as everywhere else in this set that
touches physical trust roots). No real cluster, no real network communication
patterns, no real training run — op partitioning is a simple round-robin, not
a realistic scheduler.
