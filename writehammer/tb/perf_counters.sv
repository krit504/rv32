// Simulation-only instrumentation. Instantiate from a testbench with hierarchical
// connections; the core itself carries no valid bits.
//
// Retirement: a flushed bubble and a retired sw/beq look identical at Writeback
// (every write enable is 0 and Branch was dropped before E), so retirement is
// tracked with a shadow valid bit shifted through the pipeline using the same
// StallD / FlushD / FlushE enables the real registers use.
//
// Window: counting runs from reset until the last instruction below END_PC has
// retired, so padding NOPs past the program never count.
module perf_counters #(
    parameter int FORWARDING = 1,
    parameter int END_PC     = 0
)(
    input  logic        clk,
    input  logic        rst_n,
    input  logic [31:0] PCF,
    input  logic [31:0] InstrD,
    input  logic        StallF,
    input  logic        StallD,
    input  logic        FlushD,
    input  logic        FlushE,
    input  logic [4:0]  RdE,
    input  logic [4:0]  RdM,
    input  logic        RegWriteE,
    input  logic        RegWriteM,
    input  logic [1:0]  ResultSrcE,
    output logic [31:0] cycles,
    output logic [31:0] stall_cycles,
    output logic [31:0] flush_cycles,
    output logic [31:0] retired,
    output logic [31:0] spurious_stalls,
    output logic        done
);

// Pipeline fill: the first instruction needs 4 more cycles to reach Writeback, so a hazard-free
// run of N instructions takes N + FILL_CYCLES cycles. Reported separately from CPI_steady.
localparam int FILL_CYCLES = 4;

logic validD, validE, validM, validW;
logic validF;

assign validF = (PCF < END_PC);
assign done   = !validF && !validD && !validE && !validM && !validW;

// Does the instruction in Decode actually read rs1 / rs2?
logic [6:0] op;
logic [4:0] rs1, rs2;
logic uses1, uses2;
assign op   = InstrD[6:0];
assign rs1  = InstrD[19:15];
assign rs2  = InstrD[24:20];
assign uses1 = !(op == 7'b0110111 || op == 7'b0010111 || op == 7'b1101111);   // not lui/auipc/jal
assign uses2 =  (op == 7'b0110011 || op == 7'b0100011 || op == 7'b1100011);   // R-type, store, branch

logic depE, depM, trueStall;
assign depE = RegWriteE && (RdE != 5'd0) && ((uses1 && rs1 == RdE) || (uses2 && rs2 == RdE));
assign depM = RegWriteM && (RdM != 5'd0) && ((uses1 && rs1 == RdM) || (uses2 && rs2 == RdM));
assign trueStall = (FORWARDING != 0) ? (ResultSrcE == 2'b01 && depE) : (depE || depM);

always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        {validD, validE, validM, validW} <= '0;
        cycles <= '0; stall_cycles <= '0; flush_cycles <= '0; retired <= '0; spurious_stalls <= '0;
    end else begin
        validD <= FlushD ? 1'b0 : (StallD ? validD : validF);
        validE <= FlushE ? 1'b0 : validD;
        validM <= validE;
        validW <= validM;

        if (validW) retired <= retired + 1;
        if (!done) begin
            cycles <= cycles + 1;
            if (StallF)           stall_cycles    <= stall_cycles + 1;
            if (FlushD)           flush_cycles    <= flush_cycles + 1;
            if (StallF && !trueStall) spurious_stalls <= spurious_stalls + 1;
        end
    end
end

// One summary line per run. Branch flush cycles are counted as 2 per taken redirect
// (FlushD cycles x 2: the two wrong-path instructions behind it). With FORWARDING = 0 the
// stall column holds dependency stalls instead of load-use stalls.
task report;
    real cpi_raw, cpi_steady, stall_pi, flush_pi, spur_pi;
    string stall_lbl;
    begin
        if (FORWARDING != 0) stall_lbl = "load_use_stall_per_instr";
        else                 stall_lbl = "dep_stall_per_instr";
        if (retired == 0) begin
            cpi_raw = 0.0; cpi_steady = 0.0; stall_pi = 0.0; flush_pi = 0.0; spur_pi = 0.0;
        end else begin
            cpi_raw    = $itor(cycles) / $itor(retired);
            cpi_steady = $itor(cycles - FILL_CYCLES) / $itor(retired);
            stall_pi   = $itor(stall_cycles) / $itor(retired);
            flush_pi   = $itor(2 * flush_cycles) / $itor(retired);
            spur_pi    = $itor(spurious_stalls) / $itor(retired);
        end
        $display("METRICS cycles=%0d retired=%0d fill_cycles=%0d stall_cycles=%0d branch_flush_cycles=%0d spurious_stalls=%0d CPI_raw=%0.3f CPI_steady=%0.3f %0s=%0.3f branch_flush_per_instr=%0.3f spurious_per_instr=%0.3f identity=%0s",
                 cycles, retired, FILL_CYCLES, stall_cycles, 2 * flush_cycles, spurious_stalls,
                 cpi_raw, cpi_steady, stall_lbl, stall_pi, flush_pi, spur_pi,
                 (cycles == retired + stall_cycles + 2 * flush_cycles + FILL_CYCLES) ? "ok" : "FAIL");
    end
endtask

endmodule
