# The 5-stage core and the changes made for this project

**What it is**

`rtl/rv32_top_pipelined.sv` is an RV32I five-stage pipeline (fetch, decode, execute, memory, writeback) with forwarding and a load-use stall in `rtl/hazard_unit.sv`. This project added three things to the existing core:

- Sub-word loads and stores (`lb`, `lbu`, `lh`, `lhu`, `sb`, `sh`). The Memory stage builds byte enables and replicates the store data across the word; a load extender shifts the addressed lane to bit 0 and sign- or zero-extends it (`docs/logs/T1.1.md`).
- An MMIO window `0xF000_0000` to `0xF000_0FFF`. Stores there never reach `dmem` or the D$ and appear as one pulse on `mmio_we`, `mmio_addr` and `mmio_wdata`. The simulation monitor `tb/sys_monitor.sv` turns them into the performance counters (cycles, retired instructions, load-use and flush stall cycles) and the halt, start, stop, phase and putchar functions (`docs/logs/T1.3.md`).
- A `funct3M` field in `rtl/e_m_reg.sv`.

**Why it is built this way**

`main_decoder` is opcode-only, so the new loads decode like `lw` and the new stores like `sw`; the width must come from `funct3`. Without `funct3M` the Memory stage cannot tell `lb` from `lw`. `docs/OPEN_QUESTIONS.md` (Q-003) records this as required for correctness, with no other pipeline register changed. The counters live in the testbench, not the core, so the core carries no instrumentation state. The log does not record an alternative rejected for the MMIO design.

**How it is verified**

`tests/subword_tests.py` (11 directed tests, 55 runs, against the independent `tests/refmodel.py`), eight sub-word mutants in `tests/mutants/subword_mutants.py` (all caught), `tests/perf_tests.py` (21/21 known-answer counts, hand-derived), the 37/37 riscv-arch-test subset against Spike (`tests/arch_test.py`), and the random lockstep generator `tests/random_lockstep.py` (seeds 1 to 1000, caches off 1000/1000).

**Known limits**

Misaligned accesses are unsupported (KI-004). Loads from the MMIO window are unsupported (KI-005). Counter windows start after START's Memory cycle, so a hazard in that cycle is not counted (T1.3). The arch-test run takes about 61 minutes and is not in `make test` (T1.5). No `mcycle` CSR exists.
