#!/usr/bin/env bash
# check_locks.sh: verify protected artifacts against docs/LOCKED.sha256 (spec 0A.A, T0.6).
#
# Usage:  scripts/check_locks.sh            check; exit 1 on any unexplained change
#         scripts/check_locks.sh --add      append hashes for protected files not yet locked
#                                           (new tests, new golden data); never rewrites a line
# Protected set: docs/CRITERIA.md, the spec ../docs/writehammer.md, and every file under tests/
# (except __pycache__ and .gitkeep).
# Rule: a locked file whose hash differs, or that is missing, passes only if one docs/CHANGE_LOG.md
# entry (a "## CHG-" block) names that path and its current sha256 (or "DELETED"). Otherwise the
# check fails. Files that exist but are not locked yet are reported; run --add to lock them.
set -uo pipefail
cd "$(dirname "$0")/.."
LOCK=docs/LOCKED.sha256
CHG=docs/CHANGE_LOG.md

protected() {
    echo docs/CRITERIA.md
    echo ../docs/writehammer.md
    find tests -type f ! -path '*/__pycache__/*' ! -name '.gitkeep' | sort
}

if [ "${1:-}" = "--add" ]; then
    touch "$LOCK"
    n=0
    while read -r f; do
        if ! awk '{print $2}' "$LOCK" | grep -qxF "$f"; then
            sha256sum "$f" >> "$LOCK"; n=$((n + 1))
        fi
    done < <(protected)
    echo "[locks] added $n file(s) to $LOCK"
    exit 0
fi

[ -f "$LOCK" ] || { echo "[locks] FAIL: $LOCK missing"; exit 1; }

# True if a single "## CHG-" entry in CHANGE_LOG.md contains both strings.
entry_has() {
    awk -v a="$1" -v b="$2" '
        /^## CHG-/ { if (ha && hb) found = 1; ha = 0; hb = 0 }
        index($0, a) { ha = 1 }
        index($0, b) { hb = 1 }
        END { if (ha && hb) found = 1; exit !found }' "$CHG"
}
fail=0
while read -r want f; do
    if [ -f "$f" ]; then
        have=$(sha256sum "$f" | cut -d' ' -f1)
        [ "$have" = "$want" ] && continue
        if entry_has "$f" "$have"; then
            echo "[locks] changed with CHANGE_LOG entry: $f"
        else
            echo "[locks] FAIL: $f changed without a CHANGE_LOG entry (current sha256 $have)"; fail=1
        fi
    else
        if entry_has "$f" "DELETED"; then
            echo "[locks] deleted with CHANGE_LOG entry: $f"
        else
            echo "[locks] FAIL: $f is locked but missing"; fail=1
        fi
    fi
done < "$LOCK"

while read -r f; do
    awk '{print $2}' "$LOCK" | grep -qxF "$f" || echo "[locks] note: $f not locked yet (run scripts/check_locks.sh --add)"
done < <(protected)

[ $fail -eq 0 ] && echo "[locks] OK: $(wc -l < "$LOCK") locked file(s) verified"
exit $fail
