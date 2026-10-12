module d_e_reg(
    input logic clk,
    input logic rst_n,
    input logic [31:0] RD1,
    input logic [31:0] RD2,
    input logic [31:0] ImmExtD,
    input logic [4:0] RdD,
    input logic [2:0] funct3D,
    input logic [31:0] PCD,
    input logic [31:0] PCPlus4D,
    input logic RegWriteD,
    input logic ALUSrcD,
    input logic ALUSrcAD,
    input logic MemWriteD,
    input logic BranchD,
    input logic [1:0] ResultSrcD,
    input logic [3:0] ALUControlD,
    input logic [1:0] PCSrcD,
    output logic [31:0] RD1E,
    output logic [31:0] RD2E,
    output logic [31:0] ImmExtE,
    output logic [4:0] RdE,
    output logic [2:0] funct3E,
    output logic [31:0] PCE,
    output logic [31:0] PCPlus4E,
    output logic RegWriteE,
    output logic ALUSrcE,
    output logic ALUSrcAE,
    output logic MemWriteE,
    output logic BranchE,
    output logic [1:0] ResultSrcE,
    output logic [3:0] ALUControlE,
    output logic [1:0] PCSrcE
);

always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        RD1E <= '0; RD2E <= '0; ImmExtE <= '0; RdE <= '0; funct3E <= '0;
        PCE <= '0; PCPlus4E <= '0;
        RegWriteE <= '0; ALUSrcE <= '0; ALUSrcAE <= '0; MemWriteE <= '0; BranchE <= '0;
        ResultSrcE <= '0; ALUControlE <= '0; PCSrcE <= '0;
        end 
    else begin
        RD1E <= RD1; RD2E <= RD2; ImmExtE <= ImmExtD; RdE <= RdD; funct3E <= funct3D;
        PCE <= PCD; PCPlus4E <= PCPlus4D;
        RegWriteE <= RegWriteD; ALUSrcE <= ALUSrcD; ALUSrcAE <= ALUSrcAD; MemWriteE <= MemWriteD; BranchE <= BranchD;
        ResultSrcE <= ResultSrcD; ALUControlE <= ALUControlD; PCSrcE <= PCSrcD;
    end
end
endmodule
