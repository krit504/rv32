`timescale 1ns/1ps
// Generic dump testbench for hazard tests. hazard_tests.py writes program.hex,
// runs this, and compares the dumped state against hand-computed expectations.
module tb_hazard;
    logic clk = 1'b0;
    logic rst_n;
    int stalls = 0;
    int flushes = 0;

    rv32_top_pipelined dut (.clk(clk), .rst_n(rst_n));

    always #5 clk = ~clk;

    initial begin
        rst_n = 1'b0;
        repeat (3) @(posedge clk);
        rst_n = 1'b1;
    end

    always @(posedge clk) if (rst_n) begin
        if (dut.StallF) stalls = stalls + 1;
        if (dut.FlushD) flushes = flushes + 1;
    end

    initial begin
        repeat (120) @(posedge clk);
        for (int i = 1; i < 32; i++)
            $display("REG %0d %h", i, dut.u_regfile.regs[i]);
        for (int i = 0; i < 4; i++)
            $display("MEM %0d %h", i, dut.u_dmem.mem[i]);
        $display("STALLS %0d", stalls);
        $display("FLUSHES %0d", flushes);
        $finish;
    end
endmodule
