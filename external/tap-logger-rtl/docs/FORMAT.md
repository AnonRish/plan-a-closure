# Log format

All integers are big-endian. A *frame* is the byte string presented on the stream interface, first byte first,
at least one byte long (the Ethernet frame without preamble and FCS if that is what the MAC hands over).

```
D(-1) = GENESIS                       32 bytes, default 00..00 (module parameter)
D(i)  = SHA-256( D(i-1)               32 bytes
               || be64(i)             frame index, starting at 0; restarts at 0 after reset
               || be64(ts_i)          only when TS_EN = 1; sampled when the frame's first byte is presented
               || frame_i )
```

A log record is `(index, length, ts, digest = D(index))`. With `TS_EN = 0` the `log_ts` output is 0 and is
not authenticated.

What the chain gives a verifier who holds the frames and one trusted chain head:

* any altered, inserted, dropped or reordered frame changes every digest from that position on, and the first
  inconsistent record is the position of the change (`tlref.chain.verify_chain`);
* the index binds position, so a record cannot be replayed at another position and a gap is visible;
* a verifier can start from any known `D(k-1)` and check frames `k...`;
* **truncating the tail is invisible without the head**: the log of the first n frames is a perfectly valid chain.
  Publish or sign the head out of band (this repository does not sign anything);
* with `TS_EN = 1` the timestamp is covered; with `TS_EN = 0` it is not.

SHA-256 padding is the standard one (FIPS 180-4 s5.1.1) over the whole message above, so the total bit length
that is hashed is `8 * (32 + 8 + [8] + len(frame))`; the hardware appends it itself.

## Worked example

Frames: `F0 = 00 01 ... 3b` (60 bytes), `F1 = ff` repeated 64 times, `F2 = "hello"`.
Timestamps: `1`, `0x0123456789abcdef`, `0xffffffffffffffff`. Genesis all zero.

<!-- vectors -->
```
D0 (timestamps) = c5baed94effe8a7afd218b39c585731b4e60789141b081fbb6e90493ba7dea9e
D1 (timestamps) = 317dafd3101557611f761088d79b40f6d51a7f9ad6dac6ef0cf5b5bc8459e467
D2 (timestamps) = d450708c5c5864999d9d85bddad7ad838cd5c61867ff0473f5f443e8d815c065
D0 (no timestamps) = 0f388e66cbc500a27679e28349f137c05d6879bfab3e4563555e985533287c27
D1 (no timestamps) = e147ff4f487364130e6fed70774e2f0d4bc6fd4c33cab7c4ecb679b6991e97b8
D2 (no timestamps) = d6cb42dfb5b3ce66064b13a9ff2423ed65098938110bda2a34a4a53909cceee0
```
<!-- /vectors -->

These are checked by `tests/test_reference.py` against the reference, against coreutils' `sha256sum`, and (through the
chain) against the RTL in `tests/test_rtl.py`.

## Interface (module `tap_logger`)

| port | dir | meaning |
| --- | --- | --- |
| `clk`, `rst` | in | one clock; synchronous active-high reset restarts the chain and drops any frame in flight |
| `s_tdata[7:0]`, `s_tvalid`, `s_tlast`, `s_tready` | in/out | frame bytes, AXI4-Stream style, one byte per beat; `s_tlast` on the final byte |
| `ts_in[63:0]` | in | timestamp, sampled when a frame's first byte is presented; hold it for the frame |
| `log_valid`, `log_ready` | out/in | record handshake; the next frame is not accepted until the record is taken |
| `log_index[63:0]`, `log_len[31:0]`, `log_ts[63:0]`, `log_digest[255:0]` | out | the record |
| `chain_head[255:0]` | out | digest of the last completed frame (`GENESIS` after reset) |

Parameters: `TS_EN` (default 1), `GENESIS` (default 0). Frames up to 2^29 bytes: the bit-length counter is 35 bits wide.
