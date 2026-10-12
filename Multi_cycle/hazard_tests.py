import re
import subprocess
import sys

FILES = ("rv32i_pipelined.sv f_d_reg.sv d_e_reg.sv e_m_reg.sv m_w_reg.sv control_unit.sv "
         "main_decoder.sv alu_decoder.sv ALU.sv immediate_generator.sv pc.sv regfile.sv "
         "imem.sv dmem.sv hazard_unit.sv perf_counters.sv tb_hazard.sv").split()

M32 = 0xFFFFFFFF

def i_type(imm, rs1, f3, rd, op=0b0010011):
    return ((imm & 0xFFF) << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | op

def r_type(f7, rs2, rs1, f3, rd):
    return (f7 << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | 0b0110011

def s_type(imm, rs2, rs1, f3=0b010):
    imm &= 0xFFF
    return ((imm >> 5) << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | ((imm & 0x1F) << 7) | 0b0100011

def b_type(imm, rs2, rs1, f3):
    imm &= 0x1FFF
    return (((imm >> 12) & 1) << 31) | (((imm >> 5) & 0x3F) << 25) | (rs2 << 20) | (rs1 << 15) | \
           (f3 << 12) | (((imm >> 1) & 0xF) << 8) | (((imm >> 11) & 1) << 7) | 0b1100011

def u_type(imm20, rd, op):
    return ((imm20 & 0xFFFFF) << 12) | (rd << 7) | op

def j_type(imm, rd):
    imm &= 0x1FFFFF
    return (((imm >> 20) & 1) << 31) | (((imm >> 1) & 0x3FF) << 21) | (((imm >> 11) & 1) << 20) | \
           (((imm >> 12) & 0xFF) << 12) | (rd << 7) | 0b1101111

addi  = lambda rd, rs1, imm: i_type(imm, rs1, 0, rd)
add   = lambda rd, rs1, rs2: r_type(0, rs2, rs1, 0, rd)
sub   = lambda rd, rs1, rs2: r_type(0b0100000, rs2, rs1, 0, rd)
lw    = lambda rd, imm, rs1: i_type(imm, rs1, 0b010, rd, 0b0000011)
sw    = lambda rs2, imm, rs1: s_type(imm, rs2, rs1)
beq   = lambda rs1, rs2, imm: b_type(imm, rs2, rs1, 0b000)
bne   = lambda rs1, rs2, imm: b_type(imm, rs2, rs1, 0b001)
lui   = lambda rd, imm20: u_type(imm20, rd, 0b0110111)
auipc = lambda rd, imm20: u_type(imm20, rd, 0b0010111)
jal   = lambda rd, imm: j_type(imm, rd)
jalr  = lambda rd, imm, rs1: i_type(imm, rs1, 0, rd, 0b1100111)
NOP = addi(0, 0, 0)

FILL = 4   # pipeline fill cycles, reported separately from steady-state CPI
NOFWD = "--nofwd" in sys.argv or "--nofw" in sys.argv
QUIET = "--quiet" in sys.argv

def run(prog):
    words = prog + [NOP] * (256 - len(prog))
    with open("program.hex", "w") as f:
        for w in words:
            f.write(f"{w & M32:08x}\n")
    subprocess.run(["iverilog", "-g2012", "-o", "hz.vvp", f"-Ptb_hazard.FWD={0 if NOFWD else 1}",
                    f"-Ptb_hazard.END_PC={len(prog) * 4}"] + FILES, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    out = subprocess.run(["vvp", "hz.vvp"], capture_output=True, text=True).stdout
    regs = {0: 0}
    mem = {}
    stats = {}
    for ln in out.splitlines():
        m = re.match(r"REG (\d+) (\w+)", ln)
        if m: regs[int(m.group(1))] = m.group(2)
        m = re.match(r"MEM (\d+) (\w+)", ln)
        if m: mem[int(m.group(1))] = m.group(2)
        m = re.match(r"(CYCLES|STALLS|FLUSHES|RETIRED|SPURIOUS|DONE|XVIOL) (\d+)", ln)
        if m: stats[m.group(1).lower()] = int(m.group(2))
        if ln.startswith("METRICS "):
            stats["metrics"] = dict(re.findall(r"(\w+)=(\S+)", ln))
    return regs, mem, stats

def hx(v):
    return f"{v & M32:08x}"

SETUP = [addi(1, 0, 5), addi(2, 0, 7), addi(4, 0, 3), NOP, NOP, NOP, NOP]  # x1=5 x2=7 x4=3, settled
LOADSET = [addi(1, 0, 9), sw(1, 0, 0), sw(0, 4, 0), NOP, NOP, NOP, NOP]    # mem[0]=9, mem[1]=0

tests = []
def T(name, prog, regs=None, mem=None, **exp):
    tests.append((name, prog, regs or {}, mem or {}, exp))

# Expectation keys: stalls / flushes / retired / spurious are always cross-checked
# for retired+flushes; stalls and spurious are only exact in forwarding mode (the
# ablation stalls on every dependency). dep=True => ablation must stall at least once.

# ---- forwarding ----
T("fwd gap1 rs1/rs2 + gap2",
  SETUP + [add(3, 1, 2), sub(5, 3, 4), sub(6, 4, 3)],
  regs={3: 12, 5: 9, 6: -9}, stalls=0, retired=10, dep=True)
T("fwd gap2", SETUP + [add(3, 1, 2), addi(9, 0, 1), sub(5, 3, 4)],
  regs={3: 12, 9: 1, 5: 9}, stalls=0, retired=10, dep=True)
T("GAP 3: producer in W while consumer in D (negedge regfile, no forwarding)",
  [addi(19, 0, 42), addi(20, 0, 1), addi(21, 0, 2), add(22, 19, 0)],
  regs={19: 42, 22: 42}, stalls=0, retired=4)
T("GAP 3 via rs2",
  [addi(19, 0, 42), addi(20, 0, 1), addi(21, 0, 2), add(22, 0, 19)],
  regs={19: 42, 22: 42}, stalls=0, retired=4)
T("M beats W priority", [addi(3, 0, 1), addi(3, 0, 2), add(5, 3, 0)],
  regs={3: 2, 5: 2}, retired=3, dep=True)
T("x0 guard", [addi(0, 0, 5), add(5, 0, 0)], regs={5: 0}, retired=2)
T("FwdDataM from lui", [lui(5, 0x12345), add(6, 5, 0)],
  regs={5: 0x12345000, 6: 0x12345000}, retired=2, dep=True)
T("store data forwarding", [addi(5, 0, 7), sw(5, 0, 0), lw(6, 0, 0)],
  regs={5: 7, 6: 7}, mem={0: 7}, retired=3, dep=True)
T("false match: addi imm bits == RdM", [addi(5, 0, 100), addi(6, 0, 5)],
  regs={5: 100, 6: 5}, retired=2)
T("false match: auipc Instr[19:15] == RdM", [addi(5, 0, 100), auipc(6, 0x28)],
  regs={5: 100, 6: 4 + 0x28000}, retired=2)
# producers that do not write a register but whose rd field matches a later source
T("RegWriteM gating: sw rd-field==5, gap 1",
  [addi(5, 0, 100), NOP, NOP, NOP, sw(0, 5, 0), add(6, 5, 0)],
  regs={5: 100, 6: 100}, retired=6)
T("RegWriteW gating: sw rd-field==5, gap 2",
  [addi(5, 0, 100), NOP, NOP, NOP, sw(0, 5, 0), NOP, add(6, 5, 0)],
  regs={5: 100, 6: 100}, retired=7)

# ---- load-use ----
T("load-use rs1", LOADSET + [lw(5, 0, 0), add(6, 5, 0)],
  regs={5: 9, 6: 9}, stalls=1, spurious=0, retired=9, dep=True)
T("load-use rs2", LOADSET + [lw(5, 0, 0), add(6, 0, 5)],
  regs={5: 9, 6: 9}, stalls=1, spurious=0, retired=9, dep=True)
T("load gap2, no stall", LOADSET + [lw(5, 0, 0), addi(9, 0, 1), add(6, 5, 0)],
  regs={5: 9, 6: 9, 9: 1}, stalls=0, retired=10, dep=True)
T("load data forwarded from W after the stall", LOADSET + [lw(5, 0, 0), add(6, 5, 5)],
  regs={5: 9, 6: 18}, stalls=1, retired=9, dep=True)
# spurious stalls: Instr[24:20]/[19:15] are immediate bits that happen to equal the load's rd
T("spurious stall: addi imm bits == lw rd (result still correct)",
  LOADSET + [lw(5, 0, 0), addi(6, 0, 5)],
  regs={5: 9, 6: 5}, stalls=1, spurious=1, retired=9)
T("spurious stall: lui imm bits == lw rd",
  LOADSET + [lw(5, 0, 0), lui(6, 0x500)],
  regs={5: 9, 6: 0x500000}, stalls=1, spurious=1, retired=9)

# ---- control ----
T("lw->beq taken",
  LOADSET + [lw(5, 4, 0), beq(5, 0, 12), addi(6, 0, 1), addi(7, 0, 1), addi(8, 0, 2)],
  regs={5: 0, 6: 0, 7: 0, 8: 2}, stalls=1, flushes=1, retired=10, dep=True)
T("lw->beq not taken",
  LOADSET + [lw(5, 0, 0), beq(5, 0, 12), addi(6, 0, 1), addi(7, 0, 1), addi(8, 0, 2)],
  regs={5: 9, 6: 1, 7: 1, 8: 2}, stalls=1, flushes=0, retired=12, dep=True)
T("beq taken: flush both wrong-path instrs",
  [beq(0, 0, 12), addi(5, 0, 1), addi(6, 0, 1), addi(7, 0, 3)],
  regs={5: 0, 6: 0, 7: 3}, flushes=1, retired=2)
T("bne not taken: no flush",
  [bne(0, 0, 12), addi(5, 0, 1), addi(6, 0, 1), addi(7, 0, 3)],
  regs={5: 1, 6: 1, 7: 3}, flushes=0, stalls=0, retired=4)
T("jal: flush + link", [jal(1, 12), addi(5, 0, 1), addi(6, 0, 1), addi(7, 0, 3)],
  regs={1: 4, 5: 0, 6: 0, 7: 3}, flushes=1, retired=2)
T("jalr: flush + link + odd target",
  [addi(2, 0, 17), jalr(1, 0, 2), addi(5, 0, 1), addi(6, 0, 1), addi(7, 0, 3)],
  regs={1: 8, 5: 0, 6: 0, 7: 3}, flushes=1, retired=3, dep=True)
T("wrong-path jal after taken beq (FlushE clears PCSrcE)",
  [beq(0, 0, 12), jal(9, 8), addi(5, 0, 1), addi(7, 0, 3)],
  regs={9: 0, 5: 0, 7: 3}, flushes=1, retired=2)

fails = 0
for name, prog, regs, mem, exp in tests:
    got_regs, got_mem, st = run(prog)
    errs = []
    for r, v in regs.items():
        if got_regs.get(r) != hx(v):
            errs.append(f"x{r}={got_regs.get(r)} expected {hx(v)}")
    for a, v in mem.items():
        if got_mem.get(a) != hx(v):
            errs.append(f"mem[{a}]={got_mem.get(a)} expected {hx(v)}")
    if st.get("done") != 1:
        errs.append("pipeline never drained")
    if st.get("xviol") != 0:
        errs.append(f"hazard_unit saw X/Z on {st.get('xviol')} cycle(s)")
    for k in ("flushes", "retired"):
        if k in exp and st.get(k) != exp[k]:
            errs.append(f"{k}={st.get(k)} expected {exp[k]}")
    if not NOFWD:
        for k in ("stalls", "spurious"):
            if k in exp and st.get(k) != exp[k]:
                errs.append(f"{k}={st.get(k)} expected {exp[k]}")
    elif exp.get("dep") and st.get("stalls", 0) == 0:
        errs.append("ablation: dependent sequence never stalled")
    ident = st["retired"] + st["stalls"] + 2 * st["flushes"] + FILL
    if st["cycles"] != ident:
        errs.append(f"cycles={st['cycles']} != retired+stalls+2*flushes+4={ident}")
    if st.get("metrics", {}).get("identity") != "ok":
        errs.append("perf_counters identity check reported " + str(st.get("metrics", {}).get("identity")))
    if not QUIET or errs:
        mt = st.get("metrics", {})
        print(("PASS  " if not errs else "FAIL  ") + f"{name:68s} cyc={st['cycles']:3d} ret={st['retired']:2d} "
              f"stall={st['stalls']} flush={st['flushes']} spur={st['spurious']} "
              f"CPI_raw={mt.get('CPI_raw', '?')} CPI_steady={mt.get('CPI_steady', '?')}"
              + ("" if not errs else "\n        <- " + "; ".join(errs)))
    fails += bool(errs)

print(f"\n[{'NO FORWARDING (ablation)' if NOFWD else 'forwarding'}] {len(tests) - fails}/{len(tests)} passed")
sys.exit(1 if fails else 0)
