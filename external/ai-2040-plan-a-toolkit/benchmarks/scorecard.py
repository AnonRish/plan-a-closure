from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass(frozen=True)
class Metric:
    name: str
    value: float | None
    unit: str
    condition: str
    evidence_uri: str = ""

def make_scorecard(metrics: list[Metric], implementation: str = "RVP-1") -> dict:
    return {"schema_version": 1, "implementation": implementation, "metrics": [asdict(m) for m in metrics]}

def write_scorecard(path: str, metrics: list[Metric]):
    Path(path).write_text(json.dumps(make_scorecard(metrics), indent=2) + "\n", encoding="utf-8")
