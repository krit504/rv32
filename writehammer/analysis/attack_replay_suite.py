"""Recheck exact golden cache replay for all attack workload images.

Usage: python3 analysis/attack_replay_suite.py
Taxonomy credit: author's group, TENDRA and the Write Hammer draft.
"""
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from attacks import load_cases  # noqa: E402
from prog_runner import parse_output  # noqa: E402
from wear_replay import replay  # noqa: E402


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    rows = []
    source_hashes = {}
    for case in load_cases():
        wear = ROOT / "work" / "attack_run" / case.id / "wear"
        image = wear / "program.hex"
        log = wear / "simulation.log"
        parsed = parse_output(log.read_text())
        if parsed["halt"] != 0 or parsed["timeout"]:
            raise AssertionError(f"bad attack exit: {case.id}")
        result = replay(wear, 2048, 16)
        rows.append({"case_id": case.id, "halt": 0,
                     "image_sha256": digest(image),
                     "trace_sha256": digest(wear / "dc_trace.csv"),
                     "wear_lines_sha256": digest(wear / "wear_lines.csv"),
                     "replay": "PASS"})
        source_hashes[case.id] = {"image": digest(image),
                                  "trace": digest(wear / "dc_trace.csv"),
                                  "wear_lines": digest(wear / "wear_lines.csv")}
    table = ROOT / "analysis" / "attack_replay_results.csv"
    with table.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    sidecar = {"script": "analysis/attack_replay_suite.py",
               "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                                     cwd=ROOT, text=True).strip(),
               "sources_sha256": source_hashes, "table_sha256": digest(table),
               "taxonomy_credit": "Author's group: TENDRA and the Write Hammer draft"}
    Path(str(table) + ".json").write_text(json.dumps(sidecar, indent=2) + "\n")
    print(f"[attack-replay-suite] {len(rows)}/{len(rows)} exact matches; {table}")


if __name__ == "__main__":
    main()
