//! §8: §2b's reassembly (frame.rs, reassembly.rs) assumed segments arrive in
//! the order they were sent. That's true for the *bytes TCP eventually
//! hands the application* (that's what TCP is for) but not necessarily true
//! for what a passive tap observes on the wire, because retransmissions are
//! new packets sent later, interleaved with whatever the sender was doing
//! at that later time — not a copy of the original arriving late. A tap has
//! no participation in the TCP handshake or flow control; it just sees
//! whatever crosses the fiber, in whatever order that happens to be.
//!
//! This buffer restores in-order delivery from out-of-order segments using
//! the TCP sequence numbers `frame.rs` already extracts — no new capture
//! mechanism, just doing something with data already in hand.

use std::collections::BTreeMap;

pub struct ReorderBuffer {
    next_expected: u32,
    pending: BTreeMap<u32, Vec<u8>>, // seq -> payload, for segments that
                                      // arrived before something earlier
    pub delivered: Vec<u8>,
    pub duplicates_dropped: u32,
    pub reordered_count: u32, // segments that arrived out of order but
                               // were eventually delivered correctly
}

impl ReorderBuffer {
    pub fn new(initial_seq: u32) -> Self {
        Self {
            next_expected: initial_seq,
            pending: BTreeMap::new(),
            delivered: Vec::new(),
            duplicates_dropped: 0,
            reordered_count: 0,
        }
    }

    /// Feed one captured segment (sequence number + payload), in whatever
    /// order the tap observed it. Delivers bytes to `self.delivered` in
    /// logical order, buffering anything that arrived ahead of a gap.
    pub fn feed(&mut self, seq: u32, payload: &[u8]) {
        if payload.is_empty() {
            return;
        }

        if seq < self.next_expected {
            // Already delivered this range — a retransmission of data we
            // already have (or, at the u32 wraparound boundary, extremely
            // stale; not handled here, same simplification frame.rs itself
            // documents for options/VLAN).
            self.duplicates_dropped += 1;
            return;
        }

        if seq == self.next_expected {
            self.delivered.extend_from_slice(payload);
            self.next_expected = self.next_expected.wrapping_add(payload.len() as u32);
            self.drain_ready();
        } else {
            // Arrived ahead of a gap — hold it, and remember this was an
            // out-of-order arrival (for the write-up's own honesty: how
            // often this actually triggers is worth reporting, not just
            // whether the mechanism exists).
            self.reordered_count += 1;
            self.pending.insert(seq, payload.to_vec());
        }
    }

    /// After delivering in-order data, check whether previously-buffered
    /// out-of-order segments now form a contiguous run and can be flushed.
    fn drain_ready(&mut self) {
        while let Some(payload) = self.pending.remove(&self.next_expected) {
            self.next_expected = self.next_expected.wrapping_add(payload.len() as u32);
            self.delivered.extend_from_slice(&payload);
        }
    }

    pub fn gap_open(&self) -> bool {
        !self.pending.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rand::seq::SliceRandom;
    use rand::thread_rng;

    fn split_into_segments(data: &[u8], seg_len: usize, start_seq: u32) -> Vec<(u32, Vec<u8>)> {
        data.chunks(seg_len)
            .scan(start_seq, |seq, chunk| {
                let this_seq = *seq;
                *seq = seq.wrapping_add(chunk.len() as u32);
                Some((this_seq, chunk.to_vec()))
            })
            .collect()
    }

    #[test]
    fn in_order_delivery_is_trivially_correct() {
        let data = b"the quick brown fox jumps over the lazy dog, repeated for length. ".repeat(10);
        let segs = split_into_segments(&data, 17, 1000);
        let mut buf = ReorderBuffer::new(1000);
        for (seq, payload) in &segs {
            buf.feed(*seq, payload);
        }
        assert_eq!(buf.delivered, data);
        assert_eq!(buf.reordered_count, 0);
        assert!(!buf.gap_open());
    }

    #[test]
    fn fully_scrambled_delivery_still_reconstructs_correctly() {
        let data = b"the quick brown fox jumps over the lazy dog, repeated for length. ".repeat(10);
        let mut segs = split_into_segments(&data, 13, 5000);
        let original_order = segs.clone();
        segs.shuffle(&mut thread_rng());

        let mut buf = ReorderBuffer::new(5000);
        for (seq, payload) in &segs {
            buf.feed(*seq, payload);
        }
        assert_eq!(buf.delivered, data, "final byte stream must match original regardless of arrival order");
        assert!(!buf.gap_open(), "everything should have drained once all segments arrived");
        assert!(
            buf.reordered_count > 0,
            "a shuffled delivery with this many segments should trigger the out-of-order path at least once"
        );
        assert_ne!(segs, original_order, "test isn't meaningful if the shuffle happened to be a no-op");
    }

    #[test]
    fn retransmission_duplicate_is_dropped_not_double_counted() {
        let data = b"duplicate segment handling test payload data here";
        let segs = split_into_segments(data, 10, 2000);
        let mut buf = ReorderBuffer::new(2000);
        for (seq, payload) in &segs {
            buf.feed(*seq, payload); // original
        }
        // Retransmit the very first segment, as a real sender might if it
        // never saw the ACK in time — arrives *after* everything else.
        let (first_seq, first_payload) = &segs[0];
        buf.feed(*first_seq, first_payload);

        assert_eq!(buf.delivered, data, "duplicate must not be appended again");
        assert_eq!(buf.duplicates_dropped, 1);
    }
}
