"""perf_mutants.py: T1.3 mutants for the MMIO monitor and performance counters (protected; add only).

Tuple format as core_mutants.py; a file name starting with "tb/" is relative to the tb directory
copy, anything else to the rtl copy.
"""

MUTANTS = [
    ("P1_loaduse_never_counted", "tb/sys_monitor.sv",
     "if (stallCond && !dmiss)  stall_loaduse <= stall_loaduse + 1;",
     "if (1'b0 && stallCond && !dmiss)  stall_loaduse <= stall_loaduse + 1;",
     "load-use stall counter stuck at 0"),
    ("P2_bubbles_counted_as_retired", "tb/sys_monitor.sv",
     "wire retire = validW && !StallW;",
     "wire retire = !StallW;",
     "retired count includes flush and stall bubbles"),
    ("P3_stop_ignored", "tb/sys_monitor.sv",
     "8'h08: active <= 1'b0;",
     "8'h08: ;",
     "the window never closes"),
    ("P4_start_does_not_clear", "tb/sys_monitor.sv",
     "{cycles, instret, stall_loaduse, redirects, imiss_cycles, dmiss_cycles} <= '0;\n                        active <= 1'b1;",
     "active <= 1'b1;",
     "START leaves the counters running from reset"),
    ("P5_redirect_counted_twice", "tb/sys_monitor.sv",
     "if (redirectE && !dmiss)  redirects <= redirects + 1;",
     "if (redirectE && !dmiss)  redirects <= redirects + 2;",
     "flush counter doubled"),
    ("P6_no_halt_report", "tb/sys_monitor.sv",
     "            if (halt_pend && !halted) begin\n                halted <= 1'b1;\n                $display(\"HALT %0d\", exit_code);\n                print_perf();\n            end\n",
     "",
     "no HALT report at all"),
    ("P7_mmio_store_reaches_dmem", "rv32_top_pipelined.sv",
     "assign MemStoreM  = MemWriteM && !mmio_we;",
     "assign MemStoreM  = MemWriteM;",
     "MMIO stores also write the data memory"),
]
