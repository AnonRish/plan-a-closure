#!/usr/bin/env python3
"""Recursive two-layer audit chain from AI 2040 Recommendation #2 (covert-projects supplement).

Layer 1 audits every owner at or above the threshold T, then every above-T customer of an
audited owner, recursively, until every unaudited recipient is below T. Recorded outflows that
cannot be traced onward (sales to counterparties that cannot be produced, unverifiable
decommissioning claims, unaccounted units, inspection shortfalls) are added in full to the
untraced pool L. A single such event of at least T units blocks certification.

Layer 2 samples units uniformly from everything recorded as delivered into the tail of
below-T recipients. Each sampled unit is resolved proportionally inside its recipient's
account (held, sold onward, decommissioned). Sold-onward units are followed to the buyer,
where the audit repeats, until the trace ends as a pass (a physically inspected chip, a
verified decommissioning, or an audited firm whose shortfalls are already counted in L) or a
fail (inspection shortfall, unbalanced account, buyer that cannot be produced, unverifiable
decommissioning claim, or a trace that exceeds the depth limit).

The result is a one-sided bound: with confidence 1 - delta, no covert project in the declared
closed population exceeds D + L, where D is the tail size times the exact binomial upper
failure rate (track3_certificate.py).

This is a research model over a synthetic or declared ledger. It is not a verification
result: it is conditional on a closed population and on the records being the records.

    python track3_audit_chain.py --input data/track3/audit_chain_input.example.json --sample-size 300
"""
from __future__ import annotations

import argparse
import json
import math
import random
from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass
from itertools import accumulate
from pathlib import Path
from typing import Any

from track3_certificate import one_sided_failure_upper_bound
from track3_tail_audit import seed_from_text

DEFAULT_MAX_DEPTH = 25
OUTCOME_LIST_LIMIT = 1000


@dataclass(frozen=True)
class Sale:
    vendor: str
    buyer: str
    units: int
    buyer_producible: bool = True


@dataclass(frozen=True)
class Transfer:
    buyer: str
    units: int
    buyer_producible: bool = True


@dataclass(frozen=True)
class Decommission:
    units: int
    verified: bool = False


@dataclass(frozen=True)
class Account:
    owner: str
    held: int = 0
    inspected: int = 0  # how many of the held units were actually produced for physical inspection
    transfers: tuple[Transfer, ...] = ()
    decommissions: tuple[Decommission, ...] = ()

    @property
    def disposed(self) -> int:
        return self.held + sum(t.units for t in self.transfers) + sum(d.units for d in self.decommissions)


def _units(value: Any, where: str) -> int:
    try:
        ok = not isinstance(value, bool) and isinstance(value, (int, float)) and value == int(value) and value >= 0
    except (ValueError, OverflowError):
        ok = False
    if not ok:
        raise ValueError(f"{where}: units must be a non-negative integer, got {value!r}")
    return int(value)


def load_population(data: dict[str, Any]) -> tuple[list[Sale], dict[str, Account]]:
    accounts: dict[str, Account] = {}
    for owner, raw in (data.get("accounts") or {}).items():
        held = _units(raw.get("held", 0), f"accounts.{owner}.held")
        inspected = _units(raw.get("inspected", 0), f"accounts.{owner}.inspected")
        if inspected > held:
            raise ValueError(f"accounts.{owner}: inspected ({inspected}) cannot exceed held ({held})")
        transfers = tuple(
            Transfer(str(t["buyer"]), _units(t["units"], f"accounts.{owner}.transfers"), bool(t.get("buyer_producible", True)))
            for t in raw.get("transfers", [])
        )
        decommissions = tuple(
            Decommission(_units(d["units"], f"accounts.{owner}.decommissions"), bool(d.get("verified", False)))
            for d in raw.get("decommissions", [])
        )
        accounts[owner] = Account(owner, held, inspected, transfers, decommissions)

    sales = [
        Sale(str(s["vendor"]), str(s["buyer"]), _units(s["units"], "sales"), bool(s.get("buyer_producible", True)))
        for s in data.get("sales", [])
    ]
    for s in sales:
        if s.buyer_producible and s.buyer not in accounts:
            raise ValueError(f"sales: buyer {s.buyer!r} has no account; mark it buyer_producible=false if it cannot be produced")
    for acct in accounts.values():
        for t in acct.transfers:
            if t.buyer_producible and t.buyer not in accounts:
                raise ValueError(
                    f"accounts.{acct.owner}: transfer buyer {t.buyer!r} has no account; mark it buyer_producible=false if it cannot be produced"
                )
    return sales, accounts


def clean_traces_needed(tail_units: int, max_d_units: float, delta: float) -> int:
    """Smallest number of clean (all-pass) traces that certifies D <= max_d_units.

    Solves 1 - delta**(1/n) <= max_d_units / tail_units. The supplement's rule of thumb is
    n ~ (tail_units / max_d_units) * ln(1 / delta).
    """
    if not 0 < delta < 1:
        raise ValueError("delta must be between 0 and 1")
    if not 0 < max_d_units < tail_units:
        raise ValueError("max_d_units must satisfy 0 < max_d_units < tail_units")
    return math.ceil(math.log(delta) / math.log1p(-max_d_units / tail_units))


def _unknown(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "UNKNOWN",
        "reason": reason,
        "upper_bound_units": None,
        "bound_method": "AUDIT_CHAIN_NOT_COMPUTED",
        **extra,
    }


def run_audit_chain(
    data: dict[str, Any],
    sample_size: int | None = None,
    seed: str | None = None,
    delta: float | None = None,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> dict[str, Any]:
    seed = seed if seed is not None else str(data.get("seed", "track3-audit-chain"))
    delta = float(delta if delta is not None else data.get("delta", 0.05))
    if not 0 < delta < 1:
        raise ValueError("delta must be between 0 and 1")
    if max_depth < 1:
        raise ValueError("max_depth must be >= 1")

    if not data.get("population_closed", False):
        return _unknown("the population is not declared closed; a certificate is only meaningful for a closed population")
    t_spec = data.get("threshold_T") or {}
    if t_spec.get("unit") != "H100e" or not isinstance(t_spec.get("value"), (int, float)) or t_spec["value"] <= 0:
        return _unknown("threshold_T must be given in H100e with a positive value; convert MW with track3_units.py")
    threshold = float(t_spec["value"])

    sales, accounts = load_population(data)

    # Complete ledger: every recorded flow into each owner. Used to reconcile accounts.
    ledger: dict[str, int] = defaultdict(int)
    for s in sales:
        if s.buyer_producible:
            ledger[s.buyer] += s.units
    for acct in accounts.values():
        for t in acct.transfers:
            if t.buyer_producible:
                ledger[t.buyer] += t.units

    # ---- Layer 1: exhaustive audit above T, recursively -------------------------------------
    l_events: list[dict[str, Any]] = []
    blocking: list[dict[str, Any]] = []

    def add_to_l(kind: str, units: int, **context: Any) -> None:
        if units <= 0:
            return
        event = {"kind": kind, "units": units, **context}
        l_events.append(event)
        if units >= threshold:
            blocking.append(event)

    known: dict[str, int] = defaultdict(int)  # units the auditor can see delivered to each owner
    for s in sales:
        if s.buyer_producible:
            known[s.buyer] += s.units
        else:
            add_to_l("UNAUDITABLE_COUNTERPARTY", s.units, seller=s.vendor, buyer=s.buyer)

    audited: list[str] = []
    audited_set: set[str] = set()
    while True:
        newly = sorted(o for o, units in known.items() if units >= threshold and o not in audited_set)
        if not newly:
            break
        for owner in newly:
            audited_set.add(owner)
            audited.append(owner)
            for t in accounts[owner].transfers:
                if t.buyer_producible:
                    known[t.buyer] += t.units
                else:
                    add_to_l("UNAUDITABLE_COUNTERPARTY", t.units, seller=owner, buyer=t.buyer)

    for owner in audited:
        acct = accounts[owner]
        received, disposed = ledger[owner], acct.disposed
        if received > disposed:
            add_to_l("UNACCOUNTED_UNITS", received - disposed, owner=owner)
        elif received < disposed:
            blocking.append(
                {
                    "kind": "INCONSISTENT_RECORDS",
                    "units": disposed - received,
                    "owner": owner,
                    "reason": "recorded dispositions exceed recorded receipts",
                }
            )
        add_to_l("INSPECTION_SHORTFALL", acct.held - acct.inspected, owner=owner)
        for d in acct.decommissions:
            if not d.verified:
                add_to_l("UNVERIFIED_DECOMMISSION", d.units, owner=owner)

    untraced_pool = sum(e["units"] for e in l_events)

    # ---- Layer 2: sample the tail and follow every trace to an end ---------------------------
    tail = {o: u for o, u in known.items() if o not in audited_set and u > 0}
    tail_units = sum(tail.values())
    outcomes: list[dict[str, Any]] = []
    failures = 0
    if tail_units > 0:
        if sample_size is None or sample_size <= 0:
            raise ValueError("sample_size is required (and must be positive) when the tail is not empty")
        if sample_size > tail_units:
            raise ValueError(f"sample_size ({sample_size}) cannot exceed the tail size ({tail_units})")
        owners = sorted(tail)
        cumulative = list(accumulate(tail[o] for o in owners))
        chosen = random.Random(seed_from_text(seed)).sample(range(tail_units), sample_size)
        for k, unit_index in enumerate(chosen):
            first = owners[bisect_right(cumulative, unit_index)]
            trace_rng = random.Random(seed_from_text(f"{seed}/trace/{k}"))
            outcome = _follow_trace(first, accounts, ledger, audited_set, trace_rng, max_depth)
            outcome["sample_index"] = k
            failures += outcome["result"] == "FAIL"
            outcomes.append(outcome)
        upper_rate = one_sided_failure_upper_bound(failures, sample_size, delta)
    else:
        sample_size = 0
        upper_rate = 0.0
    d_units = tail_units * upper_rate

    status = "BLOCKED" if blocking else "PASS"
    return {
        "schema_version": 1,
        "status": status,
        "claim": (
            "With confidence 1 - delta, no covert project in the declared closed population exceeds "
            "D + L (units in the input's unit, H100e). Research model only."
        ),
        "delta": delta,
        "threshold_T": {"value": threshold, "unit": "H100e"},
        "seed": seed,
        "max_depth": max_depth,
        "audited_firms": [{"owner": o, "received_units": ledger[o]} for o in audited],
        "untraced_pool_L": {"units": untraced_pool, "events": l_events},
        "blocking_events": blocking,
        "tail": {
            "recipients": len(tail),
            "delivered_units": tail_units,
            "sample_size": sample_size,
            "passes": sample_size - failures,
            "failures": failures,
            "upper_failure_rate": upper_rate,
            "D_units": d_units,
            "bound_method": "exact_binomial_upper",
            "outcomes": outcomes[:OUTCOME_LIST_LIMIT],
            "outcomes_truncated": len(outcomes) > OUTCOME_LIST_LIMIT,
        },
        "upper_bound_units": untraced_pool + d_units,
        "bound_method": "L_PLUS_TAIL_TIMES_EXACT_BINOMIAL_UPPER_FAILURE_RATE",
        "limitations": [
            "Conditional on a declared closed population and on the records being the records; a research model, not a verification result.",
            "Vendor production records (Recommendation #1) and unrecorded sales (Recommendation #3) are outside this model.",
            "Serial-number continuity and advance-notice rules are protocol requirements; inspections here pass or fail as recorded.",
            "A trace that reaches an audited firm ends as a pass because that firm's shortfalls are already counted in L.",
            "The finite-population correction is not applied, which makes D slightly conservative.",
            "When status is BLOCKED the numeric bound is still computed but exceeds what can be certified against the treaty bound.",
        ],
    }


def _follow_trace(
    first_owner: str,
    accounts: dict[str, Account],
    ledger: dict[str, int],
    audited: set[str],
    rng: random.Random,
    max_depth: int,
) -> dict[str, Any]:
    path = [first_owner]
    owner = first_owner

    def end(result: str, terminal: str, reason: str) -> dict[str, Any]:
        return {"result": result, "terminal": terminal, "reason": reason, "path": path}

    for _ in range(max_depth):
        if owner in audited:
            return end("PASS", "audited_firm", "reached an audited firm; any shortfall there is already in L")
        acct = accounts[owner]
        received = ledger[owner]
        if received != acct.disposed:
            return end("FAIL", "unbalanced_account", f"{owner}: received {received} but accounts for {acct.disposed}")
        offset = rng.randrange(received)  # sales records do not distinguish chips: resolve proportionally
        if offset < acct.held:
            if offset < acct.inspected:
                return end("PASS", "inspected_chip", f"{owner}: a held chip was produced for inspection")
            return end("FAIL", "inspection_shortfall", f"{owner}: a held chip could not be produced")
        offset -= acct.held
        moved = False
        for t in acct.transfers:
            if offset < t.units:
                if not t.buyer_producible:
                    return end("FAIL", "buyer_not_produced", f"{owner}: buyer {t.buyer} cannot be produced")
                owner = t.buyer
                path.append(owner)
                moved = True
                break
            offset -= t.units
        if moved:
            continue
        for d in acct.decommissions:
            if offset < d.units:
                if d.verified:
                    return end("PASS", "verified_decommission", f"{owner}: decommissioning verified")
                return end("FAIL", "unverified_decommission", f"{owner}: decommissioning claim not verified")
            offset -= d.units
        return end("FAIL", "unbalanced_account", f"{owner}: sampled unit fell outside every recorded disposition")
    return end("FAIL", "max_depth_exceeded", f"trace exceeded {max_depth} hops")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--sample-size", type=int)
    ap.add_argument("--seed")
    ap.add_argument("--delta", type=float)
    ap.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH)
    args = ap.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    sample = args.sample_size if args.sample_size is not None else data.get("sample_size")
    result = run_audit_chain(data, sample_size=sample, seed=args.seed, delta=args.delta, max_depth=args.max_depth)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
