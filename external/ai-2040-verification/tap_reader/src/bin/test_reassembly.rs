use rand::Rng;
use std::time::Instant;
use tap_reader::reassembly::{encode_chunked_sse, ChunkedDecoder, SseReassembler};

fn main() {
    // --- Correctness, under adversarial-ish random fragmentation ---
    // "Adversarial-ish" because fragment sizes are drawn small (1-9 bytes),
    // which maximizes the chance of splitting exactly on a hex-length
    // boundary, a CRLF, the "data: " prefix, or mid-JSON — the cases a
    // sloppier implementation gets wrong.
    let n_events = 500;
    let events: Vec<String> = (0..n_events)
        .map(|i| format!(r#"{{"id":{i},"token":" tok{i}","logprob":-0.{i:03}}}"#))
        .collect();
    let event_refs: Vec<&[u8]> = events.iter().map(|s| s.as_bytes()).collect();
    let wire = encode_chunked_sse(&event_refs);

    let mut rng = rand::thread_rng();
    let mut all_passed = true;

    for trial in 0..20 {
        let mut chunked = ChunkedDecoder::new();
        let mut sse = SseReassembler::new();
        let mut collected: Vec<Vec<u8>> = Vec::new();

        let mut pos = 0;
        while pos < wire.len() {
            let take = rng.gen_range(1..=9).min(wire.len() - pos);
            let before = chunked.decoded.len();
            chunked.feed(&wire[pos..pos + take]);
            pos += take;
            if chunked.decoded.len() > before {
                let new_bytes = chunked.decoded[before..].to_vec();
                collected.extend(sse.feed(&new_bytes));
            }
        }

        let ok = chunked.is_done()
            && sse.done
            && collected.len() == event_refs.len()
            && collected.iter().zip(event_refs.iter()).all(|(g, w)| g.as_slice() == *w);

        if !ok {
            all_passed = false;
            println!(
                "trial {trial}: FAIL (chunked_done={}, sse_done={}, collected={}, expected={})",
                chunked.is_done(),
                sse.done,
                collected.len(),
                event_refs.len()
            );
        }
    }

    println!(
        "Correctness: {} random-fragmentation trials, 1-9 byte fragments, {} events/trial: {}",
        20,
        n_events,
        if all_passed { "ALL PASSED" } else { "FAILURES ABOVE" }
    );

    // --- Throughput: realistic fragment sizes (TCP segments, not
    // byte-at-a-time), repeated to get a stable measurement ---
    let repeats = 2000;
    let total_wire_bytes = wire.len() * repeats;

    let start = Instant::now();
    let mut total_events = 0usize;
    for _ in 0..repeats {
        let mut chunked = ChunkedDecoder::new();
        let mut sse = SseReassembler::new();
        let mut pos = 0;
        // ~1200-byte fragments: realistic TCP segment payload size, not
        // the adversarial 1-9 byte case above.
        while pos < wire.len() {
            let take = 1200.min(wire.len() - pos);
            let before = chunked.decoded.len();
            chunked.feed(&wire[pos..pos + take]);
            pos += take;
            if chunked.decoded.len() > before {
                let new_bytes = chunked.decoded[before..].to_vec();
                total_events += sse.feed(&new_bytes).len();
            }
        }
    }
    let elapsed = start.elapsed();
    let mb_per_sec = total_wire_bytes as f64 / elapsed.as_secs_f64() / 1_000_000.0;
    let events_per_sec = total_events as f64 / elapsed.as_secs_f64();

    println!();
    println!(
        "Throughput ({repeats} streams x {n_events} events, ~1200B fragments): \
{:.1} MB/s ({:.3} Gbps-equiv), {:.0} events/sec, single core",
        mb_per_sec,
        mb_per_sec * 8.0 / 1000.0,
        events_per_sec
    );

    if !all_passed {
        std::process::exit(1);
    }
}
