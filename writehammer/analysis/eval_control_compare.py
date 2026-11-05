"""Join each real detector with NONE, ALWAYS and its rate-matched PLACEBO.

Reads only the two evaluation CSVs. Attack mean/range summaries expose seed
spread and never turn a smaller difference into a claim.
"""
import csv
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import statistics
import subprocess

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "analysis"
RESULTS = HERE / "results.csv"
MANIFEST = HERE / "matrix_manifest.csv"
DETAIL = HERE / "eval_table_control_compare.csv"
SUMMARY = HERE / "eval_table_attack_seed_summary.csv"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, rows, fields, commit):
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    sidecar = {"script": "analysis/eval_control_compare.py", "git_commit": commit,
               "results_sha256": sha(RESULTS), "manifest_sha256": sha(MANIFEST),
               "artifact_sha256": sha(path), "rows": len(rows)}
    Path(str(path) + ".json").write_text(json.dumps(sidecar, indent=2) + "\n")


def main():
    results = list(csv.DictReader(RESULTS.open()))
    manifest = list(csv.DictReader(MANIFEST.open()))
    by_id = {r["run_id"]: r for r in results}
    if len(by_id) != len(results) or {r["run_id"] for r in manifest} != set(by_id):
        raise ValueError("control comparison requires the complete unique matrix")
    if any(r["correct"] != "1" for r in results):
        raise ValueError("incorrect row blocks control comparison")
    baseline = {}
    always = {}
    placebo = {}
    for plan in manifest:
        r = by_id[plan["run_id"]]
        if plan["detector"] == "NONE" and plan["dcache_bytes"] == "2048":
            baseline[plan["workload"]] = r
        elif plan["detector"] == "ALWAYS":
            always[plan["workload"]] = r
        elif plan["detector"] == "PLACEBO":
            key = (plan["workload"], plan["control_for"], plan["mode"],
                   plan["window_cycles"], plan["threshold_k"], plan["M"])
            if key in placebo:
                raise ValueError(f"duplicate rate-matched PLACEBO: {key}")
            placebo[key] = r
    fields = ["run_id", "workload", "workload_class", "detector", "mode", "window_cycles",
              "threshold_k", "M", "seed", "none_pmr_all", "always_pmr_all",
              "placebo_pmr_all", "detector_pmr_all", "detector_reduction_vs_none",
              "placebo_reduction_vs_none", "delta_pmr_vs_placebo",
              "detector_beats_placebo"]
    detail = []
    for plan in manifest:
        if plan["detector"] not in ("D1", "D2", "D3"):
            continue
        name = plan["workload"]
        key = (name, plan["detector"], plan["mode"], plan["window_cycles"],
               plan["threshold_k"], plan["M"])
        if name not in baseline or name not in always or key not in placebo:
            raise ValueError(f"missing matched control for {key}")
        r = by_id[plan["run_id"]]
        n, a, p, d = (float(x["pmr_all"]) for x in (baseline[name], always[name], placebo[key], r))
        if n <= 0:
            raise ValueError(f"invalid NONE PMR for {name}")
        detail.append(dict(run_id=r["run_id"], workload=name,
                           workload_class=r["workload_class"], detector=r["detector"],
                           mode=r["mode"], window_cycles=r["window_cycles"],
                           threshold_k=r["threshold_k"], M=r["M"], seed=r["seed"],
                           none_pmr_all=n, always_pmr_all=a, placebo_pmr_all=p,
                           detector_pmr_all=d, detector_reduction_vs_none=1-d/n,
                           placebo_reduction_vs_none=1-p/n,
                           delta_pmr_vs_placebo=p-d,
                           detector_beats_placebo=int(d < p)))
    if len(detail) != 4718:
        raise ValueError(f"expected 4718 real detector/control pairs, got {len(detail)}")
    attack_groups = defaultdict(list)
    for row in detail:
        if (row["workload_class"] == "attack" and row["window_cycles"] == "10000"
                and row["threshold_k"] == "2"):
            kind_form = "_".join(row["workload"].split("_")[:2])
            key = (kind_form, row["detector"], row["mode"], row["M"])
            attack_groups[key].append(row)
    summary_fields = ["attack_kind_form", "detector", "mode", "M", "seeds",
                      "mean_detector_reduction", "range_detector_reduction",
                      "mean_placebo_reduction", "range_placebo_reduction",
                      "mean_delta_pmr_vs_placebo", "range_delta_pmr_vs_placebo",
                      "difference_exceeds_seed_range"]
    summary = []
    for (kind_form, detector, mode, m), group in sorted(attack_groups.items()):
        def values(field):
            return [float(r[field]) for r in group]
        real = values("detector_reduction_vs_none")
        control = values("placebo_reduction_vs_none")
        delta = values("delta_pmr_vs_placebo")
        spread = max(max(real)-min(real), max(control)-min(control))
        summary.append(dict(attack_kind_form=kind_form, detector=detector, mode=mode,
                            M=m, seeds=len(group),
                            mean_detector_reduction=statistics.mean(real),
                            range_detector_reduction=max(real)-min(real),
                            mean_placebo_reduction=statistics.mean(control),
                            range_placebo_reduction=max(control)-min(control),
                            mean_delta_pmr_vs_placebo=statistics.mean(delta),
                            range_delta_pmr_vs_placebo=max(delta)-min(delta),
                            difference_exceeds_seed_range=(int(abs(statistics.mean(real)-statistics.mean(control)) > spread)
                                                           if len(group) > 1 else "")))
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    write(DETAIL, detail, fields, commit)
    write(SUMMARY, summary, summary_fields, commit)
    print(f"controls: {len(detail)} real/PLACEBO/NONE/ALWAYS comparisons; {len(summary)} attack seed summaries")


if __name__ == "__main__":
    main()
