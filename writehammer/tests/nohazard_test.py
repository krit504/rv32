"""nohazard_test.py: the 27-instruction no-hazard regression (21 register checks).

Inputs: tests/golden/nohazard_program.hex. Env CACHES=1 LAT=n runs it through the caches.
Output: prints the testbench's "N PASS, M FAIL" line; exit 0 only on 21 PASS, 0 FAIL.
Usage: python3 tests/nohazard_test.py
Checks: final values of the 21 registers the program writes. Does not check timing.
"""
import os
import re
import shutil
import subprocess
import sys
from paths import CORE_RTL, TB, TESTS, work_dir

CACHES = int(os.environ.get("CACHES", "0"))
LAT = int(os.environ.get("LAT", "2"))
# Caches off: 60 cycles, as in the original testbench. Caches on: 7 I$ refills of up to LAT+2
# cycles each, plus the program and its drain; 200 + 10*LAT stays well short of the point where
# pc wraps the 256-word memory (the program is followed by zero words, which are no-ops).
CYCLES = 60 if not CACHES else 200 + 10 * LAT

work = work_dir(f"nohazard_c{CACHES}_l{LAT}")
shutil.copy(os.path.join(TESTS, "golden", "nohazard_program.hex"), os.path.join(work, "program.hex"))
subprocess.run(["iverilog", "-g2012", "-o", os.path.join(work, "nh.vvp"),
                f"-Ptb_rv32_top_pipelined.CACHES={CACHES}", f"-Ptb_rv32_top_pipelined.LAT={LAT}",
                f"-Ptb_rv32_top_pipelined.CYCLES={CYCLES}"]
               + CORE_RTL + [os.path.join(TB, "tb_rv32i_pipelined.sv")],
               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
out = subprocess.run(["vvp", "nh.vvp"], cwd=work, capture_output=True, text=True).stdout
m = re.search(r"(\d+) PASS, (\d+) FAIL", out)
print(f"[nohazard CACHES={CACHES} LAT={LAT}] {m.group(0) if m else 'no result line'}")
sys.exit(0 if m and m.group(1) == "21" and m.group(2) == "0" else 1)
