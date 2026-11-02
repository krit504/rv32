"""build_coremark.py: build CoreMark 1.0 (eembc/coremark, pinned in docs/TOOLS.md) for this core.

Usage:   python3 sw/coremark/build_coremark.py OUT_DIR [ITERATIONS]      (default 10 iterations)
Output:  OUT_DIR/program.hex (+ the files sw/build.py writes).
Port:    derived from the stock `barebones` port with these patches and nothing else:
  core_portme.c  - the two `#error` blocks (clock, board init) are replaced: start_time/stop_time open
                   and close the MMIO measurement window (counted by tb/sys_monitor.sv); get_time
                   returns 0 and EE_TICKS_PER_SEC is 1 (this core has no readable clock); no board
                   init is needed.
  core_portme.h  - includes <stddef.h> (size_t); `main` is renamed coremark_main so sw/coremark/wrapper.c can supply main (see
                   there). Everything else is configured with -D flags: HAS_FLOAT=0, HAS_TIME_H=0,
                   USE_CLOCK=0, HAS_PRINTF=1 (printf is sw/rt.c), MEM_METHOD=MEM_STATIC,
                   ITERATIONS=N, PERFORMANCE_RUN seeds (TOTAL_DATA_SIZE 2000).
Compiler flags: -O2, rv32i (mul/div by libgcc software routines): results are rv32i, not rv32im.
  -fno-isolate-erroneous-paths-dereference: at -O2 GCC 13 proves a null dereference on one path in
  core_list_mergesort and core_bench_list and replaces it with `sw zero,0(zero); ebreak`. Those paths
  are never executed by a correct run, but ebreak is not an RV32I instruction this core implements and
  sw/build.py rejects it. The flag only stops GCC inserting that trap; valid paths are unchanged.
CoreMark/MHz is computed outside the program from the monitor's cycle count (analysis/baseline.py).
Exit code: the number of CoreMark CRC-error messages (sw/coremark/wrapper.c); 0 = every CRC matched.
"""
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CM = os.path.join(ROOT, "third_party", "coremark")


def patch(text, old, new, what):
    if text.count(old) != 1:
        sys.exit(f"build_coremark.py: patch point '{what}' found {text.count(old)} times (pinned source changed?)")
    return text.replace(old, new)


def main():
    out = sys.argv[1]
    iters = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    src = os.path.join(out, "src")
    shutil.rmtree(src, ignore_errors=True)
    os.makedirs(src)
    for f in ("core_main.c", "core_list_join.c", "core_matrix.c", "core_state.c", "core_util.c", "coremark.h"):
        shutil.copy(os.path.join(CM, f), src)
    h = open(os.path.join(CM, "barebones", "core_portme.h")).read()
    h = patch(h, "#define CORE_PORTME_H", "#define CORE_PORTME_H\n#include <stddef.h>   /* port: ee_size_t is size_t, freestanding header */", "header guard")
    h = patch(h, "#endif /* CORE_PORTME_H */", "/* port: sw/coremark/wrapper.c supplies main and interprets coremark_main's result */\n#define main coremark_main\n#endif /* CORE_PORTME_H */", "header end")
    open(os.path.join(src, "core_portme.h"), "w").write(h)

    c = open(os.path.join(CM, "barebones", "core_portme.c")).read()
    c = re.sub(r"CORETIMETYPE\nbarebones_clock\(\)\n\{\n#error.*?\n\}", "CORETIMETYPE\nbarebones_clock()\n{\n    return 0;   /* unused: timing is the MMIO measurement window, see start_time/stop_time */\n}", c, count=1, flags=re.S)
    c = patch(c, "#define EE_TICKS_PER_SEC           (CLOCKS_PER_SEC / TIMER_RES_DIVIDER)", "#define EE_TICKS_PER_SEC           1", "ticks per sec")
    c = patch(c, "    GETMYTIME(&start_time_val);", "    perf_start();   /* open the MMIO measurement window */\n    GETMYTIME(&start_time_val);", "start_time")
    c = patch(c, "    GETMYTIME(&stop_time_val);", "    perf_stop();    /* close it */\n    GETMYTIME(&stop_time_val);", "stop_time")
    c = re.sub(r'#error \\\n\s+"Call board initialization routines in portable init \(if needed\), in particular initialize UART!\\n"', "    /* no board initialization needed in simulation */", c, count=1)
    if "#error" in c:
        sys.exit("build_coremark.py: a #error is left in core_portme.c")
    c = f'#include "{os.path.join(ROOT, "sw", "mmio.h")}"\n' + c    # absolute: the output directory varies
    open(os.path.join(src, "core_portme.c"), "w").write(c)

    flags = (f"-std=gnu99 -w -fno-isolate-erroneous-paths-dereference -I{src} -DHAS_FLOAT=0 -DHAS_TIME_H=0 -DUSE_CLOCK=0 -DHAS_PRINTF=1 "
             f"-DMEM_METHOD=MEM_STATIC -DITERATIONS={iters} -DFLAGS_STR=\"-O2\" -DTOTAL_DATA_SIZE=2000")
    env = dict(os.environ, CFLAGS_EXTRA=flags, LDLIBS_EXTRA="-lc")
    srcs = [os.path.join(src, f) for f in ("core_main.c", "core_list_join.c", "core_matrix.c", "core_state.c",
                                           "core_util.c", "core_portme.c")]
    cmd = [sys.executable, os.path.join(ROOT, "sw", "build.py"), out] + srcs + [
        os.path.join(HERE, "wrapper.c"), os.path.join(ROOT, "sw", "rt.c")]
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    print(r.stdout + r.stderr, end="")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
