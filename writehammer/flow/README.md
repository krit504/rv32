# T6.5 physical-cost flow

This flow uses the delivered observation-free `cache_system` and `core_only` tops
and `docs/T5_INTERFACE.md`. Physical runs are author-controlled; on 2026-11-05
the author explicitly authorized this agent to launch the pinned run. The attack
taxonomy is prior work of the author's group (TENDRA and the Write Hammer draft).

The plan fixes 2 KiB I$, 16-byte lines, and 1 KiB/2 KiB D$. D2 uses powers of
two from M=4 through half the number of D$ lines. The single SDC template and
the same scripts apply to all variants. A baseline core-only run supplies the
core-area denominator. The script rejects an elaborated netlist containing
observation-only signals. It searches each variant's minimum passing clock
period to 0.1 ns resolution and saves each tested period and its timing report.

## Before the author runs EDA

1. Verify `phase-T5-done` and both delivered RTL tops exist.
2. Run `flow/specialize_core.py`, then `flow/make_interface.py --write`.
   The specialization creates a source-hashed copy of `rv32_top_pipelined.sv`
   containing only the `CORE_ONLY=1` generate branches and packs its unused
   debug-memory output for Yosys's standard Verilog reader. It never edits
   `rtl/`. The shared flow parameterizes the cache top in a separate Yosys
   step to avoid a frontend hierarchy assertion in the pinned image.
   It reads detector-specific k=2/window=10,000 thresholds directly from
   `analysis/calibration.csv` and writes a hashed `flow/interface.json`.
   The runner checks `OBSERVE=0`, A1, static D3, 16-bit counters and source
   availability. `core_only` uses the pipeline source; unused cache and memory
   modules are pruned by hierarchy before area and timing are measured. Do not
   use a held-out workload for calibration.
3. Confirm the exact pinned image ID and the PDK location below. The author
   launches the container and the `--execute` command; the agent does neither.

## Author commands (run from the worktree)

```sh
scripts/run.sh -- python3 flow/plan.py
scripts/run.sh -- python3 flow/specialize_core.py
scripts/run.sh -- python3 flow/make_interface.py --write
scripts/run.sh -- python3 flow/run_flow.py --check-plan
docker image inspect ghcr.io/librelane/librelane:3.1.0.dev3 --format '{{.Id}}'
docker run --rm -it --user "$(id -u):$(id -g)" -v "$PWD:/work" -v "$HOME/.cache/tt-pdk/root/ciel/sky130/versions/74c0e6b118a67d94c24172143d3bd597473fa63d/sky130A:/pdk:ro" -w /work -e PDK_ROOT=/pdk -e WH_AUTHORIZED_FLOW=1 -e WH_PINNED_IMAGE_ID=sha256:369c964be30bcec52d98bf18b2f8c7d80f133c5c9cf34cc1f7d5a0d2890a3103 ghcr.io/librelane/librelane:3.1.0.dev3 scripts/run.sh -- python3 flow/run_flow.py --execute --repeats 3
scripts/run.sh -- python3 flow/parse_results.py --repeats 3
MPLCONFIGDIR=/tmp/wh-mpl make plots
```

The inspected Docker image ID must equal
`sha256:369c964be30bcec52d98bf18b2f8c7d80f133c5c9cf34cc1f7d5a0d2890a3103`.
If it differs, stop. Do not substitute another image. The PDK is sky130A with
`sky130_fd_sc_hd__tt_025C_1v80.lib`.

The author returns the complete `flow/raw/` directory and run log. The parser
requires every planned variant and every repeat, validates the pinned image,
tool/PDK/constraint consistency, and only then writes `flow/cost_table.csv`,
`flow/cost_table.md`, and a provenance sidecar. `make plots` then generates
`flow/area_fmax.png` from that measured CSV. Until parsing succeeds, T6.5 is
NOT RUN and no area or Fmax number is reported.
