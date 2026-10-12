// FORWARDING = 1 : spec §13 behavior (forward from M/W, stall only for load-use).
// FORWARDING = 0 : ablation. No forwarding; instead stall the consumer in Decode
//                  until every producer ahead of it has reached Writeback. A
//                  producer in Writeback needs no stall: the negedge regfile
//                  write lands before the Decode-stage read is sampled.
module hazard_unit #(parameter int FORWARDING = 1)(
    input  logic [4:0] Rs1D,
    input  logic [4:0] Rs2D,
    input  logic [4:0] Rs1E,
    input  logic [4:0] Rs2E,
    input  logic [4:0] RdE,
    input  logic [4:0] RdM,
    input  logic [4:0] RdW,
    input  logic       RegWriteE,
    input  logic       RegWriteM,
    input  logic       RegWriteW,
    input  logic [1:0] ResultSrcE,
    input  logic [1:0] PCNextSelE,
    output logic [1:0] ForwardAE,
    output logic [1:0] ForwardBE,
    output logic       StallF,
    output logic       StallD,
    output logic       FlushD,
    output logic       FlushE
);

logic lwStall;
logic depStall;
logic stallCond;
logic redirectE;

generate
    if (FORWARDING != 0) begin : g_fwd
        assign ForwardAE = ((Rs1E == RdM) && RegWriteM && (RdM != 5'd0)) ? 2'b10 :
                           ((Rs1E == RdW) && RegWriteW && (RdW != 5'd0)) ? 2'b01 :
                                                                            2'b00;

        assign ForwardBE = ((Rs2E == RdM) && RegWriteM && (RdM != 5'd0)) ? 2'b10 :
                           ((Rs2E == RdW) && RegWriteW && (RdW != 5'd0)) ? 2'b01 :
                                                                            2'b00;
    end else begin : g_nofwd
        assign ForwardAE = 2'b00;
        assign ForwardBE = 2'b00;
    end
endgenerate

// RegWriteE qualifies the load: sw/branch carry ResultSrc = xx (don't care) and an
// "rd" field that is really immediate bits, so (ResultSrcE == 01) alone can be X.
assign lwStall   = ((Rs1D == RdE) || (Rs2D == RdE)) && RegWriteE && (ResultSrcE == 2'b01) && (RdE != 5'd0);
assign redirectE = (PCNextSelE != 2'b00);

// Ablation stall. Masked by redirectE: a redirect flushes the instruction in
// Decode anyway, and holding pc during a redirect would drop the new target.
assign depStall  = ((RegWriteE && (RdE != 5'd0) && ((Rs1D == RdE) || (Rs2D == RdE))) ||
                    (RegWriteM && (RdM != 5'd0) && ((Rs1D == RdM) || (Rs2D == RdM)))) && !redirectE;

assign stallCond = (FORWARDING != 0) ? lwStall : depStall;

assign StallF = stallCond;
assign StallD = stallCond;
assign FlushD = redirectE;
assign FlushE = stallCond | redirectE;

endmodule
