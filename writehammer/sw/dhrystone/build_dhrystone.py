"""build_dhrystone.py: build Dhrystone 2.2 (riscv-tests benchmarks/dhrystone, pinned in docs/TOOLS.md).

Usage:   python3 sw/dhrystone/build_dhrystone.py OUT_DIR [RUNS]
Output:  OUT_DIR/program.hex (and the files sw/build.py writes). RUNS defaults to the source's 500.
Method:  copies the three Dhrystone sources into OUT_DIR/src and applies these patches, nothing else:
  1. dhrystone.h: the `__riscv` timer block read the mcycle CSR, which this core does not have. Start
     and stop are now no-ops and Too_Small_Time is 0, so the loop runs once (RUNS iterations).
     Timing comes from the MMIO measurement window opened by setStats(1)/setStats(0) around the loop
     (sw/dhrystone/port.c), counted by tb/sys_monitor.sv.
  2. dhrystone_main.c: the rate printout divides by the measured time, which is meaningless without a
     timer; it is replaced by a self-check of every "should be" value the benchmark itself lists
     (Int_Glob 5, Bool_Glob 1, Ch_1_Glob 'A', ... Arr_2_Glob[8][7] == RUNS + 10), whose error count
     becomes main's return value and so the exit code.
  3. util.h is replaced by sw/dhrystone/shim_util.h (declares setStats only).
Dhrystone/MHz is computed outside the program from the monitor's cycle count (analysis/baseline.py).
"""
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(ROOT, "third_party", "riscv-tests", "benchmarks", "dhrystone")

CHECK = r'''
  {
    int e = 0;
    e += (Int_Glob != 5);
    e += (Bool_Glob != 1);
    e += (Ch_1_Glob != 'A');
    e += (Ch_2_Glob != 'B');
    e += (Arr_1_Glob[8] != 7);
    e += (Arr_2_Glob[8][7] != Number_Of_Runs + 10);
    e += (Ptr_Glob->Discr != 0);
    e += (Ptr_Glob->variant.var_1.Enum_Comp != 2);
    e += (Ptr_Glob->variant.var_1.Int_Comp != 17);
    e += (strcmp(Ptr_Glob->variant.var_1.Str_Comp, "DHRYSTONE PROGRAM, SOME STRING") != 0);
    e += (Next_Ptr_Glob->Discr != 0);
    e += (Next_Ptr_Glob->variant.var_1.Enum_Comp != 1);
    e += (Next_Ptr_Glob->variant.var_1.Int_Comp != 18);
    e += (strcmp(Next_Ptr_Glob->variant.var_1.Str_Comp, "DHRYSTONE PROGRAM, SOME STRING") != 0);
    e += (Int_1_Loc != 5);
    e += (Int_2_Loc != 13);
    e += (Int_3_Loc != 7);
    e += (Enum_Loc != 1);
    e += (strcmp(Str_1_Loc, "DHRYSTONE PROGRAM, 1'ST STRING") != 0);
    e += (strcmp(Str_2_Loc, "DHRYSTONE PROGRAM, 2'ND STRING") != 0);
    printf("DHRY_SELFCHECK errors=%d runs=%d\n", e, Number_Of_Runs);
    return e;
  }
'''


def patch(text, old, new, what):
    if text.count(old) != 1:
        sys.exit(f"build_dhrystone.py: patch point '{what}' found {text.count(old)} times (pinned source changed?)")
    return text.replace(old, new)


def main():
    out = sys.argv[1]
    runs = sys.argv[2] if len(sys.argv) > 2 else None
    src = os.path.join(out, "src")
    shutil.rmtree(src, ignore_errors=True)
    os.makedirs(src)
    for f in ("dhrystone.c", "dhrystone.h", "dhrystone_main.c"):
        shutil.copy(os.path.join(SRC, f), src)
    shutil.copy(os.path.join(HERE, "shim_util.h"), os.path.join(src, "util.h"))

    h = open(os.path.join(src, "dhrystone.h")).read()
    h = patch(h, '''#define HZ 1000000
#define Too_Small_Time 1
#define CLOCK_TYPE "rdcycle()"
#define Start_Timer() Begin_Time = read_csr(mcycle)
#define Stop_Timer() End_Time = read_csr(mcycle)''', '''#define HZ 1000000
#define Too_Small_Time 0
#define CLOCK_TYPE "MMIO measurement window"
#define Start_Timer() Begin_Time = 0
#define Stop_Timer() End_Time = 0''', "timer block")
    if runs:
        h = patch(h, "#define NUMBER_OF_RUNS\t\t500", f"#define NUMBER_OF_RUNS\t\t{int(runs)}", "run count")
    open(os.path.join(src, "dhrystone.h"), "w").write(h)

    m = open(os.path.join(src, "dhrystone_main.c")).read()
    m = re.sub(r"  Microseconds = \(\(User_Time / Number_Of_Runs\).*?  return 0;\n\}", lambda _: CHECK + "}", m, count=1, flags=re.S)
    if "DHRY_SELFCHECK" not in m:
        sys.exit("build_dhrystone.py: could not patch the end of main")
    m = patch(m, '#include "util.h"', '#include "util.h"\n#include <string.h>', "util include")
    open(os.path.join(src, "dhrystone_main.c"), "w").write(m)

    env = dict(os.environ, CFLAGS_EXTRA="-std=gnu99 -w -DREG=register" if False else "-std=gnu99 -w", LDLIBS_EXTRA="-lc")
    cmd = [sys.executable, os.path.join(ROOT, "sw", "build.py"), out,
           os.path.join(src, "dhrystone.c"), os.path.join(src, "dhrystone_main.c"),
           os.path.join(HERE, "port.c"), os.path.join(ROOT, "sw", "rt.c")]
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    print(r.stdout + r.stderr, end="")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
