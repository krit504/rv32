"""T6.4: measured false-positive fraction versus attack detection latency.

Reads the complete Section 7 results CSV only. Produces a derived CSV and a
figure with one panel per attack kind/form. Randomized seeds are shown as
mean and full seed range. Missing detections are reported as censored counts,
never assigned an invented latency.
"""
import csv
import hashlib
import json
from pathlib import Path
import statistics
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "analysis/results.csv"
MANIFEST = ROOT / "analysis/matrix_manifest.csv"
OUT = ROOT / "analysis/sensitivity.csv"
FIG = ROOT / "analysis/sensitivity.png"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    runs = list(csv.DictReader(RESULTS.open()))
    planned = list(csv.DictReader(MANIFEST.open()))
    if {r["run_id"] for r in runs} != {r["run_id"] for r in planned} or len(runs) != len(planned):
        raise SystemExit("complete T6.1 matrix required for sensitivity")
    if any(r["correct"] != "1" for r in runs):
        raise SystemExit("incorrect run in matrix; sensitivity is blocked")
    real = [r for r in runs if r["detector"] in ("D1", "D2", "D3")]
    if any(not r["fp_cycle_frac"] for r in real if r["workload_class"] == "held-out"):
        raise SystemExit("phase-based held-out false-positive metrics required")
    if any(not r["restricted_cycle_frac"] for r in real if r["workload_class"] in ("attack", "mixed")):
        raise SystemExit("phase-based attack snapshots required")
    groups = {}
    for row in real:
        key = (row["detector"], row["M"], row["mode"], row["window_cycles"], row["threshold_k"])
        groups.setdefault(key, []).append(row)
    fields = ["detector", "M", "mode", "window_cycles", "threshold_k", "attack_kind_form",
              "benign_fp_cycle_frac_mean", "latency_cycles_mean", "latency_cycles_min",
              "latency_cycles_max", "detected_seeds", "total_seeds", "censored_seeds"]
    output = []
    for key, group in sorted(groups.items()):
        benign = [float(r["fp_cycle_frac"]) for r in group if r["workload_class"] == "held-out"]
        if not benign:
            raise ValueError(f"no held-out benign runs for {key}")
        attack_groups = {}
        for row in group:
            if row["workload_class"] == "attack":
                name = "_".join(row["workload"].split("_")[:2])
                attack_groups.setdefault(name, []).append(row)
            elif row["workload_class"] == "mixed":
                attack_groups.setdefault(row["workload"], []).append(row)
        for attack, sample in sorted(attack_groups.items()):
            # Empty means no restriction in the measured attack interval.
            values = [int(r["detect_latency_cycles"]) if r["detect_latency_cycles"] else None for r in sample]
            detected = [v for v in values if v is not None]
            fp = (statistics.mean(float(r["fp_cycle_frac"]) for r in sample)
                  if attack.startswith("mixed_") else statistics.mean(benign))
            output.append(dict(zip(fields[:6], (*key, attack)),
                               benign_fp_cycle_frac_mean=fp,
                               latency_cycles_mean=statistics.mean(detected) if detected else "",
                               latency_cycles_min=min(detected) if detected else "",
                               latency_cycles_max=max(detected) if detected else "",
                               detected_seeds=len(detected), total_seeds=len(values),
                               censored_seeds=len(values) - len(detected)))
    with OUT.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, lineterminator="\n")
        writer.writeheader(); writer.writerows(output)
    attacks = sorted({r["attack_kind_form"] for r in output})
    fig, axes = plt.subplots(3, 4, figsize=(16, 11), sharex=True, sharey=True)
    colors = {"D1": "#1f77b4", "D2": "#ff7f0e", "D3": "#2ca02c"}
    for ax, attack in zip(axes.flat, attacks):
        for detector in colors:
            points = sorted((r for r in output if r["attack_kind_form"] == attack
                             and r["detector"] == detector and r["latency_cycles_mean"] != ""),
                            key=lambda r: float(r["benign_fp_cycle_frac_mean"]))
            if not points:
                continue
            xs = [float(r["benign_fp_cycle_frac_mean"]) for r in points]
            ys = [float(r["latency_cycles_mean"]) for r in points]
            ax.plot(xs, ys, "-o", markersize=2, linewidth=0.7, color=colors[detector], alpha=0.5)
            for x, y, row in zip(xs, ys, points):
                lo, hi = float(row["latency_cycles_min"]), float(row["latency_cycles_max"])
                ax.errorbar(x, y, yerr=[[y - lo], [hi - y]], fmt="none",
                            elinewidth=0.5, capsize=1, color=colors[detector], alpha=0.35)
        ax.set_title(attack)
        ax.grid(alpha=0.2)
    for ax in axes[-1]:
        ax.set_xlabel("Benign false-positive cycle fraction")
    for ax in axes[:, 0]:
        ax.set_ylabel("Detection latency (cycles)")
    handles = [plt.Line2D([], [], color=color, marker="o", linestyle="", label=det)
               for det, color in colors.items()]
    fig.legend(handles=handles, loc="upper center", ncol=3)
    fig.suptitle("T6.4 sensitivity: held-out benign for attacks, own benign phases for mixed; censored counts in CSV")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIG, dpi=160)
    plt.close(fig)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    sidecar = {"script": "analysis/sensitivity.py", "git_commit": commit,
               "script_sha256": sha(Path(__file__)),
               "results_sha256": sha(RESULTS), "manifest_sha256": sha(MANIFEST),
               "derived_csv_sha256": sha(OUT), "figure_sha256": sha(FIG),
               "censored_total": sum(int(r["censored_seeds"]) for r in output)}
    Path(str(OUT) + ".json").write_text(json.dumps(sidecar, indent=2) + "\n")
    Path(str(FIG) + ".json").write_text(json.dumps(sidecar, indent=2) + "\n")
    print(f"sensitivity: {len(output)} measured points; {sidecar['censored_total']} censored attack seeds")


if __name__ == "__main__":
    main()
