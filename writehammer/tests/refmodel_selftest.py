"""refmodel_selftest.py: hand-computed checks of tests/refmodel.py (T1.2).

Every expected value below was worked out by hand from the RISC-V unprivileged ISA, with the
derivation in the comment on its line. Output: "refmodel selftest OK" or an AssertionError.
"""
from asm import *   # noqa: F401,F403
from refmodel import run

w = [lui(1, 0x80F1F), addi(1, 1, 0x2A3), sw(1, 0, 0),      # x1 = 0x80F1F2A3, bytes (lo to hi) A3 F2 F1 80
     lb(2, 0, 0), lb(3, 3, 0), lbu(4, 3, 0), lh(5, 2, 0), lhu(6, 2, 0),
     sb(0, 1, 0), lw(7, 0, 0), jal(0, 0)]
r, _ = run(w)
assert r[1] == 0x80F1F2A3
assert r[2] == 0xFFFFFFA3      # lb byte0 = 0xA3, bit 7 set -> sign-extended
assert r[3] == 0xFFFFFF80      # lb byte3 = 0x80 -> sign-extended
assert r[4] == 0x00000080      # lbu byte3 = 0x80 -> zero-extended
assert r[5] == 0xFFFF80F1      # lh half at offset 2 = 0x80F1, bit 15 set -> sign-extended
assert r[6] == 0x000080F1      # lhu half at offset 2 = 0x80F1 -> zero-extended
assert r[7] == 0x80F100A3      # sb x0 at byte 1 clears 0xF2 only

r, _ = run([addi(1, 0, -1), addi(2, 0, 1), slt(3, 1, 2), sltu(4, 1, 2), sra(5, 1, 2), srl(6, 1, 2), sll(7, 2, 2), jal(0, 0)])
assert r[3] == 1 and r[4] == 0   # -1 < 1 signed; 0xFFFFFFFF > 1 unsigned
assert r[5] == 0xFFFFFFFF        # arithmetic shift of -1
assert r[6] == 0x7FFFFFFF        # logical shift of 0xFFFFFFFF by 1
assert r[7] == 2                 # 1 << 1

r, _ = run([addi(1, 0, 5), beq(1, 1, 8), addi(2, 0, 9), addi(3, 0, 7), jal(0, 0)])
assert r[2] == 0 and r[3] == 7   # taken beq skips the instruction at pc 8

r, _ = run([jal(1, 8), addi(2, 0, 9), addi(3, 0, 7), jal(0, 0)])
assert r[1] == 4 and r[2] == 0 and r[3] == 7   # link = pc+4; skipped instruction

r, _ = run([addi(1, 0, 17), jalr(2, 0, 1), addi(3, 0, 9), addi(4, 0, 9), jal(0, 0)])
assert r[2] == 8 and r[3] == 0 and r[4] == 0   # target (17+0)&~1 = 16 = the final jal: skips pc 8 and pc 12; link = 8
print("refmodel selftest OK")
