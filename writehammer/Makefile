# writehammer Makefile. Targets per spec Section 5. Run from this directory.
# Targets not yet implemented print "NOT IMPLEMENTED" with their task ID and fail, so nothing passes silently.

PY      := python3
VENV_PY := .venv/bin/python
RTL     := $(wildcard rtl/*.sv)
TOP     := rv32_top_pipelined
LATS    := 1 2 3 10
RUN     := scripts/run.sh --   # every result-producing command is logged to logs/runs/ (spec 0B.1)

.PHONY: all lint test arch-test random bench caches wear attacks calibrate eval synth plots \
        hypotheses locks audit clean test-nohazard test-hazard test-cache test-mutants

all: lint test arch-test random bench caches wear attacks calibrate eval synth plots hypotheses audit

lint:
	$(RUN) verilator --lint-only -Wall --top-module $(TOP) $(RTL)
	@echo "[lint] OK: 0 warnings, 0 errors"

test: test-nohazard test-hazard test-cache test-mutants
	@echo "[test] OK"

test-nohazard:
	$(RUN) $(PY) tests/nohazard_test.py
	@for l in $(LATS); do CACHES=1 LAT=$$l $(RUN) $(PY) tests/nohazard_test.py || exit 1; done

test-hazard:
	$(RUN) $(PY) tests/hazard_tests.py --quiet
	$(RUN) $(PY) tests/hazard_tests.py --nofwd --quiet
	@for l in $(LATS); do CACHES=1 LAT=$$l $(RUN) $(PY) tests/hazard_tests.py --quiet || exit 1; \
	                      CACHES=1 LAT=$$l $(RUN) $(PY) tests/hazard_tests.py --nofwd --quiet || exit 1; done

test-cache:
	$(RUN) $(PY) tests/cache_integration.py

test-mutants:
	$(RUN) $(PY) tests/run_mutants.py

# Targets wired to the task that implements them. Until then each prints NOT IMPLEMENTED and fails.
arch-test:  ; @scripts/not_implemented.sh $@ T1.5
random:     ; @scripts/not_implemented.sh $@ T1.6
bench:      ; @scripts/not_implemented.sh $@ "T1.7 T1.8"
caches:     ; @scripts/not_implemented.sh $@ T2.7
wear:       ; @scripts/not_implemented.sh $@ "T3.1-T3.5"
attacks:    ; @scripts/not_implemented.sh $@ "T4.1-T4.8"
calibrate:  ; @scripts/not_implemented.sh $@ T5.6
eval:       ; @scripts/not_implemented.sh $@ T6.1
synth:      ; @scripts/not_implemented.sh $@ T6.5
plots:      ; @scripts/not_implemented.sh $@ T6.2
hypotheses: ; @scripts/not_implemented.sh $@ T6.3
locks:      ; @scripts/not_implemented.sh $@ T0.6
audit:      ; @scripts/not_implemented.sh $@ T7.8

clean:
	rm -rf work obj_dir build
