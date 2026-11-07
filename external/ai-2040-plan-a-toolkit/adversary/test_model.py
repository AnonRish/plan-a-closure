from adversary.model import coverage_report,default_attack_catalog,evaluate_observed

def test_catalog_is_covered():
    r=coverage_report(); assert r['status']=='PASS'; assert r['attack_count']>=12

def test_pass_is_never_safe():
    for attack in default_attack_catalog(): assert evaluate_observed(attack,'PASS')['safe'] is False

def test_investigate_is_safe_terminal_class():
    assert evaluate_observed(default_attack_catalog()[10],'INVESTIGATE')['safe'] is True
