module m_w_reg(
    input logic clk,
    input logic rst_n,
    input logic [31:0] ReadDataM,
    input logic [31:0] ALUResultM,
    input logic [4:0] RdM,
    input logic [31:0] PCPlus4M,
    input logic [31:0] ImmExtM,
    input logic RegWriteM,
    input logic [1:0] ResultSrcM,
    output logic [31:0] ReadDataW,
    output logic [31:0] ALUResultW,
    output logic [4:0] RdW,
    output logic [31:0] PCPlus4W,
    output logic [31:0] ImmExtW,
    output logic RegWriteW,
    output logic [1:0] ResultSrcW
);

always_ff @(posedge clk or negedge rst_n) begin
    if(!rst_n) begin
        {ReadDataW,ALUResultW,RdW,PCPlus4W,ImmExtW,RegWriteW,ResultSrcW} <='0;
    end
    else begin
        {ReadDataW,ALUResultW,RdW,PCPlus4W,ImmExtW,RegWriteW,ResultSrcW}<={ReadDataM,ALUResultM,RdM,PCPlus4M,ImmExtM,RegWriteM,ResultSrcM};
    end
end
endmodule
