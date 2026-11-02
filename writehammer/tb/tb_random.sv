`timescale 1ns/1ps
// tb_random: runs one random program (program.hex in the run directory, instruction memory only;
// the data memory starts zeroed) until it writes the MMIO HALT register, then dumps registers
// x1..x31 ("REG n hex") and the data window ("WIN word hex", words WIN_BEGIN_W..WIN_END_W-1, read
// through the top's debug port). Prints "TIMEOUT" if MAXCYC cycles pass without HALT (always a
// failure; MAXCYC only guards against a hung simulation).
// Parameters: CACHES, LAT, FWD, MEMW (words per memory), WIN_BEGIN_W, WIN_END_W, MAXCYC.
// Checks: nothing itself; tests/random_lockstep.py compares the dump with the reference model.
module tb_random #(
    parameter bit CACHES = 1'b0,
    parameter int LAT = 2,
    parameter int FWD = 1,
    parameter int MEMW = 1024,
    parameter int WIN_BEGIN_W = 512,
    parameter int WIN_END_W = 1024,
    parameter int MAXCYC = 100000,
    parameter int INJECT = 0,           // INJECT_STALL_SEED (test only)
    parameter bit RANDLAT = 1'b0,       // random memory latency 1..2*LAT-1
    parameter int MEM_SEED = 1
);
    logic clk = 1'b0, rst_n = 1'b0;
    always #5 clk = ~clk;
    initial begin repeat (3) @(posedge clk); #1 rst_n = 1'b1; end

    logic [31:0] ic_refill_cnt, dc_refill_cnt, dc_write_cnt, dbg_word;
    logic [31:0] dbg_widx = '0;
    logic        mmio_we;
    logic [31:0] mmio_addr, mmio_wdata;
    rv32_top_pipelined #(.FORWARDING(FWD), .CACHES_ON(CACHES), .MEM_LATENCY(LAT), .MEM_WORDS(MEMW), .INJECT_STALL_SEED(INJECT),
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
            repeat (8) @(posedge clk);              // let the older instructions finish writing back
            for (int i = 1; i < 32; i++) $display("REG %0d %h", i, dut.u_regfile.regs[i]);
            for (int w = WIN_BEGIN_W; w < WIN_END_W; w++) begin
                dbg_widx = w;
                #1 $display("WIN %0d %h", w, dbg_word);
            end
            $finish;
        end else if (cyc >= MAXCYC) begin
            $display("TIMEOUT after %0d cycles", cyc);
            $finish;
        end
    end
endmodule
