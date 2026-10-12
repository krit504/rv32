import re
import subprocess
import sys

FILES = ("rv32i_pipelined.sv f_d_reg.sv d_e_reg.sv e_m_reg.sv m_w_reg.sv control_unit.sv "
         "main_decoder.sv alu_decoder.sv ALU.sv immediate_generator.sv pc.sv regfile.sv "
         "imem.sv dmem.sv hazard_unit.sv tb_hazard.sv").split()

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

def run(prog):
    words = prog + [NOP] * (256 - len(prog))
    with open("program.hex", "w") as f:
        for w in words:
            f.write(f"{w & M32:08x}\n")
    subprocess.run(["iverilog", "-g2012", "-o", "hz.vvp"] + FILES, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    out = subprocess.run(["vvp", "hz.vvp"], capture_output=True, text=True).stdout
    regs = {0: 0}
    mem = {}
    stalls = flushes = None
    for ln in out.splitlines():
        m = re.match(r"REG (\d+) (\w+)", ln)
        if m: regs[int(m.group(1))] = m.group(2)
        m = re.match(r"MEM (\d+) (\w+)", ln)
        if m: mem[int(m.group(1))] = m.group(2)
        m = re.match(r"STALLS (\d+)", ln)
        if m: stalls = int(m.group(1))
        m = re.match(r"FLUSHES (\d+)", ln)
        if m: flushes = int(m.group(1))
    return regs, mem, stalls, flushes

def hx(v):
    return f"{v & M32:08x}"

SETUP = [addi(1, 0, 5), addi(2, 0, 7), addi(4, 0, 3), NOP, NOP, NOP, NOP]  # x1=5 x2=7 x4=3, settled
LOADSET = [addi(1, 0, 9), sw(1, 0, 0), sw(0, 4, 0), NOP, NOP, NOP, NOP]    # mem[0]=9, mem[1]=0

tests = []
def T(name, prog, regs=None, mem=None, stalls=None, flushes=None):
    tests.append((name, prog, regs or {}, mem or {}, stalls, flushes))

T("fwd gap1 rs1 / rs2, gap2",
  SETUP + [add(3, 1, 2), sub(5, 3, 4), sub(6, 4, 3)],
  regs={3: 12, 5: 9, 6: -9}, stalls=0)
T("fwd gap2", SETUP + [add(3, 1, 2), addi(9, 0, 1), sub(5, 3, 4)],
  regs={3: 12, 9: 1, 5: 9}, stalls=0)
T("M beats W priority", [addi(3, 0, 1), addi(3, 0, 2), add(5, 3, 0)], regs={3: 2, 5: 2})
T("x0 guard", [addi(0, 0, 5), add(5, 0, 0)], regs={5: 0})
T("FwdDataM lui", [lui(5, 0x12345), add(6, 5, 0)], regs={5: 0x12345000, 6: 0x12345000})
T("store data fwd", [addi(5, 0, 7), sw(5, 0, 0), lw(6, 0, 0)], regs={5: 7, 6: 7}, mem={0: 7})
T("false match addi imm", [addi(5, 0, 100), addi(6, 0, 5)], regs={5: 100, 6: 5})
T("false match auipc", [addi(5, 0, 100), auipc(6, 0x28)], regs={5: 100, 6: 4 + 0x28000})
T("load-use rs1", LOADSET + [lw(5, 0, 0), add(6, 5, 0)], regs={5: 9, 6: 9}, stalls=1)
T("load-use rs2", LOADSET + [lw(5, 0, 0), add(6, 0, 5)], regs={5: 9, 6: 9}, stalls=1)
T("load gap2", LOADSET + [lw(5, 0, 0), addi(9, 0, 1), add(6, 5, 0)], regs={5: 9, 6: 9, 9: 1}, stalls=0)
T("lw->beq taken", LOADSET + [lw(5, 4, 0), beq(5, 0, 12), addi(6, 0, 1), addi(7, 0, 1), addi(8, 0, 2)],
  regs={5: 0, 6: 0, 7: 0, 8: 2}, stalls=1, flushes=1)
T("lw->beq not taken", LOADSET + [lw(5, 0, 0), beq(5, 0, 12), addi(6, 0, 1), addi(7, 0, 1), addi(8, 0, 2)],
  regs={5: 9, 6: 1, 7: 1, 8: 2}, stalls=1, flushes=0)
T("beq taken flush", [beq(0, 0, 12), addi(5, 0, 1), addi(6, 0, 1), addi(7, 0, 3)],
  regs={5: 0, 6: 0, 7: 3}, flushes=1)
T("bne not taken", [bne(0, 0, 12), addi(5, 0, 1), addi(6, 0, 1), addi(7, 0, 3)],
  regs={5: 1, 6: 1, 7: 3}, flushes=0, stalls=0)
T("jal flush + link", [jal(1, 12), addi(5, 0, 1), addi(6, 0, 1), addi(7, 0, 3)],
  regs={1: 4, 5: 0, 6: 0, 7: 3}, flushes=1)
T("jalr flush + link + bit0", [addi(2, 0, 17), jalr(1, 0, 2), addi(5, 0, 1), addi(6, 0, 1), addi(7, 0, 3)],
  regs={1: 8, 5: 0, 6: 0, 7: 3}, flushes=1)
T("wrong-path jal after taken beq", [beq(0, 0, 12), jal(9, 8), addi(5, 0, 1), addi(7, 0, 3)],
  regs={9: 0, 5: 0, 7: 3}, flushes=1)

fails = 0
for name, prog, regs, mem, stalls, flushes in tests:
    got_regs, got_mem, got_stalls, got_flushes = run(prog)
    errs = []
    for r, v in regs.items():
        if got_regs.get(r) != hx(v):
            errs.append(f"x{r}={got_regs.get(r)} expected {hx(v)}")
    for a, v in mem.items():
        if got_mem.get(a) != hx(v):
            errs.append(f"mem[{a}]={got_mem.get(a)} expected {hx(v)}")
    if stalls is not None and got_stalls != stalls:
        errs.append(f"stalls={got_stalls} expected {stalls}")
    if flushes is not None and got_flushes != flushes:
        errs.append(f"flushes={got_flushes} expected {flushes}")
    print(("PASS  " if not errs else "FAIL  ") + name + ("" if not errs else "   <- " + "; ".join(errs)))
    fails += bool(errs)

print(f"\n{len(tests) - fails}/{len(tests)} passed")
sys.exit(1 if fails else 0)
