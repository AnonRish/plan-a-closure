// Cycle-accurate testbench for tap_logger. Everything is sampled with pre-edge values and driven with
// non-blocking assignments, so valid/ready handshakes behave as they would between two synchronous blocks.
//
// Plusargs: +FRAMES= +META= +EXPECTED= (readmemh files) +N= frames, +STALL= percent of idle source cycles,
//           +READY= percent of cycles the consumer is ready, +SEED=, +RESET_AT= cycle at which to pulse reset
//           mid-run (0 = never); after the reset the whole stream is sent again from the beginning,
//           +DELAY= when non-zero the consumer takes each record exactly DELAY cycles after it appears
//           (a long stall: the logger must hold off the source rather than overwrite an untaken record).
// Compile-time: -DTS_EN=0|1  -DGENESIS=256'h...  -DMAXB=  -DMAXF=
`timescale 1ns/1ps
`ifndef TS_EN
`define TS_EN 1
`endif
`ifndef GENESIS
`define GENESIS 256'h0
`endif
`ifndef MAXB
`define MAXB 600000
`endif
`ifndef MAXF
`define MAXF 2048
`endif

module tb_tap_logger;
    localparam TS_EN = `TS_EN;
    localparam MAXB  = `MAXB;
    localparam MAXF  = `MAXF;

    reg clk = 1'b0;
    always #5 clk = ~clk;
    reg rst = 1'b1;

    reg  [7:0]   s_tdata  = 8'h00;
    reg          s_tvalid = 1'b0;
    reg          s_tlast  = 1'b0;
    wire         s_tready;
    reg  [63:0]  ts_in    = 64'h0;
    wire         log_valid;
    reg          log_ready = 1'b0;
    wire [255:0] log_digest;
    wire [63:0]  log_index, log_ts;
    wire [31:0]  log_len;
    wire [255:0] chain_head;

`ifdef GATE
    // post-synthesis netlist: parameters were fixed when it was generated
    tap_logger dut (
`else
    tap_logger #(.TS_EN(TS_EN), .GENESIS(`GENESIS)) dut (
`endif
        .clk(clk), .rst(rst), .s_tdata(s_tdata), .s_tvalid(s_tvalid), .s_tlast(s_tlast), .s_tready(s_tready),
        .ts_in(ts_in), .log_valid(log_valid), .log_ready(log_ready), .log_digest(log_digest),
        .log_index(log_index), .log_len(log_len), .log_ts(log_ts), .chain_head(chain_head));

    reg [7:0]   frame_bytes [0:MAXB-1];
    reg [95:0]  meta        [0:MAXF-1];
    reg [255:0] expd        [0:MAXF-1];
    integer offs [0:MAXF];
    integer nframes, stall, ready_pct, seed_d, seed_c, reset_at, maxcyc, delay, valid_age;
    reg [1023:0] f_frames, f_meta, f_exp;

    integer cycles, f, bi, cur_len, rec_idx, errors, i, bytes_acc, t_first, t_last, resets;
    reg started;

    initial begin
        if (!$value$plusargs("FRAMES=%s", f_frames))   f_frames = "build/frames.mem";
        if (!$value$plusargs("META=%s", f_meta))       f_meta   = "build/meta.mem";
        if (!$value$plusargs("EXPECTED=%s", f_exp))    f_exp    = "build/expected.mem";
        if (!$value$plusargs("N=%d", nframes))         nframes  = 1;
        if (!$value$plusargs("STALL=%d", stall))       stall    = 0;
        if (!$value$plusargs("READY=%d", ready_pct))   ready_pct = 100;
        if (!$value$plusargs("SEED=%d", seed_d))       seed_d   = 1;
        if (!$value$plusargs("RESET_AT=%d", reset_at)) reset_at = 0;
        if (!$value$plusargs("MAXCYC=%d", maxcyc))     maxcyc   = 40000000;
        if (!$value$plusargs("DELAY=%d", delay))       delay    = 0;
        valid_age = 0;
        seed_c = seed_d * 7919 + 13;
        $readmemh(f_frames, frame_bytes);
        $readmemh(f_meta, meta);
        $readmemh(f_exp, expd);
        offs[0] = 0;
        for (i = 0; i < nframes; i = i + 1) offs[i+1] = offs[i] + meta[i][95:64];
        cycles = 0; f = 0; bi = 0; rec_idx = 0; errors = 0; bytes_acc = 0; t_first = -1; t_last = 0; resets = 0;
        started = 1'b0;
        repeat (4) @(posedge clk);
        rst <= 1'b0;
    end

    // reset sequencing: power-on reset above, then an optional mid-run pulse
    always @(posedge clk) begin
        cycles <= cycles + 1;
        if (reset_at != 0 && cycles == reset_at && resets == 0) begin rst <= 1'b1; resets <= 1; end
        if (reset_at != 0 && cycles == reset_at + 3)            rst <= 1'b0;
    end

    // source
    always @(posedge clk) begin
        if (rst) begin
            s_tvalid <= 1'b0; s_tlast <= 1'b0; f <= 0; bi <= 0;
        end else begin
            if (s_tvalid && s_tready) begin
                bytes_acc <= bytes_acc + 1;
                if (t_first < 0) t_first <= cycles;
            end
            if (!s_tvalid || s_tready) begin
                if (f < nframes && (($random(seed_d) & 32'h7fffffff) % 100) >= stall) begin
                    cur_len = meta[f][95:64];
                    s_tvalid <= 1'b1;
                    s_tdata  <= frame_bytes[offs[f] + bi];
                    s_tlast  <= (bi == cur_len - 1);
                    if (bi == 0) ts_in <= meta[f][63:0];
                    if (bi == cur_len - 1) begin f <= f + 1; bi <= 0; end else bi <= bi + 1;
                end else begin
                    s_tvalid <= 1'b0; s_tlast <= 1'b0;
                end
            end
        end
    end

    // consumer and checker
    always @(posedge clk) begin
        if (rst) begin
            log_ready <= 1'b0; rec_idx <= 0;
        end else begin
            if (delay > 0) begin
                valid_age <= (log_valid && !log_ready) ? valid_age + 1 : 0;
                log_ready <= log_valid && (valid_age >= delay);
            end else begin
                log_ready <= ((($random(seed_c) & 32'h7fffffff) % 100) < ready_pct);
            end
            if (log_valid && chain_head !== log_digest) begin
                errors = errors + 1; $display("MISMATCH chain_head != log_digest at record %0d", rec_idx);
            end
            if (log_valid && log_ready) begin
                if (rec_idx >= nframes) begin errors = errors + 1; $display("MISMATCH extra record"); end
                else begin
                    if (log_index !== rec_idx) begin errors = errors + 1; $display("MISMATCH rec=%0d field=index got=%0d", rec_idx, log_index); end
                    if (log_len !== meta[rec_idx][95:64]) begin errors = errors + 1; $display("MISMATCH rec=%0d field=len got=%0d want=%0d", rec_idx, log_len, meta[rec_idx][95:64]); end
                    if (log_ts !== (TS_EN ? meta[rec_idx][63:0] : 64'h0)) begin errors = errors + 1; $display("MISMATCH rec=%0d field=ts got=%016h", rec_idx, log_ts); end
                    if (log_digest !== expd[rec_idx]) begin errors = errors + 1; $display("MISMATCH rec=%0d field=digest got=%064h want=%064h", rec_idx, log_digest, expd[rec_idx]); end
                end
                $display("LOG %0d %0d %016h %064h", log_index, log_len, log_ts, log_digest);
                rec_idx <= rec_idx + 1;
                t_last <= cycles;
            end
        end
    end

    // finish
    always @(posedge clk) begin
        if (!rst && cycles > 8 && rec_idx == nframes && !log_valid) begin
            if (chain_head !== expd[nframes-1]) begin errors = errors + 1; $display("MISMATCH final chain_head"); end
            $display("DONE errors=%0d frames=%0d bytes=%0d cycles=%0d resets=%0d", errors, nframes, bytes_acc, t_last - t_first + 1, resets);
            $finish;
        end
        if (cycles > maxcyc) begin
            $display("TIMEOUT rec_idx=%0d of %0d", rec_idx, nframes);
            $display("DONE errors=%0d frames=%0d bytes=%0d cycles=0 resets=%0d", errors + 1, nframes, bytes_acc, resets);
            $finish;
        end
    end
endmodule
