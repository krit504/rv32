module imem #(parameter DEPTH = 256, parameter INIT_FILE = "program.hex")
(
    input logic[31:0] A,
    output logic [31:0] RD
);

logic [31:0] mem [0: DEPTH-1];

// Zero first, then overlay the image: words past the end of the image are 0 (a no-op), not x.
initial begin
    for (int i = 0; i < DEPTH; i++) mem[i] = 32'b0;
    $readmemh(INIT_FILE, mem);
end

always_comb begin
    RD=mem[A[$clog2(DEPTH)+1:2]];
end
endmodule
