"""random_control.py: the random lockstep must catch known-bad cores (T1.6 acceptance control).

Applies a seeded known bug (a mutant from tests/mutants/) to a copy of rtl/ and runs
random_lockstep.py on it; the run must report mismatches. Mutants used: H1 (no forwarding from
Memory to SrcA), H3 (no load-use stall), H5 (register file written on the wrong edge), S2 (loads
read the mirrored byte lane), C4 (Writeback not held during a D$ freeze, needs caches on).
Exit 0 only if every bad core fails (fewer than all programs pass) and an unmodified core passes.
Usage: python3 tests/random_control.py
"""
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "mutants"))
from paths import ROOT, RTL
from core_mutants import MUTANTS as CORE
from subword_mutants import MUTANTS as SUB

N = 200
CASES = [("H1_no_fwd_from_M_srcA", {}), ("H3_no_load_use_stall", {}), ("H5_regfile_posedge_write", {}),
         ("S2_load_wrong_byte_lane", {}), ("C4_mwreg_not_held", {"CACHES": "1", "LAT": "3"}),
         (None, {})]        # None = unmodified core: must pass
ok = True
for mid, extra in CASES:
    base = os.path.join(ROOT, "work", "random_control", mid or "clean")
    shutil.rmtree(base, ignore_errors=True)
    shutil.copytree(RTL, os.path.join(base, "rtl"))
    if mid:
        m = next(x for x in CORE + SUB if x[0] == mid)
        p = os.path.join(base, "rtl", m[1])
        s = open(p).read()
        assert s.count(m[2]) == 1, f"{mid}: patch text not found exactly once"
        open(p, "w").write(s.replace(m[2], m[3]))
    env = dict(os.environ, RTL_DIR=os.path.join(base, "rtl"), WORK_ROOT=os.path.join(base, "work"), **extra)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tests", "random_lockstep.py"), "--n", str(N)],
                       env=env, cwd=ROOT, capture_output=True, text=True)
    last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-200:]
    good = (r.returncode == 0) if mid is None else (r.returncode != 0 and "passed" in last)
    ok &= good
    print(f"{'ok  ' if good else 'BAD '} {(mid or 'unmodified core'):28s} {last}")
print("[random_control] " + ("OK" if ok else "FAIL"))
sys.exit(0 if ok else 1)
