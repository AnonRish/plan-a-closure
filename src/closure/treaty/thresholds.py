"""Compute thresholds the proposals name, and how fast compute that verification cannot see reaches them.

Training compute [FLOP] = computing power [FLOP/s] x time [s] (A Narrow Path, p. 52). The trial measures how much
energy can hide below detection (the closure gap, a share of capacity); the probe measures the fewest joules a FLOP can
cost on the device (the energy floor). Hidden FLOP/s <= gap x capacity / floor, so the time a fleet needs to run a
threshold-sized training run in secret follows from two measured numbers and the fleet size.
"""
from __future__ import annotations

from dataclasses import dataclass

DAY_S = 86400.0
H100_SXM_W = 700.0


@dataclass(frozen=True)
class Threshold:
    key: str
    value: float
    unit: str          # "FLOP" (total training compute) or "FLOP/s" (computing power)
    what: str
    source: str


THRESHOLDS = {t.key: t for t in (
    Threshold("np-training-licence", 1e25, "FLOP", "Training Licence needed before a run above this",
              "A Narrow Path (ControlAI 2024), pp. 30, 33"),
    Threshold("np-compute-licence", 1e17, "FLOP/s", "Compute Licence needed for a data centre above this",
              "A Narrow Path, pp. 30, 36"),
    Threshold("beijing-draft", 1e26, "FLOP", "Beijing's draft training-compute threshold, as cited",
              "CBPAI, The Deal of the Century (cbpai.org)"),
    Threshold("miri-accounting-example", 1e25, "FLOP", "illustrative threshold for compute accounting",
              "Scher and Thiergart 2024, compute accounting"),
)}


def run_flop(chips: float, peak_flop_per_s: float, utilization: float, seconds: float) -> float:
    """Training compute of a run: chips x peak x utilization x time."""
    return float(chips) * float(peak_flop_per_s) * float(utilization) * float(seconds)


def seconds_to(threshold_flop: float, flop_per_s: float) -> float:
    """Seconds a computing power needs to accumulate a threshold (inf if it is zero)."""
    return float("inf") if flop_per_s <= 0 else float(threshold_flop) / float(flop_per_s)


def licences_needed(training_flop: float = None, facility_flop_per_s: float = None) -> list:
    """Which of A Narrow Path's Phase 0 licences a run or a facility needs (strictly above the threshold)."""
    out = []
    if training_flop is not None and training_flop > THRESHOLDS["np-training-licence"].value:
        out.append("Training Licence")
    if facility_flop_per_s is not None and facility_flop_per_s > THRESHOLDS["np-compute-licence"].value:
        out.append("Compute Licence")
    return out


def narrow_path_regime_ratio_s(training_flop: float, computing_flop_per_s: float) -> float:
    """Seconds the largest permitted run takes at the permitted computing power. A Narrow Path says such runs 'could be
    run as quickly as within 12 days' in each limit regime (p. 52), which needs this ratio near 1e6 s; the Phase 0
    licence pair (1e25 FLOP, 1e17 FLOP/s) gives 1e8 s (3.2 years), so the 12 days refers to the Phase 1 limits."""
    return float(training_flop) / float(computing_flop_per_s)


def hidden_flop_per_s(gap_fraction: float, n_gpu: float, p_max_w: float, e_floor_j_per_flop: float) -> float:
    """Upper bound on hidden FLOP/s when a share gap_fraction of capacity energy can hide: gap x n x p_max / floor."""
    return float(gap_fraction) * float(n_gpu) * float(p_max_w) / float(e_floor_j_per_flop)


@dataclass(frozen=True)
class CovertRun:
    threshold_flop: float
    gap_fraction: float
    fleet_gpus: float
    p_max_w: float
    e_floor_j_per_flop: float
    hidden_flop_per_s: float
    days: float
    source: str

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def covert_days(threshold_flop: float, gap_fraction: float, fleet_gpus: float, p_max_w: float = H100_SXM_W,
                e_floor_j_per_flop: float = 0.5e-12, source: str = "given") -> CovertRun:
    """Days a fleet needs to run a threshold-sized training run with compute that stays below detection.

    It assumes the hidden work can be pooled into one run. It cannot without moving gradients between GPUs, which the
    traffic closure (traffic.py) and interconnect limits (Scher and Thiergart's 'pods') bound separately, so the result
    is a lower bound on the time a covert run needs: the energy alone does not rule it out sooner."""
    r = hidden_flop_per_s(gap_fraction, fleet_gpus, p_max_w, e_floor_j_per_flop)
    return CovertRun(float(threshold_flop), float(gap_fraction), float(fleet_gpus), float(p_max_w),
                     float(e_floor_j_per_flop), r, seconds_to(threshold_flop, r) / DAY_S, source)


def covert_days_from_trial(results: dict, cfg: dict, threshold_flop: float, fleet_gpus: float,
                           use_slack: bool = True) -> CovertRun:
    """covert_days with the gap and floor a trial measured (results.json) and the capacity it ran at (prereg cfg).

    The slack-inflated gap is used when the probe measured slack (H1.6), since an adversary on a more efficient stack
    hides that much more. Raises if the trial measured no gap (too few blocks, or detection never reached 95%)."""
    gap = results.get("closure_gap_fraction")
    sl = (results.get("slack") or {}).get("slack_inflated_gap_fraction")
    src = "closure gap"
    if use_slack and sl is not None:
        gap, src = sl, "slack-inflated closure gap"
    if gap is None:
        raise ValueError("the trial measured no closure gap: no hidden-load intensity was detected 95% of the time")
    floor = (results.get("hidden_compute_at_gap_per_week") or {}).get("energy_floor_j_per_flop")
    if not floor:
        raise ValueError("results.json has no energy floor")
    fsrc = (results.get("hidden_compute_at_gap_per_week") or {}).get("energy_floor_source", "?")
    return covert_days(threshold_flop, gap, fleet_gpus, cfg.get("p_max_w", H100_SXM_W), floor,
                       f"{src} from the trial ({results.get('status')}); energy floor: {fsrc}")
