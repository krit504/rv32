# Wear monitor, PMR and T_fail

**What it is**

`tb/wear_monitor.sv` is a simulation-only observer of the D$ data-array write strobe. It counts one event per asserted `aw_valid` pulse, per line and per window of `WINDOW_CYCLES` (default 10000), and separates store or partial-merge writes from fills. It writes `wear_windows.csv`, `wear_lines.csv`, `wear_phases.csv` (MMIO phase markers) and `dc_trace.csv` (completed non-MMIO D$ requests). It checks nothing about the cache itself.

`analysis/wear_stats.py` turns these into the Section 4 quantities of `../docs/writehammer.md`: `w[i]`, PMR = max over lines of `w[i]` divided by the mean, reported over all lines and over written lines, and `T_fail = E * cycles / (w_max * f_clk)` with `E = 1e15` and f_clk of 50, 100 and 500 MHz. Reads, write-back reads and tag, valid and dirty updates are not array writes.

**Why it is built this way**

The monitor only counts; correctness is delegated to an independent check. `analysis/wear_replay.py` replays `dc_trace.csv` through `tests/cache_model.py`, which was written before the monitor, and requires exact per-line counts and counters (`docs/logs/T3.5.md`). `E` is labelled illustrative and `T_fail` an extrapolation from a short run. The logs record no rejected alternative.

**How it is verified**

`tests/wear_known.py` (2/2): hand-derived micro-programs with expected line counts 7 and 2 and counters 7 accesses, 3 hits, 4 misses, 1 write-back, 5 stores. `wear_stats.py` rejects runs whose window sums differ from per-line totals. The golden replay matched 13/13 benign workloads at 2 KiB, 16-byte lines, latency 20 (also 13/13 at latency 2) and 24/24 attack images. `tests/mutants/wear_mutants.py` miscounts one line in a copied run and the replay rejects it. `make wear` (T3.4) gave 13/13 workloads; PMR over all lines ranges from 1.0 to 127.93722842512231 (`crc32`).

**Known limits**

A modeled-NVM, single-core study: no claim about SRAM endurance or multicore attribution. `T_fail` depends on the assumed `E`. The monitor assumes reset precedes traffic and one `finish_run` call after HALT.
