"""T6 matrix manifest and resumable Verilator evaluation.

Usage: python3 analysis/eval_matrix.py --manifest-only
       python3 analysis/eval_matrix.py --smoke
       python3 analysis/eval_matrix.py --run
The full detector runs require docs/T5_INTERFACE.md and calibration.csv.
Attack taxonomy: prior work of the author's group (TENDRA/Write Hammer draft).
"""
import argparse
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from attacks import load_cases  # noqa: E402
from paths import CORE_RTL, TB  # noqa: E402
from prog_runner import parse_output  # noqa: E402
from vl_tb import _build as vl_build  # noqa: E402
sys.path.insert(0, str(ROOT / "analysis"))
from baseline import workloads as benign_workloads  # noqa: E402
from attack_runner import flags as attack_flags  # noqa: E402
from wear_stats import main as wear_stats  # noqa: E402

RESULT_COLUMNS = """run_id git_commit workload workload_class icache_bytes dcache_bytes line_bytes mem_latency dc_write_latency detector action mode window_cycles threshold_k threshold M seed cycles instret cpi stall_loaduse stall_flush stall_imiss stall_dmiss i_miss_rate d_miss_rate array_writes_total w_max w_mean pmr_all pmr_written t_fail_50mhz t_fail_100mhz t_fail_500mhz bypassed_stores refills_after_bypass restricted_cycle_frac fp_cycle_frac fp_store_frac detect_latency_cycles signature_hash correct""".split()
MANIFEST_COLUMNS = ["run_id", "workload", "workload_class", "source_kind", "source_id", "icache_bytes", "dcache_bytes", "line_bytes", "mem_latency", "dc_write_latency", "detector", "action", "mode", "window_cycles", "threshold_k", "threshold", "M", "seed", "control_for", "manifest_status"]
SIZES = (1024, 2048, 4096, 8192)
WINDOWS = (1000, 10000, 100000)
KS = (1.5, 2, 4)
MS = (4, 8, 16, 32, 64)
MODES = ("STATIC", "ADAPTIVE")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_commit():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def all_workloads():
    items = [(f"Dhrystone ({n} runs)" if kind == "dhrystone" else f"CoreMark ({n} iterations)",
              "calibration", "benign", name, 1) for name, kind, n in __import__("workloads").CALIBRATION]
    items += [(name, "held-out", "benign", name, 1)
              for name, _kind, _arg in __import__("workloads").HELD_OUT]
    items += [(case.id, "attack", "attack", case.id, case.seed) for case in load_cases()]
    items += [(f"mixed_{kind.lower()}", "mixed", "mixed", kind, 1)
              for kind in ("RLA", "RTA", "RnLA", "RnTA")]
    assert len(items) == 41
    return items


def planned_rows():
    items = all_workloads()
    rows = []
    def add(item, detector, *, icb=2048, dcb=2048, caches=1, mode="", window=10000,
            k="", m="", control_for=""):
        name, cls, source_kind, source_id, seed = item
        key = [name, caches, icb, dcb, 16, detector, mode, window, k, m, seed, control_for]
        run_id = "ev_" + hashlib.sha256(json.dumps(key).encode()).hexdigest()[:16]
        rows.append(dict(run_id=run_id, workload=name, workload_class=cls,
                         source_kind=source_kind, source_id=source_id,
                         icache_bytes=icb, dcache_bytes=dcb, line_bytes=16,
                         mem_latency=20, dc_write_latency=1, detector=detector,
                         action="A1" if detector not in ("NONE", "NEVER") else "NONE",
                         mode=mode, window_cycles=window, threshold_k=k, threshold="", M=m,
                         seed=seed, control_for=control_for,
                         manifest_status="PROVISIONAL" if detector not in ("NONE", "ALWAYS") else "READY"))
    for item in items:
        add(item, "NONE", caches=0, icb=0, dcb=0)
        for size in SIZES:
            add(item, "NONE", icb=size, dcb=size)
    for item in items:
        if item[1] == "mixed":
            variants = [(d, m, md, 10000, 2) for d in ("D1", "D2", "D3")
                        for m in (MS if d == "D2" else ("",)) for md in MODES]
        else:
            variants = [(d, m, md, w, k) for d in ("D1", "D2", "D3")
                        for m in (MS if d == "D2" else ("",)) for md in MODES
                        for w in WINDOWS for k in KS]
        add(item, "NEVER")
        add(item, "ALWAYS")
        for d, m, md, w, k in variants:
            add(item, d, mode=md, window=w, k=k, m=m)
            add(item, "PLACEBO", mode=md, window=w, k=k, m=m,
                control_for=d)
    ids = [r["run_id"] for r in rows]
    assert len(ids) == len(set(ids)), "run_id collision"
    return rows


def write_manifest(rows):
    path = ROOT / "analysis" / "matrix_manifest.csv"
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, MANIFEST_COLUMNS, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    sidecar = {"script": "analysis/eval_matrix.py", "git_commit": git_commit(),
               "manifest_sha256": sha(path),
               "inputs_sha256": {p: sha(ROOT / p) for p in
                                 ("tests/workloads.py", "tests/attacks.py", "sw/attacks/manifest.json", "../docs/writehammer.md")},
               "calibration": "pending docs/T5_INTERFACE.md and analysis/calibration.csv",
               "taxonomy_credit": "Author's group: TENDRA and the Write Hammer draft"}
    Path(str(path) + ".json").write_text(json.dumps(sidecar, indent=2) + "\n")
    return path


def eval_bench():
    """Generate an observation-only Phase A bench; never edit locked tb/ or rtl/."""
    source = (ROOT / "tb" / "tb_prog.sv").read_text()
    def patch(old, new):
        nonlocal source
        assert source.count(old) == 1, f"tb_prog interface changed: {old[:60]}"
        source = source.replace(old, new)
    patch("parameter int LINEB = 16            // line bytes (both caches)",
          "parameter int LINEB = 16,           // line bytes (both caches)\n"
          "    parameter int EVAL_DETECTOR = 0,\n    parameter int EVAL_WINDOW = 10000")
    patch(".CACHES_ON(CACHES), .MEM_LATENCY(LAT)",
          ".CACHES_ON(CACHES), .DETECTOR(EVAL_DETECTOR), .MEM_LATENCY(LAT)")
    patch("    rv32_top_pipelined #(",
          "    logic eval_aw_valid, eval_aw_kind, eval_tr_valid, eval_tr_we, eval_tr_bypass;\n"
          "    logic [31:0] eval_aw_line, eval_tr_addr;\n"
          "    logic [2:0] eval_tr_size;\n"
          "    rv32_top_pipelined #(")
    patch("        .ic_refill_cnt(ic_refill_cnt),", "        .dc_aw_valid(eval_aw_valid), .dc_aw_line(eval_aw_line), .dc_aw_kind(eval_aw_kind),\n"
          "        .dc_tr_valid(eval_tr_valid), .dc_tr_we(eval_tr_we), .dc_tr_addr(eval_tr_addr),\n"
          "        .dc_tr_size(eval_tr_size), .dc_tr_bypass(eval_tr_bypass),\n"
          "        .ic_refill_cnt(ic_refill_cnt),")
    patch("    logic halted;", "    wear_monitor #(.NLINES(DCB/LINEB), .WINDOW_CYCLES(EVAL_WINDOW)) eval_wear (\n"
          "        .clk(clk), .rst_n(rst_n), .aw_valid(eval_aw_valid), .aw_line(eval_aw_line),\n"
          "        .aw_kind(eval_aw_kind), .tr_valid(eval_tr_valid), .tr_we(eval_tr_we),\n"
          "        .tr_addr(eval_tr_addr), .tr_size(eval_tr_size), .tr_bypass(eval_tr_bypass),\n"
          "        .mmio_we(mmio_we), .mmio_addr(mmio_addr), .mmio_wdata(mmio_wdata));\n"
          "    logic halted;")
    patch("            repeat (6) @(posedge clk);          // let the HALT store's neighbours drain",
          "            repeat (6) @(posedge clk);          // let the HALT store's neighbours drain\n"
          "            #1 eval_wear.finish_run();")
    patch('            $display("TIMEOUT after %0d cycles", cyc);',
          '            #1 eval_wear.finish_run();\n            $display("TIMEOUT after %0d cycles", cyc);')
    out = ROOT / "work" / "eval" / "tb_eval.sv"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(source)
    return out


def command(argv, *, env=None):
    proc = subprocess.run(argv, env=env, capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError(f"failed {argv}: {proc.stdout[-500:]} {proc.stderr[-500:]}")


def build_images(items):
    benign = {name: Path(image) for name, _cls, image, _check, _rate in benign_workloads()}
    cases = {case.id: case for case in load_cases()}
    images = {}
    for name, cls, kind, source_id, seed in items:
        if kind == "benign":
            images[name] = benign[name]
        elif kind == "attack":
            case = cases[source_id]
            out = ROOT / "work" / "eval" / "build" / case.id
            env = dict(os.environ, CFLAGS_EXTRA=" ".join(attack_flags(case)))
            command([sys.executable, str(ROOT / "sw" / "build.py"), str(out), str(case.source)], env=env)
            images[name] = out / "program.hex"
        else:
            case = next(c for c in cases.values() if c.kind == source_id and c.form == "direct" and c.seed == 1)
            from dataclasses import replace
            cf = attack_flags(replace(case, run_cycles=1_000_000))
            cf += [f"-DATTACK_KIND={['RLA','RTA','RnLA','RnTA'].index(source_id)+1}",
                   "-DBENIGN_ITERATIONS=100000"]
            out = ROOT / "work" / "eval" / "build" / name
            env = dict(os.environ, CFLAGS_EXTRA=" ".join(cf))
            command([sys.executable, str(ROOT / "sw" / "build.py"), str(out),
                     str(ROOT / "sw/attacks/mixed.c")], env=env)
            images[name] = out / "program.hex"
    return images


def cachewin(output):
    match = re.search(r"^CACHEWIN (.*)$", output, re.M)
    if not match:
        raise ValueError("missing CACHEWIN")
    return {k: int(v) for k, v in re.findall(r"([a-z_]+)=(\d+)", match.group(1))}


def signature(output, parsed):
    reg = re.search(r"^REGHASH ([0-9a-f]+)$", output, re.M)
    mem = re.search(r"^MEMHASH ([0-9a-f]+)$", output, re.M)
    if not reg or not mem or parsed["halt"] is None:
        raise ValueError("missing architectural signature")
    return hashlib.sha256(json.dumps([parsed["halt"], parsed["text"],
                                      reg.group(1), mem.group(1)]).encode()).hexdigest()


def sim_one(plan, image, bench, baseline_signature=None):
    rid = plan["run_id"]
    run_dir = ROOT / "work" / "eval" / "runs" / rid
    run_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(image, run_dir / "program.hex")
    detector = {"NONE": 0, "ALWAYS": 1}[plan["detector"]]
    caches = int(plan["icache_bytes"]) > 0
    icb = int(plan["icache_bytes"]) or 2048
    dcb = int(plan["dcache_bytes"]) or 2048
    params = {"CACHES": int(caches), "LAT": int(plan["mem_latency"]),
              "RANDLAT": 0, "MEM_SEED": 1, "MEMW": 65536, "IMAGE": 1, "HASH": 1,
              "MAXCYC": 800_000_000, "ICB": icb, "DCB": dcb, "LINEB": int(plan["line_bytes"]),
              "EVAL_DETECTOR": detector, "EVAL_WINDOW": int(plan["window_cycles"])}
    sources = CORE_RTL + [str(ROOT / "tb/sys_monitor.sv"),
                          str(ROOT / "tb/wear_monitor.sv"), str(bench)]
    input_signature = hashlib.sha256(json.dumps({
        "plan": plan, "image": sha(image),
        "sources": {str(Path(path).relative_to(ROOT)): sha(path) for path in sources},
        "params": params, "baseline_signature": baseline_signature,
    }, sort_keys=True).encode()).hexdigest()
    meta_path = run_dir / "provenance.json"
    saved_row = run_dir / "result_row.json"
    if meta_path.is_file() and saved_row.is_file():
        meta_old = json.loads(meta_path.read_text())
        if meta_old.get("input_signature") == input_signature and not meta_old.get("reason"):
            print(f"eval resume {rid}: unchanged inputs, reusing completed row", flush=True)
            return json.loads(saved_row.read_text()), ""
    exe = vl_build("tb_prog", sources, params)
    limit = 20_000_000 if plan["workload_class"] in ("attack", "mixed") else 500_000_000
    stop = threading.Event()
    def heartbeat():
        while not stop.wait(30):
            print(f"eval heartbeat {rid}", flush=True)
    thread = threading.Thread(target=heartbeat, daemon=True); thread.start()
    try:
        proc = subprocess.run([exe, f"+maxcyc={limit}"], cwd=run_dir,
                              capture_output=True, text=True, timeout=1800)
    finally:
        stop.set(); thread.join()
    output = proc.stdout + proc.stderr
    (run_dir / "simulation.log").write_text(output)
    parsed = parse_output(output)
    row = {field: "" for field in RESULT_COLUMNS}
    row.update({k: plan[k] for k in ("run_id", "workload", "workload_class", "icache_bytes",
                                   "dcache_bytes", "line_bytes", "mem_latency", "dc_write_latency",
                                   "detector", "action", "mode", "window_cycles", "threshold_k",
                                   "threshold", "M", "seed")})
    row["git_commit"] = git_commit()
    if proc.returncode or parsed["timeout"] or parsed["halt"] != 0:
        row["correct"] = 0
        reason = f"sim_failed rc={proc.returncode} timeout={parsed['timeout']} halt={parsed['halt']}"
    else:
        perf = parsed["perf"]
        counters = cachewin(output)
        sig = signature(output, parsed)
        row["signature_hash"] = sig
        row["correct"] = int(baseline_signature is None or sig == baseline_signature)
        row.update({"cycles": perf["cycles"], "instret": perf["instret"],
                    "cpi": perf["cycles"] / perf["instret"] if perf["instret"] else "",
                    "stall_loaduse": perf["stall_loaduse"], "stall_flush": perf["flush_cycles"],
                    "stall_imiss": perf["imiss_cycles"], "stall_dmiss": perf["dmiss_cycles"],
                    "i_miss_rate": counters["ic_miss"] / counters["ic_lookup"] if counters["ic_lookup"] else 0,
                    "d_miss_rate": counters["dc_miss"] / counters["dc_access"] if counters["dc_access"] else 0,
                    "bypassed_stores": counters["dc_bypass"],
                    "refills_after_bypass": counters["dc_rab"]})
        if caches:
            wear_stats(run_dir)
            wear = json.loads((run_dir / "wear_summary.json").read_text())
            row.update({"array_writes_total": wear["array_writes"], "w_max": wear["w_max"],
                        "w_mean": wear["mean_all"], "pmr_all": wear["pmr_all"],
                        "pmr_written": wear["pmr_written"],
                        "t_fail_50mhz": wear["t_fail_extrapolated_seconds"]["50"],
                        "t_fail_100mhz": wear["t_fail_extrapolated_seconds"]["100"],
                        "t_fail_500mhz": wear["t_fail_extrapolated_seconds"]["500"]})
        reason = "" if row["correct"] else "signature_mismatch"
    meta = {"run_id": rid, "script": "analysis/eval_matrix.py", "git_commit": row["git_commit"],
            "input_signature": input_signature,
            "image_sha256": sha(image), "bench_sha256": sha(bench),
            "rtl_sha256": hashlib.sha256("".join(sha(x) for x in CORE_RTL).encode()).hexdigest(),
            "simulation_sha256": sha(run_dir / "simulation.log"), "reason": reason,
            "max_cycles": limit, "wall_timeout_seconds": 1800}
    (run_dir / "provenance.json").write_text(json.dumps(meta, indent=2) + "\n")
    saved_row.write_text(json.dumps(row, indent=2) + "\n")
    return row, reason


def write_results(rows, *, development_subset=True):
    out = ROOT / "analysis" / "results.csv"
    with out.open("w", newline="") as file:
        writer = csv.DictWriter(file, RESULT_COLUMNS, lineterminator="\n")
        writer.writeheader(); writer.writerows(sorted(rows, key=lambda r: r["run_id"]))
    sidecar = {"script": "analysis/eval_matrix.py", "git_commit": git_commit(),
               "results_sha256": sha(out), "manifest_sha256": sha(ROOT / "analysis/matrix_manifest.csv"),
               "run_count": len(rows), "development_subset": development_subset}
    Path(str(out) + ".json").write_text(json.dumps(sidecar, indent=2) + "\n")


def write_exclusions(plans, completed, *, phase):
    done = {r["run_id"] for r in completed}
    missing = [r for r in plans if r["run_id"] not in done]
    manifest = ROOT / "analysis/matrix_manifest.csv"
    lines = ["# T6.1 planned and excluded runs", "",
             "Generated by `analysis/eval_matrix.py` from `analysis/matrix_manifest.csv`.",
             f"Source commit: `{git_commit()}`. Manifest SHA-256: `{sha(manifest)}`.",
             f"Phase: {phase}. Planned: {len(plans)}. Completed: {len(done)}. Missing: {len(missing)}.", "",
             "Every missing run is listed below. A pending run is not an observed result.", "",
             "| Run ID | Workload | Detector | Reason |", "|---|---|---|---|"]
    for row in missing:
        reason = ("T5 interface and calibration unavailable" if row["manifest_status"] == "PROVISIONAL"
                  else "not selected in Phase A smoke")
        lines.append(f"| `{row['run_id']}` | {row['workload']} | {row['detector']} | {reason} |")
    (ROOT / "docs/EXCLUDED_RUNS.md").write_text("\n".join(lines) + "\n")
    sidecar = {"script": "analysis/eval_matrix.py", "git_commit": git_commit(),
               "manifest_sha256": sha(manifest), "planned": len(plans),
               "completed": len(done), "missing": len(missing),
               "excluded_document_sha256": sha(ROOT / "docs/EXCLUDED_RUNS.md")}
    (ROOT / "analysis/eval_exclusions.json").write_text(json.dumps(sidecar, indent=2) + "\n")


def smoke(rows):
    wanted = {"storeloop", "rla_direct_s1"}
    selected = [r for r in rows if r["workload"] in wanted and
                (r["icache_bytes"] == 0 or r["icache_bytes"] == 2048) and
                r["detector"] == "NONE"]
    selected += [r for r in rows if r["workload"] in wanted and
                 r["icache_bytes"] == 2048 and r["detector"] == "ALWAYS"]
    images = build_images([i for i in all_workloads() if i[0] in wanted])
    bench = eval_bench()
    result = []
    baselines = {}
    for workload in wanted:
        group = [p for p in selected if p["workload"] == workload]
        group.sort(key=lambda p: (p["detector"] != "NONE", p["icache_bytes"] != 0))
        for plan in group:
            baseline_sig = baselines.get(workload)
            row, reason = sim_one(plan, images[workload], bench, baseline_sig)
            result.append(row)
            if plan["detector"] == "NONE" and plan["icache_bytes"] == 0 and row["correct"] == 1:
                baselines[workload] = row["signature_hash"]
            if reason:
                raise AssertionError(f"{plan['run_id']}: {reason}")
            print(f"eval smoke PASS {plan['workload']} {plan['detector']} cache={plan['icache_bytes']}", flush=True)
    write_results(result)
    write_exclusions(rows, result, phase="Phase A smoke")
    print(f"[eval-smoke] {len(result)}/{len(result)} passed")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--manifest-only", action="store_true")
    group.add_argument("--smoke", action="store_true")
    group.add_argument("--run", action="store_true")
    args = ap.parse_args()
    rows = planned_rows()
    path = write_manifest(rows)
    print(f"matrix manifest: {len(rows)} planned runs; {path}")
    if args.smoke:
        smoke(rows)
    elif args.run:
        if not (ROOT / "docs/T5_INTERFACE.md").is_file() or not (ROOT / "analysis/calibration.csv").is_file():
            raise SystemExit("full T6.1 run waits for docs/T5_INTERFACE.md and analysis/calibration.csv")
        raise SystemExit("full T6.1 execution adapter pending final T5 parameter names")


if __name__ == "__main__":
    main()
