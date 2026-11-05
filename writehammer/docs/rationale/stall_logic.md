# Stall and freeze handling

**What it is**

Every pipeline register has an enable: `StallF` (pc), `StallD` (F/D), `StallE` (D/E), `StallM` (E/M), `StallW` (M/W), generated in `rtl/hazard_unit.sv`. A D$ miss (`dmiss`) freezes all five, including M/W, so a held consumer keeps its forwarding source. An I$ miss holds only the pc and bubbles F/D. A load-use stall holds pc and F/D and flushes D/E. A redirect flushes F/D and D/E. The equations are `StallF = freeze | stallCond | (imiss & ~redirectE)`, `FlushD = redirectE | (imiss & ~stallCond)`.

**Why it is built this way**

The interaction rules are in `docs/logs/T2.2.md`. A freeze outranks everything, and flushes have no effect while frozen, so a redirect or load-use stall is re-evaluated after the freeze ends because the causing instruction is still in Execute. If a load-use stall is active, F/D must keep its instruction, hence `imiss & ~stallCond`. A redirect in the same cycle wins over the fetch stall, because holding pc would drop the new target. The no-forwarding ablation (`FORWARDING = 0`) masks its dependency stall with `redirectE` for the same reason.

For testing, the top parameter `INJECT_STALL_SEED` (0 means no logic exists) adds two seeded 16-bit LFSRs: one ORs a pipeline-wide freeze into `dmiss`, the other a fetch bubble into `imiss`, each about one cycle in four, in `rtl/rv32_top_pipelined.sv`. The log records no rejected alternative.

**How it is verified**

`tests/stall_injection_test.py` compares against `tests/refmodel.py`: 1000 random hazard-dense programs for each of caches off and caches on (latency 3) with injection seeds 3 and 11 (4000 runs), plus the 21-check no-hazard regression with injection. A control shows injection really stalls (41 cycles in the window without, 82 with). `tests/mutants/stall_mutants.py` has 4 stall-enable mutants, all caught.

**Known limits**

Injected stalls are random, not adversarial, and about one cycle in four each. A first caches-on failure was a test artifact (the program ran off its end and re-executed); the test now appends `jal x0, 0`. Results are compared at HALT, not per cycle.
