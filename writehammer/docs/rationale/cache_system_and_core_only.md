# cache_system, core_only, and the OBSERVE and CORE_ONLY parameters

**What it is**

`rtl/cache_system.sv` is the I$, the D$ and the `write_guard` in one module: the part of the system the T6.5 cost study synthesizes. It has no memory model; both caches present line-granule requests on memory-side ports. `rv32_top_pipelined` instantiates it when `CACHES_ON = 1`, so the whole regression exercises it.

`rtl/core_only.sv` is the same pipeline source with no caches, guard, memory model or observation logic, used as the core-area denominator. Its fetch port (`i_addr`, `i_rdata`, `i_stall`) and Memory-stage data port (`d_*`, `d_stall`) are plain request and response ports; the stall inputs freeze the pipeline like a cache miss.

`OBSERVE = 0` ties every observation output (cache counters, array-write and request trace, peek port, guard counters) to zero so synthesis prunes the logic. `CORE_ONLY = 1` on the top selects the `ext_*` ports in place of memory and caches.

**Why it is built this way**

The cost study needs a synthesizable subset free of simulation-only logic, and a core-only denominator that is the real core's area, so `core_only` wraps the unchanged pipeline (the header says same pipeline source). Making the observation logic a parameter keeps the functional behavior identical; the header of `rtl/cache_system.sv` says this is checked by the whole test suite through the top. The repo does not document a rejected alternative.

**How it is verified**

`tests/core_only_test.py` runs random hazard-dense programs (seeds 1 to N) with random fetch and data stalls against `tests/refmodel.py`, and requires the wrapper's registers and memory to equal the top's. A control whose data-stall input is ignored must fail, so the check is not vacuous. At delivery it was run with `--n 100` (control: 60 of 60 programs fail as required); the script's default is N = 200. The flow also rejects a netlist that still contains observation-only signals (`flow/README.md`).

**Known limits**

MMIO stores (`0xF000_0xxx`) never appear on `d_*`, because the MMIO window is simulation-only. `core_only` leaves every observation output of the top unconnected. Equivalence of `OBSERVE = 0` and `OBSERVE = 1` is shown through the regression, not by a separate formal check; none is documented.
