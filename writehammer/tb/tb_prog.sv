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
    parameter bit HASH = 1'b0           // print REGHASH and MEMHASH (FNV-1a over registers / every memory word) at HALT
);
    logic clk = 1'b0, rst_n = 1'b0;
    always #5 clk = ~clk;
    initial begin repeat (3) @(posedge clk); #1 rst_n = 1'b1; end

    logic [31:0] ic_refill_cnt, dc_refill_cnt, dc_write_cnt;
    logic [31:0] dbg_word;
    logic [31:0] dbg_widx = '0;
    logic        mmio_we;
    logic [31:0] mmio_addr, mmio_wdata;
    rv32_top_pipelined #(.FORWARDING(FWD), .CACHES_ON(CACHES), .MEM_LATENCY(LAT),
                         .MEM_WORDS(MEMW), .DMEM_FROM_IMAGE(IMAGE), .INJECT_STALL_SEED(INJECT),
                         .MEM_RANDOM_LATENCY(RANDLAT), .MEM_SEED(MEM_SEED)) dut (
        .clk(clk), .rst_n(rst_n),
        .ic_refill_cnt(ic_refill_cnt), .dc_refill_cnt(dc_refill_cnt), .dc_write_cnt(dc_write_cnt),
        .mmio_we(mmio_we), .mmio_addr(mmio_addr), .mmio_wdata(mmio_wdata),
        .dbg_widx(dbg_widx), .dbg_word(dbg_word)
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
            $display("IC_REFILL %0d", ic_refill_cnt);
            $display("DC_REFILL %0d", dc_refill_cnt);
            $display("DC_WRITE %0d", dc_write_cnt);
            $finish;
        end else if (cyc >= MAXCYC) begin
            $display("TIMEOUT after %0d cycles", cyc);
            $finish;
        end
    end
endmodule
