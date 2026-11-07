use std::hint::black_box;
use std::time::{Duration, Instant};
use tap_reader::hashing::{blake3_128, siphash13_128, GmacHasher};

struct BenchResult {
    name: &'static str,
    size: usize,
    ops_per_sec: f64,
    mb_per_sec: f64,
    ns_per_op: f64,
}

fn bench<F: FnMut(&[u8]) -> [u8; 16]>(name: &'static str, size: usize, mut f: F, min_time: Duration) -> BenchResult {
    let data = vec![0xABu8; size];

    // Warm-up: let branch predictors / caches settle, and let the loop run
    // long enough that measurement overhead is negligible relative to work.
    for _ in 0..1000 {
        black_box(f(black_box(&data)));
    }

    let mut iters: u64 = 0;
    let start = Instant::now();
    loop {
        for _ in 0..1000 {
            black_box(f(black_box(&data)));
        }
        iters += 1000;
        if start.elapsed() >= min_time {
            break;
        }
    }
    let elapsed = start.elapsed();
    let ops_per_sec = iters as f64 / elapsed.as_secs_f64();
    let mb_per_sec = ops_per_sec * size as f64 / 1_000_000.0;
    let ns_per_op = elapsed.as_nanos() as f64 / iters as f64;

    BenchResult {
        name,
        size,
        ops_per_sec,
        mb_per_sec,
        ns_per_op,
    }
}

fn main() {
    println!("Single-core hash throughput. CPU: {}", cpu_model());
    println!(
        "{:<22} {:>10} {:>14} {:>12} {:>12} {:>12}",
        "hash", "size(B)", "ops/sec", "MB/s", "ns/op", "Gbps-equiv"
    );
    println!("{}", "-".repeat(88));

    let sizes = [10usize, 46, 1446, 8946]; // 64B/100B/1500B/9000B frames minus 54B headers
    let gmac_key = [0x11u8; 16];
    let gmac = GmacHasher::new(&gmac_key);
    let sip_key = [0x22u8; 16];

    let mut results = Vec::new();
    for &size in &sizes {
        results.push(bench("BLAKE3-128", size, |d| blake3_128(d), Duration::from_millis(500)));
        results.push(bench(
            "SipHash-1-3-128",
            size,
            |d| siphash13_128(&sip_key, d),
            Duration::from_millis(500),
        ));
        results.push(bench("AES-128-GMAC", size, |d| gmac.hash(d), Duration::from_millis(500)));
    }

    for r in &results {
        let gbps = r.mb_per_sec * 8.0 / 1000.0;
        println!(
            "{:<22} {:>10} {:>14.0} {:>12.1} {:>12.1} {:>12.3}",
            r.name, r.size, r.ops_per_sec, r.mb_per_sec, r.ns_per_op, gbps
        );
    }

    println!();
    println!("Relative to BLAKE3-128 at each size (>1.0x = faster than BLAKE3):");
    for &size in &sizes {
        let base = results.iter().find(|r| r.size == size && r.name == "BLAKE3-128").unwrap();
        for r in results.iter().filter(|r| r.size == size) {
            println!(
                "  {:>6}B  {:<18} {:>6.2}x",
                size,
                r.name,
                r.ops_per_sec / base.ops_per_sec
            );
        }
    }
}

fn cpu_model() -> String {
    std::fs::read_to_string("/proc/cpuinfo")
        .ok()
        .and_then(|s| {
            s.lines()
                .find(|l| l.starts_with("model name"))
                .map(|l| l.split(':').nth(1).unwrap_or("unknown").trim().to_string())
        })
        .unwrap_or_else(|| "unknown".to_string())
}
