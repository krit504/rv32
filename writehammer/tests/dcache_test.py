"""dcache_test.py: the D$ against independent models, on randomized operation lists (T2.4).

Usage:   python3 tests/dcache_test.py
Oracles (independent of the RTL):
  data     a plain byte array updated by every store: every load must return the byte array's word, and
           after the run main memory with the cache overlaid (peek) must equal the byte array everywhere;
           this checks write-back, eviction, write-allocate, byte-enable merges and the bypass path.
  counts   tests/cache_model.py replays the request stream: access, hit, miss, fill, write-back, bypass,
           refill-after-bypass, write counts, per-line array-write counts (the wear counts) and the stall
           cycles of every request (fixed latency) must match the RTL's counters exactly.
  trace    the RTL's per-request trace pulses (tr_valid) equal the number of operations.
Simulator: Verilator (the same testbench takes minutes in Icarus).
Configurations: cache 1/2/4/8 KiB x line 16/32/64 B x latency 1/3/10 (+ random latency), array-write latency
1 and 4, bypass probability 0, 0.15 and 0.5. Operation lists are seeded (seed printed on failure).
Env DCACHE_QUICK=1 runs 6 configurations (used for the mutation runs).
Output: PASS/FAIL per configuration and "[dcache] n/n passed"; exit 0 only if all pass.
Directed cases mixed in every list: stores to every byte offset, sub-word merges into one word, conflict
(same index, different tag) ping-pong, store then load of the same address, bypass of present-dirty,
present-clean and absent lines, back-to-back bypasses.
"""
import os
import random
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from paths import RTL, TB, work_dir
from cache_model import CacheModel
from vl_tb import run_tb

NOPS = 1500
DUMP_W = 4096                      # 16 KiB of address space


def gen_ops(seed, cache_bytes, line_bytes, byp_p):
    rnd = random.Random(seed)
    ops = []
    hot = [rnd.randrange(0, DUMP_W * 4, line_bytes) for _ in range(8)]       # hot lines to force reuse
    for _ in range(NOPS):
        r = rnd.random()
        if r < 0.45:                                                          # near a hot line
            base = rnd.choice(hot) + rnd.randrange(0, line_bytes, 4)
        elif r < 0.65:                                                        # conflict: same index, other tag
            base = (rnd.choice(hot) + rnd.randrange(1, 8) * cache_bytes) % (DUMP_W * 4)
        else:
            base = rnd.randrange(0, DUMP_W * 4, 4)
        base &= ~3
        kind = "L" if rnd.random() < 0.5 else "S"
        size = rnd.choice([1, 2, 4, 4]) if kind == "S" else 4
        off = rnd.randrange(0, 4, size) if size < 4 else 0
        bypass = kind == "S" and rnd.random() < byp_p
        ops.append((kind, base + off, size, bypass, rnd.getrandbits(32), rnd.randrange(0, 4)))
    return ops


def entry(op):
    kind, addr, size, bypass, val, idle = op
    be = {1: 1 << (addr & 3), 2: 0b0011 << (addr & 2), 4: 0b1111}[size] if kind == "S" else 0
    if kind == "S":                          # lane-aligned data: replicate the value across the word
        val = {1: (val & 0xFF) * 0x01010101, 2: (val & 0xFFFF) * 0x00010001, 4: val}[size]
    e = (addr & 0xFFFFFFFF) | (val << 32) | (be << 64) | ((kind == "S") << 68) | ((kind == "L") << 69) | (int(bypass) << 70) | (idle << 72)
    return f"{e:032x}\n", val, be


def run(cfg):
    cb, lb, lat, rnd_lat, wl, byp_p, seed = cfg
    d = work_dir(f"dcache/cb{cb}_lb{lb}_l{lat}_r{int(rnd_lat)}_w{wl}_b{byp_p}_s{seed}")
    ops = gen_ops(seed, cb, lb, byp_p)
    lines, vals = [], []
    for op in ops:
        t, v, be = entry(op)
        lines.append(t); vals.append((v, be))
    open(os.path.join(d, "ops.hex"), "w").writelines(lines)
    out = run_tb("tb_dcache", [os.path.join(RTL, "dcache.sv"), os.path.join(RTL, "mem_model.sv"), os.path.join(TB, "tb_dcache.sv")],
                 {"NOPS": len(ops), "DUMP_W": DUMP_W, "CACHE_BYTES": cb, "LINE_BYTES": lb, "LAT": lat,
                  "RANDOM": int(rnd_lat), "WL": wl}, d)
    if "TIMEOUT" in out:
        return cfg, ["timeout"]
    errs = []
    gold = bytearray(DUMP_W * 4)
    model = CacheModel(cb, lb)
    lds = {int(m.group(1)): int(m.group(2), 16) for m in re.finditer(r"^LD (\d+) ([0-9a-f]+)$", out, re.M)}
    stall = 0
    for i, (op, (v, be)) in enumerate(zip(ops, vals)):
        kind, addr, size, bypass = op[0], op[1], op[2], op[3]
        if not rnd_lat:
            stall += model.stall(kind, addr, bypass, lat, wl)
        model.op(kind, addr, size, bypass)
        if kind == "S":
            for j in range(4):
                if be >> j & 1:
                    gold[(addr & ~3) + j] = (v >> (8 * j)) & 0xFF
        else:
            exp = int.from_bytes(gold[addr & ~3:(addr & ~3) + 4], "little")
            if lds.get(i) != exp:
                errs.append(f"op {i} load {addr:#x}: got {lds.get(i)} expected {exp:#x}")
                break
    m = re.search(r"CNT access=(\d+) hit=(\d+) miss=(\d+) fill=(\d+) wb=(\d+) bypass=(\d+) rab=(\d+) stall=(\d+) write=(\d+) traces=(\d+)", out)
    if not m:
        return cfg, errs + ["no counter line"]
    got = dict(zip(("access", "hit", "miss", "fill", "wb", "bypass", "refill_after_bypass", "stall", "write", "traces"), map(int, m.groups())))
    exp = model.counters
    for k, v in exp.items():
        if got[k] != v:
            errs.append(f"counter {k}: rtl {got[k]} model {v}")
    if got["traces"] != len(ops):
        errs.append(f"trace pulses {got['traces']} expected {len(ops)}")
    if not rnd_lat and got["stall"] != stall:
        errs.append(f"stall cycles: rtl {got['stall']} model {stall}")
    awl = {int(a): int(b) for a, b in re.findall(r"^AWL (\d+) (\d+)$", out, re.M)}
    for ln in range(model.lines):
        if awl.get(ln, 0) != model.writes[ln]:
            errs.append(f"array writes on line {ln}: rtl {awl.get(ln, 0)} model {model.writes[ln]}")
            break
    mem = {int(a): int(b, 16) for a, b in re.findall(r"^MEM (\d+) ([0-9a-f]+)$", out, re.M)}
    for w in range(DUMP_W):
        if mem.get(w) != int.from_bytes(gold[4 * w:4 * w + 4], "little"):
            errs.append(f"final memory word {w}: got {mem.get(w)} expected {int.from_bytes(gold[4 * w:4 * w + 4], 'little'):#x}")
            break
    return cfg, errs


cfgs = []
seed = 1
for cb in (1024, 2048, 4096, 8192):
    for lb in (16, 32, 64):
        for lat, rl in ((1, False), (3, False), (10, False), (4, True)):
            cfgs.append((cb, lb, lat, rl, 1, (0, 0.15, 0.5)[seed % 3], seed)); seed += 1
cfgs += [(2048, 16, 3, False, 4, 0.15, 900), (2048, 32, 1, False, 4, 0.0, 901), (1024, 16, 10, False, 4, 0.5, 902)]
if os.environ.get("DCACHE_QUICK"):
    # 6 configurations for the mutation runs: every line size, fixed and random latency, bypass on and off, wl 1 and 4
    cfgs = [(2048, 16, 3, False, 1, 0.15, 101), (1024, 32, 10, False, 1, 0.5, 102), (4096, 64, 1, False, 1, 0.15, 103),
            (2048, 16, 4, True, 1, 0.15, 104), (2048, 16, 3, False, 4, 0.15, 105), (8192, 32, 3, False, 1, 0.0, 106)]
with ThreadPoolExecutor(max_workers=int(os.environ.get("JOBS", "12"))) as ex:
    res = list(ex.map(run, cfgs))
bad = 0
for cfg, errs in res:
    bad += bool(errs)
    print(("PASS  " if not errs else "FAIL  ") + f"cache={cfg[0]} line={cfg[1]} lat={cfg[2]}{'(rand)' if cfg[3] else ''} wl={cfg[4]} bypass={cfg[5]} seed={cfg[6]}"
          + ("" if not errs else "  <- " + "; ".join(errs[:3])))
print(f"[dcache] {len(res) - bad}/{len(res)} passed")
sys.exit(1 if bad else 0)
