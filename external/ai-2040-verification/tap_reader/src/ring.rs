//! Lock-free hand-off from tap worker threads to whatever consumes evidence
//! next (§5's recomputation server, in the real design; a drain thread in
//! these benchmarks).
//!
//! Built on crossbeam-queue's `ArrayQueue`, not hand-rolled unsafe atomics.
//! A hand-rolled SPSC/MPSC ring is exactly the kind of code where a subtle
//! bug (a missed memory-ordering constraint, an off-by-one on wraparound)
//! produces evidence corruption that only shows up under real contention —
//! the wrong place to be clever when a well-reviewed, widely-used crate
//! does the same job.

use crossbeam_queue::ArrayQueue;
use std::sync::Arc;

/// What one tap worker hands off per frame. Fixed-size, Copy — no
/// allocation on the hot path once the queue itself is allocated.
#[derive(Debug, Clone, Copy)]
pub struct Evidence {
    pub seq: u32,
    pub src_ip: [u8; 4],
    pub dst_ip: [u8; 4],
    pub src_port: u16,
    pub dst_port: u16,
    pub payload_len: u16,
    pub payload_hash: [u8; 16],
}

pub type EvidenceQueue = Arc<ArrayQueue<Evidence>>;

pub fn new_queue(capacity: usize) -> EvidenceQueue {
    Arc::new(ArrayQueue::new(capacity))
}
