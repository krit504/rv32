module rv32_top_pipelined(
    input logic clk,
    input logic rst_n
);


////////////////////////////////
////////////FETCH///////////////
////////////////////////////////

logic [31:0] instruction_imem_to_FETCH;
logic [31:0] PCPlus4F_to_FETCH;
logic [31:0] InstrD_from_FETCH;
logic [31:0] PCD_from_FETCH;
logic [31:0] PCPlus4D_from_FETCH;
logic [31:0] PCNext_pc_mux_to_pc;
logic [31:0] A_PC_to_imem_and_ALU;

f_d_reg u_f_d_reg(
    .clk(clk),
    .rst_n(rst_n),
    .StallD(StallD),
    .FlushD(FlushD),
    .InstrF(instruction_imem_to_FETCH),
    .PCF(A_PC_to_imem_and_ALU),
    .PCPlus4F(PCPlus4F_to_FETCH),
    .InstrD(InstrD_from_FETCH),
    .PCD(PCD_from_FETCH),
    .PCPlus4D(PCPlus4D_from_FETCH)
);

//PC

pc u_pc(
    .clk(clk),
    .rst_n(rst_n),
    .PCNext(PCNext_pc_mux_to_pc),
    .StallF(StallF),
    .PCOut(A_PC_to_imem_and_ALU)
);

//pc adder

assign PCPlus4F_to_FETCH=A_PC_to_imem_and_ALU+ 32'd4;

//next PC

assign PCNext_pc_mux_to_pc =
    (PCNextSelE == 2'b00) ? PCPlus4F_to_FETCH :
    (PCNextSelE == 2'b01) ? PCTargetE :
                             {ALUResultE[31:1], 1'b0};
//IMEM

imem u_imem(
    .A(A_PC_to_imem_and_ALU),
    .RD(instruction_imem_to_FETCH)
);



////////////////////////////////
////////////DECODE///////////////
////////////////////////////////


logic RegWrite_CU_to_DECODE;
logic [2:0] ImmSrc_CU_to_DECODE;
logic ALUSrc_CU_to_DECODE;
logic ALUSrcA_CU_to_DECODE;
logic MemWrite_CU_to_DECODE;
logic [1:0] ResultSrc_CU_to_DECODE;
logic [3:0] ALUControl_CU_to_DECODE;
logic [1:0] PCSrc_CU_to_DECODE;
logic [4:0] RdD_FETCH_to_DECODE;
logic Branch_CU_to_DECODE;

logic [31:0] RD1_REGFILE_to_DECODE;
logic [31:0] RD2_REGFILE_to_DECODE;

logic [31:0] ImmExt_to_DECODE;

assign RdD_FETCH_to_DECODE = InstrD_from_FETCH[11:7];

d_e_reg u_d_e_reg(
    .clk(clk),
    .rst_n(rst_n),
    .RD1(RD1_REGFILE_to_DECODE),
    .RD2(RD2_REGFILE_to_DECODE),
    .ImmExtD(ImmExt_to_DECODE),
    .RdD(RdD_FETCH_to_DECODE),
    .funct3D(InstrD_from_FETCH[14:12]),
    .PCD(PCD_from_FETCH),
    .PCPlus4D(PCPlus4D_from_FETCH),
    .RegWriteD(RegWrite_CU_to_DECODE),
    .ALUSrcD(ALUSrc_CU_to_DECODE),
    .ALUSrcAD(ALUSrcA_CU_to_DECODE),
    .MemWriteD(MemWrite_CU_to_DECODE),
    .BranchD(Branch_CU_to_DECODE),
    .ResultSrcD(ResultSrc_CU_to_DECODE),
    .ALUControlD(ALUControl_CU_to_DECODE),
    .PCSrcD(PCSrc_CU_to_DECODE),
    .Rs1D(InstrD_from_FETCH[19:15]),
    .Rs2D(InstrD_from_FETCH[24:20]),
    .FlushE(FlushE),
    .Rs1E(Rs1E),
    .Rs2E(Rs2E),
    .RD1E(RD1E),
    .RD2E(RD2E),
    .ImmExtE(ImmExtE),
    .RdE(RdE),
    .funct3E(funct3E),
    .PCE(PCE),
    .PCPlus4E(PCPlus4E),
    .RegWriteE(RegWriteE),
    .ALUSrcE(ALUSrcE),
    .ALUSrcAE(ALUSrcAE),
    .MemWriteE(MemWriteE),
    .BranchE(BranchE),
    .ResultSrcE(ResultSrcE),
    .ALUControlE(ALUControlE),
    .PCSrcE(PCSrcE)
);

//decode to execute signals
logic [31:0] RD1E;
logic [31:0] RD2E;
logic [31:0] ImmExtE;
logic [4:0] RdE;
logic [4:0] Rs1E;
logic [4:0] Rs2E;
logic [2:0] funct3E;
logic [31:0] PCE;
logic [31:0] PCPlus4E;
logic RegWriteE;
logic ALUSrcE;
logic ALUSrcAE;
logic MemWriteE;
logic BranchE;
logic [1:0] ResultSrcE;
logic [3:0] ALUControlE;
logic [1:0] PCSrcE;

//CONTROL UNIT

control_unit u_control_unit(
    .op(InstrD_from_FETCH[6:0]),
    .funct3(InstrD_from_FETCH[14:12]),
    .funct7_5(InstrD_from_FETCH[30]),
    .RegWrite(RegWrite_CU_to_DECODE),
    .ImmSrc(ImmSrc_CU_to_DECODE), 
    .ALUSrc(ALUSrc_CU_to_DECODE),
    .ALUSrcA(ALUSrcA_CU_to_DECODE),
    .MemWrite(MemWrite_CU_to_DECODE),
    .ResultSrc(ResultSrc_CU_to_DECODE), 
    .ALUControl(ALUControl_CU_to_DECODE),
    .Branch(Branch_CU_to_DECODE),
    .PCSrc(PCSrc_CU_to_DECODE)
);

//REGFILE

regfile u_regfile(
    .clk(clk),
    .rst_n(rst_n),
    .A1(InstrD_from_FETCH[19:15]),
    .A2(InstrD_from_FETCH[24:20]),
    .A3(RdW),
    .WD3(ResultW),
    .WE3(RegWriteW),
    .RD1(RD1_REGFILE_to_DECODE),
    .RD2(RD2_REGFILE_to_DECODE)
);

//EXTEND

immediate_generator u_immediate_generator(
    .instr(InstrD_from_FETCH[31:7]),
    .ImmSrc(ImmSrc_CU_to_DECODE),
    .ImmExt(ImmExt_to_DECODE)
);

////////////////////////////////
///////////EXECUTE//////////////
////////////////////////////////


logic [1:0] ForwardAE;
logic [1:0] ForwardBE;
logic StallF;
logic StallD;
logic FlushD;
logic FlushE;

hazard_unit u_hazard_unit(
    .Rs1D(InstrD_from_FETCH[19:15]),
    .Rs2D(InstrD_from_FETCH[24:20]),
    .Rs1E(Rs1E),
    .Rs2E(Rs2E),
    .RdE(RdE),
    .RdM(RdM),
    .RdW(RdW),
    .RegWriteE(RegWriteE),
    .RegWriteM(RegWriteM),
    .RegWriteW(RegWriteW),
    .ResultSrcE(ResultSrcE),
    .PCNextSelE(PCNextSelE),
    .ForwardAE(ForwardAE),
    .ForwardBE(ForwardBE),
    .StallF(StallF),
    .StallD(StallD),
    .FlushD(FlushD),
    .FlushE(FlushE)
);

logic [31:0] FwdDataM;
logic [31:0] FwdRD1E;
logic [31:0] FwdRD2E;
logic [31:0] WriteDataE;
logic [31:0] SrcAE;
logic [31:0] SrcBE;

assign FwdDataM = (ResultSrcM == 2'b10) ? ImmExtM  :
                  (ResultSrcM == 2'b11) ? PCPlus4M :
                                           ALUResultM;

assign FwdRD1E = (ForwardAE == 2'b10) ? FwdDataM :
                 (ForwardAE == 2'b01) ? ResultW  :
                                         RD1E;

assign FwdRD2E = (ForwardBE == 2'b10) ? FwdDataM :
                 (ForwardBE == 2'b01) ? ResultW  :
                                         RD2E;

assign SrcAE      = ALUSrcAE ? PCE     : FwdRD1E;
assign SrcBE      = ALUSrcE  ? ImmExtE : FwdRD2E;
assign WriteDataE = FwdRD2E;

logic [31:0] ALUResultE;
logic ZeroE;

logic [31:0] PCTargetE;

assign PCTargetE=PCE+ImmExtE;

logic takenE;

always_comb begin
    takenE = 1'b0;
    case(funct3E)
    3'b000: begin //BEQ
        if(ZeroE) begin
            takenE=1;
        end
    end
    3'b001: begin //BNE
        if(ZeroE==0) begin
            takenE=1;
        end
    end
    3'b100: begin //BLT
        if(ALUResultE[0]==1) begin
            takenE=1;
        end
    end
    3'b101: begin //BLT
        if(ALUResultE[0]==0) begin
            takenE=1;
        end
    end
    3'b110: begin //BLTU
        if(ALUResultE[0]==1) begin
            takenE=1;
        end
    end
    3'b111: begin //BGEU
        if(ALUResultE[0]==0) begin
            takenE=1;
        end
    end
    default: takenE=0;
    endcase
end

logic [1:0] PCNextSelE;

assign PCNextSelE  = (PCSrcE != 2'b00)      ? PCSrcE :   // jal (01) or jalr (10), opcode-forced
              (BranchE & takenE)     ? 2'b01  :   // branch actually taken
                                        2'b00;    // default: sequential


//ALU

//ALU srcb mux

alu u_alu(
    .SrcA(SrcAE),
    .SrcB(SrcBE),
    .ALUControl(ALUControlE),
    .ALUResult(ALUResultE),
    .Zero(ZeroE)
);

e_m_reg u_e_m_reg(
    .clk(clk),
    .rst_n(rst_n),
    .ALUResultE(ALUResultE),
    .WriteDataE(WriteDataE),
    .PCPlus4E(PCPlus4E),
    .RdE(RdE),
    .ImmExtE(ImmExtE),
    .RegWriteE(RegWriteE),
    .MemWriteE(MemWriteE),
    .ResultSrcE(ResultSrcE),
    .ALUResultM(ALUResultM),
    .WriteDataM(WriteDataM),
    .PCPlus4M(PCPlus4M),
    .RdM(RdM),
    .ImmExtM(ImmExtM),
    .RegWriteM(RegWriteM),
    .MemWriteM(MemWriteM), 
    .ResultSrcM(ResultSrcM)
);

////////////////////////////////
///////MEMORY/WRITEBACK/////////
////////////////////////////////

logic [31:0] WriteDataM;
logic [31:0] ALUResultM;
logic [31:0] PCPlus4M;
logic [4:0] RdM;
logic [31:0] ImmExtM;
logic [1:0] ResultSrcM;
logic [1:0] ResultSrcW;
logic RegWriteM;
logic MemWriteM;

logic [4:0] RdW;
logic [31:0] ResultW;
logic RegWriteW;

logic [31:0] ReadDataM;
logic [31:0] ReadDataW;
logic [31:0] ALUResultW;

logic [31:0] PCPlus4W;
logic [31:0] ImmExtW;



m_w_reg u_m_w_reg(
    .clk(clk),
    .rst_n(rst_n),
    .ReadDataM(ReadDataM),
    .ALUResultM(ALUResultM),
    .RdM(RdM),
    .PCPlus4M(PCPlus4M),
    .ImmExtM(ImmExtM),
    .RegWriteM(RegWriteM),
    .ResultSrcM(ResultSrcM),
    .ReadDataW(ReadDataW),
    .ALUResultW(ALUResultW),
    .RdW(RdW),
    .PCPlus4W(PCPlus4W),
    .ImmExtW(ImmExtW),
    .RegWriteW(RegWriteW),
    .ResultSrcW(ResultSrcW)
);

//DMEM

dmem u_dmem(
    .clk(clk),
    .A(ALUResultM),
    .WD(WriteDataM),
    .WE(MemWriteM),
    .RD(ReadDataM)
);

assign ResultW = (ResultSrcW == 2'b00) ? ALUResultW :
                 (ResultSrcW == 2'b01) ? ReadDataW  :
                 (ResultSrcW == 2'b10) ? ImmExtW    :
                                          PCPlus4W;


endmodule