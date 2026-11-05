"""Plot author-measured physical cost from flow/cost_table.csv only."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
FLOW = Path(__file__).resolve().parent
TABLE = FLOW / "cost_table.csv"
OUT = FLOW / "area_fmax.png"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--if-available", action="store_true")
    args = ap.parse_args()
    if not TABLE.is_file():
        if args.if_available:
            print("physical area/Fmax plot pending author EDA outputs")
            return
        raise FileNotFoundError(TABLE)
    rows = list(csv.DictReader(TABLE.open()))
    planned = list(csv.DictReader((FLOW / "variants.csv").open()))
    if len(rows) != len(planned) or {r["variant"] for r in rows} != {r["variant"] for r in planned}:
        raise ValueError("physical cost table is incomplete")
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    colors = {1024: "#4477aa", 2048: "#cc6677"}
    for dbytes in (1024, 2048):
        chosen = [r for r in rows if int(r["dcache_bytes"]) == dbytes]
        chosen.sort(key=lambda r: (r["detector"], int(r["M"] or 0)))
        labels = [r["detector"] + (f" M{r['M']}" if r["M"] else "") for r in chosen]
        x = list(range(len(chosen)))
        axes[0].plot(x, [float(r["area_um2_mean"]) for r in chosen], "o-",
                     color=colors[dbytes], label=f"{dbytes // 1024} KiB D$")
        axes[1].plot(x, [float(r["fmax_mhz_mean"]) for r in chosen], "o-",
                     color=colors[dbytes], label=f"{dbytes // 1024} KiB D$")
        for ax in axes[:2]:
            ax.set_xticks(x, labels, rotation=55, ha="right")
        hashed = sorted((r for r in chosen if r["detector"] == "D2"),
                        key=lambda r: int(r["M"]))
        axes[2].plot([int(r["M"]) for r in hashed],
                     [float(r["area_um2_mean"]) for r in hashed], "o-",
                     color=colors[dbytes], label=f"{dbytes // 1024} KiB D$")
    axes[0].set(ylabel="Cell area (µm²)", title="Area by detector")
    axes[1].set(ylabel="Post-synthesis Fmax (MHz)", title="Fmax by detector")
    axes[2].set(xlabel="D2 counter count M", ylabel="Cell area (µm²)",
                title="D2 state-size sensitivity")
    for ax in axes:
        ax.grid(alpha=0.2)
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT, dpi=160)
    plt.close(fig)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    sidecar = {"script": "flow/plot_area.py", "git_commit": commit,
               "script_sha256": sha(Path(__file__)), "cost_table_sha256": sha(TABLE),
               "variants_sha256": sha(FLOW / "variants.csv"), "figure_sha256": sha(OUT)}
    Path(str(OUT) + ".json").write_text(json.dumps(sidecar, indent=2) + "\n")
    print(f"physical area/Fmax plot: {len(rows)} measured variants")


if __name__ == "__main__":
    main()
