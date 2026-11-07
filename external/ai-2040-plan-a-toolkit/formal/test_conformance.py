from formal.conformance import bounded_state_conformance,execute

def test_illegal_order_is_rejected_without_breaking_invariants():
    r=execute(('check','terminalize','commit','challenge'))
    assert r['status']=='PASS'
    assert r['accepted']==['commit','challenge']

def test_bounded_state_conformance():
    r=bounded_state_conformance(4)
    assert r['status']=='PASS'
    assert r['checked_sequences']>100
