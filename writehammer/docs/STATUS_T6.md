# T6 status

This worktree's T6 rows; the first agent merges them into `docs/STATUS.md`.

| Task | Status | Last command | Last result | Updated |
|---|---|---|---|---|
| T6.1 | PARTIAL | `MPLCONFIGDIR=/tmp/wh-mpl make eval` | 9,723/9,723 planned rows, all correct=1 and same runner commit; zero missing; four phase-based metric columns await author snapshots | 2026-11-04 |
| T6.2 | PARTIAL | `MPLCONFIGDIR=/tmp/wh-mpl make plots` | 13 miss-rate, 13 CPI/stall, 109 heatmaps, 3 tables, 3,101 post-hoc window rows; phase/sensitivity/physical/hypothesis outputs pending | 2026-11-04 |
| T6.3 | NOT RUN | | Requires calibrated T5 results | 2026-11-03 |
| T6.4 | NOT RUN | | Requires detector threshold/window sweep | 2026-11-03 |
| T6.5 | NOT RUN | `scripts/run.sh -- python3 flow/make_interface.py --check` | 16 planned variants and 13 calibrated detector thresholds checked without EDA; core-only top and author outputs pending | 2026-11-04 |
