
from telemetry.consistency import *
def test_matching_intervals_are_consistent():
    c=TelemetryClaim(Interval(90,110),Interval(95,100),Interval(100,120),Interval(105,115))
    assert consistency(c)["status"]=="CONSISTENT"
def test_disjoint_power_interval_is_flagged():
    c=TelemetryClaim(Interval(90,110),Interval(95,100),Interval(100,120),Interval(140,150))
    assert consistency(c)["status"]=="INCONSISTENT"
