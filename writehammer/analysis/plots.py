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
        if row["detector"] == "NONE" and row["icache_bytes"] not in ("", "0") and row["d_miss_rate"]:
            by_workload[row["workload"]].append((int(row["dcache_bytes"]), float(row["d_miss_rate"])))
    if not by_workload:
        return
    fig, ax = plt.subplots(figsize=(8, 4))
    for name, vals in sorted(by_workload.items()):
        vals.sort()
        ax.plot([x / 1024 for x, _ in vals], [y for _, y in vals], marker="o", label=name)
    ax.set(xlabel="D$ size (KiB)", ylabel="D$ miss rate", title="Measured NONE runs")
    ax.legend(fontsize=7); fig.tight_layout()
    path = HERE / "eval_fig_miss_vs_size.png"
    fig.savefig(path, dpi=150); plt.close(fig)
    provenance(path, [RESULT], sum(len(v) for v in by_workload.values()))


def cpi_plot(rows):
    good = [r for r in rows if r["correct"] == "1" and r["cycles"] and r["instret"]]
    if not good:
        return
    labels = [f"{r['workload']}\n{r['detector']} {'off' if r['icache_bytes']=='0' else 'on'}" for r in good]
    fig, ax = plt.subplots(figsize=(max(8, len(good)*1.2), 4))
    x = np.arange(len(good))
    for field, name, color in (("stall_loaduse", "load-use", "#4477aa"),
                               ("stall_flush", "flush", "#cc6677"),
                               ("stall_imiss", "I$ miss", "#228833"),
                               ("stall_dmiss", "D$ miss", "#aa3377")):
        y = [float(r[field]) / float(r["instret"]) if r[field] else 0.0 for r in good]
        ax.plot(x, y, marker="o", label=name, color=color)
    ax.plot(x, [float(r["cpi"]) for r in good], marker="s", label="total CPI", color="black")
    ax.set_xticks(x, labels, rotation=45, ha="right", fontsize=7)
    ax.set(ylabel="Cycles per instruction", title="CPI and measured stall components")
    ax.legend(fontsize=7); fig.tight_layout()
    path = HERE / "eval_fig_cpi_stalls.png"
    fig.savefig(path, dpi=150); plt.close(fig)
    provenance(path, [RESULT], len(good))


def heatmaps(results, window_rows):
    meta = {r["run_id"]: r for r in results}
    by_run = defaultdict(list)
    for row in window_rows:
        if row["run_id"] not in meta:
            raise ValueError(f"wear CSV has unknown run {row['run_id']}")
        by_run[row["run_id"]].append(row)
    for run_id, entries in by_run.items():
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
    return len(by_run)


def main():
    if not RESULT.is_file() or not WINDOWS.is_file():
        raise FileNotFoundError("results.csv and eval_wear_windows.csv are required")
    rows = list(csv.DictReader(RESULT.open()))
    if not rows or any(r["correct"] != "1" for r in rows):
        raise ValueError("results.csv has no complete correct rows")
    miss_plot(rows)
    cpi_plot(rows)
    nheat = heatmaps(rows, list(csv.DictReader(WINDOWS.open())))
    fields = ["run_id", "workload", "workload_class", "detector", "mode", "M", "seed",
              "pmr_all", "t_fail_50mhz", "t_fail_100mhz", "t_fail_500mhz"]
    write_table("eval_table_pmr_tfail.csv", [{k: r[k] for k in fields} for r in rows], fields, [RESULT])
    fields = ["run_id", "workload", "detector", "seed", "fp_cycle_frac",
              "fp_store_frac", "detect_latency_cycles"]
    write_table("eval_table_fp_latency.csv", [{k: r[k] for k in fields} for r in rows], fields, [RESULT])
    print(f"[plots] regenerated miss-rate, CPI/stall plots, {nheat} measured heatmaps and two tables from CSVs")
    print("[plots] sensitivity, area/Fmax and hypotheses await T5 and author physical-flow results")


if __name__ == "__main__":
    main()
