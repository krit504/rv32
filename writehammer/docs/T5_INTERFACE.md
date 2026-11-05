# T5 INTERFACE (for the T6 evaluation)

Status: names and semantics final once tag `phase-T5-done` exists (a CHANGED note would appear here otherwise).

## Top-level parameters (`rv32_top_pipelined`)

| Parameter | Values | Meaning |
|---|---|---|
| `DETECTOR` | 0 NONE, 1 ALWAYS, 2 D1, 3 D2, 4 D3, 5 NEVER, 6 PLACEBO | write_guard arm. 1, 5, 6 are test controls. |
| `WG_ACTION` | 0 = A1 (bypass) | 1 = A2 is NOT RUN (elaboration error). |
| `WG_MODE` | 0 STATIC, 1 ADAPTIVE | D3 only. |
| `WG_WINDOW` | cycles, default 10000 | sweep 1000 / 10000 / 100000. |
| `WG_THRESHOLD` | count per window | from `analysis/calibration.csv` (column `threshold`; rows by detector D1/D2(M)/D3, `window_cycles`, `k`; primary k=2, window 10000: D1 740, D3 1534). Calibrated on Dhrystone + CoreMark only. |
| `WG_M` | 4..64, power of two, at most lines/2 | D2 counters. |
| `WG_W` | default 16 | counter width, saturating. |
| `WG_PLACEBO_RATE` | 0..65536 | PLACEBO restricted-store fraction x 65536; set from the real detector's measured `wg_stores_restricted / wg_stores` of the same workload (two-pass). |
| `WG_PLACEBO_SEED` | non-zero | PLACEBO PRNG seed (xorshift32). |
| `OBSERVE` | 1 default; 0 compiles all observation logic out (write_guard counters, cache counters, array-write/request trace, peek port) | for synthesis. |

Verilator: pass as `-G<name>=<value>`.

## Semantics (DEC-011)
- Window: counters are cleared every `WG_WINDOW` cycles. A counter above `WG_THRESHOLD` sets its hot flag at once; at a window end the flag is released if that window's count is below `WG_THRESHOLD/2`.
- D1: counts D$ data-array writes per line. D2: same, per bucket; bucket(idx) = top `log2(M)` bits of `(((idx[7:0]) ^ idx[15:8]) * 167) mod 256`. D3: counts completed stores (bypassed ones included); STATIC latches until reset, ADAPTIVE re-evaluates each window.
- A hot flag only changes while no store is mid-request in Memory (dcache needs a stable bypass); a window end in a frozen cycle is processed at the next free cycle.
- `bypass_store` restricts stores only; loads are never restricted.

## Metric outputs (top-level ports, valid at any time, cleared by reset)
| Port | Meaning |
|---|---|
| `wg_restricted` | any hot flag / control restriction set now |
| `wg_cycles_restricted` | cycles with `wg_restricted` = 1 |
| `wg_first_restrict` | cycle count at first restriction, 32'hFFFFFFFF if never (detection latency = this minus the attack start cycle, from the PHASE marker) |
| `wg_stores`, `wg_stores_restricted` | completed (non-MMIO) stores, and those bypassed |
| `dc_cnt_bypass`, `dc_cnt_rab` | existing D$ counters: bypassed stores, refills after bypass |
| `dc_aw_*` | existing array-write trace (wear) |

## Synthesis tops
- `rtl/cache_system.sv` is delivered: I$ + D$ + write_guard, line-granule memory-side ports, no memory model, same `WG_*`/`DETECTOR`/`OBSERVE` parameters (without the `WG_` prefix on ACTION etc., see the port list in the file). With `OBSERVE=0` every observation output is tied to 0 (synthesis prunes the logic). `rv32_top_pipelined` instantiates it, so the whole regression exercises it. `DETECTOR=0 OBSERVE=0` is the plain cache pair; compare detector variants against it for the guard's area and timing.
- **Core-only top: `rtl/core_only.sv`** (module `core_only`, parameter `RESET_PC`). It is `rv32_top_pipelined` with `CORE_ONLY=1` (same pipeline source, no caches, guard, memory model or observation; every observation output is left unconnected). Ports: `clk, rst_n`; fetch `i_addr` out, `i_rdata`, `i_stall` in; Memory-stage data `d_addr, d_wdata, d_be, d_we, d_re` out, `d_rdata`, `d_stall` in. The responses must be stable while the stage is stalled; `i_stall`/`d_stall` freeze fetch / the pipeline like a cache miss. MMIO stores (0xF000_0xxx) never appear on `d_*` (simulation-only window). Verified by `tests/core_only_test.py` (run with `--n 100` at delivery, default 200): 100 random programs with random stalls match the reference model, the wrapper matches the top, and a control that ignores `d_stall` fails (60/60).

## How the results rows are produced
`tests/guard_integration.py` writes `work/guard_integration/results*.csv` with columns image, arm, latency, cycles, restricted_cycles, first_restrict, stores, stores_restricted, dc_bypass, dc_rab, dc_write: the T5.9 metric hooks as the evaluation will read them. Detection latency = `first_restrict` minus the cycle of the PHASE marker that starts the attack (both from the same run).
PLACEBO needs two passes per workload: run the real detector, compute `stores_restricted/stores`, then run PLACEBO with `WG_PLACEBO_RATE = round(65536 * that fraction)` (T6 harness; the RTL side is verified: `tests/write_guard_test.py` placebo_rate*).

## Per-phase snapshots and the evaluation metrics (T5.9)
`tb_prog` prints, at every PHASE marker write (MMIO +0xC) and at HALT:
```
WGPHASE id=<marker value> cycle=<n> restricted_cycles=<c> stores=<s> stores_restricted=<r> restricted_now=<0|1> first_restrict_prev_phase=<cycle|4294967295>
WGEND   cycle=<n> restricted_cycles=<c> stores=<s> stores_restricted=<r> restricted_now=<0|1> first_restrict_prev_phase=<cycle|4294967295>
```
`cycle` counts from reset release (same clock for every field; it can differ by a few cycles from the `PHASE ... cycle=` line of `sys_monitor`, so use the `WGPHASE` cycle for everything below). A snapshot describes the interval since the previous snapshot (the first one, since reset). `first_restrict_prev_phase` is the first cycle in that interval with `restricted=1`. Counters are cumulative since reset. Taking consecutive differences gives per-phase values; benign and attack phases are the workload's own marker intervals (mixed: benign, attack, benign).

| CSV column | Definition |
|---|---|
| `restricted_cycle_frac` | `WGEND.restricted_cycles / WGEND.cycle` (whole run) |
| `fp_cycle_frac` | restricted cycles in benign intervals / cycles in benign intervals (a pure benign workload: the whole run; every restriction there is a false positive) |
| `fp_store_frac` | restricted stores in benign intervals / completed stores in benign intervals |
| `detect_latency_cycles` | for an attack interval that starts at snapshot k-1 and ends at snapshot k: `first_restrict_prev_phase(k) - cycle(k-1)`; empty if it is 4294967295 (not detected in that phase); 0 and flagged "carry-over" if `restricted_now` was already 1 at snapshot k-1 |
| `bypassed_stores` | `WGEND.stores_restricted` (equals `dc_bypass` of the D$ counters) |

Example (mixed RLA, D1, window 10000, threshold 740): benign phase 0 restricted_cycles 0; attack phase restriction first at cycle 1008588, 5230 cycles after the marker at 1003358; restriction ended about 2,200 cycles into the last benign phase (release after the attack, a measured false-positive tail).
