"""Prepare the T4.7 attack PMR table and heatmaps from completed runs.

Usage: .venv/bin/python analysis/attack_validate.py --benign BASELINE.csv
Requires the author-defined attack manifest and every work/attack_run/CASE_ID/wear
result. Fails if any attack PMR is not strictly above every benign workload.
Copies each generated heatmap to analysis/ with a source-hash sidecar. Reports
dominant-line movement for randomized cases as evidence for a later visual
inspection; the required "visibly wandering" decision remains a visual check.
The taxonomy is prior work of the author's group (TENDRA and Write Hammer).
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tests"))
from attacks import DEFAULT_MANIFEST, load_cases  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dominant_lines(path):
    windows = {}
    for row in csv.DictReader(Path(path).open()):
        windows.setdefault(int(row["window"]), []).append((int(row["line"]), int(row["count"])))
    hot = []
    for entries in windows.values():
        line, count = max(entries, key=lambda item: item[1])
        if count:
            hot.append(line)
    return len(set(hot)), sum(a != b for a, b in zip(hot, hot[1:]))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--benign", required=True, type=Path)
    args = ap.parse_args()
    benign_rows = list(csv.DictReader(args.benign.open()))
    if not benign_rows:
        raise ValueError("benign baseline CSV has no rows")
    max_benign = max(float(row["pmr_all"]) for row in benign_rows)
    cases = load_cases()
    runset = hashlib.sha256((DEFAULT_MANIFEST.read_bytes() + args.benign.read_bytes())).hexdigest()[:12]
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    rows = []
    source_hashes = {}
    for case in cases:
        d = ROOT / "work" / "attack_run" / case.id / "wear"
        summary_path = d / "wear_summary.json"
        if not summary_path.is_file():
            raise FileNotFoundError(f"missing attack result: {summary_path}")
        summary = json.loads(summary_path.read_text())
        distinct, changes = dominant_lines(d / "wear_windows.csv")
        plot = HERE / f"attack_{runset}_{case.id}_heatmap.png"
        shutil.copyfile(d / "wear_heatmap.png", plot)
        source_hashes[case.id] = {"wear_lines.csv": sha(d / "wear_lines.csv"),
                                  "wear_windows.csv": sha(d / "wear_windows.csv")}
        sidecar = {"script": "analysis/attack_validate.py; analysis/wear_stats.py",
                   "git_commit": commit, "run_set_id": runset, "case_id": case.id,
                   "source_csv_sha256": source_hashes[case.id],
                   "figure_sha256": sha(plot)}
        Path(str(plot) + ".json").write_text(json.dumps(sidecar, indent=2) + "\n")
        rows.append({"case_id": case.id, "kind": case.kind, "form": case.form,
                     "seed": case.seed, "pmr_all": summary["pmr_all"],
                     "max_benign_pmr_all": max_benign,
                     "above_every_benign": summary["pmr_all"] > max_benign,
                     "dominant_lines": distinct, "dominant_line_changes": changes,
                     "visual_review": "REQUIRED" if case.kind.startswith("Rn") else "n/a",
                     "heatmap": plot.name})
    table = HERE / f"attack_{runset}_validation.csv"
    with table.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    sidecar = {"script": "analysis/attack_validate.py", "git_commit": commit,
               "run_set_id": runset, "table_sha256": sha(table),
               "benign_csv_sha256": sha(args.benign),
               "attack_source_csv_sha256": source_hashes,
               "visual_review_required": [c.id for c in cases if c.kind.startswith("Rn")],
               "taxonomy_credit": "Author's group: TENDRA and the Write Hammer draft"}
    Path(str(table) + ".json").write_text(json.dumps(sidecar, indent=2) + "\n")
    failed = [r["case_id"] for r in rows if not r["above_every_benign"]]
    print(f"attack validation: {len(rows) - len(failed)}/{len(rows)} above all benign; {table}")
    if failed:
        raise AssertionError(f"PMR validation failed for: {failed}")
    print("Randomized heatmaps still require visual inspection")


if __name__ == "__main__":
    main()
