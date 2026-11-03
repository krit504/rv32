"""guard_integration.py: correctness invariant with the write_guard active (spec T5.8) plus metric rows (T5.9).

Usage:   python3 tests/guard_integration.py [--quick | --mini] [--csv PATH]
For every image (benign workloads, attack programs, mixed workloads) the final architectural signature
(exit code, program output, register hash, hash of every memory word with the D$ overlaid) with a detector
or control active must equal the caches-off signature, for every arm and memory latency 1, 20 and random.
Arms: NEVER, ALWAYS, PLACEBO, D1, D2, D3 STATIC, D3 ADAPTIVE with deliberately small windows and
thresholds ("stress") so that restriction really happens on short programs, plus D1, D3 with the calibrated
THRESHOLD (k=2, window 10000) from analysis/calibration.csv.
Also checks (so a pass cannot be vacuous): every stress arm restricted at least one store somewhere;
NEVER restricted none and its bypass/refill counters equal the NONE run's; ALWAYS restricted every store.
--mini (used by tests/guard_mutants.py against RTL mutants) runs two images, arms ALWAYS and D1 stress, latency 20.
Needs the attack and mixed images from `make attacks`. --quick uses a subset of images.
Output: PASS/FAIL lines, "[guard_integration] ..." summary, a CSV of metric rows (default
work/guard_integration/results.csv); exit 0 only if every signature agrees and the checks hold.
"""
import csv
import glob
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from paths import ROOT, CORE_RTL, TB, work_dir
from vl_tb import _build as vl_build
from prog_runner import parse_output

sys.path.insert(0, os.path.join(ROOT, "analysis"))
QUICK = "--quick" in sys.argv or "--mini" in sys.argv
MINI = "--mini" in sys.argv    # two images, ALWAYS and D1 only, latency 20: the quick check run against RTL mutants
CSV_PATH = sys.argv[sys.argv.index("--csv") + 1] if "--csv" in sys.argv else os.path.join(work_dir("guard_integration"), "results.csv")
JOBS = int(os.environ.get("JOBS", "6"))
SRCS = [*CORE_RTL, os.path.join(TB, "sys_monitor.sv"), os.path.join(TB, "tb_prog.sv")]
MAXCYC = 150_000_000


def calibrated(det, k=2, window=10000):
    for r in csv.DictReader(open(os.path.join(ROOT, "analysis", "calibration.csv"))):
        if r["detector"] == det and int(r["window_cycles"]) == window and float(r["k"]) == k and int(r["M"]) in (0, 16):
            return int(r["threshold"])
    raise SystemExit(f"no calibration row for {det}")


ARMS = [
    ("NEVER", dict(DETECTOR=5)),
    ("ALWAYS", dict(DETECTOR=1)),
    ("PLACEBO", dict(DETECTOR=6, WG_PLACEBO_RATE=16384, WG_PLACEBO_SEED=5)),
    ("D1_stress", dict(DETECTOR=2, WG_WINDOW=500, WG_THRESHOLD=6)),
    ("D2_stress", dict(DETECTOR=3, WG_WINDOW=500, WG_THRESHOLD=6, WG_M=16)),
    ("D3_static_stress", dict(DETECTOR=4, WG_MODE=0, WG_WINDOW=500, WG_THRESHOLD=20)),
    ("D3_adaptive_stress", dict(DETECTOR=4, WG_MODE=1, WG_WINDOW=500, WG_THRESHOLD=20)),
    ("D1_calibrated", dict(DETECTOR=2, WG_WINDOW=10000, WG_THRESHOLD=calibrated("D1"))),
    ("D3_calibrated", dict(DETECTOR=4, WG_MODE=1, WG_WINDOW=10000, WG_THRESHOLD=calibrated("D3"))),
]
LATS = [("L1", 1, 0, 1), ("L20", 20, 0, 1), ("rand10", 10, 1, 3)]
if MINI:
    ARMS = [a for a in ARMS if a[0] in ("ALWAYS", "D1_stress")]
    LATS = [l for l in LATS if l[0] == "L20"]


def images():
    from baseline import workloads
    out = [(n, h) for n, _c, h, _k, _r in workloads()]
    out += [(f"attack_{os.path.basename(os.path.dirname(os.path.dirname(p)))}", p)
            for p in sorted(glob.glob(os.path.join(ROOT, "work", "attack_run", "*", "build", "program.hex")))]
    out += [(f"mixed_{os.path.basename(os.path.dirname(os.path.dirname(p)))}", p)
            for p in sorted(glob.glob(os.path.join(ROOT, "work", "attack_mixed", "*", "build", "program.hex")))]
    if QUICK:
        keep = ("Dhrystone", "CoreMark", "memcpy_big", "crc32", "attack_rla_direct_s1", "attack_rnta_paper_s1",
                "attack_rta_direct_s1", "mixed_rla")
        out = [x for x in out if x[0].startswith(keep)]
    if MINI:
        out = [x for x in out if x[0].startswith(("Dhrystone", "attack_rla_direct_s1"))]
    if not any(n.startswith("attack_") for n, _ in out):
        raise SystemExit("no attack images under work/attack_run: run `make attacks` first")
    return out


def run_one(name, hexf, caches, lat, rl, seed, extra):
    d = work_dir(f"guard_integration/{re.sub('[^A-Za-z0-9]+', '_', name)}")
    open(os.path.join(d, "program.hex"), "w").write(open(hexf).read())
    params = {"CACHES": caches, "LAT": lat, "RANDLAT": rl, "MEM_SEED": seed, "MEMW": 65536, "IMAGE": 1,
              "HASH": 1, "MAXCYC": 800_000_000, **extra}
    exe = vl_build("tb_prog", SRCS, params)
    out = subprocess.run([exe, f"+maxcyc={MAXCYC}"], cwd=d, capture_output=True, text=True).stdout
    r = parse_output(out)
    sig = ("TIMEOUT",) if r["timeout"] else (r["halt"], r["text"], re.search(r"REGHASH (\w+)", out).group(1) if "REGHASH" in out else None,
                                             re.search(r"MEMHASH (\w+)", out).group(1) if "MEMHASH" in out else None)
    wg = {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", (re.search(r"^WG .*$", out, re.M) or re.search("^$", "")).group(0))}
    cw = {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", (re.search(r"^CACHEWIN .*$", out, re.M) or re.search("^$", "")).group(0))}
    m = re.search(r"^PERF cycles=(\d+)", out, re.M)
    return sig, wg, cw, r["perf"]["cycles"] if r.get("perf") else None


def job(item):
    name, hexf = item
    ref, *_ = run_one(name, hexf, 0, 2, 0, 1, {})
    rows, bad = [], []
    if ref[0] != 0 or ref[0] == "TIMEOUT" or ref[2] is None:
        return name, rows, [f"reference run failed: {ref[:2]}"]
    none_sig, _, none_cw, none_cyc = run_one(name, hexf, 1, 20, 0, 1, {"DETECTOR": 0})
    for lname, lat, rl, seed in LATS:
        for aname, extra in ARMS:
            sig, wg, cw, cyc = run_one(name, hexf, 1, lat, rl, seed, extra)
            if sig != ref:
                bad.append(f"{aname}/{lname}: signature {sig[:1]}/{sig[2:]} != caches-off {ref[:1]}/{ref[2:]}")
            rows.append({"image": name, "arm": aname, "latency": lname, "cycles": cyc, **wg,
                         "dc_bypass": cw.get("dc_bypass"), "dc_rab": cw.get("dc_rab"), "dc_write": cw.get("dc_write")})
            if aname == "NEVER" and lname == "L20":
                if wg.get("stores_restricted") != 0 or wg.get("restricted_cycles") != 0:
                    bad.append("NEVER restricted something")
                if cyc != none_cyc or {k: cw.get(k) for k in cw} != {k: none_cw.get(k) for k in cw}:
                    bad.append(f"NEVER differs from NONE: cycles {cyc} vs {none_cyc}, counters {cw} vs {none_cw}")
            if aname == "ALWAYS" and wg.get("stores") != wg.get("stores_restricted"):
                bad.append(f"ALWAYS let a store through: {wg}")
    return name, rows, bad


if __name__ == "__main__":
    imgs = images()
    print(f"[guard_integration] {len(imgs)} images x {len(ARMS)} arms x {len(LATS)} latencies", flush=True)
    with ThreadPoolExecutor(max_workers=JOBS) as ex:
        results = list(ex.map(job, imgs))
    allrows, nbad = [], 0
    for name, rows, bad in results:
        print(("PASS " if not bad else "FAIL ") + name + ("" if not bad else ": " + "; ".join(bad[:3])))
        nbad += bool(bad)
        allrows += rows
    # non-vacuity: every restricting arm must have restricted at least one store somewhere
    for aname, extra in ARMS:
        if aname.endswith("_stress") or aname in ("ALWAYS", "PLACEBO"):
            tot = sum(r.get("stores_restricted") or 0 for r in allrows if r["arm"] == aname)
            if tot == 0:
                print(f"FAIL {aname}: restricted no store in any run (vacuous)")
                nbad += 1
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    cols = sorted({k for r in allrows for k in r}, key=lambda k: (k not in ("image", "arm", "latency"), k))
    with open(CSV_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(allrows)
    print(f"[guard_integration] {len(results) - sum(1 for _, _, b in results if b)}/{len(results)} images passed; rows -> {CSV_PATH}")
    sys.exit(1 if nbad else 0)
