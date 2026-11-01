#!/usr/bin/env bash
# run.sh: run one result-producing command and append a provenance record (spec rule 0B.1).
#
# Usage:   scripts/run.sh [--out FILE]... [--seed N] [--tag NAME] -- COMMAND [ARGS...]
# Inputs:  --out   an output file to hash after the run (repeatable; missing files are noted)
#          --seed  the seed the command uses (recorded only; pass it to the command yourself)
#          --tag   short label added to the run id (default: the command's basename)
# Outputs: logs/runs/<run_id>.log with timestamp (IST), working directory, command, git commit
#          and dirty flag, tool versions, parameters (selected environment variables), seed,
#          exit code, duration, the last 40 lines of combined stdout/stderr, and sha256 of each
#          --out file. Full output goes to work/runs/<run_id>.out (not committed).
# Exit:    the command's exit code. The command's output is also streamed to the terminal.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
outs=(); seed="none"; tag=""
while [ $# -gt 0 ]; do
    case "$1" in
        --out)  outs+=("$2"); shift 2 ;;
        --seed) seed="$2"; shift 2 ;;
        --tag)  tag="$2"; shift 2 ;;
        --)     shift; break ;;
        *)      echo "run.sh: expected options then -- COMMAND (got '$1')" >&2; exit 2 ;;
    esac
done
[ $# -gt 0 ] || { echo "run.sh: no command given" >&2; exit 2; }

[ -n "$tag" ] || tag="$(basename "$1")"
[ "$tag" = "python3" ] && [ $# -ge 2 ] && tag="$(basename "$2" .py)"
tag="${tag//[^A-Za-z0-9_.-]/_}"
run_id="$(TZ=Asia/Kolkata date +%Y%m%d-%H%M%S)-$$-${tag}"
mkdir -p "$ROOT/logs/runs" "$ROOT/work/runs"
log="$ROOT/logs/runs/$run_id.log"
full="$ROOT/work/runs/$run_id.out"

ver() { "$@" 2>&1 | head -1; }
start=$(date +%s)
"$@" 2>&1 | tee "$full"
rc=${PIPESTATUS[0]}
dur=$(( $(date +%s) - start ))

{
    echo "run_id: $run_id"
    echo "timestamp: $(TZ=Asia/Kolkata date '+%Y-%m-%d %H:%M:%S %z')"
    echo "cwd: $(pwd)"
    printf 'command:'; printf ' %q' "$@"; echo
    echo "git_commit: $(git -C "$ROOT" rev-parse HEAD 2>/dev/null)"
    echo "git_dirty: $([ -n "$(git -C "$ROOT" status --porcelain -- . 2>/dev/null)" ] && echo yes || echo no)"
    echo "tools:"
    echo "  verilator: $(ver verilator --version)"
    echo "  iverilog: $(ver iverilog -V)"
    echo "  riscv-gcc: $(ver riscv64-unknown-elf-gcc --version)"
    echo "  spike: $(spike -h 2>&1 | head -1)"
    echo "  python3: $(ver python3 --version)"
    echo "parameters:"
    for v in CACHES LAT JOBS SEED RTL_DIR WORK_ROOT $(compgen -e | grep '^WH_' || true); do
        [ -n "${!v+x}" ] && echo "  $v=${!v}"
    done
    echo "seed: $seed"
    echo "exit_code: $rc"
    echo "duration_s: $dur"
    echo "outputs:"
    for f in "${outs[@]+"${outs[@]}"}"; do
        if [ -f "$f" ]; then echo "  $(sha256sum "$f" | cut -d' ' -f1)  $f"; else echo "  MISSING  $f"; fi
    done
    echo "full_output: work/runs/$run_id.out"
    echo "output_tail: |"
    tail -n 40 "$full" | sed 's/^/  /'
} > "$log"
exit "$rc"
