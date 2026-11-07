"""tests/test_hardware.py -- Phases 6-9, 18."""
import sys, os, collections
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
import torch
import torch.nn as nn

from cuda_guard.ledger import TamperEvidentLedger
from cuda_guard.hardware import DeviceDiscovery, run_attestation, DeviceRegistry, ModelIdentity, compose_device_authorization
from cuda_guard.evidence import RegistryStatus, EvidenceStatus, EvidenceRecord, EvidenceClass, EvidenceSource, TrustRoot


def test_device_discovery_emulated_fallback():
    devices = DeviceDiscovery().query()
    assert len(devices) >= 1


def test_attestation_skips_fast_without_hanging_when_no_cc_gpu():
    ledger = TamperEvidentLedger()
    t0 = time.monotonic()
    ev = run_attestation(ledger, cc_capable_gpu_suspected=False, device_uuid="x")
    assert ev.status == EvidenceStatus.UNAVAILABLE
    assert time.monotonic() - t0 < 2.0


def test_composition_never_upgrades_unknown_registry_to_authorized():
    reg = DeviceRegistry()
    ok = EvidenceRecord(EvidenceClass.HARDWARE_ATTESTATION, EvidenceSource.NRAS_LOCAL_VERIFIER,
                         EvidenceStatus.SUCCESS, TrustRoot.NVIDIA_SIGNING_INFRASTRUCTURE, [], [])
    result = compose_device_authorization(ok, reg.check("never-registered"))
    assert "AUTHORIZED" not in result["conclusion"]


def test_composition_failed_attestation_is_adverse_even_with_authorized_registry():
    reg = DeviceRegistry()
    reg.register("gpu-A", RegistryStatus.AUTHORIZED)
    failed = EvidenceRecord(EvidenceClass.HARDWARE_ATTESTATION, EvidenceSource.NRAS_LOCAL_VERIFIER,
                             EvidenceStatus.FAILED, TrustRoot.NVIDIA_SIGNING_INFRASTRUCTURE, [], [])
    result = compose_device_authorization(failed, reg.check("gpu-A"))
    assert result["conclusion"] == "DEVICE_AUTHORIZATION_ADVERSE"


def test_model_identity_matrix():
    ledger = TamperEvidentLedger()
    mi = ModelIdentity(ledger)
    model = nn.Linear(4, 4)
    h_orig = mi.hash_state_dict(model.state_dict())

    # same model
    assert mi.hash_state_dict(model.state_dict()) == h_orig
    # reordered dict -> still matches (sorted internally)
    reordered = collections.OrderedDict(reversed(list(model.state_dict().items())))
    assert mi.hash_state_dict(reordered) == h_orig
    # changed tensor
    m2 = nn.Linear(4, 4)
    with torch.no_grad():
        m2.load_state_dict(model.state_dict())
        m2.weight[0, 0] += 1.0
    assert mi.hash_state_dict(m2.state_dict()) != h_orig
    # changed dtype
    sd64 = {k: v.double() for k, v in model.state_dict().items()}
    assert mi.hash_state_dict(sd64) != h_orig
    # missing tensor
    sd_missing = dict(model.state_dict()); del sd_missing["bias"]
    assert mi.hash_state_dict(sd_missing) != h_orig
    # additional tensor
    sd_extra = dict(model.state_dict()); sd_extra["extra"] = torch.zeros(1)
    assert mi.hash_state_dict(sd_extra) != h_orig
    # post-verification replacement -- hash changes, proving the one-time-measurement limitation
    with torch.no_grad():
        model.weight[0, 0] += 5.0
    assert mi.hash_state_dict(model.state_dict()) != h_orig
