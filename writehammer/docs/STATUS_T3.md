# T3 status

This worktree's T3 results; the main agent merges these into `docs/STATUS.md`.

| Task | Status | Last command | Last result | Updated |
|---|---|---|---|---|
| T3.1 | DONE | `scripts/run.sh -- python3 analysis/wear_run.py work/wear_smoke/program.hex work/wear_smoke/run --maxcyc 100000 --expect-exit 1892521041` | Verilator smoke compiled; HALT matched; four CSVs and simulation log written | 2026-11-02 |
| T3.2 | DONE | `scripts/run.sh -- .venv/bin/python analysis/wear_stats.py work/wear_smoke/run` | JSON/CSV summary, two PNG figures, provenance sidecars; 71 writes, w_max=9 | 2026-11-02 |
| T3.3 | DONE | `scripts/run.sh -- python3 tests/wear_known.py` | 2/2 exact known-answer programs passed, including fills, byte merge and dirty eviction | 2026-11-02 |
| T3.4 | NOT RUN | | RTL freeze pending | 2026-11-02 |
| T3.5 | PARTIAL | `scripts/run.sh -- python3 analysis/wear_replay_suite.py --benign` | 13/13 benign workloads exact at latency 20; mis-count mutant caught; attack images do not exist yet | 2026-11-02 |
