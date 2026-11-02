"""Attack run registry loaded from sw/attacks/manifest.json.

The manifest is intentionally absent until the author defines what the L and T
attacks do and what Rn randomizes. This registry validates coverage and numeric
parameters without assigning those meanings. RLA/RTA/RnLA/RnTA are prior work
of the author's group (TENDRA and the Write Hammer draft), not new taxonomy.

Usage: from attacks import load_cases; cases = load_cases()
Manifest schema: {"variants": [{"kind":"RLA", "form":"direct",
"source":"rla.c", "locations":N, "dwell_min":N, "dwell_max":N,
"run_cycles":2000000}, ...]}; one entry per kind/form. Randomized kinds
expand into seeds 1..5; fixed-location kinds use seed 1.
"""
from dataclasses import dataclass
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "sw" / "attacks" / "manifest.json"
KINDS = ("RLA", "RTA", "RnLA", "RnTA")
FORMS = ("direct", "paper")


@dataclass(frozen=True)
class AttackCase:
    kind: str
    form: str
    source: Path
    locations: int
    dwell_min: int
    dwell_max: int
    run_cycles: int
    seed: int

    @property
    def id(self):
        return f"{self.kind.lower()}_{self.form}_s{self.seed}"


def load_cases(manifest=DEFAULT_MANIFEST):
    manifest = Path(manifest)
    if not manifest.is_file():
        raise FileNotFoundError(
            f"{manifest} is absent: the author must first define L, T and Rn attack behavior"
        )
    data = json.loads(manifest.read_text())
    variants = data.get("variants")
    if not isinstance(variants, list):
        raise ValueError("attack manifest must contain a variants list")
    seen = set()
    cases = []
    for v in variants:
        kind, form = v["kind"], v["form"]
        if kind not in KINDS or form not in FORMS or (kind, form) in seen:
            raise ValueError(f"invalid or duplicate attack variant: {kind}/{form}")
        seen.add((kind, form))
        source_name = v["source"]
        if Path(source_name).name != source_name or not source_name.endswith(".c"):
            raise ValueError(f"source must be a .c file under sw/attacks/: {source_name}")
        source = ROOT / "sw" / "attacks" / source_name
        if not source.is_file():
            raise FileNotFoundError(source)
        values = tuple(v[k] for k in ("locations", "dwell_min", "dwell_max", "run_cycles"))
        if any(type(x) is not int or x <= 0 for x in values):
            raise ValueError(f"positive integer attack parameters required: {kind}/{form}")
        locations, dwell_min, dwell_max, run_cycles = values
        if dwell_min > dwell_max or run_cycles != 2_000_000:
            raise ValueError(f"invalid dwell range or run length: {kind}/{form}")
        for seed in (range(1, 6) if kind.startswith("Rn") else (1,)):
            cases.append(AttackCase(kind, form, source, locations, dwell_min,
                                    dwell_max, run_cycles, seed))
    expected = {(kind, form) for kind in KINDS for form in FORMS}
    if seen != expected:
        raise ValueError(f"attack manifest coverage missing: {sorted(expected - seen)}")
    return tuple(cases)
