"""guard_mutants.py: mutation tests of rtl/write_guard.sv (spec T5.7).

Usage:   python3 tests/guard_mutants.py [--bypass-only]
Each mutant patches a copy of rtl/ and runs tests/write_guard_test.py against it; a mutant is CAUGHT if that
test fails. Exit 0 only if every patch applies exactly once and every mutant is caught. (Separate from
tests/run_mutants.py, whose suite is locked: this file only adds mutants, spec 0A.A.)
"""
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from paths import ROOT, RTL, TB, work_dir

GUARD = "write_guard.sv"
# invariant-breaking mutants of the bypass path (spec 0A.D, T5.10): must be caught by the T5.8 check
# (tests/guard_integration.py --mini), not by the guard unit test.
BYPASS_MUTANTS = [
    ("X1_bypass_drops_the_store", "dcache.sv", "mem_valid = 1'b1; mem_we = 1'b1;\n                mem_wdata[32 * wsel +: 32] = wdata;",
     "mem_valid = 1'b1; mem_we = 1'b0;\n                mem_wdata[32 * wsel +: 32] = wdata;"),
    ("X2_bypass_writes_wrong_data", "dcache.sv", "mem_wdata[32 * wsel +: 32] = wdata;", "mem_wdata[32 * wsel +: 32] = ~wdata;"),
]
MUTANTS = [
    ("G1_cnt_no_midwindow_compare", "if (!freeze && 32'(cnt_n) > 32'(THRESHOLD)) hot[i] <= 1'b1;", "if (1'b0) hot[i] <= 1'b1;"),
    ("G2_cnt_no_window_set", "if (32'(cnt_n) > 32'(THRESHOLD))      hot[i] <= 1'b1;\n                    else if", "if (1'b0)      hot[i] <= 1'b1;\n                    else if"),
    ("G3_cnt_threshold_ge", "if (!freeze && 32'(cnt_n) > 32'(THRESHOLD)) hot[i] <= 1'b1;", "if (!freeze && 32'(cnt_n) >= 32'(THRESHOLD)) hot[i] <= 1'b1;"),
    ("G4_cnt_window_reset_broken", "                    cnt[i] <= '0;\n                    if (32'(cnt_n) > 32'(THRESHOLD))", "                    cnt[i] <= cnt_n;\n                    if (32'(cnt_n) > 32'(THRESHOLD))"),
    ("G5_d3_window_reset_broken", "                cnt <= '0;\n                if (32'(cnt_n) > 32'(THRESHOLD))", "                cnt <= cnt_n;\n                if (32'(cnt_n) > 32'(THRESHOLD))"),
    ("G6_stuck_restricted", "assign restricted   = any_hot;", "assign restricted   = 1'b1;"),
    ("G7_stuck_released_bypass", "assign bypass_store = store_valid && hot_store;", "assign bypass_store = 1'b0;"),
    ("G8_inverted_bypass", "assign bypass_store = store_valid && hot_store;", "assign bypass_store = store_valid && !hot_store;"),
    ("G9_wrong_hash_index_source", "bucket({{(16-IDXW){1'b0}}, store_line[IDXW-1:0]})", "bucket({{(16-IDXW){1'b0}}, line_idx[IDXW-1:0]})"),
    ("G10_no_hysteresis", "else if (32'(cnt_n) < 32'(HALF))      hot[i] <= 1'b0;", "else if (32'(cnt_n) < 32'(THRESHOLD))      hot[i] <= 1'b0;"),
    ("G11_d3_static_releases", "else if (MODE == 1 && 32'(cnt_n) < 32'(HALF))", "else if (32'(cnt_n) < 32'(HALF))"),
    ("G12_no_saturation", "(inc && cnt[i] != SATMAX) ?", "(inc) ?"),
    ("G13_decision_changes_while_busy", "if (!freeze && 32'(cnt_n) > 32'(THRESHOLD)) hot[i] <= 1'b1;", "if (32'(cnt_n) > 32'(THRESHOLD)) hot[i] <= 1'b1;"),
    ("G14_placebo_rate_ignored", "(32'(x3[15:0]) < 32'(PLACEBO_RATE))", "(32'(x3[15:0]) < 32'd32768)"),
    ("G15_hash_not_odd_multiply", "p = 8'(16'(f) * 16'd167);", "p = 8'(16'(f) * 16'd166);"),
    ("G16_d3_counts_array_writes", "wire [W-1:0]  cnt_n = (store_done && cnt != SATMAX)", "wire [W-1:0]  cnt_n = (array_write_valid && cnt != SATMAX)"),
    ("G17_window_ignores_freeze", "assign win_proc = (wtimer >= 32'(WINDOW_CYCLES - 1)) && !freeze;", "assign win_proc = (wtimer >= 32'(WINDOW_CYCLES - 1));"),
]


def run(m):
    if len(m) == 4:
        name, fname, old, new = m
        test = ["tests/guard_integration.py", "--mini", "--csv", "/dev/null"]
    else:
        name, old, new = m
        fname, test = GUARD, ["tests/write_guard_test.py"]
    d = work_dir(f"guard_mutants/{name}")
    shutil.rmtree(os.path.join(d, "rtl"), ignore_errors=True)
    shutil.copytree(RTL, os.path.join(d, "rtl"))
    p = os.path.join(d, "rtl", fname)
    s = open(p).read()
    if s.count(old) != 1:
        return name, "PATCH-ERROR", f"patch text found {s.count(old)} times"
    open(p, "w").write(s.replace(old, new))
    env = dict(os.environ, RTL_DIR=os.path.join(d, "rtl"), WORK_ROOT=os.path.join(d, "work"))
    r = subprocess.run([sys.executable, os.path.join(ROOT, test[0]), *test[1:]], capture_output=True, text=True, env=env, cwd=ROOT)
    fails = [ln for ln in r.stdout.splitlines() if ln.startswith("FAIL")]
    if r.returncode == 0:
        return name, "SURVIVED", ""
    return name, "CAUGHT", (fails[0][:110] if fails else r.stderr[-110:])


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=3) as ex:
        res = list(ex.map(run, BYPASS_MUTANTS if "--bypass-only" in sys.argv else MUTANTS + BYPASS_MUTANTS))
    bad = 0
    for name, st, why in res:
        print(f"{st:11s} {name}  {why}")
        bad += st != "CAUGHT"
    print(f"[guard_mutants] {len(res) - bad}/{len(res)} caught")
    sys.exit(1 if bad else 0)
