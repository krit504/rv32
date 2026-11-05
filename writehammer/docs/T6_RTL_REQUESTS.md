# T6 RTL interface requests for T5 owner

No RTL file was edited on `t6-eval`. T6.5 needs two synthesizable, observation-free tops on `main` before the author launches the pinned physical flow:

Both requested tops are delivered on `main` at `e66ada1`:
`rtl/cache_system.sv` with `OBSERVE=0`, and `rtl/core_only.sv` (module
`core_only`) using `rv32_top_pipelined` with `CORE_ONLY=1`. The original
requirements below remain as the physical-flow acceptance contract.

1. `rtl/cache_system.sv`: I$ + D$ + `write_guard`, without the simulation memory model. D$ flop arrays remain present. The top needs `clk`, `rst_n`, stable request/response ports, and parameters for `ICACHE_BYTES`, `DCACHE_BYTES`, `LINE_BYTES`, `DETECTOR`, `ACTION`, `MODE`, `WINDOW_CYCLES`, `THRESHOLD`, `M` and counter width `W` (use the final T5 names, documented in `docs/T5_INTERFACE.md`). Its request/response ports must be constrained identically for every variant.
2. A core-only top (proposed `rtl/core_only.sv`) with the caches and write guard removed, so the same script can measure the core-area denominator for “% of core.” It needs `clk`, `rst_n` and stable I/D request/response ports. Please give its final module/file name in `docs/T5_INTERFACE.md`.

For both tops, remove or compile out **all observation-only logic** from synthesis: `dc_aw_*`, `dc_tr_*`, cache and MMIO performance counters, wear trace, debug peek/read ports and the memory model. The existing cache source files include these ports and state; synthesizing them as-is would inflate area and alter timing. The flow will check that the final elaborated netlist has no observation/debug ports before accepting an area number.

The detector parameters and per-phase WG snapshot contract are delivered in
`docs/T5_INTERFACE.md` and `tb/tb_prog.sv`. The evaluation bench is generated
under `work/eval/` for observation-only wear counts; it never edits `tb/` or
`rtl/`.

The attack taxonomy used by this evaluation is prior work of the author's group (TENDRA and the Write Hammer draft). The `crc32` false-positive finding in DEC-010 remains part of the evaluation.
