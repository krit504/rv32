// core_only: the RV32I 5-stage core without caches, write guard, memory model or any observation logic,
// for the T6.5 physical-cost study (the denominator of "% of the core"). It is rv32_top_pipelined with
// CORE_ONLY = 1 (same pipeline source, so the area is the real core's); the instruction and data memories
// are outside: the fetch port (i_addr -> i_rdata) and the Memory-stage data port (d_*) are plain
// request/response ports, and i_stall / d_stall freeze fetch / the pipeline like a cache miss would.
// All simulation observation outputs of the top are left unconnected, so synthesis removes them.
module core_only #(
    parameter logic [31:0] RESET_PC = 32'h0
)(
    input  logic        clk,
    input  logic        rst_n,
    output logic [31:0] i_addr,
    input  logic [31:0] i_rdata,
    input  logic        i_stall,
    output logic [31:0] d_addr,
    output logic [31:0] d_wdata,
    output logic [3:0]  d_be,
    output logic        d_we,
    output logic        d_re,
    input  logic [31:0] d_rdata,
    input  logic        d_stall
);
    /* verilator lint_off PINCONNECTEMPTY */  // observation outputs are intentionally dropped
    /* verilator lint_off PINMISSING */
    rv32_top_pipelined #(.CORE_ONLY(1'b1), .CACHES_ON(1'b0), .OBSERVE(1'b0), .RESET_PC(RESET_PC)) u_core(
        .clk(clk),
        .rst_n(rst_n),
        .ext_instr(i_rdata),
        .ext_imiss(i_stall),
        .ext_rdata(d_rdata),
        .ext_dmiss(d_stall),
        .ext_iaddr(i_addr),
        .ext_daddr(d_addr),
        .ext_wdata(d_wdata),
        .ext_be(d_be),
        .ext_we(d_we),
        .ext_re(d_re),
        .dbg_widx(32'b0)
    );
    /* verilator lint_on PINMISSING */
    /* verilator lint_on PINCONNECTEMPTY */
endmodule
