"""The link analysis (pre-registration amendment v0.6): a calibrated curve from verified work to each channel, and one
distribution-free threshold.

Why. The first analysis predicted a window's energy and busy time as a straight line in the verified work. On real
GPUs neither is a straight line: a GPU near its power limit lowers its clocks, so power flattens while work keeps
rising, and with unlocked clocks the time and energy a unit of work takes depend on the clock the load put the GPU on.
Kaggle run 5 showed the cost (docs/DEVIATIONS.md section 5): at one load level the GPU drew 4 to 5 W more than the
straight line, half the null blocks at that level were false alarms (11 of 22, none elsewhere), and most of the
block-to-block spread was misfit, not noise.

What. For each channel (energy, busy time):
  1. a work index per window, w = the linear model's prediction from the work features alone;
  2. a monotone piecewise-linear curve of the rate w / duration, fitted by non-negative least squares on K equal
     segments (more work never predicts less energy or less busy time);
  3. block residual sums, each divided by the spread the curve's own window residuals predict for that block's mix
     of load (a studentised score), cross-fitted over the reference blocks so every reference block is scored by a
     curve that never saw it.
The combined score of a block is the larger of its two channel scores, each in units of its reference spread. A block
is flagged when that exceeds the conformal quantile of the reference blocks' combined scores: no distribution is
assumed. With interleaved calibration the reference blocks sit at random positions among the audit blocks (one in each
equal stretch of the run), so reference and null audit blocks are drawn from the same sequence by design and a drift
reaches both alike. That needs at least 1/alpha - 1 reference blocks (99 at alpha = 0.01); with fewer, or with
sequential calibration and too few effective blocks, a Student-t threshold is used and labelled as such.

How exact the level is. A conformal threshold holds its level exactly when the reference scores and a null audit score
are exchangeable. Two things here are close to that and not identical to it. A reference block is scored by a curve
fitted on four fifths of the reference blocks, an audit block by the curve fitted on all of them (cross-conformal: the
proven worst case is 2 alpha, Vovk 2015, Barber et al. 2021; here the held-out curves have slightly more error, which
errs towards fewer alarms). And the reference positions are stratified, not a simple random sample (which makes them
more representative, not less). The level is therefore checked, not assumed: by simulation on drifting sequences
(tests/test_link.py) and, on every run, by H1.2 itself.

Only verified quantities enter the curve (work features and durations). Nothing the device reports about itself
(power, utilisation, temperature, clocks) is a regressor, because hidden work moves all of those.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .conformal import jarque_bera_p, lower_conformal_quantile, t_upper, upper_conformal_quantile
from .residual import nnls

K_SEGMENTS = 20          # segments of the curve between zero and the top work rate seen in calibration
TOP_QUANTILE = 0.995     # the last knot; faster windows extend the last segment
MIN_SEG_WINDOWS = 30     # a segment with fewer calibration windows borrows the pooled residual variance
SMOOTH = 1e-3            # pull of neighbouring slopes towards each other, relative to the data (see Curve.fit). On run
                         # 5's data anything from 0 to 1e-2 gives the same detections and false alarms within one


def nnls_exact(A, b) -> np.ndarray:
    """Non-negative least squares by the Lawson-Hanson active-set method on the normal equations."""
    A, b = np.asarray(A, float), np.asarray(b, float)
    n = A.shape[1]
    scale = np.linalg.norm(A, axis=0)
    scale[scale == 0] = 1.0
    Z = A / scale
    G, h = Z.T @ Z, Z.T @ b
    x, P, tried = np.zeros(n), np.zeros(n, bool), np.zeros(n, bool)
    tol = 1e-10 * max(1.0, float(np.abs(h).max()))
    for _ in range(10 * n + 10):
        w = h - G @ x
        w[P | tried] = -np.inf
        j = int(np.argmax(w))
        if w[j] <= tol:
            return x / scale
        P[j] = True
        for _ in range(10 * n + 10):
            s = np.zeros(n)
            s[P] = np.linalg.lstsq(G[np.ix_(P, P)], h[P], rcond=None)[0]
            if s[P].min() > 0:
                break
            neg = P & (s <= 0)
            step = float(np.min(x[neg] / np.maximum(x[neg] - s[neg], 1e-300)))
            x = x + step * (s - x)
            P &= x > 1e-14 * max(1.0, float(x.max()))
            x[~P] = 0.0
            if not P.any():
                s = np.zeros(n)
                break
        tried = (tried | ~P) if not P[j] else np.zeros(n, bool)   # a column thrown straight back out is not retried
        tried[j] = not P[j]
        x = s
    return nnls(A, b)                                    # did not settle (never seen): the slow solver always does


def _rate(dur, w):
    return np.divide(w, dur, out=np.zeros(len(w)), where=np.asarray(dur) > 0)


def _phi(dur, w, knots):
    r = _rate(dur, w)
    edges = np.concatenate([[0.0], knots, [np.inf]])
    return np.column_stack([dur] + [np.clip(r - a, 0.0, b - a) * dur for a, b in zip(edges[:-1], edges[1:])])


@dataclass
class Curve:
    """One channel's calibrated curve: y = duration x (c0 + f(work index / duration)), f monotone piecewise linear."""
    theta1: np.ndarray            # the linear model; its work part defines the index
    knots: np.ndarray
    coef: np.ndarray              # c0, then one non-negative slope per segment
    seg_var: np.ndarray           # window residual variance by segment

    @staticmethod
    def fit(X, y, K: int = K_SEGMENTS) -> "Curve":
        X, y = np.asarray(X, float), np.asarray(y, float)
        theta1 = nnls_exact(X, y)
        dur, w = X[:, 0], X[:, 1:] @ theta1[1:]
        top = float(np.quantile(_rate(dur, w), TOP_QUANTILE)) if len(w) else 0.0
        knots = np.linspace(0.0, top, K + 1)[1:] if top > 0 else np.array([])
        Phi = _phi(dur, w, knots)
        n_slopes = Phi.shape[1] - 1
        if n_slopes >= 2:
            # A segment no calibration window falls in has no slope of its own: only the rise across a gap between
            # two load levels is known. A faint pull of each slope towards its neighbour (SMOOTH of the data's weight)
            # leaves measured slopes where they are and lets the slope change evenly across a gap, from the slope
            # below it to the slope above it, instead of a step wherever the solver happened to put it. Hidden work
            # that displaces verified work lands exactly in such gaps.
            lam = SMOOTH * float(np.mean(np.sum(Phi[:, 1:] ** 2, axis=0)))
            D = np.zeros((n_slopes - 1, n_slopes + 1))
            for j in range(n_slopes - 1):
                D[j, 1 + j], D[j, 2 + j] = -1.0, 1.0
            coef = nnls_exact(np.vstack([Phi, math.sqrt(lam) * D]), np.concatenate([y, np.zeros(n_slopes - 1)]))
        else:
            coef = nnls_exact(Phi, y)
        c = Curve(theta1, knots, coef, np.ones(len(knots) + 1))
        r = y - c.predict(X)
        seg, pooled = c.segment(X), float(np.mean(r * r)) if len(r) else 1.0
        c.seg_var = np.array([float(np.mean(r[seg == j] ** 2)) if (seg == j).sum() >= MIN_SEG_WINDOWS else pooled
                              for j in range(len(knots) + 1)])
        c.seg_var = np.maximum(c.seg_var, 1e-12 * max(pooled, 1e-300))
        return c

    def index(self, X):
        X = np.asarray(X, float)
        return X[:, 0], X[:, 1:] @ self.theta1[1:]

    def predict(self, X):
        dur, w = self.index(X)
        return _phi(dur, w, self.knots) @ self.coef

    def segment(self, X):
        dur, w = self.index(X)
        return np.searchsorted(self.knots, _rate(dur, w), side="left")

    def blocks(self, X, y, L: int):
        """Per block: residual sum, the spread the curve predicts for it, and the predicted total."""
        n = (len(y) // L) * L
        X, y = np.asarray(X, float)[:n], np.asarray(y, float)[:n]
        pred = self.predict(X)
        return ((y - pred).reshape(-1, L).sum(1), np.sqrt(self.seg_var[self.segment(X)].reshape(-1, L).sum(1)),
                pred.reshape(-1, L).sum(1))

    def floor_blocks(self, X, L: int):
        """Per block, the least this channel can be for the verified work: the zero-work level plus the work index
        times the curve's smallest average slope (its most efficient point). The calibrated curve says what the work
        usually costs at that load; this says what it must cost at least, so an amount above it is unexplained even
        if hidden work moved the GPU to a more efficient operating point (assumption A1 not needed)."""
        dur, w = self.index(X)
        n = (len(w) // L) * L
        slope = 0.0
        if len(self.knots):
            r = np.linspace(0.0, float(self.knots[-1]), 201)[1:]
            f = _phi(np.ones_like(r), r, self.knots) @ self.coef
            slope = float(np.min((f - self.coef[0]) / r))
        return (dur[:n] * self.coef[0] + slope * w[:n]).reshape(-1, L).sum(1)

    def partial_load_slack(self) -> float:
        """How much less energy the curve's most efficient point needs for the same work, at worst, as a fraction of
        what the curve predicts: 1 - chord(idle to top) / curve. Zero for a straight line. A GPU whose power flattens
        near its limit is cheaper per unit of work when full, so an operator who keeps it full has this much energy
        to spare against the calibration (an efficiency slack the probe's variants do not measure)."""
        if not len(self.knots):
            return 0.0
        r = np.linspace(0.0, float(self.knots[-1]), 201)
        f = _phi(np.ones_like(r), r, self.knots) @ self.coef
        chord = f[0] + (f[-1] - f[0]) * r / r[-1]
        return float(np.max(1.0 - chord[1:] / np.maximum(f[1:], 1e-300)))

    def to_dict(self) -> dict:
        return {"theta1": self.theta1.tolist(), "knots": self.knots.tolist(), "coef": self.coef.tolist(),
                "segment_variance": self.seg_var.tolist()}


@dataclass
class Channel:
    name: str
    unit: str
    curve: Curve                  # fitted on every reference block; scores the audit
    S: np.ndarray                 # cross-fitted residual sums of the reference blocks
    G: np.ndarray                 # their predicted spreads
    scale: float                  # standard deviation of S / G over the reference blocks
    rho: float
    normal_p: float

    @property
    def z(self):
        return self.S / self.G


@dataclass
class LinkCalibration:
    L: int
    energy: Channel
    busy: Channel
    score: np.ndarray             # reference blocks' combined scores
    exchangeable_by_design: bool  # interleaved calibration
    rho: float
    n_eff: float                  # reference blocks, discounted for autocorrelation unless exchangeable by design

    @property
    def channels(self):
        return (self.energy, self.busy)

    def to_dict(self) -> dict:
        return {"analysis": "link", "L": self.L, "n_reference_blocks": int(len(self.score)), "n_eff": self.n_eff,
                "rho": self.rho, "exchangeable_by_design": self.exchangeable_by_design,
                "channels": {c.name: {"unit": c.unit, "curve": c.curve.to_dict(), "scale": c.scale, "rho": c.rho,
                                      "normal_p": c.normal_p,
                                      "block_residual_sd": float(np.std(c.S, ddof=1))} for c in self.channels}}


def _rho1(v) -> float:
    s = np.asarray(v, float) - np.mean(v)
    den = float(np.sum(s * s))
    return float(np.clip(np.sum(s[:-1] * s[1:]) / den, -0.99, 0.99)) if den > 0 and len(s) > 2 else 0.0


def calibrate(X, ys: dict, L: int, folds: int = 5, seed: int = 0, exchangeable_by_design: bool = False,
              K: int = K_SEGMENTS) -> LinkCalibration:
    """ys: {"energy": per-window joules, "busy": per-window busy seconds} for the reference windows X."""
    X = np.asarray(X, float)
    B = len(X) // L
    if B < 2 * folds:
        raise ValueError(f"{B} reference blocks are too few to cross-fit ({folds} folds)")
    Xb = X[: B * L].reshape(B, L, -1)
    fold = np.empty(B, int)
    fold[np.random.default_rng(seed).permutation(B)] = np.arange(B) % folds
    chans = {}
    for name, unit in (("energy", "J"), ("busy", "s")):
        yb = np.asarray(ys[name], float)[: B * L].reshape(B, L)
        S, G = np.empty(B), np.empty(B)
        for f in range(folds):
            tr, te = fold != f, fold == f
            c = Curve.fit(Xb[tr].reshape(-1, Xb.shape[2]), yb[tr].ravel(), K)
            S[te], G[te], _ = c.blocks(Xb[te].reshape(-1, Xb.shape[2]), yb[te].ravel(), L)
        z = S / G
        sd = float(np.std(z, ddof=1))
        chans[name] = Channel(name, unit, Curve.fit(Xb.reshape(-1, Xb.shape[2]), yb.ravel(), K), S, G,
                              sd if sd > 0 else 1.0, _rho1(z), float(jarque_bera_p(z)))
    e, b = chans["energy"], chans["busy"]
    score = np.maximum(e.z / e.scale, b.z / b.scale)
    rho = _rho1(score)
    n_eff = float(B) if exchangeable_by_design else max(3.0, B * (1 - max(rho, 0.0)) / (1 + max(rho, 0.0)))
    return LinkCalibration(L, e, b, score, bool(exchangeable_by_design), rho, n_eff)


def _upper(null, alpha: float, n_rule: float):
    """(threshold, method): conformal when there are enough reference blocks for this alpha, else Student-t."""
    null = np.asarray(null, float)
    if alpha * (n_rule + 1.0) >= 1.0:
        t = upper_conformal_quantile(null, alpha)
        if math.isfinite(t):
            return float(t), "conformal"
    return (float(null.mean() + t_upper(alpha, n_rule - 1.0) * null.std(ddof=1) * math.sqrt(1.0 + 1.0 / n_rule)),
            "student-t (too few reference blocks for a distribution-free threshold)")


def _lower(null, alpha: float, n_rule: float) -> float:
    null = np.asarray(null, float)
    if alpha * (n_rule + 1.0) >= 1.0:
        q = lower_conformal_quantile(null, alpha)
        if math.isfinite(q):
            return float(q)
    return float(null.mean() - t_upper(alpha, n_rule - 1.0) * null.std(ddof=1) * math.sqrt(1.0 + 1.0 / n_rule))


def audit(cal: LinkCalibration, X, ys: dict, alpha: float) -> dict:
    """Score audit windows. Returns, per block: each channel's flag at alpha, the combined flag at alpha, each
    channel's residual and upper bound on what is unexplained, and the predicted energy."""
    out = {"flag": {}, "resid": {}, "ub": {}, "ub_floor": {}, "z": {}, "method": {}, "threshold": {}}
    comb = None
    for c in cal.channels:
        S, G, pred = c.curve.blocks(X, ys[c.name], cal.L)
        z = S / G
        thr, how = _upper(c.z, alpha, cal.n_eff)
        out["flag"][c.name], out["z"][c.name], out["resid"][c.name] = z > thr, z, S
        # The flag is studentised by the spread at the block's own (verified) load. A bound has to hold when hidden
        # work has moved the GPU to a different load, possibly a noisier one, so its margin uses the largest spread
        # anywhere on the curve.
        margin = -_lower(c.z, alpha, cal.n_eff) * math.sqrt(cal.L * float(c.curve.seg_var.max()))
        out["ub"][c.name] = np.maximum(0.0, S + margin)
        out["ub_floor"][c.name] = np.maximum(0.0, S + pred - c.curve.floor_blocks(X, cal.L) + margin)
        out["method"][c.name], out["threshold"][c.name] = how, thr
        comb = z / c.scale if comb is None else np.maximum(comb, z / c.scale)
        if c.name == "energy":
            out["pred_energy"] = pred
    thr, how = _upper(cal.score, alpha, cal.n_eff)
    out["flag"]["combined"], out["score"] = comb > thr, comb
    out["method"]["combined"], out["threshold"]["combined"] = how, thr
    return out


def min_detectable(cal: LinkCalibration, name: str, alpha: float, beta: float) -> float:
    """Smallest amount added to a typical block (median predicted spread) that this channel alone flags with
    probability >= 1 - beta, in the channel's unit."""
    c = getattr(cal, name)
    thr, _ = _upper(c.z, alpha, cal.n_eff)
    return float(max(0.0, thr - np.quantile(c.z, beta)) * np.median(c.G))
