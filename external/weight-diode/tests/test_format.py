import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from weight_diode import format as F

KEY = Ed25519PrivateKey.generate()
GOOD = dict(v=1, serial=4, label="llama-x", file_size=100_000, file_sha256="ab" * 32, symbol_size=1000, k=10, r=4,
            n_blocks=10, root="cd" * 32)


def manifest(**over):
    d = dict(GOOD, **over)
    return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()


def test_round_trip_is_canonical_and_id_is_stable():
    m = F.Manifest.from_bytes(manifest())
    assert m.to_bytes() == manifest()
    assert m.n == 14 and m.tree_size == 140
    assert m.manifest_id == F.Manifest.from_bytes(manifest()).manifest_id and len(m.manifest_id) == 8
    assert F.Manifest.from_bytes(manifest(serial=5)).manifest_id != m.manifest_id


@pytest.mark.parametrize("over", [
    dict(k=0), dict(k=200, r=57), dict(r=-1), dict(symbol_size=0), dict(symbol_size=60_001), dict(serial=-1),
    dict(file_size=-1), dict(n_blocks=9), dict(n_blocks=11), dict(v=2),
    dict(file_sha256="AB" * 32), dict(file_sha256="ab" * 31), dict(root="zz" * 32), dict(label="x" * 65),
    dict(label="bad\nlabel"), dict(serial=True), dict(k=10.0), dict(k="10"), dict(label=5),
])
def test_manifest_validation_rejects(over):
    with pytest.raises(F.FormatError):
        F.Manifest.from_bytes(manifest(**over))


@pytest.mark.parametrize("raw", [b"", b"not json", b"[]", b"null", b'{"v":1}',
                                 manifest()[:-1] + b',"extra":1}', b"\xff\xfe", json.dumps({**GOOD, "extra": 1}).encode()])
def test_manifest_structure_errors(raw):
    with pytest.raises(F.FormatError):
        F.Manifest.from_bytes(raw)


def test_blocks_for_boundaries():
    assert F.Manifest.blocks_for(0, 10, 1000) == 1
    assert F.Manifest.blocks_for(10_000, 10, 1000) == 1
    assert F.Manifest.blocks_for(10_001, 10, 1000) == 2


def test_signature_accepts_only_the_right_key_and_bytes_and_domain():
    mb = manifest()
    sig = F.sign_manifest(mb, KEY)
    assert F.verify_manifest_signature(mb, sig, [KEY.public_key()])
    other = Ed25519PrivateKey.generate().public_key()
    assert not F.verify_manifest_signature(mb, sig, [other])
    assert F.verify_manifest_signature(mb, sig, [other, KEY.public_key()])
    assert not F.verify_manifest_signature(mb + b" ", sig, [KEY.public_key()])
    assert not F.verify_manifest_signature(mb, sig[:-1] + bytes([sig[-1] ^ 1]), [KEY.public_key()])
    assert not F.verify_manifest_signature(mb, b"", [KEY.public_key()])
    raw_sig = KEY.sign(mb)                                                    # signed WITHOUT the domain prefix
    assert not F.verify_manifest_signature(mb, raw_sig, [KEY.public_key()])


def test_manifest_packet_round_trip_and_limits():
    mb = manifest()
    pkt = F.pack_manifest_packet(mb, F.sign_manifest(mb, KEY))
    typ, mid, body = F.parse_header(pkt)
    assert typ == F.T_MANIFEST
    mp = F.parse_manifest_packet(mid, body)
    assert mp.manifest_bytes == mb and len(mp.signature) == 64
    with pytest.raises(F.FormatError):
        F.pack_manifest_packet(b"x" * 2000, b"s" * 64)
    with pytest.raises(F.FormatError):
        F.pack_manifest_packet(mb, b"short")
    with pytest.raises(F.FormatError):
        F.parse_manifest_packet(mid, body[:-1])
    with pytest.raises(F.FormatError):
        F.parse_manifest_packet(mid, body + b"z")


def test_header_and_symbol_parsing_errors():
    m = F.Manifest.from_bytes(manifest())
    for bad in (b"", b"x" * 15, b"NOPE" + bytes(12), F.HDR.pack(b"WDIO", 2, 1, 0, 0, bytes(8))):
        with pytest.raises(F.FormatError):
            F.parse_header(bad)
    body = b"\x00" * 3
    with pytest.raises(F.FormatError):
        F.parse_symbol_packet(bytes(8), body, m)
    import struct
    with pytest.raises(F.FormatError):                                         # block out of range
        F.parse_symbol_packet(bytes(8), struct.pack(">IH", 10, 0) + bytes(1000 + 32 * 8), m)
    with pytest.raises(F.FormatError):                                         # index out of range
        F.parse_symbol_packet(bytes(8), struct.pack(">IH", 0, 14) + bytes(1000 + 32 * 8), m)
    with pytest.raises(F.FormatError):                                         # wrong length
        F.parse_symbol_packet(bytes(8), struct.pack(">IH", 0, 0) + bytes(999), m)
