
from assurance.compose import *
def test_default_is_conservative_union_bound():
    r=compose([FailureBound("tap",.01),FailureBound("server",.02)])
    assert r["method"]=="UNION_BOUND"; assert r["combined_failure_upper"]==.03
def test_product_requires_explicit_independence():
    r=compose([FailureBound("a",.01,True),FailureBound("b",.02,True)])
    assert r["method"]=="PRODUCT_WITH_CERTIFIED_INDEPENDENCE"; assert r["combined_failure_upper"]==.0002
def test_common_mode_blocks_product():
    r=compose([FailureBound("a",.01,True,"root"),FailureBound("b",.02,True,"root")])
    assert r["method"]=="UNION_BOUND"
