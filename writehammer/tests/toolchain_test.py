"""toolchain_test.py: the C build flow and the core agree with a native build (T1.4).

Inputs: sw/smoke/checksum.c. Output: PASS/FAIL lines and "[toolchain] n/n passed"; exit 0 only if
all pass.
Oracle: the same C source compiled natively with the host gcc (-O0 and -O2) and run on the host.
It uses a different compiler and a different ISA from both the RISC-V build and the RTL, and the
-O0 and -O2 results must agree (no undefined behavior in the program). The expected exit code is
that value, never anything taken from RTL output.
Checks:
  - sw/build.py builds the program (rv32i architecture attribute, RV32I-only instructions)
  - the linked image has real .data and .bss (nm), so the test cannot pass by never touching them
  - the core halts with exactly the oracle's value, caches off and caches on at LAT 1, 2, 3, 10
  - control: without loading the data image the result differs (so .data is genuinely exercised)
  - build.py rejects a program using a non-RV32I instruction (a multiply with -march=rv32im)
Does not check: timing.
"""
import os
import subprocess
import sys
from paths import ROOT, work_dir
from image_runner import run_image

W = work_dir("toolchain")
SMOKE = os.path.join(ROOT, "sw", "smoke", "checksum.c")
fails = []


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


# ---- native oracle ----
drv = os.path.join(W, "drv.c")
open(drv, "w").write('#include <stdio.h>\nint prog_main(void);\nint main(void){ printf("%d\\n", prog_main()); return 0; }\n')
vals = []
for opt in ("-O0", "-O2"):
    obj, exe = os.path.join(W, f"cs{opt}.o"), os.path.join(W, f"cs{opt}")
    r = sh(["gcc", opt, "-Dmain=prog_main", "-w", "-c", SMOKE, "-o", obj]); assert r.returncode == 0, r.stderr
    r = sh(["gcc", drv, obj, "-o", exe]); assert r.returncode == 0, r.stderr
    vals.append(int(sh([exe]).stdout))
if vals[0] != vals[1]:
    fails.append(f"native -O0 ({vals[0]}) and -O2 ({vals[1]}) disagree: the program has undefined behavior")
expected = vals[0]
print(f"native oracle: {expected}")

# ---- build ----
r = sh([sys.executable, os.path.join(ROOT, "sw", "build.py"), os.path.join(W, "smoke"), SMOKE])
if r.returncode:
    fails.append("build failed: " + (r.stdout + r.stderr).strip())
else:
    nm = sh(["riscv64-unknown-elf-nm", os.path.join(W, "smoke", "prog.elf")]).stdout
    kinds = {ln.split()[2]: ln.split()[1] for ln in nm.splitlines() if len(ln.split()) == 3}
    if kinds.get("counter") not in ("d", "D") or kinds.get("table") not in ("d", "D"):
        fails.append(f"counter/table not in .data (nm kinds: counter={kinds.get('counter')}, table={kinds.get('table')})")
    if kinds.get("scratch") not in ("b", "B"):
        fails.append("scratch not in .bss")
    hexf = os.path.join(W, "smoke", "program.hex")
    for caches, lat in ((0, 2), (1, 1), (1, 2), (1, 3), (1, 10)):
        res = run_image(hexf, caches=caches, lat=lat, name="smoke")
        if res["timeout"] or res["halt"] != expected:
            fails.append(f"caches={caches} lat={lat}: halt={res['halt']} timeout={res['timeout']} expected {expected}")

    # control: with the data memory NOT loaded from the image the program must give a different
    # answer, otherwise this test would pass even if .data were never loaded
    ctl = run_image(hexf, caches=0, lat=2, name="smoke_noimage", image=0)
    if ctl["halt"] == expected:
        fails.append("control run without the data image still matches the oracle: .data is not exercised")

# ---- negative: build.py must reject non-RV32I code ----
bad = os.path.join(W, "bad_mul.c")
open(bad, "w").write("int main(void){ volatile int a = 3, b = 5; int c; __asm__ volatile (\"mul %0, %1, %2\" : \"=r\"(c) : \"r\"(a), \"r\"(b)); return c; }\n")
r = sh([sys.executable, os.path.join(ROOT, "sw", "build.py"), os.path.join(W, "bad"), bad],
       env=dict(os.environ, CFLAGS_EXTRA="-march=rv32im_zicsr"))
# -march given twice: the later one wins in gcc, so the assembler accepts `mul`; build.py must then refuse
if r.returncode == 0 or "non-RV32I" not in (r.stdout + r.stderr) and "architecture" not in (r.stdout + r.stderr):
    fails.append(f"build.py accepted a program using mul (rc={r.returncode}): {(r.stdout + r.stderr).strip()[:200]}")

total = 2 + 5 + 1 + 1 + 1
for ln in fails: print("FAIL " + ln)
print(f"[toolchain] {total - len(fails)}/{total} passed")
sys.exit(1 if fails else 0)
