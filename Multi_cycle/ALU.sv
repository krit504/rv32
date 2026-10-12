module alu(
    input logic [31:0] SrcA,
    input logic [31:0] SrcB,
    input logic [3:0] ALUControl,
    output logic [31:0] ALUResult,
    output logic Zero
);
always_comb begin
    
    if(ALUControl==4'b0000) begin //ADD
        ALUResult=SrcA+SrcB; 
    end
    else if(ALUControl==4'b0001) begin //SUB
        ALUResult=SrcA-SrcB;
    end
    else if(ALUControl==4'b0010) begin //AND
        ALUResult=SrcA & SrcB;
    end
    else if(ALUControl==4'b0011) begin //OR
        ALUResult=SrcA | SrcB;
    end
    else if(ALUControl==4'b0100) begin 
        ALUResult=((SrcA<SrcB) ? 32'd1 : 32'd0); //SLTU
    end
    else if(ALUControl==4'b0101) begin 
        ALUResult=($signed(SrcA)<$signed(SrcB) ? 32'd1 : 32'd0); //SLT
    end
    else if(ALUControl==4'b0110) begin 
        ALUResult=(SrcA<<SrcB[4:0]); //SLL
    end
    else if(ALUControl==4'b0111) begin 
        ALUResult=(SrcA>>SrcB[4:0]); //SRL
    end
    else if(ALUControl==4'b1000) begin 
        ALUResult=(SrcA^SrcB); //XOR
    end
    else  begin
        ALUResult=($signed(SrcA)>>>$signed(SrcB[4:0])); //SRA
    end

    Zero=(ALUResult==0);

end
endmodule