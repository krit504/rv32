module control_unit(
    input  logic [6:0] op,
    input  logic [2:0] funct3,
    input  logic funct7_5,
    input  logic Zero,
    input  logic ALUResult0, 
    output logic RegWrite,
    output logic [2:0] ImmSrc,
    output logic ALUSrc,
    output logic ALUSrcA,
    output logic MemWrite,
    output logic [1:0] ResultSrc,
    output logic [3:0] ALUControl,
    output logic [1:0] PCSrc
);

logic Branch;
logic [1:0] ALUOp;
logic op5;

assign op5 = op[5];

logic [1:0] PCSrc_from_main_decoder;

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
    .PCSrc(PCSrc_from_main_decoder)
);

alu_decoder u_alu_decoder (
    .ALUOp(ALUOp),
    .funct3(funct3),
    .op5(op5),
    .funct7_5(funct7_5),
    .ALUControl(ALUControl)
);

logic taken;
always_comb begin
    taken = 1'b0;
    case(funct3)
        3'b000: taken = Zero;
        3'b001: taken = ~Zero;
        3'b100: taken = ALUResult0;
        3'b101: taken = ~ALUResult0;
        3'b110: taken = ALUResult0;
        3'b111: taken = ~ALUResult0;
        default: taken = 1'b0;
    endcase
end

assign PCSrc = (PCSrc_from_main_decoder != 2'b00) ? PCSrc_from_main_decoder :
               (Branch & taken)                    ? 2'b01 : 2'b00;

endmodule