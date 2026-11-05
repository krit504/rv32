# Instruction cache

**What it is**

`rtl/icache.sv` is a direct-mapped, read-only instruction cache. Size is `CACHE_BYTES` (default 2048) and line size `LINE_BYTES` (16, 32 or 64), so the default has 128 lines. Lookup is combinational: a hit returns the instruction in the same cycle. A miss runs a two-state FSM, `LOOKUP` to `REFILL` and back, and `imiss` stays high through the whole refill including the `mem_done` cycle, costing L+2 cycles for memory latency L. Counters record refills, lookups, misses and stall cycles.

**Why it is built this way**

The miss index and tag are captured at the miss. The live address is the PC, and a taken branch can change it while a refill runs, so the line must be filled with the block that was requested, under its own tag (header of `rtl/icache.sv`). It uses the same memory-side handshake as the D$ (`mem_valid` held until `mem_done`, line-aligned address, whole-line data) so both can sit behind the unified `rtl/mem_model.sv`. Read-only means no write path exists. The log records no rejected alternative.

**How it is verified**

`docs/logs/T2.3.md` states the I$ has no separate unit test. It is tested inside the full core by `tests/cache_integration.py` (L+2 first-fetch miss pattern at latencies 1, 2, 3 and 10; a loop that fits refills once; a branch to an uncached block; `imiss` together with a load-use stall and with a taken branch), `tests/hazard_tests.py` and `tests/random_lockstep.py` with caches on, the arch tests and the benchmarks. Mutants C1 (valid not cleared at reset), C2 (refill under the live address) and C7 (word lanes reversed) are caught; the full `make test` recorded mutants 52/52 caught. `tests/invariant_test.py` runs three small geometries, and the T2.7 sweeps in `analysis/caches.py` cover 1 to 8 KiB and 16 to 64-byte lines.

**Known limits**

No self-modifying code or `fence.i`; code and data regions are disjoint (T2.5). Fetch is word-aligned only (KI-001). Tags and data are not reset; only `valid` is.
