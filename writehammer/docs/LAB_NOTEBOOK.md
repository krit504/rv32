# LAB NOTEBOOK

Append-only, timestamped (IST). Earlier entries are never rewritten.

## 2026-11-01 18:16 Project start
Spec v4 read in full. Baseline commit of the existing cache work in `Multi_cycle/` (`848892a`) so the import starts from a recorded state. Layout created (T0.1).

## 2026-11-01 18:40 Tool survey (T0.2)
- I first told the author sky130 was not installed and they chose IHP sg13g2 on that basis (DEC-003). Wrong: sky130A sits under `~/.cache/tt-pdk/root/ciel/sky130/versions/74c0e6b…/sky130A`, which my first search did not look inside. DEC-006 restores the spec default. Lesson: search the whole PDK root, including ciel version stores, before declaring a PDK missing.
- riscv-arch-test HEAD is now the ACT4 framework (needs Sail, uv, Ruby, UDB). Tag `3.10.0` still has the classic `riscv-test-suite/rv32i_m/I` layout with 39 tests, including the six sub-word ones. Pinned that; Spike will produce the reference signatures.
- Dhrystone comes from riscv-tests `benchmarks/dhrystone`; there is no canonical standalone repository.
- The EDA tools live in the author's LibreLane image. I recorded the image id from `docker image inspect` but did not start the container: the author's flow runs go through a supervised launcher with approval.
