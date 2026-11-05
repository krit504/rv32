"""Compute the Section 4 wear scalars from a run's raw line CSV and log.

The full matrix does not make per-run PNGs; Section 8 figures are generated
later from normalized CSV. Data-array writes exclude metadata writes.
"""
import csv
import hashlib
import json
from pathlib import Path
import re

ENDURANCE = 10**15


def summarize(run_dir):
    run_dir = Path(run_dir)
    line_path = run_dir / "wear_lines.csv"
    lines = list(csv.DictReader(line_path.open()))
    indices = [int(row["line"]) for row in lines]
    if indices != list(range(len(indices))) or not lines:
        raise ValueError("wear line CSV is incomplete")
    counts = [int(row["count"]) for row in lines]
    log = (run_dir / "simulation.log").read_text()
    match = re.search(r"^WEAR cycles=(\d+) fills=(\d+) stores=(\d+)$", log, re.M)
    if not match:
        raise ValueError("missing WEAR event totals")
    cycles, fills, stores = map(int, match.groups())
    total = sum(counts)
    if total != fills + stores:
        raise ValueError("wear count does not match event totals")
    wmax = max(counts)
    written = [x for x in counts if x]
    result = {"array_writes": total, "w_max": wmax,
              "mean_all": total / len(counts),
              "pmr_all": wmax * len(counts) / total if total else None,
              "pmr_written": wmax * len(written) / total if total else None,
              "t_fail_extrapolated_seconds": {
                  str(mhz): ENDURANCE * cycles / (wmax * mhz * 1_000_000) if wmax else None
                  for mhz in (50, 100, 500)}}
    out = run_dir / "eval_wear_summary.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    sidecar = {"script": "analysis/eval_wear_stats.py",
               "line_csv_sha256": hashlib.sha256(line_path.read_bytes()).hexdigest(),
               "simulation_sha256": hashlib.sha256((run_dir / "simulation.log").read_bytes()).hexdigest(),
               "summary_sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
    (run_dir / "eval_wear_summary.json.json").write_text(json.dumps(sidecar, indent=2) + "\n")
    return result
