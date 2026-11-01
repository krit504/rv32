module dmem#(parameter DEPTH=256)(
    input logic clk,
    input logic [31:0] A,
    input logic [31:0] WD,
    input logic WE,
    input logic [3:0] BE,   // byte enables (lane k = bits [8k+7:8k]); ignored unless WE
    output logic [31:0] RD
);

logic [31:0] mem [0:DEPTH-1];

// Zero-initialized, like the data backing_mem, so CACHES_ON=0 and CACHES_ON=1 start from the same
// memory state and a load from a never-written word reads 0 rather than x.
initial begin
    for (int i = 0; i < DEPTH; i++) mem[i] = 32'b0;
end

assign RD=mem[A[$clog2(DEPTH)+1:2]];

always_ff @(posedge clk) begin
    if(WE) begin
        for (int k = 0; k < 4; k++)
            if (BE[k]) mem[A[$clog2(DEPTH)+1:2]][8*k +: 8] <= WD[8*k +: 8];
    end
end
endmodule
