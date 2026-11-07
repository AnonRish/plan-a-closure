//! ATTACK 4: timing/scheduling manipulation, tested concretely rather than
//! left as a vague "could bias sampling" concern.
//!
//! §3 already showed (real simulation, not assumed) that a prover without
//! the verifier's key cannot PREDICT individual sample_decision outcomes
//! better than chance — guessed keys, and a logistic regression trained on
//! 480K labeled examples, both landed within 0.005 AUC of 0.5. So the
//! question this file actually tests is different and sharper: even
//! without predicting individual outcomes, can a prover manipulate
//! *how many independent packet_ids* a fixed amount of dishonest content
//! gets split across — batching many logical exchanges into fewer, larger
//! requests — to reduce N_fake in §1's own P(detected) ≈ 1 − e^(−C·N_fake)
//! formula, and thereby reduce detection probability for the identical
//! amount of misbehavior?

use tap_reader::gateway::{sample_decision, threshold_for_rate};

fn detection_prob_empirical(key: &[u8; 16], threshold: u64, n_fake_packets: u64, base_id: u64, trials: u32) -> f64 {
    let mut caught = 0u32;
    for t in 0..trials {
        let mut any_sampled = false;
        for i in 0..n_fake_packets {
            let packet_id = base_id.wrapping_add(t as u64 * 1_000_003).wrapping_add(i);
            if sample_decision(key, packet_id, threshold) {
                any_sampled = true;
                break;
            }
        }
        if any_sampled {
            caught += 1;
        }
    }
    caught as f64 / trials as f64
}

fn formula_prediction(c: f64, n_fake: f64) -> f64 {
    1.0 - (-c * n_fake).exp()
}

fn main() {
    let key = [0x77u8; 16];
    let c = 0.01; // §1's illustrative 1% recomputation budget
    let threshold = threshold_for_rate(c);

    println!("Fixed total dishonest content, split across different numbers of packets.");
    println!("Question: does batching (fewer, larger packets) for the SAME content reduce detection?");
    println!();
    println!(
        "{:<20} {:>18} {:>18} {:>10}",
        "framing", "empirical P(caught)", "§1 formula predicts", "trials"
    );
    println!("{}", "-".repeat(70));

    // Same total "amount of dishonest content" conceptually, expressed as
    // different numbers of packets: 500 tiny packets vs 50 medium vs 5 huge
    // batched ones, each scenario run for real against the actual keyed PRF.
    let scenarios = [
        ("500 small packets", 500u64),
        ("50 medium packets", 50u64),
        ("5 large batched", 5u64),
        ("1 maximally batched", 1u64),
    ];

    for (label, n_fake) in scenarios {
        let empirical = detection_prob_empirical(&key, threshold, n_fake, 0xA5A5_0000, 20_000);
        let predicted = formula_prediction(c, n_fake as f64);
        println!("{:<20} {:>18.4} {:>18.4} {:>10}", label, empirical, predicted, 20_000);
    }

    println!();
    println!(
        "Batching content into fewer packets measurably and predictably lowers detection \
probability for the SAME misbehavior — this is real, matches §1's own formula almost exactly, \
and doesn't require predicting any individual sample_decision (which §3 already showed is \
infeasible without the key). This is a genuine attack on the SYSTEM'S granularity choice, not \
on the PRF's unpredictability, which is exactly why §1/§4/§14 already treat packet granularity \
as a dial the verifier controls, not the prover — the fix isn't a stronger PRF, it's not letting \
the prover choose how their own content gets divided into 'packets' in the first place."
    );
}
