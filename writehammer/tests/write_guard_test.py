"""write_guard_test.py: unit tests of rtl/write_guard.sv on synthetic store streams (spec T5.7).

Usage:   python3 tests/write_guard_test.py
Two layers:
  directed  behaviours asserted directly on the RTL output (detects above threshold, not at/below it,
            hysteresis release, STATIC latch vs ADAPTIVE, counter saturation, NEVER == NONE, ALWAYS,
            PLACEBO rate), so a wrong model cannot hide a wrong RTL;
  random    per-cycle comparison of the RTL against the independent model tests/guard_model.py over
            random streams (hot lines, bursts, busy cycles) for every detector, window, threshold.
Output: PASS/FAIL per case and "[write_guard] n/n passed"; exit 0 only if all pass.
"""
import os
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from paths import RTL, TB, work_dir
from vl_tb import run_tb
from guard_model import Guard

SRCS = [os.path.join(RTL, "write_guard.sv"), os.path.join(TB, "tb_write_guard.sv")]


def word(sv=0, busy=0, awv=0, line=0, sline=0):
    return sv | (busy << 1) | (awv << 2) | (line << 8) | (sline << 16)


def run_rtl(name, stim, **params):
    d = work_dir(f"wg/{name}")
    with open(os.path.join(d, "stim.hex"), "w") as f:
        f.write("\n".join(f"{w:08x}" for w in stim) + "\n")
    p = dict(params)
    p["NCYC"] = len(stim)
    out = run_tb("tb_write_guard", SRCS, p, d)
    rows = []
    for ln in out.splitlines():
        if ln.startswith("C "):
            rows.append(tuple(int(x) for x in ln.split()[2:]))
    if len(rows) != len(stim) or "DONE" not in out:
        raise RuntimeError(f"{name}: testbench did not complete ({len(rows)}/{len(stim)} rows)")
    return rows


MODEL_KEYS = dict(DETECTOR="det", MODE="mode", WINDOW_CYCLES="window", THRESHOLD="thr", M="m", W="w",
                  LINES="lines", PLACEBO_RATE="rate", PLACEBO_SEED="seed")


def run_model(stim, **params):
    g = Guard(**{MODEL_KEYS[k]: v for k, v in params.items()})
    rows = []
    for w in stim:
        rows.append(g.step(w & 1, (w >> 1) & 1, (w >> 2) & 1, (w >> 8) & 0xFF, (w >> 16) & 0xFF))
    return rows


def writes(line, n, gap=1, store_line=None):
    """n array-write cycles to `line`, one every `gap` cycles."""
    s = []
    for _ in range(n):
        s.append(word(awv=1, line=line))
        s += [word()] * (gap - 1)
    return s


def pad(stim, n):
    return stim + [word()] * (n - len(stim)) if len(stim) < n else stim


# ---- directed cases: (name, params, stimulus, check(rows) -> error string or None) ----
def d1_params(**kw):
    p = dict(DETECTOR=2, WINDOW_CYCLES=100, THRESHOLD=10, LINES=128)
    p.update(kw)
    return p


def probe(stim, line, extra=0):
    """append a probe store (sv, not busy) targeting `line` at the end and return the stimulus."""
    return stim + [word(sv=1, sline=line)] * 1


def directed():
    cases = []

    # 1. detects above threshold: 11 writes (> 10) to line 5 in one window; probes 5 and 6 afterwards
    s = pad(writes(5, 11), 20) + [word(sv=1, sline=5), word(sv=1, sline=6)]
    cases.append(("d1_detects_above", d1_params(), s,
                  lambda r: None if (r[-2][0] == 1 and r[-1][0] == 0 and r[-1][1] == 1) else f"probe5/6 = {r[-2][0]}/{r[-1][0]}, restricted {r[-1][1]}"))
    # 2. no detection at the threshold: exactly 10 writes
    s = pad(writes(5, 10), 20) + [word(sv=1, sline=5)]
    cases.append(("d1_no_detect_at_threshold", d1_params(), s,
                  lambda r: None if (r[-1][0] == 0 and r[-1][1] == 0) else f"restricted at exactly THRESHOLD: {r[-1]}"))
    # 3. hysteresis: hot in window 1; window 2 has 6 writes (>= 5 = THRESHOLD/2): stays; window 3 has 2 (< 5): released
    s = pad(writes(5, 11), 100) + pad(writes(5, 6), 100) + [word(sv=1, sline=5)]          # probe at start of window 3
    s2 = s + pad([], 99) + pad(writes(5, 2), 100) + [word(sv=1, sline=5)]                    # probe in window 4
    s2 = s2[:len(s2)]
    probe_at = len(s) - 1

    def chk_h(r, probe_at=probe_at):
        # r[len(s)-1] is the probe after window 2 (still hot); the last row is after window 3 (released)
        if r[probe_at][0] != 1:
            return "released too early (count 6 >= THRESHOLD/2)"
        if r[-1][0] != 0:
            return "not released after a window with count < THRESHOLD/2"
        return None
    cases.append(("d1_hysteresis", d1_params(), s2, chk_h))
    # 4. D3 STATIC latches, ADAPTIVE releases: 11 stores in window 1, none afterwards
    stores = [word(sv=1, sline=0)] * 11
    s = pad(stores, 100) + [word()] * 220 + [word(sv=1, sline=0)]
    cases.append(("d3_static_latches", dict(DETECTOR=4, MODE=0, WINDOW_CYCLES=100, THRESHOLD=10), s,
                  lambda r: None if r[-1][0] == 1 else "STATIC did not hold the restriction"))
    cases.append(("d3_adaptive_releases", dict(DETECTOR=4, MODE=1, WINDOW_CYCLES=100, THRESHOLD=10), s,
                  lambda r: None if (r[-1][0] == 0 and any(x[1] for x in r)) else "ADAPTIVE did not release (or never restricted)"))
    # 5. saturation: W=4 saturates at 15; THRESHOLD=15 is never exceeded
    s = pad(writes(5, 40), 60) + [word(sv=1, sline=5)]
    cases.append(("d1_saturation_no_wrap", dict(DETECTOR=2, WINDOW_CYCLES=1000, THRESHOLD=15, W=4), s,
                  lambda r: None if r[-1][1] == 0 else "saturated counter exceeded THRESHOLD (or wrapped)"))
    cases.append(("d1_saturation_detects", dict(DETECTOR=2, WINDOW_CYCLES=1000, THRESHOLD=14, W=4), s,
                  lambda r: None if r[-1][0] == 1 else "saturated counter at 15 did not exceed THRESHOLD 14"))
    # 6. D2 aliasing: lines that hash to the same bucket share a counter
    from guard_model import bucket
    same = [l for l in range(128) if bucket(l, 8) == bucket(5, 8) and l != 5][:1]
    other = [l for l in range(128) if bucket(l, 8) != bucket(5, 8)][:1]
    s = pad(writes(5, 6) + writes(same[0], 6), 30) + [word(sv=1, sline=same[0]), word(sv=1, sline=other[0])]
    cases.append(("d2_aliasing", dict(DETECTOR=3, WINDOW_CYCLES=1000, THRESHOLD=10, M=8), s,
                  lambda r: None if (r[-2][0] == 1 and r[-1][0] == 0) else f"aliased bucket/other = {r[-2][0]}/{r[-1][0]}"))
    # 7. controls
    s = [word(sv=1, sline=i % 7) for i in range(50)] + [word(awv=1, line=3)] * 40
    cases.append(("always_restricts_every_store", dict(DETECTOR=1), s,
                  lambda r: None if all(r[i][0] == 1 for i in range(50)) else "ALWAYS let a store through"))
    cases.append(("never_equals_none", dict(DETECTOR=5), s,
                  lambda r: None if all(x[:2] == (0, 0) for x in r) else "NEVER restricted"))
    # 8. PLACEBO: rate 1/4 over many stores lands near 25 %, rate 0 gives none, rate 65536 gives all
    s = [word(sv=1, sline=1)] * 4000
    def chk_pl(r):
        n = r[-1][5]; t = r[-1][4]
        return None if t > 3900 and 0.20 < n / t < 0.30 else f"placebo fraction {n}/{t}"
    cases.append(("placebo_rate", dict(DETECTOR=6, PLACEBO_RATE=16384, PLACEBO_SEED=7), s, chk_pl))
    cases.append(("placebo_rate_zero", dict(DETECTOR=6, PLACEBO_RATE=0, PLACEBO_SEED=7), s,
                  lambda r: None if r[-1][5] == 0 else "placebo rate 0 restricted stores"))
    cases.append(("placebo_rate_full", dict(DETECTOR=6, PLACEBO_RATE=65536, PLACEBO_SEED=7), s,
                  lambda r: None if r[-1][5] == r[-1][4] - 1 or r[-1][5] == r[-1][4] else "placebo rate 65536 missed stores"))
    # 9. busy freeze: the decision never changes while a store is mid-request
    st = [word(sv=1, busy=1, awv=1, line=5, sline=5)] * 30 + [word(sv=1, busy=0, sline=5)]
    def chk_stable(r):
        vals = {x[0] for x in r[:-1]}
        return None if len(vals) == 1 else "bypass changed while the store was busy"
    cases.append(("d1_decision_stable_while_busy", d1_params(), st, chk_stable))
    return cases


def run_directed(case):
    name, params, stim, check = case
    try:
        rows = run_rtl(name, stim, **params)
        err = check(rows)
        # the independent model must agree too
        if err is None and rows != run_model(stim, **params):
            err = "RTL differs from the model"
    except Exception as e:  # noqa: BLE001
        err = repr(e)
    return name, err


def random_stream(rng, n, mode):
    s = []
    hot = rng.randrange(128)
    for i in range(n):
        sv = rng.random() < 0.4
        busy = sv and rng.random() < 0.3
        if mode == "hot":
            line = hot if rng.random() < 0.7 else rng.randrange(128)
        elif mode == "burst":
            line = hot if (i // 150) % 2 == 0 else rng.randrange(128)
        else:
            line = rng.randrange(128)
        awv = rng.random() < (0.9 if mode != "uniform" else 0.5)
        s.append(word(sv=int(sv), busy=int(busy), awv=int(awv), line=line, sline=line if rng.random() < 0.7 else rng.randrange(128)))
    return s


def random_cases():
    cfgs = []
    for det in (2, 3, 4, 6, 1, 5, 0):
        for window, thr in ((50, 6), (120, 20), (200, 4)):
            for mode in (0, 1) if det == 4 else (0,):
                kw = dict(DETECTOR=det, MODE=mode, WINDOW_CYCLES=window, THRESHOLD=thr, M=8 if det == 3 else 16,
                          W=6 if det in (2, 3) else 16, PLACEBO_RATE=20000, PLACEBO_SEED=3 + window)
                cfgs.append(kw)
    return cfgs


def run_random(arg):
    i, kw, smode = arg
    name = f"rand_{i}_{smode}"
    try:
        stim = random_stream(random.Random(1000 + i), 1500, smode)
        rtl = run_rtl(name, stim, **kw)
        mod = run_model(stim, **kw)
        for c, (a, b) in enumerate(zip(rtl, mod)):
            if a != b:
                return name, f"cycle {c}: RTL {a} model {b} cfg {kw}"
        if kw["DETECTOR"] in (2, 3, 4) and not any(x[1] for x in rtl):
            return name, "stream never restricted: the random case would be vacuous"
        return name, None
    except Exception as e:  # noqa: BLE001
        return name, repr(e)


if __name__ == "__main__":
    jobs = [("d", c) for c in directed()]
    rjobs = [(i, kw, sm) for i, kw in enumerate(random_cases()) for sm in ("hot", "burst")]
    results = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        results += list(ex.map(run_directed, [c for _, c in jobs]))
        results += list(ex.map(run_random, rjobs))
    bad = 0
    for name, err in results:
        print(("PASS " if err is None else "FAIL ") + name + ("" if err is None else f": {err}"))
        bad += err is not None
    print(f"[write_guard] {len(results) - bad}/{len(results)} passed")
    sys.exit(1 if bad else 0)
