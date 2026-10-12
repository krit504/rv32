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
  gen_pipeline_datapath.py         regenerates rv32i_pipeline_datapath.svg/.png
docs/           specs and concept notes (the RTL is written against these)
```

Both core directories carry their own copy of the shared modules (ALU, decoders, regfile, ...).

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
