"""vl_runner.py: run a linked program image on the core under Verilator (T1.7 onward).

Inputs: path to a program.hex from sw/build.py. Output: the dict of image_runner.run_image (halt
exit code, PERF columns, PHASE markers, PUTCHAR text, registers, cache counters, timeout flag) plus
"wall_s". Same testbench (tb/tb_prog.sv) and same monitor as the Icarus runs; Verilator is used
because the benchmarks run millions of cycles.
Usage: from vl_runner import run_image_vl;
       run_image_vl(hex_path, caches=0, lat=2, fwd=1, name="dhry", maxcyc=50_000_000)
Build cache: work/vl/<hash>/ (safe for parallel callers: file lock + atomic rename) where <hash> covers every rtl/ and tb/ source, the parameters and the
Verilator version, so a changed design always rebuilds (a stale binary is never reused).
Timeout: maxcyc only guards against a hung simulation; a timeout is a failure for the caller.
"""
import fcntl
import hashlib
import os
import shutil
import subprocess
import time
from paths import CORE_RTL, TB, work_dir
from prog_runner import parse_output

MEMW = 65536


def _build(caches, lat, fwd, memw, maxcyc):
    srcs = CORE_RTL + [os.path.join(TB, "sys_monitor.sv"), os.path.join(TB, "tb_prog.sv")]
    h = hashlib.sha256()
    for s in srcs:
        h.update(open(s, "rb").read())
    ver = subprocess.run(["verilator", "--version"], capture_output=True, text=True).stdout.strip()
    h.update(f"{caches},{lat},{fwd},{memw},{maxcyc},{ver}".encode())
    d = work_dir(f"vl/{h.hexdigest()[:16]}")
    exe = os.path.join(d, "Vtb_prog")
    # Several workers may ask for the same configuration at once: build under an exclusive lock and
    # move the finished binary into place atomically, so nobody runs or overwrites a half-built one.
    with open(os.path.join(d, ".lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not os.path.exists(exe):
            r = subprocess.run(["verilator", "--binary", "--timing", "-Wno-fatal", "-Wno-lint", "-Wno-style",
                                "-j", "4", "--top-module", "tb_prog", f"-GCACHES={caches}", f"-GLAT={lat}",
                                f"-GFWD={fwd}", f"-GMAXCYC={maxcyc}", f"-GMEMW={memw}", "-GIMAGE=1",
                                "-Mdir", os.path.join(d, "obj"), "-o", "Vtb_prog"] + srcs,
                               capture_output=True, text=True)
            if r.returncode:
                raise RuntimeError("verilator build failed:\n" + r.stderr[-1500:])
            shutil.copy(os.path.join(d, "obj", "Vtb_prog"), exe + ".tmp")
            os.replace(exe + ".tmp", exe)
    return exe


def run_image_vl(hex_path, caches=0, lat=2, fwd=1, name="img", maxcyc=50_000_000, memw=MEMW):
    exe = _build(caches, lat, fwd, memw, maxcyc)
    run_dir = work_dir(f"vlrun/{name}_c{caches}_l{lat}_f{fwd}")
    shutil.copy(hex_path, os.path.join(run_dir, "program.hex"))
    t0 = time.time()
    out = subprocess.run([exe], cwd=run_dir, capture_output=True, text=True).stdout
    r = parse_output(out)
    r["wall_s"] = time.time() - t0
    return r
