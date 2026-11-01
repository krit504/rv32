`timescale 1ns/1ps
// tb_cache_integration: runs prog.hex (in the run directory) on rv32_top_pipelined with caches on,
// then prints final registers, the first four data-memory words, the cache counters, and the
// per-cycle imiss pattern for the first 48 cycles after reset.
// Checks: nothing itself; tests/cache_integration.py compares the dump with expected values.
// Does not check: per-cycle pipeline state other than imiss.
module tb_cache_integration #(parameter int LAT = 2, parameter int CYC = 400);
    logic clk = 1'b0, rst_n = 1'b0;
    always #5 clk = ~clk;

    logic [31:0] ic_refill_cnt, dc_refill_cnt, dc_write_cnt;
    rv32_top_pipelined #(.CACHES_ON(1), .MEM_LATENCY(LAT), .IMEM_FILE("prog.hex")) dut (
        .clk(clk), .rst_n(rst_n),
        .ic_refill_cnt(ic_refill_cnt), .dc_refill_cnt(dc_refill_cnt), .dc_write_cnt(dc_write_cnt)
    );   // dbg_dmem is read hierarchically below: Icarus 12 leaves an unpacked-array output port x

    initial begin repeat (3) @(posedge clk); #1 rst_n = 1'b1; end

    string im = "";
    int n = 0;
    always @(negedge clk) if (rst_n && n < 48) begin
        im = {im, dut.imiss ? "1" : "0"};
        n++;
    end

    initial begin
        repeat (CYC) @(posedge clk);
        for (int i = 1; i < 32; i++) $display("REG %0d %h", i, dut.u_regfile.regs[i]);
        for (int i = 0; i < 4; i++)  $display("MEM %0d %h", i, dut.dbg_dmem[i]);
        $display("IC_REFILL %0d", ic_refill_cnt);
        $display("DC_REFILL %0d", dc_refill_cnt);
        $display("DC_WRITE %0d", dc_write_cnt);
        $display("IMISS %s", im);
        $finish;
    end
endmodule
