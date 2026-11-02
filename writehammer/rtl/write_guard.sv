// write_guard: decides, per store, whether the D$ must handle it as a restricted (bypassed) store
// (spec T5.1 interface; the detectors D1, D2, D3 arrive in T5, this version has the two that need no
// state).
//
// DETECTOR: 0 = NONE (never restricts; the plain cache), 1 = ALWAYS (restricts every store, the
// upper-bound test control of T5.10). Any other value is an elaboration error until T5.
// Interface (spec T5.1): store_valid = a store (not an MMIO store) is in the Memory stage;
// array_write_valid / line_idx = the D$ data-array write event of this cycle and the line it hit;
// cycle_strobe = 1 every cycle (windowing clock for the T5 detectors). bypass_store is combinational in
// store_valid and stable while the store is in Memory (the pipeline is frozen while the D$ works on
// it), as dcache requires. stall_req (action A2, T5.5) is 0 here. restricted = the guard is currently
// in a restricted state (reported by the detectors, used for the false-positive fractions).
// Unused inputs by design until T5: they carry the detectors' observations.
module write_guard #(
    parameter int DETECTOR = 0
)(
    input  logic        clk,
    input  logic        rst_n,
    /* verilator lint_off UNUSEDSIGNAL */  // KI-015: observation inputs used by the T5 detectors (store_valid only by ALWAYS)
    input  logic        store_valid,
    input  logic        array_write_valid,
    input  logic [31:0] line_idx,
    input  logic        cycle_strobe,
    /* verilator lint_on UNUSEDSIGNAL */
    output logic        bypass_store,
    output logic        stall_req,
    output logic        restricted
);
    /* verilator lint_off UNUSEDSIGNAL */
    logic unused_clk_rst;
    assign unused_clk_rst = clk ^ rst_n;
    /* verilator lint_on UNUSEDSIGNAL */

    if (DETECTOR == 0) begin : g_none
        assign bypass_store = 1'b0;
        assign restricted   = 1'b0;
    end else if (DETECTOR == 1) begin : g_always
        assign bypass_store = store_valid;
        assign restricted   = 1'b1;
    end else begin : g_unimplemented
        $error("write_guard: DETECTOR %0d not implemented yet (T5)", DETECTOR);
    end
    assign stall_req = 1'b0;
endmodule
