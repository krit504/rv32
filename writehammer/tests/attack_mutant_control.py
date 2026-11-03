"""Demand a nonzero self-check exit on the scoped stale-store RTL mutant.

Usage: python3 tests/attack_mutant_control.py --kind RTA [--kind RnLA ...]
Builds each image itself. A mutant timeout is a failure of this test: the C
self-check must execute and report a nonzero HALT. Taxonomy credit: the
author's group, TENDRA and the Write Hammer draft.
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
from attack_runner import flags  # noqa: E402
from attacks import load_cases  # noqa: E402
from mutants.attack_mutants import FILE, OLD, NEW  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kind", action="append", required=True)
    args = ap.parse_args()
    cases = [case for case in load_cases() if case.kind in args.kind]
    if not cases:
        ap.error("no matching case")
    base = ROOT / "work" / "attack_mutant_control"
    rtl = base / "rtl"
    shutil.rmtree(base, ignore_errors=True)
    shutil.copytree(ROOT / "rtl", rtl)
    path = rtl / FILE
    source = path.read_text()
    assert source.count(OLD) == 1
    path.write_text(source.replace(OLD, NEW))
    env = dict(os.environ, RTL_DIR=str(rtl), WORK_ROOT=str(base / "work"))
    for case in cases:
        out = base / case.id
        out.mkdir(parents=True, exist_ok=True)
        build_env = dict(os.environ, CFLAGS_EXTRA=" ".join(flags(case)))
        build = subprocess.run([sys.executable, str(ROOT / "sw" / "build.py"),
                                str(out), str(case.source)], env=build_env,
                               capture_output=True, text=True)
        if build.returncode:
            raise AssertionError(build.stdout + build.stderr)
        code = ("import sys; sys.path.insert(0, " + repr(str(ROOT / "tests")) + ")\n"
                "from vl_runner import run_image_vl\n"
                f"r=run_image_vl({str(out / 'program.hex')!r}, caches=1, lat=20, "
                f"name='scoped_{case.id}', maxcyc=20000000)\n"
                "print('MUTANT_RESULT',r['halt'],r['timeout'])\n")
        run = subprocess.run([sys.executable, "-c", code], env=env,
                             capture_output=True, text=True)
        lines = [s for s in run.stdout.splitlines() if s.startswith("MUTANT_RESULT ")]
        if run.returncode or len(lines) != 1:
            raise AssertionError(run.stdout[-500:] + run.stderr[-500:])
        _, halt, timeout = lines[0].split()
        if timeout != "False" or halt in ("0", "None"):
            raise AssertionError(f"{case.id}: self-check did not reject mutant: {lines[0]}")
        print(f"PASS {case.id}: broken D$ produced self-check HALT {halt}", flush=True)
    print(f"[attack-mutant-control] {len(cases)}/{len(cases)} passed", flush=True)


if __name__ == "__main__":
    main()
