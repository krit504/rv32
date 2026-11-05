"""Parse real author-run T6.5 raw outputs into the physical-cost table.

Usage: python3 flow/parse_results.py --repeats 3
Refuses missing, inconsistent or unpinned raw outputs. No synthetic result or
placeholder row is accepted.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FLOW = Path(__file__).resolve().parent
IMAGE_ID = "sha256:369c964be30bcec52d98bf18b2f8c7d80f133c5c9cf34cc1f7d5a0d2890a3103"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repeats", type=int, default=3)
    args = ap.parse_args()
    if args.repeats < 1:
        ap.error("repeats must be positive")
    variants = list(csv.DictReader((FLOW / "variants.csv").open()))
    groups = {}
    hashes = {}
    common = None
    for variant in variants:
        group = []
        for rep in range(1, args.repeats + 1):
            path = FLOW / "raw" / variant["variant"] / f"repeat_{rep}" / "result.json"
            if not path.is_file():
                raise FileNotFoundError(f"author output missing: {path}")
            raw = json.loads(path.read_text())
            if raw["variant"] != variant["variant"] or raw["repeat"] != rep:
                raise ValueError(f"raw variant/repeat mismatch: {path}")
            if raw["pinned_image_id"] != IMAGE_ID:
                raise ValueError(f"unexpected EDA image: {path}")
            if raw["area_um2"] <= 0 or raw["min_passing_period_ns"] <= 0 or raw["fmax_mhz"] <= 0:
                raise ValueError(f"invalid physical result: {path}")
            measured = (raw["tool_versions"], raw["pdk_lib_sha256"],
                        raw["constraints_sha256"], raw["pinned_image_id"],
                        raw["interface_sha256"])
            if common is None:
                common = measured
            elif common != measured:
                raise ValueError(f"tool/PDK/constraint mismatch: {path}")
            hashes[str(path.relative_to(ROOT))] = sha(path)
            group.append(raw)
        groups[variant["variant"]] = group
    if common is None:
        raise ValueError("no raw outputs")
    interface = FLOW / "interface.json"
    if not interface.is_file() or sha(interface) != common[4]:
        raise ValueError("physical interface absent or differs from author outputs")
    core = statistics.mean(r["area_um2"] for r in groups["CORE_ONLY"])
    baseline = {}
    for dbytes in (1024, 2048):
        name = f"D{dbytes}_NONE"
        baseline[dbytes] = groups[name]
    fields = ["variant", "dcache_bytes", "detector", "M", "repeats",
              "area_um2_mean", "area_um2_min", "area_um2_max", "area_delta_um2",
              "area_delta_pct_cache", "area_delta_pct_core", "fmax_mhz_mean",
              "fmax_mhz_min", "fmax_mhz_max", "fmax_delta_mhz", "fmax_delta_pct",
              "critical_path", "critical_path_changed", "yosys_version", "sta_version",
              "pdk_lib_sha256", "constraints_sha256", "pinned_image_id"]
    rows = []
    for variant in variants:
        name, dbytes = variant["variant"], int(variant["dcache_bytes"])
        group = groups[name]
        areas = [r["area_um2"] for r in group]
        fmaxes = [r["fmax_mhz"] for r in group]
        area = statistics.mean(areas)
        fmax = statistics.mean(fmaxes)
        if name == "CORE_ONLY":
            base_area, base_fmax, base_path = area, fmax, ""
        else:
            base = baseline[dbytes]
            base_area = statistics.mean(r["area_um2"] for r in base)
            base_fmax = statistics.mean(r["fmax_mhz"] for r in base)
            base_path = f"{base[0]['critical_startpoint']} -> {base[0]['critical_endpoint']}"
        path = f"{group[0]['critical_startpoint']} -> {group[0]['critical_endpoint']}"
        delta = area - base_area
        rows.append(dict(variant=name, dcache_bytes=dbytes, detector=variant["detector"],
                         M=variant["M"], repeats=len(group),
                         area_um2_mean=area, area_um2_min=min(areas), area_um2_max=max(areas),
                         area_delta_um2=delta,
                         area_delta_pct_cache=100 * delta / base_area,
                         area_delta_pct_core=100 * delta / core,
                         fmax_mhz_mean=fmax, fmax_mhz_min=min(fmaxes), fmax_mhz_max=max(fmaxes),
                         fmax_delta_mhz=fmax - base_fmax,
                         fmax_delta_pct=100 * (fmax - base_fmax) / base_fmax,
                         critical_path=path, critical_path_changed=int(path != base_path) if base_path else 0,
                         yosys_version=common[0]["yosys"], sta_version=common[0]["sta"],
                         pdk_lib_sha256=common[1], constraints_sha256=common[2],
                         pinned_image_id=common[3]))
    table = FLOW / "cost_table.csv"
    with table.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    lines = ["# T6.5 physical cost (author-run pinned flow)", "",
             f"Yosys: `{common[0]['yosys']}`. OpenSTA: `{common[0]['sta']}`.",
             f"Pinned image: `{common[3]}`. sky130_fd_sc_hd liberty SHA-256: `{common[1]}`.",
             f"Constraint SHA-256: `{common[2]}`. Each variant: {args.repeats} repeats.", "",
             "| Variant | D$ bytes | Area µm² | Δ area µm² | Δ cache % | Δ core % | Fmax MHz | Δ Fmax % | Path changed |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in rows:
        lines.append(f"| {r['variant']} | {r['dcache_bytes']} | {r['area_um2_mean']:.2f} | "
                     f"{r['area_delta_um2']:+.2f} | {r['area_delta_pct_cache']:+.2f} | "
                     f"{r['area_delta_pct_core']:+.2f} | {r['fmax_mhz_mean']:.2f} | "
                     f"{r['fmax_delta_pct']:+.2f} | {bool(r['critical_path_changed'])} |")
    (FLOW / "cost_table.md").write_text("\n".join(lines) + "\n")
    sidecar = {"script": "flow/parse_results.py", "git_commit": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "raw_source_sha256": hashes, "interface_sha256": common[4], "table_sha256": sha(table),
        "markdown_sha256": sha(FLOW / "cost_table.md"), "variants_sha256": sha(FLOW / "variants.csv")}
    (FLOW / "cost_table.csv.json").write_text(json.dumps(sidecar, indent=2) + "\n")
    print(f"physical cost: {len(rows)} real variants parsed from {len(hashes)} author runs")


if __name__ == "__main__":
    main()
