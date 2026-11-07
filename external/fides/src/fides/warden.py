"""
Side-channel warden -- addresses SITREP item 17 ("Side channel wardens":
scanning/observing side channels to detect covert communication, graded
not on track). This module does not mitigate side channels (that's item
16, physical shielding, genuinely out of software's reach); it detects
when a telemetry stream that should look like ordinary system noise
instead carries a statistically detectable injected signal -- the
signature of a covert channel encoding information onto a side channel
(power draw, EM emission, timing) that a network tap doesn't observe
directly.

Detection uses autocorrelation. Genuine thermal/electrical noise is close
to white noise: autocorrelation near zero at every nonzero lag. An
injected periodic signal -- the simplest, most bandwidth-efficient way to
encode bits onto an otherwise-unwatched channel -- produces a detectable
peak in the autocorrelation at the injection period, even at amplitudes
well below what's visible by eye in the raw signal. This is standard
signal-processing, not novel cryptography; the contribution here is
wiring it up as a tested detector with an empirically characterized
detection floor, not the underlying math.

Known limitation, now partially resolved: autocorrelation of a periodic
signal peaks at the true period AND at every integer multiple of it (its
harmonics), so `detect_periodic_signal`'s peak-picking can land on a
harmonic rather than the fundamental (see test_warden.py for the
original finding). `detect_fundamental_period` resolves this using the
signal's power spectrum instead of its autocorrelation: a sinusoid's
spectral energy sits at its actual frequency only, with no harmonic
content of its own to be confused with, unlike autocorrelation, which is
periodic by construction regardless of the underlying signal's shape.
This does NOT change the module's other, structural limitation: none of
this has been run against real power/EM/timing sensor data, only
synthetic signals, since that requires physical hardware access this
environment does not have.
"""

import math
import random


def generate_baseline_noise(n_samples: int, mean: float = 0.0, stdev: float = 1.0, seed: int = None) -> list:
    rng = random.Random(seed)
    return [rng.gauss(mean, stdev) for _ in range(n_samples)]


def inject_covert_signal(baseline: list, period: int, amplitude: float) -> list:
    """Adds a periodic component to an existing signal -- simulates a
    covert channel modulating a side channel at a fixed period."""
    return [x + amplitude * math.sin(2 * math.pi * i / period) for i, x in enumerate(baseline)]


def autocorrelation(signal: list, lag: int) -> float:
    n = len(signal)
    mean = sum(signal) / n
    centered = [x - mean for x in signal]
    variance = sum(x * x for x in centered) / n
    if variance == 0:
        return 0.0
    covariance = sum(centered[i] * centered[i + lag] for i in range(n - lag)) / (n - lag)
    return covariance / variance


def autocorrelation_spectrum(signal: list, max_lag: int) -> list:
    return [autocorrelation(signal, lag) for lag in range(1, max_lag + 1)]


def detect_periodic_signal(signal: list, max_lag: int, threshold: float = 0.15):
    """Returns (detected: bool, best_lag: int | None, peak_value: float)."""
    spectrum = autocorrelation_spectrum(signal, max_lag)
    peak_value = max(spectrum)
    peak_lag = spectrum.index(peak_value) + 1
    return (peak_value >= threshold, peak_lag if peak_value >= threshold else None, peak_value)


def power_spectrum(signal: list, max_freq_bins: int = None) -> list:
    """Direct O(n^2) DFT power spectrum. Deliberately not an FFT: at the
    sample sizes this module works with (thousands, not millions), the
    direct sum is fast enough and avoids the correctness risk of
    implementing FFT's bit-reversal and butterfly structure from
    scratch. Returns power at frequency bins 1..max_freq_bins (bin 0,
    DC/mean, is excluded since the signal is centered before transforming)."""
    n = len(signal)
    mean = sum(signal) / n
    centered = [x - mean for x in signal]
    max_freq_bins = max_freq_bins or n // 2
    power = []
    for k in range(1, max_freq_bins + 1):
        real = sum(centered[t] * math.cos(2 * math.pi * k * t / n) for t in range(n))
        imag = sum(centered[t] * math.sin(2 * math.pi * k * t / n) for t in range(n))
        power.append((real * real + imag * imag) / n)
    return power


def detect_fundamental_period(signal: list, threshold_ratio: float = 30.0):
    """Resolves the harmonic-ambiguity limitation documented above:
    autocorrelation of ANY periodic signal (even a pure sinusoid) is
    itself periodic with the same period, so its peaks recur at every
    integer multiple of the true period and a peak-picking detector can
    land on any of them. A pure sinusoid's *power spectrum*, in
    contrast, has essentially all its energy at its actual frequency --
    it has no harmonic content of its own to be confused with, which is
    a different mathematical fact from autocorrelation's periodicity.

    threshold_ratio=30 is not a guess: with ~n/2 bins being compared
    simultaneously, pure noise alone produces peak/median power ratios
    up to roughly 16 just from extreme-value statistics across that many
    comparisons (measured directly -- see the diagnostic in this
    module's git history), while an actual injected signal produces
    ratios in the hundreds. 30 sits with real margin on both sides of
    that gap. An earlier version of this function used threshold_ratio=4,
    which is far inside the noise-only range and produced false
    positives on 100% of clean-noise trials when tested -- caught by
    running test_warden.py, not by inspection.

    Returns the estimated fundamental period (in samples), or None if
    nothing stands clearly above the calibrated noise floor."""
    n = len(signal)
    spectrum = power_spectrum(signal, max_freq_bins=n // 2)
    sorted_spectrum = sorted(spectrum)
    noise_floor = sorted_spectrum[len(sorted_spectrum) // 2]  # median: robust to the true peak itself
    significant_bins = [k + 1 for k, p in enumerate(spectrum) if p > threshold_ratio * max(noise_floor, 1e-12)]
    if not significant_bins:
        return None
    fundamental_freq_bin = min(significant_bins)
    return round(n / fundamental_freq_bin)
