"""random_lockstep.py: random hazard-dense programs, RTL vs reference model, lockstep on results (T1.6).

Usage:   python3 tests/random_lockstep.py [--n N] [--start S] [--pc-free]
Env:     CACHES=1 LAT=n (caches on), FWD=0 (no-forwarding ablation), JOBS=n, MAXCYC=n
Inputs:  tests/random_gen.py (seed -> program), tests/refmodel.py (independent reference).
Output:  prints the exact seed range and configuration, one FAIL line per mismatching seed, then
         "[random ...] n/n passed"; exit 0 only if every program matches.
Default: 1000 programs, seeds 1..1000 (the spec's minimum per run). Failing seeds can be replayed
         with --start SEED --n 1.
Checks:  after the program halts, registers x1..x29 and the whole 2 KiB data window must equal the
         model's. x30 (jalr scratch) and x31 (window base) are not general registers.
         A timeout or a missing dump is a failure, never a pass.
Does not check: timing (cycle counts differ with caches, by design).
"""
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from asm import sw, lui, M32
from paths import CORE_RTL, TB, work_dir
from random_gen import gen, DATA_BASE, WINDOW_BYTES
from refmodel import run as model_run

CACHES = int(os.environ.get("CACHES", "0"))
LAT = int(os.environ.get("LAT", "2"))
FWD = int(os.environ.get("FWD", "1"))
MAXCYC = int(os.environ.get("MAXCYC", "100000"))
MEMW = 1024
WIN_W0, WIN_W1 = DATA_BASE // 4, (DATA_BASE + WINDOW_BYTES) // 4
HALT_EPILOGUE = [lui(30, 0xF0000), sw(0, 0, 30)]       # x30 = MMIO base; HALT with exit code 0
CFG = f"c{CACHES}_l{LAT}_f{FWD}"


def compile_tb():
    d = work_dir(f"random/{CFG}")
    subprocess.run(["iverilog", "-g2012", "-o", os.path.join(d, "r.vvp"),
                    f"-Ptb_random.CACHES={CACHES}", f"-Ptb_random.LAT={LAT}", f"-Ptb_random.FWD={FWD}",
                    f"-Ptb_random.MEMW={MEMW}", f"-Ptb_random.WIN_BEGIN_W={WIN_W0}",
                    f"-Ptb_random.WIN_END_W={WIN_W1}", f"-Ptb_random.MAXCYC={MAXCYC}"] + CORE_RTL
                   + [os.path.join(TB, "sys_monitor.sv"), os.path.join(TB, "tb_random.sv")],
                   check=True, capture_output=True)
    return d


def check(args):
    seed, pc_free, base = args
    p = gen(seed, pc_free)
    prog = p.prologue_rtl + p.body
    d = os.path.join(base, f"s{seed}")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "program.hex"), "w") as f:
        f.write("".join(f"{w & M32:08x}\n" for w in prog + HALT_EPILOGUE))
    out = subprocess.run(["vvp", os.path.join(base, "r.vvp")], cwd=d, capture_output=True, text=True).stdout
    if "TIMEOUT" in out:
        return seed, "RTL run timed out"
    regs = {int(m.group(1)): int(m.group(2), 16) for m in re.finditer(r"^REG (\d+) ([0-9a-f]+)$", out, re.M)}
    win = {int(m.group(1)): int(m.group(2), 16) for m in re.finditer(r"^WIN (\d+) ([0-9a-f]+)$", out, re.M)}
    if len(regs) != 31 or len(win) != WIN_W1 - WIN_W0:
        return seed, f"incomplete dump (regs {len(regs)}, window words {len(win)}): no HALT?"
    mregs, mmem = model_run(prog, mem_bytes=4 * MEMW)
    bad = [f"x{r}={regs[r]:#x} expected {mregs[r]:#x}" for r in range(1, 30) if regs[r] != mregs[r]]
    for w in range(WIN_W0, WIN_W1):
        exp = int.from_bytes(mmem[4 * w:4 * w + 4], "little")
        if win[w] != exp:
            bad.append(f"mem[{4 * w:#x}]={win[w]:#x} expected {exp:#x}")
    if bad:
        return seed, f"{len(bad)} mismatches, first: {bad[0]}"
    return seed, None


def main():
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 1000
    start = int(sys.argv[sys.argv.index("--start") + 1]) if "--start" in sys.argv else 1
    pc_free = "--pc-free" in sys.argv
    base = compile_tb()
    jobs = [(s, pc_free, base) for s in range(start, start + n)]
    with ThreadPoolExecutor(max_workers=int(os.environ.get("JOBS", "12"))) as ex:
        res = list(ex.map(check, jobs))
    fails = [(s, e) for s, e in res if e]
    for s, e in fails:
        print(f"FAIL seed {s}: {e}")
    tag = f"CACHES={CACHES} LAT={LAT} FWD={FWD} pc_free={int(pc_free)} seeds={start}..{start + n - 1}"
    print(f"[random {tag}] {n - len(fails)}/{n} passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
