# HANDOFF: T3 (wear instrumentation) for a second agent

Written 2026-11-02 at the T2 checkpoint commit. Read this file first, then `docs/writehammer.md` (the spec; Sections 0, 0A, 0B and 4 are binding).

## 0. The one-paragraph picture
`writehammer/` is an RV32I 5-stage core plus I$/D$ study. T0 and T1 are done; T2 (caches) is mostly done and is being finished by the first agent (T2.6 and T2.7 remain). You do **T3.1, T3.2, T3.3 and T3.5 now, and T3.4 only after the first agent tells you the RTL is frozen**. The D$ is write-back + write-allocate and already emits everything the wear monitor needs (below). You work in your own git worktree on branch `t3-wear` so the two agents never edit the same files.

## 1. Your tasks (verbatim from the spec)
- **T3.1** Testbench `wear_monitor`: hooks the D$ data-array write strobes (store hit, fill, partial merge); per-line counters; windowed counts written to CSV (`window, line, count`); phase markers read from MMIO. *Accept:* compiles and logs in a smoke run.
- **T3.2** Statistics script: PMR (all lines and written lines), `w_max`, mean, `T_fail` at 50, 100, 500 MHz; per-line plot and time-windowed heatmap (line vs. window). *Accept:* produces the files for one run.
- **T3.3** Instrument check: micro-programs with known store and fill counts must give exactly the expected per-line counts. *Accept:* all known-answer tests pass.
- **T3.4** Baseline wear for every benign workload (caches on, no detector). *Accept:* heatmap and summary row per workload from `make wear`.
- **T3.5** Independent golden-cache replay check (Section 0A.D): the RTL logs every D$ access (cycle, type, address, size); a separately written Python cache model replays the trace and computes per-line data-array write counts, hits, misses and write-backs. *Accept:* exact match with the `wear_monitor` and the RTL counters on every benign and attack workload, and a deliberately mis-counting monitor mutant is caught.

Acceptance checks are binding. Status words: `DONE` only if the acceptance check ran and passed in this run; otherwise `PARTIAL`/`BLOCKED`/`NOT RUN` (spec 0B.11).

## 2. Where you work
- Worktree: `/home/kritin/Scratch/personal/sv_practice/PROJECTS/RV32I-t3` (branch `t3-wear`), project root `writehammer/` inside it. `.venv` and `third_party` are symlinks to the first agent's copies (read only); `work/` is yours.
- Run everything from `writehammer/` through `scripts/run.sh` when it produces a result (spec 0B.1).
- Python: `.venv/bin/python` has numpy, pandas, matplotlib. Simulators: Verilator 5.020 (use it for anything long) and Icarus 12 (slow with the big cache arrays: minutes where Verilator takes seconds).

## 3. Files you may create or edit
Create new files only, in these places:
- `tb/wear_monitor.sv`, `tb/tb_*wear*.sv`
- `tests/wear_*.py`, `tests/mutants/wear_mutants.py`, `tests/golden/*` for your own known-answer data
- `analysis/wear_*.py`, `analysis/*.csv`, `analysis/*.png`
- `docs/logs/T3.1.md` ... `docs/logs/T3.5.md`, `docs/STATUS_T3.md` (a table with the same columns as `docs/STATUS.md`, T3 rows only)
- `Makefile`: you may replace the single line `wear:       ; @scripts/not_implemented.sh $@ "T3.1-T3.5"` by a real `wear:` target. Do not touch anything else in it.

## 4. Files you must NOT edit (the first agent owns them; ask in your log if you need a change)
- everything under `rtl/` (including `dcache.sv`, `rv32_top_pipelined.sv`)
- every existing file under `tests/` and `tb/` (they are locked or shared), `tests/paths.py`, `tests/run_mutants.py`
- `docs/STATUS.md`, `docs/CHANGE_LOG.md`, `docs/LOCKED.sha256`, `docs/DECISIONS.md`, `docs/TRACEABILITY.md`, `docs/KNOWN_ISSUES.md`, `docs/LAB_NOTEBOOK.md`
Instead keep your own `docs/logs/T3.x.md` (put your decisions, problems and any needed change requests there) and `docs/STATUS_T3.md`. The first agent merges them into the shared files. If you add test files, lock them with `scripts/check_locks.sh --add` and commit the resulting `docs/LOCKED.sha256` lines (the merge of that file is a trivial union of lines). Adding tests is always allowed; changing or removing an existing one is not (spec 0A.A).
If you believe the RTL needs a change, **do not make it**: write the request, the evidence, and a minimal reproducer in your task log.

## 5. Git rules (the author's, mandatory)
- Author identity for every commit: `git -c user.name=krit504 -c user.email=138591590+krit504@users.noreply.github.com commit ...` (the repository's own config holds a different identity and must not be used).
- **No `Co-Authored-By` line, no "Generated with" line, no attribution of any kind** in commit messages.
- Stage files by name only (`git add path/one path/two`). Never `git add -A` or `git add .`.
- One commit per task, message `T<ID>: summary` (spec 0B.12). Never rewrite history. **Never push** to any remote (the repository may be public; the author has not cleared publishing).
- Do not run `git commit` on `main`; stay on `t3-wear`.

## 6. Interfaces you can rely on (tested; the first agent will not change them without telling you)
Top module `rv32_top_pipelined` (`rtl/rv32_top_pipelined.sv`), parameter `CACHES_ON = 1` for the cache system. Outputs, all observation only:

| Signal | Meaning |
|---|---|
| `dc_aw_valid`, `dc_aw_line[31:0]`, `dc_aw_kind` | one pulse per **data-array write event** in the D$. `aw_line` is the cache line index (0..NUM_LINES-1, zero-extended). `aw_kind` 0 = store hit (including a partial-word merge), 1 = line fill. |
| `dc_tr_valid`, `dc_tr_we`, `dc_tr_addr`, `dc_tr_size[2:0]`, `dc_tr_bypass` | one pulse per **completed request** (one per load or store instruction that reaches Memory and is not an MMIO store). `tr_size` is 1/2/4 for stores; for loads it is always 4 (the width is not visible there; it does not matter for the counts). `tr_bypass` = a restricted store (T5; always 0 until a detector is on). |
| `dc_refill_cnt`, `dc_write_cnt`, `dc_cnt_access/hit/miss/wb/bypass/rab/stall` | counters: fills, stores completed, accesses, first-lookup hits, misses, dirty write-backs, restricted stores, refills after a bypass, cycles with `dmiss = 1` |
| `mmio_we`, `mmio_addr`, `mmio_wdata` | MMIO stores; `tb/sys_monitor.sv` decodes HALT (+0x00), START (+0x04), STOP (+0x08), PHASE (+0x0C, prints `PHASE <value> cycle=<n>`), PUTCHAR (+0x10) at 0xF0000000 |
| `dbg_widx`, `dbg_word` | debug read of memory word `dbg_widx` (the D$ is overlaid, so dirty lines count); use the TRUE address, not a bare index |

Definitions you must use exactly (spec Section 4; do not change them): a **data-array write event** is a store hit, a line fill, or a partial-word merge into the D$ data array. Array reads (hits, write-back reads) and metadata (tag, valid, dirty) writes are **not** writes. A restricted store never writes the array. Primary geometry: 2 KiB, 16-byte lines, direct-mapped (128 lines); the cache is parameterized (`DCACHE_BYTES`, `LINE_BYTES`).

Existing examples to copy from (read, do not edit):
- `tb/tb_dcache.sv` + `tests/dcache_test.py`: a testbench that logs the array-write events per line (`AWL <line> <n>`) and a test that compares them with the Python model. Your wear monitor does the same job on the whole core.
- `tests/cache_model.py` (`CacheModel`): the independent Python D$ model. It replays a request stream `[(kind, addr, size, bypass)]` (`kind` "L" or "S") and gives `writes[line]` and the counters. T3.5's golden replay is this model driven by the RTL's trace.
- `tb/sys_monitor.sv`, `tb/tb_prog.sv`, `tests/vl_runner.py` (`run_image_vl`): how a program image is run and its MMIO events read. `tests/vl_tb.py` (`run_tb`) builds and runs any testbench under Verilator with `-G` parameters, cached and safe for parallel use.
- Programs: `sw/build.py` builds C into `program.hex`; the benign workloads are registered in `tests/workloads.py` and built by `analysis/baseline.py`'s `workloads()`.

## 7. Practical rules learned the hard way
- Use Verilator for anything beyond a few thousand cycles. Icarus is about 100x slower on the cache arrays.
- SystemVerilog: a variable declared **with an initializer inside a loop or block** is initialized once at time 0, not per iteration (this broke two testbenches). Declare, then assign.
- Verilator 5.020 does not support default values on module input ports. Icarus 12 cannot bind string-typed parameters inside `generate` blocks (keep file-name parameters untyped).
- Never use `pkill -f` or `pgrep -f` with a pattern that appears in your own command line (it kills your own shell).
- Run long jobs with the tool's background mode and write a heartbeat line every 30 s to a log; do not trust a silent job. The laptop sleeps when the lid is closed and everything pauses.
- Resource limits: at most 4 parallel jobs (`JOBS=4`), Verilator `-j 2`. Two agents share 12 cores and 14 GB.
- Do not weaken any test, assertion, tolerance or timeout to get a pass (spec 0A.B). If a check fails, find the root cause (0A.C) and log it.
- Every number, plot and table must come from a script that regenerates it; never edit results by hand; every plot gets a sidecar `.json` naming the script, commit and data hash (0B.8).

## 8. How the first agent merges your work
When a task passes its acceptance check: commit it on `t3-wear` as `T3.x: ...`, record the hash and the exact command that proves it in `docs/logs/T3.x.md` and `docs/STATUS_T3.md`, and tell the author. Periodically (and before reporting) run `git merge main` in your worktree to pick up RTL or test changes; you only add files, so it merges cleanly. The first agent then merges `t3-wear` into `main`, combining the status, change-log and lock lines.

## 9. What may still change under you (and how you will know)
The first agent is finishing T2.6 (full invariant run, mutant check) and T2.7 (counters and sweeps for miss rate). If either shows an RTL bug the fix goes into `rtl/dcache.sv` or the top; any change to the interfaces in Section 6 or to the wear numbers will be written in `docs/RTL_CHANGES_AFTER_CHECKPOINT.md` on `main` (it does not exist until something changes). T3.4 (baseline wear) is the only task whose numbers depend on a frozen RTL, which is why it waits for the freeze message.
