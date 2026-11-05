# Data cache and the restricted-store (bypass) path

**What it is**

`rtl/dcache.sv` is a direct-mapped, write-back, write-allocate data cache (default 2048 bytes, 16-byte lines, 128 lines) with valid and dirty bits, byte-enable stores and an FSM (`LOOKUP`, `WB`, `FILL`, `BYP_WB`, `BYP_WR`, `WAIT_ST`, `WAIT_FILL`). Store hits finish in the lookup cycle; a store miss is a fill followed by a store hit (two array writes). It exposes array-write events, a per-request trace and counters for the wear monitor.

The restricted store is the action of spec Section 4. If the line is present, write it back when dirty, invalidate it, then write the store's bytes to memory; if absent, write memory only. It never writes the data array.

**Why it is built this way**

Invalidation follows the spec's definition of a restricted store (`../docs/writehammer.md`, Section 4). The consequence is documented: a later load of that line misses and refills, and a fill is an array write. `docs/RESULTS.md` section 4 measures it: with every store restricted (ALWAYS) the array writes fall to at most 20.8 % below NONE (mean ratio 0.919, median 0.997, minimum 0.792) because of refills after bypass; for `rla_direct_s1` 285,713 of 285,716 remaining array writes are such refills. The repo does not document a rejected alternative for invalidation versus keeping the line valid.

**How it is verified**

`tests/dcache_test.py` runs 51 configurations (1/2/4/8 KiB, 16/32/64-byte lines, latencies 1/3/10 plus random, array-write latency 1 and 4, bypass probability 0, 0.15, 0.5) of 1500 operations each against two oracles: a plain byte array, and `tests/cache_model.py` for counters, per-line array writes and every request's stall cycles. Result 51/51, and 12 of 12 D$ mutants caught, including "bypass leaves the line valid", "bypass writes the array" and "refills after bypass not counted" (`docs/logs/T2.4.md`).

**Known limits**

No misaligned accesses, no MMIO (decoded earlier), no instruction-fetch coherence. Metadata writes are not counted as array writes. The per-request stall-cycle check is stated for fixed latency only (`tests/dcache_test.py`).
