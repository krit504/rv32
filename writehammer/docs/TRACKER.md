# TRACKER

What is planned (spec `../../docs/writehammer.md`, Section 6), what is done, what is not, who owns it, what is next.
`docs/STATUS.md` has the per-task evidence; this file is the planning view. Updated 2026-11-04 (IST), after tag `phase-T5-done` (`53f0280` on `main`).

## Done (on `main`, acceptance ran and passed)
| Phase | Tasks | Evidence |
|---|---|---|
| T0 setup | T0.1, T0.2, T0.4 to T0.6 | tag `phase-T0-done` |
| T1 core and benchmarks | T1.1 to T1.8 | tag `phase-T1-done` |
| T2 caches | T2.1 to T2.7 | tag `phase-T2-done` |
| T3 wear instrumentation | T3.1 to T3.5 | tag `phase-T3-done` |
| T4 attacks | T4.1 to T4.6, T4.8 | merged `86cffbb` |
| T5 detectors | T5.1 to T5.4, T5.6, T5.7, T5.8, T5.9 | tag `phase-T5-done`; `make test` green; full guard matrix 1107 rows, 0 mismatches |

## Partly done or not done
| ID | What is missing | Owner | Needed for | Crucial? | Next step |
|---|---|---|---|---|---|
| ~~CORE-ONLY TOP~~ **DONE 2026-11-04** | `rtl/core_only.sv` delivered and tested (KI-019 resolved). Spec T6.5 requires overhead "as a percentage of ... the core". | me | T6.5 | Yes | Add a `CORE_ONLY` branch to `rv32_top_pipelined` (external instruction/data ports instead of imem/dmem/caches; default unchanged, so testbenches keep their hierarchy) plus a thin `core_only.sv` wrapper. Regress lint, cache_integration, hazard, random, bypass of the default path. |
| T5.10 (rest) | Rate-matched PLACEBO two-pass runs and control rows in `results.csv` and the report. RTL side is done and tested. | other agent (T6.1/T6.2) | T6.1, T6.3 | Yes | They run each real detector, compute `stores_restricted/stores`, then PLACEBO with `WG_PLACEBO_RATE = round(65536 * fraction)` (see `docs/T5_INTERFACE.md`). |
| ~~METRIC CONTRACT~~ **DONE 2026-11-04** (`7efefa4`; formulas in `docs/T5_INTERFACE.md`) | Their `restricted_cycle_frac`, `fp_cycle_frac`, `fp_store_frac`, `detect_latency_cycles` columns. I provide the raw counters (`WG` line of `tb_prog`: restricted_cycles, first_restrict, stores, stores_restricted) and detector parameters; the fractions and latency come from the raw values plus PHASE markers (harness side). `tb_prog` already forwards `DETECTOR`, `WG_*`. | split | T6.1 | Yes | I document the exact formulas in `docs/T5_INTERFACE.md` (task below). |
| T5.5 | Action A2 (stall-throttle, K=16). `WG_ACTION=1` is an elaboration error (KI-020). | me, optional | extra arm only | No (spec: optional after A1) | Implement only if you want the arm; needs a stall hook in `hazard_unit` plus tests. |
| T4.7 | Fixed PMR rule fails 23 of 24 attacks (`crc32`, DEC-010, KI-017). | **you** (criterion is yours) | interpretation of attack validity | No for running; yes for the claims | Decide: keep as a finding (default) or amend the criterion with a CHANGE_LOG entry. |
| T0.3 | The quoted "5 of 5 mutants" cannot be rerun; replaced by a larger harness. | nobody | nothing | No | Leave documented. |
| KI-023 | G17 guard mutant caught by a Verilator build crash in the last run, by mismatch in the earlier one. | me | nothing | No | Rerun `tests/guard_mutants.py` alone (10 to 15 min) when convenient. |
| KI-018 | Stale docstring in `analysis/attack_runner.py`. | other agent / me | nothing | No | Fix when the file is next touched. |

## Phase T6 (other agent, branch `t6-eval`, MERGED into `main` 2026-11-05)
Results: matrix 9,723/9,723 correct; H1 REFUTED, H2 INCONCLUSIVE, H3 REFUTED (`docs/HYPOTHESES.md`). Cause checked by me on the raw data: store+load read-back attacks get the same array writes with bypass, because the bypassed store invalidates the line and the next load refills it (RLA: 285,718 store-hit writes with NONE; 0 store writes but 285,716 fills with ALWAYS).

| ID | Status | Blocked on |
|---|---|---|
| T6.1 matrix (9,723-run manifest) | Phase A done (6 smoke runs); full detector matrix pending | `phase-T5-done` (now available), placebo two-pass, calibration CSV (available) |
| T6.2 plots | built from development CSV; detector figures pending | T6.1 results |
| T6.3 hypotheses script | NOT RUN | T6.1 results |
| T6.4 sensitivity sweeps | NOT RUN | T6.1 results (window and threshold sweeps need the other windows' calibration, available) |
| T6.5 physical cost | plan, parser and author commands done; NOT RUN | `cache_system.sv` (delivered), **core-only top (not yet)**, and **you launching the flow** (Q-002: agents must not run the EDA container) |

## Phase T7 (documentation; mostly me, after T6 results)
T7.1 README, T7.2 REPORT, T7.3 rationale notes, T7.4 EXPLAIN_FOR_AUTHOR, T7.5 RESULTS (generated), T7.6 clean-clone `make all`, T7.7 claim audit, T7.8 integrity audit: all NOT RUN. Partial results are allowed, so I can draft the design parts (T7.3, parts of T7.1/T7.2/T7.4) now.

## Blocking decisions that are yours
1. Launch the T6.5 flow in the author's Docker image once the core-only top exists (Q-002).
2. T4.7: keep as a finding or amend (DEC-010).
3. Whether A2 is wanted.

## Next, in order
1. Me: write the metric formulas into `docs/T5_INTERFACE.md`; build the core-only top; regress; commit.
2. Other agent: merge `main`, run the full detector matrix with the placebo two-pass, then T6.3 and T6.4.
3. Me: merge `t6-eval` into `main` when they report (expected conflict only in `docs/LOCKED.sha256`: keep both sides).
4. You: run the T6.5 flow commands when the other agent hands them over.
5. Me: T7 documents; final `make all` and the audits.

## 2026-11-05 update: T6.5 physical flow DONE (author-authorized, other agent)
- 16 variants x 3 repeats in the pinned image (Yosys 0.66, OpenSTA 2.7.0, sky130_fd_sc_hd); `flow/cost_table.md`, `flow/area_fmax.png`, raw archive `flow/raw.tar.zst` (34 MB).
- Replayed onto `main` as commits `1ba2191`, `d11e094`, `cd308df`, `98ddb33` under the krit504 identity. The branch `t6-eval` also holds a merge commit `a065ae1` that used the default work identity; it was **not** imported (do not push `t6-eval`; delete the branch and worktree when done).
- Reading the table: the cache pair is about 14x the core's area (flop arrays), so deltas under about 2 % of the cache are inside synthesis variation (D2 M=4/8/16 come out *smaller* than NONE, which a design that only adds logic cannot be). Only D1 stands out above that (+4.0 % at 1 KiB, +5.7 % at 2 KiB of the cache; +57 % / +109 % of the core). Fmax is 5 to 10 MHz (untuned flow, huge flop-array muxes), and its deltas (-18 % to +6.7 %, D1 faster than NONE at 2 KiB) have no stable sign: report as measured, not as a guard-caused effect.

## 2026-11-05 update: T7 documents
README, REPORT, RESULTS (generated), EXPLAIN_FOR_AUTHOR, CLAIMS, INTEGRITY_REPORT, 14 rationale notes, `make results|synth|audit` done (T7.1 to T7.5, T7.7, T7.8 DONE). **T7.6 DONE 2026-11-07**: clean-clone `make all` reproduced all 9,723 rows and every artifact (`docs/logs/T7.6.md`). Remaining decisions for the author: push to a private GitHub repo (verify private first; Q-001), optional read-around follow-up, T4.7 stays a finding.
