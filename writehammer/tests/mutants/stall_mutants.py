"""stall_mutants.py: T2.2 mutants of the stall enables (protected; add only). Tuple format as core_mutants.py."""

MUTANTS = [
    ("ST1_emreg_ignores_stallM", "e_m_reg.sv",
     "    else if(StallM) begin\n        // hold\n    end\n", "",
     "E/M keeps capturing during a freeze, so the instruction in Memory is lost"),
    ("ST2_dereg_ignores_stallE", "d_e_reg.sv",
     "    else if (StallE) begin\n        // hold\n    end\n", "",
     "D/E keeps capturing (or flushing) during a freeze"),
    ("ST3_pc_ignores_stallF", "pc.sv",
     "else if(!StallF) begin", "else begin",
     "pc advances while fetch is stalled"),
    ("ST4_fdreg_ignores_stallD", "f_d_reg.sv",
     "    else if(StallD) begin\n        // hold\n    end\n", "",
     "F/D keeps capturing during a stall: the held instruction is overwritten"),
]
