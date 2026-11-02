"""bench_test.py: Dhrystone and CoreMark run correctly on the core (T1.7).

Usage:   python3 tests/bench_test.py
Builds sw/dhrystone and sw/coremark (500 Dhrystone runs, 10 CoreMark iterations) and runs them under
Verilator (tests/vl_runner.py) with caches off and caches on at LAT 1 and 10.
Oracles (never the RTL's own output):
  Dhrystone  the benchmark's own list of final values ("should be"), checked in the program; exit
             code = number of mismatches; the DHRY_SELFCHECK line must also be printed.
  CoreMark   the same sources built natively with the host gcc and the stock posix port, run with
             the same seeds and iteration count; seedcrc, crclist, crcmatrix, crcstate and crcfinal
             printed by the RTL run must equal the native values, and the program's exit code (count
             of CoreMark CRC-error messages) must be 0.
Controls: three known-bad cores (mutants H1, H3, C4 from tests/mutants) must fail each benchmark they
          can affect, by a wrong exit code, a CRC difference, a timeout or missing output.
Output:  PASS/FAIL lines and "[bench] n/n passed"; exit 0 only if all pass.
Does not check: performance numbers (analysis/baseline.py records them).
"""
import os
import re
import shutil
import subprocess
import sys
from paths import ROOT, RTL, work_dir
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "mutants"))
from core_mutants import MUTANTS
from vl_runner import run_image_vl

RUNS, ITERS = 500, 10
CFGS = [(0, 2), (1, 1), (1, 10)]
CM = os.path.join(ROOT, "third_party", "coremark")
fails, total = [], 0


def check(ok, msg):
    global total
    total += 1
    if not ok:
        fails.append(msg)


def build(script, out, arg):
    r = subprocess.run([sys.executable, os.path.join(ROOT, "sw", script), out, str(arg)], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"build failed ({script}): {(r.stdout + r.stderr)[-600:]}")
    return os.path.join(out, "program.hex")


def crc_lines(text):
    return dict(re.findall(r"^(seedcrc|\[0\]crclist|\[0\]crcmatrix|\[0\]crcstate|\[0\]crcfinal)\s*:\s*(0x[0-9a-f]{4})", text, re.M))


def native_crcs(n):
    d = work_dir("bench/native")
    exe = os.path.join(d, f"cm{n}")
    srcs = [os.path.join(CM, f) for f in ("core_main.c", "core_list_join.c", "core_matrix.c", "core_state.c", "core_util.c")]
    r = subprocess.run(["gcc", "-O2", "-w", "-DPERFORMANCE_RUN=1", f"-DITERATIONS={n}", "-DHAS_FLOAT=1", '-DFLAGS_STR="-O2"',
                        "-DSEED_METHOD=SEED_ARG", "-I" + CM, "-I" + os.path.join(CM, "posix")] + srcs
                       + [os.path.join(CM, "posix", "core_portme.c"), "-o", exe, "-lpthread"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = subprocess.run([exe, "0x0", "0x0", "0x66", str(n), "7", "1", "2000"], capture_output=True, text=True).stdout
    c = crc_lines(out)
    assert len(c) == 5, f"native oracle printed {c}"
    return c


def run_dhry(hexf, caches, lat, name):
    r = run_image_vl(hexf, caches=caches, lat=lat, name=name, maxcyc=20_000_000)
    ok = (not r["timeout"]) and r["halt"] == 0 and f"DHRY_SELFCHECK errors=0 runs={RUNS}" in r["text"]
    return ok, r


def run_cm(hexf, caches, lat, name, oracle):
    r = run_image_vl(hexf, caches=caches, lat=lat, name=name, maxcyc=100_000_000)
    got = crc_lines(r["text"])
    ok = (not r["timeout"]) and r["halt"] == 0 and got == oracle
    return ok, r, got


dh = build("dhrystone/build_dhrystone.py", work_dir("bench/dhry"), RUNS)
cm = build("coremark/build_coremark.py", work_dir("bench/coremark"), ITERS)
oracle = native_crcs(ITERS)
print(f"native CoreMark oracle ({ITERS} iterations): {oracle}")

for caches, lat in CFGS:
    ok, r = run_dhry(dh, caches, lat, "dhry")
    check(ok, f"Dhrystone caches={caches} lat={lat}: halt={r['halt']} timeout={r['timeout']} text={r['text']!r}")
    ok, r, got = run_cm(cm, caches, lat, "cm", oracle)
    check(ok, f"CoreMark caches={caches} lat={lat}: halt={r['halt']} timeout={r['timeout']} crcs={got} expected {oracle}")

# controls: a known-bad core must fail the benchmark
CONTROLS = [("H1_no_fwd_from_M_srcA", 0, 2), ("H3_no_load_use_stall", 0, 2), ("C4_mwreg_not_held", 1, 3)]
for mid, caches, lat in CONTROLS:
    m = next(x for x in MUTANTS if x[0] == mid)
    base = os.path.join(ROOT, "work", "bench_control", mid)
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
for kind, hexf in (("dhry", {dh!r}), ("cm", {cm!r})):
    r = run_image_vl(hexf, caches={caches}, lat={lat}, name="ctl_"+kind, maxcyc=3_000_000)
    print(kind, r["halt"], r["timeout"], repr(r["text"][-400:]))
"""
    out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True).stdout
    # parse results back: each benchmark line is "<kind> <halt> <timeout> <text>"
    bad_dhry = bad_cm = False
    for ln in out.splitlines():
        kind, halt, to, txt = ln.split(" ", 3)
        if kind == "dhry":
            bad_dhry = (to == "True") or halt != "0" or "errors=0" not in txt
        if kind == "cm":
            got = crc_lines(eval(txt))
            bad_cm = (to == "True") or halt != "0" or got != oracle
    check(bad_dhry or bad_cm, f"control {mid}: neither Dhrystone nor CoreMark noticed the bad core")
    print(f"control {mid}: Dhrystone {'FAILS' if bad_dhry else 'passes'}, CoreMark {'FAILS' if bad_cm else 'passes'} (a bad core must fail at least one)")

for f in fails:
    print("FAIL " + f)
print(f"[bench] {total - len(fails)}/{total} passed")
sys.exit(1 if fails else 0)
