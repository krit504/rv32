module rv32_top_pipelined #(
    parameter int FORWARDING  = 1,
    parameter bit CACHES_ON   = 1'b1,
    parameter int MEM_LATENCY = 10,
    // Cache geometry (spec Section 3 primary configuration: 2 KiB each, 16-byte lines, direct-mapped)
    // and memory/array timing, used when CACHES_ON = 1.
    parameter int ICACHE_BYTES = 2048,
    parameter int DCACHE_BYTES = 2048,
    parameter int LINE_BYTES = 16,
    parameter bit MEM_RANDOM_LATENCY = 1'b0,      // 1: per-request latency uniform in 1..2*MEM_LATENCY-1 (seeded)
    parameter int MEM_SEED = 1,                   // seed of the random latency
    parameter int DC_WRITE_LATENCY = 1,           // extra pipeline cycles per D$ array write (1 = none)
    parameter int INJECT_STALL_SEED = 0,           // test only (T2.2): non-zero adds random freezes and fetch bubbles, see below
    parameter int DETECTOR = 0,                   // write_guard: 0 NONE, 1 ALWAYS, 2 D1, 3 D2, 4 D3, 5 NEVER, 6 PLACEBO
    parameter int WG_ACTION = 0,                  // 0 = A1 (bypass)
    parameter int WG_MODE = 0,                    // D3: 0 STATIC, 1 ADAPTIVE
    parameter int WG_WINDOW = 10000,
    parameter int WG_THRESHOLD = 1000,
    parameter int WG_M = 16,
    parameter int WG_W = 16,
    parameter int WG_PLACEBO_RATE = 0,            // PLACEBO restricted fraction in 1/65536
    parameter int WG_PLACEBO_SEED = 1,
    parameter bit OBSERVE = 1'b1,                 // 0 compiles the write_guard observation counters out
    parameter IMEM_FILE = "program.hex",   // untyped on purpose: Icarus 12 cannot bind a string-typed parameter inside generate blocks
    // Words in main memory: each of imem and dmem with CACHES_ON = 0, the one unified memory with
    // CACHES_ON = 1 (256 = 1 KiB, the default the earlier tests rely on; the C flow uses 65536 =
    // 256 KiB). Addresses wrap modulo this size.
    parameter int MEM_WORDS   = 256,
    // 1: the data memory is also loaded from IMEM_FILE, so a linked image's initialized .data and
    // .rodata are present at their linked addresses (CACHES_ON = 0; the unified memory of
    // CACHES_ON = 1 always holds the whole image). Code and data regions are disjoint (T2.5).
    parameter bit DMEM_FROM_IMAGE = 1'b0,
    // Address of the first instruction after reset. The memories ignore high address bits, so an
    // image linked at 0x8000_0000 (the architectural tests, which Spike also runs there) sits at
    // word 0.
    parameter logic [31:0] RESET_PC = 32'h0
)(
    input  logic        clk,
    input  logic        rst_n,
    // Observation outputs for testbenches (cache counters, first four data-memory words).
    // Tied to zero when CACHES_ON = 0, except dbg_dmem, which then reads dmem.
    output logic [31:0] ic_refill_cnt,
    output logic [31:0] dc_refill_cnt,
    output logic [31:0] dc_write_cnt,
    // D$ observation (zero when CACHES_ON = 0): data-array write events, per-request trace, counters.
    output logic        dc_aw_valid,
    output logic [31:0] dc_aw_line,
    output logic        dc_aw_kind,
    output logic        dc_tr_valid,
    output logic        dc_tr_we,
    output logic [31:0] dc_tr_addr,
    output logic [2:0]  dc_tr_size,
    output logic        dc_tr_bypass,
    output logic [31:0] dc_cnt_access,
    output logic [31:0] dc_cnt_hit,
    output logic [31:0] dc_cnt_miss,
    output logic [31:0] dc_cnt_wb,
    output logic [31:0] dc_cnt_bypass,
    output logic [31:0] dc_cnt_rab,
    // write_guard observation (T5.9; zero when OBSERVE = 0)
    output logic        wg_restricted,
    output logic [31:0] wg_cycles_restricted,
    output logic [31:0] wg_first_restrict,
    output logic [31:0] wg_stores,
    output logic [31:0] wg_stores_restricted,
    output logic [31:0] dc_cnt_stall,
    output logic [31:0] ic_cnt_lookup,
    output logic [31:0] ic_cnt_miss,
    output logic [31:0] ic_cnt_stall,
    output logic [31:0] dbg_dmem [0:3],
    // MMIO window 0xF000_0000-0xF000_0FFF: stores there never reach dmem or the D$. One pulse per
    // store, in the Memory stage; the simulation monitor (tb/sys_monitor.sv) interprets them.
    /* verilator lint_off UNUSEDSIGNAL */  // KI-008: only the low log2(MEM_WORDS) bits of dbg_widx are used
    input  logic [31:0] dbg_widx,   // simulation debug read port into the data memory: word index
    /* verilator lint_on UNUSEDSIGNAL */
    output logic [31:0] dbg_word,   // the data memory's word dbg_widx (combinational; the D$ overlaid on memory)

    output logic        mmio_we,
    output logic [31:0] mmio_addr,
    output logic [31:0] mmio_wdata
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

logic imiss;      // effective: the I$'s miss, plus injected fetch bubbles (test only)
logic dmiss;      // effective: the D$'s miss, plus injected freezes (test only)
logic imiss_c;    // from the I$ (0 with CACHES_ON = 0)
logic dmiss_c;    // from the D$ (0 with CACHES_ON = 0)

// Stall injection (T2.2, test only). With INJECT_STALL_SEED != 0 two seeded LFSRs add, at random cycles
// (about one in four each), a pipeline-wide freeze (OR-ed into dmiss: every register holds, as for a D$
// miss) and a fetch bubble (OR-ed into imiss: pc holds and F/D takes a bubble, as for an I$ miss).
// Architectural results must not change (tests/stall_injection_test.py). With seed 0 no logic exists.
generate
    if (INJECT_STALL_SEED != 0) begin : g_inject
        logic [15:0] lfsr_f, lfsr_i;
        always_ff @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                lfsr_f <= 16'(INJECT_STALL_SEED * 2654435761);
                lfsr_i <= 16'(INJECT_STALL_SEED * 40503 + 12345);
            end else begin
                lfsr_f <= {lfsr_f[14:0], lfsr_f[15] ^ lfsr_f[13] ^ lfsr_f[12] ^ lfsr_f[10]};
                lfsr_i <= {lfsr_i[14:0], lfsr_i[15] ^ lfsr_i[13] ^ lfsr_i[12] ^ lfsr_i[10]};
            end
        end
        assign dmiss = dmiss_c | (lfsr_f[3] & lfsr_f[9]);
        assign imiss = imiss_c | (lfsr_i[5] & lfsr_i[11]);
    end else begin : g_no_inject
        assign dmiss = dmiss_c;
        assign imiss = imiss_c;
    end
endgenerate
logic StallE;
logic StallM;
logic StallW;

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

pc #(.RESET_PC(RESET_PC)) u_pc(
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
//IMEM / I$

localparam int LINE_BITS = 8 * LINE_BYTES;
logic                 ic_mem_valid;
logic [31:0]          ic_mem_addr;
logic [LINE_BITS-1:0] ic_mem_rdata;
logic                 ic_mem_done;

generate
    if (CACHES_ON) begin : g_icache
        icache #(.CACHE_BYTES(ICACHE_BYTES), .LINE_BYTES(LINE_BYTES)) u_icache(
            .clk(clk),
            .rst_n(rst_n),
            .addr(A_PC_to_imem_and_ALU),
            .rdata(instruction_imem_to_FETCH),
            .imiss(imiss_c),
            .mem_valid(ic_mem_valid),
            .mem_addr(ic_mem_addr),
            .mem_rdata(ic_mem_rdata),
            .mem_done(ic_mem_done),
            .refill_cnt(ic_refill_cnt),
            .cnt_lookup(ic_cnt_lookup),
            .cnt_miss(ic_cnt_miss),
            .cnt_stall(ic_cnt_stall)
        );
    end else begin : g_imem
        imem #(.DEPTH(MEM_WORDS), .INIT_FILE(IMEM_FILE)) u_imem(
            .A(A_PC_to_imem_and_ALU),
            .RD(instruction_imem_to_FETCH)
        );
        assign imiss_c = 1'b0;
        assign ic_mem_valid = 1'b0;
        assign ic_mem_addr = 32'b0;
        assign ic_refill_cnt = 32'b0;
        assign ic_cnt_lookup = 32'b0;
        assign ic_cnt_miss = 32'b0;
        assign ic_cnt_stall = 32'b0;
    end
endgenerate



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
    .StallE(StallE),
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

hazard_unit #(.FORWARDING(FORWARDING)) u_hazard_unit(
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
    .imiss(imiss),
    .dmiss(dmiss),
    .ForwardAE(ForwardAE),
    .ForwardBE(ForwardBE),
    .StallF(StallF),
    .StallD(StallD),
    .StallE(StallE),
    .StallM(StallM),
    .StallW(StallW),
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
    .StallM(StallM),
    .ALUResultE(ALUResultE),
    .WriteDataE(WriteDataE),
    .PCPlus4E(PCPlus4E),
    .RdE(RdE),
    .ImmExtE(ImmExtE),
    .RegWriteE(RegWriteE),
    .MemWriteE(MemWriteE),
    .ResultSrcE(ResultSrcE),
    .funct3E(funct3E),
    .ALUResultM(ALUResultM),
    .WriteDataM(WriteDataM),
    .PCPlus4M(PCPlus4M),
    .RdM(RdM),
    .ImmExtM(ImmExtM),
    .RegWriteM(RegWriteM),
    .MemWriteM(MemWriteM), 
    .ResultSrcM(ResultSrcM),
    .funct3M(funct3M)
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

logic [2:0]  funct3M;
logic [31:0] ReadRawM;     // word returned by the data memory or D$, before the load extender
logic [31:0] ReadDataM;    // extended load value into m_w_reg

// Store lane logic (Memory stage): sb/sh replicate the low byte/half across the word and enable
// only the addressed lanes; sw enables all four. Misaligned accesses are unsupported (excluded
// from the arch-test subset, see docs/KNOWN_ISSUES.md KI-004).
logic [3:0]  StoreBEM;
logic [31:0] StoreDataM;
logic        MemStoreM;     // a store that goes to dmem / the D$ (not to the MMIO window)
assign mmio_we    = MemWriteM && (ALUResultM[31:12] == 20'hF0000);
assign mmio_addr  = ALUResultM;
assign mmio_wdata = WriteDataM;
assign MemStoreM  = MemWriteM && !mmio_we;
always_comb begin
    StoreBEM   = 4'b0000;
    StoreDataM = WriteDataM;
    if (MemStoreM) begin
        case (funct3M[1:0])
            2'b00: begin StoreBEM = 4'b0001 << ALUResultM[1:0]; StoreDataM = {4{WriteDataM[7:0]}};  end   // sb
            2'b01: begin StoreBEM = ALUResultM[1] ? 4'b1100 : 4'b0011; StoreDataM = {2{WriteDataM[15:0]}}; end // sh
            default: StoreBEM = 4'b1111;                                                                    // sw
        endcase
    end
end

// Load extender: shift the addressed byte/half to bit 0, then sign- or zero-extend.
logic [15:0] LoadShiftM;    // only the low half is ever needed (lw bypasses the shift)
assign LoadShiftM = 16'(ReadRawM >> (8 * ALUResultM[1:0]));
always_comb begin
    case (funct3M)
        3'b000:  ReadDataM = {{24{LoadShiftM[7]}},  LoadShiftM[7:0]};    // lb
        3'b001:  ReadDataM = {{16{LoadShiftM[15]}}, LoadShiftM[15:0]};   // lh
        3'b100:  ReadDataM = {24'b0, LoadShiftM[7:0]};                   // lbu
        3'b101:  ReadDataM = {16'b0, LoadShiftM[15:0]};                  // lhu
        default: ReadDataM = ReadRawM;                                   // lw
    endcase
end
logic [31:0] ReadDataW;
logic [31:0] ALUResultW;

logic [31:0] PCPlus4W;
logic [31:0] ImmExtW;



m_w_reg u_m_w_reg(
    .clk(clk),
    .rst_n(rst_n),
    .StallW(StallW),
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

//DMEM / D$ / main memory

logic                 dc_mem_valid;
logic                 dc_mem_we;
logic [31:0]          dc_mem_addr;
logic [LINE_BITS-1:0] dc_mem_wdata;
logic [LINE_BYTES-1:0] dc_mem_be;
logic [LINE_BITS-1:0] dc_mem_rdata;
logic                 dc_mem_done;

// restricted-store decision (T5 detectors; NONE by default)
logic dc_bypass_w;
write_guard #(.DETECTOR(DETECTOR), .ACTION(WG_ACTION), .MODE(WG_MODE), .WINDOW_CYCLES(WG_WINDOW),
             .THRESHOLD(WG_THRESHOLD), .M(WG_M), .W(WG_W), .LINES(DCACHE_BYTES/LINE_BYTES),
             .PLACEBO_RATE(WG_PLACEBO_RATE), .PLACEBO_SEED(WG_PLACEBO_SEED), .OBSERVE(OBSERVE)) u_write_guard(
    .clk(clk),
    .rst_n(rst_n),
    .store_valid(MemStoreM),
    .store_busy(dmiss),
    .store_line(32'(ALUResultM[$clog2(LINE_BYTES) +: $clog2(DCACHE_BYTES/LINE_BYTES)])),
    .array_write_valid(dc_aw_valid),
    .line_idx(dc_aw_line),
    .cycle_strobe(1'b1),
    .bypass_store(dc_bypass_w),
    /* verilator lint_off PINCONNECTEMPTY */  // KI-016: stall_req is used by A2 (not implemented)
    .stall_req(),
    /* verilator lint_on PINCONNECTEMPTY */
    .restricted(wg_restricted),
    .obs_cycles_restricted(wg_cycles_restricted),
    .obs_first_restrict(wg_first_restrict),
    .obs_stores(wg_stores),
    .obs_stores_restricted(wg_stores_restricted)
);

generate
    if (CACHES_ON) begin : g_dcache
        logic [$clog2(DCACHE_BYTES/LINE_BYTES)-1:0] aw_line_w;
        assign dc_aw_line = 32'(aw_line_w);
        logic [4:0]    peek_hit;
        logic [159:0]  peek_data;
        dcache #(.CACHE_BYTES(DCACHE_BYTES), .LINE_BYTES(LINE_BYTES), .DC_WRITE_LATENCY(DC_WRITE_LATENCY), .NPEEK(5)) u_dcache(
            .clk(clk),
            .rst_n(rst_n),
            .addr(ALUResultM),
            .wdata(StoreDataM),
            .be(StoreBEM),
            .we(MemStoreM),
            .re(RegWriteM & (ResultSrcM == 2'b01)),
            .bypass(dc_bypass_w),
            .rdata(ReadRawM),
            .dmiss(dmiss_c),
            .mem_valid(dc_mem_valid),
            .mem_we(dc_mem_we),
            .mem_addr(dc_mem_addr),
            .mem_wdata(dc_mem_wdata),
            .mem_be(dc_mem_be),
            .mem_done(dc_mem_done),
            .mem_rdata(dc_mem_rdata),
            .aw_valid(dc_aw_valid),
            .aw_line(aw_line_w),
            .aw_kind(dc_aw_kind),
            .tr_valid(dc_tr_valid),
            .tr_we(dc_tr_we),
            .tr_addr(dc_tr_addr),
            .tr_size(dc_tr_size),
            .tr_bypass(dc_tr_bypass),
            .cnt_access(dc_cnt_access),
            .cnt_hit(dc_cnt_hit),
            .cnt_miss(dc_cnt_miss),
            .cnt_fill(dc_refill_cnt),
            .cnt_wb(dc_cnt_wb),
            .cnt_bypass(dc_cnt_bypass),
            .cnt_refill_after_bypass(dc_cnt_rab),
            .cnt_stall(dc_cnt_stall),
            .cnt_write(dc_write_cnt),
            .peek_addr({32'd12, 32'd8, 32'd4, 32'd0, dbg_widx[29:0], 2'b00}),
            .peek_hit(peek_hit),
            .peek_data(peek_data)
        );
        // one memory shared by both caches (D$ has priority); loaded from the whole image
        /* verilator lint_off UNUSEDSIGNAL */  // KI-016: the ready handshake outputs are informational
        logic i_ready_unused, d_ready_unused;
        /* verilator lint_on UNUSEDSIGNAL */
        mem_model #(.WORDS(MEM_WORDS), .LINE_BYTES(LINE_BYTES), .LATENCY(MEM_LATENCY),
                    .RANDOM_LATENCY(MEM_RANDOM_LATENCY), .SEED(MEM_SEED), .INIT_FILE(IMEM_FILE)) u_mem(
            .clk(clk),
            .rst_n(rst_n),
            .i_valid(ic_mem_valid),
            .i_ready(i_ready_unused),
            .i_addr(ic_mem_addr),
            .i_done(ic_mem_done),
            .i_rdata(ic_mem_rdata),
            .d_valid(dc_mem_valid),
            .d_ready(d_ready_unused),
            .d_we(dc_mem_we),
            .d_addr(dc_mem_addr),
            .d_wdata(dc_mem_wdata),
            .d_be(dc_mem_be),
            .d_done(dc_mem_done),
            .d_rdata(dc_mem_rdata)
        );
        for (genvar i = 0; i < 4; i++) begin : g_dbg
            assign dbg_dmem[i] = peek_hit[i + 1] ? peek_data[32 * (i + 1) +: 32] : u_mem.mem[i];
        end
        assign dbg_word = peek_hit[0] ? peek_data[31:0] : u_mem.mem[dbg_widx[$clog2(MEM_WORDS)-1:0]];
    end else begin : g_dmem
        if (DMEM_FROM_IMAGE) begin : g_img
            dmem #(.DEPTH(MEM_WORDS), .INIT_FILE(IMEM_FILE)) u_dmem(
                .clk(clk),
                .A(ALUResultM),
                .WD(StoreDataM),
                .WE(MemStoreM),
                .BE(StoreBEM),
                .RD(ReadRawM)
            );
            for (genvar i = 0; i < 4; i++) begin : g_dbg
                assign dbg_dmem[i] = u_dmem.mem[i];
            end
            assign dbg_word = u_dmem.mem[dbg_widx[$clog2(MEM_WORDS)-1:0]];
        end else begin : g_zero
            dmem #(.DEPTH(MEM_WORDS), .INIT_FILE("")) u_dmem(
                .clk(clk),
                .A(ALUResultM),
                .WD(StoreDataM),
                .WE(MemStoreM),
                .BE(StoreBEM),
                .RD(ReadRawM)
            );
            for (genvar i = 0; i < 4; i++) begin : g_dbg
                assign dbg_dmem[i] = u_dmem.mem[i];
            end
            assign dbg_word = u_dmem.mem[dbg_widx[$clog2(MEM_WORDS)-1:0]];
        end
        assign dmiss_c = 1'b0;
        assign dc_mem_valid = 1'b0;
        assign dc_mem_we = 1'b0;
        assign dc_mem_addr = 32'b0;
        assign dc_mem_wdata = '0;
        assign dc_mem_be = '0;
        assign dc_mem_done = 1'b0;
        assign ic_mem_done = 1'b0;
        assign ic_mem_rdata = '0;
        assign dc_refill_cnt = 32'b0;
        assign dc_write_cnt = 32'b0;
        assign dc_aw_valid = 1'b0; assign dc_aw_line = 32'b0; assign dc_aw_kind = 1'b0;
        assign dc_tr_valid = 1'b0; assign dc_tr_we = 1'b0; assign dc_tr_addr = 32'b0; assign dc_tr_size = 3'b0; assign dc_tr_bypass = 1'b0;
        assign dc_cnt_access = 32'b0; assign dc_cnt_hit = 32'b0; assign dc_cnt_miss = 32'b0; assign dc_cnt_wb = 32'b0; assign dc_cnt_bypass = 32'b0;
        assign dc_cnt_rab = 32'b0; assign dc_cnt_stall = 32'b0;
    end
endgenerate

assign ResultW = (ResultSrcW == 2'b00) ? ALUResultW :
                 (ResultSrcW == 2'b01) ? ReadDataW  :
                 (ResultSrcW == 2'b10) ? ImmExtW    :
                                          PCPlus4W;


endmodule
