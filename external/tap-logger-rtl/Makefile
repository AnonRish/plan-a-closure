# Everything here is also what the tests run; `make test` is the one to use.
PY ?= python3
RTL = rtl/sha256_core.v rtl/tap_logger.v

.PHONY: test sim lint synth mutate consts clean

test:            ## the whole suite: reference, RTL in two simulators, synthesis, gate level
	$(PY) -m pytest -q

sim:             ## RTL tests only (Icarus Verilog; Verilator cross-check)
	$(PY) -m pytest -q tests/test_rtl.py

lint:
	verilator --lint-only -Wall -Irtl --top-module tap_logger $(RTL)
	iverilog -g2005 -Wall -I rtl -o /dev/null $(RTL)

synth:           ## generic gate-level netlist and resource counts -> build/tap_logger_gates.v
	mkdir -p build
	yosys -q -p "read_verilog -I rtl $(RTL); hierarchy -check -top tap_logger; proc; opt; check -assert; synth -top tap_logger -flatten; opt_clean -purge; check -assert; tee -o /dev/stdout stat; write_verilog -noattr build/tap_logger_gates.v"

mutate:          ## inject 24 hardware bugs, one at a time; the simulation suite must catch each
	$(PY) tools/mutate_rtl.py

consts:          ## regenerate rtl/sha256_consts.vh from the FIPS 180-4 definition
	$(PY) tools/gen_consts.py

clean:
	rm -rf build .pytest_cache
