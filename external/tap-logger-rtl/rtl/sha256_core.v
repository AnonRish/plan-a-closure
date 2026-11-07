// SHA-256 compression function, one round per clock.
//
//   start  : pulse while idle. `init`=1 loads the standard initial hash value, `init`=0 continues from the
//            chaining value left by the previous block.
//   block  : 512-bit message block, first byte in bits [511:504]. Must be stable for the cycle `start` is high.
//   busy   : high from the cycle after `start` until the digest is ready.
//   done   : one-cycle pulse; `digest` then holds the updated chaining value (valid until the next start).
//
// 66 cycles per block: 1 load, 64 rounds, 1 final addition. Synchronous active-high reset.
`timescale 1ns/1ps
module sha256_core (
    input  wire         clk,
    input  wire         rst,
    input  wire         start,
    input  wire         init,
    input  wire [511:0] block,
    output reg          busy,
    output reg          done,
    output wire [255:0] digest
);
    `include "sha256_consts.vh"

    reg [31:0]  h0, h1, h2, h3, h4, h5, h6, h7;     // chaining value
    reg [31:0]  a, b, c, d, e, f, g, h;             // working variables
    reg [511:0] wv;                                  // message-schedule window: word t in [511:480]
    reg [6:0]   t;                                   // 0..63 rounds, 64 final addition

    assign digest = {h0, h1, h2, h3, h4, h5, h6, h7};

    function [31:0] bsig0; input [31:0] x; bsig0 = {x[1:0], x[31:2]} ^ {x[12:0], x[31:13]} ^ {x[21:0], x[31:22]}; endfunction
    function [31:0] bsig1; input [31:0] x; bsig1 = {x[5:0], x[31:6]} ^ {x[10:0], x[31:11]} ^ {x[24:0], x[31:25]}; endfunction
    function [31:0] ssig0; input [31:0] x; ssig0 = {x[6:0], x[31:7]} ^ {x[17:0], x[31:18]} ^ {3'b000, x[31:3]}; endfunction
    function [31:0] ssig1; input [31:0] x; ssig1 = {x[16:0], x[31:17]} ^ {x[18:0], x[31:19]} ^ {10'b0000000000, x[31:10]}; endfunction
    function [31:0] ch;    input [31:0] x, y, z; ch  = (x & y) ^ (~x & z); endfunction
    function [31:0] maj;   input [31:0] x, y, z; maj = (x & y) ^ (x & z) ^ (y & z); endfunction

    wire [31:0] w_t   = wv[511:480];
    wire [31:0] w_t1  = wv[479:448];
    wire [31:0] w_t9  = wv[223:192];
    wire [31:0] w_t14 = wv[63:32];
    // W[t+16] = sigma1(W[t+14]) + W[t+9] + sigma0(W[t+1]) + W[t]
    wire [31:0] w_new = ssig1(w_t14) + w_t9 + ssig0(w_t1) + w_t;

    wire [31:0] t1 = h + bsig1(e) + ch(e, f, g) + sha256_k(t[5:0]) + w_t;
    wire [31:0] t2 = bsig0(a) + maj(a, b, c);

    always @(posedge clk) begin
        done <= 1'b0;
        if (rst) begin
            busy <= 1'b0;
            t    <= 7'd0;
        end else if (start && !busy) begin
            if (init) begin
                h0 <= IV0; h1 <= IV1; h2 <= IV2; h3 <= IV3; h4 <= IV4; h5 <= IV5; h6 <= IV6; h7 <= IV7;
                a  <= IV0; b  <= IV1; c  <= IV2; d  <= IV3; e  <= IV4; f  <= IV5; g  <= IV6; h  <= IV7;
            end else begin
                a <= h0; b <= h1; c <= h2; d <= h3; e <= h4; f <= h5; g <= h6; h <= h7;
            end
            wv   <= block;
            t    <= 7'd0;
            busy <= 1'b1;
        end else if (busy) begin
            if (t[6] == 1'b0) begin                  // rounds 0..63
                h  <= g;
                g  <= f;
                f  <= e;
                e  <= d + t1;
                d  <= c;
                c  <= b;
                b  <= a;
                a  <= t1 + t2;
                wv <= {wv[479:0], w_new};
                t  <= t + 7'd1;
            end else begin                           // t == 64: add the working variables into the chaining value
                h0 <= h0 + a; h1 <= h1 + b; h2 <= h2 + c; h3 <= h3 + d;
                h4 <= h4 + e; h5 <= h5 + f; h6 <= h6 + g; h7 <= h7 + h;
                busy <= 1'b0;
                done <= 1'b1;
            end
        end
    end
endmodule
