"""subword_tests.py: directed tests for lb, lbu, lh, lhu, sb, sh (T1.2).

Inputs: none (programs built with asm.py). Env CACHES=1 LAT=n runs through the caches.
Output: one PASS/FAIL line per test, then "[subword] n/n passed"; exit 0 only if all pass.
Expected values: from tests/refmodel.py, an independent ISS written from the ISA spec; the model
is itself checked by hand-computed cases in tests/refmodel_selftest.py. Never from RTL output.
Checks: all 31 registers and the first four data-memory words after the program.
Does not check: timing, misaligned accesses (unsupported, KI-004).
Tests: each load at every legal offset with sign-bit-set and clear data; each store at every
legal offset; adjacent byte stores into one word; a loaded sub-word forwarded to the next
instruction and across one instruction; load-use stall with each sub-word load; forwarding of
the store data into sb/sh.
"""
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from asm import *   # noqa: F401,F403  (encoders)
from paths import CORE_RTL, TB, work_dir
from refmodel import run as model_run

CACHES = int(os.environ.get("CACHES", "0"))
LAT = int(os.environ.get("LAT", "2"))
HALT = jal(0, 0)


def li(rd, value):
    """lui+addi pair loading a 32-bit constant (addi immediate is signed, so compensate)."""
    lo = ((value & 0xFFF) ^ 0x800) - 0x800
    return [lui(rd, ((value - lo) >> 12) & 0xFFFFF), addi(rd, rd, lo)]


def rtl_run(name, prog):
    d = work_dir(f"subword_c{CACHES}_l{LAT}/{name}")
    full = prog + [HALT] if CACHES else prog
    with open(os.path.join(d, "program.hex"), "w") as f:
        f.write("".join(f"{w & M32:08x}\n" for w in full + [NOP] * (256 - len(full))))
    params = [f"-Ptb_hazard.CACHES={CACHES}", f"-Ptb_hazard.LAT={LAT}",
              f"-Ptb_hazard.CYCLES={300 + 40 * (LAT + 2) if CACHES else 200}"]
    subprocess.run(["iverilog", "-g2012", "-o", os.path.join(d, "sw.vvp"), *params]
                   + CORE_RTL + [os.path.join(TB, "perf_counters.sv"), os.path.join(TB, "tb_hazard.sv")],
                   check=True, capture_output=True)
    out = subprocess.run(["vvp", "sw.vvp"], cwd=d, capture_output=True, text=True).stdout
    regs, mem = {0: 0}, {}
    for ln in out.splitlines():
        if m := re.match(r"REG (\d+) (\w+)", ln): regs[int(m.group(1))] = int(m.group(2), 16) if "x" not in m.group(2) else None
        if m := re.match(r"MEM (\d+) (\w+)", ln): mem[int(m.group(1))] = int(m.group(2), 16) if "x" not in m.group(2) else None
    return regs, mem


A, B = 0x80F1F2A3, 0x7FFF807F        # data words: sign bits set / clear in different lanes
T = {}
T["loads_all_offsets"] = li(1, A) + li(2, B) + [sw(1, 0, 0), sw(2, 4, 0)] + [
    lb(3, 0, 0), lb(4, 1, 0), lb(5, 2, 0), lb(6, 3, 0), lb(7, 4, 0), lb(8, 5, 0), lb(9, 6, 0), lb(10, 7, 0),
    lbu(11, 0, 0), lbu(12, 1, 0), lbu(13, 2, 0), lbu(14, 3, 0), lbu(15, 4, 0), lbu(16, 5, 0), lbu(17, 6, 0), lbu(18, 7, 0),
    lh(19, 0, 0), lh(20, 2, 0), lh(21, 4, 0), lh(22, 6, 0),
    lhu(23, 0, 0), lhu(24, 2, 0), lhu(25, 4, 0), lhu(26, 6, 0)]
T["stores_all_offsets"] = li(1, 0x11223344) + li(2, 0xAABBCCDD) + [sw(1, 0, 0), sw(1, 4, 0), sw(1, 8, 0), sw(1, 12, 0)] + [
    sb(2, 0, 0), sb(2, 5, 0), sb(2, 10, 0), sb(2, 15, 0), lw(3, 0, 0), lw(4, 4, 0), lw(5, 8, 0), lw(6, 12, 0)]
T["half_stores_all_offsets"] = li(1, 0x11223344) + li(2, 0xAABBCCDD) + [sw(1, 0, 0), sw(1, 4, 0)] + [
    sh(2, 0, 0), sh(2, 6, 0), lw(3, 0, 0), lw(4, 4, 0)]
T["adjacent_byte_stores"] = li(1, 0xFFFFFFFF) + [sw(1, 0, 0), addi(2, 0, 0x11), addi(3, 0, 0x22), addi(4, 0, 0x33), addi(5, 0, 0x44),
    sb(2, 0, 0), sb(3, 1, 0), sb(4, 2, 0), sb(5, 3, 0), lw(6, 0, 0)]
T["adjacent_half_stores"] = li(1, 0xFFFFFFFF) + li(2, 0x1234) + li(3, 0xABCD) + [sw(1, 0, 0), sh(2, 0, 0), sh(3, 2, 0), lw(4, 0, 0)]
T["load_forward_to_next"] = li(1, A) + [sw(1, 0, 0), lb(2, 3, 0), add(3, 2, 2), lhu(4, 2, 0), add(5, 4, 4), lbu(6, 0, 0), addi(7, 6, 1)]
T["load_forward_gap1"] = li(1, A) + [sw(1, 0, 0), lb(2, 0, 0), addi(8, 0, 1), add(3, 2, 2), lh(4, 2, 0), addi(8, 0, 2), sub(5, 0, 4)]
T["loaduse_each_load"] = li(1, A) + [sw(1, 0, 0), lb(2, 0, 0), add(3, 2, 0), lbu(4, 3, 0), add(5, 4, 0),
    lh(6, 2, 0), add(7, 6, 0), lhu(8, 0, 0), add(9, 8, 0)]
T["store_data_forwarding"] = li(1, 0xFFFFFFFF) + [sw(1, 0, 0), addi(5, 0, 0x1AB), sb(5, 1, 0), addi(6, 0, 0x7C3), sh(6, 2, 0), lw(7, 0, 0)]
T["store_then_load_same_byte"] = li(1, 0x11223344) + [sw(1, 0, 0), addi(2, 0, -2), sb(2, 2, 0), lb(3, 2, 0), lbu(4, 2, 0),
    sh(2, 0, 0), lh(5, 0, 0), lhu(6, 0, 0)]
T["subword_with_negative_base"] = li(1, A) + [addi(9, 0, 8), sw(1, 0, 9), addi(10, 9, 4), lb(2, -4, 10), lbu(3, -3, 10), lh(4, -2, 10), sb(0, -4, 10), lw(5, 0, 9)]


# The unified memory (caches on) holds the program image at word 0, so the data words these tests use start
# as code, not zero. Every program first zeroes the four words it works in; the model runs the same code.
ZERO_DATA = [sw(0, 0, 0), sw(0, 4, 0), sw(0, 8, 0), sw(0, 12, 0)]


def check(item):
    name, prog = item
    prog = ZERO_DATA + prog
    regs, mem = rtl_run(name, prog)
    mregs, mmem = model_run(prog)
    errs = []
    for r in range(1, 32):
        if regs.get(r) != mregs[r]:
            errs.append(f"x{r}={regs.get(r) if regs.get(r) is None else hex(regs[r])} expected {mregs[r]:#x}")
    for w in range(4):
        exp = int.from_bytes(mmem[4 * w:4 * w + 4], "little")
        if mem.get(w) != exp:
            errs.append(f"mem[{w}]={mem.get(w) if mem.get(w) is None else hex(mem[w])} expected {exp:#x}")
    return name, errs


with ThreadPoolExecutor(max_workers=int(os.environ.get("JOBS", "8"))) as ex:
    results = list(ex.map(check, T.items()))
fails = 0
for name, errs in results:
    fails += bool(errs)
    print(("PASS  " if not errs else "FAIL  ") + name + ("" if not errs else "\n        <- " + "; ".join(errs[:6])))
print(f"[subword CACHES={CACHES} LAT={LAT}] {len(T) - fails}/{len(T)} passed")
sys.exit(1 if fails else 0)
