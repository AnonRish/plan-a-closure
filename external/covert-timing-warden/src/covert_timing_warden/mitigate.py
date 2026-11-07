"""Shielding-plus-noise mitigations, and what each can and cannot bound.

Model (worst case for the defender). A sender inside the cluster chooses an *extra delay* ``x in [0, D]`` before
each packet. A boundary device applies a mitigation to the release times and an observer sees the resulting
timestamps. Sender and observer share a clock, the sender knows the device's phase, and payload symbols are
uniform i.i.d. Every bound below is bits per packet under exactly this model, as a bracket
``[lower, upper]``: ``lower`` is achieved by an explicit scheme (see the ``lattice_*`` reference schemes, verified
by simulation), ``upper`` is proven. Neither end is claimed to be the capacity.

* :class:`QuantizedRelease` (release on a clock of period ``delta``): ``[log2(floor(D/delta)+1), log2(ceil(D/delta)+1)]``.
  The upper end counts the distinct tick increments one packet can produce and is at least 1 bit for any ``D > 0``:
  a sender that controls arrival phase can always straddle a tick boundary. Quantisation alone never removes
  the channel.
* :class:`UniformJitter` (independent ``U[0, w)`` added to each packet's release time, FIFO order kept):
  ``[log2(1 + floor(D/w)), log2(2 + D/w)]``. Upper end: ``I(X^n;Y^n) = h(Y^n) - n log2 w`` and
  ``h(Y^n) <= sum_i h(Y_i - Y_{i-1}) <= n log2(D + 2w)`` because ``Y_i - Y_{i-1} = X_i + N_i - N_{i-1}`` lies in an
  interval of length ``D + 2w``. FIFO release times are the running maximum of the unclamped ones, a deterministic
  function, so by data processing the bound covers FIFO devices too.
* :class:`FixedSchedule` (one packet per tick, dummies when idle): observable timing is a fixed function of
  elapsed time, so the timing channel carries 0 bits. Costs: latency, and bandwidth at all times. Assumes dummies
  are indistinguishable from real packets and the queue never overflows.

Why not just compute a per-inter-packet-delay capacity? Because jitter is added to *timestamps*, not to delays.
Successive delay-noises ``N_i - N_{i-1}`` are dependent, and a receiver with a shared clock decodes cumulative
timestamps, beating any per-delay memoryless bound: see ``examples/why_per_ipd_is_unsafe.py`` (20 to 36 % of the
leakage is missed at D/w between 1 and 8).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CapacityBound:
    mitigation: str
    lower_bits: float      # achieved by an explicit scheme
    upper_bits: float      # proven bound, same model
    assumptions: str


def _ratio(D: float, unit: float) -> float:
    if D < 0 or unit <= 0 or not math.isfinite(D) or not math.isfinite(unit):
        raise ValueError("need max extra delay >= 0 and a positive mitigation parameter")
    q = D / unit
    r = round(q)
    return float(r) if abs(q - r) <= 1e-9 * max(1.0, q) else q


def _sorted_arrivals(arrivals) -> np.ndarray:
    a = np.asarray(arrivals, dtype=float)
    if a.ndim != 1 or (a.size > 1 and np.any(np.diff(a) < 0)):
        raise ValueError("arrivals must be a 1-D non-decreasing array")
    return a


@dataclass(frozen=True)
class QuantizedRelease:
    delta: float

    def apply(self, timestamps) -> np.ndarray:
        """Release at the next tick, ``ceil(t / delta) * delta`` (arrivals on a tick go out on it)."""
        t = np.asarray(timestamps, dtype=float)
        return np.ceil(t / self.delta - 1e-9) * self.delta

    def capacity(self, max_extra_delay: float) -> CapacityBound:
        q = _ratio(max_extra_delay, self.delta)
        lo = math.log2(math.floor(q) + 1)
        hi = math.log2(math.ceil(q) + 1) if q > 0 else 0.0
        return CapacityBound("quantized release", lo, hi,
                             "sender controls arrival phase and knows the tick clock; upper end counts tick increments")

    @property
    def mean_added_latency(self) -> float:
        return self.delta / 2.0                    # arrival phase uniform within a tick


@dataclass(frozen=True)
class UniformJitter:
    width: float

    def apply(self, timestamps, rng: np.random.Generator) -> np.ndarray:
        """``t_i + U[0, width)`` per packet, then FIFO: the running maximum of the unclamped release times."""
        t = _sorted_arrivals(timestamps)
        return np.maximum.accumulate(t + self.width * rng.random(t.size))

    def capacity(self, max_extra_delay: float) -> CapacityBound:
        q = _ratio(max_extra_delay, self.width)
        return CapacityBound("uniform release jitter", math.log2(1 + math.floor(q)), math.log2(2 + q),
                             "independent per-packet jitter on timestamps; sender and receiver share a clock")

    @property
    def mean_added_latency(self) -> float:
        return self.width / 2.0                    # before the FIFO clamp, which only adds a little


@dataclass(frozen=True)
class FixedSchedule:
    period: float

    def release_times(self, arrivals) -> np.ndarray:
        """One real packet per tick, FIFO: tick_i = max(ceil(t_i / period), tick_{i-1} + 1)."""
        a = _sorted_arrivals(arrivals)
        c = np.ceil(a / self.period - 1e-9).astype(np.int64)
        idx = np.arange(a.size, dtype=np.int64)
        return (idx + np.maximum.accumulate(c - idx)) * self.period

    def observable(self, horizon: float) -> np.ndarray:
        """What the observer sees: a packet at every tick (real or dummy), whatever the arrivals were."""
        return np.arange(1, int(horizon / self.period + 1e-9) + 1) * self.period

    def latency(self, arrivals) -> np.ndarray:
        return self.release_times(arrivals) - _sorted_arrivals(arrivals)

    def is_stable(self, arrival_rate: float) -> bool:
        """The queue is stable only if real packets arrive slower than one per period."""
        return arrival_rate * self.period < 1.0

    def capacity(self, max_extra_delay: float = 0.0) -> CapacityBound:
        return CapacityBound("fixed schedule with padding", 0.0, 0.0,
                             "dummies indistinguishable from real packets; queue never overflows; packet sizes and counts out of model")


def exfiltration_seconds(secret_bits: float, bits_per_packet: float, packets_per_second: float, streams: int = 1) -> float:
    """Time to move ``secret_bits`` through a channel of ``bits_per_packet`` on ``streams`` parallel streams."""
    rate = bits_per_packet * packets_per_second * streams
    if secret_bits < 0 or rate < 0:
        raise ValueError("inputs must be non-negative")
    return math.inf if rate == 0 else secret_bits / rate


# --------------------------------------------------------------------------- #
# Reference schemes in exact integer time (nanoseconds): achievability, by simulation
# --------------------------------------------------------------------------- #
def lattice_roundtrip_jitter(symbols, spacing_ns: int, width_ns: int, rng: np.random.Generator) -> np.ndarray:
    """Send ``symbols`` (extra delays of ``k * spacing``) through per-packet ``U[0, width)`` FIFO jitter and decode.

    The receiver recovers ``floor(Y_i / spacing)``, the cumulative lattice index, from each absolute timestamp;
    this is exact whenever ``width <= spacing``. Returns the decoded symbols (equal to the input).
    """
    if width_ns > spacing_ns or spacing_ns <= 0 or width_ns < 0:
        raise ValueError("need 0 <= width <= spacing")
    s = np.asarray(symbols, dtype=np.int64)
    release_request = spacing_ns * np.cumsum(s)
    noise = rng.integers(0, max(int(width_ns), 1), size=s.size, dtype=np.int64)
    released = np.maximum.accumulate(release_request + noise)                   # FIFO
    k = released // spacing_ns
    return np.diff(np.concatenate([[0], k]))


def lattice_roundtrip_quantizer(symbols, delta_ns: int) -> np.ndarray:
    """Send ``symbols`` (extra delays of ``k * delta``, arrivals on ticks) through quantised release and decode."""
    if delta_ns <= 0:
        raise ValueError("delta must be positive")
    s = np.asarray(symbols, dtype=np.int64)
    arrivals = delta_ns * np.cumsum(s)
    released = -(-arrivals // delta_ns) * delta_ns                             # ceil to the tick
    k = released // delta_ns
    return np.diff(np.concatenate([[0], k]))
