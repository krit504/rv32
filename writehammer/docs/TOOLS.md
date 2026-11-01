# TOOLS

Recorded 2026-11-01 (IST) by T0.2. "Verified" means the agent ran the version command on this host. "Reported" means the author stated it and the agent did not run it.

## Host tools

| Tool | Version | Path / note | How recorded |
|---|---|---|---|
| Verilator | 5.020 2024-01-01 rev (Debian 5.020-1) | system package | verified |
| Icarus Verilog | 12.0 (stable) | system package | verified |
| RISC-V GCC | `riscv64-unknown-elf-gcc` 13.4.0 (g99677969d46-dirty) | `~/Scratch/toolchain/gcc-13.4/bin`. Used with `-march=rv32i -mabi=ilp32`; the closest multilib is `rv32i_zicsr/ilp32` | verified |
| Spike | 1.1.1-dev | `~/Scratch/toolchain/gcc-13.4/bin/spike` | verified |
| Python | 3.12.3 | system; project venv in `.venv/` (gitignored) | verified |
| numpy / pandas / matplotlib | 2.5.4 / 3.1.0 / 3.11.2 | `.venv/` | verified |
| GNU Make | 4.3 | | verified |
| git | 2.55.0 | | verified |
| Docker | 29.1.3 | | verified |

## Physical-design tools (Docker image, author-launched)

Image `ghcr.io/librelane/librelane:3.1.0.dev3`, id `sha256:369c964be30bcec52d98bf18b2f8c7d80f133c5c9cf34cc1f7d5a0d2890a3103` (id verified with `docker image inspect`; the agent did not start the container).

| Tool | Version | How recorded |
|---|---|---|
| Yosys | 0.66 | reported |
| OpenROAD | 2026-02-17 build (OpenROAD `dcf36133`) | reported |
| OpenSTA | included in the image | reported |
| KLayout, Magic, Netgen | included in the image | reported |

The agent verifies these versions inside the container only when the author launches the T6.5 flow (Q-002).

## PDK

| PDK | Location | Version | How recorded |
|---|---|---|---|
| sky130A, `sky130_fd_sc_hd` (used by T6.5, DEC-006) | `~/.cache/tt-pdk/root/ciel/sky130/versions/74c0e6b118a67d94c24172143d3bd597473fa63d/sky130A` | open_pdks `74c0e6b` | verified (files present) |

## Third-party sources (`third_party/`, gitignored, pinned)

| Source | Repository | Commit | Used by |
|---|---|---|---|
| riscv-arch-test | github.com/riscv-non-isa/riscv-arch-test, tag `3.10.0` | `fc32e41d49480fd99ba0a192dfff9c3319b44873` | T1.5. Classic `riscv-test-suite/rv32i_m/I` layout; HEAD has moved to the ACT4 framework (needs Sail, uv, Ruby, UDB), so the last 3.x release is used, with Spike for the reference signatures |
| CoreMark | github.com/eembc/coremark | `1f483d5b8316753a742cbf5590caf5bd0a4e4777` | T1.7 |
| Embench-IoT | github.com/embench/embench-iot | `09c2ed8c3b7008c95d08b038de4a3f6dc103ed70` | T1.8 |
| riscv-tests (Dhrystone in `benchmarks/dhrystone`) | github.com/riscv-software-src/riscv-tests | `3df703cd52d5f0d8224e3c50bf03c6cb70efff98` | T1.7 |

`scripts/fetch_third_party.sh` (T0.4) re-clones these at the pinned commits.

## Missing or not used

| Tool | Status | Fallback |
|---|---|---|
| SymbiYosys / riscv-formal | not installed on host | stretch item only (Section 10) |
