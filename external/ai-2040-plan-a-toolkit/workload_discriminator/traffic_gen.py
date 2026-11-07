"""
traffic_gen.py

Generates synthetic network-telemetry sessions with the qualitative
signatures that distinguish distributed training from inference serving --
NOT captured from real clusters (I have no access to that), but built from
the actual mechanics of each workload type:

TRAINING (data/model-parallel): gradient synchronization (AllReduce) fires
on a regular cadence set by step time. Each sync is roughly symmetric --
every worker sends about what it receives -- and roughly the same size
step over step, since it's the same model's gradients every time.

INFERENCE (serving): requests arrive on an irregular, externally-driven
schedule. Each exchange is asymmetric -- a short prompt upload, a much
larger streamed completion download -- and sizes vary a lot request to
request depending on what's being asked.

A third generator, generate_adversarial_regular_inference_session, builds
inference traffic (asymmetric bytes) on a deliberately REGULAR schedule --
e.g. a load-testing script hitting an API at fixed intervals -- specifically
to stress-test whether a classifier is actually using more than just timing
regularity.
"""

from dataclasses import dataclass
import numpy as np


@dataclass
class Session:
    label: str  # 'training' or 'inference'
    timestamps: np.ndarray
    bytes_sent: np.ndarray
    bytes_received: np.ndarray


def generate_training_session(rng, duration_s=None, step_interval_s=None, step_jitter=None,
                               gradient_bytes_mean=None, gradient_bytes_cv=0.08):
    duration_s = duration_s or rng.uniform(3600, 48 * 3600)
    step_interval_s = step_interval_s or rng.uniform(0.5, 6.0)
    step_jitter = step_jitter if step_jitter is not None else rng.uniform(0.03, 0.15)
    gradient_bytes_mean = gradient_bytes_mean or np.exp(rng.uniform(np.log(5e6), np.log(2e9)))

    n_steps = max(8, int(duration_s / step_interval_s))
    intervals = np.clip(rng.normal(step_interval_s, step_interval_s * step_jitter, n_steps), step_interval_s * 0.5, None)
    timestamps = np.cumsum(intervals)

    burst = rng.lognormal(mean=np.log(gradient_bytes_mean), sigma=gradient_bytes_cv, size=n_steps)
    sent = np.clip(burst * rng.normal(1.0, 0.03, n_steps), 1, None)
    received = np.clip(burst * rng.normal(1.0, 0.03, n_steps), 1, None)
    return Session('training', timestamps, sent, received)


def generate_inference_session(rng, duration_s=None, mean_request_rate_hz=None, burstiness=None,
                                prompt_bytes_mean=None, completion_ratio_mean=None):
    duration_s = duration_s or rng.uniform(1800, 24 * 3600)
    mean_request_rate_hz = mean_request_rate_hz or rng.uniform(0.05, 5.0)
    burstiness = burstiness if burstiness is not None else rng.uniform(1.2, 4.0)
    n_events = max(8, int(duration_s * mean_request_rate_hz))

    shape = 1.0 / burstiness  # < 1 => heavier-tailed gaps than a plain Poisson process => burstier
    scale = (1.0 / mean_request_rate_hz) / shape
    intervals = rng.gamma(shape, scale, n_events)
    timestamps = np.cumsum(intervals)

    prompt_bytes_mean = prompt_bytes_mean or np.exp(rng.uniform(np.log(200), np.log(4000)))
    completion_ratio_mean = completion_ratio_mean or rng.uniform(3, 20)

    sent = np.clip(rng.lognormal(mean=np.log(prompt_bytes_mean), sigma=0.5, size=n_events), 1, None)
    ratio = rng.lognormal(mean=np.log(completion_ratio_mean), sigma=0.4, size=n_events)
    received = np.clip(sent * ratio, 1, None)
    return Session('inference', timestamps, sent, received)


def generate_adversarial_regular_inference_session(rng, duration_s=None, request_interval_s=None, jitter=None,
                                                     prompt_bytes_mean=None, completion_ratio_mean=None):
    """Inference traffic (asymmetric bytes) deliberately shaped onto a training-like regular clock."""
    duration_s = duration_s or rng.uniform(1800, 24 * 3600)
    request_interval_s = request_interval_s or rng.uniform(0.5, 6.0)
    jitter = jitter if jitter is not None else rng.uniform(0.03, 0.15)
    n_events = max(8, int(duration_s / request_interval_s))
    intervals = np.clip(rng.normal(request_interval_s, request_interval_s * jitter, n_events), request_interval_s * 0.5, None)
    timestamps = np.cumsum(intervals)

    prompt_bytes_mean = prompt_bytes_mean or np.exp(rng.uniform(np.log(200), np.log(4000)))
    completion_ratio_mean = completion_ratio_mean or rng.uniform(3, 20)
    sent = np.clip(rng.lognormal(mean=np.log(prompt_bytes_mean), sigma=0.5, size=n_events), 1, None)
    ratio = rng.lognormal(mean=np.log(completion_ratio_mean), sigma=0.4, size=n_events)
    received = np.clip(sent * ratio, 1, None)
    return Session('inference', timestamps, sent, received)
