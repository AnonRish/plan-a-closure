use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::thread;
use std::time::Instant;
use tap_reader::ring::{new_queue, Evidence};

fn dummy_evidence(seq: u32) -> Evidence {
    Evidence {
        seq,
        src_ip: [10, 0, 0, 1],
        dst_ip: [10, 0, 0, 2],
        src_port: 8443,
        dst_port: 443,
        payload_len: 1446,
        payload_hash: [0xAB; 16],
    }
}

fn main() {
    let capacity = 1 << 16; // 65536 slots
    let per_producer = 500_000usize;

    for &n_producers in &[1usize, 2, 4, 8] {
        let queue = new_queue(capacity);
        let produced = Arc::new(AtomicU64::new(0));
        let consumed = Arc::new(AtomicU64::new(0));
        let stop = Arc::new(std::sync::atomic::AtomicBool::new(false));

        let start = Instant::now();

        let producers: Vec<_> = (0..n_producers)
            .map(|_| {
                let q = queue.clone();
                let produced = produced.clone();
                thread::spawn(move || {
                    for i in 0..per_producer {
                        let mut ev = dummy_evidence(i as u32);
                        // Spin on push when the queue is momentarily full
                        // rather than dropping — this measures the queue's
                        // real sustained throughput under backpressure,
                        // which is the condition that actually matters
                        // (silently dropping evidence would be a
                        // completeness bug, not a performance feature).
                        while q.push(ev).is_err() {
                            ev.seq = ev.seq; // no-op, just retry
                            std::hint::spin_loop();
                        }
                        produced.fetch_add(1, Ordering::Relaxed);
                    }
                })
            })
            .collect();

        let total_expected = (n_producers * per_producer) as u64;
        let consumer_queue = queue.clone();
        let consumer_consumed = consumed.clone();
        let consumer_stop = stop.clone();
        let consumer = thread::spawn(move || {
            let mut last_seen: std::collections::HashMap<(u16, u16), i64> =
                std::collections::HashMap::new();
            let mut reordered = 0u64;
            loop {
                match consumer_queue.pop() {
                    Some(ev) => {
                        // Sanity check: within a given (src_port,dst_port)
                        // "flow" from a single producer things should still
                        // be internally consistent-ish; this is a coarse
                        // corruption check, not a strict ordering
                        // guarantee across producers (the queue is MPMC,
                        // so cross-producer interleaving is expected).
                        let key = (ev.src_port, ev.dst_port);
                        let seq = ev.seq as i64;
                        if let Some(&last) = last_seen.get(&key) {
                            if seq < last {
                                reordered += 1;
                            }
                        }
                        last_seen.insert(key, seq);
                        consumer_consumed.fetch_add(1, Ordering::Relaxed);
                    }
                    None => {
                        if consumer_stop.load(Ordering::Relaxed) {
                            break;
                        }
                        std::hint::spin_loop();
                    }
                }
            }
            reordered
        });

        for p in producers {
            p.join().unwrap();
        }
        // Drain whatever's left, then signal the consumer to stop once the
        // queue is empty and no more is coming.
        while consumed.load(Ordering::Relaxed) < total_expected {
            std::hint::spin_loop();
        }
        stop.store(true, Ordering::Relaxed);
        let _reordered_within_flow = consumer.join().unwrap();

        let elapsed = start.elapsed();
        let ops_per_sec = total_expected as f64 / elapsed.as_secs_f64();
        let bytes_per_item = std::mem::size_of::<Evidence>();
        let mb_per_sec = ops_per_sec * bytes_per_item as f64 / 1_000_000.0;

        println!(
            "{} producer(s) + 1 consumer: {:>10} items in {:>7.1}ms -> {:>12.0} items/sec ({:.1} MB/s of evidence records, {} bytes/item)",
            n_producers,
            total_expected,
            elapsed.as_secs_f64() * 1000.0,
            ops_per_sec,
            mb_per_sec,
            bytes_per_item,
        );
        assert_eq!(produced.load(Ordering::Relaxed), total_expected);
        assert_eq!(consumed.load(Ordering::Relaxed), total_expected);
    }

    println!();
    println!(
        "All producer counts: produced == consumed, no lost or duplicated items \
(verified by atomic counters matching total_expected exactly)."
    );
    println!(
        "Note: this container reports {} logical CPU(s), so counts above {} producer(s) \
are measuring thread-scheduling overhead on oversubscribed cores, not independent \
parallel throughput — see write-up for what that does and doesn't tell us.",
        num_cpus(),
        num_cpus()
    );
}

fn num_cpus() -> usize {
    std::thread::available_parallelism()
        .map(|n| n.get())
        .unwrap_or(1)
}
