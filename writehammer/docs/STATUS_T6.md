# T6 status

This worktree's T6 rows; the first agent merges them into `docs/STATUS.md`.

| Task | Status | Last command | Last result | Updated |
|---|---|---|---|---|
| T6.1 | DONE | `MPLCONFIGDIR=/tmp/wh-mpl JOBS=4 scripts/run.sh -- .venv/bin/python analysis/eval_matrix.py --run --jobs 4` | 9,723/9,723 planned rows, all correct=1 and same committed phase parser; zero missing; measured phase metrics present where applicable | 2026-11-05 |
| T6.2 | PARTIAL | `MPLCONFIGDIR=/tmp/wh-mpl make plots` | 13 miss-rate, 13 CPI/stall, 109 heatmaps, 5 tables, 3,101 post-hoc windows; 4,718 matched control comparisons; phase/sensitivity/physical/hypothesis outputs pending | 2026-11-04 |
| T6.3 | DONE | `scripts/run.sh -- .venv/bin/python analysis/hypotheses.py` | Generated verdicts: H1 REFUTED; H2 INCONCLUSIVE; H3 REFUTED, with full numeric report and provenance | 2026-11-05 |
| T6.4 | DONE | `MPLCONFIGDIR=/tmp/wh-mpl scripts/run.sh -- .venv/bin/python analysis/sensitivity.py` | 1,064 measured sweep points; 2,466 censored seeds recorded without invented latency; CSV, plot, provenance generated | 2026-11-05 |
| T6.5 | NOT RUN | `scripts/run.sh -- python3 flow/run_flow.py --check-plan` | Both tops delivered; 16 variants and 13 calibrated thresholds checked without EDA; author physical outputs pending | 2026-11-04 |
