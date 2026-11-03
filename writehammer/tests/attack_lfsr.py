"""Known-answer LFSR check on native GCC and RV32I, with a broken-tap control.

Usage: python3 tests/attack_lfsr.py
Inputs: sw/attacks/lfsr.h, lfsr_known.c. Outputs under work/attack_lfsr/.
The six expected states are literals in the C test, derived from the polynomial.
This test does not define the RLA/RTA/RnLA/RnTA taxonomy; that prior work is
from the author's group (TENDRA and the Write Hammer draft).
"""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
from wear_run import run  # noqa: E402


def command(argv, **kwargs):
    result = subprocess.run(argv, capture_output=True, text=True, **kwargs)
    if result.returncode:
        raise AssertionError(f"command failed {argv}: {result.stdout[-500:]} {result.stderr[-500:]}")
    return result


def main():
    sources = ROOT / "sw" / "attacks"
    work = ROOT / "work" / "attack_lfsr"
    work.mkdir(parents=True, exist_ok=True)
    native = work / "lfsr_native"
    command(["gcc", "-O2", "-std=c99", "-Wall", "-Wextra", "-Werror", "-DNATIVE",
             str(sources / "lfsr_known.c"), "-o", str(native)])
    command([str(native)])
    print("PASS native known-answer sequence")

    build = work / "rv32i"
    command([sys.executable, str(ROOT / "sw" / "build.py"), str(build),
             str(sources / "lfsr_known.c")])
    run(build / "program.hex", work / "rtl", maxcyc=100000, lat=20)
    print("PASS RV32I known-answer sequence")

    broken = work / "broken"
    broken.mkdir(exist_ok=True)
    header = (sources / "lfsr.h").read_text()
    assert header.count("0x80200003u") == 1
    (broken / "lfsr.h").write_text(header.replace("0x80200003u", "0x80200001u"))
    shutil.copyfile(sources / "lfsr_known.c", broken / "lfsr_known.c")
    mutant = broken / "lfsr_mutant"
    command(["gcc", "-O2", "-std=c99", "-Wall", "-Wextra", "-Werror", "-DNATIVE",
             str(broken / "lfsr_known.c"), "-o", str(mutant)])
    result = subprocess.run([str(mutant)], capture_output=True, text=True)
    if result.returncode == 0:
        raise AssertionError("broken-tap LFSR passed the known-answer test")
    print(f"PASS native broken-tap control rejected with exit {result.returncode}")
    mutant_build = broken / "rv32i"
    command([sys.executable, str(ROOT / "sw" / "build.py"), str(mutant_build),
             str(broken / "lfsr_known.c")])
    run(mutant_build / "program.hex", broken / "rtl", maxcyc=100000, lat=20,
        expect_exit=result.returncode)
    print(f"PASS RV32I broken-tap control rejected with exit {result.returncode}")
    print("[attack-lfsr] 4/4 passed")


if __name__ == "__main__":
    main()
