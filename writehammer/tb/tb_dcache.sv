`timescale 1ns/1ps
// tb_dcache: standalone D$ against mem_model, driven by an operation list (ops.hex in the run
// directory, one 128-bit entry per operation, hex). Entry layout:
//   [31:0] addr  [63:32] wdata (lane-aligned)  [67:64] be  [68] we  [69] re  [70] bypass  [79:72] idle cycles before
// Each operation is presented until dmiss falls (the pipeline is frozen while dmiss = 1, as in the core),
// loads print "LD <index> <word>", the run ends with the counters, the per-line array-write counts
// ("AWL <line> <n>" for n > 0), the stall cycles, and a dump of main memory with the cache overlaid
// (peek) over words 0..DUMP_W-1 ("MEM <word> <hex>"), so the result does not depend on what has been
// written back. Checks nothing itself: tests/dcache_test.py compares everything with independent models.
// Parameters: NOPS, DUMP_W, CACHE_BYTES, LINE_BYTES, LAT, RANDOM, WL (DC_WRITE_LATENCY), MAXCYC.
module tb_dcache #(
    parameter int NOPS = 1,
    parameter int DUMP_W = 4096,
    parameter int CACHE_BYTES = 2048,
    parameter int LINE_BYTES = 16,
    parameter int LAT = 3,
    parameter bit RANDOM = 1'b0,
    parameter int WL = 1,
    parameter int MAXCYC = 2000000
);
    localparam int LB = 8 * LINE_BYTES;
    localparam int NL = CACHE_BYTES / LINE_BYTES;
    logic clk = 1'b0, rst_n = 1'b0;
    always #5 clk = ~clk;
    initial begin repeat (3) @(posedge clk); #1 rst_n = 1'b1; end

    logic [127:0] ops [0:NOPS-1];
    initial $readmemh("ops.hex", ops);

    logic [31:0] addr = 0, wdata = 0, peek_addr = 0;
    logic [3:0] be = 0;
    logic we = 0, re = 0, bypass = 0;
    wire [31:0] rdata, peek_data;
    wire dmiss, mem_valid, mem_we, mem_done, peek_hit;     // NPEEK = 1 here
    wire [31:0] mem_addr;
    wire [LB-1:0] mem_wdata, mem_rdata;
    wire [LINE_BYTES-1:0] mem_be;
    wire aw_valid, aw_kind, tr_valid, tr_we, tr_bypass;
    wire [$clog2(NL)-1:0] aw_line;
    wire [31:0] tr_addr;
    wire [2:0] tr_size;
    wire [31:0] c_access, c_hit, c_miss, c_fill, c_wb, c_bypass, c_rab, c_stall, c_write;

    dcache #(.CACHE_BYTES(CACHE_BYTES), .LINE_BYTES(LINE_BYTES), .DC_WRITE_LATENCY(WL), .NPEEK(1)) dut (
        .clk(clk), .rst_n(rst_n), .addr(addr), .wdata(wdata), .be(be), .we(we), .re(re), .bypass(bypass),
        .rdata(rdata), .dmiss(dmiss), .mem_valid(mem_valid), .mem_we(mem_we), .mem_addr(mem_addr),
        .mem_wdata(mem_wdata), .mem_be(mem_be), .mem_done(mem_done), .mem_rdata(mem_rdata),
        .aw_valid(aw_valid), .aw_line(aw_line), .aw_kind(aw_kind), .tr_valid(tr_valid), .tr_we(tr_we),
        .tr_addr(tr_addr), .tr_size(tr_size), .tr_bypass(tr_bypass),
        .cnt_access(c_access), .cnt_hit(c_hit), .cnt_miss(c_miss), .cnt_fill(c_fill), .cnt_wb(c_wb),
        .cnt_bypass(c_bypass), .cnt_refill_after_bypass(c_rab), .cnt_stall(c_stall), .cnt_write(c_write),
        .peek_addr(peek_addr), .peek_hit(peek_hit), .peek_data(peek_data));

    wire i_ready, i_done, d_ready;
    wire [LB-1:0] i_rdata;
    mem_model #(.WORDS(65536), .LINE_BYTES(LINE_BYTES), .LATENCY(LAT), .RANDOM_LATENCY(RANDOM), .SEED(7)) mm (
        .clk(clk), .rst_n(rst_n), .i_valid(1'b0), .i_ready(i_ready), .i_addr(32'b0), .i_done(i_done), .i_rdata(i_rdata),
        .d_valid(mem_valid), .d_ready(d_ready), .d_we(mem_we), .d_addr(mem_addr), .d_wdata(mem_wdata), .d_be(mem_be),
        .d_done(mem_done), .d_rdata(mem_rdata));

    int awl [0:NL-1];
    int traces = 0;
    initial for (int i = 0; i < NL; i++) awl[i] = 0;
    always @(posedge clk) if (rst_n) begin
        if (aw_valid) awl[aw_line]++;
        if (tr_valid) traces++;
    end

    int cyc = 0, k;
    initial begin
        wait (rst_n);
        for (k = 0; k < NOPS; k++) begin
            repeat (ops[k][79:72]) @(negedge clk);
            @(negedge clk);
            addr = ops[k][31:0]; wdata = ops[k][63:32]; be = ops[k][67:64];
            we = ops[k][68]; re = ops[k][69]; bypass = ops[k][70];
            // wait until the request completes: sample after the combinational response settles
            #1;
            while (dmiss) begin @(negedge clk); #1; end
            if (re) $display("LD %0d %h", k, rdata);
            @(posedge clk);                      // the cycle in which the request completes ends here
            #1; we = 0; re = 0; bypass = 0;
        end
        repeat (4) @(posedge clk);
        $display("CNT access=%0d hit=%0d miss=%0d fill=%0d wb=%0d bypass=%0d rab=%0d stall=%0d write=%0d traces=%0d",
                 c_access, c_hit, c_miss, c_fill, c_wb, c_bypass, c_rab, c_stall, c_write, traces);
        for (int i = 0; i < NL; i++) if (awl[i] != 0) $display("AWL %0d %0d", i, awl[i]);
        for (int w = 0; w < DUMP_W; w++) begin
            peek_addr = 4 * w;
            #1 $display("MEM %0d %h", w, peek_hit ? peek_data : mm.mem[w]);
        end
        $finish;
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc > MAXCYC) begin $display("TIMEOUT"); $finish; end
    end
endmodule
