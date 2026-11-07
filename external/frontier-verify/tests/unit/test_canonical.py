from frontier_verify.core.canonical import canonicalize, digest


def test_key_order_does_not_affect_digest():
    assert digest({"b": 1, "a": 2}) == digest({"a": 2, "b": 1})


def test_nested_key_order_does_not_affect_digest():
    a = {"outer": {"z": 1, "a": 2}, "list": [1, 2, 3]}
    b = {"list": [1, 2, 3], "outer": {"a": 2, "z": 1}}
    assert digest(a) == digest(b)


def test_different_content_different_digest():
    assert digest({"a": 1}) != digest({"a": 2})


def test_canonicalize_is_deterministic_bytes():
    obj = {"x": [1, 2, 3], "y": "hello"}
    assert canonicalize(obj) == canonicalize(obj)


def test_canonicalize_has_no_insignificant_whitespace():
    assert canonicalize({"a": 1, "b": 2}) == b'{"a":1,"b":2}'
