from verification_lab.workstream_matrix import build_matrix

def test_all_17_workstreams_present():
    r=build_matrix(); assert r['count']==17; assert [x['id'] for x in r['entries']]==list(range(1,18))

def test_external_gates_are_explicit():
    r=build_matrix(); assert all(x['required_real_evidence'] for x in r['entries']); assert r['unresolved_workstreams']
