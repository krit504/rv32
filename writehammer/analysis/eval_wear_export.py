"""Normalize measured per-line windows into a CSV for T6 plots.

Usage: python3 analysis/eval_wear_export.py
Reads only completed run artifacts named in analysis/results.csv. The output is
an input CSV to plots.py; it never invents missing line/window counts.
"""
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    result_path = ROOT / "analysis/results.csv"
    results = list(csv.DictReader(result_path.open()))
    rows = []
    sources = {}
    def selected(result):
        if result["icache_bytes"] != "2048" or result["dcache_bytes"] != "2048":
            return False
        if result["detector"] == "NONE":
            return result["workload_class"] in ("calibration", "held-out", "attack")
        return (result["workload_class"] == "attack"
                and result["window_cycles"] == "10000"
                and result["threshold_k"] == "2"
                and ((result["detector"] == "D1" and result["mode"] == "STATIC")
                     or (result["detector"] == "D2" and result["mode"] == "STATIC" and result["M"] == "16")
                     or (result["detector"] == "D3" and result["mode"] == "ADAPTIVE")))
    for result in results:
        if not selected(result):
            continue
        if result["icache_bytes"] in ("", "0") or result["correct"] != "1":
            continue
        path = ROOT / "work/eval/runs" / result["run_id"] / "wear_windows.csv"
        log_path = ROOT / "work/eval/runs" / result["run_id"] / "simulation.log"
        if not path.is_file():
            raise FileNotFoundError(f"missing measured wear windows for {result['run_id']}: {path}")
        match = re.search(r"^WEAR cycles=(\d+)", log_path.read_text(), re.M)
        if not match:
            raise ValueError(f"missing measured wear duration for {result['run_id']}")
        total_cycles = int(match.group(1))
        sources[result["run_id"]] = {"wear_windows_sha256": sha(path),
                                      "simulation_sha256": sha(log_path)}
        for row in csv.DictReader(path.open()):
            duration = min(100000, total_cycles - int(row["window"]) * 100000)
            if duration <= 0:
                raise ValueError(f"invalid zero-duration window for {result['run_id']}")
            rows.append({"run_id": result["run_id"], "window": row["window"],
                         "line": row["line"], "count": row["count"],
                         "window_duration_cycles": duration})
    out = ROOT / "analysis/eval_wear_windows.csv"
    with out.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=("run_id", "window", "line", "count", "window_duration_cycles"),
                                lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    sidecar = {"script": "analysis/eval_wear_export.py",
               "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                                     cwd=ROOT, text=True).strip(),
               "results_sha256": sha(result_path), "source_sha256": sources,
               "output_sha256": sha(out)}
    Path(str(out) + ".json").write_text(json.dumps(sidecar, indent=2) + "\n")
    if len(results) == 9723 and len(sources) != 109:
        raise ValueError(f"expected 13 benign NONE + 24 attack NONE + 72 attack detector heatmaps, got {len(sources)}")
    print(f"wear CSV: {len(rows)} measured line/window rows from {len(sources)} selected cached runs")


if __name__ == "__main__":
    main()
