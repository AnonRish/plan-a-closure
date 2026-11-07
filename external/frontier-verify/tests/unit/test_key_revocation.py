"""Key revocation: distinct from rotation, with the specific semantic
the brief names explicitly -- 'receipt was valid when issued' vs 'receipt
remains trusted today.'
"""
from __future__ import annotations

import pytest

from frontier_verify.keys.kms_provider import CloudKmsKeyProvider, HsmKeyProvider, KmsKeyProvider
from frontier_verify.keys.local_provider import LocalFileKeyProvider, RevokedKeyError
from frontier_verify.keys.provider import KeyStatus


def test_freshly_rotated_key_is_active_and_old_one_is_rotated_not_revoked(tmp_path):
    provider = LocalFileKeyProvider(tmp_path)
    old_id = provider.current_key_id()
    new_id = provider.rotate()

    assert provider.key_status(new_id) == KeyStatus.ACTIVE
    assert provider.key_status(old_id) == KeyStatus.ROTATED  # NOT revoked -- routine hygiene only


def test_revoking_a_rotated_out_key_marks_it_revoked_not_active(tmp_path):
    provider = LocalFileKeyProvider(tmp_path)
    old_id = provider.current_key_id()
    provider.rotate()

    provider.revoke(old_id, reason="suspected compromise during incident #123")

    assert provider.key_status(old_id) == KeyStatus.REVOKED
    assert provider.revocation_reason(old_id) == "suspected compromise during incident #123"


def test_revoked_key_public_key_remains_retrievable(tmp_path):
    """Revocation must NOT make the key unrecoverable -- a verifier still
    needs to check whether an old receipt was genuinely signed by it, even
    though it's no longer trusted. Revocation changes trust, not
    checkability. See frontier_verify/keys/local_provider.py,
    get_public_key()'s docstring."""
    provider = LocalFileKeyProvider(tmp_path)
    key_id = provider.current_key_id()
    provider.revoke(key_id, reason="test")

    # Does not raise -- still retrievable.
    pk = provider.get_public_key(key_id)
    assert pk is not None


def test_revoked_current_key_refuses_to_sign_anything_new(tmp_path):
    """The critical safety property: a revoked key -- even if it's still
    technically 'current' because no one rotated after revoking -- must
    never be handed out for signing. Revoking without rotating is a
    dangerous state; get_signing_key() must not silently paper over it."""
    provider = LocalFileKeyProvider(tmp_path)
    current_id = provider.current_key_id()
    provider.revoke(current_id, reason="compromised")

    with pytest.raises(RevokedKeyError):
        provider.get_signing_key()  # implicitly uses the (revoked) current key

    with pytest.raises(RevokedKeyError):
        provider.get_signing_key(current_id)  # explicit key_id, same result


def test_rotating_after_revocation_produces_a_usable_new_signing_key(tmp_path):
    """The correct recovery sequence: revoke, THEN rotate. After that, the
    new key signs fine -- revocation of the OLD key doesn't somehow poison
    the provider going forward."""
    provider = LocalFileKeyProvider(tmp_path)
    old_id = provider.current_key_id()
    provider.revoke(old_id, reason="compromised")
    new_id = provider.rotate()

    key_id, _sk = provider.get_signing_key()
    assert key_id == new_id
    assert provider.key_status(new_id) == KeyStatus.ACTIVE


def test_revoking_unknown_key_id_raises_keyerror_not_silently_succeeding(tmp_path):
    provider = LocalFileKeyProvider(tmp_path)
    with pytest.raises(KeyError):
        provider.revoke("key-that-was-never-issued", reason="doesn't matter")


def test_status_of_unknown_key_id_raises_keyerror(tmp_path):
    provider = LocalFileKeyProvider(tmp_path)
    with pytest.raises(KeyError):
        provider.key_status("never-issued")


@pytest.mark.parametrize("cls", [HsmKeyProvider, KmsKeyProvider, CloudKmsKeyProvider])
def test_kms_stubs_are_still_honestly_not_implemented_for_revocation(cls):
    """Confirms adding revoke()/key_status() to the KeyProvider interface
    didn't accidentally make these classes instantiable-but-silently-
    working -- they must still raise, same as every other method."""
    provider = cls()  # this alone would raise TypeError if any abstract method were missing
    with pytest.raises(NotImplementedError):
        provider.revoke("some-key", reason="test")
    with pytest.raises(NotImplementedError):
        provider.key_status("some-key")


def test_private_key_file_permissions_are_restrictive(tmp_path):
    """Security review finding (Phase 3): write_text() alone left private
    keys world-readable (-rw-r--r--) under the default umask. This test
    would fail against the pre-fix code -- it's a regression test for a
    real finding, not a speculative check."""
    import stat

    provider = LocalFileKeyProvider(tmp_path)
    key_id = provider.current_key_id()
    sk_path = tmp_path / f"{key_id}.sk.hex"

    mode = stat.filemode(sk_path.stat().st_mode)
    assert mode == "-rw-------", f"private key file has overly permissive mode: {mode}"
