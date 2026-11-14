"""`closure doctor`: the report of what the pilot can do on a machine, checked against machines described by hand."""
import json
from types import SimpleNamespace

import pytest

from closure import doctor as D
from closure.cli import main


class NVMLError(Exception):
    pass


def fake_nvml(gpus):
    """A pynvml stand-in. gpus: [{name, limit_w, energy (bool), util (bool), mem_gb, mig}]."""
    def need(g, key, value):
        if not g.get(key, True):
            raise NVMLError("Not Supported")
        return value
    return SimpleNamespace(
        NVML_CLOCK_SM=1, nvmlInit=lambda: None, nvmlShutdown=lambda: None,
        nvmlSystemGetDriverVersion=lambda: b"580.82.07", nvmlDeviceGetCount=lambda: len(gpus),
        nvmlDeviceGetHandleByIndex=lambda i: gpus[i], nvmlDeviceGetName=lambda g: g["name"].encode(),
        nvmlDeviceGetUUID=lambda g: f"GPU-{g['name'][-4:]}", nvmlDeviceGetTotalEnergyConsumption=lambda g: need(g, "energy", 123456),
        nvmlDeviceGetUtilizationRates=lambda g: need(g, "util", SimpleNamespace(gpu=7)),
        nvmlDeviceGetPowerManagementLimit=lambda g: int(g["limit_w"] * 1000),
        nvmlDeviceGetPowerManagementDefaultLimit=lambda g: int(g["limit_w"] * 1000),
        nvmlDeviceGetPowerManagementLimitConstraints=lambda g: (int(g["limit_w"] * 400), int(g["limit_w"] * 1000)),
        nvmlDeviceGetMemoryInfo=lambda g: SimpleNamespace(total=int(g.get("mem_gb", 16) * 2 ** 30)),
        nvmlDeviceGetClockInfo=lambda g, kind: 1200, nvmlDeviceGetMigMode=lambda g: (int(g.get("mig", 0)), 0))


def fake_torch(caps, version="2.14.1+cu130"):
    cuda = SimpleNamespace(is_available=lambda: bool(caps), device_count=lambda: len(caps),
                           get_device_capability=lambda i: caps[i], get_device_name=lambda i: f"cuda{i}")
    return SimpleNamespace(__version__=version, cuda=cuda)


def sysinfo(root=True, smi=True):
    return {"closure": "x", "git_commit": None, "python": "3.12", "os": "Linux", "machine": "x86_64", "root": root,
            "nvidia_smi": smi, "ots": False}


def steps(gpu):
    return {r["step"]: r for r in gpu["plan"]}


def test_a_t4_as_root_runs_every_step_without_the_fp8_variant():
    r = D.report(fake_nvml([{"name": "Tesla T4", "limit_w": 70}]), fake_torch([(7, 5)]), "/nonexistent", sysinfo())
    g = r["nvidia_gpus"][0]
    assert g["architecture"] == "Turing" and g["hardware_runs_on_record_for_this_model"] and g["power_limit_w"] == 70.0
    s = steps(g)
    assert [s[k]["runs"] for k in ("preflight", "hw-selftest", "hw-probe", "hw-state", "hw-trial")] == ["yes"] * 5
    assert "no FP8 variant" in s["hw-probe"]["note"] and s["independent meter"]["runs"] == "no"
    assert "--gpu 0" in r["verdict"]


@pytest.mark.parametrize("name,cap,arch,watts", [("NVIDIA H100 80GB HBM3", (9, 0), "Hopper", 700),
                                                ("NVIDIA H200", (9, 0), "Hopper", 700),
                                                ("NVIDIA B200", (10, 0), "Blackwell", 1000),
                                                ("NVIDIA L40S", (8, 9), "Ada Lovelace", 350),
                                                ("NVIDIA GeForce RTX 5090", (12, 0), "Blackwell (RTX)", 575)])
def test_newer_gpus_get_the_fp8_variant_and_are_said_to_be_new_to_the_kit(name, cap, arch, watts):
    r = D.report(fake_nvml([{"name": name, "limit_w": watts, "mem_gb": 80}] * 2), fake_torch([cap, cap]), "/nonexistent", sysinfo())
    assert len(r["nvidia_gpus"]) == 2
    g = r["nvidia_gpus"][1]
    assert g["architecture"] == arch and g["compute_capability"] == list(cap) and g["power_limit_w"] == watts
    assert not g["hardware_runs_on_record_for_this_model"]
    assert "FP8 variant" in steps(g)["hw-probe"]["note"] and "no FP8" not in steps(g)["hw-probe"]["note"]
    assert "no hardware run of this kit on this GPU model" in D.to_markdown(r)


def test_without_root_the_probe_and_trial_run_reduced_and_say_why():
    r = D.report(fake_nvml([{"name": "Tesla T4", "limit_w": 70}]), fake_torch([(7, 5)]), "/nonexistent", sysinfo(root=False))
    s = steps(r["nvidia_gpus"][0])
    assert s["hw-probe"]["runs"] == "reduced" and "lower bound" in s["hw-probe"]["note"]
    assert s["hw-trial"]["runs"] == "yes" and "clocks not locked" in s["hw-trial"]["note"]


def test_missing_counters_cuda_or_mig_are_named():
    no_energy = D.report(fake_nvml([{"name": "Old GPU", "limit_w": 250, "energy": False}]), fake_torch([(6, 1)]), "/nonexistent", sysinfo())
    s = steps(no_energy["nvidia_gpus"][0])
    assert s["preflight"]["runs"] == "no" and "no NVML energy counter" in s["preflight"]["note"] and s["hw-trial"]["runs"] == "no"
    assert "no NVIDIA GPU that NVML can read" in no_energy["verdict"] and s["hw-state"]["runs"] == "yes"
    no_util = D.report(fake_nvml([{"name": "Tesla T4", "limit_w": 70, "util": False}]), fake_torch([(7, 5)]), "/nonexistent", sysinfo())
    assert steps(no_util["nvidia_gpus"][0])["hw-trial"]["runs"] == "reduced"
    no_cuda = D.report(fake_nvml([{"name": "Tesla T4", "limit_w": 70}]), fake_torch([]), "/nonexistent", sysinfo())
    assert steps(no_cuda["nvidia_gpus"][0])["preflight"]["runs"] == "no" and no_cuda["nvidia_gpus"][0]["compute_capability"] is None
    # the GPU is there and NVML reads it: the verdict must blame the PyTorch build, not say that no GPU was found
    assert "NVML reads 1 GPU with an energy counter" in no_cuda["verdict"] and "cannot use CUDA" in no_cuda["verdict"]
    assert "no NVIDIA GPU" not in no_cuda["verdict"] and "see its row" in steps(no_cuda["nvidia_gpus"][0])["hw-trial"]["note"]
    mig = D.report(fake_nvml([{"name": "NVIDIA H100", "limit_w": 700, "mig": 1}]), fake_torch([(9, 0)]), "/nonexistent", sysinfo())
    assert mig["nvidia_gpus"][0]["plan"][0]["step"] == "everything" and "turn MIG off" in mig["verdict"]
    assert "tier0 --mock" in mig["verdict"]
    mixed = D.report(fake_nvml([{"name": "Tesla T4", "limit_w": 70}, {"name": "NVIDIA H100", "limit_w": 700}]),
                     fake_torch([(9, 0), (7, 5)]), "/nonexistent", sysinfo())
    assert all(g["compute_capability"] is None for g in mixed["nvidia_gpus"])       # orders can differ: no guess


def test_without_pytorch_the_gpu_is_reported_as_not_read_rather_than_unable():
    """The first look at a machine is often before PyTorch is installed (scripts/run_anywhere.sh installs it only for
    a hardware run). NVML can already say the GPU is there and has its counters; what CUDA can do on it is unknown, and
    the report must say unknown, not no."""
    r = D.report(fake_nvml([{"name": "NVIDIA H100 80GB HBM3", "limit_w": 700}]), False, "/nonexistent", sysinfo())
    s = steps(r["nvidia_gpus"][0])
    assert [s[k]["runs"] for k in ("preflight", "hw-selftest", "hw-probe", "hw-state", "hw-trial")] == ["not read"] * 5
    assert "PyTorch is not installed" in s["hw-trial"]["note"] and r["nvidia_gpus"][0]["compute_capability"] is None
    assert "NVML reads 1 GPU with an energy counter" in r["verdict"] and "run_anywhere.sh --hardware" in r["verdict"]
    assert "| hw-trial | not read |" in D.to_markdown(r)
    blind = D.report(fake_nvml([{"name": "Old GPU", "limit_w": 250, "energy": False}]), False, "/nonexistent", sysinfo())
    assert steps(blind["nvidia_gpus"][0])["hw-trial"]["runs"] == "no" and "no NVIDIA GPU that NVML can read" in blind["verdict"]


def test_the_record_holds_no_path_from_this_machine():
    """doctor.json travels in every pilot bundle: tools are recorded as found or not, never by where they are."""
    sysf = D.system_facts()
    assert isinstance(sysf["nvidia_smi"], bool) and isinstance(sysf["ots"], bool)
    assert not any(isinstance(v, str) and ("/home/" in v or "/Users/" in v or "\\Users\\" in v) for v in sysf.values())


def test_no_nvml_at_all_points_to_the_mock_pilot():
    broken = SimpleNamespace(nvmlInit=lambda: (_ for _ in ()).throw(NVMLError("Driver Not Loaded")))
    r = D.report(broken, fake_torch([]), "/nonexistent", sysinfo())
    assert not r["nvml"]["nvml"] and "Driver Not Loaded" in r["nvml"]["why"] and "tier0 --mock" in r["verdict"]
    assert "not available" in D.to_markdown(r)


def test_other_makers_gpus_are_listed_from_sysfs_with_what_the_kernel_reports(tmp_path):
    def card(name, vendor, files=(), busy=False):
        dev = tmp_path / "class" / "drm" / name / "device"
        (dev / "hwmon" / "hwmon3").mkdir(parents=True)
        (dev / "vendor").write_text(vendor + "\n")
        for f in files:
            (dev / "hwmon" / "hwmon3" / f).write_text("1\n")
        if busy:
            (dev / "gpu_busy_percent").write_text("0\n")
    card("card0", "0x1002", ("power1_average", "temp1_input"), busy=True)
    card("card1", "0x8086", ("energy1_input",))
    card("card2", "0x10de")
    card("card3", "0x1a03")
    (tmp_path / "class" / "drm" / "card0-DP-1").mkdir()
    got = {c["card"]: c for c in D.sysfs_gpus(tmp_path)}
    assert set(got) == {"card0", "card1", "card2", "card3"}
    assert got["card0"]["vendor"] == "AMD" and got["card0"]["power_or_energy_files"] == ["power1_average"] and got["card0"]["busy_percent_file"]
    assert got["card1"]["vendor"] == "Intel" and got["card1"]["power_or_energy_files"] == ["energy1_input"]
    r = D.report(fake_nvml([]), fake_torch([]), tmp_path, sysinfo())
    assert [c["vendor"] for c in r["other_gpus"]] == ["AMD", "Intel", "other"]              # NVIDIA is read through NVML
    assert "dcbus-analyze" in r["other_gpus"][0]["note"] and "no power or energy" in r["other_gpus"][2]["note"]
    assert "none is written for this maker" in D.to_markdown(r)
    assert D.sysfs_gpus(tmp_path / "missing") == []


def test_the_command_runs_on_a_machine_without_a_gpu_and_writes_both_files(tmp_path, capsys):
    assert main(["doctor", "--out", str(tmp_path)]) == 0
    text = capsys.readouterr().out
    assert text.startswith("# closure doctor") and (tmp_path / "doctor.md").read_text().strip() == text.strip()
    rep = json.loads((tmp_path / "doctor.json").read_text())
    assert rep["verdict"] and rep["system"]["closure"]
    assert main(["doctor", "--json"]) == 0 and json.loads(capsys.readouterr().out)["what"]
