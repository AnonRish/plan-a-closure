"""DC-bus power import + clock alignment: the independent physical channel (Side Channel Cloud).

NVML power is reported by the prover's own stack and can be spoofed or replayed; a bus meter cannot."""
from __future__ import annotations

import numpy as np


_TS_UNIT = {"s": 1.0, "ms": 1e-3, "us": 1e-6, "ns": 1e-9}


def load_csv(path, ts_col: str = "timestamp_s", p_col: str = "power_w", scale: float = 1.0, ts_unit: str = "s"):
    """Read `timestamp_s,power_w` (header optional). `scale` converts the power column to watts, `ts_unit` the time column
    to seconds. Loads the whole file: reduce very large traces first with `decimate_csv`."""
    import csv
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    head = [h.strip() for h in rows[0]]
    try:
        i, j, body = head.index(ts_col), head.index(p_col), rows[1:]
    except ValueError:
        i, j, body = 0, 1, rows[1:] if not _isnum(rows[0][0]) else rows
    t = np.array([float(r[i]) for r in body]) * _TS_UNIT[ts_unit]
    p = np.array([float(r[j]) for r in body]) * scale
    o = np.argsort(t)
    return t[o], p[o]


def check_absolute_power(t, p, ref_mean_w: float | None = None) -> dict:
    """Closure needs *absolute* power in watts. An AC-coupled probe (a Rogowski coil, say: no DC response) shows the shape
    of the load but not its level, so its trace is roughly zero-mean and swings negative, and integrating it gives
    nonsense joules. Such a trace is rejected; a calibrated shunt, Hall-effect sensor or PSU/PDU meter is what is needed."""
    p = np.asarray(p, float)
    if len(p) < 2:
        return {"ok": False, "mean_w": None, "sd_w": None, "negative_fraction": None,
                "warnings": ["the trace has fewer than two samples"]}
    mean, sd, neg = float(p.mean()), float(p.std()), float(np.mean(p < 0))
    warnings, ok = [], True
    if neg > 0.02:
        ok = False
        warnings.append(f"{neg:.1%} of the power samples are negative: the trace looks AC-coupled or sign-inverted; closure "
                        "needs absolute power in watts (DC-coupled and calibrated)")
    elif sd > 0 and abs(mean) < 0.1 * sd:
        ok = False
        warnings.append("the trace mean is about zero relative to its swing: it looks AC-coupled (no DC component), so it "
                        "carries no energy information")
    if mean <= 0:
        ok = False
        if not warnings:
            warnings.append(f"the mean power is {mean:.3g} W: not a power trace")
    return {"ok": ok, "mean_w": mean, "sd_w": sd, "negative_fraction": neg,
            "mean_w_over_nvml_mean": (mean / ref_mean_w if ref_mean_w else None), "warnings": warnings}


def decimate_csv(src, dst, window_s: float, ts_col: str = "timestamp_s", p_col: str = "power_w", scale: float = 1.0,
                 ts_unit: str = "s", chunk_rows: int = 1_000_000) -> dict:
    """Constant-memory reduction of a very high-rate trace (10 MHz is 8.6e11 rows a day) to window-mean power.

    Each trapezoid segment is assigned to the window that contains its start, so the energy error is at most one sample
    period per window edge. Timestamps must be non-decreasing. Writes `timestamp_s,power_w` (window centre, mean power)."""
    import csv
    from pathlib import Path
    u = _TS_UNIT[ts_unit]
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    with open(src, newline="") as fin, open(dst, "w", newline="") as fout:
        rd = csv.reader(fin)
        first = next(rd)
        if _isnum(first[0]):
            i, j, buf = 0, 1, [first]
        else:
            head = [h.strip() for h in first]
            i, j = (head.index(ts_col), head.index(p_col)) if (ts_col in head and p_col in head) else (0, 1)
            buf = []
        wr = csv.writer(fout)
        wr.writerow(["timestamp_s", "power_w"])
        st = {"t0": None, "carry": None, "n_in": 0, "n_out": 0, "e_in": 0.0, "t_last": None}
        acc = {}

        def flush(upto):
            for b in sorted(k for k in acc if k < upto):
                e, d = acc.pop(b)
                if d > 0:
                    wr.writerow([f"{st['t0'] + (b + 0.5) * window_s:.9f}", f"{e / d:.6f}"])
                    st["n_out"] += 1

        def consume(rows):
            t = np.array([float(r[i]) for r in rows]) * u
            p = np.array([float(r[j]) for r in rows]) * scale
            st["n_in"] += len(rows)
            if st["carry"] is not None:
                t, p = np.concatenate([[st["carry"][0]], t]), np.concatenate([[st["carry"][1]], p])
            if len(t) > 1 and np.any(np.diff(t) < 0):
                raise ValueError("timestamps must be non-decreasing for streaming decimation: sort the file first")
            if st["t0"] is None:
                st["t0"] = float(t[0])
            if len(t) > 1:
                dts = np.diff(t)
                e_seg = 0.5 * (p[1:] + p[:-1]) * dts
                b = np.floor((t[:-1] - st["t0"]) / window_s).astype(np.int64)
                lo = int(b.min())
                esum, dsum = np.bincount(b - lo, weights=e_seg), np.bincount(b - lo, weights=dts)
                for k in np.nonzero(dsum)[0]:
                    cell = acc.setdefault(int(k) + lo, [0.0, 0.0])
                    cell[0] += float(esum[k])
                    cell[1] += float(dsum[k])
                st["e_in"] += float(e_seg.sum())
                flush(int(b.max()))
            st["carry"], st["t_last"] = (float(t[-1]), float(p[-1])), float(t[-1])

        for r in rd:
            if not r:
                continue
            buf.append(r)
            if len(buf) >= chunk_rows:
                consume(buf)
                buf = []
        if buf:
            consume(buf)
        flush(10 ** 18)
    return {"rows_in": st["n_in"], "rows_out": st["n_out"], "t_start": st["t0"], "t_end": st["t_last"],
            "energy_j_in": st["e_in"], "window_s": window_s}


def _isnum(s) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


def window_energy(t, p, starts, dt: float) -> np.ndarray:
    """Energy (J) of the bus trace over [start, start+dt) via exact trapezoid integration."""
    cum = np.concatenate([[0.0], np.cumsum(0.5 * (p[1:] + p[:-1]) * np.diff(t))])
    s = np.asarray(starts, float)
    return np.interp(s + dt, t, cum) - np.interp(s, t, cum)


def align_offset(t_win, e_win, t_bus, p_bus, dt: float = 1.0, max_shift_s: float = 30.0) -> float:
    """Offset s = bus_clock - nvml_clock (seconds) that maximises correlation of window energies."""
    ref = np.asarray(e_win, float) / dt
    step = dt / 4
    shifts = np.arange(-max_shift_s, max_shift_s + step / 2, step)
    corr = np.empty(len(shifts))
    for k, s in enumerate(shifts):
        b = window_energy(t_bus, p_bus, np.asarray(t_win) + s, dt) / dt
        corr[k] = np.corrcoef(ref, b)[0, 1] if np.std(b) > 0 else -1.0
    k = int(np.argmax(corr))
    if 0 < k < len(shifts) - 1:                       # parabolic refinement
        y0, y1, y2 = corr[k - 1], corr[k], corr[k + 1]
        den = y0 - 2 * y1 + y2
        if den != 0:
            return float(shifts[k] + 0.5 * step * (y0 - y2) / den)
    return float(shifts[k])
