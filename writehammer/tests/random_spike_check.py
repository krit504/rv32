"""random_spike_check.py: cross-check the reference model against Spike on random programs (T1.6).

Usage:   python3 tests/random_spike_check.py [--n N] [--start S]
Why:     random_lockstep.py trusts tests/refmodel.py as its oracle. This script checks the model
         itself against an independently written simulator (Spike) on the same programs.
Start state: Spike's boot ROM leaves x11 = device-tree pointer and clobbers x5, so the Spike build zeroes
         x1..x29 first (the RTL and the model start with all registers 0).
Method:  generate PC-independent programs (random_gen with pc_free=True: no pc-dependent value
         reaches a general register, so results do not depend on the load address), assemble the
         instruction words into an ELF linked at 0x80000000, run it on Spike (--isa=rv32i --priv=m),
         and compare Spike's signature (x1..x29 stored by an epilogue, then the 2 KiB data window,
         which starts zeroed as in the RTL tests) with the model's final registers and window.
Output:  FAIL lines per mismatching seed, then "[random_spike_check ...] n/n passed"; exit 0 only if
         all match. Default 200 programs, seeds 1..200.
"""
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from paths import work_dir
from random_gen import gen, DATA_BASE, WINDOW_BYTES
from refmodel import run as model_run

WIN_WORDS = WINDOW_BYTES // 4
GCC = "riscv64-unknown-elf-gcc"
LD = """OUTPUT_ARCH(riscv)
ENTRY(_start)
SECTIONS { . = 0x80000000; .text : { *(.text.init) *(.text) } . = ALIGN(0x1000);
           .tohost : { *(.tohost) } . = ALIGN(0x1000); .data : { *(.data) } }
"""


def build_and_run(seed):
    p = gen(seed, pc_free=True)
    d = work_dir(f"random_spike/s{seed}")
    # Spike's boot ROM leaves a1 (x11) = device-tree pointer and clobbers t0 (x5); the RTL and the
    # model start with every register 0, so zero x1..x29 first (pc-independent: only affects values)
    lines = ["    .section .text.init, \"ax\"", "    .globl _start", "_start:"]
    lines += [f"    addi  x{r}, x0, 0" for r in range(1, 30)]
    lines += ["    lui   x31, %hi(win)", "    addi  x31, x31, %lo(win)"]       # same two-instruction shape as the RTL prologue
    lines += [f"    .word 0x{w & 0xFFFFFFFF:08x}" for w in p.prologue_tail + p.body]
    lines += ["    lui   x30, %hi(regs_sig)", "    addi  x30, x30, %lo(regs_sig)"]
    lines += [f"    sw    x{r}, {4 * (r - 1)}(x30)" for r in range(1, 30)]
    lines += ["    lui   x30, %hi(tohost)", "    addi  x30, x30, %lo(tohost)", "    li    x29, 1", "    sw    x29, 0(x30)",
              "1:  j     1b", "    .section .tohost, \"aw\", @progbits", "    .align 6",
              "    .globl tohost", "tohost: .dword 0", "    .globl fromhost", "fromhost: .dword 0",
              "    .data", "    .align 4", "    .globl begin_signature", "begin_signature:",
              "regs_sig: .fill 29, 4, 0xdeadbeef", f"win: .fill {WIN_WORDS}, 4, 0", "    .globl end_signature", "end_signature:"]
    s, ld, elf, sig = (os.path.join(d, x) for x in ("t.S", "l.ld", "t.elf", "t.sig"))
    open(s, "w").write("\n".join(lines) + "\n")
    open(ld, "w").write(LD)
    r = subprocess.run([GCC, "-march=rv32i_zicsr", "-mabi=ilp32", "-nostdlib", "-nostartfiles", "-static",
                        "-T", ld, s, "-o", elf], capture_output=True, text=True)
    if r.returncode:
        return seed, f"assemble failed: {r.stderr[-200:]}"
    r = subprocess.run(["spike", "--isa=rv32i", "--priv=m", f"+signature={sig}", "+signature-granularity=4", elf],
                       capture_output=True, text=True, timeout=60)
    if r.returncode or not os.path.exists(sig):
        return seed, f"spike failed rc={r.returncode}: {r.stderr[-200:]}"
    words = [int(x, 16) for x in open(sig).read().split()]
    if len(words) != 29 + WIN_WORDS:
        return seed, f"signature has {len(words)} words, expected {29 + WIN_WORDS}"
    prog = p.prologue_rtl + p.body
    regs, mem = model_run(prog, mem_bytes=8192)
    bad = [f"x{r}: spike {words[r - 1]:#x} model {regs[r]:#x}" for r in range(1, 30) if words[r - 1] != regs[r]]
    for i in range(WIN_WORDS):
        m = int.from_bytes(mem[DATA_BASE + 4 * i:DATA_BASE + 4 * i + 4], "little")
        if words[29 + i] != m:
            bad.append(f"window word {i}: spike {words[29 + i]:#x} model {m:#x}")
    return seed, (f"{len(bad)} mismatches, first: {bad[0]}" if bad else None)


def main():
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 200
    start = int(sys.argv[sys.argv.index("--start") + 1]) if "--start" in sys.argv else 1
    with ThreadPoolExecutor(max_workers=int(os.environ.get("JOBS", "12"))) as ex:
        res = list(ex.map(build_and_run, range(start, start + n)))
    fails = [(s, e) for s, e in res if e]
    for s, e in fails:
        print(f"FAIL seed {s}: {e}")
    print(f"[random_spike_check seeds={start}..{start + n - 1}] {n - len(fails)}/{n} passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
