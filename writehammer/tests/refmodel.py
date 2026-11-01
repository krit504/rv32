"""refmodel.py: independent RV32I reference model (instruction-set simulator in Python).

Written from the RISC-V unprivileged ISA specification, not from the RTL, so it can check the RTL
without sharing its mistakes. Supports the RV32I subset the core implements: all R-type and
I-type ALU ops, lb/lh/lw/lbu/lhu, sb/sh/sw, all six branches, lui, auipc, jal, jalr.
Not modelled: fence, ecall, ebreak, CSRs, misaligned accesses (raise ValueError).

Usage:
    from refmodel import run
    regs, mem = run(program_words, max_steps=10000, mem_bytes=1024)
`regs` is a list of 32 ints (unsigned); `mem` is a bytearray. Execution stops when pc leaves the
program, or at an instruction that jumps to itself (jal x0, 0), or after max_steps.
Memory wraps modulo mem_bytes, matching the core's 256-word dmem.
"""

M32 = 0xFFFFFFFF


def s32(x):
    x &= M32
    return x - (1 << 32) if x & 0x80000000 else x


def sext(x, bits):
    x &= (1 << bits) - 1
    return x - (1 << bits) if x >> (bits - 1) else x


def run(prog, max_steps=100000, mem_bytes=1024, init_mem=None):
    regs = [0] * 32
    mem = bytearray(mem_bytes) if init_mem is None else bytearray(init_mem)
    pc = 0
    mask = mem_bytes - 1

    def lb(a): return mem[a & mask]

    def load(a, n):
        if a % n:
            raise ValueError(f"misaligned load {n} at {a:#x}")
        return sum(lb(a + i) << (8 * i) for i in range(n))

    def store(a, v, n):
        if a % n:
            raise ValueError(f"misaligned store {n} at {a:#x}")
        for i in range(n):
            mem[(a + i) & mask] = (v >> (8 * i)) & 0xFF

    for _ in range(max_steps):
        if pc < 0 or pc // 4 >= len(prog) or pc % 4:
            break
        w = prog[pc // 4] & M32
        op, rd, f3 = w & 0x7F, (w >> 7) & 0x1F, (w >> 12) & 7
        rs1, rs2, f7 = (w >> 15) & 0x1F, (w >> 20) & 0x1F, w >> 25
        a, b = regs[rs1], regs[rs2]
        nxt, res = pc + 4, None
        imm_i = sext(w >> 20, 12)
        if op == 0b0110011:                                    # R-type
            sh = b & 31
            res = {(0, 0): a + b, (0x20, 0): a - b, (0, 1): a << sh, (0, 2): int(s32(a) < s32(b)),
                   (0, 3): int(a < b), (0, 4): a ^ b, (0, 5): a >> sh, (0x20, 5): s32(a) >> sh,
                   (0, 6): a | b, (0, 7): a & b}[(f7, f3)]
        elif op == 0b0010011:                                  # I-type ALU
            sh = (w >> 20) & 31
            if f3 == 0: res = a + imm_i
            elif f3 == 2: res = int(s32(a) < imm_i)
            elif f3 == 3: res = int(a < (imm_i & M32))
            elif f3 == 4: res = a ^ imm_i
            elif f3 == 6: res = a | imm_i
            elif f3 == 7: res = a & imm_i
            elif f3 == 1: res = a << sh
            elif f3 == 5: res = (s32(a) >> sh) if f7 == 0x20 else (a >> sh)
        elif op == 0b0000011:                                  # loads
            ad = (a + imm_i) & M32
            res = {0: lambda: sext(load(ad, 1), 8), 1: lambda: sext(load(ad, 2), 16), 2: lambda: load(ad, 4),
                   4: lambda: load(ad, 1), 5: lambda: load(ad, 2)}[f3]()
        elif op == 0b0100011:                                  # stores
            ad = (a + sext(((w >> 25) << 5) | ((w >> 7) & 0x1F), 12)) & M32
            store(ad, b, {0: 1, 1: 2, 2: 4}[f3])
        elif op == 0b1100011:                                  # branches
            imm = sext(((w >> 31) << 12) | (((w >> 7) & 1) << 11) | (((w >> 25) & 0x3F) << 5) | (((w >> 8) & 0xF) << 1), 13)
            take = {0: a == b, 1: a != b, 4: s32(a) < s32(b), 5: s32(a) >= s32(b), 6: a < b, 7: a >= b}[f3]
            if take: nxt = (pc + imm) & M32
        elif op == 0b0110111: res = w & 0xFFFFF000             # lui
        elif op == 0b0010111: res = pc + (w & 0xFFFFF000)      # auipc
        elif op == 0b1101111:                                  # jal
            imm = sext(((w >> 31) << 20) | (((w >> 12) & 0xFF) << 12) | (((w >> 20) & 1) << 11) | (((w >> 21) & 0x3FF) << 1), 21)
            res, nxt = pc + 4, (pc + imm) & M32
        elif op == 0b1100111:                                  # jalr
            res, nxt = pc + 4, (a + imm_i) & M32 & ~1
        else:
            raise ValueError(f"unsupported instruction {w:#010x} at pc {pc:#x}")
        if res is not None and rd:
            regs[rd] = res & M32
        if nxt == pc:
            break
        pc = nxt
    return regs, mem
