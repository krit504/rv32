# Memory model

**What it is**

`rtl/mem_model.sv` is a simulation-only unified main memory behind the two caches. One array (default 65536 words, 256 KiB) is zero-filled and then loaded from `INIT_FILE`. It has two ports, I$ read-only and D$ with line writes and byte enables, with one request in flight and D$ priority, non-preemptive. Latency is fixed (`LATENCY`) or, with `RANDOM_LATENCY`, drawn per request uniformly from 1 to 2L-1 by a seeded 16-bit LFSR. Line size is 16, 32 or 64 bytes.

Protocol: the master holds `valid` until `done`; `ready` pulses at acceptance; `done` is a one-cycle pulse L cycles after acceptance; a write takes effect at the edge ending the `done` cycle.

**Why it is built this way**

DEC-004 in `docs/DECISIONS.md` replaced the old two-memory `backing_mem` with this single memory and an arbiter, as the spec requires. The handshake keeps the earlier `backing_mem` timing. Random latency exists because the spec asks for latency tests beyond the fixed 20 cycles. A bypassed store uses only the store's byte enables inside a line image.

**How it is verified**

`tests/mem_model_test.py` (testbench `tb/tb_mem_model.sv`) passes 18/18: line sizes 16/32/64 times latency 1/2/3/10 fixed, plus random latency (LATENCY 5 and 10, two seeds) with a determinism check and a seed-dependence check. It checks exact latency, line packing, byte-enable writes, read-after-write, D$ priority and the I$ served right after, `done` as a one-cycle pulse, `INIT_FILE` words at address 0 and zero fill past the image. `tests/mutants/mem_mutants.py` has 6 mutants (off-by-one latency, swapped priority, ignored byte enables, reversed lanes, unbounded random latency, writes lost), all caught (`docs/logs/T2.1.md`).

**Known limits**

It is not synthesizable and not part of the T6.5 cost study. No misaligned or sub-line requests (addresses are rounded down to the line) and no error responses. Addresses wrap modulo the memory size. Two testbench bugs found along the way were SystemVerilog initializer traps, not memory faults.
