# T6.5 physical-cost flow

This flow is prepared for the author to run after the observation-free tops and
`docs/T5_INTERFACE.md` land on `main`. The agent must not launch a container or
EDA command. The attack taxonomy is prior work of the author's group (TENDRA
and the Write Hammer draft).

The plan fixes 2 KiB I$, 16-byte lines, and 1 KiB/2 KiB D$. D2 uses powers of
two from M=4 through half the number of D$ lines. The single SDC template and
the same scripts apply to all variants. A baseline core-only run supplies the
core-area denominator. The script rejects an elaborated netlist containing
observation-only signals. It searches each variant's minimum passing clock
period to 0.1 ns resolution and saves each tested period and its timing report.

## Before the author runs EDA

1. Merge the branch carrying `docs/T6_RTL_REQUESTS.md` into `main`; obtain the
   observation-free tops and final T5 interface. Verify `phase-T5-done` exists.
2. Copy `flow/interface.template.json` to `flow/interface.json`, replace all
   provisional names/values from `docs/T5_INTERFACE.md`, list every RTL source
   file needed by both tops, and set detector-specific calibrated thresholds.
   The runner refuses a remaining `TODO` token. Verify threshold values against
   `analysis/calibration.csv`; do not use a held-out workload for calibration.
3. Confirm the exact pinned image ID and the PDK location below. The author
   launches the container and the `--execute` command; the agent does neither.

## Author commands (run from the worktree)

```sh
scripts/run.sh -- python3 flow/plan.py
docker image inspect ghcr.io/librelane/librelane:3.1.0.dev3 --format '{{.Id}}'
docker run --rm -it -v "$PWD:/work" -v "$HOME/.cache/tt-pdk/root/ciel/sky130/versions/74c0e6b118a67d94c24172143d3bd597473fa63d/sky130A:/pdk:ro" -w /work -e PDK_ROOT=/pdk -e WH_AUTHORIZED_FLOW=1 -e WH_PINNED_IMAGE_ID=sha256:369c964be30bcec52d98bf18b2f8c7d80f133c5c9cf34cc1f7d5a0d2890a3103 ghcr.io/librelane/librelane:3.1.0.dev3 scripts/run.sh -- python3 flow/run_flow.py --execute --repeats 3
scripts/run.sh -- python3 flow/parse_results.py --repeats 3
```

The inspected Docker image ID must equal
`sha256:369c964be30bcec52d98bf18b2f8c7d80f133c5c9cf34cc1f7d5a0d2890a3103`.
If it differs, stop. Do not substitute another image. The PDK is sky130A with
`sky130_fd_sc_hd__tt_025C_1v80.lib`.

The author returns the complete `flow/raw/` directory and run log. The parser
requires every planned variant and every repeat, validates the pinned image,
tool/PDK/constraint consistency, and only then writes `flow/cost_table.csv`,
`flow/cost_table.md`, and a provenance sidecar. Until that succeeds, T6.5 is
NOT RUN and no area or Fmax number is reported.
