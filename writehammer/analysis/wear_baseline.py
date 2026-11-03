"""Generate the frozen-RTL benign wear baseline.

Usage: .venv/bin/python analysis/wear_baseline.py (or make wear)
Inputs: the complete benign registry in tests/workloads.py, built by
analysis/baseline.py. Runs cached core (2 KiB D$, 16-byte lines), no detector,
20-cycle backing memory, 10,000-cycle windows. Outputs analysis/wear_<runset>.csv,
one analysis/wear_<runset>_<workload>_heatmap.png per workload, and JSON
provenance sidecars. Raw CSVs and logs live in work/wear_baseline/<runset>/.
"""
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tests"))
from prog_runner import parse_output  # noqa: E402
from baseline import workloads  # noqa: E402
from wear_run import run  # noqa: E402
from wear_replay import replay  # noqa: E402
from wear_stats import main as stats  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def heartbeat(done, name):
    while not done.wait(30):
        print(f"wear baseline still running: {name}", flush=True)


def main():
    rtl_tree = subprocess.check_output(["git", "rev-parse", "HEAD:writehammer/rtl"],
                                       cwd=ROOT, text=True).strip()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    runset = "baseline_" + rtl_tree[:12]
    entries = workloads()
    rows = []
    source_hashes = {}
    for name, group, image, check, _rate in entries:
        slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        d = ROOT / "work" / "wear_baseline" / runset / slug
        print(f"wear baseline starting: {name}", flush=True)
        done = threading.Event()
        thread = threading.Thread(target=heartbeat, args=(done, name), daemon=True)
        thread.start()
        try:
            run(image, d, maxcyc=500_000_000, window=10_000, lat=20)
            result = parse_output((d / "simulation.log").read_text())
            error = check(result)
            if error:
                raise AssertionError(f"{name}: self-check failed: {error}")
            replay(d)
            stats(d)
        finally:
            done.set()
            thread.join()
        summary = json.loads((d / "wear_summary.json").read_text())
        row = {"run_set_id": runset, "workload": name, "class": group,
               "cycles": summary["cycles"], "array_writes": summary["array_writes"],
               "w_max": summary["w_max"], "mean_all": summary["mean_all"],
               "mean_written": summary["mean_written"], "pmr_all": summary["pmr_all"],
               "pmr_written": summary["pmr_written"],
               "t_fail_50mhz_s": summary["t_fail_extrapolated_seconds"]["50"],
               "t_fail_100mhz_s": summary["t_fail_extrapolated_seconds"]["100"],
               "t_fail_500mhz_s": summary["t_fail_extrapolated_seconds"]["500"],
               "heatmap": f"wear_{runset}_{slug}_heatmap.png"}
        rows.append(row)
        plot = HERE / row["heatmap"]
        shutil.copyfile(d / "wear_heatmap.png", plot)
        source_hashes[name] = {"wear_lines.csv": sha(d / "wear_lines.csv"),
                               "wear_windows.csv": sha(d / "wear_windows.csv"),
                               "dc_trace.csv": sha(d / "dc_trace.csv")}
        sidecar = {"script": "analysis/wear_baseline.py; analysis/wear_stats.py",
                   "git_commit": commit, "rtl_tree": rtl_tree, "run_set_id": runset,
                   "workload": name, "source_csv_sha256": source_hashes[name],
                   "figure_sha256": sha(plot), "assumed_endurance_writes": 10**15}
        (HERE / (plot.name + ".json")).write_text(json.dumps(sidecar, indent=2) + "\n")
        print(f"wear baseline PASS: {name} w_max={row['w_max']}", flush=True)
    if len(rows) != len(entries):
        raise AssertionError(f"expected all {len(entries)} benign workloads, found {len(rows)}")
    table = HERE / f"wear_{runset}.csv"
    with table.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    manifest = {"script": "analysis/wear_baseline.py", "git_commit": commit,
                "rtl_tree": rtl_tree, "run_set_id": runset, "table_sha256": sha(table),
                "source_csv_sha256": source_hashes, "workloads": len(rows),
                "configuration": {"dcache_bytes": 2048, "line_bytes": 16,
                                  "memory_latency_cycles": 20, "detector": "NONE",
                                  "window_cycles": 10000,
                                  "assumed_endurance_writes": 10**15}}
    (HERE / (table.name + ".json")).write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"[wear baseline] {len(rows)}/{len(rows)} workloads: {table}", flush=True)


if __name__ == "__main__":
    main()
