# Negative controls and bypass verification

**What it is**

Three controls live in `rtl/write_guard.sv` next to the detectors:

- `NEVER` (`DETECTOR = 5`) restricts nothing and must match `NONE` in every metric.
- `ALWAYS` (`DETECTOR = 1`) restricts every store, giving the upper bound of the bypass action.
- `PLACEBO` (`DETECTOR = 6`) restricts a seeded pseudo-random fraction PLACEBO_RATE in units of 1/65536 of stores: an xorshift32 generator advances once per completed store and the store is restricted when its low 16 bits are below the rate. The rate is set from a real detector's measured restricted-store fraction on the same workload (two passes, `docs/T5_INTERFACE.md`).

Bypass verification checks that a restricted store writes no data-array word and that its data reaches memory.

**Why it is built this way**

Spec Section 0A.D (`../docs/writehammer.md`) requires these controls and independent cross-checks so that a detector result is not self-graded: every real detector is to be compared with `PLACEBO` and `ALWAYS`, and a detector that does not beat its placebo is to be reported as such. The invariant-breaking mutant (a bypass that drops a store) must be caught by the integration check, not by the guard unit test.

**How it is verified**

`tests/bypass_verify.py` (18/18) runs `storeloop`, `memset_big` and an attack image: NONE must make store-hit array writes (so the check can fail), ALWAYS must make zero and log every store as bypassed, and ALWAYS and a stress D1 run must replay exactly against `tests/cache_model.py`. `tests/guard_integration.py` (full run: 41 images, 9 arms, 3 latencies, 1107 rows, 0 mismatches) compares every arm's final signature with the caches-off core, and checks that NEVER restricted nothing and that ALWAYS restricted every store. `tests/guard_mutants.py` catches 19/19, including X1 (bypass drops the store), X2 (bypass writes wrong data) and G14 (placebo rate ignored). In `docs/RESULTS.md` section 4, ALWAYS removes at most 20.8 % of array writes (minimum ratio 0.792); section 5 reports whether each detector beats PLACEBO.

**Known limits**

`ALWAYS` is a test control, not a defense. The restricted-store refill cost limits what bypass can achieve (see `docs/rationale/dcache.md`). The two-pass PLACEBO rate setting is done by the T6 harness, not by the RTL.
