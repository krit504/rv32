"""vl_tb.py: build and run any testbench under Verilator, cached and safe for parallel callers.

Usage:  from vl_tb import run_tb
        out = run_tb("tb_dcache", [files...], params={"NOPS": 1500, ...}, cwd=run_dir)
Builds (once per distinct source hash + parameters + Verilator version) with `--binary --timing`,
top-level parameters set with -G, under work/vltb/<hash>/ (exclusive file lock, atomic rename), then
runs the binary in `cwd` and returns its stdout. Used by tests whose Icarus runs are too slow
(Icarus 12 evaluates the large cache arrays very slowly).
"""
import fcntl
import hashlib
import os
import shutil
import subprocess
from paths import work_dir


def _build(top, srcs, params):
    h = hashlib.sha256()
    for s in srcs:
        h.update(open(s, "rb").read())
    ver = subprocess.run(["verilator", "--version"], capture_output=True, text=True).stdout.strip()
    h.update(f"{top},{sorted(params.items())},{ver}".encode())
    d = work_dir(f"vltb/{top}_{h.hexdigest()[:14]}")
    exe = os.path.join(d, "Vsim")
    with open(os.path.join(d, ".lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not os.path.exists(exe):
            r = subprocess.run(["verilator", "--binary", "--timing", "-Wno-fatal", "-Wno-lint", "-Wno-style", "-j", "2",
                                "--top-module", top, "-Mdir", os.path.join(d, "obj"), "-o", "Vsim"]
                               + [f"-G{k}={v}" for k, v in params.items()] + list(srcs), capture_output=True, text=True)
            if r.returncode:
                raise RuntimeError("verilator build failed:\n" + r.stderr[-1500:])
            shutil.copy(os.path.join(d, "obj", "Vsim"), exe + ".tmp")
            os.replace(exe + ".tmp", exe)
    return exe


def run_tb(top, srcs, params, cwd):
    exe = _build(top, srcs, params)
    return subprocess.run([exe], cwd=cwd, capture_output=True, text=True).stdout
