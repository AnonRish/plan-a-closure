"""Generic residual closure: predict a scalar (energy, busy-time, ...) from *verified* work
features, calibrate the null distribution of block-summed residuals, then audit new blocks.

Hidden work adds to the observed total but not to the verified features, so it shows up as a
positive residual. The hidden-quantity upper bound is S_obs - q_low (valid under additivity and
exchangeability of calibration and audit blocks; see README for the assumptions).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .conformal import (jarque_bera_p, lower_conformal_quantile, t_upper,
                        upper_conformal_quantile)


def nnls(X, y, max_iter: int = 20000, tol: float = 1e-12) -> np.ndarray:
    """Non-negative least squares by projected Gauss-Seidel on column-scaled normal equations."""
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    scale = np.linalg.norm(X, axis=0)
    scale[scale == 0] = 1.0
    Z = X / scale
    G, b = Z.T @ Z, Z.T @ y
    th = np.zeros(Z.shape[1])
    for _ in range(max_iter):
        old = th.copy()
        for j in range(len(th)):
            gj = G[j, j]
            if gj > 0:
                th[j] = max(0.0, (b[j] - G[j] @ th + gj * th[j]) / gj)
        if np.max(np.abs(th - old)) <= tol * (1 + np.max(np.abs(th))):
            break
    return th / scale


def to_blocks(X, y, L: int):
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    B = len(y) // L
    return X[: B * L].reshape(B, L, -1), y[: B * L].reshape(B, L)


@dataclass
class Calibration:
    channel: str
    names: list
    theta: np.ndarray
    L: int
    edges: np.ndarray
    mu: np.ndarray
    sd: np.ndarray
    null: list
    normal_p: np.ndarray
    unit: str = ""
    n_eff: np.ndarray = None
    rho: float = 0.0

    @property
    def n_regimes(self) -> int:
        return len(self.mu)

    def to_dict(self) -> dict:
        return {"channel": self.channel, "names": list(self.names), "theta": self.theta.tolist(),
                "L": self.L, "edges": self.edges.tolist(), "mu": self.mu.tolist(),
                "sd": self.sd.tolist(), "n_cal_blocks": [len(a) for a in self.null],
                "normal_p": self.normal_p.tolist(), "unit": self.unit,
                "n_eff": (None if self.n_eff is None else self.n_eff.tolist()), "rho": self.rho}


def fit(X, y, L: int, n_regimes: int = 3, folds: int = 5, seed: int = 0,
        channel: str = "energy_j", names=None, unit: str = "J", min_cal_per_regime: int = 30) -> Calibration:
    """Cross-fitted calibration: every reference block yields one out-of-fold residual sum, so all
    data serve both to fit the model and to estimate the null distribution (CV+ style)."""
    Xb, yb = to_blocks(X, y, L)
    B, k = len(yb), Xb.shape[2]
    rng = np.random.default_rng(seed)
    fold = np.empty(B, int)
    fold[rng.permutation(B)] = np.arange(B) % folds
    pb, S = np.empty(B), np.empty(B)
    for f in range(folds):
        tr, te = fold != f, fold == f
        th = nnls(Xb[tr].reshape(-1, k), yb[tr].reshape(-1))
        pb[te] = (Xb[te] @ th).sum(1)
        S[te] = yb[te].sum(1) - pb[te]
    theta = nnls(Xb.reshape(-1, k), yb.reshape(-1))
    edges = (np.quantile(pb, np.linspace(0, 1, n_regimes + 1)[1:-1]) if n_regimes > 1 else np.array([]))
    reg = np.searchsorted(edges, pb, side="right")
    mu, sd, null, npv = [], [], [], []
    for r in range(n_regimes):
        a = S[reg == r]
        if len(a) < min_cal_per_regime:
            raise ValueError(f"regime {r} has only {len(a)} calibration blocks (< {min_cal_per_regime}); "
                             "collect more reference data or lower n_regimes")
        mu.append(float(a.mean()))
        sd.append(float(a.std(ddof=1)))
        null.append(a)
        npv.append(jarque_bera_p(a))
    # temporal dependence (thermal / clock drift) shrinks the effective calibration sample size
    s0 = S - np.array(mu)[reg]
    den = float(np.sum(s0 * s0))
    rho = float(np.clip(np.sum(s0[:-1] * s0[1:]) / den, 0.0, 0.99)) if den > 0 and B > 2 else 0.0
    n_eff = np.array([max(3.0, len(a) * (1 - rho) / (1 + rho)) for a in null])
    return Calibration(channel, list(names) if names is not None else [f"x{i}" for i in range(k)],
                       theta, L, np.asarray(edges, float), np.array(mu), np.array(sd), null,
                       np.array(npv), unit, n_eff, rho)


def threshold(cal: Calibration, r: int, alpha: float, method: str = "auto"):
    """Return (flag threshold, lower noise quantile, method actually used)."""
    n = float(cal.n_eff[r]) if cal.n_eff is not None else float(len(cal.null[r]))
    # predictive (future-observation) interval with the *effective* number of independent blocks
    half = t_upper(alpha, n - 1.0) * cal.sd[r] * math.sqrt(1.0 + 1.0 / n)
    tg, qg = cal.mu[r] + half, cal.mu[r] - half
    can_conf = alpha * (n + 1.0) >= 1.0          # conformal needs enough *independent* calibration blocks
    tc = upper_conformal_quantile(cal.null[r], alpha) if can_conf else math.inf
    qc = lower_conformal_quantile(cal.null[r], alpha) if can_conf else -math.inf
    if method == "gaussian":
        return tg, qg, "gaussian"
    if method == "conformal":
        return tc, qc, "conformal"
    if math.isfinite(tc) and math.isfinite(qc):
        return tc, qc, "conformal"
    return tg, qg, "gaussian"


@dataclass
class AuditResult:
    S: np.ndarray
    pred: np.ndarray
    regime: np.ndarray
    thr: np.ndarray
    flagged: np.ndarray
    hidden_ub: np.ndarray
    method: list = field(default_factory=list)


def audit(cal: Calibration, X, y, alpha: float = 1e-3, method: str = "auto") -> AuditResult:
    Xb, yb = to_blocks(X, y, cal.L)
    pb = (Xb @ cal.theta).sum(1)
    S = yb.sum(1) - pb
    reg = np.searchsorted(cal.edges, pb, side="right")
    thr = np.empty(len(S))
    qlow = np.empty(len(S))
    used = []
    for r in range(cal.n_regimes):
        t, q, m = threshold(cal, r, alpha, method)
        thr[reg == r], qlow[reg == r] = t, q
        used.append(m)
    return AuditResult(S, pb, reg, thr, S > thr, np.maximum(0.0, S - qlow), used)


def detection_power(cal: Calibration, regime: int, hidden, alpha: float = 1e-3,
                    method: str = "auto") -> np.ndarray:
    t, _, _ = threshold(cal, regime, alpha, method)
    return np.array([float(np.mean(cal.null[regime] + h > t)) for h in np.atleast_1d(hidden)])


def min_detectable(cal: Calibration, regime: int, alpha: float = 1e-3, beta: float = 0.05,
                   method: str = "auto") -> float:
    """Smallest additive hidden amount per block detected with probability >= 1 - beta."""
    t, _, _ = threshold(cal, regime, alpha, method)
    return float(max(0.0, t - np.quantile(cal.null[regime], beta)))
