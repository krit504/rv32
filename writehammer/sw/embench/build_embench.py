"""build_embench.py: build one Embench-IoT kernel (embench/embench-iot, pinned in docs/TOOLS.md).

Usage:   python3 sw/embench/build_embench.py KERNEL OUT_DIR
Output:  OUT_DIR/program.hex. The kernel's main (support/main.c) returns !verify_benchmark(result),
         so exit code 0 means the kernel's own built-in check passed.
Port:    support/main.c, support/beebsc.c and support/board.c are compiled unmodified with the kernel's
         own sources; board hooks are sw/embench/boardsupport.c (measurement window around the timed
         call). Flags: -DCPU_MHZ=1 -DGLOBAL_SCALE_FACTOR=1 -DWARMUP_HEAT=1, -O2, rv32i (software
         multiply and divide; software floating point where a kernel uses it).
"""
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
EB = os.path.join(ROOT, "third_party", "embench-iot")


def main():
    kernel, out = sys.argv[1], sys.argv[2]
    srcs = sorted(glob.glob(os.path.join(EB, "src", kernel, "*.c")))
    if not srcs:
        sys.exit(f"build_embench.py: no sources for kernel '{kernel}'")
    srcs += [os.path.join(EB, "support", f) for f in ("main.c", "beebsc.c", "board.c")]
    flags = (f"-std=gnu99 -w -DCPU_MHZ=1 -DGLOBAL_SCALE_FACTOR=1 -DWARMUP_HEAT=1 -I{HERE} "
             f"-I{os.path.join(EB, 'support')} -I{os.path.join(EB, 'src', kernel)}")
    env = dict(os.environ, CFLAGS_EXTRA=flags, LDLIBS_EXTRA="-lc -lm")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "sw", "build.py"), out] + srcs, env=env, capture_output=True, text=True)
    print(r.stdout + r.stderr, end="")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
