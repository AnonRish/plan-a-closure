"""Content-addressed storage: identity is the digest, and corruption after
the fact must be detected on read, not silently served."""
from __future__ import annotations

import pytest

from frontier_verify.storage.content_addressed import ContentAddressedStore, IntegrityError


def test_put_then_get_roundtrips(tmp_path):
    cas = ContentAddressedStore(tmp_path)
    digest = cas.put({"a": 1, "b": [1, 2, 3]})
    assert cas.get(digest) == {"a": 1, "b": [1, 2, 3]}


def test_identical_content_produces_identical_digest_regardless_of_key_order(tmp_path):
    cas = ContentAddressedStore(tmp_path)
    d1 = cas.put({"z": 1, "a": 2})
    d2 = cas.put({"a": 2, "z": 1})
    assert d1 == d2


def test_missing_digest_raises_keyerror(tmp_path):
    cas = ContentAddressedStore(tmp_path)
    with pytest.raises(KeyError):
        cas.get("0" * 64)


def test_corrupted_stored_bytes_are_detected_on_read(tmp_path):
    """The property this test exists for: moving/copying/re-serving
    evidence between storage systems is safe (docs/architecture.md,
    'Evidence Portability') ONLY IF corruption or tampering after storage
    is actually caught. This test corrupts the file on disk directly,
    bypassing the store's own put() -- simulating a storage-layer
    compromise, not an application bug."""
    cas = ContentAddressedStore(tmp_path)
    digest = cas.put({"important": "evidence"})

    path = cas._path_for(digest)
    path.write_bytes(b'{"important":"TAMPERED"}')

    with pytest.raises(IntegrityError):
        cas.get(digest)


def test_exists_reflects_reality(tmp_path):
    cas = ContentAddressedStore(tmp_path)
    digest = cas.put({"x": 1})
    assert cas.exists(digest) is True
    assert cas.exists("0" * 64) is False


def test_malformed_digest_is_rejected_defensively(tmp_path):
    """Security review finding (Phase 3): no current caller passes an
    attacker-controlled digest directly to _path_for(), but validating
    the shape is cheap defense-in-depth. A path-traversal-shaped input
    must raise ValueError, not silently construct a path outside
    base_dir."""
    cas = ContentAddressedStore(tmp_path)
    with pytest.raises(ValueError):
        cas.get("../../../etc/passwd")
    with pytest.raises(ValueError):
        cas.get("not-even-hex-shaped")
    with pytest.raises(ValueError):
        cas.get("a" * 63)  # one character short of a real sha256 hex digest
