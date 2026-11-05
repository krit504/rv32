# Detector D2: hashed counters

**What it is**

D2 is `DETECTOR = 3` in `rtl/write_guard.sv`. It has the same behavior as D1 but with M counters instead of one per line, where M is a power of two, at most 64 and at most LINES/2 (an elaboration error otherwise). Several lines share a counter, so a bucket's count is the sum of its lines' array writes.

**The exact hash.** The `bucket()` function takes the D$ line index zero-extended to 16 bits:

1. `f = idx[7:0] ^ idx[15:8]` (XOR-fold to 8 bits);
2. `p = (f * 167) mod 256` (multiply by the odd constant 167, keep 8 bits);
3. bucket = the top `log2(M)` bits of `p`, that is `p[7 : 8-log2(M)]`.

Both the array-write line (`line_idx`) and the target line of a store (`store_line`) go through it. `docs/T5_INTERFACE.md` gives the same formula, and `tests/guard_model.py` and `analysis/calibrate.py` reuse it.

**Why it is built this way**

DEC-011 (`docs/DECISIONS.md`) fixes the hash and says each choice is the simplest that keeps the calibration and the RTL measuring the same quantity; the repo does not document why 167 was chosen or what hashes were rejected. The DEC-011 text itself calls 167 odd; mutant G15 replaces it with the even 166. Counter, window and hysteresis semantics are those of D1.

**How it is verified**

`tests/write_guard_test.py` (62/62) compares RTL and `tests/guard_model.py` cycle by cycle. `tests/guard_mutants.py` has G9 (hash index taken from the wrong source) and G15 (multiplier 166), both caught, among 17/17. `analysis/calibrate.py` computes per-bucket maxima for every M using the same function.

**Known limits**

Lines that share a bucket share its count, so in principle one hot line can restrict stores to other lines; the repo does not measure that effect separately. At the primary configuration `docs/RESULTS.md` section 3 shows D2 detecting 11 of 24 attack runs for each of M = 4 to 64, and section 2 shows `fp_cycle_frac` 0 on all 13 benign runs for every M. Section 5 shows a mean reduction of 0 versus NONE. Physical cost does not follow a clean trend with M, and differences under about 2 % of cache area are not claims (`flow/cost_table.md`). Action A2 is not implemented.
