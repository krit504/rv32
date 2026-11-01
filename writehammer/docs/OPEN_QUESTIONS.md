# OPEN QUESTIONS

Things the agent would have asked mid-run (spec 0.1). Each has the default taken meanwhile.

| ID | Question | Default taken | Raised |
|---|---|---|---|
| Q-001 | Is `github.com/krit504/rv32` private? The agent cannot check (`gh` not installed). | Never push from this project. | 2026-11-01 |
| Q-002 | Who launches T6.5 flow runs, and how? The author's runs use a supervised launcher with a hash-checked manifest and approval. | The agent writes `flow/` scripts and hands the exact commands to the author. T6.5 stays `NOT RUN` until the author runs them. | 2026-11-01 |
| Q-003 | T1.1 needs `funct3` in the Memory stage (to pick load/store width), so `e_m_reg` gains a `funct3E`/`funct3M` field. Spec 0.9 says pipeline-register changes beyond stall enables go here, with the change made only if required for correctness. | Made: required for correctness (without it Memory cannot tell `lb` from `lw`). No other register changed. | 2026-11-01 |
