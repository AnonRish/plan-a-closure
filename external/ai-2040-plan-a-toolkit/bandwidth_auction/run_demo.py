from auction import Bid, run_auction, efficient_allocation_capped, vcg_payments_capped, welfare

if __name__ == "__main__":
    # A plausible epoch: several research efforts competing for the capped outgoing
    # channel. Units are arbitrary (think: MB of this epoch's allowance).
    bids = [
        Bid("interp_release", max_qty=40, unit_value=8.5),   # a capability eval result, high value, modest size
        Bid("incident_report", max_qty=15, unit_value=9.0),  # small, urgent, high value
        Bid("routine_metrics", max_qty=60, unit_value=1.2),  # low value, wants a lot
        Bid("external_audit", max_qty=25, unit_value=6.0),
        Bid("dataset_export", max_qty=80, unit_value=0.8),   # low value, wants the most
    ]
    capacity = 100.0

    print("=== Uncapped VCG ===")
    alloc, pay = run_auction(bids, capacity)
    by_id = {b.bidder_id: b for b in bids}
    for bidder_id, qty in sorted(alloc.items(), key=lambda kv: -kv[1]):
        v = by_id[bidder_id].unit_value
        p = pay.get(bidder_id, 0.0)
        print(f"  {bidder_id:18s} qty={qty:6.2f}  value/unit={v:5.2f}  pays={p:7.2f}  (avg price/unit={p/qty if qty else 0:.3f})")
    print(f"  total welfare: {welfare(by_id, alloc):.2f}   total allocated: {sum(alloc.values()):.2f} / {capacity}")

    print("\n=== Capped at 30% of capacity per bidder ===")
    alloc_c = efficient_allocation_capped(bids, capacity, 0.30)
    pay_c = vcg_payments_capped(bids, capacity, 0.30)
    for bidder_id, qty in sorted(alloc_c.items(), key=lambda kv: -kv[1]):
        v = by_id[bidder_id].unit_value
        p = pay_c.get(bidder_id, 0.0)
        print(f"  {bidder_id:18s} qty={qty:6.2f}  value/unit={v:5.2f}  pays={p:7.2f}")
    print(f"  total welfare: {welfare(by_id, alloc_c):.2f}   (uncapped was {welfare(by_id, alloc):.2f})")
    print(f"  total allocated: {sum(alloc_c.values()):.2f} / {capacity}")
