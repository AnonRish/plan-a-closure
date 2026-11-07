
from redteam.integrated import run_integrated_attacks

def test_whole_system_attacks_have_safe_outcomes():
    outcomes=run_integrated_attacks()
    assert len(outcomes)==9
    assert all(o.observed_status in {o.safe,"UNION_BOUND"} for o in outcomes)
