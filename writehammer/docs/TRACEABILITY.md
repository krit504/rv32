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
