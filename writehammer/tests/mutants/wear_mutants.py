"""Prove the golden replay rejects a deliberately mis-counting wear monitor.

Usage: python3 tests/mutants/wear_mutants.py RUN_DIR
Copies a real completed run into work/wear_mutant, increments one monitor line
count, and requires the independent replay to fail on the changed count.
The original RTL run and its protected artifacts are never modified.
"""
import csv
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "analysis"))
from wear_replay import replay  # noqa: E402


def main(source):
    source = Path(source).resolve()
    dest = ROOT / "work" / "wear_mutant" / source.name
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("dc_trace.csv", "wear_lines.csv", "simulation.log"):
        shutil.copyfile(source / name, dest / name)
    path = dest / "wear_lines.csv"
    rows = list(csv.DictReader(path.open()))
    target = next(i for i, row in enumerate(rows) if int(row["count"]) > 0)
    rows[target]["count"] = str(int(rows[target]["count"]) + 1)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=("line", "count"))
        writer.writeheader()
        writer.writerows(rows)
    try:
        replay(dest)
    except AssertionError as exc:
        if "per-line array-write mismatch" not in str(exc):
            raise
        print(f"PASS: mis-counting monitor mutant caught: {exc}")
    else:
        raise AssertionError("mis-counting monitor mutant survived replay")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
