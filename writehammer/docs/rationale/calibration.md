# Threshold calibration and the held-out set

**What it is**

`analysis/calibrate.py` derives the detector thresholds. It runs only the calibration set, Dhrystone (500 runs) and CoreMark (10 iterations), on the frozen RTL with no detector (2 KiB D$, 16-byte lines, 20-cycle memory) for windows of 1000, 10000 and 100000 cycles. Per window length it takes the maximum per-window count over both workloads: D1 array writes of one line, D2 array writes summed per hash bucket for each M of 4 to 64 (same hash as `rtl/write_guard.sv`), and D3 completed stores. `THRESHOLD = ceil(k x max)` for k of 1.5, 2 and 4. The output is `analysis/calibration.csv` (63 rows) with a hash sidecar. At window 10000 the maxima are 370 per line and 767 stores, giving thresholds 740 and 1534 at k = 2 (`docs/logs/T5.1-T5.7.md`).

**Why it is built this way**

The thresholds must be measured on the same quantity the RTL counts, which is why counters clear each window (DEC-011 in `docs/DECISIONS.md`). Spec Section 0A.B forbids tuning on the false-positive set. DEC-008 fixed the held-out set before any detector existed: `crc32`, `md5sum`, `nettle-sha256`, `nettle-aes`, `huffbench`, `wikisort`, `sglib-combined`, `qrduino`, `memcpy_big`, `memset_big` and `storeloop`, chosen by a stated run-time rule and behavior groups rather than by detector results. Alternatives considered there: all 19 kernels, the 4 cheapest, a random subset.

**How the held-out set is protected**

`analysis/calibrate.py` builds only the `CALIBRATION` entries of the locked registry `tests/workloads.py`, and aborts if any other entry would be read. The registry is hash-locked (`docs/LOCKED.sha256`, checked by `scripts/check_locks.sh`), and spec Section 0A.B item 4 forbids tuning thresholds with held-out workloads.

**How it is verified**

The held-out guard is a code check rather than a test; no test of it is documented. `tests/guard_integration.py` reads thresholds from `analysis/calibration.csv` for its calibrated arms.

**Known limits**

The RTL window timer starts at reset and can defer a boundary past a mid-request store, so its windows differ from the script's `cycle // WINDOW` binning by a few cycles. Two workloads set the maxima, so a held-out program can exceed them; `docs/RESULTS.md` section 2 shows D3 doing so on `huffbench`.
