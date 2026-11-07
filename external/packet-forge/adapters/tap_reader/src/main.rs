//! Feeds packet-forge corpus captures through tap_reader's real frame parser and ReorderBuffer.
//!
//! stdin, one line per case:  `<case-id> <pcap-path> <initial-seq> <mode>`
//!   mode `asis` feeds exactly what `frame::parse` returns as the payload;
//!   mode `trim` first cuts the payload to the IPv4 total length (drops Ethernet padding) and skips
//!   empty payloads, so that only `ReorderBuffer`'s own behaviour is being measured.
//! stdout, one line per case: `RESULT <id> <mode> <delivered-hex|-> <duplicates_dropped> <reordered_count> <gap_open> <parsed> <rejected>`
//!
//! Only client->server frames (destination port 80) are fed, exactly as a tap that follows one
//! direction of one flow would.  Nothing here changes tap_reader's behaviour.

use std::fs;
use std::io::{self, BufRead};

use tap_reader::frame;
use tap_reader::reorder::ReorderBuffer;

const SERVER_PORT: u16 = 80;

fn read_pcap(path: &str) -> Vec<Vec<u8>> {
    let b = fs::read(path).expect("read pcap");
    assert!(b.len() >= 24, "short pcap");
    let magic = u32::from_le_bytes([b[0], b[1], b[2], b[3]]);
    assert!(magic == 0xa1b2c3d4 || magic == 0xa1b23c4d, "adapter reads little-endian classic pcap");
    let mut off = 24;
    let mut out = Vec::new();
    while off + 16 <= b.len() {
        let incl = u32::from_le_bytes([b[off + 8], b[off + 9], b[off + 10], b[off + 11]]) as usize;
        off += 16;
        out.push(b[off..off + incl].to_vec());
        off += incl;
    }
    out
}

fn hex(b: &[u8]) -> String {
    if b.is_empty() {
        return "-".to_string();
    }
    b.iter().map(|x| format!("{:02x}", x)).collect()
}

fn main() {
    let stdin = io::stdin();
    for line in stdin.lock().lines() {
        let line = line.unwrap();
        let mut it = line.split_whitespace();
        let (id, path, init, mode) = match (it.next(), it.next(), it.next(), it.next()) {
            (Some(a), Some(b), Some(c), Some(m)) => (a, b, c.parse::<u32>().expect("initial seq"), m),
            _ => continue,
        };
        let trim = mode == "trim";
        let mut buf = ReorderBuffer::new(init);
        let (mut parsed, mut rejected) = (0u32, 0u32);
        for raw in read_pcap(path) {
            match frame::parse(&raw) {
                Ok(p) if p.tuple.dst_port == SERVER_PORT => {
                    parsed += 1;
                    let mut payload = p.payload;
                    if trim {
                        let ip_total = u16::from_be_bytes([raw[16], raw[17]]) as usize;
                        let real = (14 + ip_total).saturating_sub(frame::MIN_HDR_LEN);
                        payload = &payload[..real.min(payload.len())];
                        if payload.is_empty() {
                            continue;
                        }
                    }
                    buf.feed(p.seq, payload);
                }
                Ok(_) => {}
                Err(_) => rejected += 1,
            }
        }
        println!(
            "RESULT {} {} {} {} {} {} {} {}",
            id,
            mode,
            hex(&buf.delivered),
            buf.duplicates_dropped,
            buf.reordered_count,
            buf.gap_open(),
            parsed,
            rejected
        );
    }
}
