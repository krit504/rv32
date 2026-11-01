"""make_criteria.py: build docs/CRITERIA.md as a verbatim extract of the spec (T0.6).

Inputs: ../docs/writehammer.md (the spec). Output: docs/CRITERIA.md.
Usage: python3 scripts/make_criteria.py   (run once at lock-in; the output is then locked)
Extracts, unchanged: Section 1 (goal, hypotheses, criteria), Section 3 (defaults, including the
calibration and held-out lists), Section 4 (definitions), the T4.7 attack-validation rule, and
every task line that defines a mutant or a mutation check (T1.2, T1.6, T3.5, T5.7, T5.10).
"""
import hashlib
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, "..", "docs", "writehammer.md")
text = open(SPEC).read()


def section(n):
    m = re.search(rf"^## {n}\. .*?(?=^---$)", text, re.S | re.M)
    assert m, f"section {n} not found"
    return m.group(0).rstrip()


def task(tid):
    m = re.search(rf"^- \*\*{re.escape(tid)}\*\*.*$", text, re.M)
    assert m, f"task {tid} not found"
    return m.group(0)


out = ["# CRITERIA (locked)", "",
       f"Verbatim extract of `docs/writehammer.md` (sha256 `{hashlib.sha256(text.encode()).hexdigest()}`), "
       "made by `scripts/make_criteria.py` at T0.6. Locked by `docs/LOCKED.sha256`; any change needs a "
       "`docs/CHANGE_LOG.md` entry (spec 0A.A).", "",
       "---", "", section(1), "", "---", "", section(3), "", "---", "", section(4), "", "---", "",
       "## Attack-validation rule", "", task("T4.7"), "",
       "## Mutant and mutation-check definitions", "",
       task("T1.2"), "", task("T1.6"), "", task("T3.5"), "", task("T5.7"), "", task("T5.10"), ""]
open(os.path.join(ROOT, "docs", "CRITERIA.md"), "w").write("\n".join(out))
print("wrote docs/CRITERIA.md")
