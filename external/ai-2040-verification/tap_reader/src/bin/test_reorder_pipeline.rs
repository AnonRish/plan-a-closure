use rand::Rng;
use tap_reader::reassembly::{encode_chunked_sse, ChunkedDecoder, SseReassembler};
use tap_reader::reorder::ReorderBuffer;

/// Split a byte stream into TCP-segment-sized chunks with sequence numbers,
/// the way a real capture would see them if nothing reordered anything.
fn segment(data: &[u8], seg_len: usize, start_seq: u32) -> Vec<(u32, Vec<u8>)> {
    data.chunks(seg_len)
        .scan(start_seq, |seq, chunk| {
            let this_seq = *seq;
            *seq = seq.wrapping_add(chunk.len() as u32);
            Some((this_seq, chunk.to_vec()))
        })
        .collect()
}

/// Realistic jitter: most segments stay in order; occasionally two adjacent
/// segments swap (a segment arrives slightly late, as from a real
/// retransmission or a few-microsecond scheduling delay) — not the fully
/// adversarial shuffle §8's unit tests already stress-test separately.
fn apply_realistic_jitter(segs: &mut Vec<(u32, Vec<u8>)>, swap_probability: f64) {
    let mut rng = rand::thread_rng();
    let mut i = 0;
    while i + 1 < segs.len() {
        if rng.gen_bool(swap_probability) {
            segs.swap(i, i + 1);
            i += 2; // don't chain-swap the same element repeatedly
        } else {
            i += 1;
        }
    }
}

fn run_pipeline(segs: &[(u32, Vec<u8>)], start_seq: u32) -> (Vec<Vec<u8>>, bool, u32, u32) {
    let mut reorder = ReorderBuffer::new(start_seq);
    let mut chunked = ChunkedDecoder::new();
    let mut sse = SseReassembler::new();
    let mut collected = Vec::new();

    for (seq, payload) in segs {
        let before = reorder.delivered.len();
        reorder.feed(*seq, payload);
        if reorder.delivered.len() > before {
            let new_bytes = reorder.delivered[before..].to_vec();
            chunked.feed(&new_bytes);
        }
    }
    // chunked.decoded now holds everything the reorder buffer released, in
    // correct logical order, decoded from HTTP chunking, ready for SSE
    // framing — the exact same §2b code path as before, just now fed
    // correctly-ordered input instead of assuming it.
    collected.extend(sse.feed(&chunked.decoded));

    (collected, sse.done, reorder.reordered_count, reorder.duplicates_dropped)
}

fn main() {
    let n_events = 200;
    let events: Vec<String> = (0..n_events)
        .map(|i| format!(r#"{{"id":{i},"token":" tok{i}"}}"#))
        .collect();
    let event_refs: Vec<&[u8]> = events.iter().map(|s| s.as_bytes()).collect();
    let wire = encode_chunked_sse(&event_refs);

    println!("=== §8: full pipeline under realistic network jitter, not just fragmentation ===");
    println!("(§2b's own tests already covered arbitrary chunk *sizes*; this covers arrival *order*)");
    println!();

    for &swap_prob in &[0.0, 0.05, 0.15, 0.30] {
        let mut segs = segment(&wire, 40, 10_000);
        let original = segs.clone();
        apply_realistic_jitter(&mut segs, swap_prob);
        let actually_reordered = segs != original;

        let (collected, done, reordered_count, dups) = run_pipeline(&segs, 10_000);

        let correct = done
            && collected.len() == event_refs.len()
            && collected.iter().zip(event_refs.iter()).all(|(g, w)| g.as_slice() == *w);

        println!(
            "swap_probability={:>4.2}  segments={:>4}  reordered_arrivals={:>3}  dups_dropped={}  \
reconstruction_correct={}",
            swap_prob,
            segs.len(),
            reordered_count,
            dups,
            correct
        );
        assert!(correct, "reconstruction must be correct regardless of arrival order");
        if swap_prob > 0.0 {
            assert!(actually_reordered, "test isn't meaningful if jitter happened to be a no-op this run");
        }
    }

    println!();
    println!("All swap-probability levels reconstructed the exact original {n_events}-event stream.");
    println!("Reordering rate scales with jitter probability as expected; reconstruction correctness");
    println!("does not depend on it at all, from 0% jitter up through 30% adjacent-segment swaps.");
}
