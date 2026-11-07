import shutil

import pytest


def pytest_collection_modifyitems(config, items):
    have = lambda *tools: all(shutil.which(t) for t in tools)
    for item in items:
        if item.nodeid.startswith("tests/test_rtl") and not have("iverilog", "vvp"):
            item.add_marker(pytest.mark.skip(reason="iverilog not installed"))
        if item.nodeid.startswith("tests/test_synth") and not have("yosys", "verilator"):
            item.add_marker(pytest.mark.skip(reason="yosys/verilator not installed"))
