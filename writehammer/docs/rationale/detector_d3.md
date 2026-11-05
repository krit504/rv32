# Detector D3: global store-rate counter

**What it is**

D3 is `DETECTOR = 4` in `rtl/write_guard.sv`. It has a single W-bit saturating counter of completed stores, including bypassed ones, so a store-heavy stream stays restricted. Above `THRESHOLD` within a window its flag is set at once, and the whole store stream is then restricted. `WG_MODE` selects STATIC (the flag latches until reset) or ADAPTIVE (re-evaluated at each window end; released when that window's count is below half the threshold).

**Why it is built this way**

It uses one counter and one flag, with no per-line state and no dependence on which line is written (`rtl/write_guard.sv`). DEC-011 in `docs/DECISIONS.md` sets that D3 counts stores whereas D1 and D2 count array writes. Hot flags change only while no store is mid-request, as for D1. The primary calibrated threshold is 1534 (k = 2, window 10000) from `analysis/calibration.csv`, using the per-window maximum of stores, 767, on the calibration set only (`docs/logs/T5.1-T5.7.md`).

**How it is verified**

`tests/write_guard_test.py` (62/62) includes STATIC versus ADAPTIVE directed cases and the model comparison. `tests/guard_mutants.py` has G5 (window reset broken), G11 (STATIC releases like ADAPTIVE) and G16 (D3 counts array writes instead of stores), all caught within 17/17. In `tests/guard_integration.py` the stress arms restricted 86 % (static) and 57 % (adaptive) of cycles over the quick set at latency 20, and the calibrated D3 arm 0 %.
**Known limits**

It counts all stores, so by construction it carries no information about where writes land. At the calibrated primary configuration `docs/RESULTS.md` section 3 shows D3 detecting 0 of 24 attack runs, while section 2 shows benign false-positive cycle fractions of mean 0.01133 and max 0.1473 (ADAPTIVE) and mean 0.07539 and max 0.9801 (STATIC, worst workload `huffbench`). STATIC mode never recovers within a run. The threshold is twice the per-window store maximum of Dhrystone and CoreMark (1,534 per 10,000 cycles); the busiest attack, RLA direct, issues about 1,430 stores per window, so it stays under it, while `huffbench` has store bursts above it (`REPORT.md` section 4.1, `docs/INTEGRITY_REPORT.md` question 2). Over all registered settings D3 does detect 30 of 432 attack runs (`scripts/audit.py`). Action A2 is not implemented.
