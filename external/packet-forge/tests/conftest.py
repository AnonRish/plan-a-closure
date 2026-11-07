import json
import os
import shutil

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, "corpus")


@pytest.fixture(scope="session")
def corpus_dir():
    return CORPUS


@pytest.fixture(scope="session")
def manifest():
    with open(os.path.join(CORPUS, "manifest.json")) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def kernel_recorded():
    with open(os.path.join(CORPUS, "kernel_observed.json")) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def kernel_bench():
    from packet_forge import kernel_replay as kr
    why = kr.kernel_available()
    if why:
        pytest.skip("live kernel replay unavailable: " + why)
    with kr.KernelBench(ifname="pftest0", port=5002) as bench:
        yield bench


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "kernel_bench" in getattr(item, "fixturenames", ()):
            item.add_marker(pytest.mark.kernel)
        if item.get_closest_marker("external") and not (shutil.which("tshark") and shutil.which("tcpdump")):
            item.add_marker(pytest.mark.skip(reason="tshark/tcpdump not installed"))
