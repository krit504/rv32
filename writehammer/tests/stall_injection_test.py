"""stall_injection_test.py: random stalls must not change any architectural result (T2.2).

Usage:   python3 tests/stall_injection_test.py
Mechanism: the top has a test-only parameter INJECT_STALL_SEED. When non-zero, two seeded LFSRs add
random pipeline-wide freezes (OR-ed into dmiss, so every register holds, as in a D$ miss) and random
fetch bubbles (OR-ed into imiss, so pc holds and F/D takes a bubble, as in an I$ miss) at random
cycles, about one cycle in four for each. With the parameter 0 (the default) no injection logic
exists.
Checks, against the independent reference model (tests/refmodel.py), never the RTL's own output:
  - 1000 hazard-dense random programs (tests/random_gen.py, seeds 1..1000), final x1..x29 and the whole
    data window, with injection seeds 3 and 11, caches off and caches on at LAT 3;
  - the 27-instruction no-hazard regression's 21 register checks (tests/nohazard_test.py's testbench)
    with injection, caches off and on.
  - a control: with injection the cycle count must actually change (the injector really stalls),
    otherwise the test would pass trivially.
Output: PASS/FAIL lines and "[stall_injection] n/n passed"; exit 0 only if all pass.
"""
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from asm import sw, lui, M32
from paths import CORE_RTL, TB, TESTS, work_dir
from random_gen import gen, DATA_BASE, WINDOW_BYTES
from refmodel import run as model_run

MEMW = 2048
WIN_W0, WIN_W1 = DATA_BASE // 4, (DATA_BASE + WINDOW_BYTES) // 4
HALT_EPILOGUE = [lui(30, 0xF0000), sw(0, 0, 30)]
N = int(os.environ.get("N", "1000"))
CFGS = [(0, 2, 3), (0, 2, 11), (1, 3, 3), (1, 3, 11)]       # (caches, lat, injection seed)
fails, total = [], 0


def compile_random(caches, lat, seed):
    d = work_dir(f"stall_inj/random_c{caches}_l{lat}_i{seed}")
    subprocess.run(["iverilog", "-g2012", "-o", os.path.join(d, "r.vvp"), f"-Ptb_random.CACHES={caches}",
                    f"-Ptb_random.LAT={lat}", f"-Ptb_random.MEMW={MEMW}", f"-Ptb_random.WIN_BEGIN_W={WIN_W0}",
                    f"-Ptb_random.WIN_END_W={WIN_W1}", f"-Ptb_random.MAXCYC=400000", f"-Ptb_random.INJECT={seed}"]
                   + CORE_RTL + [os.path.join(TB, "sys_monitor.sv"), os.path.join(TB, "tb_random.sv")],
                   check=True, capture_output=True)
    return d


def one(args):
    seed, base = args
    p = gen(seed)
    prog = p.prologue_rtl + p.body
    d = os.path.join(base, f"s{seed}")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "program.hex"), "w").write("".join(f"{w & M32:08x}\n" for w in prog + HALT_EPILOGUE))
    out = subprocess.run(["vvp", os.path.join(base, "r.vvp")], cwd=d, capture_output=True, text=True).stdout
    if "TIMEOUT" in out:
        return seed, "timeout"
    regs = {int(m.group(1)): int(m.group(2), 16) for m in re.finditer(r"^REG (\d+) ([0-9a-f]+)$", out, re.M)}
    win = {int(m.group(1)): int(m.group(2), 16) for m in re.finditer(r"^WIN (\d+) ([0-9a-f]+)$", out, re.M)}
    if len(regs) != 31 or len(win) != WIN_W1 - WIN_W0:
        return seed, "incomplete dump"
    mregs, mmem = model_run(prog, mem_bytes=4 * MEMW)
    bad = [f"x{r}" for r in range(1, 30) if regs[r] != mregs[r]]
    bad += [f"mem[{4 * w:#x}]" for w in range(WIN_W0, WIN_W1) if win[w] != int.from_bytes(mmem[4 * w:4 * w + 4], "little")]
    return seed, (f"{len(bad)} mismatches, first {bad[0]}" if bad else None)


# 1. random programs
for caches, lat, inj in CFGS:
    base = compile_random(caches, lat, inj)
    with ThreadPoolExecutor(max_workers=int(os.environ.get("JOBS", "12"))) as ex:
        res = list(ex.map(one, [(s, base) for s in range(1, N + 1)]))
    bad = [(s, e) for s, e in res if e]
    total += 1
    print(f"{'PASS' if not bad else 'FAIL'}  random programs caches={caches} lat={lat} inject_seed={inj}: {N - len(bad)}/{N}"
          + ("" if not bad else f"  first: seed {bad[0][0]} {bad[0][1]}"))
    if bad:
        fails.append(f"random c{caches} i{inj}")

# 2. the no-hazard regression with injection
for caches, lat, inj in ((0, 2, 5), (1, 3, 5)):
    d = work_dir(f"stall_inj/nohazard_c{caches}_i{inj}")
    # the golden program followed by `jal x0, 0`: with stalls injected the run is long enough for pc to run off
    # the end and wrap the 1 KiB memory, re-executing the program (an `auipc` would then give a second,
    # different value); parked on the loop the cycle budget does not matter
    words = open(os.path.join(TESTS, "golden", "nohazard_program.hex")).read().split()
    open(os.path.join(d, "program.hex"), "w").write("\n".join(words + ["0000006f"]) + "\n")
    cycles = 60 if not caches else 220
    subprocess.run(["iverilog", "-g2012", "-o", os.path.join(d, "n.vvp"), f"-Ptb_rv32_top_pipelined.CACHES={caches}",
                    f"-Ptb_rv32_top_pipelined.LAT={lat}", f"-Ptb_rv32_top_pipelined.CYCLES={cycles * 4}",
                    f"-Ptb_rv32_top_pipelined.INJECT={inj}"] + CORE_RTL + [os.path.join(TB, "tb_rv32i_pipelined.sv")],
                   check=True, capture_output=True)
    out = subprocess.run(["vvp", "n.vvp"], cwd=d, capture_output=True, text=True).stdout
    m = re.search(r"(\d+) PASS, (\d+) FAIL", out)
    ok = bool(m) and m.group(1) == "21" and m.group(2) == "0"
    total += 1
    print(f"{'PASS' if ok else 'FAIL'}  no-hazard regression caches={caches} inject_seed={inj}: {m.group(0) if m else 'no result'}")
    if not ok:
        fails.append(f"nohazard c{caches}")

# 3. control: injection really stalls (cycle count with injection > without), measured with tb_prog's monitor
sys.path.insert(0, TESTS)
from prog_runner import parse_output
from asm import addi, NOP
prog = [lui(1, 0xF0000), addi(2, 0, 1), sw(2, 4, 1)] + [addi(3, 3, 1)] * 40 + [sw(2, 8, 1), addi(6, 0, 0), sw(6, 0, 1)]
cyc = {}
for inj in (0, 7):
    d = work_dir(f"stall_inj/control_i{inj}")
    open(os.path.join(d, "program.hex"), "w").write("".join(f"{w & M32:08x}\n" for w in prog + [NOP] * (256 - len(prog))))
    subprocess.run(["iverilog", "-g2012", "-o", os.path.join(d, "c.vvp"), f"-Ptb_prog.INJECT={inj}"] + CORE_RTL
                   + [os.path.join(TB, "sys_monitor.sv"), os.path.join(TB, "tb_prog.sv")], check=True, capture_output=True)
    r = parse_output(subprocess.run(["vvp", "c.vvp"], cwd=d, capture_output=True, text=True).stdout)
    cyc[inj] = r["perf"]["cycles"] if r["perf"] else None
total += 1
ok = cyc[0] is not None and cyc[7] is not None and cyc[7] > cyc[0]
print(f"{'PASS' if ok else 'FAIL'}  control: window cycles without injection {cyc[0]}, with injection {cyc[7]} (must be larger)")
if not ok:
    fails.append("control: injection does not stall")

for f in fails:
    print("FAIL " + f)
print(f"[stall_injection] {total - len(fails)}/{total} passed")
sys.exit(1 if fails else 0)
