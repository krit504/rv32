# STATUS

Resume point for any session. Spec: `../../docs/writehammer.md` (v4).
Status words (spec 0B.11): `DONE` only if the acceptance check ran and passed in this run; `PARTIAL` lists unmet sub-criteria; otherwise `BLOCKED` or `NOT RUN`.

Times are IST.

| Task | Status | Last command | Last result | Updated |
|---|---|---|---|---|
| T0.1 | DONE | `ls writehammer` + first commit | layout, `.gitignore`, `STATUS.md`, `DECISIONS.md`, `OPEN_QUESTIONS.md` exist | 2026-11-01 18:16 |
| T0.2 | DONE | `scripts/fetch_third_party.sh` | `docs/TOOLS.md` complete; EDA tool versions are author-reported (container not started by agent) | 2026-11-01 18:45 |
| T0.3 | PARTIAL | `make lint && make test` | lint 0 warnings; test green (21/21 x5, 25/25 x10, 36/36, 12/12 mutants). Unmet: the quoted "5 of 5 mutants" cannot be rerun (no harness in repo); replaced by a 12-mutant harness | 2026-11-01 |
| T0.4 | DONE | `make -n all` | exit 0; unimplemented targets fail loudly with their task ID | 2026-11-01 |
| T0.5 | DONE | `make lint test` via `scripts/run.sh` | complete log records in `logs/runs/`; templates exist | 2026-11-01 |
| T0.6 | DONE | `make locks locks-selftest` | 14 files locked; tamper cases behave as required | 2026-11-01 |
| T1.1 | NOT RUN | | | |
| T1.2 | NOT RUN | | | |
| T1.3 | NOT RUN | | | |
| T1.4 | NOT RUN | | | |
| T1.5 | NOT RUN | | | |
| T1.6 | NOT RUN | | | |
| T1.7 | NOT RUN | | | |
| T1.8 | NOT RUN | | | |
| T2.1 | NOT RUN | | | |
| T2.2 | NOT RUN | | | |
| T2.3 | NOT RUN | | | |
| T2.4 | NOT RUN | | | |
| T2.5 | NOT RUN | | | |
| T2.6 | NOT RUN | | | |
| T2.7 | NOT RUN | | | |
| T3.1 | NOT RUN | | | |
| T3.2 | NOT RUN | | | |
| T3.3 | NOT RUN | | | |
| T3.4 | NOT RUN | | | |
| T3.5 | NOT RUN | | | |
| T4.1 | NOT RUN | | | |
| T4.2 | NOT RUN | | | |
| T4.3 | NOT RUN | | | |
| T4.4 | NOT RUN | | | |
| T4.5 | NOT RUN | | | |
| T4.6 | NOT RUN | | | |
| T4.7 | NOT RUN | | | |
| T4.8 | NOT RUN | | | |
| T5.1 | NOT RUN | | | |
| T5.2 | NOT RUN | | | |
| T5.3 | NOT RUN | | | |
| T5.4 | NOT RUN | | | |
| T5.5 | NOT RUN | | | |
| T5.6 | NOT RUN | | | |
| T5.7 | NOT RUN | | | |
| T5.8 | NOT RUN | | | |
| T5.9 | NOT RUN | | | |
| T5.10 | NOT RUN | | | |
| T6.1 | NOT RUN | | | |
| T6.2 | NOT RUN | | | |
| T6.3 | NOT RUN | | | |
| T6.4 | NOT RUN | | | |
| T6.5 | NOT RUN | | | |
| T7.1 | NOT RUN | | | |
| T7.2 | NOT RUN | | | |
| T7.3 | NOT RUN | | | |
| T7.4 | NOT RUN | | | |
| T7.5 | NOT RUN | | | |
| T7.6 | NOT RUN | | | |
| T7.7 | NOT RUN | | | |
| T7.8 | NOT RUN | | | |
