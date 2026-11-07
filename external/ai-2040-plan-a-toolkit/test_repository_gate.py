from repository_gate import validate_repository

def test_repository_gate():
    r=validate_repository('.')
    assert r['status']=='PASS', r['errors']
