`timescale 1ns/1ps
// ============================================================================
// No-hazard integration test for rv32_top_pipelined.
//
// Loads program.hex (must sit in the simulator's run directory, since imem
// itself does $readmemh("program.hex", mem) internally) and runs the program
// listed below. Every register write in this program is spaced at least 3
// instructions from any earlier write to the same register, which is the
// minimum gap this design's regfile (falling-edge write, per spec) supports
// without forwarding — see the x19/x22 pair for the exact 3-instruction
// boundary case, deliberately included to exercise it.
//
// No branch is taken and neither jal nor jalr appears, since this design has
// no flush logic yet (out of scope per the pipelined spec, Note 5) and a
// taken redirect would corrupt the two already-fetched instructions behind it.
//
// Program (see encode.py for the exact encoder used to produce program.hex):
//   0  addi x1,  x0, 5
//   1  addi x2,  x0, 10
//   2  addi x3,  x0, -3
//   3  lui  x4,  0x12345
//   4  auipc x5, 0x1
//   5  add  x6,  x1, x2
//   6  sub  x7,  x2, x1
//   7  and  x8,  x1, x2
//   8  or   x9,  x1, x2
//   9  xor  x10, x1, x2
//  10  slt  x11, x3, x1
//  11  sltu x12, x3, x1
//  12  sll  x13, x1, x2
//  13  srl  x14, x3, x1
//  14  sra  x15, x3, x1
//  15  addi x16, x1, 100
//  16  beq  x1,  x3, 40      (not taken: x1 != x3)
//  17  sw   x6,  0(x0)
//  18  lw   x17, 0(x0)
//  19  addi x19, x0, 42      (writer for the 3-gap test)
//  20  addi x20, x0, 1
//  21  addi x21, x0, 2
//  22  add  x22, x19, x0     (reader, gap = 3: same-cycle W/D falling-edge case)
//  23..26  addi x0, x0, 0    (drain)
// ============================================================================

module tb_rv32_top_pipelined;

    logic clk;
    logic rst_n;

    rv32_top_pipelined dut (
        .clk(clk),
        .rst_n(rst_n)
    );

    // 100 MHz clock
    initial clk = 1'b0;
    always #5 clk = ~clk;

    // async active-low reset, held for 3 cycles
    initial begin
        rst_n = 1'b0;
        repeat (3) @(posedge clk);
        rst_n = 1'b1;
    end

    // ---- expected final register values (computed by encode.py's reference model) ----
    localparam int NUM_CHECKS = 21;
    int          check_reg [NUM_CHECKS];
    logic [31:0] check_val [NUM_CHECKS];

    initial begin
        check_reg[0]=1;  check_val[0]=32'h00000005;
        check_reg[1]=2;  check_val[1]=32'h0000000a;
        check_reg[2]=3;  check_val[2]=32'hfffffffd;
        check_reg[3]=4;  check_val[3]=32'h12345000;
        check_reg[4]=5;  check_val[4]=32'h00001010;
        check_reg[5]=6;  check_val[5]=32'h0000000f;
        check_reg[6]=7;  check_val[6]=32'h00000005;
        check_reg[7]=8;  check_val[7]=32'h00000000;
        check_reg[8]=9;  check_val[8]=32'h0000000f;
        check_reg[9]=10; check_val[9]=32'h0000000f;
        check_reg[10]=11; check_val[10]=32'h00000001;
        check_reg[11]=12; check_val[11]=32'h00000000;
        check_reg[12]=13; check_val[12]=32'h00001400;
        check_reg[13]=14; check_val[13]=32'h07ffffff;
        check_reg[14]=15; check_val[14]=32'hffffffff;
        check_reg[15]=16; check_val[15]=32'h00000069;
        check_reg[16]=17; check_val[16]=32'h0000000f;
        check_reg[17]=19; check_val[17]=32'h0000002a;
        check_reg[18]=20; check_val[18]=32'h00000001;
        check_reg[19]=21; check_val[19]=32'h00000002;
        check_reg[20]=22; check_val[20]=32'h0000002a;
    end

    // ---- per-cycle trace: InstrD through ResultW, one line per cycle ----
    always @(posedge clk) begin
        if (rst_n) begin
            $display("t=%0t  InstrD=%h  RD1E=%h RD2E=%h  ALUResultM=%h  ReadDataW=%h  ResultW=%h  RdW=%0d RegWriteW=%b",
                $time,
                dut.InstrD_from_FETCH,
                dut.RD1E, dut.RD2E,
                dut.ALUResultM,
                dut.ReadDataW,
                dut.ResultW,
                dut.RdW, dut.RegWriteW);
        end
    end

    // ---- run the program, then check final register file state ----
    initial begin
        int pass_count;
        int fail_count;
        logic [31:0] actual;

        pass_count = 0;
        fail_count = 0;

        // 3 reset cycles + 27 instructions + 4-cycle pipeline fill + slack
        repeat (60) @(posedge clk);

        $display("\n===== Register File Check =====");
        for (int i = 0; i < NUM_CHECKS; i++) begin
            actual = dut.u_regfile.regs[check_reg[i]];
            if (actual === check_val[i]) begin
                $display("PASS  x%0d = %h", check_reg[i], actual);
                pass_count = pass_count + 1;
            end else begin
                $display("FAIL  x%0d = %h  (expected %h)", check_reg[i], actual, check_val[i]);
                fail_count = fail_count + 1;
            end
        end

        $display("\n%0d PASS, %0d FAIL", pass_count, fail_count);
        if (fail_count == 0)
            $display("ALL CHECKS PASSED");
        else
            $display("SOME CHECKS FAILED");

        $finish;
    end

endmodule
