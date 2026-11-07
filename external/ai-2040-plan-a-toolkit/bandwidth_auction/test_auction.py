import random
import itertools
import pytest

from .auction import (
    Bid, efficient_allocation, vcg_payments, run_auction, welfare, utility,
    efficient_allocation_capped, vcg_payments_capped,
)


def random_bids(rng, n, id_prefix="b"):
    return [
        Bid(bidder_id=f"{id_prefix}{i}", max_qty=rng.uniform(1, 20), unit_value=rng.uniform(0.1, 10))
        for i in range(n)
    ]


# ---------- worked example, hand-verified in the design notes ----------

def test_hand_verified_three_bidder_example():
    bids = [Bid("A", 10, 5), Bid("B", 10, 3), Bid("C", 10, 1)]
    alloc, pay = run_auction(bids, capacity=15)
    assert alloc == {"A": 10, "B": 5}
    assert pay["A"] == pytest.approx(20.0)
    assert pay["B"] == pytest.approx(5.0)


# ---------- basic invariants ----------

def test_allocation_never_exceeds_capacity():
    rng = random.Random(1)
    for _ in range(100):
        bids = random_bids(rng, rng.randint(1, 8))
        cap = rng.uniform(1, 50)
        alloc = efficient_allocation(bids, cap)
        assert sum(alloc.values()) <= cap + 1e-9


def test_allocation_never_exceeds_individual_max_qty():
    rng = random.Random(2)
    for _ in range(100):
        bids = random_bids(rng, rng.randint(1, 8))
        cap = rng.uniform(1, 50)
        alloc = efficient_allocation(bids, cap)
        by_id = {b.bidder_id: b for b in bids}
        for bidder_id, qty in alloc.items():
            assert qty <= by_id[bidder_id].max_qty + 1e-9


def test_payments_are_nonnegative():
    rng = random.Random(3)
    for _ in range(100):
        bids = random_bids(rng, rng.randint(2, 8))
        cap = rng.uniform(1, 50)
        _, pay = run_auction(bids, cap)
        assert all(p >= -1e-9 for p in pay.values())


def test_individual_rationality():
    """No winner should ever pay more than what they won is worth to them."""
    rng = random.Random(4)
    for _ in range(200):
        bids = random_bids(rng, rng.randint(2, 8))
        cap = rng.uniform(1, 50)
        alloc, pay = run_auction(bids, cap)
        by_id = {b.bidder_id: b for b in bids}
        for bidder_id, qty in alloc.items():
            assert pay.get(bidder_id, 0.0) <= qty * by_id[bidder_id].unit_value + 1e-6


def test_greedy_allocation_is_welfare_optimal_vs_brute_force():
    """For small instances, brute-force every allocation on a coarse grid and confirm
    the greedy rule matches or beats all of them. Fractional knapsack with a single
    'density' (unit_value, no varying size) is greedy-optimal by construction, but
    this checks the implementation, not just the theorem."""
    rng = random.Random(5)
    for _ in range(30):
        bids = random_bids(rng, 3)
        cap = rng.uniform(2, 20)
        by_id = {b.bidder_id: b for b in bids}
        greedy_alloc = efficient_allocation(bids, cap)
        greedy_w = welfare(by_id, greedy_alloc)

        # brute force: try every order of "who gets priority" and every corresponding
        # greedy-in-that-order allocation; true optimum must be >= all of these, and
        # greedy-by-value must match the best one found.
        best_alt = 0.0
        for perm in itertools.permutations(bids):
            remaining, alloc = cap, {}
            for b in perm:
                q = min(b.max_qty, remaining)
                if q > 0:
                    alloc[b.bidder_id] = q
                    remaining -= q
            best_alt = max(best_alt, welfare(by_id, alloc))
        assert greedy_w >= best_alt - 1e-6


def test_truthful_bidding_weakly_dominates_lying():
    """The core VCG guarantee, checked empirically rather than just asserted: across
    many random scenarios, a bidder trying various lies about their unit_value never
    ends up with higher true-utility than they'd get by reporting truthfully."""
    rng = random.Random(6)
    lie_multipliers = [0.1, 0.3, 0.5, 0.7, 0.9, 1.1, 1.3, 1.6, 2.0, 3.0, 5.0]
    violations = []

    for trial in range(300):
        n = rng.randint(2, 6)
        bids = random_bids(rng, n)
        cap = rng.uniform(1, 40)
        target = rng.choice(bids)
        true_value = target.unit_value

        alloc_t, pay_t = run_auction(bids, cap)
        u_truth = utility(alloc_t, pay_t, target.bidder_id, true_value)

        for m in lie_multipliers:
            lied_bids = [
                Bid(target.bidder_id, target.max_qty, true_value * m) if b.bidder_id == target.bidder_id else b
                for b in bids
            ]
            alloc_l, pay_l = run_auction(lied_bids, cap)
            u_lie = utility(alloc_l, pay_l, target.bidder_id, true_value)  # utility measured at TRUE value
            if u_lie > u_truth + 1e-6:
                violations.append((trial, m, u_truth, u_lie))

    assert violations == [], f"found {len(violations)} case(s) where lying beat truth-telling: {violations[:5]}"


# ---------- capped variant ----------

def test_capped_allocation_respects_cap():
    rng = random.Random(7)
    for _ in range(100):
        bids = random_bids(rng, rng.randint(2, 8))
        cap = rng.uniform(5, 50)
        share = rng.uniform(0.1, 0.6)
        alloc = efficient_allocation_capped(bids, cap, share)
        for qty in alloc.values():
            assert qty <= cap * share + 1e-9


def test_capped_payments_still_nonnegative_and_individually_rational():
    rng = random.Random(8)
    for _ in range(100):
        bids = random_bids(rng, rng.randint(2, 8))
        cap = rng.uniform(5, 50)
        share = rng.uniform(0.2, 0.7)
        alloc = efficient_allocation_capped(bids, cap, share)
        pay = vcg_payments_capped(bids, cap, share)
        by_id = {b.bidder_id: b for b in bids}
        for bidder_id, qty in alloc.items():
            assert pay.get(bidder_id, 0.0) >= -1e-9
            assert pay.get(bidder_id, 0.0) <= qty * by_id[bidder_id].unit_value + 1e-6


def test_cap_can_reduce_total_welfare_vs_uncapped():
    """This is the honest cost of the fairness cap, demonstrated rather than asserted away:
    construct a case where one bidder's true value justifies more than the cap allows,
    and show capped welfare is strictly lower than uncapped."""
    bids = [Bid("whale", 100, 10.0), Bid("small1", 5, 1.0), Bid("small2", 5, 1.0)]
    cap = 20
    uncapped_alloc = efficient_allocation(bids, cap)
    capped_alloc = efficient_allocation_capped(bids, cap, max_share_frac=0.25)  # whale limited to 5 units
    by_id = {b.bidder_id: b for b in bids}
    uncapped_w = welfare(by_id, uncapped_alloc)
    capped_w = welfare(by_id, capped_alloc)
    assert capped_w < uncapped_w


def test_capped_mechanism_is_still_truthful_empirically():
    """The cap costs efficiency (proven above) -- but does it also cost truthfulness?
    Tested, not assumed: VCG payments computed relative to the SAME capped allocation
    rule stay truthful, because the cap is a fixed constraint independent of any one
    bidder's own report. Same sweep as the uncapped test, same zero-violations result."""
    rng = random.Random(9)
    lie_multipliers = [0.1, 0.3, 0.5, 0.7, 0.9, 1.1, 1.3, 1.6, 2.0, 3.0, 5.0]
    violations = []
    for trial in range(300):
        n = rng.randint(2, 6)
        bids = random_bids(rng, n)
        cap = rng.uniform(1, 40)
        share = rng.uniform(0.15, 0.6)
        target = rng.choice(bids)
        true_value = target.unit_value

        alloc_t = efficient_allocation_capped(bids, cap, share)
        pay_t = vcg_payments_capped(bids, cap, share)
        u_truth = alloc_t.get(target.bidder_id, 0.0) * true_value - pay_t.get(target.bidder_id, 0.0)

        for m in lie_multipliers:
            lied_bids = [
                Bid(target.bidder_id, target.max_qty, true_value * m) if b.bidder_id == target.bidder_id else b
                for b in bids
            ]
            alloc_l = efficient_allocation_capped(lied_bids, cap, share)
            pay_l = vcg_payments_capped(lied_bids, cap, share)
            u_lie = alloc_l.get(target.bidder_id, 0.0) * true_value - pay_l.get(target.bidder_id, 0.0)
            if u_lie > u_truth + 1e-6:
                violations.append((trial, m, u_truth, u_lie))

    assert violations == [], f"found {len(violations)} case(s): {violations[:5]}"
