"""Run golden wear replay across the benign registry and supplied attack images.

Usage: python3 analysis/wear_replay_suite.py [--benign] [--image NAME=HEX]...
Builds selected benign workloads using analysis/baseline.py's registry, runs each
with tb_wear and checks exit/self-check plus exact golden replay. Additional attack
images can be supplied when T4 creates them. Outputs live under work/wear_suite/.
"""
import argparse
from pathlib import Path
import re
import threading
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from prog_runner import parse_output  # noqa: E402
from wear_run import run  # noqa: E402
from wear_replay import replay  # noqa: E402


def heartbeat(stop, name):
    while not stop.wait(30):
        print(f"wear replay still running: {name}", flush=True)


def checked_run(name, image, check=None):
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    d = ROOT / "work" / "wear_suite" / safe
    print(f"wear replay starting: {name}", flush=True)
    stop = threading.Event()
    thread = threading.Thread(target=heartbeat, args=(stop, name), daemon=True)
    thread.start()
    try:
        run(image, d, maxcyc=500_000_000, window=10000, lat=20)
        if check:
            err = check(parse_output((d / "simulation.log").read_text()))
            if err:
                raise AssertionError(f"{name} self-check: {err}")
        replay(d)
    finally:
        stop.set()
        thread.join()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--benign", action="store_true")
    ap.add_argument("--image", action="append", default=[], metavar="NAME=HEX")
    ap.add_argument("--name", action="append", default=[], help="restrict benign registry for a diagnostic run")
    args = ap.parse_args()
    n = 0
    if args.benign:
        from baseline import workloads
        for name, _cls, image, check, _rate in workloads():
            if args.name and name.split()[0].lower() not in [x.lower() for x in args.name]:
                continue
            checked_run(name, image, check)
            n += 1
    for entry in args.image:
        name, path = entry.split("=", 1)
        checked_run(name, path)
        n += 1
    if n == 0:
        ap.error("select --benign or provide --image NAME=HEX")
    print(f"[wear-replay-suite] {n}/{n} passed", flush=True)


if __name__ == "__main__":
    main()
