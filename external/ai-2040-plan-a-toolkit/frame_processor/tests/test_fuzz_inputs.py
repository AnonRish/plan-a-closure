
import random
from frame_processor.processor import Whitelist, process_frame

W=Whitelist("02:00:00:00:00:01","02:00:00:00:00:02","10.0.0.1","10.0.0.2")

def test_malformed_frames_never_escape_parser():
    rng=random.Random(20260928)
    for _ in range(500):
        frame=bytes(rng.randrange(256) for _ in range(rng.randrange(0,300)))
        event=process_frame(frame,W,"fuzz",123)
        assert event.classification
