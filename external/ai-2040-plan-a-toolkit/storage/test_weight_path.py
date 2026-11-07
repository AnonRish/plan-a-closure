
from storage.weight_path import *
def test_weight_path_requires_diode():
    t=WeightTransfer("bank","inference","abc","WEIGHT_ONLY",True,False)
    assert validate_weight_path(t)["status"]=="UNKNOWN"
def test_weight_path_passes_when_all_controls_exist():
    t=WeightTransfer("bank","inference","abc","WEIGHT_ONLY",True,True)
    assert validate_weight_path(t)["status"]=="PASS"
