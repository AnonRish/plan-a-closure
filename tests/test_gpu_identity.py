"""`--gpu N` touches only the physical GPU behind cuda:N: matched in NVML by UUID or PCI address, never by index alone."""
import signal
import types

import pytest

from closure.hw import gpu as G


def _nvml(n=4, uuids=None):
    uuids = uuids or [f"GPU-aaaa0000-0000-4000-8000-{i:012d}" for i in range(n)]
    N = types.SimpleNamespace()
    N.nvmlDeviceGetCount = lambda: n
    N.nvmlDeviceGetHandleByIndex = lambda i: i
    N.nvmlDeviceGetUUID = lambda h: uuids[h].encode()                 # older pynvml returns bytes
    N.nvmlDeviceGetPciInfo = lambda h: types.SimpleNamespace(domain=0, bus=0x18 + h, device=0)
    return N


def _torch(props, count=1, cuda=True):
    cuda_ns = types.SimpleNamespace(is_available=lambda: cuda, device_count=lambda: count,
                                    get_device_properties=lambda i: props[i])
    return types.SimpleNamespace(cuda=cuda_ns)


def test_a_scheduler_that_renumbers_gpus_is_followed_by_uuid():
    # Slurm gave this job physical GPU 3 as cuda:0: index 0 in NVML would be somebody else's GPU
    props = [types.SimpleNamespace(uuid="aaaa0000-0000-4000-8000-000000000003")]
    t = G.resolve(0, N=_nvml(), torch=_torch(props), env={"CUDA_VISIBLE_DEVICES": "3"})
    assert (t.index, t.torch_device, t.nvml_index, t.how) == (0, "cuda:0", 3, "uuid")
    assert t.uuid == "GPU-aaaa0000-0000-4000-8000-000000000003" and not t.rehearsal


def test_pci_address_is_the_fallback_when_torch_gives_no_uuid():
    props = [types.SimpleNamespace(uuid=None, pci_domain_id=0, pci_bus_id=0x1A, pci_device_id=0)]
    t = G.resolve(0, N=_nvml(), torch=_torch(props), env={})
    assert t.nvml_index == 2 and t.how == "PCI address"


def test_it_refuses_rather_than_guesses():
    stranger = [types.SimpleNamespace(uuid="bbbb0000-0000-4000-8000-000000000009")]
    with pytest.raises(RuntimeError, match="refusing to guess"):
        G.resolve(0, N=_nvml(), torch=_torch(stranger), env={})
    with pytest.raises(RuntimeError, match="sees 1 GPU"):
        G.resolve(1, N=_nvml(), torch=_torch(stranger), env={})
    old_torch = [types.SimpleNamespace()]                               # neither uuid nor PCI address
    with pytest.raises(RuntimeError, match="cannot be matched"):
        G.resolve(0, N=_nvml(), torch=_torch(old_torch), env={"CUDA_VISIBLE_DEVICES": "2"})
    t = G.resolve(0, N=_nvml(), torch=_torch(old_torch), env={"CUDA_DEVICE_ORDER": "PCI_BUS_ID"})
    assert t.nvml_index == 0 and "PCI order" in t.how                 # safe only without CUDA_VISIBLE_DEVICES


def test_no_cuda_is_an_error_unless_this_is_a_rehearsal():
    with pytest.raises(RuntimeError, match="no CUDA GPU"):
        G.resolve(0, N=_nvml(), torch=_torch([], cuda=False), env={})
    t = G.resolve(1, N=_nvml(), torch=_torch([], cuda=False), env={G.REHEARSAL_ENV: "1"})
    assert t.rehearsal and t.torch_device == "cpu" and t.nvml_index == 1 and "REHEARSAL" in t.describe()


def test_pci_order_is_preferred_without_overriding_an_explicit_choice():
    env = {}
    G.prefer_pci_order(env)
    assert env["CUDA_DEVICE_ORDER"] == "PCI_BUS_ID"
    env = {"CUDA_DEVICE_ORDER": "FASTEST_FIRST"}
    G.prefer_pci_order(env)
    assert env["CUDA_DEVICE_ORDER"] == "FASTEST_FIRST"


def test_signals_are_held_while_the_gpu_is_restored():
    before = signal.getsignal(signal.SIGTERM)
    with G.signals_held():
        assert signal.getsignal(signal.SIGTERM) == signal.SIG_IGN
    assert signal.getsignal(signal.SIGTERM) == before


def test_rehearsal_results_can_never_stand_in_for_a_hardware_run(tmp_path, monkeypatch):
    import json
    from closure import cli
    from closure.hw import probe as P
    monkeypatch.delenv(G.REHEARSAL_ENV, raising=False)
    assert cli.main(["hw-trial", "--confirm-hardware", "--profile", "rehearsal", "--out", str(tmp_path / "r")]) == 2
    f = tmp_path / "probe.json"
    f.write_text(json.dumps(P.seal(P.run_probe(P.FakeProbeRig(), P.default_variants(), repeats=2), cli.REHEARSAL_STATUS)))
    cfg = cli._cfg("smoke", 1, "HARDWARE")
    with pytest.raises(SystemExit, match="CPU rehearsal"):
        cli._apply_probe(cfg, f, tmp_path / "run", hardware=True, rehearsal=False)
    cli._apply_probe(cfg, f, tmp_path / "run2", hardware=True, rehearsal=True)       # a rehearsal may use its own probe
    assert cfg.probe_sha256 == json.loads(f.read_text())["sha256"]
