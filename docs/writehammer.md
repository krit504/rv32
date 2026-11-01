# RTL Study: Detecting Write-Hammer Patterns in a Modeled-NVM Data Cache (v4, full task list with integrity and documentation rules)

**Audience:** an AI coding agent that will execute this project end to end in one run, working from the existing RV32I repository. The author (Kritin) owns the result and must be able to explain every module and number afterward. This version replaces v1, v2 and v3. Every task is listed in Section 6 with an ID, a deliverable and an acceptance check.

---

## 0. Autonomy contract (read first)

1. **Run to completion without asking questions mid-run.** Where this spec leaves a choice open, pick the default in Section 3, log it in `DECISIONS.md`, and continue. Put anything you would have asked into `OPEN_QUESTIONS.md`.
2. **Gates.** After each task, run its acceptance check, record pass/fail in `STATUS.md`, and `git commit` with the task ID in the message. Do not start a task whose dependencies failed. If a task still fails after 3 distinct fix attempts, mark it `BLOCKED` with the evidence, then continue with every task that does not depend on it.
3. **Resume protocol.** Keep `STATUS.md` current at all times (task ID, status `DONE` / `PARTIAL` / `BLOCKED` / `NOT RUN`, last command, last result). If the session ends, a new session must resume from `STATUS.md` without redoing finished tasks.
4. **No fabricated results.** Every number, table and plot must come from a script or `make` target that regenerates it from a clean checkout. Anything not run is reported as `NOT RUN`. Never edit a results CSV by hand.
5. **Mitigations must preserve architectural correctness.** For any program, final registers and memory must be identical with every detector and action on or off, with caches on or off, and under any memory latency. Never drop or reorder a store's architectural effect.
6. **Private repository only.** Do not push to any public remote. The author has not yet cleared publishing this work with the advisor.
7. **Credit prior work.** The attack taxonomy (RLA, RTA, RnLA, RnTA) comes from the author's research group (TENDRA and the Write Hammer draft). Cite it as prior work in the README, report and explanation document. Do not present it as new here.
8. **Explainability.** Each new module gets a rationale note (what it does, why it is built that way, what was considered and rejected). The author must be able to defend it in an SOP, with a recommender or in an interview.
9. **Conventions:** SystemVerilog; Verilator lint clean (0 errors, 0 width warnings); Icarus Verilog or Verilator for simulation (Verilator for long runs); the Python reference model in the style of the existing `encode.py`; directed tests plus mutation testing. Extend the existing core; do not rewrite it. Pipeline-register changes beyond stall enables go into `OPEN_QUESTIONS.md`, with the change made only if required for correctness.

---

## 0A. Integrity rules: no shortcuts, no loopholes

**Principle:** the goal is a true, defensible measurement, not green checkmarks. If a check can pass for the wrong reason, treat that as a failure to fix, not a success to report.

### A. Protected artifacts (lock them early)
Protected: everything under `tests/` (including expected values, golden signatures and the reference model), every acceptance check in Section 6, the hypotheses and criteria in Section 1, the defaults in Section 3, the definitions in Section 4, the calibration and held-out workload lists, the attack-validation rule in T4.7, the mutant lists, and the results schema in Section 7.

- T0.6 hashes these into `docs/LOCKED.sha256`. `scripts/check_locks.sh` must fail if a locked file changes without a matching entry in `docs/CHANGE_LOG.md` (what changed, why, evidence the original was wrong).
- **Adding** tests, checks and mutants is always allowed. **Removing or loosening** them is never allowed, and a change is never justified by "it made a failing result pass".
- Test counts, mutant counts and included arch-test counts must never decrease from the T0.3 / T1.5 baseline.

### B. Forbidden shortcuts (each is a violation, even if the run "passes")
1. Deleting, skipping, commenting out, marking expected-fail, or loosening any test, assertion, lint rule, timeout, tolerance or mutant.
2. Editing expected values, golden outputs or signatures to match what the RTL produced. Expected values come only from the independent reference model or the specification.
3. Hard-coding results, or special-casing a workload, benchmark, seed, address or cycle count in RTL, scripts or testbenches. No logic that detects "am I under test".
4. Tuning thresholds, windows or attack parameters using held-out workloads or after seeing evaluation results, or changing the hypothesis criteria.
5. Weakening attacks so detectors look good, or strengthening them artificially so the baseline looks bad. The T4.7 validation rule is fixed.
6. Counting writes differently across configurations. The data-array write definition (Section 4) is identical everywhere, and refills caused by bypassed stores are always counted.
7. A "bypass" that still writes the data array, a restriction that does not change behavior, or any mitigation that drops, delays beyond its definition, or reorders a store's architectural effect.
8. Reporting selected seeds, runs or workloads. Every planned run appears in the CSV, or in `docs/EXCLUDED_RUNS.md` with a reason. Randomized results are reported as mean and range over all seeds.
9. Shortening runs, shrinking workloads or lowering iteration counts to dodge timeouts without logging and disclosing it in the report.
10. Suppressing warnings or adding lint waivers without a logged root cause. Blanket waivers are forbidden; each waiver is listed in `docs/KNOWN_ISSUES.md`.
11. Making mutants trivial, inapplicable or equivalent. A script must show each mutant changes behavior and is caught; any mutant claimed equivalent is argued individually in the task log.
12. Replacing real tools with mocks, stubs or estimates for simulation, synthesis or timing results. If a tool is missing, the result is `NOT RUN`.
13. Claiming a check passed that did not run, writing `STATUS.md` optimistically, or reporting `PARTIAL` as `DONE`.
14. Validating code only with code written from the same understanding. Where Section 0A.D requires an independent check, it must be built independently.
15. Quoting literature numbers or figures from memory. Cite only what was actually read, or omit.
16. Silently changing definitions (Section 4) or parameters (Section 3). Any change goes into `DECISIONS.md` and `docs/CHANGE_LOG.md` with the reason, and **all affected runs are redone**.

### C. Problem-handling protocol (how to fix, not how to dodge)
When anything fails:
1. Record the symptom with the exact command and output in the task log.
2. List hypotheses.
3. Reduce to a minimal reproducer.
4. Find the root cause with evidence (waveform excerpt, log line, assertion).
5. Fix the cause.
6. Add a regression test that fails before the fix and passes after.
7. Rerun everything the fix could affect.
8. Record all of it in `docs/LAB_NOTEBOOK.md`.

A change that makes the symptom disappear without a demonstrated root cause is not a fix. After three distinct attempts without a root cause, mark the task `BLOCKED` and attach the evidence. Do not work around it.

### D. Independent cross-checks (no self-grading)
- ISA behavior is checked against the reference model or Spike, never against the RTL's own output.
- **Golden cache replay (T3.5):** a separately written Python cache model replays the RTL's logged D$ access trace and must reproduce per-line data-array write counts, hits, misses and write-backs exactly.
- **Bypass verification (T5.10):** a restricted store produces zero data-array writes and its data reaches memory, checked against a golden memory model.
- **Negative controls (T5.10):**
  - `NEVER` (never restricts) must match `NONE` in every metric.
  - `ALWAYS` (restricts every store) gives the upper bound on wear reduction and its IPC and refill cost.
  - `PLACEBO` (rate-matched random restriction: restricts a seeded pseudo-random fraction of stores equal to the real detector's measured restricted-store fraction on that run) shows what non-specific bypass achieves. Each real detector must be compared with `PLACEBO` and `ALWAYS` in the report. If a detector does not beat its placebo, say so.
  - An invariant-breaking mutant (a bypass that drops a store) must be caught by the T5.8 check.
- Differences smaller than the seed-to-seed range are not claimed as differences.

### E. Adversarial self-review (T7.8)
At the end, re-read the work as a skeptical reviewer. For every headline claim ask "how could this be true for the wrong reason?", run a targeted check, and record the question, the check and the outcome in `docs/INTEGRITY_REPORT.md`. List known weaknesses openly.

---

## 0B. Documentation rules (document everything, as it happens)

1. **Command log.** Every command that produces a result runs through `scripts/run.sh`, which appends to `logs/runs/<run_id>.log`: timestamp, command, git commit, tool versions, parameters, seed, exit code, stdout/stderr tail, and hashes of output files.
2. **Per-task log** `docs/logs/T<ID>.md` for every task: goal, what was done, files changed, commands run, results (numbers with file paths), problems met (symptom, root cause, fix, regression test), deviations from this spec, open items. Written when the task finishes, not at the end of the project.
3. **Lab notebook** `docs/LAB_NOTEBOOK.md`: append-only, timestamped narrative of decisions, surprises, dead ends and failed attempts. Never rewrite earlier entries.
4. **`docs/DECISIONS.md`:** each choice with the alternatives, the reason, the impact and the date.
5. **`docs/CHANGE_LOG.md`:** every change to a protected artifact.
6. **`docs/TRACEABILITY.md`:** a table mapping each task to its RTL files, tests, result rows, figures and the document sections that cite them.
7. **Code documentation.** Every RTL module has a header comment (purpose, parameters, ports, assumptions, known limitations). Every script has a docstring (inputs, outputs, usage). Every testbench states what it checks and what it does **not** check.
8. **Result provenance.** Each figure or table has a sidecar `.json` naming the generating script, git commit and CSV hash. File names include the run-set id.
9. **`docs/EXCLUDED_RUNS.md`:** planned vs. completed run counts, and each missing run with its reason.
10. **`docs/KNOWN_ISSUES.md`:** every known bug, limitation, lint waiver and unverified area.
11. **Honest status words.** `DONE` only if the acceptance check ran and passed in this run. `PARTIAL` if some sub-criteria are unmet (list which). `BLOCKED` or `NOT RUN` otherwise.
12. **Commit hygiene.** One commit per task, message `T<ID>: summary`. No history rewriting. Tag each finished phase (`phase-T1-done`, and so on).

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

## 2. What this is not (state these limits in every document)

- Not a claim that SRAM L1 caches are endurance-limited. This is a modeled-NVM study.
- Not a reproduction of the multicore threat model. One core cannot distinguish an attacker core from a benign one. Detectors operate on the store stream and cache-array writes of a single core.
- Not a replication of the group's per-core drop-at-admission throttle. That mechanism is valid only when a core is known to be malicious. Dropping stores on a benign core would corrupt results, so it is not implemented. Action A2 (stall-throttle) is the correctness-preserving analogue.
- Not a breakthrough. Its value is rigorous measurement and honest framing.

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

## 5. Environment and repository

Repository layout:

```
rtl/        core, caches, write_guard (D1, D2, D3)
tb/         testbenches, mem_model, wear_monitor
sw/         crt0, linker script, benchmarks, attack programs, libs
tests/      arch-test glue, random generator, reference model, mutants
analysis/   calibration, plotting, hypothesis scripts, CSV outputs
flow/       synthesis / OpenLane configs and run scripts
scripts/    run.sh (command logger), check_locks.sh
logs/       runs/ (one log per run)
docs/       README, REPORT, RESULTS, EXPLAIN_FOR_AUTHOR, INTEGRITY_REPORT, HYPOTHESES, CRITERIA, LOCKED.sha256,
            LAB_NOTEBOOK, DECISIONS, CHANGE_LOG, KNOWN_ISSUES, EXCLUDED_RUNS, TRACEABILITY, OPEN_QUESTIONS,
            STATUS, TOOLS, baseline, logs/ (per-task), rationale/
```

`make` targets: `lint`, `test`, `arch-test`, `random`, `bench`, `caches`, `wear`, `attacks`, `calibrate`, `eval`, `synth`, `plots`, `hypotheses`, `locks`, `audit`, `all`, `clean`.

---

## 6. Task list

Dependencies are noted as `needs:`. Do tasks in ID order unless a dependency says otherwise.

### Phase T0: Setup
- **T0.1** Create the repository layout, `.gitignore`, `STATUS.md`, `DECISIONS.md`, `OPEN_QUESTIONS.md`. No public remote. *Accept:* files exist; first commit made.
- **T0.2** Check or install tools: Verilator, Icarus Verilog, Yosys, OpenSTA (or OpenROAD), RISC-V GCC (`riscv32-unknown-elf` or `riscv64-unknown-elf` with `-march=rv32i -mabi=ilp32`), Spike (optional, for lockstep), Python 3 with numpy, pandas, matplotlib. Record versions in `docs/TOOLS.md`. If a tool cannot be installed, log it, apply the fallback (for example the Python reference model instead of Spike), and mark dependent tasks `PARTIAL`. *Accept:* `docs/TOOLS.md` lists every tool and version or `MISSING`.
- **T0.3** Import the existing core and tests. Get `make lint` and `make test` green. *Accept:* previously reported results reproduce (21/21 integration, 16 directed hazard cases in 18 runs, 5 of 5 mutants caught).
- **T0.4** Create the Makefile with every target stubbed and wired. *Accept:* `make -n all` runs.
- **T0.5** Logging infrastructure: `scripts/run.sh` (rule 0B.1), the `logs/` tree, and templates for the per-task log, lab notebook, `DECISIONS.md`, `CHANGE_LOG.md`, `KNOWN_ISSUES.md` and `EXCLUDED_RUNS.md`. *Accept:* running a sample command produces a complete log record; all templates exist.
- **T0.6** Lock-in: write `docs/CRITERIA.md` (verbatim copy of Section 1 hypotheses and criteria, Section 3 defaults, Section 4 definitions, the calibration and held-out lists, the T4.7 rule and the mutant lists), create `docs/LOCKED.sha256` covering it plus `tests/` golden data, and write `scripts/check_locks.sh` (run by `make test`). *Accept:* the check passes on a clean tree and **fails** after a deliberate edit to a locked file made without a `CHANGE_LOG.md` entry.

### Phase T1: Core completion and benchmarks (needs T0)
- **T1.1** Sub-word loads and stores (`lb`, `lbu`, `lh`, `lhu`, `sb`, `sh`): decoder changes by `funct3`, byte-enable stores, load extender with sign/zero extension. Keep the word path unchanged. *Accept:* lint clean; existing tests still pass.
- **T1.2** Update the Python encoder and reference model for the six instructions. Add directed tests: each instruction at every legal byte or halfword offset, sign extension, adjacent sub-word stores to one word, forwarding of a loaded sub-word value, load-use stall with sub-word loads. Add a mutant for each of: wrong sign extension, wrong byte lane, byte enable stuck. *Accept:* all new tests pass; each new mutant is caught.
- **T1.3** Performance counters: cycles, instructions retired, stall cycles by cause (load-use, branch/jump flush), exposed by MMIO start/stop/halt writes and printed as one CSV line at halt. *Accept:* counters match hand-computed values on a tiny program with known stall counts.
- **T1.4** Software toolchain flow: `crt0.S` (set `sp`, zero `.bss`, call `main`, write the exit code to the halt MMIO), linker script (text, data, bss, stack in 256 KB), a script that builds an ELF into a `$readmemh` hex. *Accept:* a C program that writes a checksum to the halt MMIO runs and the testbench reads it correctly.
- **T1.5** `riscv-arch-test` target for the supported RV32I subset (signature dump and compare; exclude `fence`, `ecall`, `ebreak`, misalignment, CSR tests), with a documented list of included and excluded tests. *Accept:* every included test passes; the pass list is in `docs/`.
- **T1.6** Random lockstep generator: hazard-dense random programs (RAW at gaps 1 to 3, load-use, taken and not-taken branches, `jal`, `jalr`, sub-word ops); compare final registers and memory against the reference model (Spike if available). At least 1,000 programs per run, seeds logged. *Accept:* 0 mismatches; a seeded known bug (a mutant) is caught.
- **T1.7** Dhrystone and CoreMark bare-metal builds that self-check their results. Run in Verilator. Record cycles, instructions, CPI, stall breakdown, and unofficial Dhrystone/MHz and CoreMark/MHz with iteration counts. *Accept:* self-checks pass; numbers are in `docs/baseline.md` with exact commands.
- **T1.8** Benign workload set for evaluation: at least 4 Embench-IoT kernels that build for rv32i bare metal (log which and why any are skipped), `memcpy` and `memset` with buffers larger than the cache, and a store-heavy loop. Each self-checks. *Accept:* all run correctly and appear in the baseline table.

### Phase T2: Memory system and caches (needs T1)
- **T2.1** `mem_model` (simulation only): configurable latency, ready/valid interface, loaded from the hex, a simple arbiter with D$ priority. *Accept:* unit test for latency and ordering.
- **T2.2** Stall-enable on every pipeline register (`pc`, `f_d_reg`, `d_e_reg`, `e_m_reg`, `m_w_reg`), integrated with the hazard unit; document interaction with load-use stall and flush. *Accept:* a **random stall-injection test** (stalls inserted at random cycles) leaves every architectural result unchanged on the T1 test suite.
- **T2.3** I$: direct-mapped, read-only, parameterized size and line size, line-fill FSM. *Accept:* directed tests (hit, miss, conflict, sequential fetch across lines).
- **T2.4** D$: direct-mapped, write-back plus write-allocate, dirty bits, byte-enable stores, fill and dirty-eviction FSM, and the restricted-store path from Section 4 (write back if dirty, invalidate, write through). *Accept:* directed tests (hit, miss, eviction, dirty write-back, byte stores, conflict, restricted-store with line present clean, present dirty and absent).
- **T2.5** Document that code and data regions are disjoint and that self-modifying code and `fence.i` are unsupported. *Accept:* the note is in `docs/`; linker script enforces the separation.
- **T2.6** Cache verification: a random memory-operation test against a golden memory model; then the whole T1 suite (arch-test, random lockstep, benchmarks) with caches on and off and with memory latency 1, 5, 20 and random. *Accept:* identical signature hashes everywhere (correctness invariant).
- **T2.7** Counters for I$/D$ accesses, hits, misses, fills, dirty write-backs, and miss-stall cycles, merged into the stall breakdown. Cache-size sweep and line-size sweep for miss rate. *Accept:* miss rate vs. size plot per benchmark, regenerated by `make caches`.

### Phase T3: Wear instrumentation (needs T2)
- **T3.1** Testbench `wear_monitor`: hooks the D$ data-array write strobes (store hit, fill, partial merge); per-line counters; windowed counts written to CSV (`window, line, count`); phase markers read from MMIO. *Accept:* compiles and logs in a smoke run.
- **T3.2** Statistics script: PMR (all lines and written lines), `w_max`, mean, `T_fail` at 50, 100, 500 MHz; per-line plot and time-windowed heatmap (line vs. window). *Accept:* produces the files for one run.
- **T3.3** Instrument check: micro-programs with known store and fill counts must give exactly the expected per-line counts. *Accept:* all known-answer tests pass.
- **T3.4** Baseline wear for every benign workload (caches on, no detector). *Accept:* heatmap and summary row per workload from `make wear`.
- **T3.5** Independent golden-cache replay check (Section 0A.D): the RTL logs every D$ access (cycle, type, address, size); a separately written Python cache model replays the trace and computes per-line data-array write counts, hits, misses and write-backs. *Accept:* exact match with the `wear_monitor` and the RTL counters on every benign and attack workload, and a deliberately mis-counting monitor mutant is caught.

### Phase T4: Attack programs (needs T3)
- **T4.1** Deterministic LFSR library (seed as a parameter). *Accept:* known-answer test.
- **T4.2** RLA, **T4.3** RTA, **T4.4** RnLA, **T4.5** RnTA, each in a **direct** form (stores confined to chosen lines using cache-geometry macros) and a **paper** form (arrays larger than the cache, so fills and write-backs occur). Parameters: number of locations, dwell-time range, run length, seed. *Accept:* each program runs correctly and terminates.
- **T4.6** Mixed workloads: benign phase, attack phase, benign phase, with MMIO phase markers. *Accept:* markers appear in the log at the right cycles.
- **T4.7** Attack validation: each attack must show higher PMR than every benign workload; randomized attacks must show a visibly wandering location pattern in the windowed heatmap. *Accept:* a table of PMR per workload and heatmaps in `analysis/`. If an attack does **not** concentrate writes, fix the attack program before any detector work and log the change.
- **T4.8** Baseline `T_fail` for each attack and benign workload. *Accept:* table generated.

### Phase T5: Detectors (needs T4)
- **T5.1** `write_guard` interface and window logic: inputs `clk`, `rst`, `store_valid`, `array_write_valid`, `line_idx`, cycle strobe; outputs `bypass_store`, `stall_req`, `restricted`; parameters `DETECTOR` (NONE, D1, D2, D3; plus test-only controls NEVER, ALWAYS, PLACEBO from T5.10), `ACTION` (A1, A2), `MODE` (STATIC, ADAPTIVE), `WINDOW_CYCLES`, `THRESHOLD`, `M`, `W`. *Accept:* `DETECTOR=NONE` is bit-identical in behavior to no guard.
- **T5.2 D1 line counters:** one saturating `W`-bit counter per D$ line, incremented on each array write; counters halved or cleared each window; a line is hot above `THRESHOLD`; stores to a hot line are restricted until its counter falls below `THRESHOLD/2`.
- **T5.3 D2 hashed counters:** `M` counters indexed by a defined hash of `line_idx` (XOR-fold of the index bits followed by a fixed odd-constant multiply and bit-select; document it); same threshold logic; aliasing is intentional and measured.
- **T5.4 D3 store-rate:** one counter of store events per window; above `THRESHOLD` the whole store stream is restricted; `STATIC` latches the restriction, `ADAPTIVE` re-evaluates each window with hysteresis.
- **T5.5** Action A1 integrated with the D$ restricted-store path. Action A2 (stall-throttle with `K=16`) after A1 passes. *Accept:* correctness invariant holds for A1; A2 marked `NOT RUN` if time ran out.
- **T5.6** Threshold calibration: `analysis/calibrate` computes, on the calibration set only, the per-window maximum counts for each detector (per-line max for D1, per-bucket max for D2, total stores for D3) and writes `THRESHOLD = k x max` for `k` in {1.5, 2, 4}. The held-out set must never be used for calibration. *Accept:* calibration table committed; script refuses to read held-out results.
- **T5.7** Unit tests per arm on synthetic store streams: detects above threshold, does not detect below, hysteresis release, static latch holds, saturation behavior. Mutation tests per arm: disable threshold compare, break window reset, stuck restricted, stuck released, inverted bypass polarity, wrong hash index. *Accept:* each mutant fails at least one test.
- **T5.8** Integration: correctness invariant (signature equality) for every arm, action, benchmark, attack and mixed workload, under memory latency 1, 20 and random. *Accept:* zero mismatches.
- **T5.9** Metric hooks: detection latency (from phase markers), restricted-cycle fraction, bypassed-store count, refill count after bypass. *Accept:* values appear in the run CSV.
- **T5.10** Negative controls and bypass verification (Section 0A.D): implement test-only detectors `NEVER`, `ALWAYS` and a rate-matched `PLACEBO`; verify `NEVER` equals `NONE` in every metric; verify a restricted store causes zero data-array writes and that memory receives the correct data (checked against a golden memory model); add an invariant-breaking mutant (a bypass that drops a store). *Accept:* all of these hold and the control rows appear in `results.csv` and the report. If a real detector does not beat its placebo, that is reported as a finding.

### Phase T6: Evaluation and cost (needs T5)
- **T6.1** Run the matrix in Section 7 in parallel, writing one row per run to `analysis/results.csv` with the schema in Section 7. *Accept:* every planned run has a row or a logged reason.
- **T6.2** Generate all figures and tables listed in Section 8 from the CSV only. *Accept:* `make plots` regenerates them from scratch.
- **T6.3** Hypothesis script: compute H1 to H3 with the pre-registered criteria in Section 1 and write `docs/HYPOTHESES.md` with CONFIRMED / REFUTED / INCONCLUSIVE and the numbers. *Accept:* file generated by the script, not written by hand.
- **T6.4** Sensitivity: window and threshold sweeps; plot false-positive fraction vs. detection latency per detector and attack (an ROC-like curve). *Accept:* plot generated.
- **T6.5** Physical cost: synthesize (Yosys) and time (OpenSTA, or OpenLane) the cache system with `NONE`, D1, D2 (each `M`) and D3, at 1 KB and 2 KB D$, identical constraints and tool versions. Find the minimum clock period that meets timing for each variant (search by period sweep). Report cell area and its delta (absolute and as a percentage of the cache block and of the core), post-synthesis Fmax and delta, and any critical-path change. Repeat each run three times if the flow is nondeterministic. *Accept:* table with tool versions and constraints in `flow/`; all variants run through the same script.

### Phase T7: Documentation (needs T6, partial results are fine)
- **T7.1** `README.md`: architecture diagram (text or Mermaid), build and run instructions, results summary that links only to generated files.
- **T7.2** `REPORT.md` (4 to 6 pages): motivation, design, methodology, results, hypotheses verdicts, limitations (Section 2 verbatim in spirit), credit to the group's prior work.
- **T7.3** `docs/rationale/*.md`: one note per module (core changes, caches, stall logic, wear monitor, each detector, calibration, flow).
- **T7.4** `docs/EXPLAIN_FOR_AUTHOR.md`: plain-language walkthrough of the design and each headline result, with at least 15 questions an interviewer could ask and answers grounded in the generated results. This is the document the author studies to be able to defend the work.
- **T7.5** `docs/RESULTS.md`: auto-generated tables, with each number linked to its CSV row.
- **T7.6** Reproducibility: from a clean clone, `make all` regenerates every table and figure. *Accept:* run it once and record the result in `STATUS.md`.
- **T7.7** Claim audit: list every claim in README and REPORT, confirm each cites a generated artifact, remove or tag anything unsupported, and list every `BLOCKED` or `NOT RUN` item in `STATUS.md`.
- **T7.8** Integrity audit and adversarial self-review (Section 0A.E): run `scripts/check_locks.sh`; confirm test, mutant and arch-test counts have not decreased from baseline; search the repo for forbidden patterns (early `$finish` in testbenches, skipped or expected-fail tests, lint waivers without a logged cause, workload names or seeds hard-coded in `rtl/`); confirm every planned run is in the CSV or in `docs/EXCLUDED_RUNS.md`; recompute at least 10 randomly chosen CSV numbers from raw logs; for each hypothesis verdict and each headline number, test at least one wrong-reason explanation. Write `docs/INTEGRITY_REPORT.md` with every check, its evidence and its result, and move unresolved items into `docs/KNOWN_ISSUES.md`. *Accept:* the report exists and lists every check above; no check is silently omitted.

---

## 7. Experiment matrix and results CSV

**Workloads:** calibration set (Dhrystone, CoreMark); held-out benign set (Embench subset, `memcpy`, `memset`, store-heavy loop); attacks RLA, RTA, RnLA, RnTA in direct and paper forms (5 seeds each for randomized ones); mixed workloads.

**Configurations (reduced; do not run the full cross product):**
1. No cache (baseline).
2. Caches, `DETECTOR=NONE`, size sweep.
3. D1, D2 (sweep `M`), D3 (STATIC and ADAPTIVE), action A1, primary cache config, `k` in {1.5, 2, 4}, window sweep.
   Controls on every attack and benign workload: `NEVER`, `ALWAYS`, and a rate-matched `PLACEBO` for each real detector run.
4. Optional: action A2; `DC_WRITE_LATENCY` in {4, 10}.

**CSV columns (one row per run):** `run_id, git_commit, workload, workload_class, icache_bytes, dcache_bytes, line_bytes, mem_latency, dc_write_latency, detector, action, mode, window_cycles, threshold_k, threshold, M, seed, cycles, instret, cpi, stall_loaduse, stall_flush, stall_imiss, stall_dmiss, i_miss_rate, d_miss_rate, array_writes_total, w_max, w_mean, pmr_all, pmr_written, t_fail_50mhz, t_fail_100mhz, t_fail_500mhz, bypassed_stores, refills_after_bypass, restricted_cycle_frac, fp_cycle_frac, fp_store_frac, detect_latency_cycles, signature_hash, correct`.

---

## 8. Required figures and tables (all generated from the CSV)

1. Miss rate vs. cache size, per benchmark.
2. CPI and stall breakdown: no cache, cache, cache plus each detector.
3. Per-line write heatmaps: benign benchmarks, each attack, each attack under each detector.
4. PMR and `T_fail` table: workload by detector, including the `NEVER`, `ALWAYS` and `PLACEBO` control rows.
5. False-positive and detection-latency table per detector and attack.
6. Sensitivity (false positives vs. latency) plot.
7. Area and Fmax: baseline vs. each detector; D2 counter-count vs. area plot.
8. Hypotheses table (H1 to H3) with verdicts and the numbers behind them.

---

## 9. Final deliverables and definition of done

**Deliverables:** the RTL, testbenches, software, scripts and flow configs; `analysis/results.csv`; every figure and table above; `README.md`, `REPORT.md`, `docs/RESULTS.md`, `docs/HYPOTHESES.md`, `docs/EXPLAIN_FOR_AUTHOR.md`, `docs/rationale/`; `STATUS.md`, `DECISIONS.md`, `OPEN_QUESTIONS.md`, `docs/TOOLS.md`; plus the documentation set from Section 0B (`docs/logs/T*.md`, `docs/LAB_NOTEBOOK.md`, `docs/CHANGE_LOG.md`, `docs/TRACEABILITY.md`, `docs/KNOWN_ISSUES.md`, `docs/EXCLUDED_RUNS.md`, `docs/CRITERIA.md`, `docs/LOCKED.sha256`, `docs/INTEGRITY_REPORT.md`), `scripts/run.sh`, `scripts/check_locks.sh` and `logs/runs/`.

**Done when:**
- Every task is `DONE`, or `BLOCKED` / `NOT RUN` with a logged reason.
- The correctness invariant holds for every detector, action, benchmark, attack and memory latency that was run.
- Every number in the documents is reproducible by `make all` and traces to a CSV row.
- H1 to H3 have verdicts under the pre-registered criteria.
- The limitations in Section 2 appear in the README and report.
- Every task has a per-task log written when it finished, and every result has a command-log record, a CSV row and provenance metadata.
- `scripts/check_locks.sh` passes, no test, mutant or check was removed or loosened, and `docs/INTEGRITY_REPORT.md` shows the adversarial review was done.
- Each real detector is reported against its `PLACEBO`, `ALWAYS` and `NONE` controls.

---

## 10. Stretch items (only after everything above is done)

- Associativity above 1 with LRU, so heatmaps are sets by ways and comparable to the group's figures.
- A counter-based wear-leveling baseline, to show the randomized attacks defeat it.
- `riscv-formal` (RVFI plus SymbiYosys) on the core.
- A branch-predictor study with the Fmax cost.
- RTL-vs-ChampSim correlation of write distributions (needs the group's traces and the author's permission).