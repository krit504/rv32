module hazard_unit(
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
logic redirectE;

assign ForwardAE = ((Rs1E == RdM) && RegWriteM && (RdM != 5'd0)) ? 2'b10 :
                   ((Rs1E == RdW) && RegWriteW && (RdW != 5'd0)) ? 2'b01 :
                                                                    2'b00;

assign ForwardBE = ((Rs2E == RdM) && RegWriteM && (RdM != 5'd0)) ? 2'b10 :
                   ((Rs2E == RdW) && RegWriteW && (RdW != 5'd0)) ? 2'b01 :
                                                                    2'b00;

// RegWriteE qualifies the load: sw/branch carry ResultSrc = xx (don't care) and an
// "rd" field that is really immediate bits, so (ResultSrcE == 01) alone can be X.
assign lwStall   = ((Rs1D == RdE) || (Rs2D == RdE)) && RegWriteE && (ResultSrcE == 2'b01) && (RdE != 5'd0);
assign redirectE = (PCNextSelE != 2'b00);

assign StallF = lwStall;
assign StallD = lwStall;
assign FlushD = redirectE;
assign FlushE = lwStall | redirectE;

endmodule
