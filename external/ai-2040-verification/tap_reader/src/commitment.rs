//! §4: a compact, tamper-evident digest of *all* traffic, not just §3's
//! sampled subset. Two layers:
//!
//! 1. Per-epoch Merkle tree over each packet's payload hash. A tree (not a
//!    flat running hash-chain) specifically because it supports efficient
//!    proof-of-inclusion later: if a candidate payload for one packet in a
//!    million-packet epoch ever surfaces through some other channel, you
//!    can check it against the epoch root with an O(log n) proof instead
//!    of needing to replay the whole epoch.
//! 2. The epoch roots themselves get appended to a §21b-style append-only,
//!    hash-chained log — a single compact, ever-growing commitment to the
//!    entire ordered history of epochs, so a prover can't rewrite which
//!    epochs occurred after the fact either.

use crate::hashing::siphash13_128;

pub const EPOCH_KEY: [u8; 16] = [0x44u8; 16]; // public — this hash is an
                                               // identifier/commitment
                                               // structure, not a secret
                                               // boundary (unlike §3's
                                               // sampling key).

fn h(a: &[u8], b: &[u8]) -> [u8; 16] {
    let mut buf = Vec::with_capacity(a.len() + b.len());
    buf.extend_from_slice(a);
    buf.extend_from_slice(b);
    siphash13_128(&EPOCH_KEY, &buf)
}

/// A Merkle tree over one epoch's packet-payload hashes. Odd node counts
/// duplicate the last node at each level (the standard, simple convention
/// — not the only one, but unambiguous and enough for this prototype).
pub struct EpochTree {
    pub leaves: Vec<[u8; 16]>,
    pub root: [u8; 16],
    levels: Vec<Vec<[u8; 16]>>, // levels[0] == leaves, levels.last() == [root]
}

impl EpochTree {
    pub fn build(leaves: Vec<[u8; 16]>) -> Self {
        assert!(!leaves.is_empty(), "empty epoch — caller's job to skip these");
        let mut levels = vec![leaves.clone()];
        let mut cur = leaves.clone();
        while cur.len() > 1 {
            let mut next = Vec::with_capacity(cur.len().div_ceil(2));
            let mut i = 0;
            while i < cur.len() {
                let left = cur[i];
                let right = if i + 1 < cur.len() { cur[i + 1] } else { cur[i] };
                next.push(h(&left, &right));
                i += 2;
            }
            levels.push(next.clone());
            cur = next;
        }
        let root = cur[0];
        Self { leaves, root, levels }
    }

    /// Sibling hashes needed to verify `leaf_index` against `self.root`,
    /// bottom to top.
    pub fn proof(&self, leaf_index: usize) -> Vec<[u8; 16]> {
        let mut proof = Vec::new();
        let mut idx = leaf_index;
        for level in &self.levels[..self.levels.len() - 1] {
            let sibling = if idx % 2 == 0 {
                if idx + 1 < level.len() { level[idx + 1] } else { level[idx] }
            } else {
                level[idx - 1]
            };
            proof.push(sibling);
            idx /= 2;
        }
        proof
    }
}

/// Verify a leaf against a root using an inclusion proof — this is the
/// operation an auditor runs *later*, if a candidate payload surfaces for
/// one specific packet in an epoch that was otherwise hash-only.
pub fn verify_inclusion(leaf: [u8; 16], leaf_index: usize, proof: &[[u8; 16]], root: [u8; 16]) -> bool {
    let mut cur = leaf;
    let mut idx = leaf_index;
    for sibling in proof {
        cur = if idx % 2 == 0 { h(&cur, sibling) } else { h(sibling, &cur) };
        idx /= 2;
    }
    cur == root
}

/// The append-only chain of epoch roots (§21b's pattern, reused rather than
/// redesigned). `commit` folds in a new epoch root; tampering with any past
/// entry breaks every subsequent link, exactly like §21b's log.
pub struct EpochChain {
    pub head: [u8; 16],
    pub entries: Vec<(u64, [u8; 16], [u8; 16])>, // (epoch_number, epoch_root, chain_head_after)
}

impl EpochChain {
    pub fn new() -> Self {
        Self { head: [0u8; 16], entries: Vec::new() }
    }

    pub fn commit(&mut self, epoch_number: u64, epoch_root: [u8; 16]) {
        let new_head = h(&self.head, &epoch_root);
        self.entries.push((epoch_number, epoch_root, new_head));
        self.head = new_head;
    }

    /// Recompute the chain from scratch and check it matches `self.head` —
    /// tampering with any single entry's stored root, without recomputing
    /// every subsequent link, is caught here.
    pub fn verify(&self) -> bool {
        let mut running = [0u8; 16];
        for &(_, root, stored_head) in &self.entries {
            running = h(&running, &root);
            if running != stored_head {
                return false;
            }
        }
        running == self.head
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn inclusion_proof_verifies_for_every_leaf() {
        let leaves: Vec<[u8; 16]> = (0u8..37).map(|i| [i; 16]).collect(); // odd count on purpose
        let tree = EpochTree::build(leaves.clone());
        for (i, &leaf) in leaves.iter().enumerate() {
            let proof = tree.proof(i);
            assert!(verify_inclusion(leaf, i, &proof, tree.root), "leaf {i} failed to verify");
        }
    }

    #[test]
    fn inclusion_proof_rejects_wrong_leaf() {
        let leaves: Vec<[u8; 16]> = (0u8..16).map(|i| [i; 16]).collect();
        let tree = EpochTree::build(leaves.clone());
        let proof = tree.proof(3);
        let wrong_leaf = [99u8; 16];
        assert!(!verify_inclusion(wrong_leaf, 3, &proof, tree.root));
    }

    #[test]
    fn tampering_with_one_epoch_breaks_chain_from_that_point_on() {
        let mut chain = EpochChain::new();
        for i in 0..10u64 {
            chain.commit(i, [i as u8; 16]);
        }
        assert!(chain.verify());

        // Tamper with entry 4's stored root without touching anything else.
        chain.entries[4].1 = [0xFFu8; 16];
        assert!(!chain.verify(), "tampering with a middle entry should break verification");
    }
}
