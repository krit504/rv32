"""core_mutants.py: the T0.3 baseline mutant list (protected; adding mutants is allowed, removing is not).

Each mutant: (id, file under rtl/, exact text to replace (must occur), replacement, what it breaks).
Hazard mutants H1-H5 come from the failure-mode notes of the pipelined spec (hazard section) and the
README. Cache mutants C1-C7 are the seven listed in the cache datasheet, section 11, step 5.
"""

MUTANTS = [
    ("H1_no_fwd_from_M_srcA", "hazard_unit.sv",
     "assign ForwardAE = ((Rs1E == RdM) && RegWriteM && (RdM != 5'd0)) ? 2'b10 :",
     "assign ForwardAE = (1'b0) ? 2'b10 :",
     "SrcA never forwards from Memory"),
    ("H2_no_x0_guard_M_srcA", "hazard_unit.sv",
     "assign ForwardAE = ((Rs1E == RdM) && RegWriteM && (RdM != 5'd0)) ? 2'b10 :",
     "assign ForwardAE = ((Rs1E == RdM) && RegWriteM) ? 2'b10 :",
     "forwarding from a write to x0"),
    ("H3_no_load_use_stall", "hazard_unit.sv",
     "assign lwStall   = ",
     "assign lwStall   = 1'b0 && ",
     "load-use hazard not stalled"),
    ("H4_flushE_keeps_PCSrcE", "d_e_reg.sv",
     "PCSrcE <= '0; Rs1E<='0;Rs2E<='0;",
     "Rs1E<='0;Rs2E<='0;",
     "flushed wrong-path jal/jalr still redirects"),
    ("H5_regfile_posedge_write", "regfile.sv",
     "always_ff @( negedge clk or negedge rst_n )",
     "always_ff @( posedge clk or negedge rst_n )",
     "same-cycle W/D register read sees the old value"),
    ("C1_valid_not_reset", "icache.sv",
     "        valid<='0;\n",
     "",
     "I$ hits on never-filled lines after reset"),
    ("C2_icache_fill_live_addr", "icache.sv",
     "data[miss_index] <= mem_rdata;\n        tags[miss_index] <=miss_tag;",
     "data[index] <= mem_rdata;\n        tags[index] <=tag;",
     "I$ refill written under the live PCF instead of the captured miss address"),
    ("C3_fdreg_flush_before_hold", "f_d_reg.sv",
     "    else if(StallD) begin\n        // hold\n    end\n    else if(FlushD) begin\n        {InstrD, PCD, PCPlus4D} <='0;\n    end",
     "    else if(FlushD) begin\n        {InstrD, PCD, PCPlus4D} <='0;\n    end\n    else if(StallD) begin\n        // hold\n    end",
     "freeze destroys the instruction held in Decode"),
    ("C4_mwreg_not_held", "m_w_reg.sv",
     "    else if(StallW) begin\n        // hold\n    end\n",
     "",
     "Writeback bubbles during a D$ freeze; forwarding source lost"),
    ("C5_store_hit_no_line_update", "dcache.sv",
     "        for (int k = 0; k < 4; k++)\n            if (be[k]) data[index][32*wordsel + 8*k +: 8] <= wdata[8*k +: 8];",
     "        ;",
     "store hit leaves the stale word in the D$ line"),
    ("C6_re_without_RegWriteM", "rv32_top_pipelined.sv",
     ".re(RegWriteM & (ResultSrcM == 2'b01)),",
     ".re(ResultSrcM == 2'b01),",
     "store or branch with ResultSrc=01 starts a refill"),
    ("C7_reversed_lane_order", "icache.sv",
     "rdata    = data[index][32*wordsel +: 32];",
     "rdata    = data[index][32*(2'd3-wordsel) +: 32];",
     "I$ returns the wrong word of the block"),
]

# C6 is equivalent with this decoder: main_decoder drives ResultSrc=01 only for lw (RegWrite=1),
# so RegWriteM & (ResultSrcM==01) == (ResultSrcM==01) on every reachable state. The runner proves
# the gate matters with C6X: the decoder is changed to drive 01 for sw (the case Note 5 guards
# against); with the gate the suite passes (C6X_control), without it the suite fails (C6X).
DECODER_SW_01 = ("main_decoder.sv",
                 "            MemWrite  = 1;\n            ResultSrc = 2'b00;",
                 "            MemWrite  = 1;\n            ResultSrc = 2'b01;")
EQUIVALENT = {"C6_re_without_RegWriteM"}
