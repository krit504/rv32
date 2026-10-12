"""Metrics table for the program currently in program.hex (the 27-instruction regression
program after `python3 encode.py`), with forwarding on and off.

    python3 encode.py && python3 perf_report.py
"""
import re
import subprocess

CORE = ("rv32i_pipelined.sv f_d_reg.sv d_e_reg.sv e_m_reg.sv m_w_reg.sv control_unit.sv "
        "main_decoder.sv alu_decoder.sv ALU.sv immediate_generator.sv pc.sv regfile.sv "
        "imem.sv dmem.sv hazard_unit.sv perf_counters.sv tb_hazard.sv").split()

n_instr = sum(1 for ln in open("program.hex") if ln.strip())
rows = []
for fwd in (1, 0):
    subprocess.run(["iverilog", "-g2012", "-o", "perf.vvp", f"-Ptb_hazard.FWD={fwd}",
                    f"-Ptb_hazard.END_PC={n_instr * 4}"] + CORE, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    out = subprocess.run(["vvp", "perf.vvp"], capture_output=True, text=True).stdout
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
