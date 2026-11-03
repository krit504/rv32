"""Compute D$ wear statistics and figures from a monitor run.

Usage: python3 analysis/wear_stats.py RUN_DIR
Inputs: wear_lines.csv, wear_windows.csv, simulation.log in RUN_DIR.
Outputs: wear_summary.json/csv, wear_per_line.png, wear_heatmap.png and PNG
provenance sidecars. T_fail uses illustrative E=1e15 and measured run cycles.
"""
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ENDURANCE = 10**15


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(run_dir):
    d = Path(run_dir).resolve()
    line_csv, win_csv = d / "wear_lines.csv", d / "wear_windows.csv"
    lines = list(csv.DictReader(line_csv.open()))
    windows = list(csv.DictReader(win_csv.open()))
    indices = [int(row["line"]) for row in lines]
    counts = np.array([int(row["count"]) for row in lines], dtype=np.int64)
    if indices != list(range(len(indices))) or len(counts) == 0:
        raise ValueError("wear_lines.csv must contain each line exactly once in order")
    nwin = max((int(r["window"]) for r in windows), default=-1) + 1
    heat = np.zeros((len(counts), nwin), dtype=np.int64)
    seen = set()
    for row in windows:
        w, line, count = map(int, (row["window"], row["line"], row["count"]))
        if not (0 <= line < len(counts)) or (w, line) in seen:
            raise ValueError("invalid or duplicate window/line")
        heat[line, w] = count
        seen.add((w, line))
    if len(seen) != nwin * len(counts) or not np.array_equal(heat.sum(axis=1), counts):
        raise ValueError("window sums do not match per-line totals")
    log = (d / "simulation.log").read_text()
    m = re.search(r"^WEAR cycles=(\d+) fills=(\d+) stores=(\d+)$", log, re.M)
    if not m:
        raise ValueError("missing WEAR run length")
    cycles, fills, stores = map(int, m.groups())
    if int(counts.sum()) != fills + stores:
        raise ValueError("array-write kinds do not match wear totals")
    wmax = int(counts.max())
    mean_all = float(counts.mean())
    written = counts[counts > 0]
    mean_written = float(written.mean()) if len(written) else 0.0
    result = {"run_set_id": d.name, "cycles": cycles, "lines": len(counts),
              "written_lines": len(written), "array_writes": int(counts.sum()),
              "fills": fills, "store_merges": stores, "w_max": wmax,
              "mean_all": mean_all, "mean_written": mean_written,
              "pmr_all": wmax / mean_all if mean_all else None,
              "pmr_written": wmax / mean_written if mean_written else None,
              "endurance_assumed_writes": ENDURANCE,
              "t_fail_extrapolated_seconds": {
                  str(mhz): ENDURANCE * cycles / (wmax * mhz * 1_000_000) if wmax else None
                  for mhz in (50, 100, 500)}}
    (d / "wear_summary.json").write_text(json.dumps(result, indent=2) + "\n")
    with (d / "wear_summary.csv").open("w", newline="") as f:
        row = {k: v for k, v in result.items() if k != "t_fail_extrapolated_seconds"}
        row.update({f"t_fail_{mhz}mhz_s": result["t_fail_extrapolated_seconds"][str(mhz)]
                    for mhz in (50, 100, 500)})
        writer = csv.DictWriter(f, row.keys())
        writer.writeheader()
        writer.writerow(row)
    plt.figure(figsize=(11, 3.5))
    plt.bar(indices, counts, width=1)
    plt.xlabel("D$ line")
    plt.ylabel("Data-array writes")
    plt.tight_layout()
    plt.savefig(d / "wear_per_line.png", dpi=150)
    plt.close()
    plt.figure(figsize=(11, 5))
    plt.imshow(heat, aspect="auto", origin="lower", interpolation="nearest")
    plt.colorbar(label="Data-array writes")
    plt.xlabel("Window")
    plt.ylabel("D$ line")
    plt.tight_layout()
    plt.savefig(d / "wear_heatmap.png", dpi=150)
    plt.close()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    for name in ("wear_per_line.png", "wear_heatmap.png"):
        sidecar = {"script": "analysis/wear_stats.py", "git_commit": commit,
                   "source_csv_sha256": {line_csv.name: sha(line_csv), win_csv.name: sha(win_csv)},
                   "figure_sha256": sha(d / name), "run_set_id": d.name}
        (d / (name + ".json")).write_text(json.dumps(sidecar, indent=2) + "\n")
    print(f"wear stats: {d} w_max={wmax} PMR(all)={result['pmr_all']}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
