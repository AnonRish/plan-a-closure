
from __future__ import annotations
import json
from pathlib import Path

def compare(published:dict, observed:dict)->dict:
    return {
        "published_source":published.get("source"),
        "published":published.get("measurements",{}),
        "observed":observed,
        "same_metric_names":set(published.get("measurements",{})).issuperset(observed),
        "warning":"Comparison is meaningful only when workload, hardware, traffic pattern and measurement method are matched."
    }

def load(path:str):return json.loads(Path(path).read_text(encoding="utf-8"))
