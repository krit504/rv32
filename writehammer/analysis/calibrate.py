"""Threshold calibration for the write_guard detectors (spec T5.6).

Usage: .venv/bin/python analysis/calibrate.py   (or make calibrate)
Inputs: the CALIBRATION set of the locked registry tests/workloads.py (Dhrystone, CoreMark) only; each is run
on the frozen RTL with no detector (2 KiB D$, 16-byte lines, 20-cycle memory) once per window length in
WINDOWS. The held-out set is never built or read: the script builds only the CALIBRATION registry entries
and aborts if any other entry would be read.
Per window length it takes, over both workloads, the maximum per-window count for
  D1  array writes of one D$ line,
  D2  array writes summed over one hash bucket, for each M in D2_M (same hash as rtl/write_guard.sv),
  D3  completed stores (not only array writes),
and writes THRESHOLD = ceil(k x max) for k in K_VALUES.
Output: analysis/calibration.csv (+ .json sidecar with the source hashes). Window boundaries here are
cycle // WINDOW; the RTL window timer starts at reset and defers a boundary past a mid-request store, so
RTL windows can differ by a few cycles (documented in docs/T5_INTERFACE.md).
"""
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tests"))
from baseline import build  # noqa: E402
from paths import work_dir  # noqa: E402
from workloads import CALIBRATION  # noqa: E402
from wear_run import run  # noqa: E402
from guard_model import bucket  # noqa: E402

def calibration_entries():
    """(name, class, image) for the CALIBRATION registry only; held-out workloads are never built."""
    out = []
    for name, kind, arg in CALIBRATION:
        if kind == "dhrystone":
            out.append((f"Dhrystone ({arg} runs)", "calibration", build("dhrystone/build_dhrystone.py", work_dir("baseline/dhrystone"), arg)))
        else:
            out.append((f"CoreMark ({arg} iterations)", "calibration", build("coremark/build_coremark.py", work_dir("baseline/coremark"), arg)))
    return out


WINDOWS = (1000, 10000, 100000)
K_VALUES = (1.5, 2, 4)
D2_M = (4, 8, 16, 32, 64)
LINES = 128
CALIBRATION_CLASS = "calibration"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def window_counts(rundir, window):
    """(per (win,line) array-write counts, per-window completed stores) from one run directory."""
    lines = {}
    with open(rundir / "wear_windows.csv") as f:
        for r in csv.DictReader(f):
            lines[(int(r["window"]), int(r["line"]))] = int(r["count"])
    stores = {}
    with open(rundir / "dc_trace.csv") as f:
        for r in csv.DictReader(f):
            if r["type"] == "S":
                w = int(r["cycle"]) // window
                stores[w] = stores.get(w, 0) + 1
    return lines, stores


def main():
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    entries = calibration_entries()
    if not entries or any(e[1] != CALIBRATION_CLASS for e in entries):
        raise SystemExit("calibrate: refusing to run: non-calibration workload in the input set")
    print("calibrating on:", ", ".join(e[0] for e in entries), flush=True)
    rows, hashes = [], {}
    for window in WINDOWS:
        d1max, d3max = 0, 0
        d2max = {m: 0 for m in D2_M}
        for name, _cls, image in entries:
            slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
            d = ROOT / "work" / "calibration" / f"w{window}" / slug
            run(image, d, maxcyc=500_000_000, window=window, lat=20)
            lines, stores = window_counts(d, window)
            hashes[f"w{window}/{slug}"] = {"wear_windows.csv": sha(d / "wear_windows.csv"),
                                           "dc_trace.csv": sha(d / "dc_trace.csv")}
            d1max = max(d1max, max(lines.values(), default=0))
            d3max = max(d3max, max(stores.values(), default=0))
            for m in D2_M:
                acc = {}
                for (w, line), c in lines.items():
                    key = (w, bucket(line, m))
                    acc[key] = acc.get(key, 0) + c
                d2max[m] = max(d2max[m], max(acc.values(), default=0))
        spec = [("D1", 0, d1max)] + [("D2", m, d2max[m]) for m in D2_M] + [("D3", 0, d3max)]
        for det, m, mx in spec:
            for k in K_VALUES:
                rows.append({"detector": det, "M": m, "window_cycles": window, "k": k,
                             "max_count": mx, "threshold": max(1, math.ceil(k * mx)),
                             "calibration_set": "+".join(e[0] for e in entries)})
    out = HERE / "calibration.csv"
    with out.open("w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        wr.writeheader()
        wr.writerows(rows)
    (HERE / "calibration.csv.json").write_text(json.dumps(
        {"script": "analysis/calibrate.py", "git_commit": commit, "table_sha256": sha(out),
         "source_csv_sha256": hashes, "windows": WINDOWS, "k": K_VALUES, "lines": LINES,
         "configuration": {"dcache_bytes": 2048, "line_bytes": 16, "memory_latency_cycles": 20, "detector": "NONE"}},
        indent=2) + "\n")
    print(f"calibrate: wrote {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
