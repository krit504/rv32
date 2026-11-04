"""Regenerate available Section 8 figures and tables from T6 CSV data only.

Usage: .venv/bin/python analysis/plots.py
Inputs: analysis/results.csv and analysis/eval_wear_windows.csv. Missing
detector/flow data is reported and never replaced with invented values.
"""
import csv
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
RESULT = HERE / "results.csv"
WINDOWS = HERE / "eval_wear_windows.csv"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def provenance(path, sources, nrows):
    sidecar = {"script": "analysis/plots.py",
               "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                                     cwd=ROOT, text=True).strip(),
               "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in sources},
               "artifact_sha256": sha(path), "source_rows": nrows,
               "development_subset": json.loads(Path(str(RESULT) + ".json").read_text()).get("development_subset")}
    Path(str(path) + ".json").write_text(json.dumps(sidecar, indent=2) + "\n")


def write_table(name, rows, fields, sources):
    out = HERE / name
    with out.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    provenance(out, sources, len(rows))


def miss_plot(rows):
    by_workload = defaultdict(list)
    for row in rows:
        if (row["workload_class"] in ("calibration", "held-out") and row["detector"] == "NONE"
                and row["icache_bytes"] not in ("", "0") and row["d_miss_rate"]):
            by_workload[row["workload"]].append((int(row["dcache_bytes"]), float(row["d_miss_rate"])))
    if not by_workload:
        return
    for name, vals in sorted(by_workload.items()):
        vals.sort()
        if len(vals) != 4:
            raise ValueError(f"incomplete cache-size sweep for {name}")
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot([x / 1024 for x, _ in vals], [y for _, y in vals], marker="o")
        ax.set(xlabel="D$ size (KiB)", ylabel="D$ miss rate", title=f"{name}: NONE detector")
        ax.set_xticks([1, 2, 4, 8]); ax.grid(alpha=0.2); fig.tight_layout()
        slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        path = HERE / f"eval_fig_miss_{slug}.png"
        fig.savefig(path, dpi=150); plt.close(fig)
        provenance(path, [RESULT], len(vals))


def cpi_plot(rows):
    benign = sorted({r["workload"] for r in rows if r["workload_class"] in ("calibration", "held-out")})
    selected = []
    for name in benign:
        cases = [("No cache", lambda r: r["detector"] == "NONE" and r["dcache_bytes"] == "0"),
                 ("Cache", lambda r: r["detector"] == "NONE" and r["dcache_bytes"] == "2048"),
                 ("D1", lambda r: r["detector"] == "D1" and r["mode"] == "STATIC" and r["window_cycles"] == "10000" and r["threshold_k"] == "2"),
                 ("D2 M16", lambda r: r["detector"] == "D2" and r["M"] == "16" and r["mode"] == "STATIC" and r["window_cycles"] == "10000" and r["threshold_k"] == "2"),
                 ("D3", lambda r: r["detector"] == "D3" and r["mode"] == "ADAPTIVE" and r["window_cycles"] == "10000" and r["threshold_k"] == "2")]
        group = []
        for label, predicate in cases:
            matches = [r for r in rows if r["workload"] == name and predicate(r)]
            if len(matches) != 1:
                raise ValueError(f"incomplete primary CPI comparison for {name}: {label}")
            group.append((label, matches[0]))
            selected.append(matches[0])
        labels = [label for label, _ in group]
        chosen = [r for _, r in group]
        x = np.arange(len(chosen))
        fig, axes = plt.subplots(2, 1, figsize=(7, 7), sharex=True)
        axes[0].bar(x, [float(r["cpi"]) for r in chosen], color="#4477aa")
        axes[0].set(ylabel="Cycles / instruction", title=f"{name}: CPI")
        bottom = np.zeros(len(chosen))
        for field, label, color in (("stall_loaduse", "load-use", "#4477aa"),
                                    ("stall_flush", "flush", "#cc6677"),
                                    ("stall_imiss", "I$ miss", "#228833"),
                                    ("stall_dmiss", "D$ miss", "#aa3377")):
            values = np.array([float(r[field]) / float(r["instret"]) for r in chosen])
            axes[1].bar(x, values, bottom=bottom, label=label, color=color)
            bottom += values
        axes[1].set(ylabel="Stall cycles / instruction", title="Measured stall components")
        axes[1].set_xticks(x, labels, rotation=30, ha="right")
        axes[1].legend(fontsize=8); fig.tight_layout()
        slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        path = HERE / f"eval_fig_cpi_{slug}.png"
        fig.savefig(path, dpi=150); plt.close(fig)
        provenance(path, [RESULT], len(chosen))
    fields = ["run_id", "workload", "detector", "mode", "M", "cycles", "instret", "cpi",
              "stall_loaduse", "stall_flush", "stall_imiss", "stall_dmiss"]
    write_table("eval_table_perf.csv", [{k: r[k] for k in fields} for r in selected], fields, [RESULT])


def heatmaps(results, window_rows):
    meta = {r["run_id"]: r for r in results}
    by_run = defaultdict(list)
    for row in window_rows:
        if row["run_id"] not in meta:
            raise ValueError(f"wear CSV has unknown run {row['run_id']}")
        by_run[row["run_id"]].append(row)
    for index, (run_id, entries) in enumerate(by_run.items(), 1):
        result = meta[run_id]
        nlines = int(result["dcache_bytes"]) // int(result["line_bytes"])
        nwindows = max(int(e["window"]) for e in entries) + 1
        heat = np.full((nlines, nwindows), -1, dtype=np.int64)
        for entry in entries:
            line, window, count = map(int, (entry["line"], entry["window"], entry["count"]))
            if not (0 <= line < nlines) or heat[line, window] != -1:
                raise ValueError(f"duplicate/out-of-range wear entry in {run_id}")
            heat[line, window] = count
        if np.any(heat < 0):
            raise ValueError(f"missing wear entries in {run_id}")
        fig, ax = plt.subplots(figsize=(9, 4))
        image = ax.imshow(heat, aspect="auto", origin="lower", interpolation="nearest")
        ax.set(xlabel="Window", ylabel="D$ line",
               title=f"{result['workload']} / {result['detector']} ({run_id})")
        fig.colorbar(image, ax=ax, label="Array writes")
        fig.tight_layout()
        path = HERE / f"eval_fig_heatmap_{run_id}.png"
        fig.savefig(path, dpi=150); plt.close(fig)
        provenance(path, [RESULT, WINDOWS], len(entries))
        if index % 10 == 0:
            print(f"[plots] heatmap progress {index}/{len(by_run)}", flush=True)
    return len(by_run)


def main():
    if not RESULT.is_file() or not WINDOWS.is_file():
        raise FileNotFoundError("results.csv and eval_wear_windows.csv are required")
    rows = list(csv.DictReader(RESULT.open()))
    if not rows or any(r["correct"] != "1" for r in rows):
        raise ValueError("results.csv has no complete correct rows")
    for pattern in ("eval_fig_*.png", "eval_fig_*.png.json",
                    "eval_table_*.csv", "eval_table_*.csv.json"):
        for old in HERE.glob(pattern):
            old.unlink()
    miss_plot(rows)
    cpi_plot(rows)
    nheat = heatmaps(rows, list(csv.DictReader(WINDOWS.open())))
    fields = ["run_id", "workload", "workload_class", "detector", "mode", "M", "seed",
              "pmr_all", "t_fail_50mhz", "t_fail_100mhz", "t_fail_500mhz"]
    write_table("eval_table_pmr_tfail.csv", [{k: r[k] for k in fields} for r in rows], fields, [RESULT])
    fields = ["run_id", "workload", "detector", "seed", "fp_cycle_frac",
              "fp_store_frac", "detect_latency_cycles"]
    write_table("eval_table_fp_latency.csv", [{k: r[k] for k in fields} for r in rows], fields, [RESULT])
    print(f"[plots] regenerated per-benign miss-rate and CPI/stall plots, {nheat} measured heatmaps and three tables from CSVs")
    print("[plots] sensitivity and hypotheses await phase snapshots; area/Fmax awaits author physical-flow results")


if __name__ == "__main__":
    main()
