from hardware.nvidia_smi import *
def test_parser():
    x=parse_nvidia_smi("GPU-1,250.5,80,4096\nGPU-2,100.0,10,2048\n")
    assert len(x)==2 and x[0].power_w==250.5
def test_malformed_rows_are_ignored():
    assert len(parse_nvidia_smi("bad\nGPU-1,not-a-number,5,4\n"))==0
