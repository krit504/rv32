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
| T2.3 | DONE | `make test` | I$ parameterized and on the shared memory interface; directed and full-core tests pass; caches-on invariant holds in 9 configurations | 2026-11-02 |
| T2.4 | DONE | `tests/dcache_test.py`, `make test` | 51/51 against the byte-array golden and the Python cache model; 12/12 D$ mutants caught | 2026-11-02 |
| T2.5 | DONE | `docs/CODE_DATA_SEPARATION.md`; linker `ASSERT` | note written; linker script separates code (.text/.rodata) from data (4 KiB page) and stack | 2026-11-02 |
| T2.6 | DONE | `make invariant`, `make test` | arch 37/37 (= Spike), workloads 13/13, random 200/200, identical across 9 configurations incl. 3 small-cache geometries | 2026-11-02 |
| T2.7 | DONE | `make caches` | 78 runs, `analysis/caches.csv`, `caches_size.png`, `caches_line.png` with provenance sidecars | 2026-11-02 |
| T3.1 | DONE | `scripts/run.sh -- python3 analysis/wear_run.py work/wear_smoke/program.hex work/wear_smoke/run --maxcyc 100000 --expect-exit 1892521041` | Verilator smoke compiled; HALT matched; four CSVs and simulation log written | 2026-11-02; re-run independently from main 2026-11-03 |
| T3.2 | DONE | `scripts/run.sh -- .venv/bin/python analysis/wear_stats.py work/wear_smoke/run` | JSON/CSV summary, two PNG figures, provenance sidecars; 71 writes, w_max=9 | 2026-11-02; re-run independently from main 2026-11-03 |
| T3.3 | DONE | `scripts/run.sh -- python3 tests/wear_known.py` | 2/2 exact known-answer programs passed, including fills, byte merge and dirty eviction | 2026-11-02; re-run independently from main 2026-11-03 |
| T3.4 | DONE | `make wear` | 13/13 benign workloads, summary row and heatmap per workload; exact golden replay on every run; frozen RTL tree f3a7ccb0eb4d | 2026-11-02; re-run independently from main 2026-11-03 |
| T3.5 | DONE | `scripts/run.sh -- python3 analysis/attack_replay_suite.py`; `scripts/run.sh -- python3 analysis/wear_replay_suite.py --benign`; `scripts/run.sh -- python3 tests/mutants/wear_mutants.py work/attack_run/rla_direct_s1/wear` | 24/24 attack and 13/13 benign exact replays; mis-counting attack monitor mutant caught | 2026-11-03; re-run independently from main 2026-11-03 |
| T4.1 | DONE | `scripts/run.sh -- python3 tests/attack_lfsr.py` | 4/4: native and RV32I known answer; broken-tap control caught in both | 2026-11-02; re-run independently from main 2026-11-03 |
| T4.2 | DONE | `scripts/run.sh -- .venv/bin/python tests/attack_program.py --kind RLA` and `scripts/run.sh -- .venv/bin/python analysis/attack_runner.py --case rla_direct_s1 --case rla_paper_s1` | Local TENDRA/Write Hammer papers resolved Q-004; both RLA forms HALT 0, C5 mutant rejected, exact replay; 2M-cycle windows | 2026-11-02; re-run independently from main 2026-11-03 |
| T4.3 | DONE | `scripts/run.sh -- .venv/bin/python tests/attack_program.py --kind RTA`; `scripts/run.sh -- .venv/bin/python tests/attack_mutant_control.py --kind RTA`; `scripts/run.sh -- .venv/bin/python analysis/attack_runner.py --case rta_direct_s1 --case rta_paper_s1` | Both forms HALT 0 on native and caches off/on; scoped broken core self-check HALT 127; exact replay; ~2M measured cycles | 2026-11-02; re-run independently from main 2026-11-03 |
| T4.4 | DONE | `scripts/run.sh -- .venv/bin/python tests/attack_program.py --kind RnLA`; `scripts/run.sh -- .venv/bin/python tests/attack_mutant_control.py --kind RnLA`; `scripts/run.sh -- .venv/bin/python analysis/attack_runner.py --case rnla_direct_s1 --case rnla_direct_s2 --case rnla_direct_s3 --case rnla_direct_s4 --case rnla_direct_s5 --case rnla_paper_s1 --case rnla_paper_s2 --case rnla_paper_s3 --case rnla_paper_s4 --case rnla_paper_s5` | 10/10 native and RTL, 10/10 broken-core HALT 127, 10/10 exact replay; ~2M-cycle windows | 2026-11-02; re-run independently from main 2026-11-03 |
| T4.5 | DONE | `scripts/run.sh -- .venv/bin/python tests/attack_program.py --kind RnTA`; `scripts/run.sh -- .venv/bin/python tests/attack_mutant_control.py --kind RnTA`; `scripts/run.sh -- .venv/bin/python analysis/attack_runner.py --case rnta_direct_s1 --case rnta_direct_s2 --case rnta_direct_s3 --case rnta_direct_s4 --case rnta_direct_s5 --case rnta_paper_s1 --case rnta_paper_s2 --case rnta_paper_s3 --case rnta_paper_s4 --case rnta_paper_s5` | 10/10 native and RTL, 10/10 broken-core HALT 127, 10/10 exact replay; ~2M-cycle windows | 2026-11-02; re-run independently from main 2026-11-03 |
| T4.6 | DONE | `scripts/run.sh -- .venv/bin/python analysis/attack_mixed.py` | 4/4 HALT 0, exact replay; PHASE 0–3 gaps all within 1% of 1M cycles; marker negative controls rejected | 2026-11-03; re-run independently from main 2026-11-03 |
| T4.7 | PARTIAL | `scripts/run.sh -- .venv/bin/python analysis/attack_validate.py --benign analysis/wear_baseline_f3a7ccb0eb4d.csv`; `scripts/run.sh -- python3 analysis/attack_pmr_table.py analysis/wear_baseline_f3a7ccb0eb4d.csv analysis/attack_6e72b1b2034e_validation.csv` | 24/24 wear/replay; 13 benign + 24 attack PMR table and heatmaps; wandering visible; binding PMR rule fails 23/24 (benign crc32 PMR 127.937) | 2026-11-03; PMR rule fails 23/24: DEC-010, KI-017 |
| T4.8 | DONE | `scripts/run.sh -- python3 analysis/attack_tfail.py analysis/wear_baseline_f3a7ccb0eb4d.csv` | Baseline T_fail table generated for 13 benign and 24 attack workloads at 50/100/500 MHz, with source-hash sidecar | 2026-11-03; re-run independently from main 2026-11-03 |
| T5.1 | DONE | `make lint test` | lint 0 warnings; full test green incl. mutants 52/52 and NONE unchanged; interface in docs/T5_INTERFACE.md | 2026-11-04 |
| T5.2 | DONE | `tests/write_guard_test.py`, `tests/guard_mutants.py` | D1: unit 62/62 vs independent model; 17/17 guard mutants caught (docs/logs/T5.1-T5.7.md) | 2026-11-03 |
| T5.3 | DONE | `tests/write_guard_test.py`, `tests/guard_mutants.py` | D2: unit 62/62 vs independent model; 17/17 guard mutants caught (docs/logs/T5.1-T5.7.md) | 2026-11-03 |
| T5.4 | DONE | `tests/write_guard_test.py`, `tests/guard_mutants.py` | D3: unit 62/62 vs independent model; 17/17 guard mutants caught (docs/logs/T5.1-T5.7.md) | 2026-11-03 |
| T5.5 | PARTIAL | `tests/guard_integration.py`, `tests/bypass_verify.py` | A1 integrated and verified (invariant holds, 41 images x 9 arms x 3 latencies, 0 mismatches). Unmet: A2 (stall-throttle) NOT RUN (KI-020) | 2026-11-04 |
| T5.6 | DONE | `make calibrate` | `analysis/calibration.csv` from Dhrystone+CoreMark only; windows 1000/10000/100000; held-out never built | 2026-11-03 |
| T5.7 | DONE | `tests/write_guard_test.py`, `tests/guard_mutants.py` | 62/62; 17/17 mutants caught | 2026-11-03 |
| T5.8 | DONE | `tests/guard_integration.py` (full, `make guard-integration`) | 41/41 images (13 benign, 24 attack, 4 mixed) x 9 arms x LAT 1, 20, random: 1107 rows, 0 signature mismatches; non-vacuity checked (every restricting arm restricted stores); quick subset in `make test` | 2026-11-04 |
| T5.9 | DONE | `tests/guard_integration.py` | restricted cycles, first-restriction cycle, stores and restricted stores, dc_bypass, dc_rab appear in the run CSV (work/guard_integration/results_full.csv) | 2026-11-04 |
| T5.10 | PARTIAL | `tests/bypass_verify.py`, `tests/guard_integration.py`, `tests/guard_mutants.py` | bypass verification 18/18 (zero store-hit array writes under ALWAYS, replay vs independent cache model, memory equals caches-off golden); NEVER == NONE in cycles and counters on every image; dropped-store and wrong-data bypass mutants caught. Unmet: rate-matched PLACEBO two-pass runs and control rows in results.csv/report are the T6 harness (RTL side verified) | 2026-11-04 |
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
