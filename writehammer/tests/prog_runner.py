"""prog_runner.py: run an assembled program on the core with the MMIO monitor (tb/tb_prog.sv).

Inputs: a list of 32-bit instruction words. Output: a dict with keys regs (x1..x31), mem (first
four data words), halt (exit code or None), perf (dict of the PERF columns or None), phases
(list of (value, cycle)), text (PUTCHAR output), ic_refill, dc_refill, dc_write, timeout (bool).
Usage: `from prog_runner import run_program`; run_program(words, caches=0, lat=2, fwd=1, name="x").
The program is padded with NOPs to 256 words. Used by T1.3 and later directed tests.
"""
import os
import re
import subprocess
from paths import CORE_RTL, TB, work_dir

PERF_COLS = ("cycles", "instret", "stall_loaduse", "flush_cycles", "imiss_cycles", "dmiss_cycles")
M32 = 0xFFFFFFFF
NOP = 0x00000013


def run_program(words, caches=0, lat=2, fwd=1, name="prog", maxcyc=200000):
    d = work_dir(f"prog/{name}_c{caches}_l{lat}_f{fwd}")
    with open(os.path.join(d, "program.hex"), "w") as f:
        f.write("".join(f"{w & M32:08x}\n" for w in words + [NOP] * (256 - len(words))))
    subprocess.run(["iverilog", "-g2012", "-o", os.path.join(d, "p.vvp"),
                    f"-Ptb_prog.CACHES={caches}", f"-Ptb_prog.LAT={lat}", f"-Ptb_prog.FWD={fwd}",
                    f"-Ptb_prog.MAXCYC={maxcyc}"] + CORE_RTL
                   + [os.path.join(TB, "sys_monitor.sv"), os.path.join(TB, "tb_prog.sv")],
                   check=True, capture_output=True)
    out = subprocess.run(["vvp", "p.vvp"], cwd=d, capture_output=True, text=True).stdout
    return parse_output(out)


def parse_output(out):
    """Parse the lines tb_prog.sv and sys_monitor.sv print (HALT, PERF, PHASE, CHR, REG, MEM, ...)."""
    r = {"regs": {0: 0}, "mem": {}, "halt": None, "perf": None, "phases": [], "text": "",
         "timeout": "TIMEOUT" in out, "raw": out}
    for ln in out.splitlines():
        if m := re.match(r"REG (\d+) (\w+)", ln): r["regs"][int(m.group(1))] = int(m.group(2), 16) if "x" not in m.group(2) else None
        elif m := re.match(r"MEM (\d+) (\w+)", ln): r["mem"][int(m.group(1))] = int(m.group(2), 16) if "x" not in m.group(2) else None
        elif m := re.match(r"HALT (\d+)", ln): r["halt"] = int(m.group(1))
        elif ln.startswith("PERF,"): r["perf"] = dict(zip(PERF_COLS, map(int, ln.split(",")[1:])))
        elif m := re.match(r"PHASE (\d+) cycle=(\d+)", ln): r["phases"].append((int(m.group(1)), int(m.group(2))))
        elif m := re.match(r"(IC_REFILL|DC_REFILL|DC_WRITE) (\d+)", ln): r[m.group(1).lower()] = int(m.group(2))
        elif m := re.match(r"CHR (\d+)", ln): r["text"] += chr(int(m.group(1)))
    return r
