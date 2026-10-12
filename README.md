# rv32

A from-scratch RV32I processor in SystemVerilog: first a single-cycle core, then a 5-stage pipeline with forwarding, load-use stalling and branch flushing, built step by step against written specs and checked with directed tests.

Goal: a complete RV32I base-ISA core (no `FENCE`/`ECALL`/`EBREAK`; decoded as no-ops) that is correct for any instruction sequence, with measurable pipeline behavior (CPI, stalls, flushes), later extended with caches and a UART on the processor bus.

## Roadmap

- [x] 1. Single-cycle core (RV32I base ISA)
- [x] 2. 5-stage pipeline (Fetch / Decode / Execute / Memory / Writeback)
- [x] 3. EX-EX and MEM-EX forwarding
- [x] 4. Load-use hazard stall
- [x] 5. Branch handling + flush (static not-taken; two instructions flushed per taken branch/jump)
- [ ] 6. Direct-mapped instruction cache
- [ ] 7. Direct-mapped data cache
- [ ] 8. Connect UART to processor bus
- [ ] 9. Run bubble sort and fibonacci in simulation
- [ ] 10. GitHub documentation

## Repo layout

```
Single_cycle/   single-cycle core (top: rv32_top), full-ISA integration test, datapath diagram
Multi_cycle/    5-stage pipelined core (top: rv32_top_pipelined) -- directory name is historical
  rv32i_pipelined.sv               pipelined top level
  f_d_reg / d_e_reg / e_m_reg / m_w_reg .sv   the four pipeline registers
  hazard_unit.sv                   forwarding, load-use stall, flush
  perf_counters.sv                 simulation-only cycle/stall/flush/retire counters
  encode.py, program.hex, tb_rv32i_pipelined.sv   no-hazard regression (21 register checks)
  hazard_tests.py, tb_hazard.sv    directed hazard tests (25 cases)
  perf_report.py                   CPI/stall/flush table for program.hex, forwarding on vs off
  gen_pipeline_datapath.py         regenerates rv32i_pipeline_datapath.svg/.png
docs/           specs and concept notes (the RTL is written against these)
```

Both core directories carry their own copy of the shared modules (ALU, decoders, regfile, ...).

History note: commits `9ee45f5` (5-stage pipeline) and `02da49f` (hazard handling) were assembled after the fact. Their pre-hazard versions of `f_d_reg`, `d_e_reg`, `pc` and the top level were reconstructed from the final files, and `02da49f` has no `FORWARDING` parameter. Each of those commits builds and passes its own tests, but `git blame` and `git bisect` across them reflect that reconstruction, not the order the code was actually written.

## Requirements

`verilator` >= 5, `iverilog` >= 12, `python3`. Run everything from the core's directory.

## Running the checks

### Pipelined core (`cd Multi_cycle`)

```sh
CORE="rv32i_pipelined.sv f_d_reg.sv d_e_reg.sv e_m_reg.sv m_w_reg.sv control_unit.sv \
      main_decoder.sv alu_decoder.sv ALU.sv immediate_generator.sv pc.sv regfile.sv \
      imem.sv dmem.sv hazard_unit.sv"

# Lint, forwarding on and off (expect no output)
verilator --lint-only -Wall -Wno-EOFNEWLINE -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL \
          -GFORWARDING=1 --top-module rv32_top_pipelined $CORE
verilator --lint-only -Wall -Wno-EOFNEWLINE -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL \
          -GFORWARDING=0 --top-module rv32_top_pipelined $CORE

# No-hazard regression: expect "21 PASS, 0 FAIL"
python3 encode.py                      # writes program.hex
iverilog -g2012 -o sim.vvp $CORE tb_rv32i_pipelined.sv && vvp sim.vvp

# Directed hazard tests: expect "25/25 passed"
python3 hazard_tests.py

# Same tests with forwarding disabled (stall-on-dependency ablation): expect "25/25 passed"
python3 hazard_tests.py --nofw         # --nofwd is accepted too

# hazard_tests.py overwrites program.hex; restore the regression program afterwards
python3 encode.py

# CPI / stall / flush table for the regression program, forwarding on and off
python3 encode.py && python3 perf_report.py
```

`iverilog` prints `sorry: constant selects in always_* processes ...` notes while compiling; they are harmless.

### Single-cycle core (`cd Single_cycle`)

```sh
SC="rv32i_single_cycle.sv control_unit.sv main_decoder.sv alu_decoder.sv ALU.sv \
    immediate_generator.sv pc.sv regfile.sv imem.sv dmem.sv"
iverilog -g2012 -o sim.vvp $SC tb_rv32i_single_cycle.sv && vvp sim.vvp   # ends with "... TEST PASSED"
```

## Pipeline hazard handling in one paragraph

Forwarding takes `FwdDataM` (ALU result, `ImmExtM` for `lui`, `PCPlus4M` for `jal`/`jalr`) or `ResultW` ahead of the `ALUSrc`/`ALUSrcA` muxes, and also feeds store data. A load immediately followed by a consumer stalls one cycle. A taken branch or jump is resolved in Execute and flushes the two wrong-path instructions behind it. The register file writes on the falling edge, so a producer in Writeback and a consumer in Decode in the same cycle need no forwarding. `FORWARDING=0` replaces forwarding with stall-on-dependency, as an ablation baseline.

## How CPI is reported

A 5-stage pipeline needs 4 extra cycles to fill: the first instruction takes 5 cycles to reach Writeback, so a hazard-free run of N instructions takes N + 4 cycles. On a short program that constant dominates (4 instructions give CPI 2.0 with no hazards at all), which hides what the hazards actually cost. Every run therefore reports both:

- `CPI_raw = cycles / retired`. Includes the fill. Comparable with the earlier numbers.
- `CPI_steady = (cycles - fill_cycles) / retired`, with `fill_cycles = 4`. Exactly 1.000 means no stalls and no flushes; anything above 1 is hazard cost.

alongside `stall_cycles`, `branch_flush_cycles` (2 per taken branch or jump: the two wrong-path instructions) and `spurious_stalls`, each divided by `retired`. The stall column is load-use stalls with forwarding on and dependency stalls with `FORWARDING=0`. A spurious stall is one on a register field the instruction in Decode does not read (immediate bits that happen to match); it is counted, not removed (spec Note 8).

Every run also checks the identity `cycles = retired + stall_cycles + 2 * flush_cycles + 4`. Counting runs from reset until the last instruction below `END_PC` retires, and retirement is tracked with a shadow valid bit shifted through the pipeline, so padding NOPs and flushed bubbles never count.

The 27-instruction regression program (`python3 encode.py && python3 perf_report.py`):

| FORWARDING | cycles | retired | CPI_raw | CPI_steady | stall/instr | branch_flush/instr | spurious/instr | identity |
|---|---|---|---|---|---|---|---|---|
| 1 | 31 | 27 | 1.148 | 1.000 | 0.000 (load-use) | 0.000 | 0.000 | ok |
| 0 | 33 | 27 | 1.222 | 1.074 | 0.074 (dependency) | 0.000 | 0.074 | ok |
