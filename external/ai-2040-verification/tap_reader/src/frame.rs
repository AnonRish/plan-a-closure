//! Minimal, fixed-offset Ethernet + IPv4 + TCP header parsing.
//!
//! This is deliberately not a general-purpose parser (no VLAN tags, no IP/TCP
//! options, no IPv6). §2's tap only needs to pull the 5-tuple and get to the
//! payload fast; a real deployment would use a proper crate (etherparse,
//! pnet) or, more likely, DPDK's own rte_mbuf offload flags for L3/L4
//! classification instead of parsing in software at all. This exists so the
//! benchmarks below have something realistic to chew on.

pub const ETH_HDR_LEN: usize = 14;
pub const IPV4_HDR_LEN: usize = 20; // no options
pub const TCP_HDR_LEN: usize = 20; // no options
pub const MIN_HDR_LEN: usize = ETH_HDR_LEN + IPV4_HDR_LEN + TCP_HDR_LEN; // 54

#[derive(Debug, Clone, Copy)]
pub struct FiveTuple {
    pub src_ip: [u8; 4],
    pub dst_ip: [u8; 4],
    pub src_port: u16,
    pub dst_port: u16,
    pub protocol: u8,
}

#[derive(Debug)]
pub struct ParsedFrame<'a> {
    pub tuple: FiveTuple,
    pub seq: u32,
    pub payload: &'a [u8],
}

#[derive(Debug, PartialEq, Eq)]
pub enum ParseError {
    TooShort,
    NotIPv4,
    NotTCP,
}

/// Parse Ethernet(no VLAN) + IPv4(no options) + TCP(no options) and return a
/// borrowed view onto the payload. Zero-copy: no allocation, no data movement.
#[inline]
pub fn parse<'a>(raw: &'a [u8]) -> Result<ParsedFrame<'a>, ParseError> {
    if raw.len() < MIN_HDR_LEN {
        return Err(ParseError::TooShort);
    }

    let ethertype = u16::from_be_bytes([raw[12], raw[13]]);
    if ethertype != 0x0800 {
        return Err(ParseError::NotIPv4);
    }

    let ip_off = ETH_HDR_LEN;
    let ihl = (raw[ip_off] & 0x0F) as usize * 4;
    if ihl != IPV4_HDR_LEN {
        // Options present; the real pipeline would handle this, this
        // benchmark harness deliberately doesn't.
        return Err(ParseError::TooShort);
    }
    let protocol = raw[ip_off + 9];
    if protocol != 6 {
        return Err(ParseError::NotTCP);
    }
    let src_ip = [
        raw[ip_off + 12],
        raw[ip_off + 13],
        raw[ip_off + 14],
        raw[ip_off + 15],
    ];
    let dst_ip = [
        raw[ip_off + 16],
        raw[ip_off + 17],
        raw[ip_off + 18],
        raw[ip_off + 19],
    ];

    let tcp_off = ip_off + ihl;
    if raw.len() < tcp_off + TCP_HDR_LEN {
        return Err(ParseError::TooShort);
    }
    let src_port = u16::from_be_bytes([raw[tcp_off], raw[tcp_off + 1]]);
    let dst_port = u16::from_be_bytes([raw[tcp_off + 2], raw[tcp_off + 3]]);
    let seq = u32::from_be_bytes([
        raw[tcp_off + 4],
        raw[tcp_off + 5],
        raw[tcp_off + 6],
        raw[tcp_off + 7],
    ]);
    let data_offset = ((raw[tcp_off + 12] >> 4) & 0x0F) as usize * 4;
    if data_offset != TCP_HDR_LEN {
        return Err(ParseError::TooShort);
    }

    let payload = &raw[tcp_off + TCP_HDR_LEN..];

    Ok(ParsedFrame {
        tuple: FiveTuple {
            src_ip,
            dst_ip,
            src_port,
            dst_port,
            protocol,
        },
        seq,
        payload,
    })
}

/// Build one synthetic, well-formed frame of exactly `total_len` bytes
/// (Ethernet header through end of TCP payload), for benchmarking. Payload
/// bytes are pseudo-random so hash benchmarks aren't measuring an
/// all-zeroes fast path.
pub fn synth_frame(total_len: usize, seq: u32, buf: &mut Vec<u8>) {
    use rand::Rng;
    buf.clear();
    buf.resize(total_len.max(MIN_HDR_LEN), 0);

    // Ethernet: dst/src MAC (arbitrary), EtherType = IPv4
    buf[0..6].copy_from_slice(&[0x02, 0x00, 0x00, 0x00, 0x00, 0x01]);
    buf[6..12].copy_from_slice(&[0x02, 0x00, 0x00, 0x00, 0x00, 0x02]);
    buf[12..14].copy_from_slice(&0x0800u16.to_be_bytes());

    let ip_off = ETH_HDR_LEN;
    let ip_total_len = (buf.len() - ip_off) as u16;
    buf[ip_off] = 0x45; // version 4, IHL 5 (20 bytes, no options)
    buf[ip_off + 1] = 0x00;
    buf[ip_off + 2..ip_off + 4].copy_from_slice(&ip_total_len.to_be_bytes());
    buf[ip_off + 9] = 6; // TCP
    buf[ip_off + 12..ip_off + 16].copy_from_slice(&[10, 0, 0, 1]);
    buf[ip_off + 16..ip_off + 20].copy_from_slice(&[10, 0, 0, 2]);

    let tcp_off = ip_off + IPV4_HDR_LEN;
    buf[tcp_off..tcp_off + 2].copy_from_slice(&8443u16.to_be_bytes()); // src port
    buf[tcp_off + 2..tcp_off + 4].copy_from_slice(&443u16.to_be_bytes()); // dst port
    buf[tcp_off + 4..tcp_off + 8].copy_from_slice(&seq.to_be_bytes());
    buf[tcp_off + 12] = (5u8) << 4; // data offset 5 (20 bytes, no options)

    let payload_off = tcp_off + TCP_HDR_LEN;
    let mut rng = rand::thread_rng();
    rng.fill(&mut buf[payload_off..]);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn roundtrip_realistic_size() {
        let mut buf = Vec::new();
        synth_frame(1500, 42, &mut buf);
        let parsed = parse(&buf).expect("should parse");
        assert_eq!(parsed.seq, 42);
        assert_eq!(parsed.payload.len(), 1500 - MIN_HDR_LEN);
        assert_eq!(parsed.tuple.protocol, 6);
    }

    #[test]
    fn roundtrip_minimum_size() {
        let mut buf = Vec::new();
        synth_frame(64, 7, &mut buf);
        let parsed = parse(&buf).expect("should parse");
        assert_eq!(parsed.payload.len(), 64 - MIN_HDR_LEN);
    }

    #[test]
    fn rejects_too_short() {
        let buf = vec![0u8; 10];
        assert_eq!(parse(&buf).unwrap_err(), ParseError::TooShort);
    }
}
