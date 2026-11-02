"""Attack self-checks on host and RV32I, with a broken D$ store control.

Usage: python3 tests/attack_program.py --kind RLA [--kind RTA ...]
The named attack taxonomy is prior work of the author's group (TENDRA and the
Write Hammer draft). The C self-check detects the C5 stale-store core mutant.
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
from mutants.core_mutants import MUTANTS  # noqa: E402
from vl_runner import run_image_vl  # noqa: E402


def command(argv, env=None):
    result = subprocess.run(argv, env=env, capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(f"failed {argv}: {result.stdout[-400:]} {result.stderr[-400:]}")


def check_case(case, mutant_rtl):
    out = ROOT / "work" / "attack_program" / case.id
    out.mkdir(parents=True, exist_ok=True)
    args = flags(case)
    native = out / "native"
    command(["gcc", "-O2", "-std=gnu99", "-Wall", "-Wextra", "-DNATIVE",
             *args, str(case.source), "-o", str(native)])
    command([str(native)])
    env = dict(os.environ, CFLAGS_EXTRA=" ".join(args))
    command([sys.executable, str(ROOT / "sw" / "build.py"), str(out), str(case.source)], env=env)
    image = out / "program.hex"
    for caches, lat in ((0, 1), (1, 20)):
        result = run_image_vl(str(image), caches=caches, lat=lat,
                              name=f"attack_{case.id}", maxcyc=20_000_000)
        assert not result["timeout"] and result["halt"] == 0, (case.id, caches, lat, result)
    code = ("import sys; sys.path.insert(0, " + repr(str(ROOT / "tests")) + ")\n"
            "from vl_runner import run_image_vl\n"
            f"r=run_image_vl({str(image)!r}, caches=1, lat=20, "
            f"name='mut_{case.id}', maxcyc=20000000)\n"
            "print('MUTANT_RESULT',r['halt'],r['timeout'])\n")
    menv = dict(os.environ, RTL_DIR=str(mutant_rtl),
                WORK_ROOT=str(ROOT / "work" / "attack_program" / "mutant_work"))
    broken = subprocess.run([sys.executable, "-c", code], env=menv,
                            capture_output=True, text=True)
    lines = [s for s in broken.stdout.splitlines() if s.startswith("MUTANT_RESULT ")]
    if broken.returncode or len(lines) != 1:
        raise AssertionError(f"mutant run failed: {broken.stdout[-400:]} {broken.stderr[-400:]}")
    _, halt, timeout = lines[0].split()
    if halt == "0" and timeout == "False":
        raise AssertionError(f"C5 mutant escaped {case.id} self-check")
    print(f"PASS {case.id}: native, caches off/on, C5 rejected ({halt}, {timeout})", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kind", action="append", required=True)
    args = ap.parse_args()
    cases = [case for case in load_cases() if case.kind in args.kind]
    if not cases:
        ap.error("no matching cases")
    base = ROOT / "work" / "attack_program" / "mutant"
    rtl = base / "rtl"
    shutil.rmtree(base, ignore_errors=True)
    shutil.copytree(ROOT / "rtl", rtl)
    mutant = next(m for m in MUTANTS if m[0] == "C5_store_hit_no_line_update")
    path = rtl / mutant[1]
    source = path.read_text()
    assert source.count(mutant[2]) == 1
    path.write_text(source.replace(mutant[2], mutant[3]))
    for case in cases:
        check_case(case, rtl)
    print(f"[attack-program] {len(cases)}/{len(cases)} passed", flush=True)


if __name__ == "__main__":
    main()
