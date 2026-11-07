// Core-level testbench: whole padded messages (several blocks, chained) against hashlib's digest.
`timescale 1ns/1ps
module tb_sha256_core;
    reg clk = 1'b0;
    always #5 clk = ~clk;
    reg rst = 1'b1;
    reg start = 1'b0, init = 1'b0;
    reg [511:0] block;
    wire busy, done;
    wire [255:0] digest;
    sha256_core dut (.clk(clk), .rst(rst), .start(start), .init(init), .block(block), .busy(busy), .done(done), .digest(digest));

    reg [511:0] blocks [0:4095];
    reg [287:0] msgs   [0:1023];
    integer nmsgs, m, b, nb, bi, errors, cycles, maxcyc;
    reg [1023:0] f_blocks, f_msgs;
    reg [255:0] want;

    initial begin
        if (!$value$plusargs("BLOCKS=%s", f_blocks)) f_blocks = "build/core/blocks.mem";
        if (!$value$plusargs("MSGS=%s", f_msgs))     f_msgs   = "build/core/msgs.mem";
        if (!$value$plusargs("N=%d", nmsgs))         nmsgs = 1;
        $readmemh(f_blocks, blocks);
        $readmemh(f_msgs, msgs);
        errors = 0; bi = 0; cycles = 0;
        repeat (4) @(posedge clk);
        rst <= 1'b0;
        @(posedge clk);
        for (m = 0; m < nmsgs; m = m + 1) begin
            nb   = msgs[m][287:256];
            want = msgs[m][255:0];
            for (b = 0; b < nb; b = b + 1) begin
                block <= blocks[bi];
                init  <= (b == 0);
                start <= 1'b1;
                @(posedge clk);
                start <= 1'b0;
                maxcyc = 0;
                while (!done) begin
                    @(posedge clk);
                    maxcyc = maxcyc + 1;
                    if (maxcyc > 100) begin $display("TIMEOUT block %0d", bi); errors = errors + 1; $finish; end
                end
                cycles = cycles + maxcyc + 1;
                bi = bi + 1;
            end
            if (digest !== want) begin
                errors = errors + 1;
                $display("MISMATCH msg=%0d got=%064h want=%064h", m, digest, want);
            end
        end
        $display("DONE errors=%0d messages=%0d blocks=%0d cycles=%0d", errors, nmsgs, bi, cycles);
        $finish;
    end
endmodule
