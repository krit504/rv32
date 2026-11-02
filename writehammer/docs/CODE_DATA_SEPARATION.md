# Code and data separation (T2.5)

The cache system assumes that **code and data regions are disjoint** and that **self-modifying code and `fence.i` are unsupported**.

## Why
- The I$ is read-only and never snoops the D$. The D$ is write-back, so a store can sit dirty in the D$ for a long time and reach main memory only when the line is evicted.
- If a program stored into a region it also executes from, an instruction fetched after the store could come from main memory (stale), from an I$ line filled earlier (stale), or from a block that a D$ write-back had just changed. Making that correct would need coherence between the two caches or `fence.i`, which are outside this study (spec Section 2 and T2.5).

## How it is enforced
- **Linker script** (`sw/link.ld`): `.text` and `.rodata` start the image; `.data` starts on a fresh 4 KiB page after them (`ALIGN(4096)`), `.bss` follows, and the stack occupies the top 16 KiB of the 256 KiB address space. An `ASSERT` fails the link if the image overlaps the stack. No cache line (16-64 bytes) can hold both code and data, because the regions are separated by at least a page boundary.
- **Program convention**: programs never write to `.text` or `.rodata`. The benchmark builds are plain C compiled and linked this way. `sw/build.py` rejects any instruction that is not RV32I base (so no `fence.i`).
- **Memory model**: the unified `mem_model` holds the whole image, so a stray store to code would be visible to a later I$ refill; the tests below show where the regions meet and that they do not.

## What the tests rely on and what they do not
- The architectural tests (`tests/arch_test.py`), random programs (`tests/random_lockstep.py`: code below 0x800, data window at 0x800) and the C builds keep code and data apart.
- Several older directed tests (`tests/hazard_tests.py`, `tests/cache_integration.py`, `tests/perf_tests.py`) deliberately use data addresses near 0, inside the region where their own few instructions sit. They only store a word before loading it, they never refetch an instruction after a store to its word, and they finish long before any eviction could write back into code, so they remain valid in the unified memory. `tests/subword_tests.py` therefore zeroes the four words it merges into before using them (CHG-011), because with caches on those words initially hold instructions. This is a property of those tests, not of the design: nothing in the hardware would make a program that stores into its own code correct.

## Known limits
- A program that does store into its code region, or loads code that was just written (JIT, self-relocation), is unsupported and may execute stale instructions with caches on (KI-004 and this note). With caches off the instruction and data memories are separate arrays, so such a program fails differently.
- `fence.i` is not implemented.
