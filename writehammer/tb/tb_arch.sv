`timescale 1ns/1ps
// tb_arch: runs one architectural-test image (program.hex in the run directory) until it writes
// the MMIO HALT register, then prints the test signature, one 32-bit word per line as "SIG <hex>",
// from word SIG_BEGIN_W up to (not including) SIG_END_W of the data memory (word indices from the
// image base, i.e. (address - 0x80000000) >> 2). Reads the data memory through the top's debug
// read port (dbg_widx/dbg_word), so it works with caches on or off.
// Parameters: CACHES, LAT, SIG_BEGIN_W, SIG_END_W, MEMW, MAXCYC (hang guard; a timeout prints TIMEOUT
// and is always a failure), RESET_PC.
// Checks: nothing itself; tests/arch_test.py compares the signature with Spike's.
module tb_arch #(
    parameter bit CACHES = 1'b0,
    parameter int LAT = 2,
    parameter int SIG_BEGIN_W = 0,
    parameter int SIG_END_W = 0,
    parameter int MEMW = 65536,          // words per memory; tests/arch_test.py sizes it to the image
    parameter int MAXCYC = 400000,
    parameter int RESET_PC = 32'h80000000
);
    logic clk = 1'b0, rst_n = 1'b0;
    always #5 clk = ~clk;
    initial begin repeat (3) @(posedge clk); #1 rst_n = 1'b1; end

    logic [31:0] ic_refill_cnt, dc_refill_cnt, dc_write_cnt, dbg_word;
    logic [31:0] dbg_widx = '0;
    logic        mmio_we;
    logic [31:0] mmio_addr, mmio_wdata;
    rv32_top_pipelined #(.CACHES_ON(CACHES), .MEM_LATENCY(LAT), .MEM_WORDS(MEMW),
                         .DMEM_FROM_IMAGE(1'b1), .RESET_PC(RESET_PC)) dut (
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
            repeat (6) @(posedge clk);
            for (int w = SIG_BEGIN_W; w < SIG_END_W; w++) begin
                dbg_widx = w;
                #1 $display("SIG %08h", dbg_word);
            end
            $finish;
        end else if (cyc >= MAXCYC) begin
            $display("TIMEOUT after %0d cycles", cyc);
            $finish;
        end
    end
endmodule
