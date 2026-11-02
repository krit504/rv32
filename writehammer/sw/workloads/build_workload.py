"""build_workload.py: build one of the in-repo benign workloads (T1.8).

Usage:   python3 sw/workloads/build_workload.py NAME OUT_DIR     NAME in {memcpy_big, memset_big, storeloop}
Output:  OUT_DIR/program.hex. The program's exit code is its self-check's error count (0 = correct).
Flags:   -O2 rv32i, libc (newlib memcpy/memset of the rv32i_zicsr multilib; the ELF check in sw/build.py
         still guarantees RV32I-only instructions).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def main():
    name, out = sys.argv[1], sys.argv[2]
    src = os.path.join(HERE, name + ".c")
    if not os.path.exists(src):
        sys.exit(f"build_workload.py: no workload '{name}'")
    env = dict(os.environ, CFLAGS_EXTRA="-std=gnu99", LDLIBS_EXTRA="-lc")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "sw", "build.py"), out, src], env=env, capture_output=True, text=True)
    print(r.stdout + r.stderr, end="")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
