# TRACEABILITY

Task to RTL files, tests, result rows, figures and the document sections that cite them (spec 0B.6). Updated as each task finishes.

| Task | RTL | Tests | Result rows / figures | Cited in |
|---|---|---|---|---|
| T0.3 | `rtl/*` (imported core) | `tests/nohazard_test.py`, `tests/hazard_tests.py`, `tests/cache_integration.py`, `tests/run_mutants.py` | `tests/BASELINE_COUNTS.json` | `docs/logs/T0.3.md` |
| T1.1 | `rtl/rv32_top_pipelined.sv`, `rtl/e_m_reg.sv`, `rtl/dmem.sv`, `rtl/dcache.sv`, `rtl/backing_mem.sv` | `tests/subword_tests.py` | n/a | `docs/logs/T1.1.md` |
| T1.2 | n/a | `tests/refmodel.py`, `tests/refmodel_selftest.py`, `tests/subword_tests.py`, `tests/mutants/subword_mutants.py` | n/a | `docs/logs/T1.2.md` |
