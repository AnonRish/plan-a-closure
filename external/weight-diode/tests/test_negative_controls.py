"""Disable each security check in turn: the matching attack must then succeed. Guards the rejection tests against passing
for the wrong reason (for example a malformed forgery that never reached the check)."""
import random

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from weight_diode import Encoder, Receiver
from weight_diode import receiver as R
from weight_diode.format import HDR, SYM
from weight_diode.merkle import proof_length

KEY = Ed25519PrivateKey.generate()
DATA = bytes(range(256)) * 60
ENC = Encoder(DATA, KEY, symbol_size=128, k=10, r=6, serial=1)


def forged_packet(rng):
    b, j = 0, 3
    plen = proof_length(b * ENC.n + j, ENC.n_blocks * ENC.n)
    return HDR.pack(b"WDIO", 1, 1, 0, 0, ENC.manifest_id) + SYM.pack(b, j) + rng.randbytes(ENC.S) + rng.randbytes(32 * plen)


def test_without_the_proof_check_a_forged_symbol_is_accepted(monkeypatch):
    rx = Receiver([KEY.public_key()])
    rx.feed(ENC.manifest_packet)
    forged = forged_packet(random.Random(0))
    assert rx.feed(forged) == R.SYMBOL_BAD_PROOF                       # normal behaviour
    monkeypatch.setattr(R, "verify_inclusion", lambda *a, **k: True)
    rx2 = Receiver([KEY.public_key()])
    rx2.feed(ENC.manifest_packet)
    assert rx2.feed(forged) == R.SYMBOL_ACCEPTED                       # the forgery was well-formed: only the check stopped it


def test_without_the_signature_check_a_stranger_manifest_is_accepted(monkeypatch):
    stranger = Encoder(DATA[::-1], Ed25519PrivateKey.generate(), symbol_size=128, k=10, r=6)
    assert Receiver([KEY.public_key()]).feed(stranger.manifest_packet) == R.MANIFEST_SIGNATURE
    monkeypatch.setattr(R, "verify_manifest_signature", lambda *a, **k: True)
    assert Receiver([KEY.public_key()]).feed(stranger.manifest_packet) == R.MANIFEST_ACCEPTED


def test_without_a_whitelist_an_unapproved_file_is_accepted():
    other = Encoder(DATA[::-1], KEY, symbol_size=128, k=10, r=6)
    approved = ["00" * 32]
    assert Receiver([KEY.public_key()], whitelist=approved).feed(other.manifest_packet) == R.MANIFEST_WHITELIST
    assert Receiver([KEY.public_key()]).feed(other.manifest_packet) == R.MANIFEST_ACCEPTED


def test_without_min_serial_a_rolled_back_manifest_is_accepted():
    old = Encoder(DATA, KEY, symbol_size=128, k=10, r=6, serial=1)
    assert Receiver([KEY.public_key()], min_serial=2).feed(old.manifest_packet) == R.MANIFEST_SERIAL
    assert Receiver([KEY.public_key()], min_serial=0).feed(old.manifest_packet) == R.MANIFEST_ACCEPTED
