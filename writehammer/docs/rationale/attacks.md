# Attack programs

**What it is**

The four attack kinds RLA, RTA, RnLA and RnTA, in a "direct" and a "paper" form, are implemented in `sw/attacks/attack_core.h`, with one-line entry files such as `sw/attacks/rla.c` and the registry `sw/attacks/manifest.json` (eight variants, 2,000,000-cycle target, seeds 1 to 5 for randomized kinds). **The taxonomy is prior work of the author's group (TENDRA and the Write Hammer draft). This project implements it and does not claim it.** As recorded in `docs/logs/T4.2.md`: L is recurring updates of a fixed location, T toggles between two targets, and Rn picks targets at random.

As implemented: RLA writes one fixed target; RTA toggles between two fixed targets, the LFSR varying each dwell; RnLA moves to a new random target (of eight) and dwell at each switch; RnTA toggles within a pair, then picks a new random pair. The direct form increments one word per target line, at geometry-derived D$ lines. The paper form sweeps whole arrays one line larger than the D$ (2064 bytes at the primary geometry), so fills and dirty write-backs occur.

**Why it is built this way**

The paper's LLC mechanism is translated to this D$ (`docs/logs/T4.2.md`). Loop counts use measured cycles per store on the frozen RTL, never a clock read. DEC-010 in `docs/DECISIONS.md` records that the T4.7 rule, "each attack has higher PMR than every benign workload", fails 23 of 24 rows, because benign `crc32` reaches PMR 127.937 on 128 lines. The rule, the benign set and the attacks were left unchanged.

**How it is verified**

Each variant builds natively and as RV32I and halts 0 with caches off and on; a scoped broken-core control (`tests/attack_mutant_control.py`) must halt 127 (`tests/attack_program.py`); `tests/attack_lfsr.py` checks the LFSR (4/4); the D$ trace replays exactly against `tests/cache_model.py` (24/24). Measured PMR(all): RLA direct 128.0 and paper 2.47, RTA direct 64.23 and paper 1.49, RnLA direct 18.77 to 23.45 and paper 1.20 to 1.28, RnTA direct 20.71 to 23.42 and paper 1.24 to 1.26 (`docs/logs/T4.2.md` to `docs/logs/T4.5.md`). 

**Known limits**

T4.7 is PARTIAL. Single-core, modeled-NVM only. Operation counts must be recalibrated if the RTL changes.
