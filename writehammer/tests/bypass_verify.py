"""bypass_verify.py: restricted stores write no data-array word and their data reaches memory (spec T5.10, 0A.D).

Usage:   python3 tests/bypass_verify.py
Runs a store-heavy benign program (storeloop) and an attack program with the cached core under
  NONE      control: store hits do write the array (AW_STORE > 0), so the check below can fail
  ALWAYS    every store is restricted: AW_STORE must be 0 and every logged store must carry bypass=1
  D1 stress a detector (window 500, threshold 1) that restricts a fraction of the stores: the golden cache replay (independent Python model,
            tests/cache_model.py, which treats a bypassed store as no array write) must match the RTL's
            per-line array-write counts exactly, so a restricted store that wrote the array is caught
and checks that memory received the correct data: the final register/memory signature equals the
caches-off signature (the caches-off core has no cache and no guard: the golden memory), via
tests/guard_integration.py's runs. Output: PASS/FAIL lines, "[bypass_verify] n/n"; exit 0 only if all pass.
"""
import csv
import os
import re
import sys
from pathlib import Path
from paths import ROOT, CORE_RTL, TB, work_dir
from vl_tb import run_tb

sys.path.insert(0, os.path.join(ROOT, "analysis"))
from wear_replay import replay  # noqa: E402
from baseline import workloads  # noqa: E402

SRCS = CORE_RTL + [os.path.join(TB, n) for n in ("sys_monitor.sv", "wear_monitor.sv", "tb_wear.sv")]


def run(image, name, extra):
    d = Path(work_dir(f"bypass_verify/{name}"))
    (d / "program.hex").write_text(open(image).read())
    out = run_tb("tb_wear", SRCS, {"MAXCYC": 30_000_000, "MEMW": 65536, "LAT": 20, "WINDOW_CYCLES": 10000, **extra}, str(d))
    (d / "simulation.log").write_text(out)
    if "TIMEOUT" in out or not re.search(r"^HALT 0$", out, re.M):
        raise RuntimeError(f"{name}: run failed\n{out[-400:]}")
    return d, int(re.search(r"^AW_STORE (\d+)", out, re.M).group(1))


def main():
    imgs = {n.split()[0]: h for n, _c, h, _k, _r in workloads()}
    imgs.pop("Dhrystone", None)
    cases = [("storeloop", imgs["storeloop"]), ("memset_big", imgs["memset_big"])]
    atk = Path(ROOT) / "work" / "attack_run" / "rla_direct_s1" / "build" / "program.hex"
    if atk.exists():
        cases.append(("rla_direct_s1", str(atk)))
    res = []

    def check(label, ok, msg=""):
        res.append(ok)
        print(("PASS " if ok else "FAIL ") + label + ("" if ok else f": {msg}"))

    for name, image in cases:
        dn, awn = run(image, f"{name}_none", {"DETECTOR": 0})
        check(f"{name}: NONE control makes store-hit array writes", awn > 0, f"AW_STORE={awn}")
        da, awa = run(image, f"{name}_always", {"DETECTOR": 1})
        check(f"{name}: ALWAYS makes zero store-hit array writes", awa == 0, f"AW_STORE={awa}")
        rows = list(csv.DictReader((da / "dc_trace.csv").open()))
        stores = [r for r in rows if r["type"] == "S"]
        check(f"{name}: ALWAYS logs every store as bypassed", bool(stores) and all(r["bypass"] == "1" for r in stores),
              f"{sum(r['bypass'] != '1' for r in stores)} of {len(stores)} not bypassed")
        try:
            replay(da)
            ok, msg = True, ""
        except Exception as e:  # noqa: BLE001
            ok, msg = False, str(e)[:200]
        check(f"{name}: ALWAYS replay matches the independent cache model", ok, msg)
        dd, _ = run(image, f"{name}_d1", {"DETECTOR": 2, "WG_WINDOW": 500, "WG_THRESHOLD": 1})
        drows = [r for r in csv.DictReader((dd / "dc_trace.csv").open()) if r["type"] == "S"]
        nb = sum(r["bypass"] == "1" for r in drows)
        check(f"{name}: D1 stress (threshold 1) restricts some stores", nb > 0, f"{nb}/{len(drows)}")
        try:
            replay(dd)
            ok, msg = True, ""
        except Exception as e:  # noqa: BLE001
            ok, msg = False, str(e)[:200]
        check(f"{name}: D1 replay matches the independent cache model", ok, msg)
    print(f"[bypass_verify] {sum(res)}/{len(res)} passed")
    sys.exit(0 if all(res) else 1)


main()
