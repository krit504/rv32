# TRACEABILITY

Task to RTL files, tests, result rows, figures and the document sections that cite them (spec 0B.6). Updated as each task finishes.

| Task | RTL | Tests | Result rows / figures | Cited in |
|---|---|---|---|---|
| T0.3 | `rtl/*` (imported core) | `tests/nohazard_test.py`, `tests/hazard_tests.py`, `tests/cache_integration.py`, `tests/run_mutants.py` | `tests/BASELINE_COUNTS.json` | `docs/logs/T0.3.md` |
| T1.1 | `rtl/rv32_top_pipelined.sv`, `rtl/e_m_reg.sv`, `rtl/dmem.sv`, `rtl/dcache.sv`, `rtl/backing_mem.sv` | `tests/subword_tests.py` | n/a | `docs/logs/T1.1.md` |
| T1.2 | n/a | `tests/refmodel.py`, `tests/refmodel_selftest.py`, `tests/subword_tests.py`, `tests/mutants/subword_mutants.py` | n/a | `docs/logs/T1.2.md` |
| T1.3 | `rtl/rv32_top_pipelined.sv` (MMIO decode), `tb/sys_monitor.sv`, `tb/tb_prog.sv` | `tests/perf_tests.py`, `tests/prog_runner.py`, `tests/mutants/perf_mutants.py` | n/a | `docs/logs/T1.3.md` |
| T1.4 | `rtl/imem.sv`, `rtl/dmem.sv`, `rtl/backing_mem.sv`, `rtl/rv32_top_pipelined.sv` (MEM_WORDS, DMEM_FROM_IMAGE) | `tests/toolchain_test.py`, `tests/image_runner.py`, `tests/mutants/toolchain_mutants.py` | n/a | `docs/logs/T1.4.md` |
| T1.5 | `rtl/pc.sv` (RESET_PC), `rtl/rv32_top_pipelined.sv` (RESET_PC, dbg port) | `tests/arch_test.py`, `tests/arch/*`, `tb/tb_arch.sv`, `tests/arch_mutant_check.py` | `docs/ARCH_TESTS_RESULTS.md` | `docs/logs/T1.5.md`, `docs/ARCH_TESTS.md` |
| T1.6 | n/a | `tests/random_gen.py`, `tests/random_lockstep.py`, `tests/random_spike_check.py`, `tests/random_control.py`, `tb/tb_random.sv` | n/a | `docs/logs/T1.6.md` |
| T1.7 | `rtl/imem.sv`, `rtl/dmem.sv`, `rtl/backing_mem.sv` (untyped INIT_FILE) | `tests/bench_test.py`, `tests/vl_runner.py` | `docs/baseline.md`, `analysis/baseline.json` | `docs/logs/T1.7.md` |
| T1.8 | n/a | `tests/workload_test.py`, `tests/workloads.py` | `docs/baseline.md` | `docs/logs/T1.8.md`, DEC-008 |
| T2.1 | `rtl/mem_model.sv` | `tests/mem_model_test.py`, `tb/tb_mem_model.sv`, `tests/mutants/mem_mutants.py` | n/a | `docs/logs/T2.1.md` |
| T2.2 | `rtl/rv32_top_pipelined.sv` (INJECT_STALL_SEED), stall enables in the pipeline registers | `tests/stall_injection_test.py`, `tests/mutants/stall_mutants.py` | n/a | `docs/logs/T2.2.md` |
| T2.3 | `rtl/icache.sv` | `tests/cache_integration.py`, `tests/hazard_tests.py`, `tests/invariant_test.py` | `analysis/caches.csv` | `docs/logs/T2.3.md` |
| T2.4 | `rtl/dcache.sv`, `rtl/write_guard.sv` | `tests/dcache_test.py`, `tests/cache_model.py`, `tests/mutants/dcache_mutants.py`, `tb/tb_dcache.sv` | n/a | `docs/logs/T2.4.md` |
| T2.5 | `sw/link.ld` | `ASSERT` in the linker script | n/a | `docs/CODE_DATA_SEPARATION.md` |
| T2.6 | testbench parameters in `tb/` | `tests/invariant_test.py`, `tests/dcache_test.py` | n/a | `docs/logs/T2.6.md` |
| T2.7 | counters in `rtl/icache.sv`, `rtl/dcache.sv` | `analysis/caches.py` | `analysis/caches.csv`, `analysis/caches_size.png`, `analysis/caches_line.png` | `docs/logs/T2.7.md` |
| T3.1 | `rtl/dcache.sv` (aw_* events) | `tb/wear_monitor.sv` (second agent) | `work/wear_*` | `docs/logs/T3.1.md` |
| T3.2 | n/a | `analysis/wear_stats.py` | per-line plots, heatmaps with sidecars | `docs/logs/T3.2.md` |
| T3.3 | n/a | `tests/wear_known.py` | n/a | `docs/logs/T3.3.md` |
| T3.4 | n/a | `analysis/wear_baseline.py` | `analysis/wear_baseline_f3a7ccb0eb4d.csv`, heatmaps | `docs/logs/T3.4.md` |
| T3.5 | `rtl/dcache.sv` (tr_* trace) | `analysis/wear_replay_suite.py`, `analysis/attack_replay_suite.py`, `tests/cache_model.py`, `tests/mutants/wear_mutants.py` | `analysis/attack_replay_results.csv` | `docs/logs/T3.5.md` |
| T4.1 | n/a | `tests/attack_lfsr.py` | n/a | `docs/logs/T4.1.md` |
| T4.2-T4.5 | `sw/attacks/` (RLA, RTA, RnLA, RnTA; direct and paper forms) | `tests/attack_program.py`, `tests/attack_mutant_control.py`, `analysis/attack_runner.py` | `analysis/attack_*.csv` | `docs/logs/T4.2.md` to `T4.5.md` |
| T4.6 | `sw/attacks/` mixed workloads | `analysis/attack_mixed.py` | `analysis/attack_mixed.csv` | `docs/logs/T4.6.md` |
| T4.7 | n/a | `analysis/attack_validate.py`, `analysis/attack_pmr_table.py` | `analysis/attack_pmr_all_workloads.csv`, heatmaps | `docs/logs/T4.7.md`, DEC-010 |
| T4.8 | n/a | `analysis/attack_tfail.py` | `analysis/attack_tfail_baseline.csv` | `docs/logs/T4.8.md` |
