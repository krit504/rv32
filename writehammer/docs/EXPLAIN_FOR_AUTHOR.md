# Explain it so you can defend it

For the author. Plain language first, then 18 questions an interviewer or reviewer could ask, with answers that come from the generated results (`docs/RESULTS.md`, `docs/HYPOTHESES.md`, `flow/cost_table.md`). If an answer here ever disagrees with those files, the files win and this page is wrong.

## The story in one minute

Some memories wear out when one cell is written too often. A "write hammer" program writes the same place over and over to kill that cell. We took a small RISC-V core, put a data cache in front of its memory, and **pretended the cache's data array is a memory that wears out**. The wear of the array is set by its most-written line. Then we asked: can a tiny piece of hardware watch the stores, notice a hammer, and stop it, cheaply?

We built three watchers. **D1** keeps a counter per cache line. **D2** keeps a few counters shared by hashing the line number. **D3** keeps one counter of all stores. When a counter passes a threshold the line (or all stores) is "restricted": a restricted store skips the cache array and goes straight to memory, invalidating the line. We built three controls to keep ourselves honest: **NEVER** (restricts nothing), **ALWAYS** (restricts every store: the best any restriction could possibly do) and **PLACEBO** (restricts a random share of stores equal to what the real detector restricted).

What we found, in order of importance:
1. **The watchers that count writes per line (D1, D2) are good detectors.** They caught the direct forms of the attacks and never raised a false alarm on any of 13 benign programs at the main setting.
2. **The mitigation does not work against these attacks.** Even ALWAYS barely reduces writes, because after a store skips the array the line is invalid, the next load refills it, and a refill is also an array write. Detection is fine, the action defeats itself.
3. **D3 (store rate) is the weak one**: it caught nothing at the main setting and wrongly restricted a benign program (`huffbench`) for 98 % of its run in static mode.
4. **Cost**: D1 is the only variant clearly above the noise of the synthesis tool (+4.0 % of the cache at 1 KiB, +5.7 % at 2 KiB).
5. **The pre-registered verdicts**: H1 refuted, H2 inconclusive, H3 refuted. We did not change the criteria after seeing the data.

## Questions and answers

**1. What is the question this project answers?**
Which cheap hardware detector catches write-hammer patterns, including randomized ones, at what cost, and which one fails? The scope is one core and a modeled NVM, not real SRAM and not a multicore attacker (`README.md`, "What this is not").

**2. Why a "modeled" NVM? Are L1 caches endurance-limited?**
No, and we do not claim they are. We use the cache data array as a stand-in for an NVM array so we can count writes per line and apply a wear model (PMR and an extrapolated time to failure with an assumed endurance of 1e15 writes). It is a measurement setup, not a product claim.

**3. What is PMR?**
Peak-to-mean ratio of writes per line: the most-written line divided by the average over lines. 128 means one line took all the writes of a 128-line cache. Lifetime is set by the peak, so a high PMR means early failure. It is computed over all lines (`pmr_all` in `analysis/results.csv`).

**4. What exactly counts as a "write" to the array?**
Every data-array write: a store that hits (it writes the line) and every line fill. This definition is identical in every configuration, and refills caused by bypassed stores are always counted (spec 0A.B.6). Metadata writes (tags, valid bits) are not counted.

**5. Walk me through what a restricted store does.**
The store skips the array. If the line is resident and dirty, it is written back first. The line is invalidated, and the store word is sent directly to memory (`rtl/dcache.sv`, states BYP_WB and BYP_WR). Architecturally nothing changes: the correctness invariant (same final registers and memory as the cache-less core) held for all 9,723 runs.

**6. Why did the mitigation not reduce writes?**
Because the attacks read the line after writing it. Restricted store, line invalid, load misses, refill writes the array. In the direct RLA attack: 285,720 array writes with no detector, 285,716 with every store restricted, and 285,713 of those are refills after a bypass (`docs/RESULTS.md` section 4). The paper forms keep 79 to 83 % of their writes. Mean over all attacks 0.919 of the baseline, best case 0.792.

**7. So are H1 to H3 wrong ideas, or is the implementation wrong?**
Neither is established beyond what we measured. We checked the implementation hard: bypass verification shows zero store-hit array writes under ALWAYS (`tests/bypass_verify.py`), the cache is replayed by an independent Python model, and the detectors fire (D1 restricted stores on every attack it detected, `scripts/audit.py`). The verdicts are about *this* action (bypass plus invalidate) against *these* read-back attacks.

**8. What do H1, H2 and H3 say and why those verdicts?**
H1: D1 stops fixed-location attacks and is evaded by randomized ones; needs at least 50 % PMR reduction on RLA and RTA. D1 reduces nothing, so REFUTED. H2: D2 keeps 80 % of D1's benefit; D1 reaches 50 % on no attack, so the comparison is empty and the verdict is INCONCLUSIVE by the criterion's own wording. H3: D3 reduces PMR by 50 % on all attacks *and* falsely flags a benign program; the second half holds (`huffbench`), the first does not, so REFUTED.

**9. Were the criteria changed after you saw results?**
No. They are in `docs/CRITERIA.md` (locked by hash), and the verdicts are generated by `analysis/hypotheses.py`, not written by hand. One related rule, the attack-validation criterion (T4.7), fails for 23 of 24 attacks; we left it failing and reported it (DEC-010) instead of amending it.

**10. Why does crc32 matter?**
Its whole-run PMR is 127.9 of a possible 128: one hot line, benign code. So whole-run PMR cannot separate attacks from that benign program, which is why the T4.7 rule fails. The windowed detectors do better: D1 and D2 restricted zero crc32 cycles at the main setting. Under 4 of 18 more aggressive D1 settings it is restricted, in the worst case for 99.6 % of its cycles (`docs/HYPOTHESES.md`).

**11. Why no false positives for D1 and D2 but some for D3?**
D1 and D2 count writes to the *same line*; benign programs spread writes, and even `crc32` stays under the calibrated threshold within each 10,000-cycle window. D3 counts all stores; store-heavy benign code such as `huffbench` crosses a threshold set from Dhrystone and CoreMark. STATIC mode latches, so one crossing restricts the rest of the run (98 %); ADAPTIVE re-checks each window (14.7 %).

**12. Why did D3 catch no attack?**
At the main setting its threshold is twice the per-window store maximum of Dhrystone and CoreMark: 1,534 stores per 10,000 cycles. The busiest attack, RLA direct, issues about 1,430. D3 is not dead: over all registered settings it detects some attack runs (30 of 432), just not at the pre-registered primary one (`scripts/audit.py`).

**13. D1 and D2 missed the "paper" attack forms and RTA direct. Is that a failure?**
It is a measured limit. Those attacks spread writes (PMR 1.2 to 2.5 without a detector for the paper forms), so no single line gets hot enough within a window. That also means they do little wear damage to any one line in this model. We report which attacks are detected, not only the average.

**14. How were thresholds chosen? Could the held-out set have leaked in?**
Threshold = `k` times the per-window maximum on the calibration set only (Dhrystone, CoreMark), for k of 1.5, 2, 4; primary k = 2. `analysis/calibrate.py` builds only the calibration workloads and the held-out set is never read for calibration. The held-out list itself was fixed before any detector existed (DEC-008).

**15. What are the controls for, and what did they show?**
NEVER must equal NONE in every metric (it did, on every image). ALWAYS gives the best possible effect of the restriction (a ratio of at most 20.8 % fewer writes). PLACEBO restricts a random fraction equal to the detector's. The detectors' mean PMR reduction (0) and the placebo's (about 1e-13 to 1e-7) are indistinguishable, so we do not claim the detectors beat random restriction on wear.

**16. What did the guard cost in hardware?**
Pinned flow, sky130, three identical repeats per variant. The cache pair is 14 to 19 times the core's area. D1: +4.0 % of the cache at 1 KiB and +5.7 % at 2 KiB (about +57 % and +109 % of the core's area). D3 and D2 up to M = 32 are inside the ~2 % synthesis variation (some D2 variants even come out smaller than no guard, which shows that variation). Fmax is 5 to 10 MHz and its deltas change sign, so we make no Fmax claim (`flow/cost_table.md`).

**17. What would an attack look like that defeats your detectors, and what would fix the mitigation?**
Defeats detection: writes spread thinly across many lines within each window (the paper forms already behave that way). Fixes the mitigation: stop refills of a flagged line from writing the array (a read-around for hot lines). That is a design change made after seeing the results, so it is future work, not part of the pre-registered study.

**18. What did you not do, and what are the weakest points?**
Action A2 (stall-throttle) was not run (KI-020). One core, one cache family, one implementation of each attack, 13 workloads. Attacks that never read back were not measured. The endurance and clock are assumptions. The physical flow is untuned. The post-hoc windowed analysis is labelled exploratory and changes no verdict. An honest answer to "so what?" is: the counting detectors work, the specified action does not, and the follow-up is a different action.

## If you only remember five numbers
- 9,723 runs, all architecturally correct (`docs/EXCLUDED_RUNS.md`).
- D1 and D2: 11 of 24 attacks detected, 0 false-positive cycles on 13 benign workloads.
- ALWAYS: attack array writes at best 20.8 % lower, 8 % on average.
- D3: false-positive 98 % (static) on `huffbench`, no attack detected at the primary setting.
- D1 area: +4.0 % / +5.7 % of the cache (1 / 2 KiB).
