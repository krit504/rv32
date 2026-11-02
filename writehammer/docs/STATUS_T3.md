# T3 status

This worktree's T3 results; the main agent merges these into `docs/STATUS.md`.

| Task | Status | Last command | Last result | Updated |
|---|---|---|---|---|
| T3.1 | DONE | `scripts/run.sh -- python3 analysis/wear_run.py work/wear_smoke/program.hex work/wear_smoke/run --maxcyc 100000 --expect-exit 1892521041` | Verilator smoke compiled; HALT matched; four CSVs and simulation log written | 2026-11-02 |
| T3.2 | DONE | `scripts/run.sh -- .venv/bin/python analysis/wear_stats.py work/wear_smoke/run` | JSON/CSV summary, two PNG figures, provenance sidecars; 71 writes, w_max=9 | 2026-11-02 |
| T3.3 | DONE | `scripts/run.sh -- python3 tests/wear_known.py` | 2/2 exact known-answer programs passed, including fills, byte merge and dirty eviction | 2026-11-02 |
| T3.4 | DONE | `make wear` | 13/13 benign workloads, summary row and heatmap per workload; exact golden replay on every run; frozen RTL tree f3a7ccb0eb4d | 2026-11-02 |
| T3.5 | PARTIAL | `scripts/run.sh -- python3 analysis/wear_replay_suite.py --benign` | 13/13 benign workloads exact at latency 20; mis-count mutant caught; attack images do not exist yet | 2026-11-02 |
| T4.1 | DONE | `scripts/run.sh -- python3 tests/attack_lfsr.py` | 4/4: native and RV32I known answer; broken-tap control caught in both | 2026-11-02 |
| T4.2 | DONE | `scripts/run.sh -- .venv/bin/python tests/attack_program.py --kind RLA` and `scripts/run.sh -- .venv/bin/python analysis/attack_runner.py --case rla_direct_s1 --case rla_paper_s1` | Local TENDRA/Write Hammer papers resolved Q-004; both RLA forms HALT 0, C5 mutant rejected, exact replay; 2M-cycle windows | 2026-11-02 |
| T4.3 | DONE | `scripts/run.sh -- .venv/bin/python tests/attack_program.py --kind RTA`; `scripts/run.sh -- .venv/bin/python tests/attack_mutant_control.py --kind RTA`; `scripts/run.sh -- .venv/bin/python analysis/attack_runner.py --case rta_direct_s1 --case rta_paper_s1` | Both forms HALT 0 on native and caches off/on; scoped broken core self-check HALT 127; exact replay; ~2M measured cycles | 2026-11-02 |
| T4.4 | NOT RUN | | Depends on attack definition and T4.2 | 2026-11-02 |
| T4.5 | NOT RUN | | Depends on attack definition and T4.2 | 2026-11-02 |
| T4.6 | NOT RUN | | Depends on attack programs | 2026-11-02 |
| T4.7 | NOT RUN | | Depends on attack programs and heatmaps | 2026-11-02 |
| T4.8 | NOT RUN | | Depends on attack baselines | 2026-11-02 |
