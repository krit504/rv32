# KNOWN ISSUES

Every known bug, limitation, lint waiver and unverified area (spec 0B.10). Lint waivers are listed with their root cause; blanket waivers are not allowed.

| ID | Kind | Where | Description and root cause | Status |
|---|---|---|---|---|
| KI-001 | lint waiver (`UNUSEDSIGNAL`) | `rtl/icache.sv`, `addr` port | `addr[1:0]` is never used: fetch addresses are word-aligned (RV32I, no compressed instructions). The port stays 32 bits because it carries `PCF` unchanged. | open (permanent unless the C extension is added) |
| KI-002 | lint waiver (`UNUSEDSIGNAL`) | `rtl/dcache.sv`, `addr` port | `addr[1:0]` unused while the D$ handles word accesses only. Byte enables in T2.4 use these bits. | open until T2.4 |
| KI-003 | lint waiver (`UNUSEDSIGNAL`) | `rtl/backing_mem.sv`, `addr` port | Address bits above the array and below the word are unused: addresses wrap, the same as the original `imem`/`dmem`. `backing_mem` is replaced by `mem_model` in T2.1. | open until T2.1 |
| KI-004 | limitation | `rtl/rv32_top_pipelined.sv` Memory stage | Misaligned loads and stores are unsupported: the store lane logic and load extender assume natural alignment (`lh`/`lhu`/`sh` at even addresses, `lw`/`sw` at multiples of 4). No exception is raised; the access silently reads or writes the wrong lanes. The arch-test subset excludes misalignment tests (T1.5). The reference model raises on a misaligned access, so tests never generate one. | open |
| KI-005 | limitation | MMIO window | Only stores are decoded. A load from `0xF000_0xxx` goes to the data memory or D$ and returns whatever is at that wrapped address. Programs must not read MMIO. | open |
| KI-006 | limitation | `tb/sys_monitor.sv` | Counter window boundary: a stall or redirect whose signal is high in or before the START store's Memory cycle is not counted, though its bubbles fall inside the window (at most 2 events per window). Negligible for runs of thousands of cycles; tests avoid it by padding. | open |
| KI-007 | limitation | `rtl/rv32_top_pipelined.sv` memories | Until T2.1 the instruction and data memories are separate, and with `DMEM_FROM_IMAGE=1` each holds a full copy of the linked image. Programs must not write code memory (the linker script keeps code and data on disjoint pages) and stores never become visible to instruction fetch. Replaced by the unified `mem_model` in T2.1. | open until T2.1 |
