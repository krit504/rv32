# LAB NOTEBOOK

Append-only, timestamped (IST). Earlier entries are never rewritten.

## 2026-11-01 18:16 Project start
Spec v4 read in full. Baseline commit of the existing cache work in `Multi_cycle/` (`848892a`) so the import starts from a recorded state. Layout created (T0.1).

## 2026-11-01 18:40 Tool survey (T0.2)
- I first told the author sky130 was not installed and they chose IHP sg13g2 on that basis (DEC-003). Wrong: sky130A sits under `~/.cache/tt-pdk/root/ciel/sky130/versions/74c0e6b…/sky130A`, which my first search did not look inside. DEC-006 restores the spec default. Lesson: search the whole PDK root, including ciel version stores, before declaring a PDK missing.
- riscv-arch-test HEAD is now the ACT4 framework (needs Sail, uv, Ruby, UDB). Tag `3.10.0` still has the classic `riscv-test-suite/rv32i_m/I` layout with 39 tests, including the six sub-word ones. Pinned that; Spike will produce the reference signatures.
- Dhrystone comes from riscv-tests `benchmarks/dhrystone`; there is no canonical standalone repository.
- The EDA tools live in the author's LibreLane image. I recorded the image id from `docker image inspect` but did not start the container: the author's flow runs go through a supervised launcher with approval.

## 2026-11-01 18:31 Core import (T0.3)
- Copied the core from `Multi_cycle/` at `848892a`. Renamed `ALU.sv` to `alu.sv` and `rv32i_pipelined.sv` to `rv32_top_pipelined.sv` to match module names (Verilator DECLFILENAME).
- `encode.py` wrote its hex to an absolute path inside `Multi_cycle/`; the test scripts wrote `program.hex` into the source directory, which earlier overwrote the tracked regression hex. All runs now happen in `work/<name>/`; the regression hex is `tests/golden/nohazard_program.hex` and `encode.py` still reproduces it byte for byte.
- Made the cache counters and `dbg_dmem` top-level outputs instead of unused internals (Verilator UNUSEDSIGNAL). Reading `dbg_dmem` through the output port gave `x` in Icarus 12 at every latency; reading it hierarchically gives the right values. At first only L=10 looked broken: `| tail -3` had hidden the other three FAIL lines. Testbenches read it hierarchically.
- No mutant harness existed in the repo, so the spec's "5 of 5 mutants" could not be rerun. Built `tests/run_mutants.py` with H1-H5 (from the hazard-section failure notes) and C1-C7 (cache datasheet step 5). The runner reports a compile error or traceback as ERROR rather than CAUGHT, so a mutant cannot pass by breaking the build. C6 (`re` without `RegWriteM`) is equivalent with this decoder; C6X proves the gate matters when the decoder drives ResultSrc=01 for sw.
