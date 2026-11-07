#!/usr/bin/env python3
"""Track 3 sampled-tail trace and account reconciliation model.

Implements the small-owner tail logic described in the AI 2040 covert-compute
verification scenario. It is a research model and requires a genuinely closed
sampling frame plus authoritative source records before any field certificate.
"""
from __future__ import annotations
import argparse, hashlib, json, random
from bisect import bisect_right
from dataclasses import dataclass
from itertools import accumulate
from pathlib import Path

from track3_certificate import one_sided_failure_upper_bound

@dataclass(frozen=True)
class TailRecipient:
    owner_id: str
    delivered_units: int

@dataclass(frozen=True)
class OwnerAccount:
    owner_id: str
    current_holdings: int
    onward_sales: int
    documented_attrition: int
    independent_records_complete: bool

    def reconciles(self, received: int) -> bool:
        return (
            self.independent_records_complete
            and received == self.current_holdings + self.onward_sales + self.documented_attrition
        )

@dataclass(frozen=True)
class TraceOutcome:
    owner_id: str
    result: str
    reason: str

def seed_from_text(seed: str) -> int:
    return int(hashlib.sha256(seed.encode()).hexdigest()[:16], 16)

def sample_tail(recipient: TailRecipient, sample_size: int, seed: str) -> list[int]:
    if recipient.delivered_units <= 0:
        raise ValueError("delivered_units must be positive")
    if not 0 < sample_size <= recipient.delivered_units:
        raise ValueError("invalid sample_size")
    rng = random.Random(seed_from_text(seed))
    return rng.sample(range(recipient.delivered_units), sample_size)

def audit_recipient(recipient: TailRecipient, account: OwnerAccount, offset: int = 0) -> TraceOutcome:
    """Resolve one sampled unit at a recipient.

    ``offset`` is the sampled unit's position among the ``delivered_units`` the
    recipient received. Those units are split in order into held, sold-onward and
    attrition units, so a sample ends at physical inventory with probability
    holdings/received, follows an onward sale with probability onward/received,
    and lands in an attrition claim otherwise. The default ``offset=0`` keeps the
    old first-unit behaviour for direct callers.
    """
    if not account.reconciles(recipient.delivered_units):
        return TraceOutcome(recipient.owner_id, "FAIL", "account does not reconcile or records are incomplete")
    if not 0 <= offset < recipient.delivered_units:
        raise ValueError("offset must be within the recipient's delivered units")
    if offset < account.current_holdings:
        return TraceOutcome(recipient.owner_id, "PASS", "sampled unit falls in physically held inventory")
    if offset < account.current_holdings + account.onward_sales:
        return TraceOutcome(recipient.owner_id, "TRACE_FORWARD", "sampled unit was sold onward; the trace must continue at the buyer")
    return TraceOutcome(recipient.owner_id, "FAIL", "sampled unit falls in an attrition claim that is not independently verified")

def run_tail_population(
    recipients: list[TailRecipient],
    accounts: dict[str, OwnerAccount],
    sample_size: int,
    seed: str,
    delta: float = 0.05,
) -> dict:
    if not recipients:
        return {"status": "UNKNOWN", "reason": "empty sampling frame"}
    if not 0 < delta < 1:
        raise ValueError("delta must be in (0,1)")
    total_units = sum(r.delivered_units for r in recipients)
    if sample_size > total_units:
        raise ValueError("sample_size exceeds tail population")
    # Sample distinct unit indices from the whole tail, then map each index to
    # its recipient by cumulative delivered units. A recipient is hit in
    # proportion to what it received, and memory stays O(recipients + sample)
    # instead of O(total units).
    cumulative = list(accumulate(r.delivered_units for r in recipients))
    rng = random.Random(seed_from_text(seed))
    chosen = rng.sample(range(total_units), sample_size)
    outcomes = []
    for i in chosen:
        j = bisect_right(cumulative, i)
        recipient = recipients[j]
        offset = i - (cumulative[j - 1] if j else 0)  # position among this recipient's received units
        account = accounts.get(recipient.owner_id)
        outcomes.append(
            audit_recipient(recipient, account, offset)
            if account is not None
            else TraceOutcome(recipient.owner_id, "FAIL", "owner account unavailable")
        )
    hard_failures = sum(o.result == "FAIL" for o in outcomes)
    unresolved = sum(o.result == "TRACE_FORWARD" for o in outcomes)
    passes = sum(o.result == "PASS" for o in outcomes)
    # A TRACE_FORWARD outcome has not ended at a physically inspected unit, so it
    # is not a pass. Count it as a failure until the trace is followed to the end.
    bound_failures = hard_failures + unresolved
    upper_failure_rate = one_sided_failure_upper_bound(bound_failures, sample_size, delta)
    method = "exact_binomial_upper_unresolved_counted_as_failures"
    return {
        "schema_version": 1,
        "status": "RESEARCH_MODEL_ONLY" if unresolved == 0 else "INCOMPLETE_TRACES",
        "tail_population_units": total_units,
        "sample_size": sample_size,
        "seed": seed,
        "failures": hard_failures,
        "unresolved_traces": unresolved,
        "passes": passes,
        "failures_counted_in_bound": bound_failures,
        "upper_failure_rate": upper_failure_rate,
        "upper_bound_untraced_tail_units": total_units * upper_failure_rate,
        "delta": delta,
        "bound_method": method,
        "outcomes": [o.__dict__ for o in outcomes],
        "limitations": [
            "The result is conditional on a genuinely closed tail sampling frame.",
            "The example trace representation does not preserve individual serial-number identity through every resale.",
            "Unresolved (TRACE_FORWARD) traces have not reached a physically inspected unit; they are counted as failures in the bound until followed to a terminal PASS or FAIL.",
            "The bound is the exact one-sided binomial (Clopper-Pearson) upper limit at the stated delta; it ignores the finite-population correction, which makes it slightly conservative.",
        ],
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--sample-size", type=int, required=True)
    ap.add_argument("--seed", required=True)
    ap.add_argument("--delta", type=float, default=0.05)
    args = ap.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    recipients = [TailRecipient(**x) for x in data["recipients"]]
    accounts = {x["owner_id"]: OwnerAccount(**x) for x in data["accounts"]}
    print(json.dumps(run_tail_population(recipients, accounts, args.sample_size, args.seed, args.delta), indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
