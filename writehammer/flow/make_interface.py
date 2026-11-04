"""Resolve the T6.5 interface from T5 calibration; no EDA or container run.

--check validates mappings without writing and may run before core_only.sv.
--write requires the final core-only top and writes flow/interface.json.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FLOW = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolved():
    cfg = json.loads((FLOW / "interface.template.json").read_text())
    rows = list(csv.DictReader((FLOW / "variants.csv").open()))
    calibration = {(r["detector"], int(r["M"]), int(r["window_cycles"]), float(r["k"])): int(r["threshold"])
                   for r in csv.DictReader((ROOT / "analysis/calibration.csv").open())}
    for row in rows:
        if row["detector"] in ("CORE", "NONE"):
            continue
        key = (row["detector"], int(row["M"] or 0), 10000, 2.0)
        if key not in calibration:
            raise ValueError(f"no calibrated primary threshold for {key}")
        cfg["variant_parameters"][row["variant"]] = {"WG_THRESHOLD": calibration[key]}
    if len(cfg["variant_parameters"]) != 13 or "TODO" in json.dumps(cfg["variant_parameters"]):
        raise ValueError("physical variant thresholds incomplete")
    return cfg, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    choice = ap.add_mutually_exclusive_group(required=True)
    choice.add_argument("--check", action="store_true")
    choice.add_argument("--write", action="store_true")
    args = ap.parse_args()
    cfg, rows = resolved()
    missing = [p for p in cfg["cache_sources"] + cfg["core_sources"] if not (ROOT / p).is_file()]
    print(f"physical interface: {len(rows)} planned variants, 13 calibrated detector thresholds; missing sources: {missing}")
    if args.check:
        return
    if missing:
        raise SystemExit("cannot write final physical interface until core-only RTL sources exist")
    if not (ROOT / "docs/T5_INTERFACE.md").is_file():
        raise SystemExit("final T5 interface missing")
    cfg["status"] = "final T5 parameter names; calibrated k=2/window=10000; core top source present"
    out = FLOW / "interface.json"
    out.write_text(json.dumps(cfg, indent=2) + "\n")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    sidecar = {"script": "flow/make_interface.py", "git_commit": commit,
               "template_sha256": sha(FLOW / "interface.template.json"),
               "variants_sha256": sha(FLOW / "variants.csv"),
               "calibration_sha256": sha(ROOT / "analysis/calibration.csv"),
               "interface_sha256": sha(out)}
    Path(str(out) + ".json").write_text(json.dumps(sidecar, indent=2) + "\n")
    print(f"wrote calibrated physical interface: {out}")


if __name__ == "__main__":
    main()
