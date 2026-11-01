module main_decoder(
    input  logic [6:0] op,
    output logic       RegWrite,
    output logic [2:0] ImmSrc, //chjanged
    output logic       ALUSrc,
    output logic       MemWrite,
    output logic [1:0] ResultSrc, //changed
    output logic [1:0] PCSrc, //new
    output logic       Branch,
    output logic [1:0] ALUOp,
    output logic       ALUSrcA
);

    // Every output is defined for every opcode. Don't-care (x) values here would cross
    // pipeline registers and can reach hazard/flush decisions (see spec failure-mode notes).
    always_comb begin
        if (op == 7'b0000011) begin // lw
            RegWrite  = 1;
            ImmSrc    = 3'b000;
            ALUSrc    = 1;
            MemWrite  = 0;
            ResultSrc = 2'b01;
            Branch    = 0;
            ALUOp     = 2'b00;
            PCSrc     = 2'b00;
            ALUSrcA   = 1'b0;
        end
        else if (op == 7'b0100011) begin // sw
            RegWrite  = 0;
            ImmSrc    = 3'b001;
            ALUSrc    = 1;
            MemWrite  = 1;
            ResultSrc = 2'b00;
            Branch    = 0;
            ALUOp     = 2'b00;
            PCSrc     = 2'b00;
            ALUSrcA   = 1'b0;
        end
        else if (op == 7'b0110011) begin // R-type: add, sub, and, or, xor, sll, srl, sra, slt, sltu
            RegWrite  = 1;
            ImmSrc    = 3'b000;
            ALUSrc    = 0;
            MemWrite  = 0;
            ResultSrc = 2'b00;
            Branch    = 0;
            ALUOp     = 2'b10;
            PCSrc     = 2'b00;
            ALUSrcA   = 1'b0;
        end
        else if (op == 7'b1100011) begin // branch: beq, bne, blt, bge, bltu, bgeu
            RegWrite  = 0;
            ImmSrc    = 3'b010;
            ALUSrc    = 0;
            MemWrite  = 0;
            ResultSrc = 2'b00;
            Branch    = 1;
            ALUOp     = 2'b01;
            PCSrc     = 2'b00;
            ALUSrcA   = 1'b0;
        end
        else if (op == 7'b0010011) begin // I TYPE
            RegWrite  = 1;
            ImmSrc    = 3'b000;
            ALUSrc    = 1;
            MemWrite  = 0;
            ResultSrc = 2'b00;
            Branch    = 0;
            ALUOp     = 2'b10;
            PCSrc     = 2'b00;
            ALUSrcA   = 1'b0;
        end
        else if (op == 7'b1101111) begin // JAL
            RegWrite  = 1;
            ImmSrc    = 3'b100;
            ALUSrc    = 1'b0;
            MemWrite  = 0;
            ResultSrc = 2'b11;
            Branch    = 0;
            ALUOp     = 2'b00;
            PCSrc     = 2'b01;
            ALUSrcA   = 1'b0;
        end
        else if (op == 7'b1100111) begin // JALR
            RegWrite  = 1;
            ImmSrc    = 3'b000;
            ALUSrc    = 1'b1;
            MemWrite  = 0;
            ResultSrc = 2'b11;
            Branch    = 0;
            ALUOp     = 2'b00;
            PCSrc     = 2'b10;
            ALUSrcA   = 1'b0;
        end
        else if (op == 7'b0110111) begin // LUI
            RegWrite  = 1;
            ImmSrc    = 3'b011;
            ALUSrc    = 1'b0;
            MemWrite  = 0;
            ResultSrc = 2'b10;
            Branch    = 0;
            ALUOp     = 2'b00;
            PCSrc     = 2'b00;
            ALUSrcA   = 1'b0;
        end
        else if (op == 7'b0010111) begin // AUIPC
            RegWrite  = 1;
            ImmSrc    = 3'b011;
            ALUSrc    = 1;
            MemWrite  = 0;
            ResultSrc = 2'b00;
            Branch    = 0;
            ALUOp     = 2'b00;
            PCSrc     = 2'b00;
            ALUSrcA   = 1'b1;
        end
        else begin // unrecognized opcode — safe default
            RegWrite  = 1'b0;
            ImmSrc    = 3'b000;
            ALUSrc    = 1'b0;
            MemWrite  = 1'b0;
            ResultSrc = 2'b00;
            Branch    = 1'b0;
            ALUOp     = 2'b00;
            PCSrc     = 2'b00;
            ALUSrcA   = 1'b0;
        end
    end
endmodule
