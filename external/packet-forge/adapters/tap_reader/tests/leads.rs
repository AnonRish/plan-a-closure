//! The two leads from the previous report (REPORT.md, "Leads in your existing code"), run verbatim against
//! the pinned revision of tap_reader.
//!
//! Lead 1 fails at the pinned revision, exactly as the report predicted, so it is marked `should_panic`:
//! when tap_reader is fixed this test starts failing, which is the cue to remove the attribute.
//! `lead_1_observed` records what actually happens.  Lead 2 passes as written: nothing signals the conflict.

use tap_reader::reorder::ReorderBuffer;

#[test]
#[should_panic(expected = "assertion")]
fn out_of_order_segment_across_the_sequence_wrap() {
    let isn = u32::MAX - 9;
    let mut b = ReorderBuffer::new(isn);
    b.feed(isn.wrapping_add(10), b"WORLD"); // seq 0, arrives before the first ten bytes
    b.feed(isn, b"0123456789");
    assert_eq!(b.delivered, b"0123456789WORLD");
}

#[test]
fn lead_1_observed() {
    let isn = u32::MAX - 9;
    let mut b = ReorderBuffer::new(isn);
    b.feed(isn.wrapping_add(10), b"WORLD");
    b.feed(isn, b"0123456789");
    assert_eq!(b.delivered, b"0123456789"); // "WORLD" is gone
    assert_eq!(b.duplicates_dropped, 1); // dropped as an "already delivered" duplicate (line 45: 0 < 0xFFFFFFF6)
    assert!(!b.gap_open()); // and nothing is pending, so nothing will ever repair it
}

#[test]
fn conflicting_retransmission_is_silently_ignored() {
    let mut b = ReorderBuffer::new(1000);
    b.feed(1000, b"AAAA");
    b.feed(1000, b"BBBB");
    assert_eq!(b.delivered, b"AAAA"); // passes today, with no signal that anything conflicted
    assert_eq!(b.duplicates_dropped, 1);
}

/// Found while writing FINDINGS-tap_reader.md (a consequence of lead 1, read from the source and then run):
/// after the wrap, a retransmission of already-delivered pre-wrap bytes is not `< next_expected`, so it is
/// parked in `pending` as if it were future data. Nothing ever drains it.
#[test]
fn stale_retransmission_after_the_wrap_is_parked_forever() {
    let isn = u32::MAX - 9;
    let mut b = ReorderBuffer::new(isn);
    b.feed(isn, b"0123456789"); // in order; next_expected wraps to 0
    assert_eq!(b.delivered, b"0123456789");
    assert!(!b.gap_open());
    b.feed(isn, b"0123456789"); // an honest, byte-identical retransmission of the same segment
    assert_eq!(b.duplicates_dropped, 0); // not recognised as a duplicate...
    assert_eq!(b.reordered_count, 1); // ...but counted as an out-of-order arrival
    assert!(b.gap_open()); // and parked forever
}
