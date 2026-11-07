"""
auction.py

The Transparency Plan's outgoing channel between the secure ("opaque") zone
and the public ("transparent") zone is bandwidth-capped -- a fixed rate,
shared by everyone who wants to move something across it -- allocated by
what the plan calls "an ongoing auction for the outgoing bandwidth." It
doesn't specify a mechanism. "Highest bidder wins, pays their bid" is the
naive answer and it's a bad one: it gives every bidder an incentive to
shade their bid down, so the allocation stops reflecting true value.

This implements Vickrey-Clarke-Groves (VCG) instead: bidders report a
per-unit value and a max quantity, capacity is allocated to maximize
declared welfare, and each winner pays exactly the externality they impose
on everyone else -- the welfare loss their presence causes the rest of the
pool. VCG's textbook guarantee is that truthful reporting is a dominant
strategy: no bidder can ever do better by lying, regardless of what anyone
else bids. That's not asserted here, it's tested -- see
test_auction.py::test_truthful_bidding_weakly_dominates_lying.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Bid:
    bidder_id: str
    max_qty: float     # most this bidder wants, ever
    unit_value: float   # true (or claimed) value per unit, flat up to max_qty


def efficient_allocation(bids, capacity):
    """Greedily allocate capacity to the highest declared unit_value first.
    This maximizes total declared welfare -- the textbook VCG allocation rule."""
    ordered = sorted(bids, key=lambda b: (-b.unit_value, b.bidder_id))
    remaining = capacity
    allocation = {}
    for b in ordered:
        if remaining <= 1e-12:
            break
        qty = min(b.max_qty, remaining)
        if qty > 1e-12:
            allocation[b.bidder_id] = qty
            remaining -= qty
    return allocation


def welfare(bids_by_id, allocation):
    return sum(allocation.get(bidder_id, 0.0) * bids_by_id[bidder_id].unit_value for bidder_id in allocation)


def vcg_payments(bids, capacity):
    """payment_i = (others' best achievable welfare without i) - (others' actual welfare with i present)."""
    bids_by_id = {b.bidder_id: b for b in bids}
    full_alloc = efficient_allocation(bids, capacity)
    full_welfare = welfare(bids_by_id, full_alloc)

    payments = {}
    for i_id, qty_i in full_alloc.items():
        others_welfare_with_i = full_welfare - qty_i * bids_by_id[i_id].unit_value
        bids_without_i = [b for b in bids if b.bidder_id != i_id]
        alloc_without_i = efficient_allocation(bids_without_i, capacity)
        others_welfare_without_i = welfare(bids_by_id, alloc_without_i)
        payments[i_id] = max(0.0, others_welfare_without_i - others_welfare_with_i)
    return payments


def run_auction(bids, capacity):
    alloc = efficient_allocation(bids, capacity)
    pay = vcg_payments(bids, capacity)
    return alloc, pay


def utility(allocation, payments, bidder_id, true_value):
    return allocation.get(bidder_id, 0.0) * true_value - payments.get(bidder_id, 0.0)


# ---- capped variant: no single bidder may take more than max_share_frac of capacity ----

def efficient_allocation_capped(bids, capacity, max_share_frac):
    """Same greedy rule, but no bidder's allocation may exceed max_share_frac * capacity.
    This is a real policy lever against one well-funded bidder permanently owning the
    channel -- but it costs something: see README, 'What the cap actually costs.'"""
    cap_per_bidder = capacity * max_share_frac
    ordered = sorted(bids, key=lambda b: (-b.unit_value, b.bidder_id))
    remaining = capacity
    allocation = {}
    for b in ordered:
        if remaining <= 1e-12:
            break
        qty = min(b.max_qty, cap_per_bidder, remaining)
        if qty > 1e-12:
            allocation[b.bidder_id] = qty
            remaining -= qty
    return allocation


def vcg_payments_capped(bids, capacity, max_share_frac):
    bids_by_id = {b.bidder_id: b for b in bids}
    full_alloc = efficient_allocation_capped(bids, capacity, max_share_frac)
    full_welfare = welfare(bids_by_id, full_alloc)
    payments = {}
    for i_id, qty_i in full_alloc.items():
        others_welfare_with_i = full_welfare - qty_i * bids_by_id[i_id].unit_value
        bids_without_i = [b for b in bids if b.bidder_id != i_id]
        alloc_without_i = efficient_allocation_capped(bids_without_i, capacity, max_share_frac)
        others_welfare_without_i = welfare(bids_by_id, alloc_without_i)
        payments[i_id] = max(0.0, others_welfare_without_i - others_welfare_with_i)
    return payments
