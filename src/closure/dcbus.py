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


class _Windows:
    """Window-mean power from a stream of (time, power) samples, in constant memory, written as `timestamp_s,power_w`
    (window centre, mean power). Each trapezoid segment goes to the window that contains its start, so the energy error
    is at most one sample period per window edge. Times must be non-decreasing."""

    def __init__(self, window_s: float, writer):
        self.window_s, self.wr = float(window_s), writer
        self.t0 = self.carry = self.t_last = None
        self.n_in = self.n_out = 0
        self.e_in = 0.0
        self.acc = {}
        writer.writerow(["timestamp_s", "power_w"])

    def _flush(self, upto):
        for b in sorted(k for k in self.acc if k < upto):
            e, d = self.acc.pop(b)
            if d > 0:
                self.wr.writerow([f"{self.t0 + (b + 0.5) * self.window_s:.9f}", f"{e / d:.6f}"])
                self.n_out += 1

    def feed(self, t, p):
        t, p = np.asarray(t, float), np.asarray(p, float)
        if not len(t):
            return
        self.n_in += len(t)
        if self.carry is not None:
            t, p = np.concatenate([[self.carry[0]], t]), np.concatenate([[self.carry[1]], p])
        if len(t) > 1 and np.any(np.diff(t) < 0):
            raise ValueError("timestamps must be non-decreasing for streaming decimation: sort the file first")
        if self.t0 is None:
            self.t0 = float(t[0])
        if len(t) > 1:
            dts = np.diff(t)
            e_seg = 0.5 * (p[1:] + p[:-1]) * dts
            b = np.floor((t[:-1] - self.t0) / self.window_s).astype(np.int64)
            lo = int(b.min())
            esum, dsum = np.bincount(b - lo, weights=e_seg), np.bincount(b - lo, weights=dts)
            for k in np.nonzero(dsum)[0]:
                cell = self.acc.setdefault(int(k) + lo, [0.0, 0.0])
                cell[0] += float(esum[k])
                cell[1] += float(dsum[k])
            self.e_in += float(e_seg.sum())
            self._flush(int(b.max()))
        self.carry, self.t_last = (float(t[-1]), float(p[-1])), float(t[-1])

    def finish(self) -> dict:
        self._flush(10 ** 18)
        return {"rows_in": self.n_in, "rows_out": self.n_out, "t_start": self.t0, "t_end": self.t_last,
                "energy_j_in": self.e_in, "window_s": self.window_s}


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
        win = _Windows(window_s, csv.writer(fout))

        def consume(rows):
            win.feed(np.array([float(r[i]) for r in rows]) * u, np.array([float(r[j]) for r in rows]) * scale)

        for r in rd:
            if not r:
                continue
            buf.append(r)
            if len(buf) >= chunk_rows:
                consume(buf)
                buf = []
        if buf:
            consume(buf)
        return win.finish()


# ---- PowerSensor3 ---------------------------------------------------------------------------------------------------
# PowerSensor3 (ASTRON and the Netherlands eScience Center; open hardware, Apache-2.0 host library) measures the power a
# PCIe card draws through the slot and its auxiliary cables with Hall-effect current sensors and isolated voltage sensors,
# about 20,000 times a second: a DC-coupled, absolute meter outside the GPU, which is what assumption A6 asks for. Its
# host library writes a "dump" (`psrun -f`, `pstest -f`, or `PowerSensor.dump(path, use_absolute_timestamp)` from Python):
#
#   marker time dt_micro device_timestamp current0 voltage0 power0 [... for each sensor pair in use] power_total
#   S 1763130000.123456 50 123456789 2.1 12.05 25.3 ... 312.7
#
# one row per sample, `time` in seconds (Unix time when the dump was started with absolute timestamps, otherwise seconds
# since the PowerSensor object was created), powers in watts, `power_total` their sum. A row starts with "S", or with
# the character a program passed to mark(). Read from the host library's source (host/src/PowerSensor.cc, dump() and
# dumpCurrentWattToFile(), at commit c5017f9 of github.com/nlesc-recruit/PowerSensor3).
PS3_HEADER_START = "marker"
ABSOLUTE_AFTER_S = 1e8           # a dump's first time above this is Unix time (1973 on); below it, seconds since start


def _ps3_rows(path, stats: dict):
    """(time, power_total, marker) for every complete row of a PowerSensor3 dump, in file order."""
    with open(path, encoding="utf-8", errors="replace") as f:
        head = None
        for line in f:
            parts = line.split()
            if not parts:
                continue
            if head is None:
                if parts[0] != PS3_HEADER_START or "time" not in parts or "power_total" not in parts:
                    raise ValueError("not a PowerSensor3 dump: its first line should be the header "
                                     "'marker time dt_micro device_timestamp ... power_total'")
                head = parts
                i_t, i_p = head.index("time"), head.index("power_total")
                stats["pairs"] = sum(1 for h in head if h.startswith("power") and h != "power_total")
                continue
            if parts[0] == PS3_HEADER_START:     # a second dump appended to the same file: its header is not a sample
                stats["headers_skipped"] = stats.get("headers_skipped", 0) + 1
                continue
            if len(parts) != len(head):           # the last line of a dump that was cut off, typically
                stats["rows_skipped"] = stats.get("rows_skipped", 0) + 1
                continue
            try:
                yield float(parts[i_t]), float(parts[i_p]), parts[0]
            except ValueError:
                stats["rows_skipped"] = stats.get("rows_skipped", 0) + 1


def _dequantise(rows, stats: dict):
    """Rows with times spread evenly within each run of identical printed times.

    Without absolute timestamps the host library prints `time` to six significant figures, so past 1,000 s many
    consecutive samples share one printed time (past 10,000 s, 0.1 s of them). Energy is unaffected, but where it falls
    in time would be misplaced by up to that step. Printing rounds to nearest, so the n samples printed as T were drawn
    over [T - q/2, T + q/2), q being the step to the next printed time; the device samples at a steady rate, so each is
    put at the middle of its n-th share of that interval. A sample with a time of its own (n = 1) keeps it. The last run
    gets the sample period seen before it."""
    run, period = [], None
    for t, p, m in rows:
        if run and t != run[0][0]:
            t_run, n = run[0][0], len(run)
            q = t - t_run
            if n > 1:
                stats["max_shared_time_rows"] = max(stats.get("max_shared_time_rows", 1), n)
            for k, (_, pk, mk) in enumerate(run):
                yield t_run + ((k + 0.5) / n - 0.5) * q, pk, mk
            period = q / n
            run = []
        run.append((t, p, m))
    if run:
        n = len(run)
        step = period if period is not None and n > 1 else 0.0
        for k, (tk, pk, mk) in enumerate(run):
            yield tk + (k + 0.5 - n / 2) * step, pk, mk


def powersensor3_to_csv(src, dst, window_s: float = 0.01, t0: float | None = None, chunk_rows: int = 200_000) -> dict:
    """A PowerSensor3 dump as `timestamp_s,power_w` window means (default 10 ms windows), in constant memory, ready for
    `closure dcbus-analyze`. `t0` is the Unix time at which a dump with relative times started; a dump with absolute
    times needs none, and is refused with one, so that no offset is applied twice. dcbus-analyze still estimates the
    remaining skew (up to 30 s) from the data."""
    import csv
    from pathlib import Path
    stats = {"markers": 0}
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    rows = _ps3_rows(src, stats)
    first = next(rows, None)
    if first is None:
        raise ValueError(f"{src}: the dump has a header but no samples")
    absolute = first[0] >= ABSOLUTE_AFTER_S
    if absolute and t0 is not None:
        raise ValueError("this dump already has absolute (Unix) times: drop --t0")
    if not absolute and t0 is None:
        raise ValueError("this dump has relative times (seconds since the PowerSensor object was created): pass --t0, the "
                         "Unix time at which the dump started (for example `date +%s.%N` printed just before psrun), or "
                         "record with `closure meter-log`, which writes absolute times")
    shift = 0.0 if absolute else float(t0)

    def chained():
        yield first
        yield from rows

    with open(dst, "w", newline="") as fout:
        win = _Windows(window_s, csv.writer(fout))
        tb, pb = [], []
        for t, p, m in _dequantise(chained(), stats):
            if m != "S":
                stats["markers"] += 1
            tb.append(t + shift)
            pb.append(p)
            if len(tb) >= chunk_rows:
                win.feed(tb, pb)
                tb, pb = [], []
        win.feed(tb, pb)
        out = win.finish()
    dur = (out["t_end"] - out["t_start"]) if out["t_start"] is not None and out["t_end"] is not None else 0.0
    out.update({"source": "PowerSensor3 dump", "absolute_times": absolute, "t0_applied": None if absolute else shift,
                "sensor_pairs": stats.get("pairs"), "markers": stats["markers"],
                "rows_skipped": stats.get("rows_skipped", 0), "headers_skipped": stats.get("headers_skipped", 0),
                "max_rows_sharing_one_printed_time": stats.get("max_shared_time_rows", 1),
                "mean_w": (out["energy_j_in"] / dur) if dur > 0 else None,
                "sample_rate_hz": ((out["rows_in"] - 1) / dur) if dur > 0 else None})
    return out


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
