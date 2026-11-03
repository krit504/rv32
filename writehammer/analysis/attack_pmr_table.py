"""Generate one PMR table for every benign and attack workload.

Usage: python3 analysis/attack_pmr_table.py BENIGN.csv ATTACK_VALIDATION.csv
The attack taxonomy is the author's group's prior work (TENDRA and the Write
Hammer draft). This script does not change the T4.7 strict comparison.
"""
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    benign_path, attack_path = (Path(arg).resolve() for arg in sys.argv[1:])
    benign = list(csv.DictReader(benign_path.open()))
    attacks = list(csv.DictReader(attack_path.open()))
    if not benign or not attacks:
        raise ValueError("both sources must have rows")
    max_benign = max(float(r["pmr_all"]) for r in benign)
    rows = []
    for row in benign:
        rows.append({"class": "benign", "workload": row.get("workload", row.get("name", "")),
                     "pmr_all": row["pmr_all"], "max_benign_pmr_all": max_benign,
                     "above_all_benign": "n/a"})
    for row in attacks:
        rows.append({"class": "attack", "workload": row["case_id"],
                     "pmr_all": row["pmr_all"], "max_benign_pmr_all": max_benign,
                     "above_all_benign": row["above_every_benign"]})
    table = HERE / "attack_pmr_all_workloads.csv"
    with table.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    sidecar = {"script": "analysis/attack_pmr_table.py",
               "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                                     cwd=ROOT, text=True).strip(),
               "source_sha256": {str(p.relative_to(ROOT)): digest(p)
                                 for p in (benign_path, attack_path)},
               "table_sha256": digest(table),
               "taxonomy_credit": "Author's group: TENDRA and the Write Hammer draft"}
    Path(str(table) + ".json").write_text(json.dumps(sidecar, indent=2) + "\n")
    print(f"PMR table: {len(benign)} benign + {len(attacks)} attack rows; {table}")
    print(f"strict comparison: {sum(r['above_all_benign']=='True' for r in rows)}/{len(attacks)} attack rows pass")


if __name__ == "__main__":
    main()
