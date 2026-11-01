# DECISIONS

Each entry: the choice, the alternatives, the reason, the impact, the date (IST). Changes to Section 3 defaults or Section 4 definitions also go into `CHANGE_LOG.md`.

## DEC-001 Project location: subdirectory `RV32I/writehammer/` of the existing repo
- **Alternatives:** a new local-only repository.
- **Reason:** author's choice (2026-11-01). Keeps the study next to the core it extends.
- **Impact:** the repo has an `origin` remote (`github.com/krit504/rv32`). Spec 0.6 forbids pushing to a public remote; nothing in this project pushes. Remote visibility is unverified (see `OPEN_QUESTIONS.md`).
- **Date:** 2026-11-01

## DEC-002 Commits by the agent, krit504 identity, no attribution trailer
- **Alternatives:** the author commits from commands the agent provides.
- **Reason:** author allowed per-task commits for this project. Every commit passes `-c user.name=krit504 -c user.email=138591590+krit504@users.noreply.github.com`, because the repo's local git config holds a different (work) identity. No co-author or tool attribution line.
- **Impact:** commit messages follow spec 0B.12 (`T<ID>: summary`).
- **Date:** 2026-11-01

## DEC-003 (SUPERSEDED by DEC-006) Physical flow uses IHP sg13g2, not sky130 (deviation from Section 3)
- **Alternatives:** IHP sg13cmos5l (the author's Tiny Tapeout chip library); installing sky130 into the PDK cache.
- **Reason:** sky130 is not installed. sg13g2 is in `~/.cache/tt-pdk/root`, and this project has no tie to the Tiny Tapeout chip. Tools come from the author's pinned LibreLane Docker image (`ghcr.io/librelane/librelane:3.1.0.dev3`, id `sha256:369c964b…`).
- **Impact:** every T6.5 number is labelled sg13g2 and must not be compared with the author's sg13cmos5l results. Flow runs are prepared as scripts and launched by the author, not by the agent.
- **Date:** 2026-11-01

## DEC-004 The cache datasheet in the author's notes is v1 history; this spec governs
- **Alternatives:** update that datasheet as the caches change.
- **Reason:** author's choice. The datasheet describes a write-through, no-write-allocate D$, word-only accesses, and two separate backing memories with no shared port.
- **Differences from the spec (spec wins):** D$ becomes write-back plus write-allocate with dirty bits and byte enables (T2.4); one unified `mem_model` with an arbiter giving the D$ priority replaces the two backing memories (T2.1); line size becomes a parameter (16/32/64 B) instead of a fixed 16 B; cache sizes default to 2 KB (128 lines) instead of 1 KB (64 lines).
- **Impact:** the new design is documented in `docs/rationale/`.
- **Date:** 2026-11-01

## DEC-005 The test baseline is the current repo, not the counts quoted in T0.3
- **Alternatives:** use T0.3's "16 directed hazard cases in 18 runs, 5 of 5 mutants".
- **Reason:** the repo has grown since the spec was written: 25 directed hazard programs, each run with forwarding and with the no-forwarding ablation, plus the cache-on runs at four latencies. Spec 0A.A forbids test counts decreasing, so the floor is what exists now. The exact counts are recorded in T0.3's log.
- **Impact:** T0.3 checks that the quoted results reproduce as a subset, and records the larger current numbers as the baseline.
- **Date:** 2026-11-01

## DEC-006 Physical flow uses sky130 `sky130_fd_sc_hd` as Section 3 specifies (supersedes DEC-003)
- **Alternatives:** IHP sg13g2 (DEC-003).
- **Reason:** DEC-003 rested on the agent's claim that sky130 was not installed. That claim was wrong: sky130A is installed through ciel at `~/.cache/tt-pdk/root/ciel/sky130/versions/74c0e6b118a67d94c24172143d3bd597473fa63d/sky130A` (open_pdks `74c0e6b`), with `libs.ref/sky130_fd_sc_hd/lib` present. With no download needed, the spec default applies and there is no deviation.
- **Impact:** T6.5 uses `sky130_fd_sc_hd`, same tools (the author's pinned LibreLane image), same constraints for every variant. Results are labelled sky130 and are not comparable with the author's sg13cmos5l numbers. Flow runs are still launched by the author (Q-002).
- **Date:** 2026-11-01
