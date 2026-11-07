"""Resume the interrupted clean-clone make all run from the LAT=10 arch pass."""

import datetime as dt
import os
from pathlib import Path
import subprocess
import sys
import threading


ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "work" / "make_all_resume.log"
EXIT = ROOT / "work" / "make_all_resume.exit"
STAGES = [
    (
        "arch CACHES=1 LAT=10",
        ["scripts/run.sh", "--", "python3", "tests/arch_test.py"],
        {"CACHES": "1", "LAT": "10", "ARCH_REPORT": "docs/ARCH_TESTS_RESULTS.md"},
    ),
    (
        "remaining make targets",
        ["make", "random", "bench", "caches", "wear", "attacks", "calibrate",
         "eval", "synth", "plots", "hypotheses", "results", "audit"],
        {},
    ),
]


def stamp():
    return dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def main():
    EXIT.unlink(missing_ok=True)
    env = os.environ.copy()
    env.update({"JOBS": "4", "MPLCONFIGDIR": "/tmp/wh-mpl", "PYTHONUNBUFFERED": "1"})
    with LOG.open("a", buffering=1) as log:
        def emit(message):
            line = f"[{stamp()}] {message}\n"
            log.write(line)
            sys.stdout.write(line)
            sys.stdout.flush()

        emit("START resumed make all")
        for label, command, extra_env in STAGES:
            emit(f"STAGE {label}: {' '.join(command)}")
            stage_env = env | extra_env
            proc = subprocess.Popen(command, cwd=ROOT, env=stage_env,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, bufsize=1)

            def copy_output():
                assert proc.stdout is not None
                for line in proc.stdout:
                    log.write(line)
                    sys.stdout.write(line)
                    sys.stdout.flush()

            reader = threading.Thread(target=copy_output, daemon=True)
            reader.start()
            while True:
                try:
                    code = proc.wait(timeout=30)
                    break
                except subprocess.TimeoutExpired:
                    emit(f"HEARTBEAT {label}: pid={proc.pid} active")
            reader.join()
            emit(f"STAGE EXIT {label}: {code}")
            if code:
                EXIT.write_text(f"{code}\n")
                emit(f"EXIT {code}")
                return code
        EXIT.write_text("0\n")
        emit("EXIT 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
