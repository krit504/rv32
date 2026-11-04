`timescale 1ns/1ps
// tb_wear: runs program.hex through the cached core and records array writes and
// completed D$ accesses. Checks completion/timeout and writes counters at HALT;
// Python checks program exit, expected counts, and golden replay.
module tb_wear #(
    parameter int LAT = 2,
    parameter int MEMW = 65536,
    parameter int MAXCYC = 200000,
    parameter int DCACHE_BYTES = 2048,
    parameter int LINE_BYTES = 16,
    parameter int WINDOW_CYCLES = 10000,
    // write_guard (T5); default = no detector
    parameter int DETECTOR = 0,
    parameter int WG_MODE = 0,
    parameter int WG_WINDOW = 10000,
    parameter int WG_THRESHOLD = 1000,
    parameter int WG_M = 16,
    parameter int WG_PLACEBO_RATE = 0,
    parameter int WG_PLACEBO_SEED = 1
);
    logic clk = 0, rst_n = 0;
    always #5 clk = ~clk;
    initial begin repeat (3) @(posedge clk); #1 rst_n = 1; end
    logic [31:0] ic_refill_cnt, dc_refill_cnt, dc_write_cnt;
    logic aw_valid, aw_kind, tr_valid, tr_we, tr_bypass;
    logic [31:0] aw_line, tr_addr;
    logic [2:0] tr_size;
    logic [31:0] cnt_access, cnt_hit, cnt_miss, cnt_wb, cnt_bypass, cnt_rab, cnt_stall;
    logic mmio_we;
    logic [31:0] mmio_addr, mmio_wdata;
    logic halted;
    logic [31:0] exit_code;
    int cyc = 0;

    rv32_top_pipelined #(.CACHES_ON(1'b1), .MEM_LATENCY(LAT), .MEM_WORDS(MEMW),
                         .DCACHE_BYTES(DCACHE_BYTES), .LINE_BYTES(LINE_BYTES),
                         .DETECTOR(DETECTOR), .WG_MODE(WG_MODE), .WG_WINDOW(WG_WINDOW), .WG_THRESHOLD(WG_THRESHOLD),
                         .WG_M(WG_M), .WG_PLACEBO_RATE(WG_PLACEBO_RATE), .WG_PLACEBO_SEED(WG_PLACEBO_SEED)) dut (
        .clk(clk), .rst_n(rst_n), .dbg_widx(32'b0),
        .ic_refill_cnt(ic_refill_cnt), .dc_refill_cnt(dc_refill_cnt), .dc_write_cnt(dc_write_cnt),
        .dc_aw_valid(aw_valid), .dc_aw_line(aw_line), .dc_aw_kind(aw_kind),
        .dc_tr_valid(tr_valid), .dc_tr_we(tr_we), .dc_tr_addr(tr_addr),
        .dc_tr_size(tr_size), .dc_tr_bypass(tr_bypass),
        .dc_cnt_access(cnt_access), .dc_cnt_hit(cnt_hit), .dc_cnt_miss(cnt_miss),
        .dc_cnt_wb(cnt_wb), .dc_cnt_bypass(cnt_bypass), .dc_cnt_rab(cnt_rab),
        .dc_cnt_stall(cnt_stall),
        .mmio_we(mmio_we), .mmio_addr(mmio_addr), .mmio_wdata(mmio_wdata),
        .wg_restricted(), .wg_cycles_restricted(), .wg_first_restrict(), .wg_stores(), .wg_stores_restricted()
    );
    int aw_store_cnt = 0;    // data-array writes made by a store hit (not fills): must be 0 for a restricted store
    always @(posedge clk) if (rst_n && aw_valid && !aw_kind) aw_store_cnt <= aw_store_cnt + 1;
    sys_monitor mon (
        .clk(clk), .rst_n(rst_n), .mmio_we(mmio_we), .mmio_addr(mmio_addr), .mmio_wdata(mmio_wdata),
        .imiss(dut.imiss), .dmiss(dut.dmiss),
        .StallD(dut.StallD), .StallE(dut.StallE), .StallM(dut.StallM), .StallW(dut.StallW),
        .FlushD(dut.FlushD), .FlushE(dut.FlushE),
        .stallCond(dut.u_hazard_unit.stallCond), .redirectE(dut.u_hazard_unit.redirectE),
        .halted(halted), .exit_code(exit_code)
    );
    wear_monitor #(.NLINES(DCACHE_BYTES/LINE_BYTES), .WINDOW_CYCLES(WINDOW_CYCLES)) wear (
        .clk(clk), .rst_n(rst_n), .aw_valid(aw_valid), .aw_line(aw_line), .aw_kind(aw_kind),
        .tr_valid(tr_valid), .tr_we(tr_we), .tr_addr(tr_addr), .tr_size(tr_size),
        .tr_bypass(tr_bypass), .mmio_we(mmio_we), .mmio_addr(mmio_addr), .mmio_wdata(mmio_wdata)
    );
    always @(posedge clk) begin
        if (rst_n) cyc <= cyc + 1;
        if (halted) begin
            repeat (6) @(posedge clk);
            #1 wear.finish_run();
            $display("AW_STORE %0d", aw_store_cnt);
            $display("DC_CNT access=%0d hit=%0d miss=%0d fill=%0d wb=%0d bypass=%0d rab=%0d write=%0d",
                     cnt_access, cnt_hit, cnt_miss, dc_refill_cnt, cnt_wb,
                     cnt_bypass, cnt_rab, dc_write_cnt);
            $finish;
        end else if (cyc >= MAXCYC) begin
            #1 wear.finish_run();
            $display("TIMEOUT after %0d cycles", cyc);
            $finish;
        end
    end
endmodule
