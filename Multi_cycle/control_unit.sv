module control_unit(
    input  logic [6:0] op,
    input  logic [2:0] funct3,
    input  logic funct7_5,
    output logic RegWrite,
    output logic [2:0] ImmSrc,
    output logic ALUSrc,
    output logic ALUSrcA,
    output logic MemWrite,
    output logic Branch,  
    output logic [1:0] ResultSrc,
    output logic [3:0] ALUControl,
    output logic [1:0] PCSrc
);

logic [1:0] ALUOp;
logic op5;

assign op5 = op[5];

main_decoder u_main_decoder (
    .op(op),
    .RegWrite(RegWrite),
    .ImmSrc(ImmSrc), 
    .ALUSrc(ALUSrc),
    .ALUSrcA(ALUSrcA),
    .MemWrite(MemWrite),
    .ResultSrc(ResultSrc),
    .Branch(Branch),
    .ALUOp(ALUOp),
    .PCSrc(PCSrc)
);

alu_decoder u_alu_decoder (
    .ALUOp(ALUOp),
    .funct3(funct3),
    .op5(op5),
    .funct7_5(funct7_5),
    .ALUControl(ALUControl)
);


endmodule