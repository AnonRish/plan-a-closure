import math

import numpy as np
import pytest
from scipy import stats

import assurance_curves as ac
from assurance_curves import BernoulliMixtureEProcess, e_bh, first_alarm_step, log_e_from_counts, log_e_paths


@pytest.mark.parametrize("p0", [0.01, 0.3, 0.8])
@pytest.mark.parametrize("n", [1, 2, 5, 12, 40])
def test_e_process_is_an_exact_martingale_under_the_null(p0, n):
    """E_H0[E_n] = 1 exactly: sum over every possible count, weighted by its binomial probability."""
    k = np.arange(n + 1)
    e = np.exp(log_e_from_counts(n, k, p0, n_grid=16))
    total = float(np.sum(stats.binom.pmf(k, n, p0) * e))
    assert total == pytest.approx(1.0, abs=1e-9)


def test_martingale_property_conditional_one_step():
    """Given any history, E[E_{t+1} | history] = E_t."""
    p0 = 0.05
    for k in (0, 1, 3, 9):
        n = 40
        base = BernoulliMixtureEProcess(p0, n_grid=32).update(n=n, k=k).e_value
        up = BernoulliMixtureEProcess(p0, n_grid=32).update(n=n + 1, k=k + 1).e_value
        down = BernoulliMixtureEProcess(p0, n_grid=32).update(n=n + 1, k=k).e_value
        assert p0 * up + (1 - p0) * down == pytest.approx(base, rel=1e-9)


def test_update_forms_agree():
    rng = np.random.default_rng(3)
    flags = rng.random(500) < 0.03
    a = BernoulliMixtureEProcess(0.01)
    for f in flags:
        a.update([f])
    b = BernoulliMixtureEProcess(0.01).update(flags)
    c = BernoulliMixtureEProcess(0.01).update(n=flags.size, k=int(flags.sum()))
    assert a.log_e == pytest.approx(b.log_e, abs=1e-9) == pytest.approx(c.log_e, abs=1e-9)
    path = log_e_paths(flags[None, :], 0.01)
    assert path[0, -1] == pytest.approx(a.log_e, abs=1e-9)


def test_time_uniform_type_one_error_is_controlled():
    """Ville: P(ever E_t >= 1/alpha) <= alpha, checked at every one of 1,000 steps."""
    rng = np.random.default_rng(2026)
    S, T, p0, alpha = 3000, 1000, 0.01, 0.05
    flags = rng.random((S, T)) < p0
    hits = first_alarm_step(log_e_paths(flags, p0, n_grid=48), alpha) >= 0
    rate = hits.mean()
    assert rate <= alpha + 4 * math.sqrt(alpha * (1 - alpha) / S)


def test_naive_peeking_inflates_error_but_the_e_process_does_not():
    """Same null data. A z-test looked at after every packet blows through alpha."""
    rng = np.random.default_rng(99)
    S, T, p0, alpha = 3000, 1000, 0.01, 0.05
    flags = rng.random((S, T)) < p0
    t = np.arange(1, T + 1)
    z = (np.cumsum(flags, axis=1) - t * p0) / np.sqrt(t * p0 * (1 - p0))
    naive = (z[:, 49:] > stats.norm.isf(alpha)).any(axis=1).mean()
    ours = (first_alarm_step(log_e_paths(flags, p0, n_grid=48), alpha) >= 0).mean()
    assert naive > 3 * alpha
    assert ours < alpha + 0.02


def test_power_against_a_five_times_higher_flag_rate():
    rng = np.random.default_rng(5)
    S, T, p0, p1, alpha = 1500, 1000, 0.01, 0.05, 0.05
    flags = rng.random((S, T)) < p1
    step = first_alarm_step(log_e_paths(flags, p0, n_grid=48), alpha)
    assert (step >= 0).mean() > 0.95
    med = np.median(step[step >= 0])
    assert 40 < med < 400    # KL(p1||p0) ~ 0.041 nats/packet => a few hundred packets at most


def test_rejects_interface_and_input_errors():
    with pytest.raises(ValueError):
        BernoulliMixtureEProcess(0.0)
    with pytest.raises(ValueError):
        BernoulliMixtureEProcess(1.0)
    p = BernoulliMixtureEProcess(0.1)
    with pytest.raises(ValueError):
        p.update(n=3, k=4)
    with pytest.raises(ValueError):
        p.update()
    with pytest.raises(ValueError):
        p.rejects(1.5)


def test_evidence_only_accumulates_when_flags_exceed_the_null_rate():
    p = BernoulliMixtureEProcess(0.05).update(n=2000, k=100)    # exactly the null rate
    assert p.e_value < 5
    q = BernoulliMixtureEProcess(0.05).update(n=2000, k=400)    # 4x the null rate
    assert q.rejects(1e-6)


def test_e_bh_worked_example():
    # m = 5, alpha = 0.1 -> thresholds m/(alpha k) = 50, 25, 16.7, 12.5, 10
    rej = e_bh([1, 100, 0.5, 50, 10], 0.1)
    assert rej.tolist() == [False, True, False, True, False]
    assert e_bh([], 0.1).size == 0
    assert not e_bh([1, 1, 1], 0.1).any()
    assert e_bh([math.inf, 0.0], 0.05).tolist() == [True, False]


def test_e_bh_controls_fdr_across_clusters():
    """60 clusters, 45 honest, 15 with a 7.5x flag rate; e-values at n = 400 audits each."""
    rng = np.random.default_rng(11)
    m, m0, n, p0, p1, alpha, reps = 60, 45, 400, 0.02, 0.15, 0.1, 600
    fdp, power = [], []
    for _ in range(reps):
        k = np.concatenate([rng.binomial(n, p0, m0), rng.binomial(n, p1, m - m0)])
        e = np.exp(log_e_from_counts(n, k, p0, n_grid=48))
        rej = e_bh(e, alpha)
        v = rej[:m0].sum()
        fdp.append(v / max(rej.sum(), 1))
        power.append(rej[m0:].mean())
    fdr = float(np.mean(fdp))
    se = float(np.std(fdp) / math.sqrt(reps))
    assert fdr <= alpha * m0 / m + 3 * se + 1e-9     # e-BH guarantee: FDR <= alpha * m0 / m
    assert np.mean(power) > 0.9
