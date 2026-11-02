"""cache_integration.py: cache-specific integration tests (cache datasheet section 11, step 4).

Inputs: none (programs are built here with asm.py). Runs each program at memory latency 1, 2, 3, 10.
Output: one FAIL line per mismatch, then "FAILS n"; exit 0 only if n == 0.
Usage: python3 tests/cache_integration.py
Checks: final registers, data-memory words, I$/D$ refill counts, D$ write count, and the imiss
pattern of the first fetches after reset (LAT+2 misses, 4 hits, LAT+2 misses).
Does not check: cycle counts of whole programs.

Expected values come from the ISA semantics of each program and the cache datasheet:
- "loop fits in cache": the loop and its final jal sit in block 0. Fetch also runs one block past
  the final `jal x0, 0` before the redirect lands (datasheet section 9, "a wrong-path fetch after
  a taken branch can add a refill"), so I$ refills = 2. A refill per loop iteration would show more.
- store miss: no-write-allocate, so no refill; a later load of it refills once.
"""
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from asm import addi, add, lw, sw, beq, bne, lui, jal, NOP, M32
from paths import CORE_RTL, TB, work_dir

HALT = jal(0, 0)
hx = lambda v: f"{v & M32:08x}"


def run(name, prog, lat):
    d = work_dir(f"cache_int/{name}_l{lat}")
    words = prog + [NOP] * (256 - len(prog))
    with open(os.path.join(d, "prog.hex"), "w") as f:
        f.write("".join(f"{w & M32:08x}\n" for w in words))
    subprocess.run(["iverilog", "-g2012", f"-Ptb_cache_integration.LAT={lat}", "-o", os.path.join(d, "ci.vvp")]
                   + CORE_RTL + [os.path.join(TB, "tb_cache_integration.sv")],
                   check=True, capture_output=True)
    out = subprocess.run(["vvp", "ci.vvp"], cwd=d, capture_output=True, text=True).stdout
    o = {"regs": {0: hx(0)}, "mem": {}}
    for ln in out.splitlines():
        if m := re.match(r"REG (\d+) (\w+)", ln): o["regs"][int(m.group(1))] = m.group(2)
        if m := re.match(r"MEM (\d+) (\w+)", ln): o["mem"][int(m.group(1))] = m.group(2)
        if m := re.match(r"(IC_REFILL|DC_REFILL|DC_WRITE) (\d+)", ln): o[m.group(1)] = int(m.group(2))
        if ln.startswith("IMISS "): o["im"] = ln.split()[1]
    return o


TESTS = [
    ("loop_fits", [addi(1, 0, 5), addi(1, 1, -1), bne(1, 0, -4), HALT], {1: 0}, {}, {"IC_REFILL": 2}),
    ("store_miss_hit_load", [addi(5, 0, 7), sw(5, 0, 0), lw(6, 0, 0), addi(7, 0, 9), sw(7, 4, 0), lw(8, 4, 0), HALT],
     {6: 7, 8: 9}, {0: 7, 1: 9}, {"DC_REFILL": 1, "DC_WRITE": 2}),
    # write-allocate (spec T2.4, DEC-004): a store miss fills the line, then merges the store
    ("store_miss_allocates", [addi(5, 0, 7), sw(5, 0x80, 0), HALT], {}, {}, {"DC_REFILL": 1, "DC_WRITE": 1}),
    ("producer_loadmiss_consumer", [addi(4, 0, 3), addi(5, 0, 7), lw(6, 0, 0), add(7, 5, 4), HALT], {7: 10}, {}, {}),
    ("branch_uncached_block", [beq(0, 0, 64), addi(9, 0, 1), addi(10, 0, 1)] + [NOP] * 13 + [addi(11, 0, 5), HALT],
     {9: 0, 10: 0, 11: 5}, {}, {}),
    # 0x1000 is a multiple of the 2 KiB D$ size: same index as address 0, different tag, so they conflict
    ("addrs_cache_size_apart", [addi(1, 0, 0), lw(2, 0, 0), lui(3, 1), lw(4, 0, 3), lw(5, 0, 0), HALT],
     {}, {}, {"DC_REFILL": 3}),
    ("dmiss_taken_branch", [lw(2, 0, 0), beq(0, 0, 12), addi(5, 0, 1), addi(6, 0, 1), addi(7, 0, 3), HALT],
     {5: 0, 6: 0, 7: 3}, {}, {}),
    ("imiss_with_lwstall", [addi(1, 0, 9), sw(1, 0, 0), lw(5, 0, 0), add(6, 5, 5)] + [NOP] * 4 + [addi(7, 0, 1), HALT],
     {5: 9, 6: 18, 7: 1}, {}, {}),
]
FIRST_FETCH = [addi(1, 0, 1)] * 3 + [HALT] + [NOP] * 8 + [HALT]


def check(job):
    lat, name, prog, regs, mem, cnt = job
    o, e = run(name, prog, lat), []
    for r, v in regs.items():
        if o["regs"].get(r) != hx(v): e.append(f"x{r}={o['regs'].get(r)} exp {hx(v)}")
    for a, v in mem.items():
        if o["mem"].get(a) != hx(v): e.append(f"mem[{a}]={o['mem'].get(a)} exp {hx(v)}")
    for c, v in cnt.items():
        if o.get(c) != v: e.append(f"{c}={o.get(c)} exp {v}")
    if name == "first_fetch":
        exp = "1" * (lat + 2) + "0" * 4 + "1" * (lat + 2)
        if not o.get("im", "").startswith(exp): e.append(f"imiss {o.get('im', '')[:len(exp)]} exp {exp}")
    return [f"FAIL L={lat} {name}: " + "; ".join(e)] if e else []


jobs = [(lat, *t) for lat in (1, 2, 3, 10) for t in TESTS + [("first_fetch", FIRST_FETCH, {}, {}, {})]]
with ThreadPoolExecutor(max_workers=int(os.environ.get("JOBS", "8"))) as ex:
    fails = [ln for r in ex.map(check, jobs) for ln in r]
for ln in fails: print(ln)
print(f"[cache_integration] {len(jobs) - len(fails)}/{len(jobs)} passed")
print("FAILS", len(fails))
sys.exit(1 if fails else 0)
