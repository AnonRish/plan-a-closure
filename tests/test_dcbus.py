import numpy as np

from closure import dcbus as D


def test_window_energy_is_exact_for_constant_and_ramp_power():
    t = np.linspace(0, 100, 100001)
    assert np.allclose(D.window_energy(t, np.full_like(t, 500.0), [10.0, 20.5], 2.0), 1000.0)
    ramp = D.window_energy(t, 10 * t, [0.0], 10.0)             # integral of 10t over [0,10] = 500
    assert abs(ramp[0] - 500.0) < 1e-6


def test_align_offset_recovers_clock_skew(tmp_path):
    rng = np.random.default_rng(0)
    n = 1500
    t_win = np.arange(n) * 1.0
    P = 3000 + 1500 * (np.sin(t_win / 37.0) + 0.5 * np.sin(t_win / 5.3)) + rng.normal(0, 60, n)   # W per window
    skew = 3.7
    tb = np.arange(0, n + 40, 0.01)
    pb = np.interp(tb - skew, t_win + 0.5, P) + rng.normal(0, 25, len(tb))      # bus clock runs ahead by 3.7 s
    est = D.align_offset(t_win, P * 1.0, tb, pb, dt=1.0, max_shift_s=15)
    assert abs(est - skew) < 0.15


def test_csv_loader_with_and_without_header(tmp_path):
    (tmp_path / "a.csv").write_text("timestamp_s,power_w\n0,10\n1,20\n")
    (tmp_path / "b.csv").write_text("0,10\n1,20\n")
    for f in ("a.csv", "b.csv"):
        t, p = D.load_csv(tmp_path / f)
        assert list(t) == [0.0, 1.0] and list(p) == [10.0, 20.0]
