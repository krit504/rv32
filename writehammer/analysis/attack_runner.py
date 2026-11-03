"""Build, self-check and measure attack cases from the author-defined registry.

Usage: .venv/bin/python analysis/attack_runner.py [--case CASE_ID]...
       [--dc-bytes 2048] [--line-bytes 16]
Requires sw/attacks/manifest.json and attack C sources; they remain absent until
the author defines L, T and Rn. For each selected case, native GCC is an
independent self-check oracle, sw/build.py rejects non-RV32I instructions, and
the cached Verilator run must HALT 0. Golden replay and wear statistics follow.
Outputs: work/attack_run/CASE_ID/{build,wear}/ at primary geometry, with a
geometry subdirectory for sweeps. This runner implements no
attack behavior. The taxonomy belongs to the author's group (TENDRA and the
Write Hammer draft).
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from attacks import load_cases  # noqa: E402
from paths import CORE_RTL, TB  # noqa: E402
from prog_runner import parse_output  # noqa: E402
from vl_tb import run_tb  # noqa: E402
from wear_replay import replay  # noqa: E402
from wear_stats import main as wear_stats  # noqa: E402


def heartbeat(stop, name):
    while not stop.wait(30):
        print(f"attack runner still working: {name}", flush=True)


def run_command(argv, *, env=None):
    result = subprocess.run(argv, env=env, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"command failed: {argv}\n{result.stdout[-700:]}\n{result.stderr[-700:]}")


def flags(case, dc_bytes=2048, line_bytes=16):
    values = {"ATTACK_FORM_DIRECT": int(case.form == "direct"),
              "ATTACK_DCACHE_BYTES": dc_bytes, "ATTACK_LINE_BYTES": line_bytes,
              "ATTACK_LOCATIONS": case.locations, "ATTACK_DWELL_MIN": case.dwell_min,
              "ATTACK_DWELL_MAX": case.dwell_max, "ATTACK_RUN_CYCLES": case.run_cycles,
              "ATTACK_SEED": case.seed}
    return [f"-D{k}={v}" for k, v in values.items()]


def run_wear_geometry(image, outdir, dc_bytes, line_bytes):
    outdir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(image, outdir / "program.hex")
    sources = CORE_RTL + [os.path.join(TB, name) for name in
                          ("sys_monitor.sv", "wear_monitor.sv", "tb_wear.sv")]
    output = run_tb("tb_wear", sources,
                    {"MAXCYC": 20_000_000, "MEMW": 65536, "LAT": 20,
                     "WINDOW_CYCLES": 10_000, "DCACHE_BYTES": dc_bytes,
                     "LINE_BYTES": line_bytes}, str(outdir))
    (outdir / "simulation.log").write_text(output)
    parsed = parse_output(output)
    if parsed["halt"] != 0 or parsed["timeout"] or "DC_CNT " not in output:
        raise AssertionError(f"bad HALT/cache output: {outdir / 'simulation.log'}")
    return outdir, parsed


def one(case, dc_bytes, line_bytes):
    root = ROOT / "work" / "attack_run" / case.id
    d = root if (dc_bytes, line_bytes) == (2048, 16) else root / f"dc{dc_bytes}_line{line_bytes}"
    build = d / "build"
    build.mkdir(parents=True, exist_ok=True)
    cflags = flags(case, dc_bytes, line_bytes)
    stop = threading.Event()
    thread = threading.Thread(target=heartbeat, args=(stop, case.id), daemon=True)
    thread.start()
    print(f"attack runner starting: {case.id}", flush=True)
    try:
        native = build / "native"
        run_command(["gcc", "-O2", "-std=gnu99", "-DNATIVE", *cflags,
                     str(case.source), "-o", str(native)])
        run_command([str(native)])
        env = dict(os.environ)
        env["CFLAGS_EXTRA"] = " ".join([env.get("CFLAGS_EXTRA", ""), "-std=gnu99", *cflags]).strip()
        run_command([sys.executable, str(ROOT / "sw" / "build.py"), str(build),
                     str(case.source)], env=env)
        wear, output = run_wear_geometry(build / "program.hex", d / "wear", dc_bytes, line_bytes)
        if output["halt"] != 0 or output["timeout"] or output["perf"] is None:
            raise AssertionError(f"{case.id}: bad HALT/PERF output")
        replay(wear, dc_bytes, line_bytes)
        wear_stats(wear)
        print(f"attack runner PASS: {case.id}, measured cycles={output['perf']['cycles']}", flush=True)
    finally:
        stop.set()
        thread.join()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", action="append", default=[], help="case ID; default all")
    ap.add_argument("--dc-bytes", type=int, default=2048)
    ap.add_argument("--line-bytes", type=int, default=16)
    args = ap.parse_args()
    if (args.dc_bytes <= 0 or args.line_bytes <= 0 or args.dc_bytes % args.line_bytes
            or args.dc_bytes & (args.dc_bytes - 1) or args.line_bytes & (args.line_bytes - 1)):
        ap.error("cache and line bytes must be positive powers of two, with whole lines")
    cases = load_cases()
    ids = {case.id for case in cases}
    if unknown := set(args.case) - ids:
        ap.error(f"unknown case IDs: {sorted(unknown)}")
    chosen = [case for case in cases if not args.case or case.id in args.case]
    for case in chosen:
        one(case, args.dc_bytes, args.line_bytes)
    print(f"[attack-runner] {len(chosen)}/{len(chosen)} passed", flush=True)


if __name__ == "__main__":
    main()
