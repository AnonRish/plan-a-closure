import json

import numpy as np
import pytest

from closure import evidence as E


def test_chain_detects_tampering_and_truncation(tmp_path):
    c = E.Chain(tmp_path / "c.jsonl")
    for i in range(5):
        c.append({"i": i, "x": float("inf") if i == 2 else i})
    ok, n, head = E.Chain.verify(tmp_path / "c.jsonl")
    assert ok and n == 5 and head == c.head
    lines = (tmp_path / "c.jsonl").read_text().splitlines()
    bad = json.loads(lines[1]); bad["record"]["i"] = 99
    (tmp_path / "t.jsonl").write_text("\n".join([lines[0], json.dumps(bad)] + lines[2:]) + "\n")
    assert not E.Chain.verify(tmp_path / "t.jsonl")[0]
    (tmp_path / "g.jsonl").write_text("\n".join([lines[0]] + lines[2:]) + "\n")        # deleted entry
    assert not E.Chain.verify(tmp_path / "g.jsonl")[0]
    assert E.Chain(tmp_path / "c.jsonl").n == 5                                      # resumes correctly


def test_signature_roundtrip_and_failure(tmp_path):
    s = E.Signer()
    s.save(tmp_path / "k")
    s2 = E.Signer.load(tmp_path / "k")
    assert s2.public_hex() == s.public_hex()
    sig = s.sign_hex(b"head")
    assert E.verify_sig(s.public_hex(), sig, b"head")
    assert not E.verify_sig(s.public_hex(), sig, b"other")
    assert not E.verify_sig(E.Signer().public_hex(), sig, b"head")


def test_commit_reveal_binds_the_schedule():
    sched = [None, {"kind": "constant", "frac": 0.05}]
    c = E.commit(sched)
    assert E.verify_commit(sched, c["commitment"], c["nonce"])
    assert not E.verify_commit([None, {"kind": "constant", "frac": 0.10}], c["commitment"], c["nonce"])
    assert not E.verify_commit(sched, c["commitment"], "00" * 16)


def test_clean_makes_nonfinite_and_numpy_json_safe():
    out = E.clean({"a": np.float64("nan"), "b": np.array([1, 2]), "c": np.int64(3), "d": float("inf")})
    assert out == {"a": None, "b": [1, 2], "c": 3, "d": None}
    json.dumps(out, allow_nan=False)


def test_array_digest_depends_on_content_dtype_shape():
    a = np.arange(6, dtype=np.float64)
    assert E.array_digest(a) == E.array_digest(a.copy())
    assert E.array_digest(a) != E.array_digest(a.reshape(2, 3))
    assert E.array_digest(a) != E.array_digest(a.astype(np.float32))
