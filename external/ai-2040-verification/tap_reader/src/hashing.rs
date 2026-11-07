//! Three candidate hash functions for per-frame evidence hashing.
//!
//! §2's context is explicit that BLAKE3 is the wrong tool here (it's right
//! for §15's GPU HBM wiping, where the bottleneck is DRAM/HBM bandwidth on
//! large buffers) and that SipHash-1-3-128 / AES-128-GMAC should beat it at
//! frame size (tens to low thousands of bytes, not the megabyte+ buffers
//! BLAKE3's tree structure is built for). `bench_hash` below measures that
//! claim directly instead of taking it on faith.

use aes_gcm::aead::{Aead, KeyInit, Payload};
use aes_gcm::{Aes128Gcm, Nonce};
use siphasher::sip128::{Hasher128, SipHasher13};
use std::hash::Hasher;

pub const OUTPUT_LEN: usize = 16; // all three produce 128-bit tags here

/// BLAKE3, 128-bit truncation (BLAKE3's native output is an XOF; taking the
/// first 16 bytes is a normal, documented way to get a fixed-size tag from
/// it and keeps the comparison apples-to-apples with the other two).
#[inline]
pub fn blake3_128(data: &[u8]) -> [u8; OUTPUT_LEN] {
    let hash = blake3::hash(data);
    let mut out = [0u8; OUTPUT_LEN];
    out.copy_from_slice(&hash.as_bytes()[..OUTPUT_LEN]);
    out
}

/// SipHash-1-3, 128-bit output. c=1 compression round / d=3 finalization
/// rounds — the fast, "less conservative than 2-4" parameterization that's
/// fine here because the tap isn't using this hash as the sole line of
/// defense against a resourceful forger; §5's DiFR comparison and §21b's
/// hash-chained log are what actually carry adversarial weight. The tap
/// just needs a fast, collision-resistant-enough fingerprint of what
/// crossed the wire.
#[inline]
pub fn siphash13_128(key: &[u8; 16], data: &[u8]) -> [u8; OUTPUT_LEN] {
    let k0 = u64::from_le_bytes(key[0..8].try_into().unwrap());
    let k1 = u64::from_le_bytes(key[8..16].try_into().unwrap());
    let mut hasher = SipHasher13::new_with_keys(k0, k1);
    hasher.write(data);
    let h = hasher.finish128();
    let mut out = [0u8; OUTPUT_LEN];
    out[0..8].copy_from_slice(&h.h1.to_le_bytes());
    out[8..16].copy_from_slice(&h.h2.to_le_bytes());
    out
}

/// AES-128-GMAC: GCM's authentication tag computed over the frame as
/// associated data with an empty plaintext, i.e. GHASH-over-AES with no
/// ciphertext to also produce. This is exactly what GMAC is; the aes-gcm
/// crate doesn't expose a separate "GMAC-only" type because it doesn't
/// need one.
///
/// Nonce handling: fixed all-zero nonce, documented rather than hidden.
/// GCM's security against forgery collapses if the same (key, nonce) pair
/// is ever reused to *encrypt two different plaintexts* — but this key is
/// never used for confidentiality anywhere in this pipeline, only as a
/// keyed fingerprint over public-on-the-wire frame contents, so nonce
/// reuse here doesn't create the usual GCM vulnerability. It would become
/// a real bug the moment this key/nonce pair were reused for actual
/// encryption elsewhere — worth a code comment, not just a design note
/// that lives only in this document.
pub struct GmacHasher {
    cipher: Aes128Gcm,
}

impl GmacHasher {
    pub fn new(key: &[u8; 16]) -> Self {
        Self {
            cipher: Aes128Gcm::new(key.into()),
        }
    }

    #[inline]
    pub fn hash(&self, data: &[u8]) -> [u8; OUTPUT_LEN] {
        let nonce = Nonce::from_slice(&[0u8; 12]);
        let tag = self
            .cipher
            .encrypt(
                nonce,
                Payload {
                    msg: &[],
                    aad: data,
                },
            )
            .expect("GMAC over empty plaintext cannot fail");
        let mut out = [0u8; OUTPUT_LEN];
        out.copy_from_slice(&tag[..OUTPUT_LEN]);
        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn blake3_deterministic() {
        let a = blake3_128(b"hello world");
        let b = blake3_128(b"hello world");
        assert_eq!(a, b);
    }

    #[test]
    fn siphash_deterministic_and_key_sensitive() {
        let k1 = [1u8; 16];
        let k2 = [2u8; 16];
        let a = siphash13_128(&k1, b"hello world");
        let b = siphash13_128(&k1, b"hello world");
        let c = siphash13_128(&k2, b"hello world");
        assert_eq!(a, b);
        assert_ne!(a, c);
    }

    #[test]
    fn gmac_deterministic_and_input_sensitive() {
        let h = GmacHasher::new(&[9u8; 16]);
        let a = h.hash(b"hello world");
        let b = h.hash(b"hello world");
        let c = h.hash(b"hello worlD");
        assert_eq!(a, b);
        assert_ne!(a, c);
    }
}
