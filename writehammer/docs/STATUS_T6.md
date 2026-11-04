# T6 status

This worktree's T6 rows; the first agent merges them into `docs/STATUS.md`.

| Task | Status | Last command | Last result | Updated |
|---|---|---|---|---|
| T6.1 | PARTIAL | `MPLCONFIGDIR=/tmp/wh-mpl make eval` | 9,723/9,723 planned rows, all correct=1 and same runner commit; zero missing; four phase-based metric columns await author snapshots | 2026-11-04 |
| T6.2 | PARTIAL | `scripts/run.sh -- python3 analysis/eval_wear_export.py`; `make plots` | CSV-only plotting passed for six-row development subset: two figures, four measured heatmaps, two tables; detector/sensitivity/physical/hypothesis data pending | 2026-11-03 |
| T6.3 | NOT RUN | | Requires calibrated T5 results | 2026-11-03 |
| T6.4 | NOT RUN | | Requires detector threshold/window sweep | 2026-11-03 |
| T6.5 | NOT RUN | | Author launches pinned EDA container after synthesis tops arrive | 2026-11-03 |
