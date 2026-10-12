module dmem#(parameter DEPTH=256)(
    input logic clk,
    input logic [31:0] A,
    input logic [31:0] WD,
    input logic WE,
    output logic [31:0] RD
);

logic [31:0] mem [0:DEPTH-1];

assign RD=mem[A[$clog2(DEPTH)+1:2]];

always_ff @(posedge clk) begin
    if(WE) begin
        mem[A[$clog2(DEPTH)+1:2]]<=WD;
    end
end
endmodule