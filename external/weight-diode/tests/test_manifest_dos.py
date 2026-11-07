"""A corrupted copy of a manifest must never poison the genuine one."""
import os

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from weight_diode import Encoder, Receiver
from weight_diode import receiver as R

KEY = Ed25519PrivateKey.generate()
DATA = os.urandom(5000)


def test_bad_signature_copy_first_does_not_block_the_good_copy():
    enc = Encoder(DATA, KEY, symbol_size=64, k=8, r=4)
    good = enc.manifest_packet
    bad = good[:-1] + bytes([good[-1] ^ 1])              # same manifest bytes, same id, one flipped signature bit
    rx = Receiver([KEY.public_key()])
    assert rx.feed(bad) == R.MANIFEST_SIGNATURE
    assert rx.feed(good) == R.MANIFEST_ACCEPTED           # the genuine manifest must still be accepted


def test_repeated_bad_signature_copies_then_a_full_transfer_completes():
    enc = Encoder(DATA, KEY, symbol_size=64, k=8, r=4)
    good = enc.manifest_packet
    bad = good[:-1] + bytes([good[-1] ^ 1])
    rx = Receiver([KEY.public_key()])
    for _ in range(50):
        assert rx.feed(bad) == R.MANIFEST_SIGNATURE or rx.feed(bad) == R.MANIFEST_DUPLICATE
    for pkt in enc.stream(passes=1):
        rx.feed(pkt)
    assert rx.result(enc.manifest_id) == DATA
