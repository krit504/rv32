# CHANGE LOG

Every change to a protected artifact (spec 0A.A): what changed, why, and evidence the original was wrong. `scripts/check_locks.sh` fails when a locked file's hash changes without an entry here naming the file.

Entry format:

```
## CHG-NNN YYYY-MM-DD <file path>
- What changed:
- Why:
- Evidence the original was wrong:
- New sha256:
```

## CHG-001 2026-11-01 tests/mutants/core_mutants.py
- What changed: the patch text of mutant C5_store_hit_no_line_update. It now removes the byte-enabled store-hit write in `dcache.sv` (`for (int k ...) if (be[k]) data[index][32*wordsel + 8*k +: 8] <= ...`) instead of the word write `data[index][32*wordsel +: 32] <= wdata;`. The mutation itself is unchanged: a store hit no longer updates the cache line.
- Why: T1.1 gave the D$ byte enables, which rewrote the line the old patch matched. Not a loosening: the harness reported PATCH_FAILED on the old text (patch text found 0 times), so the mutant was not applied.
- Evidence the original was wrong: `make test-mutants` after T1.1 printed `C5_store_hit_no_line_update PATCH_FAILED patch text found 0 times in dcache.sv`. The new text is verified to apply (it must occur exactly once) and the mutant is caught by `cache_integration` (see below).
- New sha256: ae24b78acda5b859404075360c103fb5b687e507db1ec2378648ec77c54d2795

## CHG-002 2026-11-01 tests/run_mutants.py
- What changed: imports the new mutant list `tests/mutants/subword_mutants.py` alongside `core_mutants.py`, and adds the sub-word test (caches off, and caches on LAT=2) to the suite the harness runs against every mutant.
- Why: T1.2 adds mutants and a test; the runner must apply and run them. Only adds mutants and tests; no existing mutant or check is removed or loosened.
- Evidence the original was wrong: not a correction. Evidence the change did not weaken anything: before the change `make test-mutants` reported 12/12 caught; after it reports 20/20 caught, and the original 12 are caught by the same tests as before.
- New sha256: 9124a19f1e6f2cd193489e36fe7e274769574cd7847438ad3ba57f16bd43991f

## CHG-003 2026-11-01 tests/asm.py
- What changed: appended encoders (sll, slt, sltu, xor_, srl, or_, and_, sra, slti, sltiu, xori, ori, andi, slli, srli, srai, lb, lh, lbu, lhu, sb, sh, blt, bge, bltu, bgeu).
- Why: T1.2 needs sub-word encoders; the remaining ALU and branch encoders are needed by the T1.6 random generator.
- Evidence the original was wrong: not a correction. `git diff HEAD -- tests/asm.py` shows 0 removed lines: no existing encoder changed, so no existing test's inputs changed.
- New sha256: ce65bd4d39e3984a3dbbe0d1066df28352b8b6ca89cf1d2c3081552a9beaf80f
