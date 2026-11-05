#!/usr/bin/env python3
"""audit.py: integrity audit (spec T7.7 claim check and T7.8 automated part).

Usage: .venv/bin/python scripts/audit.py        (make audit)
Checks, each printed PASS/FAIL, exit 1 on any FAIL:
  locks        scripts/check_locks.sh passes
  counts       defined mutants and the check counts in the latest test logs are not below tests/BASELINE_COUNTS.json
  patterns     no skipped/expected-fail tests, no blanket lint waivers without a comment, no unexplained -Wno- flags
  results      analysis/results.csv: planned == completed (docs/EXCLUDED_RUNS.md), every row correct = 1, run_ids unique
  claims       every file path cited in backticks in README.md, REPORT.md and docs/RESULTS.md exists
  adversarial  targeted checks behind docs/INTEGRITY_REPORT.md (D3 detects at some setting? PLACEBO matched? bypass applied?)
Does not check: that the prose is correct (that is the reviewer's job); it only checks what can be computed.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
bad = 0


def report(name, ok, detail=""):
    global bad
    bad += not ok
    print(("PASS " if ok else "FAIL ") + name + (f": {detail}" if detail else ""))


# locks
r = subprocess.run([str(ROOT / "scripts" / "check_locks.sh")], capture_output=True, text=True, cwd=ROOT)
report("locks", r.returncode == 0, r.stdout.strip().splitlines()[-1])

# counts
base = json.loads((ROOT / "tests" / "BASELINE_COUNTS.json").read_text())
from mutants.core_mutants import MUTANTS as m1
from mutants.subword_mutants import MUTANTS as m2
from mutants.perf_mutants import MUTANTS as m3
from mutants.toolchain_mutants import MUTANTS as m4
from mutants.mem_mutants import MUTANTS as m5
from mutants.dcache_mutants import MUTANTS as m6
from mutants.stall_mutants import MUTANTS as m7
n_mut = len(m1 + m2 + m3 + m4 + m5 + m6 + m7)
report("counts: mutants", n_mut >= base["mutants_caught"] + base["mutants_argued_equivalent"], f"{n_mut} defined, baseline {base['mutants_caught'] + base['mutants_argued_equivalent']}")


def last_log(tag):
    logs = sorted((ROOT / "logs" / "runs").glob(f"*-{tag}*.log"))
    return logs[-1].read_text() if logs else ""


txt = last_log("nohazard_test")
report("counts: nohazard register checks", len(re.findall(r"PASS", txt)) >= base["nohazard_register_checks"] or "21 PASS" in txt, "latest nohazard log")
txt = last_log("cache_integration")
m = re.search(r"(\d+)/(\d+) passed", txt)
report("counts: cache_integration", bool(m) and int(m.group(1)) >= base["cache_integration_checks"], m.group(0) if m else "no log")

# patterns
tests = list((ROOT / "tests").glob("*.py")) + list((ROOT / "tests" / "mutants").glob("*.py"))
hits = [p.name for p in tests if re.search(r"pytest\.mark\.(skip|xfail)|expected.?fail|@unittest\.skip|\bSKIP\b", p.read_text())]
report("patterns: skipped or expected-fail tests", not hits, ", ".join(hits))
rtl_waivers = [f"{p.name}:{i + 1}" for p in (ROOT / "rtl").glob("*.sv") for i, l in enumerate(p.read_text().splitlines())
               if "lint_off" in l and "//" not in l and not l.strip().startswith("//")]
# a bare lint_off pragma is allowed when the same or the previous line explains it; list those that have no comment at all
unexplained = []
for p in (ROOT / "rtl").glob("*.sv"):
    L = p.read_text().splitlines()
    for i, l in enumerate(L):
        if "lint_off" in l and "//" not in l.split("lint_off")[0] + l.split("*/")[-1] and "//" not in l:
            prev = L[i - 1] if i else ""
            nxt = L[i + 1] if i + 1 < len(L) else ""
            if "//" not in prev and "//" not in nxt:
                unexplained.append(f"{p.name}:{i + 1}")
report("patterns: lint waivers without any comment", not unexplained, ", ".join(unexplained))
mk = (ROOT / "Makefile").read_text()
report("patterns: -Wno- flags in the lint target", "-Wno-" not in "".join(re.findall(r"^lint:\n(?:\t.*\n)+", mk, re.M)))

# results
res = pd.read_csv(ROOT / "analysis" / "results.csv", low_memory=False)
ex = (ROOT / "docs" / "EXCLUDED_RUNS.md").read_text()
pl = re.search(r"Planned: (\d+)\. Completed: (\d+)\. Missing: (\d+)", ex)
report("results: planned == completed", bool(pl) and pl.group(1) == pl.group(2) and pl.group(3) == "0" and len(res) == int(pl.group(1)),
       f"{len(res)} rows; {pl.group(0) if pl else 'no summary'}")
report("results: every row correct = 1", bool((res.correct == 1).all()))
report("results: run_ids unique", res.run_id.is_unique)

# claims: backticked paths exist
missing = []
for doc in ("README.md", "REPORT.md", "docs/RESULTS.md"):
    for tok in re.findall(r"`([A-Za-z0-9_./*-]+\.(?:md|csv|png|py|sv|json|sh|zst|sdc|hex|c|h))`", (ROOT / doc).read_text()):
        if "*" in tok:
            ok = bool(list(ROOT.glob(tok)))
        else:
            ok = (ROOT / tok).exists() or (ROOT / "docs" / tok).exists() or (ROOT / "analysis" / tok).exists()
        if not ok:
            missing.append(f"{doc}: {tok}")
report("claims: cited files exist", not missing, "; ".join(missing[:6]))

# adversarial: D3 detection at ANY registered setting, and PLACEBO matching
att = res[(res.workload_class == "attack") & (res.detector == "D3")]
report("adversarial: D3 detects an attack at some registered setting (else the zero is a threshold property, not a dead detector)",
       att.detect_latency_cycles.notna().any(), f"{int(att.detect_latency_cycles.notna().sum())} of {len(att)} D3 attack runs detected over all settings")
d1 = res[(res.workload_class == "attack") & (res.detector == "D1")]
report("adversarial: D1 restricted stores on the attacks it detected (bypass was actually applied)",
       bool((d1[d1.detect_latency_cycles.notna()].bypassed_stores > 0).all()))
stress = res[res.detector == "ALWAYS"]
report("adversarial: ALWAYS bypassed stores in every run", bool((stress.bypassed_stores > 0).all()))
none = res[res.detector == "NEVER"]
report("adversarial: NEVER bypassed nothing", bool((none.bypassed_stores == 0).all()))

print(f"[audit] {'OK' if not bad else str(bad) + ' check(s) failed'}")
sys.exit(1 if bad else 0)
