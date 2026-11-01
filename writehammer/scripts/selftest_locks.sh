#!/usr/bin/env bash
# selftest_locks.sh: prove check_locks.sh catches tampering (T0.6 acceptance; rerun by the T7.8 audit).
# Works on a throwaway copy in work/locktest/; the real tree is not touched.
# Cases: clean copy passes; edited locked file fails; the same edit with a CHANGE_LOG entry split
# across two entries fails; with one proper entry passes; a deleted locked file fails.
# Output: one PASS/FAIL line per case; exit 0 only if every case behaves as expected.
set -uo pipefail
cd "$(dirname "$0")/.."
T=work/locktest; rm -rf "$T"; mkdir -p "$T/RV32I/docs"
cp ../docs/writehammer.md "$T/RV32I/docs/"
rsync -a --exclude work --exclude .venv --exclude third_party ./ "$T/RV32I/writehammer/"
cd "$T/RV32I/writehammer"
ok=1
expect() { # name expected_rc
    scripts/check_locks.sh > /dev/null; rc=$?
    if [ "$rc" = "$2" ]; then echo "PASS $1 (rc=$rc)"; else echo "FAIL $1 (rc=$rc, expected $2)"; ok=0; fi
}
expect "clean copy" 0
f=tests/golden/nohazard_program.hex
echo "# tamper" >> "$f"; H=$(sha256sum "$f" | cut -d' ' -f1)
expect "edited locked file, no entry" 1
printf '\n## CHG-901 x tests/asm.py\n- New sha256: %s\n\n## CHG-902 x %s\n- New sha256: 0\n' "$H" "$f" >> docs/CHANGE_LOG.md
expect "entry split across two CHG blocks" 1
printf '\n## CHG-903 x %s\n- New sha256: %s\n' "$f" "$H" >> docs/CHANGE_LOG.md
expect "one proper CHANGE_LOG entry" 0
rm tests/asm.py
expect "deleted locked file" 1
[ $ok = 1 ] && echo "[selftest_locks] OK" || echo "[selftest_locks] FAIL"
[ $ok = 1 ]
