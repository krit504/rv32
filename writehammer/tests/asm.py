"""asm.py: RV32I instruction encoders for directed tests (same encodings as hazard_tests.py).

Inputs: none. Output: functions returning 32-bit instruction words, e.g. addi(rd, rs1, imm).
Usage: `from asm import addi, lw, sw, beq, jal, NOP, M32`.
"""

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
