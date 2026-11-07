
def test_live_capture_module_imports():
    from hardware.live_capture import CaptureStats
    assert CaptureStats(0,0,0).frames==0
