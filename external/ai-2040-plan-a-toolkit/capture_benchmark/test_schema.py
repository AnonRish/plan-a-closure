import json
from pathlib import Path
from jsonschema import validate

def test_capture_result_schema_accepts_fixture():
    schema=json.loads(Path("capture_benchmark/schema.json").read_text(encoding="utf-8"))
    validate({"schema_version":1,"benchmark":"software_capture_replay","config":{},"expected_frames":1,"observed_frames":1,"hardware_observation":False,
              "line_rate_projections":[{"line_rate_gbps":100,"measured":False,"theoretical_frames_per_second":1},
                                      {"line_rate_gbps":400,"measured":False,"theoretical_frames_per_second":1},
                                      {"line_rate_gbps":800,"measured":False,"theoretical_frames_per_second":1},
                                      {"line_rate_gbps":1600,"measured":False,"theoretical_frames_per_second":1}]},schema)
