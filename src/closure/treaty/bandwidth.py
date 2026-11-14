"""How much bandwidth between pods a training run needs, and what a cap on it costs: arithmetic for interconnect limits.

Scher and Thiergart's interconnect limits split a data centre into pods (about 128 chips in their example) joined by
links too thin to train across and wide enough to serve inference. Whether a given cap does that is arithmetic on
four numbers: how big the model is, how often the pods must exchange it, how many pods there are, and how many bytes
inference moves. This module does that arithmetic and states what it assumes. It measures nothing: the measured side
is traffic.py (bytes and flows out of a pcap against what served tokens can explain).

Assumptions, each one a parameter:
  * synchronous data-parallel training: every `sync_every` steps the pods exchange a full set of gradients or
    parameters (`params` values of `bytes_per_value` each, divided by `compression`);
  * the exchange is a ring all-reduce, in which each of P pods sends 2 (P - 1) / P times the payload per exchange
    (Patarasuk and Yuan 2009). Other schemes change the constant, not the scale;
  * a pod's uplink carries what that pod sends.
A run can cut its traffic by syncing less often or compressing harder, at a cost in steps to converge that this module
does not model; `sync_every` and `compression` are there so the reader can see how far those have to go.
"""
from __future__ import annotations

GBIT = 1e9 / 8.0          # bytes a second in one gigabit a second


def payload_bytes(params: float, bytes_per_value: float = 2.0, compression: float = 1.0) -> float:
    """Bytes one pod contributes to one exchange: params x bytes each / compression."""
    if params <= 0 or bytes_per_value <= 0 or compression <= 0:
        raise ValueError("params, bytes_per_value and compression must be positive")
    return float(params) * float(bytes_per_value) / float(compression)


def sent_per_exchange(payload: float, pods: int) -> float:
    """Bytes each pod sends in one ring all-reduce among `pods` pods: 2 (P - 1) / P x payload."""
    if int(pods) < 2:
        raise ValueError("an exchange needs at least two pods")
    return 2.0 * (int(pods) - 1) / int(pods) * float(payload)


def needed_gbps(params: float, steps_per_s: float, pods: int, sync_every: int = 1, bytes_per_value: float = 2.0,
                compression: float = 1.0) -> float:
    """Uplink each pod needs, in Gbit/s, to train across `pods` pods at `steps_per_s` without waiting on the link."""
    if steps_per_s <= 0 or int(sync_every) < 1:
        raise ValueError("steps_per_s must be positive and sync_every at least 1")
    per = sent_per_exchange(payload_bytes(params, bytes_per_value, compression), pods)
    return per * float(steps_per_s) / int(sync_every) / GBIT


def exchanges_per_s(cap_gbps: float, params: float, pods: int, bytes_per_value: float = 2.0,
                    compression: float = 1.0) -> float:
    """Exchanges a second a capped uplink allows."""
    if cap_gbps <= 0:
        return 0.0
    return float(cap_gbps) * GBIT / sent_per_exchange(payload_bytes(params, bytes_per_value, compression), pods)


def slowdown(cap_gbps: float, params: float, steps_per_s: float, pods: int, sync_every: int = 1,
             bytes_per_value: float = 2.0, compression: float = 1.0) -> float:
    """How many times slower the run goes when the link, not the chips, sets the pace: needed / cap, at least 1.
    Infinite for a cap of zero."""
    need = needed_gbps(params, steps_per_s, pods, sync_every, bytes_per_value, compression)
    return float("inf") if cap_gbps <= 0 else max(1.0, need / float(cap_gbps))


def inference_gbps(tokens_per_s: float, bytes_per_token: float = 16.0) -> float:
    """Uplink that serving needs: tokens a second x bytes a token on the wire, both ways and with framing folded into
    `bytes_per_token` (traffic.py measures the real figure for a deployment)."""
    return float(tokens_per_s) * float(bytes_per_token) / GBIT


def assess(cap_gbps: float, params: float, steps_per_s: float, pods: int, tokens_per_s: float, sync_every: int = 1,
           bytes_per_value: float = 2.0, compression: float = 1.0, bytes_per_token: float = 16.0) -> dict:
    """One cap, read both ways: what it does to training across pods and what room it leaves serving."""
    need = needed_gbps(params, steps_per_s, pods, sync_every, bytes_per_value, compression)
    serve = inference_gbps(tokens_per_s, bytes_per_token)
    return {"cap_gbps": float(cap_gbps), "training_needs_gbps": need, "inference_needs_gbps": serve,
            "training_slowdown": slowdown(cap_gbps, params, steps_per_s, pods, sync_every, bytes_per_value, compression),
            "inference_fits": bool(serve <= cap_gbps),
            "cap_separates_them": bool(serve <= cap_gbps < need),
            "headroom_between_them": need / serve if serve > 0 else float("inf"),
            "assumptions": {"pods": int(pods), "sync_every": int(sync_every), "bytes_per_value": float(bytes_per_value),
                            "compression": float(compression), "bytes_per_token": float(bytes_per_token),
                            "exchange": "ring all-reduce: each pod sends 2 (P - 1) / P x the payload"}}
