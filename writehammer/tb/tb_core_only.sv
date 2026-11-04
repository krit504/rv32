`timescale 1ns/1ps
// tb_core_only: runs one random program (program.hex) on rv32_top_pipelined with CORE_ONLY = 1 against a
// testbench memory (the top's ext_* ports) and, in parallel, on the synthesis wrapper rtl/core_only.sv
// against its own copy of the memory, with random i_stall / d_stall (STALL = 1) to exercise the freeze
// contract. HALT comes from the top's MMIO monitor (the wrapper has no MMIO port); after the drain, the
// wrapper's registers and its memory window must equal the top's ("WRAPPER_MATCH 1"). Dump format as tb_random
// ("REG n hex", "WIN word hex"), compared with the reference model by tests/core_only_test.py.
module tb_core_only #(
    parameter int MEMW = 2048,
    parameter int WIN_BEGIN_W = 1024,
    parameter int WIN_END_W = 1536,
    parameter int MAXCYC = 400000,
    parameter int STALL = 1,
    parameter int SEED = 1
);
    logic clk = 1'b0, rst_n = 1'b0;
    always #5 clk = ~clk;
    initial begin repeat (3) @(posedge clk); #1 rst_n = 1'b1; end

    // ---- instance A: rv32_top_pipelined, CORE_ONLY = 1 ----
    logic [31:0] a_instr, a_rdata, a_iaddr, a_daddr, a_wdata;
    logic        a_imiss, a_dmiss, a_we, a_re;
    logic [3:0]  a_be;
    logic        mmio_we;
    logic [31:0] mmio_addr, mmio_wdata;
    logic [31:0] mem_a [MEMW];
    logic [31:0] mem_b [MEMW];
    logic [31:0] unused_dbg_word;
    rv32_top_pipelined #(.CORE_ONLY(1'b1), .CACHES_ON(1'b0), .MEM_WORDS(MEMW)) dut_a (
        .clk(clk), .rst_n(rst_n), .dbg_widx(32'b0), .dbg_word(unused_dbg_word),
        .ext_instr(a_instr), .ext_imiss(a_imiss), .ext_rdata(a_rdata), .ext_dmiss(a_dmiss),
        .ext_iaddr(a_iaddr), .ext_daddr(a_daddr), .ext_wdata(a_wdata), .ext_be(a_be), .ext_we(a_we), .ext_re(a_re),
        .mmio_we(mmio_we), .mmio_addr(mmio_addr), .mmio_wdata(mmio_wdata)
    );
    // ---- instance B: the synthesis wrapper ----
    logic [31:0] b_instr, b_rdata, b_iaddr, b_daddr, b_wdata;
    logic        b_istall, b_dstall, b_we, b_re;
    logic [3:0]  b_be;
    core_only dut_b (
        .clk(clk), .rst_n(rst_n), .i_addr(b_iaddr), .i_rdata(b_instr), .i_stall(b_istall),
        .d_addr(b_daddr), .d_wdata(b_wdata), .d_be(b_be), .d_we(b_we), .d_re(b_re), .d_rdata(b_rdata), .d_stall(b_dstall)
    );

    initial begin
        for (int i = 0; i < MEMW; i++) begin mem_a[i] = 32'b0; mem_b[i] = 32'b0; end
        $readmemh("program.hex", mem_a);
        $readmemh("program.hex", mem_b);
    end

    // seeded stalls, identical for both instances so they stay cycle-identical
    logic [15:0] lf, ld;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin lf <= 16'(SEED * 2654435761); ld <= 16'(SEED * 40503 + 12345); end
        else begin
            lf <= {lf[14:0], lf[15] ^ lf[13] ^ lf[12] ^ lf[10]};
            ld <= {ld[14:0], ld[15] ^ ld[13] ^ ld[12] ^ ld[10]};
        end
    end
    wire stall_i = (STALL != 0) && (lf[5] & lf[11]);
    wire stall_d = (STALL != 0) && (ld[3] & ld[9]);
    assign a_imiss = stall_i;  assign b_istall = stall_i;
    assign a_dmiss = stall_d;  assign b_dstall = stall_d;

    // combinational read, write on the edge when the stage advances (not stalled)
    // while a stall is asserted the response is garbage, as a missing cache line would be: a core that
    // ignores i_stall / d_stall consumes it and fails
    assign a_instr = stall_i ? 32'hDEADBEEF : mem_a[a_iaddr[$clog2(MEMW)+1:2]];
    assign b_instr = stall_i ? 32'hDEADBEEF : mem_b[b_iaddr[$clog2(MEMW)+1:2]];
    assign a_rdata = stall_d ? 32'hCAFEF00D : mem_a[a_daddr[$clog2(MEMW)+1:2]];
    assign b_rdata = stall_d ? 32'hCAFEF00D : mem_b[b_daddr[$clog2(MEMW)+1:2]];
    always @(posedge clk) begin
        if (rst_n && a_we && !stall_d)
            for (int k = 0; k < 4; k++) if (a_be[k]) mem_a[a_daddr[$clog2(MEMW)+1:2]][8*k +: 8] <= a_wdata[8*k +: 8];
        if (rst_n && b_we && !stall_d)
            for (int k = 0; k < 4; k++) if (b_be[k]) mem_b[b_daddr[$clog2(MEMW)+1:2]][8*k +: 8] <= b_wdata[8*k +: 8];
    end

    logic halted;
    logic [31:0] exit_code;
    sys_monitor mon (
        .clk(clk), .rst_n(rst_n),
        .mmio_we(mmio_we), .mmio_addr(mmio_addr), .mmio_wdata(mmio_wdata),
        .imiss(dut_a.imiss), .dmiss(dut_a.dmiss),
        .StallD(dut_a.StallD), .StallE(dut_a.StallE), .StallM(dut_a.StallM), .StallW(dut_a.StallW),
        .FlushD(dut_a.FlushD), .FlushE(dut_a.FlushE),
        .stallCond(dut_a.u_hazard_unit.stallCond), .redirectE(dut_a.u_hazard_unit.redirectE),
        .halted(halted), .exit_code(exit_code)
    );

    int cyc = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (halted) begin
            logic match;
            repeat (8) @(posedge clk);
            match = 1'b1;
            for (int i = 1; i < 32; i++) begin
                $display("REG %0d %h", i, dut_a.u_regfile.regs[i]);
                if (dut_a.u_regfile.regs[i] !== dut_b.u_core.u_regfile.regs[i]) match = 1'b0;
            end
            for (int w = WIN_BEGIN_W; w < WIN_END_W; w++) begin
                $display("WIN %0d %h", w, mem_a[w]);
                if (mem_a[w] !== mem_b[w]) match = 1'b0;
            end
            $display("WRAPPER_MATCH %0d", match);
            $finish;
        end else if (cyc >= MAXCYC) begin
            $display("TIMEOUT after %0d cycles", cyc);
            $finish;
        end
    end
endmodule
