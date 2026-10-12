`timescale 1ns/1ps
// Generic dump testbench. hazard_tests.py writes program.hex, overrides FWD and
// END_PC with -P, runs this, and compares the dump against hand-computed values.
module tb_hazard #(
    parameter int FWD    = 1,
    parameter int END_PC = 0
);
    logic clk = 1'b0;
    logic rst_n;

    rv32_top_pipelined #(.FORWARDING(FWD)) dut (.clk(clk), .rst_n(rst_n));

    always #5 clk = ~clk;

    initial begin
        rst_n = 1'b0;
        repeat (3) @(posedge clk);
        rst_n = 1'b1;
    end

    logic [31:0] cycles, stall_cycles, flush_cycles, retired, spurious;
    logic done;

    perf_counters #(.FORWARDING(FWD), .END_PC(END_PC)) perf (
        .clk(clk), .rst_n(rst_n),
        .PCF(dut.A_PC_to_imem_and_ALU),
        .InstrD(dut.InstrD_from_FETCH),
        .StallF(dut.StallF), .StallD(dut.StallD),
        .FlushD(dut.FlushD), .FlushE(dut.FlushE),
        .RdE(dut.RdE), .RdM(dut.RdM),
        .RegWriteE(dut.RegWriteE), .RegWriteM(dut.RegWriteM),
        .ResultSrcE(dut.ResultSrcE),
        .cycles(cycles), .stall_cycles(stall_cycles), .flush_cycles(flush_cycles),
        .retired(retired), .spurious_stalls(spurious), .done(done)
    );

    initial begin
        repeat (200) @(posedge clk);
        for (int i = 1; i < 32; i++)
            $display("REG %0d %h", i, dut.u_regfile.regs[i]);
        for (int i = 0; i < 4; i++)
            $display("MEM %0d %h", i, dut.u_dmem.mem[i]);
        $display("CYCLES %0d", cycles);
        $display("STALLS %0d", stall_cycles);
        $display("FLUSHES %0d", flush_cycles);
        $display("RETIRED %0d", retired);
        $display("SPURIOUS %0d", spurious);
        $display("DONE %0d", done);
        $finish;
    end
endmodule
