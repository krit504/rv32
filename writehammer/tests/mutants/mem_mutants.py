"""mem_mutants.py: T2.1 mutants of rtl/mem_model.sv (protected; add only). Tuple format as core_mutants.py."""

MUTANTS = [
    ("M1_latency_off_by_one", "mem_model.sv",
     "cnt <= lat_new - 1'b1;", "cnt <= lat_new;",
     "done arrives one cycle late"),
    ("M2_icache_priority", "mem_model.sv",
     "wire take_d = (state == IDLE) && d_valid;\n    wire take_i = (state == IDLE) && !d_valid && i_valid;",
     "wire take_i = (state == IDLE) && i_valid;\n    wire take_d = (state == IDLE) && !i_valid && d_valid;",
     "the I$ wins arbitration instead of the D$"),
    ("M3_byte_enable_ignored", "mem_model.sv",
     "if (be_q[j]) mem[", "if (1'b1) mem[",
     "writes ignore the byte enables"),
    ("M4_line_lane_order_reversed", "mem_model.sv",
     "line[32*k +: 32] = mem[line_w + ADDR_BITS'(k)];", "line[32*k +: 32] = mem[line_w + ADDR_BITS'(WPL - 1 - k)];",
     "words of a line returned in reverse order"),
    ("M5_random_latency_unbounded", "mem_model.sv",
     "lat_new = LAT_BITS'(1 + (int'(lfsr) % (2 * LATENCY - 1)));", "lat_new = LAT_BITS'(1 + (int'(lfsr) % (2 * LATENCY)));",
     "random latency can reach 2*LATENCY"),
    ("M6_write_before_done", "mem_model.sv",
     "                        if (we_q)                            // write at the edge ending the done cycle",
     "                        if (1'b0 && we_q)                    // write at the edge ending the done cycle",
     "writes never reach the array"),
]
