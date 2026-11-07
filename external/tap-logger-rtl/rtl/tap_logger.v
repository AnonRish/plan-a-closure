// Tamper-evident frame logger: a SHA-256 hash chain over captured Ethernet frames.
//
//   D(-1) = GENESIS
//   D(i)  = SHA-256( D(i-1) || be64(i) || [be64(ts_i)] || frame_i )          (see docs/FORMAT.md)
//
// Frames arrive one byte per beat (AXI4-Stream style: s_tdata/s_tvalid/s_tlast/s_tready). The 64-bit timestamp
// `ts_in` is sampled when a frame's first byte is presented and is hashed in when TS_EN = 1. After the last
// byte of a frame a log record (index, length, timestamp, digest) is presented with a valid/ready handshake;
// the next frame is not accepted until the record has been taken. The serial dependence D(i-1) -> D(i) means
// frames are hashed one at a time: see README.md for the measured throughput and what that implies.
//
// Synchronous active-high reset restarts the chain at GENESIS with index 0 and discards any frame in flight.
`timescale 1ns/1ps
module tap_logger #(
    parameter TS_EN = 1,
    parameter [255:0] GENESIS = 256'h0
) (
    input  wire         clk,
    input  wire         rst,
    // frame bytes
    input  wire [7:0]   s_tdata,
    input  wire         s_tvalid,
    input  wire         s_tlast,
    output wire         s_tready,
    input  wire [63:0]  ts_in,
    // log record
    output reg          log_valid,
    input  wire         log_ready,
    output reg  [255:0] log_digest,
    output reg  [63:0]  log_index,
    output reg  [31:0]  log_len,
    output reg  [63:0]  log_ts,
    // current chain head (digest of the last completed frame; GENESIS after reset)
    output wire [255:0] chain_head
);
    localparam [5:0] HDR_BYTES = TS_EN ? 6'd48 : 6'd40;

    localparam [2:0] S_IDLE = 3'd0, S_HDR = 3'd1, S_DATA = 3'd2, S_PAD = 3'd3,
                     S_CSTART = 3'd4, S_CWAIT = 3'd5, S_LOG = 3'd6;

    reg [2:0]   state, after_comp;
    reg [511:0] blk;                 // block being assembled, oldest byte in the most significant position
    reg [5:0]   cnt;                 // bytes already in blk
    reg [5:0]   hdr_cnt;
    reg [31:0]  nbytes;              // message bytes so far (header + frame), excluding padding
    reg [31:0]  frame_len;
    reg         first_block;
    reg [1:0]   pad_stage;           // 0: 0x80 marker, 1: zeros, 2: 64-bit length
    reg [2:0]   len_idx;
    reg [63:0]  index;               // index of the frame being (or about to be) hashed
    reg [63:0]  ts_reg;
    reg [255:0] chain;

    reg         core_start, core_init;
    /* verilator lint_off UNUSEDSIGNAL */
    wire        core_busy;                 // part of the core's interface; observed by the testbenches
    /* verilator lint_on UNUSEDSIGNAL */
    wire        core_done;
    wire [255:0] core_digest;

    sha256_core core (.clk(clk), .rst(rst), .start(core_start), .init(core_init), .block(blk),
                      .busy(core_busy), .done(core_done), .digest(core_digest));

    assign chain_head = chain;
    assign s_tready   = (state == S_DATA);

    wire [383:0] hdr_all  = {chain, index, ts_reg};
    wire [7:0]   hdr_byte = hdr_all[383 - 8 * hdr_cnt -: 8];
    wire [63:0]  bitlen   = {29'd0, nbytes, 3'd0};
    wire [7:0]   len_byte = bitlen[63 - 8 * len_idx -: 8];
    wire [7:0]   pad_byte = (pad_stage == 2'd0) ? 8'h80 : (pad_stage == 2'd1) ? 8'h00 : len_byte;

    always @(posedge clk) begin
        core_start <= 1'b0;
        if (rst) begin
            state       <= S_IDLE;
            after_comp  <= S_IDLE;
            log_valid   <= 1'b0;
            chain       <= GENESIS;
            index       <= 64'd0;
            cnt         <= 6'd0;
            hdr_cnt     <= 6'd0;
            nbytes      <= 32'd0;
            frame_len   <= 32'd0;
            first_block <= 1'b1;
            pad_stage   <= 2'd0;
            len_idx     <= 3'd0;
            ts_reg      <= 64'd0;
            core_init   <= 1'b0;
        end else begin
            if (log_valid && log_ready)
                log_valid <= 1'b0;

            case (state)
            S_IDLE: begin
                if (s_tvalid && !log_valid) begin
                    ts_reg      <= TS_EN ? ts_in : 64'd0;
                    frame_len   <= 32'd0;
                    nbytes      <= 32'd0;
                    cnt         <= 6'd0;
                    hdr_cnt     <= 6'd0;
                    first_block <= 1'b1;
                    pad_stage   <= 2'd0;
                    len_idx     <= 3'd0;
                    state       <= S_HDR;
                end
            end

            S_HDR: begin
                blk     <= {blk[503:0], hdr_byte};
                cnt     <= cnt + 6'd1;
                nbytes  <= nbytes + 32'd1;
                hdr_cnt <= hdr_cnt + 6'd1;
                if (hdr_cnt == HDR_BYTES - 6'd1)
                    state <= S_DATA;
            end

            S_DATA: begin
                if (s_tvalid) begin
                    blk       <= {blk[503:0], s_tdata};
                    cnt       <= cnt + 6'd1;
                    nbytes    <= nbytes + 32'd1;
                    frame_len <= frame_len + 32'd1;
                    if (cnt == 6'd63) begin
                        state      <= S_CSTART;
                        after_comp <= s_tlast ? S_PAD : S_DATA;
                    end else if (s_tlast) begin
                        state <= S_PAD;
                    end
                end
            end

            S_PAD: begin
                blk <= {blk[503:0], pad_byte};
                cnt <= cnt + 6'd1;
                case (pad_stage)
                    2'd0:    pad_stage <= (cnt == 6'd55) ? 2'd2 : 2'd1;
                    2'd1:    if (cnt == 6'd55) pad_stage <= 2'd2;
                    default: len_idx <= len_idx + 3'd1;
                endcase
                if (cnt == 6'd63) begin
                    state      <= S_CSTART;
                    after_comp <= (pad_stage == 2'd2 && len_idx == 3'd7) ? S_LOG : S_PAD;
                end
            end

            S_CSTART: begin
                core_start  <= 1'b1;
                core_init   <= first_block;
                first_block <= 1'b0;
                state       <= S_CWAIT;
            end

            S_CWAIT: begin
                if (core_done)
                    state <= after_comp;
            end

            S_LOG: begin
                log_digest <= core_digest;
                log_index  <= index;
                log_len    <= frame_len;
                log_ts     <= ts_reg;
                log_valid  <= 1'b1;
                chain      <= core_digest;
                index      <= index + 64'd1;
                state      <= S_IDLE;
            end

            default: state <= S_IDLE;
            endcase
        end
    end
endmodule
