"""invariant_test.py: the correctness invariant of spec Section 4 across cache and memory configurations (T2.6).

Usage:   python3 tests/invariant_test.py [--quick]
For every program the final architectural state must be identical with caches off and with caches on at
memory latency 1, 5, 20 and with random latency (two seeds). The "signature" compared is:
  arch tests      the riscv-arch-test signature words (and they must also equal Spike's)
  workloads       exit code, program output, the register file hash and a hash of every word of main memory
                  (with the D$ overlaid on memory, so dirty lines count), for Dhrystone, CoreMark, the
                  8 Embench kernels, memcpy_big, memset_big and storeloop (tests/workloads.py)
  random programs registers x1..x29 and the 2 KiB data window, equal to the independent reference model
                  (tests/refmodel.py) as well as across configurations
Configurations: off, on/L=1, on/L=5, on/L=20, on/random L=10 seed 3, on/random L=10 seed 9, and three small-cache
geometries (1 KiB; 512 B with 32-byte lines; 256 B with 64-byte lines) that force frequent evictions.
Output: one line per group; "[invariant] n/n groups passed"; exit 0 only if every signature agrees.
--quick uses a third of the arch tests and 100 random programs.
"""
import hashlib
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from paths import ROOT, CORE_RTL, TB, work_dir
from vl_tb import _build as vl_build
import arch_test as A
from asm import sw, lui, M32
from random_gen import gen, DATA_BASE, WINDOW_BYTES
from refmodel import run as model_run
sys.path.insert(0, os.path.join(ROOT, "analysis"))

QUICK = "--quick" in sys.argv
# (name, caches, latency, random latency, seed, I$ bytes, D$ bytes, line bytes). The last three use caches much
# smaller than the programs' working sets so evictions, dirty write-backs and conflicts are frequent (with
# the 2 KiB caches the random programs' 2 KiB window never evicts anything).
CONFIGS = [("off", 0, 2, 0, 1, 2048, 2048, 16), ("on_L1", 1, 1, 0, 1, 2048, 2048, 16), ("on_L5", 1, 5, 0, 1, 2048, 2048, 16),
           ("on_L20", 1, 20, 0, 1, 2048, 2048, 16), ("on_rand_s3", 1, 10, 1, 3, 2048, 2048, 16),
           ("on_rand_s9", 1, 10, 1, 9, 2048, 2048, 16), ("on_1KiB_L5", 1, 5, 0, 1, 1024, 1024, 16),
           ("on_512B_line32_L3", 1, 3, 0, 1, 512, 512, 32), ("on_256B_line64_L2", 1, 2, 0, 1, 256, 256, 64)]
JOBS = int(os.environ.get("JOBS", "8"))
failures = []
groups = 0


def run_exe(exe, cwd, args=()):   # (a hung simulation of a broken core must not burn minutes: callers pass tight limits)
    return subprocess.run([exe, *args], cwd=cwd, capture_output=True, text=True).stdout


# ---------------------------------------------------------------- arch tests
def arch_one(name):
    d = work_dir(f"invariant/arch/{name}")
    sp, rt = A.build(name, "spike", d), A.build(name, "rtl", d)
    ss = A.symbols(sp)
    beg, end = ss["begin_signature"], ss["end_signature"]
    sig = os.path.join(d, "spike.sig")
    subprocess.run(["spike", "--isa=rv32i", "--priv=m", f"+signature={sig}", "+signature-granularity=4", sp],
                   capture_output=True, timeout=120)
    ref = [ln.strip() for ln in open(sig) if ln.strip()]
    subprocess.run(["riscv64-unknown-elf-objcopy", "-O", "binary", rt, os.path.join(d, "rtl.bin")], check=True)
    data = open(os.path.join(d, "rtl.bin"), "rb").read()
    data += b"\0" * (-len(data) % 4)
    open(os.path.join(d, "program.hex"), "w").write("".join(f"{int.from_bytes(data[i:i + 4], 'little'):08x}\n" for i in range(0, len(data), 4)))
    memw = max(65536, 1 << (len(data) // 4 - 1).bit_length())
    bw, ew = (beg - 0x80000000) >> 2, (end - 0x80000000) >> 2
    sigs = {}
    for cname, caches, lat, rl, seed, icb, dcb, lineb in CONFIGS:
        exe = vl_build("tb_arch", [*CORE_RTL, os.path.join(TB, "sys_monitor.sv"), os.path.join(TB, "tb_arch.sv")],
                       {"CACHES": caches, "LAT": lat, "RANDLAT": rl, "MEM_SEED": seed, "MEMW": memw, "MAXCYC": 5_000_000,
                        "ICB": icb, "DCB": dcb, "LINEB": lineb})
        out = run_exe(exe, d, [f"+sigb={bw}", f"+sige={ew}"])
        got = re.findall(r"^SIG (\w+)$", out, re.M)
        sigs[cname] = got if "TIMEOUT" not in out else ["TIMEOUT"]
    bad = [c for c, g in sigs.items() if g != ref]
    return name, bad


names = A.included()
if QUICK:
    names = names[::3]
with ThreadPoolExecutor(max_workers=JOBS) as ex:
    res = list(ex.map(arch_one, names))
bad = [(n, b) for n, b in res if b]
groups += 1
print(f"{'PASS' if not bad else 'FAIL'}  arch tests: {len(res) - len(bad)}/{len(res)} tests have the same signature (= Spike's) in all {len(CONFIGS)} configurations"
      + ("" if not bad else f"  first: {bad[0]}"))
if bad:
    failures.append("arch")

# ---------------------------------------------------------------- benchmark workloads
from baseline import workloads as build_workloads
from prog_runner import parse_output


def prog_one(item):
    name, cls, hexf = item[0], item[1], item[2]
    d = work_dir(f"invariant/wl/{re.sub('[^A-Za-z0-9]+', '_', name)}")
    open(os.path.join(d, "program.hex"), "w").write(open(hexf).read())
    sigs = {}
    # cycle limit from the known-good run length: caches-on runs take at most a few times longer; a core
    # that hangs must be cut off quickly (a mutant otherwise spins for minutes per workload and configuration)
    limit = 12 * WINDOW_CYCLES.get(name, 5_000_000) + 2_000_000
    for cname, caches, lat, rl, seed, icb, dcb, lineb in CONFIGS:
        exe = vl_build("tb_prog", [*CORE_RTL, os.path.join(TB, "sys_monitor.sv"), os.path.join(TB, "tb_prog.sv")],
                       {"CACHES": caches, "LAT": lat, "RANDLAT": rl, "MEM_SEED": seed, "MEMW": 65536, "IMAGE": 1,
                        "HASH": 1, "MAXCYC": 800_000_000, "ICB": icb, "DCB": dcb, "LINEB": lineb})
        out = run_exe(exe, d, [f"+maxcyc={limit}"])
        r = parse_output(out)
        rh = re.search(r"REGHASH (\w+)", out)
        mh = re.search(r"MEMHASH (\w+)", out)
        sigs[cname] = ("TIMEOUT",) if r["timeout"] else (r["halt"], r["text"], rh and rh.group(1), mh and mh.group(1))
        if cname != "off" and sigs[cname] != sigs["off"]:
            break                                    # already a mismatch: no need to run the other configurations
    base = sigs["off"]
    return name, [c for c, g in sigs.items() if g != base or g[0] != 0 or g[2] is None], base


wl = build_workloads()
import json
WINDOW_CYCLES = {x['workload']: x['cycles'] for x in json.load(open(os.path.join(ROOT, 'analysis', 'baseline.json')))}
with ThreadPoolExecutor(max_workers=max(2, JOBS // 2)) as ex:
    res = list(ex.map(prog_one, wl))
bad = [(n, b) for n, b, _ in res if b]
groups += 1
print(f"{'PASS' if not bad else 'FAIL'}  workloads: {len(res) - len(bad)}/{len(res)} programs end with the same exit code, output, registers and memory in all {len(CONFIGS)} configurations"
      + ("" if not bad else f"  first: {bad[0]}"))
if bad:
    failures.append("workloads")

# ---------------------------------------------------------------- random programs vs the model
MEMW_R = 2048
WIN0, WIN1 = DATA_BASE // 4, (DATA_BASE + WINDOW_BYTES) // 4
HALT = [lui(30, 0xF0000), sw(0, 0, 30)]
NRAND = 100 if QUICK else 200


def rand_cfg(cfg):
    cname, caches, lat, rl, seed, icb, dcb, lineb = cfg
    d = work_dir(f"invariant/rand/{cname}")
    subprocess.run(["iverilog", "-g2012", "-o", os.path.join(d, "r.vvp"), f"-Ptb_random.CACHES={caches}", f"-Ptb_random.LAT={lat}",
                    f"-Ptb_random.RANDLAT={rl}", f"-Ptb_random.MEM_SEED={seed}", f"-Ptb_random.MEMW={MEMW_R}",
                    f"-Ptb_random.WIN_BEGIN_W={WIN0}", f"-Ptb_random.WIN_END_W={WIN1}", "-Ptb_random.MAXCYC=60000",
                    f"-Ptb_random.ICB={icb}", f"-Ptb_random.DCB={dcb}", f"-Ptb_random.LINEB={lineb}"] + CORE_RTL
                   + [os.path.join(TB, "sys_monitor.sv"), os.path.join(TB, "tb_random.sv")], check=True, capture_output=True)
    bad = 0
    for s in range(1, NRAND + 1):
        p = gen(s)
        prog = p.prologue_rtl + p.body
        sd = os.path.join(d, f"s{s}")
        os.makedirs(sd, exist_ok=True)
        open(os.path.join(sd, "program.hex"), "w").write("".join(f"{w & M32:08x}\n" for w in prog + HALT))
        out = subprocess.run(["vvp", os.path.join(d, "r.vvp")], cwd=sd, capture_output=True, text=True).stdout
        regs = {int(m.group(1)): int(m.group(2), 16) for m in re.finditer(r"^REG (\d+) ([0-9a-f]+)$", out, re.M)}
        win = {int(m.group(1)): int(m.group(2), 16) for m in re.finditer(r"^WIN (\d+) ([0-9a-f]+)$", out, re.M)}
        mr, mm = model_run(prog, mem_bytes=4 * MEMW_R)
        ok = len(regs) == 31 and len(win) == WIN1 - WIN0 and all(regs[r] == mr[r] for r in range(1, 30)) \
            and all(win[w] == int.from_bytes(mm[4 * w:4 * w + 4], "little") for w in range(WIN0, WIN1))
        bad += not ok
        if bad >= 3:
            break                                     # clearly broken: stop this configuration early
    return cname, bad


with ThreadPoolExecutor(max_workers=JOBS) as ex:
    res = list(ex.map(rand_cfg, CONFIGS))
groups += 1
badr = [(c, b) for c, b in res if b]
print(f"{'PASS' if not badr else 'FAIL'}  random programs: {NRAND} programs equal the model in all {len(CONFIGS)} configurations"
      + ("" if not badr else f"  mismatches per configuration: {badr}"))
if badr:
    failures.append("random")

print(f"[invariant] {groups - len(failures)}/{groups} groups passed")
sys.exit(1 if failures else 0)
