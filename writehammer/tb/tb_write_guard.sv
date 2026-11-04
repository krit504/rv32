// tb_write_guard: drives write_guard with a per-cycle stimulus file (stim.hex) and prints one line per cycle:
//   "C <cycle> <bypass> <restricted> <cycles_restricted> <first_restrict> <stores> <stores_restricted>"
// stimulus word: bit0 store_valid, bit1 store_busy, bit2 array_write_valid, [15:8] line_idx, [23:16] store_line.
// The expected values come from the independent Python model tests/guard_model.py (tests/write_guard_test.py).
module tb_write_guard #(
    parameter int DETECTOR = 2, parameter int MODE = 0, parameter int WINDOW_CYCLES = 100,
    parameter int THRESHOLD = 10, parameter int M = 16, parameter int W = 16, parameter int LINES = 128,
    parameter int PLACEBO_RATE = 0, parameter int PLACEBO_SEED = 1, parameter int NCYC = 1000
);
    logic clk = 0, rst_n = 0;
    logic sv, busy, awv;
    logic [31:0] lidx, sline;
    logic byp, stall, restr;
    logic [31:0] ocr, ofr, ost, osr;
    logic [31:0] mem [NCYC];
    write_guard #(.DETECTOR(DETECTOR), .MODE(MODE), .WINDOW_CYCLES(WINDOW_CYCLES), .THRESHOLD(THRESHOLD),
                  .M(M), .W(W), .LINES(LINES), .PLACEBO_RATE(PLACEBO_RATE), .PLACEBO_SEED(PLACEBO_SEED)) dut(
        .clk(clk), .rst_n(rst_n), .store_valid(sv), .store_busy(busy), .store_line(sline),
        .array_write_valid(awv), .line_idx(lidx), .cycle_strobe(1'b1), .bypass_store(byp), .stall_req(stall),
        .restricted(restr), .obs_cycles_restricted(ocr), .obs_first_restrict(ofr), .obs_stores(ost),
        .obs_stores_restricted(osr));
    always #5 clk = ~clk;
    initial begin
        $readmemh("stim.hex", mem);
        sv = 0; busy = 0; awv = 0; lidx = 0; sline = 0;
        @(negedge clk);
        rst_n = 1;
        for (int c = 0; c < NCYC; c++) begin
            if (c > 0) @(negedge clk);
            sv = mem[c][0]; busy = mem[c][1]; awv = mem[c][2];
            lidx = {24'b0, mem[c][15:8]}; sline = {24'b0, mem[c][23:16]};
            #1;
            $display("C %0d %0d %0d %0d %0d %0d %0d", c, byp, restr, ocr, ofr, ost, osr);
        end
        $display("DONE");
        $finish;
    end
endmodule
