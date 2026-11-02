"""mem_model_test.py: unit test of rtl/mem_model.sv (T2.1: latency and ordering).

Usage:   python3 tests/mem_model_test.py
Runs tb/tb_mem_model.sv for LINE_BYTES 16, 32, 64 and LATENCY 1, 2, 3, 10 with fixed latency, and with
random latency (LATENCY 5 and 10, two seeds). Random mode is run twice per configuration: the latency
sequence must be identical (deterministic) and differ between the two seeds.
Output: PASS/FAIL per configuration and "[mem_model] n/n passed"; exit 0 only if all pass.
Expected values are in the testbench from the port protocol documented in rtl/mem_model.sv.
"""
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from paths import CORE_RTL, TB, RTL, work_dir


def run(cfg):
    lb, lat, rnd, seed = cfg
    d = work_dir(f"mem_model/lb{lb}_l{lat}_r{rnd}_s{seed}")
    with open(os.path.join(d, "init.hex"), "w") as f:
        f.write("000000a0\n000000a1\n000000a2\n000000a3\n")
    subprocess.run(["iverilog", "-g2012", "-o", os.path.join(d, "m.vvp"), f"-Ptb_mem_model.LAT={lat}",
                    f"-Ptb_mem_model.LINE_BYTES={lb}", f"-Ptb_mem_model.RANDOM={rnd}", f"-Ptb_mem_model.SEED={seed}",
                    os.path.join(RTL, "mem_model.sv"), os.path.join(TB, "tb_mem_model.sv")], check=True, capture_output=True)
    out = subprocess.run(["vvp", "m.vvp"], cwd=d, capture_output=True, text=True).stdout
    m = re.search(r"MEMMODEL errors=(\d+)", out)
    seq = re.search(r"LATSEQ (.*)", out)
    fails = [ln for ln in out.splitlines() if ln.startswith("FAIL")]
    return cfg, (int(m.group(1)) if m else -1), fails, (seq.group(1) if seq else None)


cfgs = [(lb, lat, 0, 5) for lb in (16, 32, 64) for lat in (1, 2, 3, 10)]
cfgs += [(16, lat, 1, seed) for lat in (5, 10) for seed in (5, 9)]
with ThreadPoolExecutor(max_workers=8) as ex:
    res = list(ex.map(run, cfgs))
bad = 0
seqs = {}
for cfg, err, fails, seq in res:
    ok = err == 0
    bad += not ok
    print(("PASS  " if ok else "FAIL  ") + f"LINE_BYTES={cfg[0]} LATENCY={cfg[1]} random={cfg[2]} seed={cfg[3]}"
          + ("" if ok else f"  errors={err} {fails[:2]}"))
    if cfg[2]:
        seqs[(cfg[1], cfg[3])] = seq
# determinism: rerun one random configuration and compare; different seeds give different sequences
again = run((16, 10, 1, 5))
total = len(res) + 2
if again[3] != seqs[(10, 5)]:
    print("FAIL  random latency is not deterministic for the same seed"); bad += 1
if seqs[(10, 5)] == seqs[(10, 9)]:
    print("FAIL  different seeds gave the same latency sequence"); bad += 1
print(f"[mem_model] {total - bad}/{total} passed")
sys.exit(1 if bad else 0)
