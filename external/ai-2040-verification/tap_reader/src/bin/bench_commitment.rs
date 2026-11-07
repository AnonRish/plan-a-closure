use std::time::{Duration, Instant};
use tap_reader::commitment::{verify_inclusion, EpochChain, EpochTree};
use tap_reader::frame::{parse, synth_frame};
use tap_reader::hashing::siphash13_128;

/// The lightest possible per-packet operation for the non-sampled path:
/// parse just enough header to get to the payload, hash it, done. No
/// reassembly, no Evidence struct, no ring-buffer push — those only matter
/// for the sampled fraction (§2/§3's job), not the hash-only commitment
/// path every packet takes.
fn hash_only_throughput(frame_size: usize, duration: Duration, key: &[u8; 16]) -> (u64, u64) {
    let mut buf = Vec::new();
    let mut seq = 0u32;
    let mut frames = 0u64;
    let mut bytes = 0u64;
    let start = Instant::now();
    while start.elapsed() < duration {
        synth_frame(frame_size, seq, &mut buf);
        seq = seq.wrapping_add(1);
        if let Ok(parsed) = parse(&buf) {
            let _ = siphash13_128(key, parsed.payload);
            frames += 1;
            bytes += buf.len() as u64;
        }
    }
    (frames, bytes)
}

fn main() {
    let key = [0x55u8; 16];

    println!("=== Hash-only throughput (no reassembly, no ring push) ===");
    println!("This is the operation every packet takes, not just §3's sampled 1% —");
    println!("so the 64B worst case matters more here than anywhere else in the pipeline.");
    println!();
    println!("{:<10} {:>14} {:>12} {:>12} {:>14}", "frame(B)", "frames/sec", "MB/s", "Gbps-eq", "ns/frame");
    println!("{}", "-".repeat(64));

    let mut ceiling_64b_gbps = 0.0;
    let mut ceiling_1500b_gbps = 0.0;

    for &size in &[64usize, 128, 512, 1500, 9000] {
        let (frames, bytes) = hash_only_throughput(size, Duration::from_millis(600), &key);
        let secs = 0.6;
        let fps = frames as f64 / secs;
        let mbps = bytes as f64 / secs / 1_000_000.0;
        let gbps = mbps * 8.0 / 1000.0;
        if size == 64 {
            ceiling_64b_gbps = gbps;
        }
        if size == 1500 {
            ceiling_1500b_gbps = gbps;
        }
        println!(
            "{:<10} {:>14.0} {:>12.1} {:>12.3} {:>14.1}",
            size, fps, mbps, gbps, secs * 1e9 / frames as f64
        );
    }

    println!();
    println!(
        "For comparison, §2's full pipeline (parse + AES-128-GMAC + ring push) measured \
3.83 Gbps at 64B and 7.35 Gbps at 1500B on this same core. Hash-only here: {:.2} Gbps at 64B \
({:.2}x), {:.2} Gbps at 1500B ({:.2}x). Dropping reassembly/ring-buffer overhead for the \
non-sampled path helps, but doesn't change the order of magnitude — the CPU-bound software \
ceiling is still single-digit-Gbps-per-core either way, which is exactly why this section asks \
for dedicated ASIC/FPGA hashing rather than more of §2's software pipeline.",
        ceiling_64b_gbps,
        ceiling_64b_gbps / 3.83,
        ceiling_1500b_gbps,
        ceiling_1500b_gbps / 7.35
    );

    println!();
    println!("=== Epoch commitment: Merkle tree construction + inclusion proof ===");

    let epoch_size = 1_000_000usize;
    let leaves: Vec<[u8; 16]> = (0..epoch_size as u64)
        .map(|i| siphash13_128(&key, &i.to_le_bytes()))
        .collect();

    let build_start = Instant::now();
    let tree = EpochTree::build(leaves);
    let build_time = build_start.elapsed();

    println!(
        "Built a {}-leaf epoch tree (one epoch = {} packets) in {:.1}ms ({:.0} leaves/sec)",
        epoch_size,
        epoch_size,
        build_time.as_secs_f64() * 1000.0,
        epoch_size as f64 / build_time.as_secs_f64()
    );

    // Prove and verify inclusion for a handful of leaves, timing both
    // sides of that later-verification workflow explicitly.
    let sample_indices = [0usize, 1, epoch_size / 2, epoch_size - 2, epoch_size - 1];
    let proof_start = Instant::now();
    let proofs: Vec<_> = sample_indices.iter().map(|&i| tree.proof(i)).collect();
    let proof_time = proof_start.elapsed();

    let mut all_verified = true;
    let verify_start = Instant::now();
    for (&idx, proof) in sample_indices.iter().zip(proofs.iter()) {
        let ok = verify_inclusion(tree.leaves[idx], idx, proof, tree.root);
        all_verified &= ok;
    }
    let verify_time = verify_start.elapsed();

    println!(
        "{} inclusion proofs generated in {:.1}µs ({} sibling hashes each, log2({})≈{}), \
verified in {:.1}µs. All verified: {}",
        sample_indices.len(),
        proof_time.as_secs_f64() * 1e6,
        proofs[0].len(),
        epoch_size,
        (epoch_size as f64).log2().ceil() as usize,
        verify_time.as_secs_f64() * 1e6,
        all_verified
    );

    // Demonstrate the negative case too: a proof for tampered content must
    // fail, or "verification" isn't actually checking anything.
    let tampered_leaf = [0xEEu8; 16];
    let should_fail = verify_inclusion(tampered_leaf, 0, &proofs[0], tree.root);
    println!(
        "Sanity check — proof against a tampered/wrong leaf: verifies = {} (must be false)",
        should_fail
    );
    assert!(!should_fail, "inclusion proof accepted a tampered leaf — broken");

    // --- Epoch chain: tamper-evidence across epochs, not just within one ---
    println!();
    println!("=== Epoch chain (§21b pattern reused) ===");
    let mut chain = EpochChain::new();
    for e in 0..1000u64 {
        // Cheap stand-in root per epoch for this part of the demo — the
        // real root would be an EpochTree.root as built above.
        chain.commit(e, siphash13_128(&key, &e.to_le_bytes()));
    }
    println!("1000 epochs committed. Chain verifies: {}", chain.verify());
    chain.entries[500].1 = [0xAAu8; 16];
    println!(
        "After tampering with epoch 500's stored root (nothing else touched): chain verifies = {}",
        chain.verify()
    );
}
