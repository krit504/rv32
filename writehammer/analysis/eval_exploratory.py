"""POST-HOC EXPLORATORY window metrics promised by DEC-010.

These metrics do not change or satisfy T4.7. They describe selected measured
wear windows using only results.csv and eval_wear_windows.csv.
"""
import csv
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "analysis"
RESULTS = HERE / "results.csv"
WINDOWS = HERE / "eval_wear_windows.csv"
OUT = HERE / "eval_exploratory_windows.csv"
FIG = HERE / "exploratory_windowed.png"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    meta = {r["run_id"]: r for r in csv.DictReader(RESULTS.open())}
    groups = defaultdict(list)
    duration = {}
    for row in csv.DictReader(WINDOWS.open()):
        key = (row["run_id"], int(row["window"]))
        groups[key].append((int(row["line"]), int(row["count"])))
        d = int(row["window_duration_cycles"])
        if key in duration and duration[key] != d:
            raise ValueError(f"inconsistent measured duration: {key}")
        duration[key] = d
    fields = ["run_id", "workload", "detector", "mode", "M", "detector_window_cycles", "threshold_k", "window",
              "window_duration_cycles", "writes_total", "w_max", "pmr_all",
              "top1_share", "top4_share", "top8_share", "w_max_per_cycle",
              "analysis_type"]
    output = []
    for (run_id, window), entries in sorted(groups.items()):
        if run_id not in meta:
            raise ValueError(f"wear window has no results row: {run_id}")
        r = meta[run_id]
        nlines = int(r["dcache_bytes"]) // int(r["line_bytes"])
        indices = sorted(line for line, _ in entries)
        if indices != list(range(nlines)):
            raise ValueError(f"incomplete line set: {run_id} window {window}")
        counts = sorted((count for _, count in entries), reverse=True)
        total, wmax = sum(counts), counts[0]
        output.append(dict(run_id=run_id, workload=r["workload"], detector=r["detector"],
                           mode=r["mode"], M=r["M"], detector_window_cycles=r["window_cycles"],
                           threshold_k=r["threshold_k"], window=window,
                           window_duration_cycles=duration[(run_id, window)],
                           writes_total=total, w_max=wmax,
                           pmr_all=wmax * nlines / total if total else "",
                           top1_share=sum(counts[:1]) / total if total else "",
                           top4_share=sum(counts[:4]) / total if total else "",
                           top8_share=sum(counts[:8]) / total if total else "",
                           w_max_per_cycle=wmax / duration[(run_id, window)],
                           analysis_type="POST-HOC EXPLORATORY"))
    with OUT.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, lineterminator="\n")
        writer.writeheader(); writer.writerows(output)
    chosen = []
    for name, detector in (("crc32", "NONE"), ("rnla_direct_s1", "NONE"),
                           ("rnla_direct_s1", "D1")):
        subset = [r for r in output if r["workload"] == name and r["detector"] == detector
                  and (detector == "NONE" or (r["mode"] == "STATIC" and r["M"] == ""
                      and r["detector_window_cycles"] == "10000" and r["threshold_k"] == "2"))]
        if not subset:
            raise ValueError(f"missing exploratory measured series: {name}/{detector}")
        chosen.append((name, detector, sorted(subset, key=lambda r: r["window"])))
    fig, axes = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    for name, detector, subset in chosen:
        label = f"{name} / {detector}"
        axes[0].plot([r["window"] for r in subset],
                     [float(r["pmr_all"]) if r["pmr_all"] != "" else float("nan") for r in subset],
                     marker=".", label=label)
        axes[1].plot([r["window"] for r in subset], [r["w_max_per_cycle"] for r in subset],
                     marker=".", label=label)
    axes[0].set_ylabel("Per-window PMR (all lines)")
    axes[1].set_ylabel("Max line writes / cycle")
    axes[1].set_xlabel("Measured 100,000-cycle window index")
    axes[0].legend(fontsize=8)
    for ax in axes:
        ax.grid(alpha=0.2)
    fig.suptitle("POST-HOC EXPLORATORY — T4.7 unchanged; partial final windows included")
    fig.tight_layout(); fig.savefig(FIG, dpi=150); plt.close(fig)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    sidecar = {"script": "analysis/eval_exploratory.py", "git_commit": commit,
               "results_sha256": sha(RESULTS), "windows_sha256": sha(WINDOWS),
               "csv_sha256": sha(OUT), "figure_sha256": sha(FIG),
               "label": "POST-HOC EXPLORATORY; not T4.7 validation"}
    Path(str(OUT) + ".json").write_text(json.dumps(sidecar, indent=2) + "\n")
    Path(str(FIG) + ".json").write_text(json.dumps(sidecar, indent=2) + "\n")
    print(f"exploratory windows: {len(output)} measured rows; T4.7 unchanged")


if __name__ == "__main__":
    main()
