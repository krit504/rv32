"""workload_test.py: every benign workload builds, self-checks, and runs with caches off and on (T1.8).

Usage:   python3 tests/workload_test.py
Covers tests/workloads.py HELD_OUT (the Embench subset of DEC-008, memcpy_big, memset_big, storeloop).
Checks per workload: the build succeeds (RV32I-only ELF, sw/build.py); under Verilator with caches
off and with caches on at LAT 1 and 10 the program halts with exit code 0 (its own self-check: Embench's
verify_benchmark, or the error count of the in-repo workloads) and does not time out.
Independent oracle: the same sources are compiled natively with the host gcc (Embench's support code
and the in-repo programs; the measurement hooks are no-ops under -DNATIVE) and run on the host; each
must also exit 0. That confirms the self-check logic itself is sound on a different compiler and ISA,
so "exit 0 on the RTL" cannot be a check that always passes.
Controls: three known-bad cores (mutants H1, H3, C4) must fail at least one workload each.
Output:  PASS/FAIL lines and "[workloads] n/n passed"; exit 0 only if all pass.
"""
import glob
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from paths import ROOT, RTL, work_dir
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "mutants"))
from core_mutants import MUTANTS
from vl_runner import run_image_vl
from workloads import HELD_OUT

EB = os.path.join(ROOT, "third_party", "embench-iot")
CFGS = [(0, 2), (1, 1), (1, 10)]


def build(kind, arg, out):
    script = {"embench": "embench/build_embench.py", "workload": "workloads/build_workload.py"}[kind]
    cmd = [sys.executable, os.path.join(ROOT, "sw", script)] + ([arg, out] if kind == "embench" else [arg, out])
    r = subprocess.run(cmd, capture_output=True, text=True)
    return None if r.returncode else os.path.join(out, "program.hex"), (r.stdout + r.stderr)[-300:]


def native_exit(kind, arg):
    d = work_dir("workloads/native")
    exe = os.path.join(d, arg)
    if kind == "embench":
        srcs = glob.glob(os.path.join(EB, "src", arg, "*.c")) + [os.path.join(EB, "support", f) for f in ("main.c", "beebsc.c", "board.c")]
        cmd = ["gcc", "-O2", "-w", "-std=gnu99", "-DNATIVE", "-DCPU_MHZ=1", "-DGLOBAL_SCALE_FACTOR=1", "-DWARMUP_HEAT=1",
               "-I" + os.path.join(ROOT, "sw", "embench"), "-I" + os.path.join(EB, "support"), "-I" + os.path.join(EB, "src", arg)] + srcs + ["-o", exe, "-lm"]
    else:
        cmd = ["gcc", "-O2", "-w", "-std=gnu99", "-DNATIVE", os.path.join(ROOT, "sw", "workloads", arg + ".c"), "-o", exe]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        return f"native build failed: {r.stderr[-200:]}"
    return subprocess.run([exe]).returncode


def one(item):
    name, kind, arg = item
    out = work_dir(f"workloads/build/{name}")
    hexf, msg = build(kind, arg, out)
    if hexf is None:
        return name, [f"build failed: {msg}"], None
    errs = []
    nat = native_exit(kind, arg)
    if nat != 0:
        errs.append(f"native oracle exit {nat}")
    for caches, lat in CFGS:
        r = run_image_vl(hexf, caches=caches, lat=lat, name=f"wl_{name}", maxcyc=300_000_000)
        if r["timeout"] or r["halt"] != 0:
            errs.append(f"caches={caches} lat={lat}: halt={r['halt']} timeout={r['timeout']}")
    return name, errs, hexf


with ThreadPoolExecutor(max_workers=int(os.environ.get("JOBS", "6"))) as ex:
    res = list(ex.map(one, HELD_OUT))
fails = []
for name, errs, _ in res:
    print(("PASS  " if not errs else "FAIL  ") + name + ("" if not errs else "  <- " + "; ".join(errs)))
    if errs:
        fails.append(name)
total = len(res)

# controls: each bad core must fail at least one workload
hexes = {n: h for n, e, h in res if h}
for mid, caches, lat in [("H1_no_fwd_from_M_srcA", 0, 2), ("H3_no_load_use_stall", 0, 2), ("C4_mwreg_not_held", 1, 3)]:
    m = next(x for x in MUTANTS if x[0] == mid)
    base = os.path.join(ROOT, "work", "workload_control", mid)
    shutil.rmtree(base, ignore_errors=True)
    shutil.copytree(RTL, os.path.join(base, "rtl"))
    p = os.path.join(base, "rtl", m[1])
    s = open(p).read()
    assert s.count(m[2]) == 1, f"{mid}: patch text not found exactly once"
    open(p, "w").write(s.replace(m[2], m[3]))
    env = dict(os.environ, RTL_DIR=os.path.join(base, "rtl"), WORK_ROOT=os.path.join(base, "work"))
    code = f"""
import sys; sys.path.insert(0, {os.path.dirname(os.path.abspath(__file__))!r})
from vl_runner import run_image_vl
for n, h in {sorted(hexes.items())!r}:
    r = run_image_vl(h, caches={caches}, lat={lat}, name="ctl_"+n, maxcyc=20_000_000)
    print(n, r["halt"], r["timeout"])
"""
    out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True).stdout
    failed = [ln.split()[0] for ln in out.splitlines() if ln.split()[2] == "True" or ln.split()[1] != "0"]
    total += 1
    print(f"control {mid}: fails {len(failed)} of {len(hexes)} workloads ({', '.join(failed[:4])}{'...' if len(failed) > 4 else ''})")
    if not failed:
        fails.append(f"control {mid} not caught by any workload")
for f in fails:
    print("FAIL " + f)
print(f"[workloads] {total - len(fails)}/{total} passed")
sys.exit(1 if fails else 0)
