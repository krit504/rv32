`timescale 1ns/1ps
// tb_prog: runs a program (program.hex in the run directory) on rv32_top_pipelined until it writes
// the HALT register, with the MMIO monitor attached. Prints HALT/PERF/PHASE lines (sys_monitor).
// Parameters: CACHES (0/1), LAT (memory latency), FWD (forwarding), MAXCYC (safety limit),
// MEMW (words per memory), IMAGE (load the data memory from the same image as the code).
// Prints "TIMEOUT" and stops if MAXCYC clock cycles pass without HALT: the limit only guards
// against a hung simulation and is logged by the caller; a timeout is always a test failure.
// Also dumps registers x1..x31 and the first four data words at HALT ("REG n h", "MEM n h"), and
// the cache counters. Checks: nothing itself; the Python tests compare the output.
module tb_prog #(
    parameter bit CACHES = 1'b0,
    parameter int LAT = 2,
    parameter int FWD = 1,
    parameter int MAXCYC = 200000,
    parameter int MEMW = 256,           // words per memory (65536 = 256 KiB for linked C images)
    parameter bit IMAGE = 1'b0,         // 1: data memory also loaded from program.hex
    parameter int INJECT = 0,           // INJECT_STALL_SEED (test only)
    parameter bit RANDLAT = 1'b0,       // random memory latency 1..2*LAT-1
    parameter int MEM_SEED = 1,
    parameter bit HASH = 1'b0,          // print REGHASH and MEMHASH (FNV-1a over registers / every memory word) at HALT
    parameter int ICB = 2048,           // I$ bytes
    parameter int DCB = 2048,           // D$ bytes
    parameter int LINEB = 16,           // line bytes (both caches)
    // write_guard (T5); defaults = no detector. Names as in rv32_top_pipelined.
    parameter int DETECTOR = 0,
    parameter int WG_MODE = 0,
    parameter int WG_WINDOW = 10000,
    parameter int WG_THRESHOLD = 1000,
    parameter int WG_M = 16,
    parameter int WG_PLACEBO_RATE = 0,
    parameter int WG_PLACEBO_SEED = 1
);
    logic clk = 1'b0, rst_n = 1'b0;
    always #5 clk = ~clk;
    initial begin repeat (3) @(posedge clk); #1 rst_n = 1'b1; end

    logic [31:0] ic_refill_cnt, dc_refill_cnt, dc_write_cnt;
    logic [31:0] dbg_word;
    logic [31:0] dbg_widx = '0;
    logic [31:0] c_dc_access, c_dc_hit, c_dc_miss, c_dc_wb, c_dc_bypass, c_dc_rab, c_dc_stall;
    logic [31:0] c_ic_lookup, c_ic_miss, c_ic_stall;
    logic        mmio_we;
    logic [31:0] mmio_addr, mmio_wdata;
    logic        wg_restricted;
    logic [31:0] wg_cycles_restricted, wg_first_restrict, wg_stores, wg_stores_restricted;
    rv32_top_pipelined #(.FORWARDING(FWD), .CACHES_ON(CACHES), .MEM_LATENCY(LAT),
                         .MEM_WORDS(MEMW), .DMEM_FROM_IMAGE(IMAGE), .INJECT_STALL_SEED(INJECT),
                         .MEM_RANDOM_LATENCY(RANDLAT), .MEM_SEED(MEM_SEED),
                         .ICACHE_BYTES(ICB), .DCACHE_BYTES(DCB), .LINE_BYTES(LINEB),
                         .DETECTOR(DETECTOR), .WG_MODE(WG_MODE), .WG_WINDOW(WG_WINDOW), .WG_THRESHOLD(WG_THRESHOLD),
                         .WG_M(WG_M), .WG_PLACEBO_RATE(WG_PLACEBO_RATE), .WG_PLACEBO_SEED(WG_PLACEBO_SEED)) dut (
        .clk(clk), .rst_n(rst_n),
        .ic_refill_cnt(ic_refill_cnt), .dc_refill_cnt(dc_refill_cnt), .dc_write_cnt(dc_write_cnt),
        .mmio_we(mmio_we), .mmio_addr(mmio_addr), .mmio_wdata(mmio_wdata),
        .dbg_widx(dbg_widx), .dbg_word(dbg_word),
        .dc_cnt_access(c_dc_access), .dc_cnt_hit(c_dc_hit), .dc_cnt_miss(c_dc_miss), .dc_cnt_wb(c_dc_wb),
        .dc_cnt_bypass(c_dc_bypass), .dc_cnt_rab(c_dc_rab), .dc_cnt_stall(c_dc_stall),
        .ic_cnt_lookup(c_ic_lookup), .ic_cnt_miss(c_ic_miss), .ic_cnt_stall(c_ic_stall),
        .wg_restricted(wg_restricted), .wg_cycles_restricted(wg_cycles_restricted),
        .wg_first_restrict(wg_first_restrict), .wg_stores(wg_stores), .wg_stores_restricted(wg_stores_restricted)
    );

    logic halted;
    logic [31:0] exit_code;
    sys_monitor mon (
        .clk(clk), .rst_n(rst_n),
        .mmio_we(mmio_we), .mmio_addr(mmio_addr), .mmio_wdata(mmio_wdata),
        .imiss(dut.imiss), .dmiss(dut.dmiss),
        .StallD(dut.StallD), .StallE(dut.StallE), .StallM(dut.StallM), .StallW(dut.StallW),
        .FlushD(dut.FlushD), .FlushE(dut.FlushE),
        .stallCond(dut.u_hazard_unit.stallCond), .redirectE(dut.u_hazard_unit.redirectE),
        .halted(halted), .exit_code(exit_code)
    );

    // cache counters over the measurement window: snapshot at the program's MMIO START and STOP writes
    // (a missing START means from reset, a missing STOP means up to HALT), printed as CACHEWIN at HALT
    localparam int NC = 12;
    logic [31:0] cur [0:NC-1], snap0 [0:NC-1], snap1 [0:NC-1];
    logic have_start = 1'b0, have_stop = 1'b0;
    always_comb begin
        cur[0] = c_ic_lookup; cur[1] = c_ic_miss; cur[2] = c_ic_stall;
        cur[3] = c_dc_access; cur[4] = c_dc_hit; cur[5] = c_dc_miss; cur[6] = dc_refill_cnt; cur[7] = c_dc_wb;
        cur[8] = c_dc_bypass; cur[9] = c_dc_rab; cur[10] = c_dc_stall; cur[11] = dc_write_cnt;
    end
    initial for (int i = 0; i < NC; i++) begin snap0[i] = '0; snap1[i] = '0; end
    always @(posedge clk) if (rst_n && mmio_we) begin
        if (mmio_addr[7:0] == 8'h04) begin for (int i = 0; i < NC; i++) snap0[i] <= cur[i]; have_start <= 1'b1; end
        if (mmio_addr[7:0] == 8'h08 && !have_stop) begin for (int i = 0; i < NC; i++) snap1[i] <= cur[i]; have_stop <= 1'b1; end
    end

    // write_guard snapshot at every PHASE marker (MMIO +0xC), for the false-positive and detection-latency
    // metrics of the evaluation: the harness differences consecutive snapshots to get per-phase restricted
    // cycles and restricted stores. first_restrict_prev_phase is the cycle of the first restriction seen in the
    // phase that this marker ends, i.e. since the previous marker (4294967295 if none). WGEND is the same
    // snapshot at HALT, closing the last phase. Cycle numbers here count from reset release, like each other.
    int cyc_ph = 0;
    logic [31:0] first_since_phase = 32'hFFFFFFFF;
    always @(posedge clk) if (rst_n) begin
        cyc_ph <= cyc_ph + 1;
        if (mmio_we && mmio_addr[7:0] == 8'h0C) first_since_phase <= 32'hFFFFFFFF;
        else if (wg_restricted && first_since_phase == 32'hFFFFFFFF) first_since_phase <= 32'(cyc_ph);
        if (mmio_we && mmio_addr[7:0] == 8'h0C)
            $display("WGPHASE id=%0d cycle=%0d restricted_cycles=%0d stores=%0d stores_restricted=%0d restricted_now=%0d first_restrict_prev_phase=%0d",
                     mmio_wdata, cyc_ph, wg_cycles_restricted, wg_stores, wg_stores_restricted, wg_restricted, first_since_phase);
    end

    // run-time cycle limit: +maxcyc=<n> overrides MAXCYC (lets one build serve workloads of very different length)
    int maxcyc_r = MAXCYC;
    initial begin
        if ($value$plusargs("maxcyc=%d", maxcyc_r)) ;
    end

    int cyc = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (halted) begin
            repeat (6) @(posedge clk);          // let the HALT store's neighbours drain
            for (int i = 1; i < 32; i++) $display("REG %0d %h", i, dut.u_regfile.regs[i]);
            for (int i = 0; i < 4; i++)  $display("MEM %0d %h", i, dut.dbg_dmem[i]);
            if (HASH) begin
                logic [31:0] hr, hm;
                hr = 32'h811c9dc5;
                for (int i = 1; i < 32; i++) hr = (hr ^ dut.u_regfile.regs[i]) * 32'h01000193;
                hm = 32'h811c9dc5;
                for (int w = 0; w < MEMW; w++) begin dbg_widx = w; #1 hm = (hm ^ dbg_word) * 32'h01000193; end
                $display("REGHASH %h", hr);
                $display("MEMHASH %h", hm);
            end
            begin
                logic [31:0] d [0:NC-1];
                for (int i = 0; i < NC; i++) d[i] = (have_stop ? snap1[i] : cur[i]) - (have_start ? snap0[i] : 32'd0);
                $display("CACHEWIN ic_lookup=%0d ic_miss=%0d ic_stall=%0d dc_access=%0d dc_hit=%0d dc_miss=%0d dc_fill=%0d dc_wb=%0d dc_bypass=%0d dc_rab=%0d dc_stall=%0d dc_write=%0d",
                         d[0], d[1], d[2], d[3], d[4], d[5], d[6], d[7], d[8], d[9], d[10], d[11]);
            end
            $display("WGEND cycle=%0d restricted_cycles=%0d stores=%0d stores_restricted=%0d restricted_now=%0d first_restrict_prev_phase=%0d",
                     cyc_ph, wg_cycles_restricted, wg_stores, wg_stores_restricted, wg_restricted, first_since_phase);
            $display("WG restricted_cycles=%0d first_restrict=%0d stores=%0d stores_restricted=%0d",
                     wg_cycles_restricted, wg_first_restrict, wg_stores, wg_stores_restricted);
            $display("IC_REFILL %0d", ic_refill_cnt);
            $display("DC_REFILL %0d", dc_refill_cnt);
            $display("DC_WRITE %0d", dc_write_cnt);
            $finish;
        end else if (cyc >= maxcyc_r) begin
            $display("TIMEOUT after %0d cycles", cyc);
            $finish;
        end
    end
endmodule
