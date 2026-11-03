"""Build and check 1M benign / 1M attack / 1M benign cycle runs.

Usage: .venv/bin/python analysis/attack_mixed.py [--kind RLA ...] [--probe]
Taxonomy credit: the author's group, TENDRA and the Write Hammer draft.
"""
import argparse
import csv
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from attacks import load_cases  # noqa: E402
from prog_runner import parse_output  # noqa: E402
from attack_runner import flags  # noqa: E402
from wear_run import run  # noqa: E402
from wear_replay import replay  # noqa: E402
from wear_stats import main as wear_stats  # noqa: E402

KINDS = {"RLA": 1, "RTA": 2, "RnLA": 3, "RnTA": 4}


def command(argv, env=None):
    result = subprocess.run(argv, env=env, capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(f"failed {argv}: {result.stdout[-400:]} {result.stderr[-400:]}")


def check_phases(phases, tolerance=0.01):
    if [value for value, _ in phases] != [0, 1, 2, 3]:
        raise AssertionError(f"wrong PHASE sequence: {phases}")
    gaps = [phases[i + 1][1] - phases[i][1] for i in range(3)]
    for i, gap in enumerate(gaps):
        if abs(gap - 1_000_000) > 1_000_000 * tolerance:
            raise AssertionError(f"phase {i} has {gap} cycles, expected 1M ± {tolerance:.0%}")
    return gaps


def one(kind, benign_iterations, probe):
    base_case = next(c for c in load_cases() if c.kind == kind and c.form == "direct" and c.seed == 1)
    case = replace(base_case, run_cycles=1_000_000)
    out = ROOT / "work" / "attack_mixed" / kind.lower()
    build = out / "build"
    build.mkdir(parents=True, exist_ok=True)
    extra = flags(case) + [f"-DATTACK_KIND={KINDS[kind]}",
                           f"-DBENIGN_ITERATIONS={benign_iterations}"]
    source = ROOT / "sw" / "attacks" / "mixed.c"
    native = build / "native"
    command(["gcc", "-O2", "-std=gnu99", "-DNATIVE", *extra,
             str(source), "-o", str(native)])
    command([str(native)])
    env = dict(os.environ, CFLAGS_EXTRA=" ".join(extra))
    command([sys.executable, str(ROOT / "sw" / "build.py"), str(build), str(source)], env=env)
    wear = run(build / "program.hex", out / "wear", maxcyc=8_000_000, lat=20)
    parsed = parse_output((wear / "simulation.log").read_text())
    if parsed["halt"] != 0 or parsed["timeout"]:
        raise AssertionError(f"mixed {kind} did not HALT 0")
    phases = parsed["phases"]
    if probe:
        gaps = [phases[i + 1][1] - phases[i][1] for i in range(3)]
    else:
        gaps = check_phases(phases)
    replay(wear, 2048, 16)
    wear_stats(wear)
    print(f"mixed {kind}: markers={phases} gaps={gaps}", flush=True)
    return {"kind": kind, "benign_iterations": benign_iterations,
            "phase_0": phases[0][1], "phase_1": phases[1][1],
            "phase_2": phases[2][1], "phase_3": phases[3][1],
            "benign_a_cycles": gaps[0], "attack_cycles": gaps[1],
            "benign_b_cycles": gaps[2], "halt": parsed["halt"]}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kind", action="append", choices=KINDS, default=[])
    ap.add_argument("--benign-iterations", type=int, default=100000)
    ap.add_argument("--probe", action="store_true")
    args = ap.parse_args()
    if args.benign_iterations <= 0:
        ap.error("benign iterations must be positive")
    # Known-bad controls establish that the marker check rejects broken logs.
    for bad in ([(0, 0), (1, 1_000_000), (3, 2_000_000), (2, 3_000_000)],
                [(0, 0), (1, 500_000), (2, 1_500_000), (3, 2_500_000)]):
        try:
            check_phases(bad)
        except AssertionError:
            pass
        else:
            raise AssertionError("broken phase control escaped validation")
    rows = [one(kind, args.benign_iterations, args.probe)
            for kind in (args.kind or list(KINDS))]
    if args.probe:
        return
    table = ROOT / "analysis" / "attack_mixed.csv"
    with table.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    digest = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    sidecar = {"script": "analysis/attack_mixed.py",
               "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                                     cwd=ROOT, text=True).strip(),
               "table_sha256": digest(table),
               "source_sha256": {str(p.relative_to(ROOT)): digest(p)
                                 for p in (ROOT / "sw/attacks/mixed.c",
                                           ROOT / "sw/attacks/attack_core.h")},
               "taxonomy_credit": "Author's group: TENDRA and the Write Hammer draft"}
    Path(str(table) + ".json").write_text(json.dumps(sidecar, indent=2) + "\n")
    print(f"[attack-mixed] {len(rows)}/{len(rows)} marker sequences passed: {table}")


if __name__ == "__main__":
    main()
