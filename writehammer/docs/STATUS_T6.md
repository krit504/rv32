# T6 status

This worktree's T6 rows; the first agent merges them into `docs/STATUS.md`.

| Task | Status | Last command | Last result | Updated |
|---|---|---|---|---|
| T6.1 | PARTIAL | `MPLCONFIGDIR=/tmp/wh-mpl make eval` | 9,723/9,723 planned rows, all correct=1 and same runner commit; zero missing; four phase-based metric columns await author snapshots | 2026-11-04 |
| T6.2 | PARTIAL | `MPLCONFIGDIR=/tmp/wh-mpl make plots` | 13 miss-rate, 13 CPI/stall, 109 heatmaps, 5 tables, 3,101 post-hoc windows; 4,718 matched control comparisons; phase/sensitivity/physical/hypothesis outputs pending | 2026-11-04 |
| T6.3 | NOT RUN | `scripts/run.sh -- .venv/bin/python analysis/hypotheses.py` | Full matrix present; script correctly refuses missing phase-based held-out false-positive fractions | 2026-11-04 |
| T6.4 | NOT RUN | `MPLCONFIGDIR=/tmp/wh-mpl scripts/run.sh -- .venv/bin/python analysis/sensitivity.py` | Full threshold/window sweep present; script correctly refuses missing phase-based false-positive and latency fields | 2026-11-04 |
| T6.5 | NOT RUN | `scripts/run.sh -- python3 flow/make_interface.py --check` | 16 planned variants and 13 calibrated detector thresholds checked without EDA; core-only top and author outputs pending | 2026-11-04 |
