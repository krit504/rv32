# Physical cost flow (sky130, T6.5)

**What it is**

`flow/run_flow.py` synthesizes and times 16 variants with Yosys 0.66 and OpenSTA 2.7.0 on `sky130_fd_sc_hd` (tt_025C_1v80), in the author's pinned image `sha256:369c964b...3103` (full ID in `flow/README.md`), with one SDC template and the same scripts for every variant. The variants (`flow/variants.csv`) are `core_only` alone, and `cache_system` with a 2 KiB I$, a 1 KiB or 2 KiB D$ and detector NONE, D1, D3 or D2 (M 4 to 32, and 64 at 2 KiB). The runner searches each variant's minimum passing clock period to 0.1 ns, with 3 repeats (48 runs). `flow/parse_results.py` writes `flow/cost_table.md`.

**Why it is built this way**

The flow runs `OBSERVE = 0` and rejects any netlist that still contains observation signals, so only the real hardware is costed. A core-only run provides the denominator for "percent of the core". The author, not the agent, controls physical runs (Q-002, and the explicit 2026-11-05 authorization in `docs/logs/T6.5.md`).

**What the numbers support**

Synthesis variation is about 2 % of the cache area (`docs/RESULTS.md` section 6), so area deltas below that are not claims. Example from `flow/cost_table.md`: `D2048_D3` is -0.03 %. D2 with M of 4, 8 and 16 comes out smaller than NONE, which a design that only adds logic cannot be (`docs/TRACKER.md`), so deltas of that size are synthesis variation. Only D1 stands out above 2 % (+3.96 % at 1 KiB, +5.71 % at 2 KiB). The Fmax deltas have no stable sign: `D1024_D1` is -10.16 % but `D2048_D1` is +6.72 %, so D1 is faster than NONE at 2 KiB; D3 is -0.93 % and -8.25 %. They are not evidence of a timing cost or benefit of the guard. The "percent of core" columns are large because the cache pair is about 14 times the core's area (`docs/TRACKER.md`, flop arrays).

**How it is verified**

All 16 groups gave identical area and minimum period across their three repeats; the host parser validated all 48 `result.json` files (image ID, tool, PDK and constraint hashes).

**Known limits**

Synthesis and static timing only: no place and route and no power are documented. The flow is untuned and its cache variants reach only about 5 to 10 MHz (huge flop-array muxes, `docs/TRACKER.md`); core-only reaches 56.15 MHz. Results are labelled sky130 and are not comparable with the author's sg13cmos5l numbers (DEC-006). Identical repeats show determinism, not that the variation between variants is absent.
