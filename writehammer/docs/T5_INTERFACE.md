# T5 INTERFACE (for the T6 evaluation)

Status: **PROVISIONAL** until tag `phase-T5-done`. Parameter names below are final unless a later section says CHANGED.
Items marked TODO are not yet delivered.

## Top-level parameters (`rv32_top_pipelined`)

| Parameter | Values | Meaning |
|---|---|---|
| `DETECTOR` | 0 NONE, 1 ALWAYS, 2 D1, 3 D2, 4 D3, 5 NEVER, 6 PLACEBO | write_guard arm. 1, 5, 6 are test controls. |
| `WG_ACTION` | 0 = A1 (bypass) | 1 = A2 is NOT RUN (elaboration error). |
| `WG_MODE` | 0 STATIC, 1 ADAPTIVE | D3 only. |
| `WG_WINDOW` | cycles, default 10000 | sweep 1000 / 10000 / 100000. |
| `WG_THRESHOLD` | count per window | from `analysis/calibration.csv` (TODO, T5.6). |
| `WG_M` | 4..64, power of two, at most lines/2 | D2 counters. |
| `WG_W` | default 16 | counter width, saturating. |
| `WG_PLACEBO_RATE` | 0..65536 | PLACEBO restricted-store fraction x 65536; set from the real detector's measured `wg_stores_restricted / wg_stores` of the same workload (two-pass). |
| `WG_PLACEBO_SEED` | non-zero | PLACEBO PRNG seed (xorshift32). |
| `OBSERVE` | 1 default, 0 compiles the write_guard counters out | for synthesis (TODO: the cache/trace observation outputs are not yet gated, T5 synthesis tops). |

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

## Delivered later (TODO)
- `analysis/calibration.csv` (T5.6), final default thresholds.
- `rtl/cache_system.sv` and a core-only top for synthesis with observation compiled out.
