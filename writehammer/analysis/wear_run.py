"""Run a program image with the cached core and D$ wear observer.

Usage: python3 analysis/wear_run.py IMAGE.hex RUN_DIR [--maxcyc N] [--window N]
Inputs: linked or directed $readmemh image. Outputs in RUN_DIR: wear_windows.csv,
wear_lines.csv, wear_phases.csv, dc_trace.csv, simulation.log. A HALT exit of zero
and no TIMEOUT are required; caller may then run wear_stats.py and wear_replay.py.
"""
import argparse
import os
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from paths import CORE_RTL, TB  # noqa: E402
from vl_tb import run_tb  # noqa: E402


def run(image, outdir, maxcyc=200000, window=10000, memw=65536, lat=2, expect_exit=0):
    outdir = Path(outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(image, outdir / "program.hex")
    sources = CORE_RTL + [os.path.join(TB, name) for name in
                          ("sys_monitor.sv", "wear_monitor.sv", "tb_wear.sv")]
    output = run_tb("tb_wear", sources, {"MAXCYC": maxcyc, "MEMW": memw, "LAT": lat,
                                         "WINDOW_CYCLES": window}, str(outdir))
    (outdir / "simulation.log").write_text(output)
    halt = re.search(r"^HALT (\d+)$", output, re.M)
    if "TIMEOUT" in output or not halt or int(halt.group(1)) != expect_exit:
        raise RuntimeError(f"wear run failed: {outdir / 'simulation.log'}\n{output[-1000:]}")
    if not re.search(r"^DC_CNT ", output, re.M):
        raise RuntimeError("wear run missing cache counters")
    print(f"wear run: {outdir} HALT {expect_exit}")
    return outdir


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image")
    ap.add_argument("outdir")
    ap.add_argument("--maxcyc", type=int, default=200000)
    ap.add_argument("--window", type=int, default=10000)
    ap.add_argument("--memw", type=int, default=65536)
    ap.add_argument("--lat", type=int, default=2)
    ap.add_argument("--expect-exit", type=int, default=0)
    args = ap.parse_args()
    run(args.image, args.outdir, args.maxcyc, args.window, args.memw, args.lat, args.expect_exit)
