"""Generate a Yosys-readable CORE_ONLY=1 copy of the delivered pipeline RTL.

Only the two generate branches disabled by CORE_ONLY=1 are removed. The
unconnected debug-memory output is packed because Yosys's Verilog frontend
cannot parse an unpacked array port. Functional core logic is unchanged.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "rtl/rv32_top_pipelined.sv"
OUT = ROOT / "flow/generated/rv32_top_pipelined.sv"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    src = SOURCE.read_text()
    old = "output logic [31:0] dbg_dmem [0:3]"
    if src.count(old) != 1 or src.count("dbg_dmem[i]") != 4:
        raise ValueError("core observation port changed; review specialization")
    src = src.replace(old, "output logic [127:0] dbg_dmem")
    src = src.replace("dbg_dmem[i]", "dbg_dmem[32 * i +: 32]")
    for label in ("g_core_i", "g_core_d"):
        pattern = rf"(generate\n    if \(CORE_ONLY\) begin : {label}.*?\n    end) else if \(CACHES_ON\).*?\nendgenerate"
        src, count = re.subn(pattern, r"\1\nendgenerate", src, flags=re.S)
        if count != 1:
            raise ValueError(f"core generate branch {label} changed; review specialization")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(src)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    sidecar = {"script": "flow/specialize_core.py", "git_commit": commit,
               "script_sha256": sha(Path(__file__)), "source_sha256": sha(SOURCE),
               "output_sha256": sha(OUT), "core_only": 1}
    Path(str(OUT) + ".json").write_text(json.dumps(sidecar, indent=2) + "\n")
    print("generated Yosys-readable CORE_ONLY=1 source:", OUT)


if __name__ == "__main__":
    main()
