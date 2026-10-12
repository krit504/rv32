`timescale 1ns/1ps

module tb_rv32i_single_cycle;
    logic clk;
    logic rst_n;
    int errors;

    rv32_top u_rs32_top (
        .clk   (clk),
        .rst_n (rst_n)
    );

    always #5 clk = ~clk;

    task automatic check_reg(
        input int unsigned index,
        input logic [31:0] expected
    );
        logic [31:0] actual;
        begin
            actual = u_rs32_top.u_regfile.regs[index];
            if (actual !== expected) begin
                $error("x%0d: got 0x%08x, expected 0x%08x",
                       index, actual, expected);
                errors++;
            end
            else begin
                $display("PASS x%0d = 0x%08x", index, actual);
            end
        end
    endtask

    task automatic check_mem(
        input int unsigned index,
        input logic [31:0] expected
    );
        logic [31:0] actual;
        begin
            actual = u_rs32_top.u_dmem.mem[index];
            if (actual !== expected) begin
                $error("dmem[%0d]: got 0x%08x, expected 0x%08x",
                       index, actual, expected);
                errors++;
            end
            else begin
                $display("PASS dmem[%0d] = 0x%08x", index, actual);
            end
        end
    endtask

    initial begin
        clk    = 1'b0;
        rst_n  = 1'b0;
        errors = 0;

        // Every operand this program needs is built from immediates or from
        // its own sw/lw round trip -- no testbench-side dmem preload required.

        // Hold reset through two rising clock edges, then release away from
        // the active edge. The first instruction executes at the next posedge.
        repeat (2) @(posedge clk);
        @(negedge clk);
        rst_n = 1'b1;

        // The program reaches its terminal self-loop after 45 executed
        // instructions (branch scaffolds skip their untaken arm). Extra
        // cycles prove the final state remains stable in the self-loop.
        repeat (60) @(posedge clk);
        #1;

        // ---- Block 1: remaining R-type / I-type ALU ops ----
        check_reg(1,  32'h00000006);
        check_reg(2,  32'h00000002);
        check_reg(3,  32'h00000018); // sll  6<<2
        check_reg(4,  32'h00000004); // xor  6^2
        check_reg(5,  32'h00000030); // slli 6<<3
        check_reg(6,  32'h00000005); // xori 6^3
        check_reg(7,  32'h0000000e); // ori  6|8
        check_reg(8,  32'h00000002); // andi 6&3
        check_reg(9,  32'hfffffff0); // -16
        check_reg(10, 32'h00000004);
        check_reg(11, 32'h0fffffff); // srl  -16>>4 logical, zero-fill
        check_reg(12, 32'hffffffff); // sra  -16>>>4 arithmetic, sign-fill
        check_reg(13, 32'h0fffffff); // srli, must match x11
        check_reg(14, 32'hffffffff); // srai, must match x12
        check_reg(15, 32'hffffffff); // -1
        check_reg(16, 32'h00000001);
        check_reg(17, 32'h00000001); // slt   -1<1 signed  -> 1
        check_reg(18, 32'h00000000); // sltu  -1<1 unsigned -> 0
        check_reg(19, 32'h00000001); // slti  matches slt
        check_reg(20, 32'h00000000); // sltiu matches sltu

        // ---- Block 2: all 6 branch types ----
        check_reg(22, 32'h00000001); // beq  (x1==x1)  taken
        check_reg(23, 32'h00000000); // bne  (x1==x1)  not taken
        check_reg(24, 32'h00000001); // blt  (-16<1 signed)    taken
        check_reg(25, 32'h00000000); // bge  (-16<1 signed)    not taken
        check_reg(26, 32'h00000000); // bltu (-16<1 unsigned)  not taken
        check_reg(27, 32'h00000001); // bgeu (-16<1 unsigned)  taken

        // ---- Block 3: sw/lw round trip ----
        check_reg(28, 32'hfffffff0);
        check_mem(3,  32'hfffffff0);

        // ---- Block 4/5: lui, auipc+addi ----
        check_reg(29, 32'h12345000);
        check_reg(30, 32'h000012f0); // auipc(PC=0xbc)+0x1000, then +0x234

        // ---- Block 6: jal/jalr call-and-return ----
        check_reg(21, 32'h000000c8); // ra saved by jal = PCPlus4
        check_reg(31, 32'h00000065); // 100 (subroutine) then +1 on correct return

        if (u_rs32_top.A_PC_to_imem_and_ALU !== 32'h000000d8) begin
            $error("terminal PC: got 0x%08x, expected 0x000000d8",
                   u_rs32_top.A_PC_to_imem_and_ALU);
            errors++;
        end
        else begin
            $display("PASS terminal PC = 0x%08x", u_rs32_top.A_PC_to_imem_and_ALU);
        end

        if (errors == 0)
            $display("RV32I SINGLE-CYCLE FULL-ISA INTEGRATION TEST PASSED");
        else
            $fatal(1, "RV32I SINGLE-CYCLE FULL-ISA INTEGRATION TEST FAILED: %0d errors",
                   errors);

        $finish;
    end

endmodule
