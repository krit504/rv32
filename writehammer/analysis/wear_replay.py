"""Replay RTL D$ access traces through the independent Python cache model.

Usage: python3 analysis/wear_replay.py RUN_DIR [--cache-bytes N] [--line-bytes N]
Inputs: dc_trace.csv, wear_lines.csv, simulation.log from tb_wear. Checks exact
per-line data-array writes, hits, misses, fills and write-backs against the
existing tests/cache_model.py model, written before this monitor. Exits nonzero
on any discrepancy and writes replay_result.json on success.
"""
import argparse
import csv
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from cache_model import CacheModel  # noqa: E402


def replay(run_dir, cache_bytes=2048, line_bytes=16):
    d = Path(run_dir).resolve()
    model = CacheModel(cache_bytes, line_bytes)
    trace = list(csv.DictReader((d / "dc_trace.csv").open()))
    last_cycle = -1
    for n, row in enumerate(trace):
        cycle = int(row["cycle"])
        kind = row["type"]
        addr = int(row["address"])
        size = int(row["size"])
        bypass = bool(int(row["bypass"]))
        if cycle <= last_cycle or kind not in ("L", "S") or size not in (1, 2, 4):
            raise AssertionError(f"bad trace entry {n}: {row}")
        if kind == "L" and bypass:
            raise AssertionError(f"load bypass at entry {n}")
        last_cycle = cycle
        model.op(kind, addr, size, bypass)
    wear = list(csv.DictReader((d / "wear_lines.csv").open()))
    got_lines = [int(r["count"]) for r in wear]
    if [int(r["line"]) for r in wear] != list(range(model.lines)):
        raise AssertionError("wear lines missing, repeated, or out of order")
    differences = [(i, got, want) for i, (got, want) in enumerate(zip(got_lines, model.writes)) if got != want]
    if differences:
        raise AssertionError(f"per-line array-write mismatch (line, RTL, model): {differences[:10]}")
    log = (d / "simulation.log").read_text()
    m = re.search(r"^DC_CNT (.*)$", log, re.M)
    if not m:
        raise AssertionError("missing RTL counters")
    rtl = {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", m.group(1))}
    mapping = {"access": "access", "hit": "hit", "miss": "miss", "fill": "fill",
               "wb": "wb", "bypass": "bypass", "rab": "refill_after_bypass", "write": "write"}
    for key, model_key in mapping.items():
        if rtl[key] != model.counters[model_key]:
            raise AssertionError(f"{key}: RTL={rtl[key]} model={model.counters[model_key]}")
    result = {"run_dir": str(d), "accesses": len(trace), "array_writes": sum(model.writes),
              "counters": model.counters, "exact_match": True}
    (d / "replay_result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"replay PASS {d}: {len(trace)} accesses, {sum(model.writes)} array writes")
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run_dir")
    ap.add_argument("--cache-bytes", type=int, default=2048)
    ap.add_argument("--line-bytes", type=int, default=16)
    a = ap.parse_args()
    replay(a.run_dir, a.cache_bytes, a.line_bytes)
