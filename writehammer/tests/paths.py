"""paths.py: shared locations for the test scripts.

Inputs: none. Outputs: ROOT, RTL, TB, WORK and the core source list CORE_RTL.
Usage: `from paths import ROOT, CORE_RTL, TB, work_dir` from any script in tests/.
Env overrides (used by the mutation runner): RTL_DIR replaces rtl/, TB_DIR replaces tb/,
WORK_ROOT replaces work/.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RTL = os.environ.get("RTL_DIR", os.path.join(ROOT, "rtl"))
TB = os.environ.get("TB_DIR", os.path.join(ROOT, "tb"))
TESTS = os.path.join(ROOT, "tests")

CORE_RTL = [os.path.join(RTL, f) for f in (
    "rv32_top_pipelined.sv", "f_d_reg.sv", "d_e_reg.sv", "e_m_reg.sv", "m_w_reg.sv",
    "control_unit.sv", "main_decoder.sv", "alu_decoder.sv", "alu.sv",
    "immediate_generator.sv", "pc.sv", "regfile.sv", "imem.sv", "dmem.sv",
    "mem_model.sv", "icache.sv", "dcache.sv", "write_guard.sv", "hazard_unit.sv")]


def work_dir(name):
    """Return (creating it) the scratch run directory work/<name>; it is gitignored."""
    d = os.path.join(os.environ.get("WORK_ROOT", os.path.join(ROOT, "work")), name)
    os.makedirs(d, exist_ok=True)
    return d
