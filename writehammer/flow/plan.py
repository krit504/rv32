"""Generate the T6.5 physical-cost variant manifest; no EDA tool is run."""
import csv
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FLOW = Path(__file__).resolve().parent


def variants():
    rows = [{"variant": "CORE_ONLY", "top": "core", "dcache_bytes": 0,
             "icache_bytes": 0, "line_bytes": 16, "detector": "CORE", "M": ""}]
    for dbytes in (1024, 2048):
        nlines = dbytes // 16
        for detector in ("NONE", "D1", "D3"):
            rows.append({"variant": f"D{dbytes}_{detector}", "top": "cache",
                         "dcache_bytes": dbytes, "icache_bytes": 2048,
                         "line_bytes": 16, "detector": detector, "M": ""})
        for m in (4, 8, 16, 32, 64):
            if m <= nlines // 2:
                rows.append({"variant": f"D{dbytes}_D2_M{m}", "top": "cache",
                             "dcache_bytes": dbytes, "icache_bytes": 2048,
                             "line_bytes": 16, "detector": "D2", "M": m})
    assert len(rows) == 16
    return rows


def main():
    rows = variants()
    out = FLOW / "variants.csv"
    with out.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    sidecar = {"script": "flow/plan.py", "git_commit": commit,
               "variants_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
               "planned_variants": len(rows), "eda_runs_started": 0,
               "source": "spec Section 3 and T6.5"}
    Path(str(out) + ".json").write_text(json.dumps(sidecar, indent=2) + "\n")
    print(f"physical flow plan: {len(rows)} variants, three repeats each if required; no EDA run")


if __name__ == "__main__":
    main()
