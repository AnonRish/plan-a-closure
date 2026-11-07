
from redteam.scenarios import catalog
def test_attack_catalog_is_explicit():
    x=catalog(); assert len(x)>=10; assert all("expected_control" in a for a in x)
