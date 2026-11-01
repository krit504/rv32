"""image_runner.py: run a linked program image (from sw/build.py) on the core (T1.4 onward).

Inputs: path to a program.hex produced by sw/build.py. Output: the same dict as
prog_runner.run_program (halt exit code, PERF columns, PHASE markers, PUTCHAR text, registers,
cache counters, timeout flag) plus "cycles_total". Uses 256 KiB memories (MEMW=65536) with the
data memory loaded from the same image.
Usage: from image_runner import run_image; run_image(hex_path, caches=0, lat=2, name="x")
Timeout: MAXCYC is only a guard against a hung simulation; a timeout is a failure the caller must
report (never treat it as a pass, and record the value used).
"""
import os
import shutil
import subprocess
from paths import CORE_RTL, TB, work_dir
from prog_runner import parse_output

MEMW = 65536


def run_image(hex_path, caches=0, lat=2, fwd=1, name="img", maxcyc=5_000_000, image=1):
    """image=0 leaves the data memory unloaded: only for negative controls."""
    d = work_dir(f"img/{name}_c{caches}_l{lat}_f{fwd}_i{image}")
    shutil.copy(hex_path, os.path.join(d, "program.hex"))
    subprocess.run(["iverilog", "-g2012", "-o", os.path.join(d, "p.vvp"),
                    f"-Ptb_prog.CACHES={caches}", f"-Ptb_prog.LAT={lat}", f"-Ptb_prog.FWD={fwd}",
                    f"-Ptb_prog.MAXCYC={maxcyc}", f"-Ptb_prog.MEMW={MEMW}", f"-Ptb_prog.IMAGE={image}"]
                   + CORE_RTL + [os.path.join(TB, "sys_monitor.sv"), os.path.join(TB, "tb_prog.sv")],
                   check=True, capture_output=True)
    out = subprocess.run(["vvp", "p.vvp"], cwd=d, capture_output=True, text=True).stdout
    return parse_output(out)
