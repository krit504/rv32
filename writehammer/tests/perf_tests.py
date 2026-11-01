"""perf_tests.py: known-answer tests for the MMIO monitor and performance counters (T1.3).

Inputs: none. Output: PASS/FAIL per test and "[perf] n/n passed"; exit 0 only if all pass.
Expected values are hand-computed from the pipeline structure, never taken from RTL output.
For a window of N retired instructions with s load-use stalls and f taken redirects the core
spends exactly N + s + 2f cycles, provided no hazard fires in or before START's Memory cycle
(boundary rule, tb/sys_monitor.sv), so every window program has a NOP right after START.
  window_straight    START, 3 addi                      N=4 s=0 f=0 -> cycles 4
  window_hazards     START, nop, lw, add (load-use), beq taken over 2 instructions, addi
                                                        N=6 s=1 f=1 -> cycles 9, flush_cycles 2
  window_two_loaduse START, nop, lw, add, lw, add       N=6 s=2     -> cycles 8
  window_back_to_back_redirects  START, nop, beq (to the next beq), beq (over one addi), addi
                                                        N=5 f=2     -> cycles 9, flush_cycles 4
Also: HALT exit code, PHASE marker, PUTCHAR text, whole-run counting without START/STOP, a hung
program reports TIMEOUT, and the invariants that hold with caches on at every latency: instret,
load-use and flush counts equal the caches-off values while imiss_cycles is positive.
Does not check: exact cache-on cycle counts.
"""
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from asm import *   # noqa: F401,F403
from prog_runner import run_program

MMIO = 0xF0000000
BASE = [lui(1, 0xF0000), addi(2, 0, 1)]              # x1 = MMIO base, x2 = 1
START = sw(2, 4, 1)
STOP = sw(2, 8, 1)
HALT0 = [addi(6, 0, 0), sw(6, 0, 1)]                 # halt, exit code 0

PROGS = {
    "window_straight": BASE + [START, addi(3, 0, 1), addi(4, 0, 2), addi(5, 0, 3), STOP] + HALT0,
    "window_hazards": BASE + [START, NOP, lw(3, 0, 0), add(4, 3, 3), beq(0, 0, 12), addi(5, 0, 1), addi(6, 0, 1),
                              addi(7, 0, 7), STOP] + HALT0,
    "window_two_loaduse": BASE + [START, NOP, lw(3, 0, 0), add(4, 3, 3), lw(5, 0, 0), add(6, 5, 5), STOP] + HALT0,
    "window_back_to_back_redirects": BASE + [START, NOP, beq(0, 0, 8), addi(9, 0, 1), beq(0, 0, 8), addi(9, 0, 1),
                                             addi(8, 0, 8), STOP] + HALT0,
}
# name -> (cycles, instret, stall_loaduse, flush_cycles) with caches off, derived by hand above
EXPECT = {
    "window_straight": (4, 4, 0, 0),
    "window_hazards": (9, 6, 1, 2),
    "window_two_loaduse": (8, 6, 2, 0),
    "window_back_to_back_redirects": (9, 5, 0, 4),
}


def check_perf(job):
    name, caches, lat = job
    r = run_program(PROGS[name], caches=caches, lat=lat, name=name)
    e = []
    if r["timeout"] or r["halt"] != 0: e.append(f"halt={r['halt']} timeout={r['timeout']}")
    p = r["perf"]
    if not p: return [f"FAIL {name} c{caches} l{lat}: no PERF line"]
    cyc, ret, lu, fl = EXPECT[name]
    if caches == 0:
        got = (p["cycles"], p["instret"], p["stall_loaduse"], p["flush_cycles"])
        if got != (cyc, ret, lu, fl): e.append(f"(cycles,instret,loaduse,flush)={got} expected {(cyc, ret, lu, fl)}")
        if p["imiss_cycles"] or p["dmiss_cycles"]: e.append("miss cycles nonzero with caches off")
    else:
        got = (p["instret"], p["stall_loaduse"], p["flush_cycles"])
        if got != (ret, lu, fl): e.append(f"(instret,loaduse,flush)={got} expected {(ret, lu, fl)}")
        if p["imiss_cycles"] == 0: e.append("imiss_cycles is 0 with caches on")
    return [f"FAIL {name} c{caches} l{lat}: " + "; ".join(e)] if e else []


def check_misc(_):
    e = []
    # exit code, PHASE, PUTCHAR, whole-run counting (no START/STOP)
    prog = [lui(1, 0xF0000), addi(2, 0, 7), sw(2, 0x0C, 1),                 # PHASE 7
            addi(3, 0, ord("O")), sw(3, 0x10, 1), addi(3, 0, ord("K")), sw(3, 0x10, 1),   # PUTCHAR "OK"
            addi(4, 0, 42), sw(4, 0, 1)]                                     # HALT 42
    r = run_program(prog, name="misc")
    if r["halt"] != 42: e.append(f"exit code {r['halt']} expected 42")
    if [v for v, _ in r["phases"]] != [7]: e.append(f"phases {r['phases']} expected [7]")
    if "OK" not in r["text"]: e.append(f"putchar text {r['text']!r} expected to contain 'OK'")
    if not r["perf"] or r["perf"]["instret"] != 8: e.append(f"whole-run instret {r['perf']} expected 8 (every instruction before the HALT store)")
    # a program that never halts must time out, not pass
    r = run_program([jal(0, 0)], name="hang", maxcyc=300)
    if not r["timeout"] or r["halt"] is not None: e.append("hung program did not report TIMEOUT")
    return [f"FAIL misc: " + "; ".join(e)] if e else []


jobs = [(n, c, l) for n in PROGS for c, l in ((0, 2), (1, 1), (1, 2), (1, 3), (1, 10))]
with ThreadPoolExecutor(max_workers=int(os.environ.get("JOBS", "8"))) as ex:
    fails = [ln for res in ex.map(check_perf, jobs) for ln in res] + check_misc(None)
total = len(jobs) + 1
for ln in fails: print(ln)
print(f"[perf] {total - len(fails)}/{total} passed")
sys.exit(1 if fails else 0)
