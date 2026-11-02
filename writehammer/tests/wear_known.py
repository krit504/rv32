"""Known-answer full-core wear checks for fill, store, merge, and eviction.

Usage: python3 tests/wear_known.py
Inputs: hand-encoded RV32I micro-programs below. Outputs: work/wear_known/*
run files; exits nonzero unless exact per-line write counts and RTL counters match.
Expected values are derived from a 2 KiB, 16 B direct-mapped write-back cache.
Does not establish correctness for arbitrary traces; T3.5 replays those.
"""
import csv
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
from wear_run import run  # noqa: E402


def addi(rd, rs1, imm):
    return ((imm & 4095) << 20) | (rs1 << 15) | (rd << 7) | 0x13


def lui(rd, imm20):
    return (imm20 << 12) | (rd << 7) | 0x37


def mem_store(rs2, imm, rs1, funct3):
    imm &= 4095
    return ((imm >> 5) << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | ((imm & 31) << 7) | 0x23


def sw(rs2, imm, rs1):
    return mem_store(rs2, imm, rs1, 2)


def sb(rs2, imm, rs1):
    return mem_store(rs2, imm, rs1, 0)


def lw(rd, imm, rs1):
    return ((imm & 4095) << 20) | (rs1 << 15) | (2 << 12) | (rd << 7) | 3


def execute(name, words, expected, counters, phases):
    d = ROOT / "work" / "wear_known" / name
    d.mkdir(parents=True, exist_ok=True)
    image = d / "known.hex"
    image.write_text("".join(f"{w:08x}\n" for w in words))
    out = run(image, d / "run", maxcyc=5000, window=13, memw=4096)
    got = {int(r["line"]): int(r["count"]) for r in csv.DictReader((out / "wear_lines.csv").open())}
    assert got == {i: expected.get(i, 0) for i in range(128)}, (name, got, expected)
    log = (out / "simulation.log").read_text()
    m = re.search(r"^DC_CNT (.*)$", log, re.M)
    assert m, log
    observed = {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", m.group(1))}
    for key, want in counters.items():
        assert observed[key] == want, (name, key, observed[key], want)
    phase_rows = list(csv.DictReader((out / "wear_phases.csv").open()))
    assert [int(r["phase"]) for r in phase_rows] == phases, phase_rows
    print(f"PASS {name}: {sum(expected.values())} writes, counters {counters}")


def main():
    # x1=0x1000 (line 0); x4=0x2000 (same line, different tag),
    # x6=0x1010 (line 1). The first SW misses (fill+store), next SW and SB
    # hit, LW hits, conflicting LW evicts dirty line 0 and fills, return SW
    # misses (fill+store), final SW misses line 1 (fill+store).
    p = [lui(1, 1), addi(2, 0, 42), lui(4, 2), lui(6, 1), addi(6, 6, 16),
         lui(7, 0xF0000), sw(2, 0, 1), sw(2, 4, 1), sb(2, 1, 1),
         lw(3, 0, 1), lw(5, 0, 4), sw(2, 0, 1), sw(2, 0, 6),
         sw(2, 12, 7), sw(0, 0, 7)]
    execute("mixed", p, {0: 7, 1: 2},
            {"access": 7, "hit": 3, "miss": 4, "fill": 4, "wb": 1, "write": 5}, [42])
    # Two loads of one cold line: one fill, then a hit; no store writes.
    p = [lui(1, 1), lui(7, 0xF0000), lw(2, 0, 1), lw(3, 4, 1), sw(0, 0, 7)]
    execute("load_only", p, {0: 1},
            {"access": 2, "hit": 1, "miss": 1, "fill": 1, "wb": 0, "write": 0}, [])
    print("[wear-known] 2/2 passed")


if __name__ == "__main__":
    main()
