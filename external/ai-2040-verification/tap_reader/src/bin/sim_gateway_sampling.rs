//! §3's self-check, demonstrated rather than asserted: can a prover predict
//! the gateway's sampling decisions better than chance without the
//! verifier's key?
//!
//! Four attackers, weakest to strongest, all working from nothing but
//! packet IDs and (for the learning attacker) past ground-truth labels —
//! never the key itself:
//!   A. Majority-class baseline (always guess "not sampled").
//!   B. Weak/guessable-key attack: try keys derived from public-ish
//!      information (all-zero, small sequential integers, a fake MAC
//!      address) and see if any of them correlate with the real decisions.
//!   C. Logistic regression on the packet ID's raw bits, trained on 80% of
//!      a large labeled set and evaluated on a held-out 20% — the "best
//!      statistical effort without the key" attack.
//!   D. Oracle with the *correct* key, included as a contrast/upper bound
//!      to show where the security actually comes from (key secrecy, not
//!      algorithm secrecy).
//!
//! Success metric is AUC, not accuracy — at a 1% sampling rate, "always
//! guess not-sampled" gets 99% accuracy while carrying zero information,
//! which is exactly the trap a less careful evaluation would fall into.
//! AUC = 0.5 is the no-information baseline regardless of class balance.

use rand::Rng;
use tap_reader::gateway::{sample_decision, threshold_for_rate};

fn auc(scores_labels: &mut Vec<(f64, bool)>) -> f64 {
    // Rank-sum (Mann-Whitney U) AUC. Sort ascending by score; average ranks
    // across ties.
    scores_labels.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap());
    let n = scores_labels.len();
    let mut ranks = vec![0.0f64; n];
    let mut i = 0;
    while i < n {
        let mut j = i;
        while j + 1 < n && scores_labels[j + 1].0 == scores_labels[i].0 {
            j += 1;
        }
        // ranks are 1-indexed; average rank for the tied block [i, j]
        let avg_rank = ((i + 1) + (j + 1)) as f64 / 2.0;
        for r in ranks.iter_mut().take(j + 1).skip(i) {
            *r = avg_rank;
        }
        i = j + 1;
    }
    let n_pos = scores_labels.iter().filter(|(_, l)| *l).count() as f64;
    let n_neg = n as f64 - n_pos;
    if n_pos == 0.0 || n_neg == 0.0 {
        return 0.5; // undefined; treat as no-information
    }
    let rank_sum_pos: f64 = ranks
        .iter()
        .zip(scores_labels.iter())
        .filter(|(_, (_, l))| *l)
        .map(|(r, _)| r)
        .sum();
    (rank_sum_pos - n_pos * (n_pos + 1.0) / 2.0) / (n_pos * n_neg)
}

fn bits(id: u64) -> [f64; 64] {
    let mut f = [0.0f64; 64];
    for (b, slot) in f.iter_mut().enumerate() {
        *slot = ((id >> b) & 1) as f64;
    }
    f
}

/// Full-batch logistic regression by gradient descent. Returns predicted
/// scores (post-sigmoid probability) for `test_ids`.
fn logistic_regression_attack(
    train_ids: &[u64],
    train_labels: &[bool],
    test_ids: &[u64],
    epochs: usize,
    lr: f64,
) -> Vec<f64> {
    let d = 64;
    let mut w = vec![0.0f64; d];
    let mut b = 0.0f64;
    let n = train_ids.len() as f64;

    let train_feats: Vec<[f64; 64]> = train_ids.iter().map(|&id| bits(id)).collect();

    for _ in 0..epochs {
        let mut grad_w = vec![0.0f64; d];
        let mut grad_b = 0.0f64;
        for (feat, &label) in train_feats.iter().zip(train_labels.iter()) {
            let z: f64 = feat.iter().zip(w.iter()).map(|(x, wi)| x * wi).sum::<f64>() + b;
            let p = 1.0 / (1.0 + (-z).exp());
            let y = if label { 1.0 } else { 0.0 };
            let err = p - y;
            for k in 0..d {
                grad_w[k] += err * feat[k];
            }
            grad_b += err;
        }
        for k in 0..d {
            w[k] -= lr * grad_w[k] / n;
        }
        b -= lr * grad_b / n;
    }

    test_ids
        .iter()
        .map(|&id| {
            let feat = bits(id);
            let z: f64 = feat.iter().zip(w.iter()).map(|(x, wi)| x * wi).sum::<f64>() + b;
            1.0 / (1.0 + (-z).exp())
        })
        .collect()
}

fn main() {
    let real_key: [u8; 16] = {
        let mut k = [0u8; 16];
        rand::thread_rng().fill(&mut k);
        k
    };
    let c = 0.01; // §1's illustrative 1% recomputation budget
    let threshold = threshold_for_rate(c);

    let n_total = 600_000u64;
    let ids: Vec<u64> = (0..n_total).collect(); // sequential — the most
                                                 // structured, easiest-to-attack ID
                                                 // space available, deliberately not
                                                 // randomized, to give every attacker
                                                 // below the best possible chance of
                                                 // finding a pattern if one existed.
    let labels: Vec<bool> = ids.iter().map(|&i| sample_decision(&real_key, i, threshold)).collect();

    let n_sampled = labels.iter().filter(|&&l| l).count();
    println!(
        "Ground truth: {n_sampled} / {n_total} packets sampled ({:.3}% — target was {:.1}%)",
        100.0 * n_sampled as f64 / n_total as f64,
        100.0 * c
    );
    println!();

    // --- A. Majority baseline ---
    let majority_acc = 1.0 - (n_sampled as f64 / n_total as f64);
    println!(
        "A. Majority-class baseline: {:.2}% accuracy, AUC = 0.5000 (by construction — a \
constant predictor carries no information regardless of how good its accuracy looks)",
        majority_acc * 100.0
    );

    // --- B. Weak/guessable-key attack ---
    let mut guessed_keys: Vec<[u8; 16]> = vec![
        [0u8; 16],
        [0xFFu8; 16],
        [1u8; 16],
    ];
    for k in 0u8..20 {
        let mut key = [0u8; 16];
        key[0] = k;
        guessed_keys.push(key);
    }
    // A "fake MAC address"-derived guess, simulating a prover trying
    // plausible device-identity-derived keys.
    guessed_keys.push([0x02, 0x00, 0x00, 0x00, 0x00, 0x01, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]);

    let mut best_weak_auc = 0.5f64;
    let mut best_weak_desc = String::new();
    // Sample a manageable subset for this scan; the point is whether *any*
    // guessable key correlates, not high-precision AUC on all 600k rows.
    let eval_n = 50_000usize;
    for guess in &guessed_keys {
        let mut sl: Vec<(f64, bool)> = (0..eval_n)
            .map(|i| {
                let id = ids[i];
                let score = if sample_decision(guess, id, threshold) { 1.0 } else { 0.0 };
                (score, labels[i])
            })
            .collect();
        let a = auc(&mut sl);
        let dist_from_chance = (a - 0.5).abs();
        if dist_from_chance > (best_weak_auc - 0.5).abs() {
            best_weak_auc = a;
            best_weak_desc = format!("{:02x?}", &guess[..4]);
        }
    }
    println!(
        "B. Best of {} guessed/weak keys: AUC = {:.4} (key prefix {}) — \
{:.4} away from the 0.5 no-information line",
        guessed_keys.len(),
        best_weak_auc,
        best_weak_desc,
        (best_weak_auc - 0.5).abs()
    );

    // --- C. Logistic regression on packet-ID bits ---
    let split = (n_total as f64 * 0.8) as usize;
    let (train_ids, test_ids) = ids.split_at(split);
    let (train_labels, test_labels) = labels.split_at(split);

    let scores = logistic_regression_attack(train_ids, train_labels, test_ids, 60, 0.5);
    let mut sl: Vec<(f64, bool)> = scores.iter().cloned().zip(test_labels.iter().cloned()).collect();
    let lr_auc = auc(&mut sl);
    println!(
        "C. Logistic regression on packet-ID bits, {} train / {} test: AUC = {:.4}",
        train_ids.len(),
        test_ids.len(),
        lr_auc
    );

    // --- D. Oracle with the correct key (contrast, not an attack) ---
    let mut sl: Vec<(f64, bool)> = (0..eval_n)
        .map(|i| {
            let id = ids[i];
            let score = if sample_decision(&real_key, id, threshold) { 1.0 } else { 0.0 };
            (score, labels[i])
        })
        .collect();
    let oracle_auc = auc(&mut sl);
    println!(
        "D. Oracle WITH the correct key (not an attacker — shows where the security actually \
comes from): AUC = {:.4}",
        oracle_auc
    );

    println!();
    let no_key_max_deviation = [
        (best_weak_auc - 0.5).abs(),
        (lr_auc - 0.5).abs(),
    ]
    .into_iter()
    .fold(0.0f64, f64::max);

    if no_key_max_deviation < 0.02 {
        println!(
            "RESULT: every attacker without the key stayed within {:.4} of AUC 0.5 (no \
information). Only the oracle with the correct key (AUC {:.4}) predicts better than chance. \
The security property holds in this simulation: it comes entirely from key secrecy, not \
algorithm secrecy — which is exactly the property a keyed PRF is supposed to have, demonstrated \
rather than assumed.",
            no_key_max_deviation, oracle_auc
        );
    } else {
        println!(
            "RESULT: an attacker without the key achieved AUC deviation {:.4} from 0.5 — \
investigate before trusting this construction.",
            no_key_max_deviation
        );
        std::process::exit(1);
    }
}
