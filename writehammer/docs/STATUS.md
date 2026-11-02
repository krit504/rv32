# STATUS

Resume point for any session. Spec: `../../docs/writehammer.md` (v4).
Status words (spec 0B.11): `DONE` only if the acceptance check ran and passed in this run; `PARTIAL` lists unmet sub-criteria; otherwise `BLOCKED` or `NOT RUN`.

Times are IST.

| Task | Status | Last command | Last result | Updated |
|---|---|---|---|---|
| T0.1 | DONE | `ls writehammer` + first commit | layout, `.gitignore`, `STATUS.md`, `DECISIONS.md`, `OPEN_QUESTIONS.md` exist | 2026-11-01 18:16 |
| T0.2 | DONE | `scripts/fetch_third_party.sh` | `docs/TOOLS.md` complete; EDA tool versions are author-reported (container not started by agent) | 2026-11-01 18:45 |
| T0.3 | PARTIAL | `make lint && make test` | lint 0 warnings; test green (21/21 x5, 25/25 x10, 36/36, 12/12 mutants). Unmet: the quoted "5 of 5 mutants" cannot be rerun (no harness in repo); replaced by a 12-mutant harness | 2026-11-01 |
| T0.4 | DONE | `make -n all` | exit 0; unimplemented targets fail loudly with their task ID | 2026-11-01 |
| T0.5 | DONE | `make lint test` via `scripts/run.sh` | complete log records in `logs/runs/`; templates exist | 2026-11-01 |
| T0.6 | DONE | `make locks locks-selftest` | 14 files locked; tamper cases behave as required | 2026-11-01 |
| T1.1 | DONE | `make lint test` | lint 0 warnings; all earlier tests unchanged | 2026-11-01 |
| T1.2 | DONE | `make test` | subword 11/11 x5 configs; mutants 20/20 caught | 2026-11-01 |
| T1.3 | DONE | `make test` | perf 21/21 hand-computed; mutants 27/27 caught | 2026-11-01 |
| T1.4 | DONE | `tests/toolchain_test.py`; `make test` | 10/10 against the native-gcc oracle at 5 configs; mutants 30/30 caught | 2026-11-02 |
| T1.5 | DONE | `make arch-test` | 37/37 caches off; 37/37 caches on LAT 1 and 10; bad-core control fails as required | 2026-11-02 |
| T1.6 | DONE | `make random` | 1000/1000 in 5 configurations; Spike vs model 200/200; 5 bad cores caught | 2026-11-02 |
| T1.7 | DONE | `make bench` | Dhrystone self-check ok; CoreMark CRCs equal native oracle; caches off and on; baseline in docs/baseline.md | 2026-11-02 |
| T1.8 | DONE | `make bench` | 19/19 Embench kernels build and pass; 8 held-out + 3 in-repo workloads 14/14 incl. native oracle and bad-core controls | 2026-11-02 |
| T2.1 | DONE | `tests/mem_model_test.py` | 18/18; 6 mutants caught | 2026-11-02 |
| T2.2 | DONE | `tests/stall_injection_test.py` | 4000 random programs + no-hazard regression with injection match; 4 mutants caught | 2026-11-02 |
| T2.3 | PARTIAL | `tests/cache_integration.py`, `tests/hazard_tests.py` (caches on), `tests/invariant_test.py --quick` | I$ parameterized (size, line size) and on the shared memory interface; directed tests pass. Unmet: full `make test` not rerun after the last edits | 2026-11-02 |
| T2.4 | PARTIAL | `tests/dcache_test.py` | 51/51 against the byte-array golden and the Python cache model, 12/12 D$ mutants caught. Unmet: full `make test` not rerun after the last edits; invariant-test mutant check still running | 2026-11-02 |
| T2.5 | DONE | `docs/CODE_DATA_SEPARATION.md`; linker `ASSERT` | note written; linker script separates code (.text/.rodata) from data (4 KiB page) and stack | 2026-11-02 |
| T2.6 | PARTIAL | `tests/invariant_test.py --quick` | quick mode 3/3 (arch, workloads, random identical across 6 configurations). Unmet: full run, mutant check | 2026-11-02 |
| T2.7 | NOT RUN | | | |
| T3.1 | NOT RUN | | | |
| T3.2 | NOT RUN | | | |
| T3.3 | NOT RUN | | | |
| T3.4 | NOT RUN | | | |
| T3.5 | NOT RUN | | | |
| T4.1 | NOT RUN | | | |
| T4.2 | NOT RUN | | | |
| T4.3 | NOT RUN | | | |
| T4.4 | NOT RUN | | | |
| T4.5 | NOT RUN | | | |
| T4.6 | NOT RUN | | | |
| T4.7 | NOT RUN | | | |
| T4.8 | NOT RUN | | | |
| T5.1 | NOT RUN | | | |
| T5.2 | NOT RUN | | | |
| T5.3 | NOT RUN | | | |
| T5.4 | NOT RUN | | | |
| T5.5 | NOT RUN | | | |
| T5.6 | NOT RUN | | | |
| T5.7 | NOT RUN | | | |
| T5.8 | NOT RUN | | | |
| T5.9 | NOT RUN | | | |
| T5.10 | NOT RUN | | | |
| T6.1 | NOT RUN | | | |
| T6.2 | NOT RUN | | | |
| T6.3 | NOT RUN | | | |
| T6.4 | NOT RUN | | | |
| T6.5 | NOT RUN | | | |
| T7.1 | NOT RUN | | | |
| T7.2 | NOT RUN | | | |
| T7.3 | NOT RUN | | | |
| T7.4 | NOT RUN | | | |
| T7.5 | NOT RUN | | | |
| T7.6 | NOT RUN | | | |
| T7.7 | NOT RUN | | | |
| T7.8 | NOT RUN | | | |
