"""caches.py: cache-size and line-size sweeps, miss rates and the stall breakdown (T2.7).

Usage:   python3 analysis/caches.py [--quick]      (or: make caches)
Runs every workload of tests/workloads.py (Dhrystone, CoreMark, the 8 Embench kernels, memcpy_big,
memset_big, storeloop) under Verilator on the pipelined core with caches on, memory latency 20 cycles
(spec Section 3), for
  size sweep       I$ and D$ both 1, 2, 4, 8 KiB, 16-byte lines, direct-mapped
  line-size sweep  I$ and D$ both 2 KiB with 16, 32 and 64-byte lines
Each run must halt with exit code 0 (the workload's own self-check) or the script stops.
Counters are measured over the same window as the cycle counts (between the program's MMIO start and
stop writes; tb/tb_prog.sv snapshots the cache counters there), so miss rates and CPI describe the same
region of the program.
Writes analysis/caches.csv (one row per workload and configuration), analysis/caches_size.png and
analysis/caches_line.png with a provenance sidecar .json each (script, git commit, CSV sha256), and
prints a summary. Definitions:
  d_miss_rate  D$ misses / D$ accesses (a request whose first lookup missed is a miss; restricted stores
               excluded; none here)
  i_miss_rate  I$ misses / retired instructions (the I$ is looked up every cycle, including repeated
               lookups of one address while the pipeline is stalled, so per-instruction is the stable
               denominator)
  stall_*      cycles in the window: load-use, flush (2 per redirect), I$ miss, D$ miss (imiss and dmiss
               cycles can overlap other stalls and each other, so the columns do not add up to
               cycles - instret)
--quick runs 3 workloads and the size sweep only.
"""
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, HERE)
from paths import CORE_RTL, TB, work_dir          # noqa: E402
from vl_tb import _build as vl_build              # noqa: E402
from prog_runner import parse_output              # noqa: E402
from baseline import workloads as build_workloads  # noqa: E402

QUICK = "--quick" in sys.argv
LAT = 20
SIZES = [1024, 2048, 4096, 8192]
LINES = [16, 32, 64]
KEYS = ("ic_lookup", "ic_miss", "ic_stall", "dc_access", "dc_hit", "dc_miss", "dc_fill", "dc_wb", "dc_bypass",
        "dc_rab", "dc_stall", "dc_write")


def configs():
    cfgs = [(sz, sz, 16, "size") for sz in SIZES]
    if not QUICK:
        cfgs += [(2048, 2048, lb, "line") for lb in LINES if lb != 16]
    return cfgs


def run(item, cfg, total_budget):
    name, cls, hexf = item[0], item[1], item[2]
    ib, db, lb, sweep = cfg
    d = work_dir(f"caches/{re.sub('[^A-Za-z0-9]+', '_', name)}_i{ib}_d{db}_l{lb}")
    open(os.path.join(d, "program.hex"), "w").write(open(hexf).read())
    exe = vl_build("tb_prog", [*CORE_RTL, os.path.join(TB, "sys_monitor.sv"), os.path.join(TB, "tb_prog.sv")],
                   {"CACHES": 1, "LAT": LAT, "MEMW": 65536, "IMAGE": 1, "ICB": ib, "DCB": db, "LINEB": lb, "MAXCYC": 800_000_000})
    out = subprocess.run([exe, f"+maxcyc={total_budget}"], cwd=d, capture_output=True, text=True).stdout
    r = parse_output(out)
    m = re.search(r"CACHEWIN " + " ".join(f"{k}=(\\d+)" for k in KEYS), out)
    if r["timeout"] or r["halt"] != 0 or not r["perf"] or not m:
        sys.exit(f"caches.py: {name} {cfg} failed: halt={r['halt']} timeout={r['timeout']} perf={bool(r['perf'])} cachewin={bool(m)}")
    c = dict(zip(KEYS, map(int, m.groups())))
    p = r["perf"]
    return {"workload": name, "class": cls, "sweep": sweep, "icache_bytes": ib, "dcache_bytes": db, "line_bytes": lb,
            "mem_latency": LAT, "cycles": p["cycles"], "instret": p["instret"], "cpi": round(p["cycles"] / p["instret"], 4),
            "i_misses": c["ic_miss"], "i_miss_rate": round(c["ic_miss"] / p["instret"], 6),
            "d_accesses": c["dc_access"], "d_misses": c["dc_miss"],
            "d_miss_rate": round(c["dc_miss"] / c["dc_access"], 6) if c["dc_access"] else 0.0,
            "d_fills": c["dc_fill"], "d_writebacks": c["dc_wb"],
            "stall_loaduse": p["stall_loaduse"], "stall_flush": p["flush_cycles"],
            "stall_imiss": p["imiss_cycles"], "stall_dmiss": p["dmiss_cycles"]}


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def plot(rows, sweep, xkey, xlabel, fname, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sub = [r for r in rows if r["sweep"] == sweep or (sweep == "line" and r["sweep"] == "size" and r["icache_bytes"] == 2048)
           or (sweep == "size" and r["sweep"] == "size")]
    names = sorted({r["workload"] for r in sub}, key=lambda n: [r["workload"] for r in rows].index(n))
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharex=True)
    cmap = plt.get_cmap("tab20")
    for ax, key, lab in ((axes[0], "d_miss_rate", "D$ miss rate (misses / accesses)"), (axes[1], "i_miss_rate", "I$ misses per retired instruction")):
        for i, n in enumerate(names):
            pts = sorted(((r[xkey], r[key]) for r in sub if r["workload"] == n))
            ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", ms=3, lw=1.2, color=cmap(i % 20), label=n.split(" (")[0])
        ax.set_xscale("log", base=2)
        ax.set_xticks(sorted({r[xkey] for r in sub}))
        ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
        ax.set_xlabel(xlabel.replace("$", r"\$")); ax.set_ylabel(lab.replace("$", r"\$")); ax.grid(alpha=0.3)
    axes[1].legend(fontsize=6, ncol=2, loc="upper right")
    fig.suptitle(title.replace("$", r"\$"), fontsize=10)
    fig.tight_layout()
    path = os.path.join(HERE, fname)
    fig.savefig(path, dpi=130)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    json.dump({"figure": fname, "generated_by": "analysis/caches.py", "git_commit": commit,
               "data": "analysis/caches.csv", "data_sha256": sha(os.path.join(HERE, "caches.csv")), "quick": QUICK},
              open(path.replace(".png", ".json"), "w"), indent=1)


def main():
    wl = build_workloads()
    if QUICK:
        wl = [w for w in wl if w[0].split(" (")[0] in ("Dhrystone", "crc32", "memcpy_big")]
    cfgs = configs()
    jobs = [(w, c) for w in wl for c in cfgs]
    with ThreadPoolExecutor(max_workers=int(os.environ.get("JOBS", "4"))) as ex:
        rows = list(ex.map(lambda a: run(a[0], a[1], 2_000_000_000), jobs))
    rows.sort(key=lambda r: ([w[0] for w in wl].index(r["workload"]), r["sweep"], r["icache_bytes"], r["line_bytes"]))
    out = os.path.join(HERE, "caches.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    plot(rows, "size", "icache_bytes", "cache size (bytes, I$ = D$, 16-byte lines)", "caches_size.png",
         f"Miss rate vs cache size, memory latency {LAT}, direct-mapped (generated by analysis/caches.py)")
    if not QUICK:
        plot(rows, "line", "line_bytes", "line size (bytes, 2 KiB caches)", "caches_line.png",
             f"Miss rate vs line size, 2 KiB caches, memory latency {LAT} (generated by analysis/caches.py)")
    print(f"{'workload':18s} {'cache':>6s} {'line':>4s} {'cycles':>10s} {'CPI':>6s} {'D$ miss%':>9s} {'I$ mpi':>8s}")
    for r in rows:
        print(f"{r['workload'][:18]:18s} {r['icache_bytes']:6d} {r['line_bytes']:4d} {r['cycles']:10d} {r['cpi']:6.3f} {100 * r['d_miss_rate']:9.3f} {r['i_miss_rate']:8.5f}")


if __name__ == "__main__":
    main()
