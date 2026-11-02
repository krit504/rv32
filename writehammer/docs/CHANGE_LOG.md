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

## CHG-004 2026-11-01 tests/run_mutants.py
- What changed: imports `tests/mutants/perf_mutants.py`; copies `tb/` into each mutant's directory and resolves file names starting with `tb/` there; sets `TB_DIR`; runs `tests/perf_tests.py` first in the suite.
- Why: T1.3 adds mutants of the testbench-side monitor, which live in `tb/`, not `rtl/`.
- Evidence the original was wrong: not a correction. Nothing was removed or loosened: the earlier 20 mutants are still applied and caught (27/27 after the change), and the test order only adds `perf` at the front.
- New sha256: 97e710b31aa38aee973dd8dd6ac0f6c68e139e00e330277b5994ff1e59177d98

## CHG-005 2026-11-01 tests/paths.py
- What changed: `TB` can be overridden with the `TB_DIR` environment variable (docstring updated).
- Why: lets the mutation runner point the tests at a patched copy of `tb/`.
- Evidence the original was wrong: not a correction; with `TB_DIR` unset the value is identical to before.
- New sha256: 2a52ae7f2468e671702e0d2983f503e95cf2a8a13e35625108a6690dd8a34037

## CHG-006 2026-11-02 tests/prog_runner.py
- What changed: the output parsing moved out of `run_program` into a new function `parse_output(out)` so `tests/image_runner.py` can reuse it. `run_program` now ends with `return parse_output(out)`; the parsing code itself is unchanged.
- Why: T1.4 runs linked images through the same testbench output.
- Evidence the original was wrong: not a correction. `make test-perf` (which uses `run_program`) gave 21/21 before and after, and all 7 monitor mutants (P1-P7) are still caught.
- New sha256: b44027c1dd83b1c3ed40700263830c1765922fd3c3268c69f5a66f57d6171b80

## CHG-007 2026-11-02 tests/run_mutants.py
- What changed: imports `tests/mutants/toolchain_mutants.py` and runs `tests/toolchain_test.py` in the suite against every mutant.
- Why: T1.4 adds mutants of the image-loading path and a test for them. Adds only; nothing removed or loosened.
- Evidence the original was wrong: not a correction. Before the change `make test-mutants` reported 27/27 caught; after it reports 30/30 caught, and the original 27 are caught by the same tests as before.
- New sha256: 155f21b6078f67c9ea1005621eeeeee1288e347079a7e71448c758d33d9b08a3

## CHG-008 2026-11-02 tests/run_mutants.py
- What changed: the suite run against every mutant now also runs `tests/random_lockstep.py --n 60` (60 random programs).
- Why: T1.6 adds the random lockstep test; running a small batch against each mutant adds a detector. Adds a test only; nothing removed or loosened.
- Evidence the original was wrong: not a correction. The earlier 30 mutants are still caught (see `work/full_test*.log` before and the post-change run in the T1.6 log).
- New sha256: 9553ea2c33df276805388ca5ca6840a95853e8e5a2266af6d4b39f8c7da60f36

## CHG-009 2026-11-02 tests/paths.py
- What changed: `CORE_RTL` drops `backing_mem.sv` and adds `mem_model.sv` and `write_guard.sv`.
- Why: T2.1 replaces the two per-cache `backing_mem` instances with one unified `mem_model` (spec T2.1, DEC-004), and T2.4/T5.1 add `write_guard`. The file list must name the sources the core now needs.
- Evidence the original was wrong: not a correction of a test. `rtl/backing_mem.sv` no longer exists (removed in the same change); any test that compiled the old list now fails to find it.
- New sha256: f0bbbd1979d79acb38a1df339225b74cca60a60c0d1596a0c771681643b39f70

## CHG-010 2026-11-02 tests/cache_integration.py
- What changed: test `store_miss_no_refill` (expected 0 D$ refills) becomes `store_miss_allocates` (expects 1 refill, 1 store); test `addrs_0x400_apart` becomes `addrs_cache_size_apart` (second address 0x1000 instead of 0x400).
- Why: T2.4 changes the D$ to write-back with write-allocate and the primary geometry to 2 KiB (spec Sections 3 and 6, DEC-004); the v1 expectations encoded the cache datasheet's write-through, no-write-allocate, 1 KiB design. The spec governs.
- Evidence the original was wrong: the original expectations are properties of the superseded design: under write-allocate a store miss must fill the line (a store merge into a line the cache does not hold is impossible for a write-back cache), and 0x400 is not a multiple of the 2 KiB cache size so it cannot conflict with address 0. The new expectations are not derived from RTL output: write-allocate store miss = 1 fill, and the conflict distance equals the cache size. The independent Python model (`tests/cache_model.py`, `tests/dcache_test.py`) checks the same rules with exact counts. No other test in the file was touched.
- New sha256: 7bed0fdd088e7308cd809c31acddddaa8e8c68efb43e41afc00133f86150b395

## CHG-011 2026-11-02 tests/subword_tests.py
- What changed: every program is prefixed with four `sw x0` that zero the data words 0 to 3; the model runs the same prefix.
- Why: with caches on the main memory is unified (T2.1) and holds the program image at word 0, so the words these tests merge sub-word stores into start as instructions, not zero. The tests assumed a separate zero-initialized data memory.
- Evidence the original was wrong: with the unified memory the unchanged test reported `mem[0]=0x80f1f0b7 expected 0x0` (the first instruction word) in 10 of 11 programs at `CACHES=1`; the RTL is correct (a store merges into whatever is there). The prefix only fixes the starting state; expected values still come from tests/refmodel.py.
- New sha256: 052a0f9c2192fed20655a54c4dd99d9ca1c653befd62c0330f1c0a2c0260bc09

## CHG-012 2026-11-02 tests/mutants/core_mutants.py
- What changed: the patch text of C1_valid_not_reset, C2_icache_fill_live_addr, C5_store_hit_no_line_update and C7_reversed_lane_order. The mutations are unchanged: I$ valid not cleared at reset; I$ refill written under the live address; store hit not updating the line; I$ word lanes reversed.
- Why: T2.3/T2.4 rewrote `icache.sv` and `dcache.sv` (parameterized geometry, write-back D$), so the old patch text no longer occurs in them.
- Evidence the original was wrong: not a correction. The old patch text matches 0 times in the rewritten files (checked by script; `run_mutants.py` reports PATCH_FAILED rather than apply it). Each new patch text occurs exactly once (script check) and no mutant was removed or loosened: the mutant count is unchanged.
- New sha256: 1eaa0dd09cf51e4fbe6fd6ce88baa45ced44d168d6e42061f3fe36098e40df00

## CHG-013 2026-11-02 tests/mutants/toolchain_mutants.py
- What changed: mutant T2 now patches `mem_model.sv` (the unified memory) instead of the removed `backing_mem.sv`; same mutation: a 256 KiB memory never loads the image.
- Why: T2.1 replaced `backing_mem` by `mem_model`.
- Evidence the original was wrong: `rtl/backing_mem.sv` no longer exists. Not a loosening: same mutation, same detecting test (`tests/toolchain_test.py`, caches on).
- New sha256: 3c5f5a7078dbe3c73ac30cf16fe6cdfe496a2911b0a0fa80b4e49bcd25087af1

## CHG-014 2026-11-02 tests/run_mutants.py
- What changed: imports `tests/mutants/dcache_mutants.py` (12 new D$ mutants) and runs the quick D$ unit test (`tests/dcache_test.py`, 6 configurations) at the end of the suite.
- Why: T2.4 adds the D$ mutants and its test. Adds only; nothing removed or loosened.
- Evidence the original was wrong: not a correction; the earlier mutants are still applied and detected by the earlier tests of the suite.
- New sha256: a5007444f4adb1dd970fbaf25b8b630fc3ff599e98346a7d1af17b3e3647dd01

## CHG-015 2026-11-02 tests/random_gen.py, tests/random_lockstep.py, tests/random_spike_check.py
- What changed: the random programs' data window moved from "0x800" to a real 0x1000 (`DATA_BASE`; x31 is set with `lui x31,1`), the window is 0x1000..0x17FF, and the memory size used by the lockstep (2048 words) and the Spike cross-check's model (8192 bytes) grew to hold it.
- Why: a generator bug found in T2. `addi x31,x31,0x800` encodes -2048, so every random program since T1.6 accessed its window at 0xFFFFF800, reaching memory only through address wrap-around. With caches off the model and the RTL both wrapped, so the test passed; with caches on the cache tags saw the true address 0xFFFFF800 and the lockstep's debug read at 0x800 missed the lines.
- Evidence the original was wrong: with the T2 D$ the unchanged generator failed 0/20 seeds at every latency with caches on (`mem[0x864]=0x0 expected 0xa000`, all registers equal), while `peek_data` held the right value 0xa000 and the stored tag was 0x1fffff (address bits [31:11] all ones). The new window address needs no wrap-around.
- New sha256: random_gen.py c8c841101e19262a3203eafab58ff637af3a895361111a38c1853573c8339e37; random_lockstep.py ae5d46d0490c5b836499f500002aba71f458f2e7f78c26b832b77d5e19f34ba6; random_spike_check.py 5a64534aad251f86c9618292f2536e551d23ec9d1546c3119c0e29e30bb335f9

## CHG-016 2026-11-02 tests/run_mutants.py
- What changed: imports `tests/mutants/stall_mutants.py` (4 new mutants of the stall enables) and runs the stall-injection test (60 random programs) in the suite.
- Why: T2.2 adds them. Adds only; nothing removed or loosened.
- Evidence the original was wrong: not a correction; earlier mutants unchanged.
- New sha256: 3c08ef2acd50d628be82a4cddcaef875eaee78a3300b8a79dd9cdb3eef8fd5fa
