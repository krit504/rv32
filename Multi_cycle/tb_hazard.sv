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

    // X/Z check: no hazard_unit input or output may be unknown on any cycle after reset.
    // Sampled mid-cycle (negedge) so the combinational outputs have settled. Reduction XOR is
    // x if any bit is x or z; $isunknown on this hierarchical concatenation gave false positives
    // in Icarus 12.
    int xviol = 0;
    always @(negedge clk) if (rst_n) begin
        if ((^{dut.u_hazard_unit.Rs1D, dut.u_hazard_unit.Rs2D,
                        dut.u_hazard_unit.Rs1E, dut.u_hazard_unit.Rs2E,
                        dut.u_hazard_unit.RdE, dut.u_hazard_unit.RdM, dut.u_hazard_unit.RdW,
                        dut.u_hazard_unit.RegWriteE, dut.u_hazard_unit.RegWriteM,
                        dut.u_hazard_unit.RegWriteW,
                        dut.u_hazard_unit.ResultSrcE, dut.u_hazard_unit.PCNextSelE,
                        dut.u_hazard_unit.ForwardAE, dut.u_hazard_unit.ForwardBE,
                        dut.u_hazard_unit.StallF, dut.u_hazard_unit.StallD,
                        dut.u_hazard_unit.FlushD, dut.u_hazard_unit.FlushE}) === 1'bx) begin
            if (xviol == 0)
                $display("XFIRST t=%0t InstrD=%h ResultSrcE=%b RegWriteE=%b PCNextSelE=%b Stall=%b%b Flush=%b%b",
                         $time, dut.InstrD_from_FETCH, dut.u_hazard_unit.ResultSrcE,
                         dut.u_hazard_unit.RegWriteE, dut.u_hazard_unit.PCNextSelE,
                         dut.u_hazard_unit.StallF, dut.u_hazard_unit.StallD,
                         dut.u_hazard_unit.FlushD, dut.u_hazard_unit.FlushE);
            xviol = xviol + 1;
        end
    end

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
        $display("XVIOL %0d", xviol);
        perf.report();
        $finish;
    end
endmodule
