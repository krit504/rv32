module f_d_reg(
    input logic clk,
    input logic rst_n,
    input logic [31:0] InstrF,
    input logic [31:0] PCF,
    input logic [31:0] PCPlus4F,
    output logic [31:0] InstrD,
    output logic [31:0] PCD,
    output logic [31:0] PCPlus4D
);
always_ff @(posedge clk or negedge rst_n) begin
    if(!rst_n) begin
        {InstrD, PCD, PCPlus4D} <='0;
    end
    else begin
        {InstrD, PCD, PCPlus4D} <={InstrF,PCF,PCPlus4F};
    end
end
endmodule
