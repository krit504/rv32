# CHANGE LOG

Every change to a protected artifact (spec 0A.A): what changed, why, and evidence the original was wrong. `scripts/check_locks.sh` fails when a locked file's hash changes without an entry here naming the file.

Entry format:

```
## CHG-NNN YYYY-MM-DD <file path>
- What changed:
- Why:
- Evidence the original was wrong:
- New sha256:
```
