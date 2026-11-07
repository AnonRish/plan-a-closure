//! Reconstructing vLLM/OpenAI-style streaming HTTP responses from a tap.
//!
//! The tap sees TCP segments, not HTTP messages — a single SSE event
//! (`data: {"token": "..."}\n\n`) can be split across an arbitrary number of
//! segments at an arbitrary byte offset, including mid-hex-length-line,
//! mid-JSON-token, or mid-CRLF. This has to be a real incremental state
//! machine, not "buffer everything and parse once," because the whole point
//! of the tap is to hand off reconstructed packets to §5 with low added
//! latency — waiting for stream completion before reconstructing anything
//! would defeat that.
//!
//! Two layers, composed: HTTP chunked transfer-encoding, then SSE framing
//! inside the decoded body. vLLM's OpenAI-compatible streaming endpoint
//! uses both.

#[derive(Debug, PartialEq, Eq, Clone, Copy)]
enum ChunkState {
    ReadingSize,
    ReadingData { remaining: usize },
    ReadingDataTrailer,
    Done,
}

/// Incremental HTTP chunked transfer-encoding decoder.
///
/// Everything not-yet-consumed lives in one accumulating buffer (`pending`)
/// with a read cursor, and every state's "do I have enough to make
/// progress" check is against that whole buffer — not just whatever bytes
/// happened to arrive in the current `feed()` call. The first version of
/// this only searched the newly-arrived slice for the size line's CRLF,
/// which is wrong the moment a TCP segment boundary splits the CRLF itself
/// (or splits the size digits from it): a single byte can never contain a
/// 2-byte CRLF, so byte-at-a-time delivery hung forever. The fragmentation
/// tests (`roundtrip_fragmented_at_every_byte_boundary`,
/// `roundtrip_random_fragmentation`) caught this immediately — which is
/// the actual point of writing them.
pub struct ChunkedDecoder {
    state: ChunkState,
    pending: Vec<u8>,
    cursor: usize,
    pub decoded: Vec<u8>,
}

impl ChunkedDecoder {
    pub fn new() -> Self {
        Self {
            state: ChunkState::ReadingSize,
            pending: Vec::new(),
            cursor: 0,
            decoded: Vec::new(),
        }
    }

    pub fn is_done(&self) -> bool {
        self.state == ChunkState::Done
    }

    /// Feed raw bytes as they arrive off the wire, in order, for one
    /// connection. Decoded body bytes accumulate in `self.decoded`; the
    /// caller drains what it wants (the SSE layer below drains per event).
    pub fn feed(&mut self, input: &[u8]) {
        self.pending.extend_from_slice(input);

        loop {
            let buf = &self.pending[self.cursor..];
            match self.state {
                ChunkState::Done => break,
                ChunkState::ReadingSize => {
                    let Some(pos) = find_crlf(buf) else { break };
                    let size_str =
                        std::str::from_utf8(&buf[..pos]).expect("chunk size must be ASCII");
                    // Chunk extensions (";...") aren't used by vLLM's
                    // emitter; strip defensively if present.
                    let size_str = size_str.split(';').next().unwrap_or("0").trim();
                    let size =
                        usize::from_str_radix(size_str, 16).expect("malformed chunk size");
                    self.cursor += pos + 2;
                    self.state = if size == 0 {
                        ChunkState::Done
                    } else {
                        ChunkState::ReadingData { remaining: size }
                    };
                }
                ChunkState::ReadingData { remaining } => {
                    if buf.len() < remaining {
                        // Take what's here, wait for the rest.
                        self.decoded.extend_from_slice(buf);
                        self.cursor += buf.len();
                        self.state = ChunkState::ReadingData {
                            remaining: remaining - buf.len(),
                        };
                        break;
                    }
                    self.decoded.extend_from_slice(&buf[..remaining]);
                    self.cursor += remaining;
                    self.state = ChunkState::ReadingDataTrailer;
                }
                ChunkState::ReadingDataTrailer => {
                    if buf.len() < 2 {
                        break;
                    }
                    self.cursor += 2; // \r\n
                    self.state = ChunkState::ReadingSize;
                }
            }
        }

        // Compact: drop the fully-consumed prefix so `pending` doesn't
        // grow unboundedly over a long-lived stream.
        if self.cursor > 0 {
            self.pending.drain(..self.cursor);
            self.cursor = 0;
        }
    }
}

/// Extracts complete `data: ...\n\n` SSE events from a decoded body stream,
/// as they become available, without waiting for the whole stream.
pub struct SseReassembler {
    buf: Vec<u8>,
    consumed: usize,
    pub done: bool,
}

impl SseReassembler {
    pub fn new() -> Self {
        Self {
            buf: Vec::new(),
            consumed: 0,
            done: false,
        }
    }

    /// Feed newly-decoded body bytes; returns any complete event payloads
    /// (the bytes between `data: ` and the terminating blank line), in
    /// order. `[DONE]` sentinel events are consumed and set `self.done`
    /// rather than being returned.
    pub fn feed(&mut self, decoded: &[u8]) -> Vec<Vec<u8>> {
        self.buf.extend_from_slice(decoded);
        let mut events = Vec::new();

        loop {
            let remaining = &self.buf[self.consumed..];
            let Some(boundary) = find_subslice(remaining, b"\n\n") else {
                break;
            };
            let raw_event = &remaining[..boundary];
            self.consumed += boundary + 2;

            let payload = strip_data_prefix(raw_event);
            if payload == b"[DONE]" {
                self.done = true;
            } else if !payload.is_empty() {
                events.push(payload.to_vec());
            }
        }

        // Compact: drop fully-consumed prefix so the buffer doesn't grow
        // unbounded over a long-lived stream.
        if self.consumed > 0 {
            self.buf.drain(..self.consumed);
            self.consumed = 0;
        }

        events
    }
}

fn strip_data_prefix(raw: &[u8]) -> &[u8] {
    const PREFIX: &[u8] = b"data: ";
    if raw.starts_with(PREFIX) {
        &raw[PREFIX.len()..]
    } else {
        raw
    }
}

fn find_crlf(buf: &[u8]) -> Option<usize> {
    find_subslice(buf, b"\r\n")
}

fn find_subslice(haystack: &[u8], needle: &[u8]) -> Option<usize> {
    if needle.is_empty() || haystack.len() < needle.len() {
        return None;
    }
    haystack.windows(needle.len()).position(|w| w == needle)
}

/// Convenience: build a well-formed chunked+SSE byte stream for a list of
/// event payloads (used to generate synthetic vLLM-style traffic for tests
/// and benchmarks — the inverse of what the reassembler above does).
pub fn encode_chunked_sse(events: &[&[u8]]) -> Vec<u8> {
    let mut out = Vec::new();
    for &ev in events {
        let mut event_bytes = Vec::new();
        event_bytes.extend_from_slice(b"data: ");
        event_bytes.extend_from_slice(ev);
        event_bytes.extend_from_slice(b"\n\n");

        out.extend_from_slice(format!("{:x}\r\n", event_bytes.len()).as_bytes());
        out.extend_from_slice(&event_bytes);
        out.extend_from_slice(b"\r\n");
    }
    // final DONE event + terminating zero-length chunk
    let done = b"data: [DONE]\n\n";
    out.extend_from_slice(format!("{:x}\r\n", done.len()).as_bytes());
    out.extend_from_slice(done);
    out.extend_from_slice(b"\r\n");
    out.extend_from_slice(b"0\r\n\r\n");
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn roundtrip_unfragmented() {
        let events: Vec<&[u8]> = vec![br#"{"token":"Hello"}"#, br#"{"token":" world"}"#];
        let wire = encode_chunked_sse(&events);

        let mut chunked = ChunkedDecoder::new();
        chunked.feed(&wire);
        assert!(chunked.is_done());

        let mut sse = SseReassembler::new();
        let out = sse.feed(&chunked.decoded);
        assert_eq!(out.len(), 2);
        assert_eq!(out[0], events[0]);
        assert_eq!(out[1], events[1]);
        assert!(sse.done);
    }

    #[test]
    fn roundtrip_fragmented_at_every_byte_boundary() {
        // The actual property that matters: reconstruction is correct no
        // matter where TCP happened to cut the stream. Test every single
        // possible one-byte-at-a-time delivery, which subsumes all coarser
        // fragmentations for correctness purposes (if it survives being
        // fed one byte at a time, it survives any grouping of those bytes).
        let events: Vec<&[u8]> = vec![
            br#"{"token":"The"}"#,
            br#"{"token":" quick"}"#,
            br#"{"token":" brown"}"#,
            br#"{"token":" fox"}"#,
        ];
        let wire = encode_chunked_sse(&events);

        let mut chunked = ChunkedDecoder::new();
        let mut sse = SseReassembler::new();
        let mut collected = Vec::new();

        for byte in wire.iter() {
            let before = chunked.decoded.len();
            chunked.feed(std::slice::from_ref(byte));
            if chunked.decoded.len() > before {
                let new_bytes = chunked.decoded[before..].to_vec();
                collected.extend(sse.feed(&new_bytes));
            }
        }

        assert!(chunked.is_done());
        assert!(sse.done);
        assert_eq!(collected.len(), events.len());
        for (got, want) in collected.iter().zip(events.iter()) {
            assert_eq!(got.as_slice(), *want);
        }
    }

    #[test]
    fn roundtrip_random_fragmentation() {
        use rand::Rng;
        let mut rng = rand::thread_rng();
        let events: Vec<String> = (0..50)
            .map(|i| format!(r#"{{"token":" tok{i}","logprob":-0.{i}}}"#))
            .collect();
        let event_refs: Vec<&[u8]> = events.iter().map(|s| s.as_bytes()).collect();
        let wire = encode_chunked_sse(&event_refs);

        let mut chunked = ChunkedDecoder::new();
        let mut sse = SseReassembler::new();
        let mut collected = Vec::new();

        let mut pos = 0;
        while pos < wire.len() {
            let take = rng.gen_range(1..=7).min(wire.len() - pos);
            let before = chunked.decoded.len();
            chunked.feed(&wire[pos..pos + take]);
            pos += take;
            if chunked.decoded.len() > before {
                let new_bytes = chunked.decoded[before..].to_vec();
                collected.extend(sse.feed(&new_bytes));
            }
        }

        assert_eq!(collected.len(), event_refs.len());
        for (got, want) in collected.iter().zip(event_refs.iter()) {
            assert_eq!(got.as_slice(), *want);
        }
    }
}
