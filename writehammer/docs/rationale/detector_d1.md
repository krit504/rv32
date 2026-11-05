# Detector D1: per-line write counters

**What it is**

D1 is `DETECTOR = 2` in `rtl/write_guard.sv`. It keeps one W-bit saturating counter (W = 16) for each D$ line (128 at the primary geometry). A counter increments on each data-array write event of its line (store hits and fills; a bypassed store produces none). The window timer clears all counters every `WINDOW_CYCLES`. A counter above `THRESHOLD` sets its hot flag at once. A store is restricted (bypassed, action A1) when the flag of the line it targets is set. At a window end a flag is released if that window's final count is below half the threshold.

**Why it is built this way**

The window and decision semantics are DEC-011 in `docs/DECISIONS.md`. Counters are cleared each window so a counter equals the per-window count that `analysis/calibrate.py` measures; the rejected alternatives listed there are halving counters, evaluating flags only at window ends, and deciding from the current cycle's array-write line. The decision needs the line a store targets before any array write, so the guard has the extra inputs `store_line` and `store_busy`. Hot flags change only while no store is mid-request, because `rtl/dcache.sv` needs `bypass` constant during a request.

**How it is verified**

`tests/write_guard_test.py` passes 62/62: 14 directed assertions on the RTL output plus 48 random streams compared cycle by cycle with the independent model `tests/guard_model.py`. `tests/guard_mutants.py` catches 17/17 guard mutants, including G3 (compare `>=`), G10 (no hysteresis) and G12 (no saturation). The primary calibrated threshold is 740 (k = 2, window 10000, `docs/logs/T5.1-T5.7.md`).

**Known limits**

`docs/DECISIONS.md` DEC-010 records that benign `crc32` rewrites one line almost exclusively (PMR 127.937 of 128) and expects per-line detectors to flag it; an earlier version of the T5 log attributed D1's 9.8 % restricted stores in the quick integration set to this; that attribution was wrong (corrected in `docs/logs/T5.1-T5.7.md`): the restrictions came from the attack images (RLA direct 28.5 % of stores, mixed RLA 11.9 %) and `crc32` had 0 %. `docs/RESULTS.md` section 2 lists D1 with `fp_cycle_frac` 0 on all 13 benign runs at the primary configuration, so DEC-010's expectation is not borne out there; at 4 of the 18 registered D1 settings `crc32` is restricted (`docs/HYPOTHESES.md`). Section 3 shows D1 detecting 11 of 24 attack runs (median latency 3.904e+04 cycles) and section 5 a mean reduction of 0 versus NONE. Action A2 is not implemented. RTL windows can differ from the calibration's binning by a few cycles.
