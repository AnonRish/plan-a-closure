from assurance.statistical_bounds import *

def test_hypergeometric_exact_bounds():
    assert finite_population_detection_probability(100,10,0)==0.0
    assert finite_population_detection_probability(100,100,1)==1.0
    assert 0<finite_population_detection_probability(100,1,10)<1

def test_sample_size_hits_target():
    n=required_sample_size(1000,10,.95)
    assert finite_population_detection_probability(1000,10,n)>=.95
    assert n==258

def test_zero_failure_upper_decreases_with_more_samples():
    assert binomial_zero_failure_upper(100)<binomial_zero_failure_upper(10)

def test_cp_upper_is_valid():
    assert 0<clopper_pearson_upper(0,100)<.05
    assert clopper_pearson_upper(100,100)==1.0

def test_finite_population_rogue_upper_is_finite():
    assert finite_population_zero_failure_rogue_upper(1000,100,.95)<1000
