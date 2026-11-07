from track3.ownership_graph import *

def p(i,o,q,e=True): return Position(i,'L1',o,q,1,(i,) if e else ())

def test_double_entry_reconciles():
    r=reconcile([p('s','A',10)],[Transfer('t','L1','A','B',6,2,('t',))],[p('e1','A',4),p('e2','B',6)],[],True)
    assert r['status']=='PASS'

def test_missing_evidence_is_unknown():
    r=reconcile([p('s','A',10,False)],[],[p('e','A',10)],[],True)
    assert r['status']=='UNKNOWN'

def test_unbalanced_inventory_fails():
    r=reconcile([p('s','A',10)],[],[p('e','A',9)],[],True)
    assert r['status']=='FAIL'

def test_cycles_are_not_false_positives():
    r=trace_lot('L1',[Transfer('1','L1','A','B',1,1),Transfer('2','L1','B','A',1,2)],{'A'},[])
    assert r['status']=='PASS'
