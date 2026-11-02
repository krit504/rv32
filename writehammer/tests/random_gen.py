"""random_gen.py: seeded random RV32I program generator for lockstep testing (T1.6).

Usage:  from random_gen import gen;  prog = gen(seed, pc_free=False)
        python3 tests/random_gen.py SEED        prints the program as hex words (for debugging)
Returns an object with:
  prologue_rtl  words that set x31 = DATA_BASE (0x800) and load random constants / window data
  body          the random instructions
  prologue_tail the part of the prologue after the two base-setting instructions
  base_setup    index range of the two x31-setting instructions inside prologue_rtl (always [0, 2))
Properties (the reason a random program is a valid test):
  - terminates: every branch, jal and jalr goes forward by 0..3 instructions
  - no misaligned access: lh/lhu/sh at even, lw/sw at multiples of 4, all inside the data window
  - registers: x31 = data window base (never written again), x30 = scratch for jalr targets (never
    a general source or destination), x1..x29 general
  - hazard dense: each source register is, with probability 0.6, one of the last three destinations
    (RAW gaps 1 to 3 and load-use), otherwise uniform; loads, stores, taken and not-taken branches,
    jal, jalr, lui, auipc, all R-type and I-type ALU ops and every sub-word access appear;
    70% of memory accesses fall in a 256-byte hot region so loads hit earlier stores
  - pc_free=True: no pc-dependent value ever reaches a general register (no auipc, jal and jalr
    write x0), so the program gives identical register and memory results at any load address; used
    to cross-check the reference model against Spike.
The instruction mix is fixed by this file, not tuned per seed or per design under test.
"""
import random
import sys
from asm import (addi, add, sub, sll, slt, sltu, xor_, srl, sra, or_, and_, slti, sltiu, xori, ori, andi,
                 slli, srli, srai, lui, auipc, lb, lh, lw, lbu, lhu, sb, sh, sw, beq, bne, blt, bge,
                 bltu, bgeu, jal, jalr, M32)

DATA_BASE = 0x800          # data window address; code must stay below it
WINDOW_BYTES = 2048        # 0x800 .. 0xFFF
HOT_BYTES = 256            # 70% of accesses fall in the first 256 bytes, so loads, stores and sub-word merges collide
MAX_WORDS = 470            # code words, keeps the program below DATA_BASE with the prologue
SCRATCH = 30
BASE = 31
GENERAL = list(range(1, 30))


class Program:
    pass


def _lui_addi(rd, value):
    lo = ((value & 0xFFF) ^ 0x800) - 0x800
    return [lui(rd, ((value - lo) >> 12) & 0xFFFFF), addi(rd, rd, lo)]


def gen(seed, pc_free=False):
    rnd = random.Random(seed)
    recent = []

    def src():
        if rnd.random() < 0.05:
            return 0
        if recent and rnd.random() < 0.6:
            return rnd.choice(recent[-3:])
        return rnd.choice(GENERAL)

    def dst():
        r = rnd.choice(GENERAL)
        recent.append(r)
        return r

    def plain():
        """one non-control instruction"""
        k = rnd.random()
        if k < 0.26:   # R-type
            op = rnd.choice([add, sub, sll, slt, sltu, xor_, srl, sra, or_, and_])
            return op(dst(), src(), src())
        if k < 0.42:   # I-type ALU
            op = rnd.choice([addi, slti, sltiu, xori, ori, andi])
            return op(dst(), src(), rnd.randint(-2048, 2047))
        if k < 0.50:   # shifts by immediate
            return rnd.choice([slli, srli, srai])(dst(), src(), rnd.randint(0, 31))
        if k < 0.55:
            return lui(dst(), rnd.randint(0, 0xFFFFF))
        if k < 0.58 and not pc_free:
            return auipc(dst(), rnd.randint(0, 0xFFFFF))
        if k < 0.78:   # loads (every width), aligned, inside the window
            kind = rnd.choice(["lb", "lbu", "lh", "lhu", "lw", "lw"])
            off = rnd.randint(0, HOT_BYTES - 4) if rnd.random() < 0.7 else rnd.randint(0, WINDOW_BYTES - 4)
            if kind in ("lh", "lhu"): off &= ~1
            if kind == "lw": off &= ~3
            return {"lb": lb, "lbu": lbu, "lh": lh, "lhu": lhu, "lw": lw}[kind](dst(), off, BASE)
        # stores
        kind = rnd.choice(["sb", "sh", "sw", "sw"])
        off = rnd.randint(0, HOT_BYTES - 4) if rnd.random() < 0.7 else rnd.randint(0, WINDOW_BYTES - 4)
        if kind == "sh": off &= ~1
        if kind == "sw": off &= ~3
        return {"sb": sb, "sh": sh, "sw": sw}[kind](src(), off, BASE)

    body = []
    target = rnd.randint(60, MAX_WORDS - 20)
    while len(body) < target:
        c = rnd.random()
        k = rnd.randint(0, 3)                      # instructions skipped when the transfer is taken
        if c < 0.12:                               # conditional branch
            op = rnd.choice([beq, bne, blt, bge, bltu, bgeu])
            body.append(op(src(), src(), 4 * (k + 1)))
            body += [plain() for _ in range(k)]
        elif c < 0.17:                             # jal
            rd = 0 if (pc_free or rnd.random() < 0.5) else dst()
            body.append(jal(rd, 4 * (k + 1)))
            body += [plain() for _ in range(k)]
        elif c < 0.22:                             # jalr through an auipc-built pointer
            rd = 0 if (pc_free or rnd.random() < 0.5) else dst()
            body.append(auipc(SCRATCH, 0))
            body.append(jalr(rd, 8 + 4 * k, SCRATCH))
            body += [plain() for _ in range(k)]
        else:
            body.append(plain())

    # prologue: x31 = window base, random constants in x1..x8, random words into the window
    p = Program()
    base_setup = [lui(BASE, 0), addi(BASE, BASE, DATA_BASE)]   # tests/random_spike_check swaps these two
    tail = []
    for r in range(1, 9):
        tail += _lui_addi(r, rnd.getrandbits(32))
    for i in range(8):
        tail.append(sw(rnd.randint(1, 8), 4 * rnd.randint(0, WINDOW_BYTES // 4 - 1), BASE))
    p.prologue_rtl = base_setup + tail
    p.prologue_tail = tail
    p.body = body
    assert len(p.prologue_rtl) + len(body) < DATA_BASE // 4, "program overlaps the data window"
    return p


if __name__ == "__main__":
    pr = gen(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
    for w in pr.prologue_rtl + pr.body:
        print(f"{w & M32:08x}")
