use std::time::{Duration, Instant};
use tap_reader::frame::{parse, synth_frame};
use tap_reader::hashing::GmacHasher;
use tap_reader::ring::{new_queue, Evidence};

/// One worker's full per-frame path: parse headers, hash payload, push
/// evidence to the ring. This is what a DPDK RX-queue-pinned worker thread
/// would do per packet in the real design; here it runs against
/// synthetic frames already in memory, isolating the CPU-bound cost of
/// software processing from anything NIC/DMA/PCIe related, which this
/// sandbox has no way to exercise.
fn run_worker(frame_size: usize, duration: Duration, gmac_key: [u8; 16]) -> (u64, u64) {
    let gmac = GmacHasher::new(&gmac_key);
    let queue = new_queue(4096);
    let mut buf = Vec::new();
    let mut seq: u32 = 0;
    let mut frames_done: u64 = 0;
    let mut bytes_done: u64 = 0;

    let start = Instant::now();
    while start.elapsed() < duration {
        synth_frame(frame_size, seq, &mut buf);
        seq = seq.wrapping_add(1);

        let parsed = match parse(&buf) {
            Ok(p) => p,
            Err(_) => continue,
        };
        let hash = gmac.hash(parsed.payload);
        let ev = Evidence {
            seq: parsed.seq,
            src_ip: parsed.tuple.src_ip,
            dst_ip: parsed.tuple.dst_ip,
            src_port: parsed.tuple.src_port,
            dst_port: parsed.tuple.dst_port,
            payload_len: parsed.payload.len() as u16,
            payload_hash: hash,
        };
        // Drain immediately so the bounded queue never blocks this
        // single-threaded benchmark; a real deployment has a separate
        // consumer thread doing this, exercised by bench_ring instead.
        if queue.push(ev).is_err() {
            let _ = queue.pop();
            let _ = queue.push(ev);
        }
        let _ = queue.pop();

        frames_done += 1;
        bytes_done += buf.len() as u64;
    }

    (frames_done, bytes_done)
}

fn main() {
    println!("End-to-end parse + AES-128-GMAC hash + ring push, single core.");
    println!("This measures the software processing ceiling only — no NIC, no DMA, no PCIe,");
    println!("no RSS hashing in hardware. Real DPDK-off-a-NIC throughput additionally depends");
    println!("on all of those, none of which this sandbox has.");
    println!();

    let gmac_key = [0x33u8; 16];
    let run_time = Duration::from_millis(800);

    println!(
        "{:<12} {:>14} {:>14} {:>12} {:>14}",
        "frame(B)", "frames/sec", "MB/s", "Gbps-equiv", "ns/frame"
    );
    println!("{}", "-".repeat(70));

    for &frame_size in &[64usize, 128, 512, 1500, 9000] {
        let (frames, bytes) = run_worker(frame_size, run_time, gmac_key);
        let secs = run_time.as_secs_f64();
        let fps = frames as f64 / secs;
        let mbps = bytes as f64 / secs / 1_000_000.0;
        let gbps = mbps * 8.0 / 1000.0;
        let ns_per_frame = secs * 1e9 / frames as f64;
        println!(
            "{:<12} {:>14.0} {:>14.1} {:>12.3} {:>14.1}",
            frame_size, fps, mbps, gbps, ns_per_frame
        );
    }

    println!();
    println!(
        "Logical CPUs available in this container: {}",
        std::thread::available_parallelism().map(|n| n.get()).unwrap_or(1)
    );
}
