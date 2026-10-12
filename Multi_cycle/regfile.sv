module regfile (
    input logic clk,
    input logic rst_n,
    input logic [4:0] A1,
    input logic [4:0] A2,
    input logic [4:0] A3,
    input logic [31:0] WD3,
    input logic WE3,
    output logic [31:0] RD1,
    output logic [31:0] RD2
);

logic [31:0] regs [0:31];

always_ff @( negedge clk or negedge rst_n ) begin
    if(!rst_n) begin
        for(int i=0;i<32;i++) regs[i]<=32'b0;
    end
    else if(WE3 && A3 != 5'd0) begin
        regs[A3]<=WD3;
    end
end

always_comb begin
    RD1=(A1==5'd0) ? 32'b0 : regs[A1]; 
    RD2=(A2==5'd0) ? 32'b0 : regs[A2];
end
    
endmodule
