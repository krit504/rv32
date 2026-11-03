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

## 2026-11-01 23:07 T1.1 and T1.2 committed together
Spec 0B.12 asks for one commit per task. T1.1 (RTL) and T1.2 (tests) touch the same shared files (STATUS, LOCKED.sha256, CHANGE_LOG, the mutant harness, and mutant C5's patch text depends on the T1.1 RTL line), so they share one commit `T1.1, T1.2`. Both have their own task log.

## 2026-11-02 06:53 T1.7 and T1.8 committed together
Both feed one baseline table (`analysis/baseline.py`) and one `make bench` target, and both needed the same Verilator runner, so they share a commit `T1.7, T1.8`; each has its own task log. The Verilator vs Icarus difference found along the way (typed string parameters) is recorded in T1.7 problem 1 and KI-012.

## 2026-11-02 08:07 T1.6 generator bug found during T2
The T1.6 random programs' data window was never at 0x800: `addi x31,x31,0x800` is -2048, so x31 was 0xFFFFF800 and the window was reached through address wrap-around. T1.6's results (1000/1000 in five configurations, the Spike cross-check, the bad-core controls) were all computed on that layout and are correct for it, but the layout was not what `docs/logs/T1.6.md` says. Fixed in CHG-015 (window now at 0x1000); all T1.6 configurations were rerun on the fixed generator: caches off 1000/1000, no-forwarding 1000/1000, caches on LAT 1/3/10 1000/1000 each, Spike vs model 200/200, bad-core control OK. Lesson: a constant that is not representable in an instruction field needs an assertion where the program is generated.

## 2026-11-02 14:29 T2 finished
Full `make test` rc=0 (47 min): mutants 52/52 caught (C6 and its control behave as argued); `make invariant` 3/3 groups, 9 configurations; `make caches` complete. Three mistakes of my own cost time and are worth recording: (1) a mutation-verification job was left waiting while the laptop slept (lid closed 08:07, suspended 09:53 to 11:04) and was lost without a report; jobs now log a heartbeat and have time limits. (2) I read a silent process list as "the job vanished" when the job was alive and had in fact hit my own 25-minute timeout; the cause was a broken core hanging every workload to an 800 M-cycle limit, now bounded per workload. (3) The random generator's data window was really at 0xFFFFF800 (CHG-015), which meant the full-core random test never evicted a cache line until the small-cache configurations were added.

## 2026-11-03 14:17 T3/T4 merged; T4.7 finding; the agent read the author's papers
Merged the second agent's branch (T3.1 to T3.5, T4.1 to T4.8) into main without conflicts (it had already merged main and unioned `docs/LOCKED.sha256`; it also wrote CHG-017 for the earlier locked copy of `tests/invariant_test.py`). It reported T4.7 PARTIAL; I checked the numbers myself from `analysis/attack_pmr_all_workloads.csv` and they hold (DEC-010). Two things worth recording: (1) when my prompt left the attack definitions as a blank for the author, the agent resolved it by reading the author's own papers in `/home/kritin/Documents/Research papers/` (outside the repository) rather than inventing definitions; that is the right outcome, but the author should know it read files outside the project. (2) `make attacks` had not been wired (only `make wear` was); I wired `attacks` and `attacks-validate` and am re-running the agent's checks independently from main.
