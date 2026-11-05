"""Archive the complete author-authorized T6.5 raw run with provenance."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FLOW = Path(__file__).resolve().parent
RAW = FLOW / "raw"
OUT = FLOW / "raw.tar.zst"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    results = sorted(RAW.glob("*/repeat_*/result.json"))
    if len(results) != 48:
        raise ValueError(f"expected 48 complete physical repeats, found {len(results)}")
    subprocess.run(["tar", "--sort=name", "--mtime=@0", "--owner=0", "--group=0",
                    "--numeric-owner", "--zstd", "-cf", str(OUT), "-C", str(FLOW), "raw"],
                   check=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    files = [p for p in RAW.rglob("*") if p.is_file()]
    sidecar = {"script": "flow/archive_raw.py", "git_commit": commit,
               "script_sha256": sha(Path(__file__)), "archive_sha256": sha(OUT),
               "file_count": len(files), "result_count": len(results),
               "result_sha256": {str(p.relative_to(ROOT)): sha(p) for p in results}}
    Path(str(OUT) + ".json").write_text(json.dumps(sidecar, indent=2) + "\n")
    print(f"archived {len(files)} raw files and {len(results)} result records: {OUT}")


if __name__ == "__main__":
    main()
