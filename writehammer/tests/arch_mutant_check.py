"""arch_mutant_check.py: the arch-test harness must reject known-bad cores (T1.5 acceptance control).

Applies two sub-word mutants (tests/mutants/subword_mutants.py: S1 lb zero-extends, S3 sb byte
enable stuck) to a copy of rtl/ and runs the tests that exercise them (lb-align-01, sb-align-01)
plus an untouched control (lbu-align-01 under S1 must still pass). Exit 0 only if each bad core
FAILS its test and the control passes, i.e. the signature comparison is not vacuous.
Usage: python3 tests/arch_mutant_check.py
"""
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "mutants"))
from paths import ROOT, RTL
from subword_mutants import MUTANTS

CASES = [("S1_lb_zero_extends", "lb-align-01", False), ("S1_lb_zero_extends", "lbu-align-01", True),
         ("S3_sb_byte_enable_stuck", "sb-align-01", False)]
ok = True
for mid, test, expect_pass in CASES:
    m = next(x for x in MUTANTS if x[0] == mid)
    base = os.path.join(ROOT, "work", "arch_mutant", mid)
    shutil.rmtree(base, ignore_errors=True)
    shutil.copytree(RTL, os.path.join(base, "rtl"))
    p = os.path.join(base, "rtl", m[1])
    s = open(p).read()
    assert s.count(m[2]) == 1, f"{mid}: patch text not found exactly once"
    open(p, "w").write(s.replace(m[2], m[3]))
    env = dict(os.environ, RTL_DIR=os.path.join(base, "rtl"), WORK_ROOT=os.path.join(base, "work"), JOBS="1")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tests", "arch_test.py"), test], env=env,
                       cwd=ROOT, capture_output=True, text=True)
    passed = r.returncode == 0
    good = passed == expect_pass
    ok &= good
    print(f"{'ok  ' if good else 'BAD '} {mid:28s} {test:14s} {'passed' if passed else 'failed'} "
          f"(expected {'pass' if expect_pass else 'fail'})")
    if not good:
        print((r.stdout + r.stderr)[-400:])
print("[arch_mutant_check] " + ("OK" if ok else "FAIL"))
sys.exit(0 if ok else 1)
