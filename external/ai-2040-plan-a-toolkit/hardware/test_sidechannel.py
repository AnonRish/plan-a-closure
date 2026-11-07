from hardware.sidechannel import estimate_binary_mutual_information
def test_constant_signal_has_zero_empirical_leakage():
    r=estimate_binary_mutual_information([1,1,1,1],[0,1,0,1])
    assert r.mutual_information_bits==0.0
