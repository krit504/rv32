# CRITERIA (locked)

Verbatim extract of `docs/writehammer.md` (sha256 `2b8b09103f9c42f6a5dc0e137d6d81f48c701f3295b34ef04de048d8b17eb179`), made by `scripts/make_criteria.py` at T0.6. Locked by `docs/LOCKED.sha256`; any change needs a `docs/CHANGE_LOG.md` entry (spec 0A.A).

---

## 1. Goal

Build a parameterized I$ and D$ for the existing 5-stage RV32I core. Treat the D$ data array as a **modeled non-volatile-memory (NVM) array** whose lifetime is set by writes to its most-written line. Measure how benign benchmarks and write-hammer-style programs concentrate writes. Implement and compare three small hardware detectors that find hammering and mitigate it, and report detection latency, false positives, wear reduction, IPC cost, area and Fmax.

**Question answered:** which cheap hardware detector catches randomized write-hammer patterns, at what cost, and which one fails?

**Pre-registered hypotheses and criteria** (state each as CONFIRMED, REFUTED or INCONCLUSIVE using exactly these criteria; do not adjust them after seeing results):

| ID | Hypothesis | CONFIRMED if (at calibrated `k=2`, primary cache config) |
|---|---|---|
| H1 | Per-line counters (D1) stop fixed-location attacks but are evaded by randomized ones | D1 reduces PMR by at least 50% on RLA and RTA, and by less than 50% on both RnLA and RnTA |
| H2 | Hashed counters (D2) keep most of D1's benefit at far less state | with `M <= N_lines/8`, D2 achieves at least 80% of D1's PMR reduction on every attack where D1 achieves at least 50%, and D2 counter flops are at most 25% of D1's |
| H3 | A global store-rate detector (D3) catches every attack but falsely flags benign store-heavy code | D3 reduces PMR by at least 50% on all four attacks, and its false-positive cycle fraction is at least 5% on at least one held-out benign workload |

REFUTED if the stated condition is clearly false in the data; INCONCLUSIVE if results are mixed across the threshold and window sweeps. Report the numbers behind every verdict.

---

## 3. Defaults for every open choice (use these; log any deviation)

| Item | Default |
|---|---|
| Primary cache config | D$ 2 KB, I$ 2 KB, 16-byte lines (128 lines), direct-mapped |
| Cache-size sweep | 1, 2, 4, 8 KB (16-byte lines) |
| Line-size sweep | 16, 32, 64 bytes at 2 KB (for miss-rate only) |
| Backing memory (simulation only) | 256 KB, latency 20 cycles (also test 1, 5, random) |
| Assumed endurance `E` | 1e15 writes (the draft cites up to 10^15; this is illustrative, label it so) |
| Assumed `f_clk` for `T_fail` | 100 MHz (assumption; also report 50 and 500 MHz) |
| `DC_WRITE_LATENCY` | 1 (SRAM-like); optional sweep 1, 4, 10 |
| Window length | 10,000 cycles (sweep 1,000 / 10,000 / 100,000) |
| Counter width `W` | 16-bit saturating |
| Threshold | calibrated: `THRESHOLD = k x (max per-window benign count on the calibration set)`, `k` in {1.5, 2, 4}, primary `k=2` |
| Calibration set | Dhrystone, CoreMark |
| Held-out false-positive set | Embench-IoT subset (at least 4 kernels), `memcpy`, `memset`, a store-heavy loop |
| D2 counter counts `M` | 4, 8, 16, 32, 64 (powers of two, never above `N_lines/2`) |
| Hysteresis | release when the counter falls below `THRESHOLD/2` |
| Attack run lengths | 2M cycles per attack; mixed workloads: 1M benign, 1M attack, 1M benign |
| Seeds | 5 seeds per randomized attack (seeds 1 to 5); report mean and range |
| Physical flow | Yosys plus OpenSTA on sky130 (`sky130_fd_sc_hd`), via OpenLane if installed; same constraints for every variant |
| Cost-study cache size | D$ 1 KB and 2 KB (flop-based arrays, so keep small) |
| Benchmark build | `rv32i`, `-O2`, bare metal, mul/div via libgcc software routines (label results rv32i, not rv32im) |

---

## 4. Definitions (use exactly)

- **Data-array write event (D$):** a store hit, a line fill, or a partial-word merge that writes the D$ data array. Array reads, including dirty-eviction reads, are not writes. **Metadata** (tag, valid, dirty bits) writes are not counted as data-array writes; state this in the report.
- **`w[i]`:** data-array write events to line `i` in a run.
- **PMR:** `max_i w[i] / mean_i w[i]` over all lines. Also report over written lines only.
- **`T_fail`:** `E / (w_max / t_run)` with `t_run = cycles / f_clk`. An extrapolation from a short run; label it so.
- **Restricted (bypassed) store:** a store that a detector sends to memory instead of the D$ data array. Correct handling: if the line is present, write back dirty data first (array read, not write), invalidate the line, then write the store to memory; if absent, write memory only. A later load to that address misses and refills (a fill is an array write). Measure this refill cost.
- **False-positive fractions (benign runs):** fraction of cycles, and fraction of stores, spent in a restricted state.
- **Detection latency:** cycles from the start of an attack phase (phase marker) to the first restriction.
- **Correctness invariant:** identical final registers and memory (compared by a signature hash) across every detector, action, cache configuration and memory latency.

**Actions.** A1 bypass (default, correct by construction). A2 stall-throttle (optional): restricted stores proceed at most once per `K` cycles by stalling the pipeline, with `K` default 16.

---

## Attack-validation rule

- **T4.7** Attack validation: each attack must show higher PMR than every benign workload; randomized attacks must show a visibly wandering location pattern in the windowed heatmap. *Accept:* a table of PMR per workload and heatmaps in `analysis/`. If an attack does **not** concentrate writes, fix the attack program before any detector work and log the change.

## Mutant and mutation-check definitions

- **T1.2** Update the Python encoder and reference model for the six instructions. Add directed tests: each instruction at every legal byte or halfword offset, sign extension, adjacent sub-word stores to one word, forwarding of a loaded sub-word value, load-use stall with sub-word loads. Add a mutant for each of: wrong sign extension, wrong byte lane, byte enable stuck. *Accept:* all new tests pass; each new mutant is caught.

- **T1.6** Random lockstep generator: hazard-dense random programs (RAW at gaps 1 to 3, load-use, taken and not-taken branches, `jal`, `jalr`, sub-word ops); compare final registers and memory against the reference model (Spike if available). At least 1,000 programs per run, seeds logged. *Accept:* 0 mismatches; a seeded known bug (a mutant) is caught.

- **T3.5** Independent golden-cache replay check (Section 0A.D): the RTL logs every D$ access (cycle, type, address, size); a separately written Python cache model replays the trace and computes per-line data-array write counts, hits, misses and write-backs. *Accept:* exact match with the `wear_monitor` and the RTL counters on every benign and attack workload, and a deliberately mis-counting monitor mutant is caught.

- **T5.7** Unit tests per arm on synthetic store streams: detects above threshold, does not detect below, hysteresis release, static latch holds, saturation behavior. Mutation tests per arm: disable threshold compare, break window reset, stuck restricted, stuck released, inverted bypass polarity, wrong hash index. *Accept:* each mutant fails at least one test.

- **T5.10** Negative controls and bypass verification (Section 0A.D): implement test-only detectors `NEVER`, `ALWAYS` and a rate-matched `PLACEBO`; verify `NEVER` equals `NONE` in every metric; verify a restricted store causes zero data-array writes and that memory receives the correct data (checked against a golden memory model); add an invariant-breaking mutant (a bypass that drops a store). *Accept:* all of these hold and the control rows appear in `results.csv` and the report. If a real detector does not beat its placebo, that is reported as a finding.
