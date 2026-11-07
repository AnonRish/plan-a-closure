"""Schema-level conformance: what happens at the edges. A future
independent implementation reading these tests should be able to infer
the required behavior without reading frontier_verify's source.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from frontier_verify.evidence.models import (
    Evidence,
    HardwareEvidence,
    ModelIdentity,
    RuntimeIdentity,
)
from frontier_verify.receipts.models import Receipt


def test_evidence_missing_required_field_is_rejected():
    """model_identity is required. A conformant implementation must
    reject evidence missing it, not default it to something."""
    with pytest.raises(ValidationError):
        Evidence.model_validate(
            {
                "evidence_id": "e1",
                "runtime_identity": {"serving_engine": "x"},
                "hardware_evidence": {"provider_name": "mock", "maturity": "MOCK", "mock": True},
            }
        )


def test_hardware_evidence_rejects_unknown_maturity_value():
    """maturity must be one of the fixed Maturity vocabulary -- this is
    deliberate closed-world design (docs/ai2040-coverage-matrix.md's
    status legend), not an oversight; a value outside that set must fail
    validation, not be silently accepted as a string."""
    with pytest.raises(ValidationError):
        HardwareEvidence.model_validate(
            {"provider_name": "mock", "maturity": "SUPER_DUPER_VALIDATED", "mock": True}
        )


def test_evidence_silently_ignores_genuinely_unknown_optional_fields():
    """Forward-compatibility decision, made explicit and tested rather
    than left as an accidental pydantic default: an OLDER verifier
    receiving evidence with a NEWER field it doesn't recognize should not
    crash. Unknown fields are dropped, not rejected. If this behavior
    ever needs to change (e.g. to reject unknown fields strictly for a
    higher-assurance profile), this test is what should change with it."""
    data = {
        "evidence_id": "e1",
        "model_identity": {"model_digest": "d1"},
        "runtime_identity": {"serving_engine": "x"},
        "hardware_evidence": {"provider_name": "mock", "maturity": "MOCK", "mock": True},
        "a_field_from_some_future_schema_version": {"nested": "data"},
    }
    ev = Evidence.model_validate(data)
    assert ev.model_identity.model_digest == "d1"
    assert not hasattr(ev, "a_field_from_some_future_schema_version")


def test_receipt_carries_an_explicit_version_field():
    """A conformant receipt reader needs a version field to know how to
    parse the rest of the document -- confirm it's present and has the
    expected default, not merely that *a* string exists somewhere."""
    r = Receipt(
        verification_id="v1",
        verifier_key_id="k1",
        model_identity_digest="m1",
        runtime_identity_digest="r1",
        hardware_evidence_digest="h1",
        policy_id="p1",
        policy_version="0.1.0",
        assurance_level="L1",
        result=True,
    )
    assert r.receipt_version == "0.1.0"


def test_model_identity_digest_is_order_independent_of_construction():
    """Two ModelIdentity objects built with kwargs in different order
    must produce the same digest -- exercising the schema layer, not just
    the canonicalization layer directly (tests/unit/test_canonical.py
    already covers that in isolation)."""
    a = ModelIdentity(model_digest="d1", name="model-a", version="1.0")
    b = ModelIdentity(version="1.0", name="model-a", model_digest="d1")
    assert a.digest() == b.digest()


def test_runtime_identity_all_fields_optional_still_produces_stable_digest():
    a = RuntimeIdentity()
    b = RuntimeIdentity()
    assert a.digest() == b.digest()
