# DECISIONS

Each entry: the choice, the alternatives, the reason, the impact, the date (IST). Changes to Section 3 defaults or Section 4 definitions also go into `CHANGE_LOG.md`.

## DEC-001 Project location: subdirectory `RV32I/writehammer/` of the existing repo
- **Alternatives:** a new local-only repository.
- **Reason:** author's choice (2026-11-01). Keeps the study next to the core it extends.
- **Impact:** the repo has an `origin` remote (`github.com/krit504/rv32`). Spec 0.6 forbids pushing to a public remote; nothing in this project pushes. Remote visibility is unverified (see `OPEN_QUESTIONS.md`).
- **Date:** 2026-11-01

## DEC-002 Commits by the agent, krit504 identity, no attribution trailer
- **Alternatives:** the author commits from commands the agent provides.
- **Reason:** author allowed per-task commits for this project. Every commit passes `-c user.name=krit504 -c user.email=138591590+krit504@users.noreply.github.com`, because the repo's local git config holds a different (work) identity. No co-author or tool attribution line.
- **Impact:** commit messages follow spec 0B.12 (`T<ID>: summary`).
- **Date:** 2026-11-01

## DEC-003 (SUPERSEDED by DEC-006) Physical flow uses IHP sg13g2, not sky130 (deviation from Section 3)
- **Alternatives:** IHP sg13cmos5l (the author's Tiny Tapeout chip library); installing sky130 into the PDK cache.
- **Reason:** sky130 is not installed. sg13g2 is in `~/.cache/tt-pdk/root`, and this project has no tie to the Tiny Tapeout chip. Tools come from the author's pinned LibreLane Docker image (`ghcr.io/librelane/librelane:3.1.0.dev3`, id `sha256:369c964b…`).
- **Impact:** every T6.5 number is labelled sg13g2 and must not be compared with the author's sg13cmos5l results. Flow runs are prepared as scripts and launched by the author, not by the agent.
- **Date:** 2026-11-01

## DEC-004 The cache datasheet in the author's notes is v1 history; this spec governs
- **Alternatives:** update that datasheet as the caches change.
- **Reason:** author's choice. The datasheet describes a write-through, no-write-allocate D$, word-only accesses, and two separate backing memories with no shared port.
- **Differences from the spec (spec wins):** D$ becomes write-back plus write-allocate with dirty bits and byte enables (T2.4); one unified `mem_model` with an arbiter giving the D$ priority replaces the two backing memories (T2.1); line size becomes a parameter (16/32/64 B) instead of a fixed 16 B; cache sizes default to 2 KB (128 lines) instead of 1 KB (64 lines).
- **Impact:** the new design is documented in `docs/rationale/`.
- **Date:** 2026-11-01

## DEC-005 The test baseline is the current repo, not the counts quoted in T0.3
- **Alternatives:** use T0.3's "16 directed hazard cases in 18 runs, 5 of 5 mutants".
- **Reason:** the repo has grown since the spec was written: 25 directed hazard programs, each run with forwarding and with the no-forwarding ablation, plus the cache-on runs at four latencies. Spec 0A.A forbids test counts decreasing, so the floor is what exists now. The exact counts are recorded in T0.3's log.
- **Impact:** T0.3 checks that the quoted results reproduce as a subset, and records the larger current numbers as the baseline.
- **Date:** 2026-11-01

## DEC-006 Physical flow uses sky130 `sky130_fd_sc_hd` as Section 3 specifies (supersedes DEC-003)
- **Alternatives:** IHP sg13g2 (DEC-003).
- **Reason:** DEC-003 rested on the agent's claim that sky130 was not installed. That claim was wrong: sky130A is installed through ciel at `~/.cache/tt-pdk/root/ciel/sky130/versions/74c0e6b118a67d94c24172143d3bd597473fa63d/sky130A` (open_pdks `74c0e6b`), with `libs.ref/sky130_fd_sc_hd/lib` present. With no download needed, the spec default applies and there is no deviation.
- **Impact:** T6.5 uses `sky130_fd_sc_hd`, same tools (the author's pinned LibreLane image), same constraints for every variant. Results are labelled sky130 and are not comparable with the author's sg13cmos5l numbers. Flow runs are still launched by the author (Q-002).
- **Date:** 2026-11-01

## DEC-007 `dmem` zero-initializes
- **Alternatives:** compare only memory words the program wrote; leave `dmem` uninitialized.
- **Reason:** with caches off `dmem` started as `x`, with caches on the data `backing_mem` starts at 0 (cache datasheet). The same program then produced different memory states, and the T1.2 reference model (which starts at 0) disagreed on untouched words. Making the two configurations start identical is also what the correctness invariant (spec Section 4) needs. Weakening the comparison to hide it was rejected.
- **Impact:** `dmem` gains an `initial` loop. A load from a never-written word now reads 0 with caches off, as it already did with caches on.
- **Date:** 2026-11-01

## DEC-008 The held-out Embench-IoT subset (fixed before any detector exists)
- **Alternatives:** all 19 kernels; the 4 cheapest; a random subset.
- **Reason:** all 19 Embench-IoT kernels build for rv32i bare metal and pass their built-in self-check on the RTL with caches off (survey in `docs/logs/T1.8.md`). The experiment matrix multiplies every workload by detectors, thresholds, windows, seeds and cache sizes, so the set must be small, but it must span different store behaviour and must not be picked after seeing detector results. Rule: exclude kernels that take more than 10 M cycles with caches off (`edn` 102 M, `depthconv` 68 M, `matmult-int` 36 M), then keep one or two from each behaviour group so the benign set is diverse: checksum (`crc32`), hashing and ciphers (`md5sum`, `nettle-sha256`, `nettle-aes`), compression and sorting with many stores (`huffbench`, `wikisort`), pointer-heavy data structures (`sglib-combined`), and buffer filling (`qrduino`). The other eight sub-10 M kernels (`aha-mont64`, `nsichneu`, `picojpeg`, `slre`, `statemate`, `tarfind`, `ud`, `xgboost`) are skipped only to bound the matrix; they build and pass and can be added.
- **Held-out set (final):** `crc32`, `md5sum`, `nettle-sha256`, `nettle-aes`, `huffbench`, `wikisort`, `sglib-combined`, `qrduino`, plus the in-repo `memcpy_big`, `memset_big` (16 KiB buffers, larger than the largest D$ in the study) and `storeloop`. The calibration set stays Dhrystone and CoreMark (spec Section 3). Thresholds are never tuned on this set (spec 0A.B.4).
- **Impact:** the list is repeated in `tests/workloads.py`, which is locked.
- **Date:** 2026-11-02

## DEC-009 Checkpoint commit in the middle of T2 so a second agent can start T3
- **Alternatives:** wait until all of T2 is DONE and commit once per task as spec 0B.12 says; let the second agent share the working tree.
- **Reason:** the author asked to speed up the project with a second agent working on T3 in parallel. T3 needs the T2 ports (data-array write events, per-request trace, counters), which exist only in the uncommitted working tree. A shared working tree is unsafe (shared files, mutation jobs that copy `rtl/` and `tb/`), so the second agent gets its own git worktree and branch, which must start from a commit that contains the T2 RTL.
- **Impact:** one commit (`T2 checkpoint`) covers T2.1 to T2.5 plus the start of T2.6, instead of one commit per task. STATUS.md says exactly which are DONE (T2.1, T2.2, T2.5) and which are PARTIAL (T2.3, T2.4, T2.6) or not run (T2.7), and why. The full `make test` had not been rerun after the last edits at checkpoint time. The T3 hand-off is `docs/HANDOFF_T3.md`.
- **Date:** 2026-11-02

## DEC-010 T4.7 fails as pre-registered and is left failing; the criterion is not changed
- **Finding (checked from the data, `analysis/attack_pmr_all_workloads.csv`):** the fixed T4.7 rule requires every attack to show a higher PMR(all lines) than every benign workload. The benign workload `crc32` has PMR(all) 127.937 on a 128-line cache, within 0.05% of the maximum possible (128 = every write on one line): it keeps its running CRC in memory and rewrites one line almost exclusively. Only the single-location attack `rla_direct_s1` (128.0) exceeds it; the other 23 of 24 variants fail the rule. This is not an attack bug: PMR = N_lines x w_max / total_writes, so beating crc32 needs more than 99.95% of all array writes in one line, which a toggle between two targets, a moving target, or a paper-form attack (arrays larger than the cache, so fills spread the writes over all lines) cannot do by definition (paper forms score 1.0 to 2.5, randomized direct forms about 20, two-target toggle 64).
- **Alternatives:** (a) change the criterion or the benign set so the check passes (drop crc32, compare windowed PMR, compare only within a class); (b) tune the attacks to concentrate more; (c) leave the rule and the programs unchanged and report the result.
- **Decision:** (c). (a) and (b) are exactly the shortcuts spec 0A.B forbids (loosening a locked criterion, removing a workload, tuning an attack after seeing results), and none of them would be justified by evidence that the original was wrong, only by the wish for a pass. T4.7 is recorded as `PARTIAL`: the table and the wandering-location heatmaps exist and the randomized attacks do show the wandering pattern; the PMR comparison fails 23 of 24. `make attacks-validate` runs the check and exits 1 by design; `make attacks` (T4.1 to T4.6 and T4.8) must pass.
- **Consequences for the study:** (1) a benign program can look like a hammer attack at line granularity, which is itself a result: expect per-line detectors (D1, D2) to flag `crc32`, reported as a false-positive finding, not hidden. (2) PMR over a whole run is the wrong yardstick for wandering attacks; the windowed view is what T4.7 asks for in the heatmap. Supplementary windowed metrics (per-window PMR, top-k line share, `w_max` per cycle) will be computed in T6 as **post-hoc exploratory analysis, labelled as such**, and are never used to claim that T4.7 passed.
- **Reserved to the author:** whether to amend the T4.7 criterion. Doing so needs a `docs/CHANGE_LOG.md` entry with evidence that the original was wrong (the saturation above is that evidence) and all affected results redone.
- **Date:** 2026-11-03
