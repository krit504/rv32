module pc #(parameter logic [31:0] RESET_PC = 32'h0)(
    input logic clk,
    input logic rst_n,
    input logic [31:0] PCNext,
    input logic StallF,
    output logic [31:0] PCOut
);

always_ff @( posedge clk or negedge rst_n ) begin
    if(!rst_n) begin
        PCOut<=RESET_PC;
    end
    else if(!StallF) begin
        PCOut<=PCNext;
    end
end
    
endmodule
