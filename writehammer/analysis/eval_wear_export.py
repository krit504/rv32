"""Normalize measured per-line windows into a CSV for T6 plots.

Usage: python3 analysis/eval_wear_export.py
Reads only completed run artifacts named in analysis/results.csv. The output is
an input CSV to plots.py; it never invents missing line/window counts.
"""
import csv
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    result_path = ROOT / "analysis/results.csv"
    results = list(csv.DictReader(result_path.open()))
    rows = []
    sources = {}
    for result in results:
        if result["icache_bytes"] in ("", "0") or result["correct"] != "1":
            continue
        path = ROOT / "work/eval/runs" / result["run_id"] / "wear_windows.csv"
        if not path.is_file():
            raise FileNotFoundError(f"missing measured wear windows for {result['run_id']}: {path}")
        sources[result["run_id"]] = sha(path)
        for row in csv.DictReader(path.open()):
            rows.append({"run_id": result["run_id"], "window": row["window"],
                         "line": row["line"], "count": row["count"]})
    out = ROOT / "analysis/eval_wear_windows.csv"
    with out.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=("run_id", "window", "line", "count"),
                                lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    sidecar = {"script": "analysis/eval_wear_export.py",
               "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                                     cwd=ROOT, text=True).strip(),
               "results_sha256": sha(result_path), "source_sha256": sources,
               "output_sha256": sha(out)}
    Path(str(out) + ".json").write_text(json.dumps(sidecar, indent=2) + "\n")
    print(f"wear CSV: {len(rows)} measured line/window rows from {len(sources)} cached runs")


if __name__ == "__main__":
    main()
