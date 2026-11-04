"""core_only_test.py: the core-only top (CORE_ONLY = 1 and rtl/core_only.sv) runs programs correctly (T6.5 deliverable).

Usage:   python3 tests/core_only_test.py [--n N]
Runs N random hazard-dense programs (tests/random_gen.py, seeds 1..N, default 200) on the core with no caches and
an external memory driven through the ext_* ports, with random fetch and data stalls, and on the synthesis
wrapper rtl/core_only.sv in parallel. Registers x1..x29 and the data window must equal the independent reference
model (tests/refmodel.py), and the wrapper's registers and memory must equal the top's. Also runs a control: a
core whose data-stall input is ignored must fail (so the check is not vacuous).
Output: FAIL lines per seed, "[core_only] n/n passed"; exit 0 only if all pass.
"""
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from asm import sw, lui, M32
from paths import CORE_RTL, RTL, TB, work_dir
from random_gen import gen, DATA_BASE, WINDOW_BYTES
from refmodel import run as model_run

MEMW = 2048
WIN_W0, WIN_W1 = DATA_BASE // 4, (DATA_BASE + WINDOW_BYTES) // 4
HALT_EPILOGUE = [lui(30, 0xF0000), sw(0, 0, 30)]
SRCS = CORE_RTL + [os.path.join(RTL, "core_only.sv"), os.path.join(TB, "sys_monitor.sv"), os.path.join(TB, "tb_core_only.sv")]


def compile_tb(tag, extra_defs=()):
    d = work_dir(f"core_only/{tag}")
    subprocess.run(["iverilog", "-g2012", "-o", os.path.join(d, "c.vvp"), f"-Ptb_core_only.MEMW={MEMW}",
                    f"-Ptb_core_only.WIN_BEGIN_W={WIN_W0}", f"-Ptb_core_only.WIN_END_W={WIN_W1}", *extra_defs] + SRCS,
                   check=True, capture_output=True)
    return d


def check(args):
    seed, base = args
    p = gen(seed, False)
    prog = p.prologue_rtl + p.body
    d = os.path.join(base, f"s{seed}")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "program.hex"), "w") as f:
        f.write("".join(f"{w & M32:08x}\n" for w in prog + HALT_EPILOGUE))
    out = subprocess.run(["vvp", os.path.join(base, "c.vvp"), f"+SEED={seed}"], cwd=d, capture_output=True, text=True).stdout
    if "TIMEOUT" in out:
        return seed, "RTL run timed out"
    regs = {int(m.group(1)): int(m.group(2), 16) for m in re.finditer(r"^REG (\d+) ([0-9a-f]+)$", out, re.M)}
    win = {int(m.group(1)): int(m.group(2), 16) for m in re.finditer(r"^WIN (\d+) ([0-9a-f]+)$", out, re.M)}
    if len(regs) != 31 or len(win) != WIN_W1 - WIN_W0:
        return seed, "incomplete dump: no HALT?"
    if "WRAPPER_MATCH 1" not in out:
        return seed, "rtl/core_only.sv differs from the CORE_ONLY top"
    mregs, mmem = model_run(prog, mem_bytes=4 * MEMW)
    bad = [f"x{r}={regs[r]:#x} expected {mregs[r]:#x}" for r in range(1, 30) if regs[r] != mregs[r]]
    for w in range(WIN_W0, WIN_W1):
        exp = int.from_bytes(mmem[4 * w:4 * w + 4], "little")
        if win[w] != exp:
            bad.append(f"mem[{4 * w:#x}]={win[w]:#x} expected {exp:#x}")
    return seed, (f"{len(bad)} mismatches, first: {bad[0]}" if bad else None)


def run_all(base, n):
    with ThreadPoolExecutor(max_workers=int(os.environ.get("JOBS", "12"))) as ex:
        return list(ex.map(check, [(s, base) for s in range(1, n + 1)]))


def main():
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 200
    res = run_all(compile_tb("good"), n)
    fails = [(s, e) for s, e in res if e]
    for s, e in fails:
        print(f"FAIL seed {s}: {e}")
    # control: the core ignores the data-stall input; the testbench returns garbage while stalled, so it must fail
    bad_dir = work_dir("core_only/control_src")
    for f in os.listdir(RTL):
        if f.endswith(".sv"):
            open(os.path.join(bad_dir, f), "w").write(open(os.path.join(RTL, f)).read())
    top = os.path.join(bad_dir, "rv32_top_pipelined.sv")
    t = open(top).read()
    assert t.count("assign dmiss_c = ext_dmiss;") == 1
    open(top, "w").write(t.replace("assign dmiss_c = ext_dmiss;", "assign dmiss_c = 1'b0;"))
    global SRCS
    saved = SRCS
    SRCS = [os.path.join(bad_dir, os.path.basename(x)) if x.startswith(RTL) else x for x in saved]
    cres = run_all(compile_tb("control"), min(n, 60))
    SRCS = saved
    caught = sum(1 for _, e in cres if e)
    ctl_ok = caught > 0
    print(("PASS" if ctl_ok else "FAIL") + f"  control (core ignores d_stall): {caught}/{len(cres)} programs fail as required")
    print(f"[core_only] {n - len(fails)}/{n} passed" + ("" if ctl_ok else "  CONTROL DID NOT FAIL"))
    return 1 if fails or not ctl_ok else 0


if __name__ == "__main__":
    sys.exit(main())
