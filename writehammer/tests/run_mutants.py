"""run_mutants.py: apply each mutant in tests/mutants/core_mutants.py to a copy of rtl/ and run the suite.

Inputs: rtl/, tests/. Output: one line per mutant (CAUGHT by <test> / SURVIVED), then a summary;
exit 0 only if every non-equivalent mutant is caught, every patch applies and changes the source,
and the equivalence argument for C6 is backed by C6X (caught) and C6X_control (passes).
Usage: python3 tests/run_mutants.py
"""
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import ROOT, RTL, TESTS
from mutants.core_mutants import MUTANTS, DECODER_SW_01, EQUIVALENT

# Cheapest first; the first failing test catches the mutant.
SUITE = [
    ("cache_integration", ["tests/cache_integration.py"], {}),
    ("nohazard_c0", ["tests/nohazard_test.py"], {}),
    ("nohazard_c1_l2", ["tests/nohazard_test.py"], {"CACHES": "1", "LAT": "2"}),
    ("hazard_fwd", ["tests/hazard_tests.py", "--quiet"], {}),
    ("hazard_nofwd", ["tests/hazard_tests.py", "--nofwd", "--quiet"], {}),
    ("hazard_c1_l2", ["tests/hazard_tests.py", "--quiet"], {"CACHES": "1", "LAT": "2"}),
]


def apply(dst, patches):
    for f, old, new in patches:
        p = os.path.join(dst, f)
        s = open(p).read()
        if s.count(old) != 1:
            return f"patch text found {s.count(old)} times in {f}"
        t = s.replace(old, new)
        if t == s:
            return f"patch does not change {f}"
        open(p, "w").write(t)
    return None


def run(name, patches):
    base = os.path.join(ROOT, "work", "mutants", name)
    shutil.rmtree(base, ignore_errors=True)
    rtl = os.path.join(base, "rtl")
    shutil.copytree(RTL, rtl)
    err = apply(rtl, patches)
    if err:
        return name, "PATCH_FAILED", err
    env = dict(os.environ, RTL_DIR=rtl, WORK_ROOT=os.path.join(base, "work"), JOBS="2")
    for tname, cmd, extra in SUITE:
        r = subprocess.run([sys.executable] + cmd, cwd=ROOT, env={**env, **extra},
                           capture_output=True, text=True)
        if r.returncode != 0:
            # A crash (compile error, Python traceback) is not a detection: report it as ERROR.
            if "Traceback" in r.stderr or "Error" in r.stderr and "FAIL" not in r.stdout:
                return name, "ERROR", f"{tname}: {r.stderr.strip().splitlines()[-1][:120]}"
            first = next((ln for ln in r.stdout.splitlines()
                          if ln.startswith("FAIL") or "<-" in ln or ln.startswith("[nohazard")), "")
            return name, "CAUGHT", f"{tname}: {first.strip()[:110]}"
    return name, "SURVIVED", ""


jobs = [(m[0], [(m[1], m[2], m[3])]) for m in MUTANTS]
jobs += [("C6X_decoder_sw01_no_gate", [DECODER_SW_01] + [(m[1], m[2], m[3]) for m in MUTANTS if m[0] == "C6_re_without_RegWriteM"]),
         ("C6X_control_decoder_sw01_with_gate", [DECODER_SW_01])]
with ThreadPoolExecutor(max_workers=6) as ex:
    res = list(ex.map(lambda j: run(*j), jobs))

ok = True
for name, status, info in res:
    print(f"{name:40s} {status:12s} {info}")
    if name == "C6X_control_decoder_sw01_with_gate":
        ok &= status == "SURVIVED"          # control: correct gate keeps every test passing
    elif name in EQUIVALENT:
        ok &= status == "SURVIVED"          # argued equivalent in core_mutants.py
    else:
        ok &= status == "CAUGHT"
real = [r for r in res if r[0] not in EQUIVALENT and not r[0].startswith("C6X_control")]
print(f"[mutants] {sum(r[1] == 'CAUGHT' for r in real)}/{len(real)} caught; "
      f"{len(EQUIVALENT)} argued equivalent (C6, backed by C6X/C6X_control); {'OK' if ok else 'FAIL'}")
sys.exit(0 if ok else 1)
