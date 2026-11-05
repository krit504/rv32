"""Author-only Yosys/OpenSTA flow in the pinned Docker image.

Usage: python3 flow/run_flow.py --check-plan      (safe: no EDA)
       WH_AUTHORIZED_FLOW=1 WH_PINNED_IMAGE_ID=sha256:... \
         python3 flow/run_flow.py --execute       (author launches inside Docker)
Never invoke --execute from an agent session. Requires flow/interface.json,
docs/T5_INTERFACE.md, observation-free RTL tops, sky130 PDK and pinned image.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import threading

ROOT = Path(__file__).resolve().parents[1]
FLOW = Path(__file__).resolve().parent
IMAGE_ID = "sha256:369c964be30bcec52d98bf18b2f8c7d80f133c5c9cf34cc1f7d5a0d2890a3103"
LIB_REL = "libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
COARSE_PERIODS = (2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 75, 100, 150, 200, 300, 500)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def command(argv, *, cwd=None, timeout=3600):
    stop = threading.Event()
    def heartbeat():
        while not stop.wait(30):
            print(f"physical-flow heartbeat: {' '.join(argv[:2])}", flush=True)
    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    try:
        proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    finally:
        stop.set()
        thread.join()
    if proc.returncode:
        raise RuntimeError(f"failed {argv}: {proc.stdout[-1000:]} {proc.stderr[-1000:]}")
    return proc.stdout + proc.stderr


def read_plan():
    return list(csv.DictReader((FLOW / "variants.csv").open()))


def load_interface():
    path = FLOW / "interface.json"
    if not path.is_file() or not (ROOT / "docs/T5_INTERFACE.md").is_file():
        raise RuntimeError("final flow/interface.json and docs/T5_INTERFACE.md are required")
    cfg = json.loads(path.read_text())
    if "TODO" in json.dumps(cfg):
        raise RuntimeError("flow/interface.json still contains TODO values")
    required = {"OBSERVE": 0, "WG_ACTION": 0, "WG_MODE": 0,
                "WG_WINDOW": 10000, "WG_W": 16, "DC_WRITE_LATENCY": 1}
    for name, value in required.items():
        if int(cfg.get("fixed_parameters", {}).get(name, -1)) != value:
            raise ValueError(f"physical interface requires {name}={value}")
    return cfg


def library():
    pdk = os.environ.get("PDK_ROOT")
    if not pdk:
        raise RuntimeError("PDK_ROOT must point to the mounted sky130A PDK")
    lib = Path(pdk) / LIB_REL
    if not lib.is_file():
        raise FileNotFoundError(lib)
    return lib


def yosys_script(row, cfg, lib, netlist):
    top = cfg["core_top"] if row["top"] == "core" else cfg["cache_top"]
    paths = cfg["core_sources"] if row["top"] == "core" else cfg["cache_sources"]
    sources = [ROOT / p for p in paths]
    if any(not p.is_file() for p in sources):
        raise FileNotFoundError("observation-free top or source is missing")
    params = {}
    if row["top"] == "cache":
        names = cfg["parameter_names"]
        params[names["icache_bytes"]] = int(row["icache_bytes"])
        params[names["dcache_bytes"]] = int(row["dcache_bytes"])
        params[names["line_bytes"]] = int(row["line_bytes"])
        params[names["detector"]] = int(cfg["detector_values"][row["detector"]])
        if row["detector"] == "D2":
            params[names["M"]] = int(row["M"])
        for name, value in cfg.get("fixed_parameters", {}).items():
            params[name] = int(value)
        if row["detector"] != "NONE":
            settings = cfg.get("variant_parameters", {}).get(row["variant"])
            if not settings:
                raise ValueError(f"calibrated physical parameters missing for {row['variant']}")
            for name, value in settings.items():
                params[name] = int(value)
    if any(not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", p) for p in params):
        raise ValueError("invalid RTL parameter name")
    lines = ["read_verilog -sv -DSYNTHESIS " + " ".join(str(p) for p in sources)]
    if params:
        lines.append("chparam " + " ".join(f"-set {k} {v}" for k, v in params.items()) + " " + top)
    lines += ["hierarchy -check -top " + top,
             "rename -top " + top,
             "synth -top " + top + " -flatten -noabc",
             "dfflibmap -liberty " + str(lib),
             "abc -liberty " + str(lib),
             "clean -purge", "write_verilog -noattr " + str(netlist),
             "stat -liberty " + str(lib)]
    return "\n".join(lines) + "\n", top, sources, params


OBSERVATION_PORTS = ("stall_req", "wg_restricted", "wg_cycles_restricted", "wg_first_restrict",
                     "wg_stores", "wg_stores_restricted", "ic_refill_cnt", "ic_cnt_lookup",
                     "ic_cnt_miss", "ic_cnt_stall", "dc_refill_cnt", "dc_write_cnt",
                     "dc_aw_valid", "dc_aw_line", "dc_aw_kind", "dc_tr_valid", "dc_tr_we",
                     "dc_tr_addr", "dc_tr_size", "dc_tr_bypass", "dc_cnt_access", "dc_cnt_hit",
                     "dc_cnt_miss", "dc_cnt_wb", "dc_cnt_bypass", "dc_cnt_rab", "dc_cnt_stall",
                     "peek_hit", "peek_data")


def check_observation_outputs(netlist_text):
    """The retained observation output ports must each be tied to zero."""
    for port in OBSERVATION_PORTS:
        match = re.search(rf"\bassign\s+{port}\s*=\s*(\d+)'([bhd])([0-9a-fA-F_]+)\s*;", netlist_text)
        if not match:
            raise ValueError(f"observation port {port} is not a constant assignment in mapped netlist")
        base = {"b": 2, "h": 16, "d": 10}[match.group(2)]
        if int(match.group(3).replace("_", ""), base) != 0:
            raise ValueError(f"observation port {port} is not tied to zero")


def parse_area(log):
    matches = re.findall(r"Chip area for module[^:]*:\s*([0-9.]+)", log)
    if not matches:
        raise ValueError("Yosys did not report mapped chip area")
    return float(matches[-1])


def sta_run(top, netlist, lib, period, outdir):
    sdc = outdir / f"clock_{period:.2f}.sdc"
    sdc.write_text((FLOW / "constraints.sdc.in").read_text().replace("@PERIOD_NS@", f"{period:.2f}"))
    script = outdir / f"sta_{period:.2f}.tcl"
    script.write_text("\n".join([f"read_liberty {lib}", f"read_verilog {netlist}",
                                 f"link_design {top}", f"read_sdc {sdc}",
                                 "report_checks -path_delay max -group_path_count 1",
                                 "report_worst_slack -max", "exit"]) + "\n")
    log = command(["sta", str(script)], cwd=outdir)
    (outdir / f"sta_{period:.2f}.log").write_text(log)
    match = re.search(r"worst slack(?: max)?\s+(-?[0-9.]+)", log, re.I)
    if not match:
        raise ValueError("OpenSTA worst slack missing; inspect report")
    start = re.search(r"Startpoint:\s*(.+)", log)
    end = re.search(r"Endpoint:\s*(.+)", log)
    return float(match.group(1)), start.group(1).strip() if start else "", end.group(1).strip() if end else ""


def sweep(top, netlist, lib, outdir):
    tested = []
    first_passing = None
    for period in COARSE_PERIODS:
        slack, start, end = sta_run(top, netlist, lib, float(period), outdir)
        tested.append({"period_ns": float(period), "slack_ns": slack, "startpoint": start, "endpoint": end})
        if slack >= 0:
            first_passing = float(period)
            break
    if first_passing is None:
        raise RuntimeError("no passing period up to 500 ns")
    lower = tested[-2]["period_ns"] if len(tested) > 1 else 0.0
    # Refine the measured passing/failing bracket to 0.1 ns resolution.
    # A full 0.1 ns grid across the coarse bracket would take thousands of STA runs.
    while first_passing - lower > 0.1 + 1e-9:
        candidate = round((first_passing + lower) / 2, 2)
        if candidate <= lower or candidate >= first_passing:
            break
        slack, start, end = sta_run(top, netlist, lib, candidate, outdir)
        tested.append({"period_ns": candidate, "slack_ns": slack,
                       "startpoint": start, "endpoint": end})
        if slack >= 0:
            first_passing = candidate
        else:
            lower = candidate
    passing = min((r for r in tested if r["slack_ns"] >= 0), key=lambda r: r["period_ns"])
    return passing, tested


def run_one(row, repeat, cfg, lib, versions):
    outdir = FLOW / "raw" / row["variant"] / f"repeat_{repeat}"
    outdir.mkdir(parents=True, exist_ok=True)
    netlist = outdir / "mapped.v"
    script, top, sources, params = yosys_script(row, cfg, lib, netlist)
    (outdir / "synth.ys").write_text(script)
    ylog = command(["yosys", "-s", str(outdir / "synth.ys")], cwd=outdir)
    (outdir / "yosys.log").write_text(ylog)
    if row["top"] == "cache":
        check_observation_outputs(netlist.read_text())
    area = parse_area(ylog)
    passing, tested = sweep(top, netlist, lib, outdir)
    raw = {"variant": row["variant"], "repeat": repeat, "top": top,
           "dcache_bytes": int(row["dcache_bytes"]), "detector": row["detector"],
           "M": row["M"], "area_um2": area,
           "min_passing_period_ns": passing["period_ns"],
           "fmax_mhz": 1000 / passing["period_ns"],
           "critical_startpoint": passing["startpoint"],
           "critical_endpoint": passing["endpoint"],
           "period_sweep": tested, "tool_versions": versions,
           "parameters": params, "interface_sha256": sha(FLOW / "interface.json"),
           "pdk_lib_sha256": sha(lib), "constraints_sha256": sha(FLOW / "constraints.sdc.in"),
           "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in sources},
           "mapped_netlist_sha256": sha(netlist), "pinned_image_id": IMAGE_ID}
    (outdir / "result.json").write_text(json.dumps(raw, indent=2) + "\n")
    return raw


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--check-plan", action="store_true")
    group.add_argument("--execute", action="store_true")
    ap.add_argument("--repeats", type=int, default=3)
    args = ap.parse_args()
    rows = read_plan()
    if args.check_plan:
        print(f"flow plan: {len(rows)} variants; no EDA tool invoked")
        return
    if os.environ.get("WH_AUTHORIZED_FLOW") != "1" or os.environ.get("WH_PINNED_IMAGE_ID") != IMAGE_ID:
        raise SystemExit("author-only flow: pinned image ID and WH_AUTHORIZED_FLOW=1 required")
    if args.repeats < 1:
        ap.error("repeats must be positive")
    cfg, lib = load_interface(), library()
    versions = {"yosys": command(["yosys", "-V"]).strip(),
                "sta": command(["sta", "-version"]).strip(),
                "image_id": IMAGE_ID}
    for row in rows:
        for rep in range(1, args.repeats + 1):
            print(f"physical flow {row['variant']} repeat {rep}/{args.repeats}", flush=True)
            run_one(row, rep, cfg, lib, versions)
    print(f"flow raw results: {len(rows) * args.repeats} completed")


if __name__ == "__main__":
    main()
