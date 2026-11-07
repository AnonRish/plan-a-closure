from input_warden.distribution import *
def test_commitment_roundtrip():
    c=commit_counts("p",{"a":3,"b":2},"fixed")
    assert verify_counts(c,{"b":2,"a":3})
def test_tampered_counts_fail():
    c=commit_counts("p",{"a":3},"fixed")
    assert not verify_counts(c,{"a":4})
def test_banned_distribution():
    assert classify_distribution({"INFERENCE":3,"TRAINING":1},frozenset({"INFERENCE"}),frozenset({"TRAINING"}),True)["status"]=="BANNED"
