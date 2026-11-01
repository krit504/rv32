module immediate_generator(
    input logic [24:0] instr,
    input logic [2:0] ImmSrc,
    output logic [31:0] ImmExt 
);

always_comb begin
    if(ImmSrc==3'b000) begin
        ImmExt={{20{instr[24]}}, instr[24:13]}; //SUPPORT FOR I TYPE INST
    end
    else if(ImmSrc==3'b001) begin
        ImmExt={{20{instr[24]}}, instr[24:18], instr[4:0]}; //SUPPORT FOR S TYPE INST
    end
    else if(ImmSrc==3'b010) begin
        ImmExt={{20{instr[24]}}, instr[0], instr[23:18], instr[4:1],1'b0}; //SUPPORT FOR BRANCHES
    end
    else if(ImmSrc==3'b011) begin
        ImmExt={instr[24:5],12'b0}; //SUPPORT FOR U TYPE INSTRUCTIONS
    end
    else if(ImmSrc==3'b100) begin
        ImmExt={{11{instr[24]}}, instr[24], instr[12:5], instr[13],instr[23:14],1'b0}; //SUPPORT FOR JAL
    end
    else  begin
        ImmExt={32'bx}; //TIE OFF
    end

end

endmodule
