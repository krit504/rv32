module e_m_reg(
    input logic clk,
    input logic rst_n,
    input logic [31:0] ALUResultE,
    input logic [31:0] WriteDataE,
    input logic [31:0] PCPlus4E,
    input logic [4:0] RdE,
    input logic [31:0] ImmExtE,
    input logic RegWriteE,
    input logic MemWriteE,
    input logic [1:0] ResultSrcE,
    output logic [31:0] ALUResultM,
    output logic [31:0] WriteDataM,
    output logic [31:0] PCPlus4M,
    output logic [4:0] RdM,
    output logic [31:0] ImmExtM,
    output logic RegWriteM,
    output logic MemWriteM,
    output logic [1:0] ResultSrcM
);

always_ff @(posedge clk or negedge rst_n) begin
    if(!rst_n) begin
        {ALUResultM,WriteDataM,PCPlus4M,RdM,ImmExtM,RegWriteM,MemWriteM,ResultSrcM}<='0;
    end
    else begin
        {ALUResultM,WriteDataM} <={ALUResultE,WriteDataE};
        PCPlus4M<=PCPlus4E;
        {RdM,ImmExtM}<={RdE,ImmExtE};
        {RegWriteM,MemWriteM,ResultSrcM}<={RegWriteE,MemWriteE,ResultSrcE};
    end
end
endmodule
