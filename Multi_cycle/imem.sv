module imem #(parameter DEPTH = 256)
(
    input logic[31:0] A,
    output logic [31:0] RD
);

logic [31:0] mem [0: DEPTH-1];

initial begin
    $readmemh("program.hex", mem);
end

always_comb begin
    RD=mem[A[$clog2(DEPTH)+1:2]];
end
endmodule