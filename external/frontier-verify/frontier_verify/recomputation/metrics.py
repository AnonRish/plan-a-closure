
from __future__ import annotations
from dataclasses import dataclass
from time import perf_counter_ns
from typing import Callable, TypeVar

T=TypeVar("T")

@dataclass(frozen=True)
class Measurement:
    value:T
    elapsed_ns:int

def measure(fn:Callable[[],T])->Measurement[T]:
    start=perf_counter_ns()
    value=fn()
    return Measurement(value,perf_counter_ns()-start)

def sampled_work(total_units:int,sampled_units:int)->dict:
    if total_units<0 or sampled_units<0 or sampled_units>total_units:
        raise ValueError("invalid workload counts")
    return {
        "total_units":total_units,
        "sampled_units":sampled_units,
        "coverage_fraction":sampled_units/total_units if total_units else 0.0,
    }
