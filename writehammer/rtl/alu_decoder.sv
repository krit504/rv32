module alu_decoder(
    input  logic [1:0] ALUOp,
    input  logic [2:0] funct3,
    input  logic       op5,
    input  logic       funct7_5,
    output logic [3:0] ALUControl
);

    always_comb begin
        case (ALUOp)
            2'b00: begin //always add
                ALUControl = 4'b0000; //lw, sw, jalr, auipc
            end

            2'b01: begin //branch — operation depends on funct3
                if (funct3 == 3'b000) begin
                    ALUControl = 4'b0001; //beq — subtract, check Zero
                end
                else if (funct3 == 3'b001) begin
                    ALUControl = 4'b0001; //bne — subtract, check ~Zero
                end
                else if (funct3 == 3'b100) begin
                    ALUControl = 4'b0101; //blt — slt (signed), check ALUResult[0]
                end
                else if (funct3 == 3'b101) begin
                    ALUControl = 4'b0101; //bge — slt (signed), check ~ALUResult[0]
                end
                else if (funct3 == 3'b110) begin
                    ALUControl = 4'b0100; //bltu — sltu (unsigned), check ALUResult[0]
                end
                else begin
                    ALUControl = 4'b0100; //bgeu — sltu (unsigned), check ~ALUResult[0]
                end
            end

            2'b10: begin //R-type / I-type ALU — funct3 selects the operation
                if (funct3 == 3'b000) begin //add / addi / sub
                    if ({op5, funct7_5} != 2'b11) begin
                        ALUControl = 4'b0000; //add — addi (op5=0) always lands here
                    end
                    else begin
                        ALUControl = 4'b0001; //subtract — only genuine R-type sub
                    end
                end
                else if (funct3 == 3'b001) begin
                    ALUControl = 4'b0110; //sll / slli
                end
                else if (funct3 == 3'b010) begin
                    ALUControl = 4'b0101; //slt / slti
                end
                else if (funct3 == 3'b011) begin
                    ALUControl = 4'b0100; //sltu / sltiu
                end
                else if (funct3 == 3'b100) begin
                    ALUControl = 4'b1000; //xor / xori
                end
                else if (funct3 == 3'b101) begin //srl / srli / sra / srai
                    if (funct7_5) begin
                        ALUControl = 4'b1001; //sra / srai
                    end
                    else begin
                        ALUControl = 4'b0111; //srl / srli
                    end
                end
                else if (funct3 == 3'b110) begin
                    ALUControl = 4'b0011; //or / ori
                end
                else if (funct3 == 3'b111) begin
                    ALUControl = 4'b0010; //and / andi
                end
                else begin
                    ALUControl = 4'b0000; //unreachable — safe default
                end
            end

            default: begin //unrecognized ALUOp — safe default
                ALUControl = 4'b0000;
            end
        endcase
    end
endmodule
