# RTL FREEZE (T2 complete)

As of the commit that adds this file (parent `3b2e8bd`, the T2 checkpoint) the RTL under `writehammer/rtl/` is **frozen for T3 and T4**:
the full `make test` passed (rc=0, mutants 52/52 caught), `make invariant` passed (arch 37/37 equal to Spike, 13/13 workloads, 200 random programs, identical across 9 cache and memory configurations), `make caches` produced the sweeps.

- No change to `rtl/dcache.sv`, `rtl/icache.sv`, `rtl/mem_model.sv` or the ports of `rtl/rv32_top_pipelined.sv` since the checkpoint `3b2e8bd` other than the testbench-only parameters listed in `docs/logs/T2.6.md`. The interfaces in `docs/HANDOFF_T3.md` section 6 are unchanged.
- **T3.4 (baseline wear for the benign workloads) may start.** Its numbers depend on this RTL; if the RTL has to change later, T3.4 must be re-run and the reason is recorded in `docs/RTL_CHANGES_AFTER_FREEZE.md`.
- To pick this up in the T3 worktree: `git merge main` (the T3 branch only adds files, so it merges cleanly).
- Counters and trace for T3/T5: `tb/tb_prog.sv` now prints `CACHEWIN` (counters over the START/STOP window); geometry parameters `ICB`, `DCB`, `LINEB`, random latency (`RANDLAT`, `MEM_SEED`) and the run-time cycle limit `+maxcyc` exist on `tb_prog`, `tb_arch` and `tb_random`.
