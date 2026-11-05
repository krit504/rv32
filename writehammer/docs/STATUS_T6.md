# T6 status

This worktree's T6 rows; the first agent merges them into `docs/STATUS.md`.

| Task | Status | Last command | Last result | Updated |
|---|---|---|---|---|
| T6.1 | DONE | `MPLCONFIGDIR=/tmp/wh-mpl JOBS=4 scripts/run.sh -- .venv/bin/python analysis/eval_matrix.py --run --jobs 4` | 9,723/9,723 planned rows, all correct=1 and same committed phase parser; zero missing; measured phase metrics present where applicable | 2026-11-05 |
| T6.2 | DONE | `MPLCONFIGDIR=/tmp/wh-mpl make plots` | All Section 8 figures/tables regenerated from measured CSVs, including physical area/Fmax and D2 M sweep; 109 heatmaps and 1,064 sensitivity points | 2026-11-05 |
| T6.3 | DONE | `scripts/run.sh -- .venv/bin/python analysis/hypotheses.py` | Generated verdicts: H1 REFUTED; H2 INCONCLUSIVE; H3 REFUTED, with full numeric report and provenance | 2026-11-05 |
| T6.4 | DONE | `MPLCONFIGDIR=/tmp/wh-mpl scripts/run.sh -- .venv/bin/python analysis/sensitivity.py` | 1,064 measured sweep points; 2,466 censored seeds recorded without invented latency; CSV, plot, provenance generated | 2026-11-05 |
| T6.5 | DONE | `scripts/run.sh -- python3 flow/parse_results.py --repeats 3` | Author-authorized pinned Docker flow completed 16 variants × 3 repeats; parsed table has periods, area/Fmax deltas, critical paths, tool/PDK/constraint provenance | 2026-11-05 |
