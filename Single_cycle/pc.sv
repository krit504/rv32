module pc(
    input logic clk,
    input logic rst_n,
    input logic [31:0] PCNext,
    output logic [31:0] PCOut
);

always_ff @( posedge clk or negedge rst_n ) begin
    if(!rst_n) begin
        PCOut<=0;
    end
    else begin
        PCOut<=PCNext;
    end
end
    
endmodule