from .reference_model import *

def test_pass_requires_evidence():
    s=State(); commit(s,'root'); challenge(s,'c')
    try: check(s,'PASS',())
    except ValueError: pass
    else: raise AssertionError('PASS without evidence must be rejected')

def test_normal_lifecycle():
    s=State(); commit(s,'root'); challenge(s,'c'); check(s,'PASS',('sample',)); terminalize(s)
    assert not safety_invariants(s)
