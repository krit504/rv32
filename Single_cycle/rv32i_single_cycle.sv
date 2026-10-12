module rv32_top(
    input logic clk,
    input logic rst_n
);


//CONTROL UNIT 

// inputs to cu 
logic [6:0] op_imem_to_cu;
logic [2:0] funct3_imem_to_cu;
logic funct7_5_imem_to_cu;
logic Zero_ALU_to_cu; 
logic [4:0] rs1_imem_to_regfile; 
logic [4:0] rs2_imem_to_regfile;
logic [4:0] a3_imem_to_regfile;
logic [24:0] imm_ext_imem_to_regfile; 

// outputs to cu
logic RegWrite_cu_to_regfile;
logic [2:0] ImmSrc_cu_to_extend; 
logic ALUSrc_cu_to_ALU_SrcB_mux;
logic MemWrite_cu_to_dmem; 
logic [1:0] ResultSrc_cu_to_Result_mux; 
logic [3:0] ALUControl_cu_to_ALU; 
logic [1:0] PCSrc_cu_to_PC_mux; 
logic ALUSrcA_cu_to_SrcA_mux;
logic ALUResult0_cu;

control_unit u_control_unit(
    .op(op_imem_to_cu),
    .funct3(funct3_imem_to_cu),
    .funct7_5(funct7_5_imem_to_cu),
    .Zero(Zero_ALU_to_cu),
    .RegWrite(RegWrite_cu_to_regfile),
    .ImmSrc(ImmSrc_cu_to_extend), 
    .ALUSrc(ALUSrc_cu_to_ALU_SrcB_mux),
    .ALUSrcA(ALUSrcA_cu_to_SrcA_mux),
    .MemWrite(MemWrite_cu_to_dmem),
    .ResultSrc(ResultSrc_cu_to_Result_mux), 
    .ALUControl(ALUControl_cu_to_ALU),
    .PCSrc(PCSrc_cu_to_PC_mux),
    .ALUResult0(ALUResult0_cu)
);

//IMEM

logic [31:0] A_PC_to_imem_and_ALU; 
logic [31:0] instruction_imem_to_regfile;

imem u_imem(
    .A(A_PC_to_imem_and_ALU),
    .RD(instruction_imem_to_regfile)
);

assign op_imem_to_cu=instruction_imem_to_regfile[6:0];
assign funct3_imem_to_cu=instruction_imem_to_regfile[14:12];
assign funct7_5_imem_to_cu=instruction_imem_to_regfile[30];
assign rs1_imem_to_regfile=instruction_imem_to_regfile[19:15];
assign rs2_imem_to_regfile=instruction_imem_to_regfile[24:20];
assign a3_imem_to_regfile=instruction_imem_to_regfile[11:7];
assign imm_ext_imem_to_regfile=instruction_imem_to_regfile[31:7];

//REGFILE
logic [31:0] Result; 
logic [31:0] RD1_regfile_to_SrcA;
logic [31:0] RD2_regfile_to_ALU_SrcB_mux;

regfile u_regfile(
    .clk(clk),
    .rst_n(rst_n),
    .A1(rs1_imem_to_regfile),
    .A2(rs2_imem_to_regfile),
    .A3(a3_imem_to_regfile),
    .WD3(Result),
    .WE3(RegWrite_cu_to_regfile),
    .RD1(RD1_regfile_to_SrcA),
    .RD2(RD2_regfile_to_ALU_SrcB_mux)
);


//ALU
logic [31:0] SrcA_mux_to_ALU_SRCA;
logic [31:0] SrcB_mux_to_ALU_SRCB;
logic [31:0] ALUResult_ALU_to_DMEM_AND_MUX;
logic [31:0] imm_ext_Extend_to_ALU_MUX;

//ALU srcb mux
assign SrcB_mux_to_ALU_SRCB=ALUSrc_cu_to_ALU_SrcB_mux?imm_ext_Extend_to_ALU_MUX: RD2_regfile_to_ALU_SrcB_mux;
assign SrcA_mux_to_ALU_SRCA=ALUSrcA_cu_to_SrcA_mux?A_PC_to_imem_and_ALU: RD1_regfile_to_SrcA;

assign ALUResult0_cu=ALUResult_ALU_to_DMEM_AND_MUX[0];

alu u_alu(
    .SrcA(SrcA_mux_to_ALU_SRCA),//replace with SrcA_mux_to_ALU_SRCA
    .SrcB(SrcB_mux_to_ALU_SRCB),
    .ALUControl(ALUControl_cu_to_ALU),
    .ALUResult(ALUResult_ALU_to_DMEM_AND_MUX),
    .Zero(Zero_ALU_to_cu)
);

//EXTEND

immediate_generator u_immediate_generator(
    .instr(imm_ext_imem_to_regfile),
    .ImmSrc(ImmSrc_cu_to_extend),
    .ImmExt(imm_ext_Extend_to_ALU_MUX)
);

//PC

logic [31:0] PCNext_pc_mux_to_pc;

pc u_pc(
    .clk(clk),
    .rst_n(rst_n),
    .PCNext(PCNext_pc_mux_to_pc),
    .PCOut(A_PC_to_imem_and_ALU)
);

//PC inc
logic [31:0] PCPlus4;

assign PCPlus4=A_PC_to_imem_and_ALU+4;

//pc next mux

logic [31:0] PCTarget_pc_jump_to_mux; 

assign PCNext_pc_mux_to_pc=(PCSrc_cu_to_PC_mux==2'b00) ? PCPlus4 :
              (PCSrc_cu_to_PC_mux==2'b01) ? PCTarget_pc_jump_to_mux : 
               {ALUResult_ALU_to_DMEM_AND_MUX[31:1],1'b0} ; 
//pc jump

assign PCTarget_pc_jump_to_mux=A_PC_to_imem_and_ALU+imm_ext_Extend_to_ALU_MUX;

//DMEM

logic [31:0] ReadData;

dmem u_dmem(
    .clk(clk),
    .A(ALUResult_ALU_to_DMEM_AND_MUX),
    .WD(RD2_regfile_to_ALU_SrcB_mux),
    .WE(MemWrite_cu_to_dmem),
    .RD(ReadData)
);

//dmem mux

assign Result=(ResultSrc_cu_to_Result_mux==2'b00) ? ALUResult_ALU_to_DMEM_AND_MUX :
              (ResultSrc_cu_to_Result_mux==2'b01) ? ReadData : 
              (ResultSrc_cu_to_Result_mux==2'b10) ? imm_ext_Extend_to_ALU_MUX :  PCPlus4 ; 


endmodule