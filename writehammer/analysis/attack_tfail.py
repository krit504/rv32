"""Generate baseline T_fail table for all benign and attack workloads.

Usage: python3 analysis/attack_tfail.py BENIGN_BASELINE.csv
Reads the independently generated attack wear summaries. Taxonomy credit:
author's group, TENDRA and the Write Hammer draft.
"""
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tests"))
from attacks import load_cases  # noqa: E402


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    benign_path = Path(sys.argv[1]).resolve()
    benign = list(csv.DictReader(benign_path.open()))
    if len(benign) != 13:
        raise AssertionError(f"expected 13 benign rows, got {len(benign)}")
    fields = ["class", "workload", "cycles", "w_max", "pmr_all",
              "t_fail_50mhz_s", "t_fail_100mhz_s", "t_fail_500mhz_s"]
    rows = [{key: value for key, value in (
        ("class", "benign"), ("workload", row["workload"]),
        ("cycles", row["cycles"]), ("w_max", row["w_max"]),
        ("pmr_all", row["pmr_all"]),
        ("t_fail_50mhz_s", row["t_fail_50mhz_s"]),
        ("t_fail_100mhz_s", row["t_fail_100mhz_s"]),
        ("t_fail_500mhz_s", row["t_fail_500mhz_s"]))}
        for row in benign]
    sources = {str(benign_path.relative_to(ROOT)): digest(benign_path)}
    for case in load_cases():
        path = ROOT / "work" / "attack_run" / case.id / "wear" / "wear_summary.json"
        summary = json.loads(path.read_text())
        assert summary["w_max"] > 0 and summary["cycles"] > 0
        vals = summary["t_fail_extrapolated_seconds"]
        rows.append({"class": "attack", "workload": case.id,
                     "cycles": summary["cycles"], "w_max": summary["w_max"],
                     "pmr_all": summary["pmr_all"],
                     "t_fail_50mhz_s": vals["50"],
                     "t_fail_100mhz_s": vals["100"],
                     "t_fail_500mhz_s": vals["500"]})
        sources[str(path.relative_to(ROOT))] = digest(path)
    table = HERE / "attack_tfail_baseline.csv"
    with table.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    sidecar = {"script": "analysis/attack_tfail.py",
               "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                                     cwd=ROOT, text=True).strip(),
               "source_sha256": sources, "table_sha256": digest(table),
               "endurance_assumed_writes": 10**15,
               "taxonomy_credit": "Author's group: TENDRA and the Write Hammer draft"}
    Path(str(table) + ".json").write_text(json.dumps(sidecar, indent=2) + "\n")
    print(f"T_fail table: {len(benign)} benign + {len(rows)-len(benign)} attack rows; {table}")


if __name__ == "__main__":
    main()
