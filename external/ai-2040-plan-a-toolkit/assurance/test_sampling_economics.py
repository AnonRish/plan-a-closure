
import math
from assurance.sampling_economics import *

def test_plan_a_style_example():
    p=SamplingPlan(.01,100,.99,46000)
    r=compare_to_budget(p)
    assert math.isclose(r["required_verified_packets"],460.51701859880916,rel_tol=1e-10)
    assert r["meets_target"] is False
    assert r["achieved_confidence"]>0.989

def test_exact_finite_population_detection():
    p=exact_detection_probability(1000,10,100)
    assert 0<p<1
    assert p > 0.63

def test_exact_sampling_hits_one_when_sample_excludes_all_nonrogue():
    assert exact_detection_probability(10,5,6)==1.0

def test_minimum_exact_sample_is_monotone_and_valid():
    n=minimum_sample_for_exact_confidence(1000,10,.99)
    assert exact_detection_probability(1000,10,n)>=.99
    assert n==0 or exact_detection_probability(1000,10,n-1)<.99

def test_budget_equation_is_positive():
    p=SamplingPlan(.02,50,.95,0)
    assert p.required_rogue_compute()>0
