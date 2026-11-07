# INTEGRITY REPORT (spec 0A.E, T7.8): adversarial self-review

Written 2026-11-05; updated 2026-11-07 after the clean-clone run (T7.6). Method: for each headline claim ask "how could this be true for the wrong reason?", run a targeted check, record the outcome. The computable checks are in `scripts/audit.py` (`make audit`); this page records the questions and the judgments that a script cannot make.

## Automated audit (`make audit`)
Locks verified (60 files); mutants defined 52 (baseline 13); every check count at or above `tests/BASELINE_COUNTS.json`; no skipped or expected-fail tests, no uncommented lint waivers, no `-Wno-` in the lint target; planned 9,723 = completed 9,723, every row `correct = 1`, run_ids unique; every file cited in README.md, REPORT.md and docs/RESULTS.md exists; four adversarial computations (below) pass.

## Questions, checks, outcomes

| # | How could the claim be true for the wrong reason? | Check | Outcome |
|---|---|---|---|
| 1 | "No detector reduces PMR" because the guard never restricts, or the bypass is not applied. | D1 restricted stores on every attack run it detected (`scripts/audit.py`); ALWAYS bypassed stores in every run; `tests/bypass_verify.py` 18/18: zero store-hit array writes under ALWAYS and the replay against the independent cache model matches. | Bypass is applied and counted. The effect is the refill after the bypass: RLA direct 285,713 refills for 285,718 bypassed stores (`docs/RESULTS.md` section 4). |
| 2 | "D3 catches no attack" because D3 is dead. | D3 attack runs over all registered settings: 30 of 432 detected (`scripts/audit.py`); the guard unit test 62/62 includes D3 detection, hysteresis and static latch. | D3 works; at the primary threshold (1,534 stores per 10,000 cycles) it is above the busiest attack's rate (about 1,430). |
| 3 | "Zero false positives for D1 and D2" because the thresholds are unreachable. | D1 and D2 detect 11 of 24 attack runs at the same setting; on `crc32`, 4 of 18 registered D1 settings restrict at least one cycle (`docs/HYPOTHESES.md`). | The detectors fire where the data says they should; the zero is a property of the calibrated threshold, not of a dead detector. |
| 4 | Thresholds were tuned with the held-out set. | `analysis/calibration.csv` column `calibration_set`: only "Dhrystone (500 runs)+CoreMark (10 iterations)"; `analysis/calibrate.py` builds only the calibration registry. | No leak found. |
| 5 | `correct = 1` for all 9,723 runs is vacuous. | The signature is the caches-off architectural state, from the core itself; the bypass mutants X1 (store dropped) and X2 (wrong data) are caught by the same comparison (`tests/guard_mutants.py`, 19/19); NEVER equals NONE in cycles and array writes on all 41 pairs (`scripts/audit.py` computation above). | Not vacuous. |
| 6 | Reported results are a selection. | `docs/EXCLUDED_RUNS.md`: planned 9,723, completed 9,723, missing 0; randomized attacks report seeds 1 to 5 separately and as mean and range. | No selection. |
| 7 | The PLACEBO comparison is unfair (rate not matched). | The harness runs the real detector first and sets `WG_PLACEBO_RATE` from its measured fraction (`docs/T5_INTERFACE.md`); the unit test checks the RTL rate (`placebo_rate*` cases). Per-run matching tolerance was not audited separately. | Mechanism verified; the per-run tolerance is an unaudited detail (listed below). |
| 8 | The cost deltas are real. | D2 M = 4, 8, 16 come out smaller than no guard at 2 KiB, which a design that only adds logic cannot; three repeats are identical (the flow is deterministic), so the variation is between netlists, not between runs. | Deltas under about 2 % of the cache are treated as noise; only D1 is claimed. Fmax deltas are not claimed. |
| 9 | The models used as cross-checks share the author's blind spots. | The guard model (`tests/guard_model.py`) was written from the documented behavior, not the RTL source, and the 14 directed cases assert on the RTL output directly; the cache replay model predates the wear monitor. Same author, same understanding of the spec. | Reduced, not removed: a weakness listed below. |
| 10 | "H1 and H3 refuted" because the attacks were weakened or the baseline strengthened. | The attacks come from the author's papers via the T4 logs; the T4.7 validation rule was kept fixed and fails (reported); no attack parameter was changed after results (`docs/DECISIONS.md` DEC-010, `docs/CHANGE_LOG.md`). | No tuning found. The finding about read-back attacks is a property of the implemented attacks and is stated as such. |

## Known weaknesses (not hidden)
- Same author wrote the RTL, its independent models and its tests (question 9). The directed tests and the controls reduce, but do not remove, shared misunderstanding.
- KI-023: one guard mutant was caught by a Verilator build crash in the last run instead of a behavioral mismatch (it was caught by mismatch earlier).
- Per-run PLACEBO matching tolerance not audited (question 7).
- Action A2 not run (KI-020); T4.7 fails by its fixed rule (KI-017).
- Synthesis variation of about 2 % of the cache area bounds the physical claims; the flow is untuned.
- The earlier `make test` run reported ERROR and PATCH_FAILED in the mutant suite; the cause was two overlapping runs sharing a work directory (and a retargeted mutant patch, CHG-020), not a design fault. The clean single run passed 52/52.
- T7.6 (clean-clone `make all`) was run: all 9,723 rows recomputed and identical to the committed CSV, other artifacts byte-identical (`docs/logs/T7.6.md`). Disclosed deviation: the run was interrupted once (arch LAT=10) and resumed, so it was not one uninterrupted `make` invocation; the physical flow itself was not re-run.
