"""Metrics table for the 27-instruction regression program (tests/golden/nohazard_program.hex),
with forwarding on and off. Caches off, as when the table was first produced.

    python3 tests/perf_report.py
"""
import os
import re
import shutil
import subprocess
from paths import CORE_RTL, TB, TESTS, work_dir

CORE = CORE_RTL + [os.path.join(TB, "perf_counters.sv"), os.path.join(TB, "tb_hazard.sv")]
WORK = work_dir("perf_report")
shutil.copy(os.path.join(TESTS, "golden", "nohazard_program.hex"), os.path.join(WORK, "program.hex"))

n_instr = sum(1 for ln in open(os.path.join(WORK, "program.hex")) if ln.strip())
rows = []
for fwd in (1, 0):
    subprocess.run(["iverilog", "-g2012", "-o", os.path.join(WORK, "perf.vvp"), f"-Ptb_hazard.FWD={fwd}",
                    f"-Ptb_hazard.END_PC={n_instr * 4}"] + CORE, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    out = subprocess.run(["vvp", "perf.vvp"], cwd=WORK, capture_output=True, text=True).stdout
    line = next(ln for ln in out.splitlines() if ln.startswith("METRICS "))
    rows.append((fwd, dict(re.findall(r"(\w+)=(\S+)", line))))

stall_key = lambda m: next(k for k in m if k.endswith("stall_per_instr") and k != "spurious_per_instr")
print(f"program.hex: {n_instr} instructions, pipeline fill = {rows[0][1]['fill_cycles']} cycles\n")
print("| FORWARDING | cycles | retired | CPI_raw | CPI_steady | stall/instr | branch_flush/instr | spurious/instr | identity |")
print("|---|---|---|---|---|---|---|---|---|")
for fwd, m in rows:
    sk = stall_key(m)
    print(f"| {fwd} | {m['cycles']} | {m['retired']} | {m['CPI_raw']} | {m['CPI_steady']} | "
          f"{m[sk]} ({'load-use' if fwd else 'dependency'}) | {m['branch_flush_per_instr']} | "
          f"{m['spurious_per_instr']} | {m['identity']} |")
