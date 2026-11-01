# writehammer Makefile. Targets per spec Section 5. Run from this directory.
# Targets not yet implemented print "NOT IMPLEMENTED (<task>)" and fail, so nothing passes silently.

PY      := python3
VENV_PY := .venv/bin/python
RTL     := $(wildcard rtl/*.sv)
TOP     := rv32_top_pipelined
LATS    := 1 2 3 10

.PHONY: all lint test arch-test random bench caches wear attacks calibrate eval synth plots \
        hypotheses locks audit clean test-nohazard test-hazard test-cache test-mutants

all: lint test arch-test random bench caches wear attacks calibrate eval synth plots hypotheses audit

lint:
	verilator --lint-only -Wall --top-module $(TOP) $(RTL)
	@echo "[lint] OK: 0 warnings, 0 errors"

test: test-nohazard test-hazard test-cache test-mutants
	@echo "[test] OK"

test-nohazard:
	$(PY) tests/nohazard_test.py
	@for l in $(LATS); do CACHES=1 LAT=$$l $(PY) tests/nohazard_test.py || exit 1; done

test-hazard:
	$(PY) tests/hazard_tests.py --quiet
	$(PY) tests/hazard_tests.py --nofwd --quiet
	@for l in $(LATS); do CACHES=1 LAT=$$l $(PY) tests/hazard_tests.py --quiet || exit 1; \
	                      CACHES=1 LAT=$$l $(PY) tests/hazard_tests.py --nofwd --quiet || exit 1; done

test-cache:
	$(PY) tests/cache_integration.py

test-mutants:
	$(PY) tests/run_mutants.py

arch-test random bench caches wear attacks calibrate eval synth plots hypotheses locks audit:
	@echo "NOT IMPLEMENTED ($@)"; exit 1

clean:
	rm -rf work obj_dir build
