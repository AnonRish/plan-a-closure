import inspect
import json
import socket
import struct

import numpy as np
import pytest

from closure import dcbus as D
from closure import traffic as T
from closure.cli import main


# ------------------------------------------------------------------ meter: absolute power only
def test_ac_coupled_trace_is_rejected_and_a_dc_coupled_trace_is_accepted():
    t = np.linspace(0, 10, 100_001)
    rng = np.random.default_rng(0)
    dc = 600 + 120 * np.sin(2 * np.pi * 3 * t) + rng.normal(0, 15, len(t))      # absolute watts
    ac = dc - dc.mean()                                                          # same shape, no DC response
    g_dc, g_ac = D.check_absolute_power(t, dc, ref_mean_w=610.0), D.check_absolute_power(t, ac)
    assert g_dc["ok"] and not g_dc["warnings"] and abs(g_dc["mean_w_over_nvml_mean"] - 600 / 610) < 0.05
    assert not g_ac["ok"] and "AC-coupled" in g_ac["warnings"][0]
    assert not D.check_absolute_power(t, -dc)["ok"]                              # sign-inverted
    assert not D.check_absolute_power(t, np.array([5.0]))["ok"]


def test_load_csv_converts_time_and_power_units(tmp_path):
    (tmp_path / "a.csv").write_text("timestamp_s,power_w\n0,10000\n1000,20000\n")        # ms and mW
    t, p = D.load_csv(tmp_path / "a.csv", scale=1e-3, ts_unit="ms")
    assert list(t) == [0.0, 1.0] and list(p) == [10.0, 20.0]


def _write_trace(path, t, p, header=True):
    with open(path, "w", newline="") as f:
        if header:
            f.write("timestamp_s,power_w\n")
        for a, b in zip(t, p):
            f.write(f"{a:.9f},{b:.6f}\n")


def test_decimate_preserves_energy_across_chunk_boundaries(tmp_path):
    rng = np.random.default_rng(1)
    t = np.cumsum(rng.uniform(0.5e-4, 1.5e-4, 120_000))                   # ~10 kHz, jittered, 12 s
    p = 500 + 80 * np.sin(2 * np.pi * 0.7 * t) + rng.normal(0, 5, len(t))
    _write_trace(tmp_path / "raw.csv", t, p)
    r = D.decimate_csv(tmp_path / "raw.csv", tmp_path / "dec.csv", window_s=0.05, chunk_rows=7_001)     # many chunks
    assert r["rows_in"] == len(t) and 200 < r["rows_out"] <= 260
    e_true = float(np.sum(0.5 * (p[1:] + p[:-1]) * np.diff(t)))
    assert abs(r["energy_j_in"] - e_true) / e_true < 1e-9
    td, pd_ = D.load_csv(tmp_path / "dec.csv")
    assert np.all(np.diff(td) > 0) and abs(td[1] - td[0] - 0.05) < 1e-6
    e_dec = float(np.sum(pd_) * 0.05)                                        # mean power x window, summed
    assert abs(e_dec - e_true) / e_true < 5e-3
    starts = np.arange(1.0, 10.0, 1.0)
    assert np.allclose(D.window_energy(td, pd_, starts, 1.0), D.window_energy(t, p, starts, 1.0), rtol=1e-2)


def test_decimate_accepts_headerless_files_and_units_and_rejects_unsorted_time(tmp_path):
    t_ms = np.arange(0, 2000.0, 0.1)
    _write_trace(tmp_path / "h.csv", t_ms, np.full(len(t_ms), 4e5), header=False)         # 400 W written in mW, time in ms
    r = D.decimate_csv(tmp_path / "h.csv", tmp_path / "o.csv", 0.5, scale=1e-3, ts_unit="ms", chunk_rows=4000)
    _, p = D.load_csv(tmp_path / "o.csv")
    assert np.allclose(p, 400.0) and abs(r["energy_j_in"] - 400 * 1.9999) < 0.1
    (tmp_path / "bad.csv").write_text("timestamp_s,power_w\n0,1\n2,1\n1,1\n")
    with pytest.raises(ValueError, match="non-decreasing"):
        D.decimate_csv(tmp_path / "bad.csv", tmp_path / "x.csv", 0.5)


def _sim_run(tmp_path):
    assert main(["sim-trial", "--profile", "smoke", "--seed", "2", "--out", str(tmp_path)]) == 0
    z = np.load(tmp_path / "raw.npz")
    t0 = np.concatenate([z["ref_t0"], z["aud_t0"]])
    E = np.concatenate([z["ref_E"], z["aud_E"]])
    tb = np.arange(0, t0[-1] + 20, 0.1)
    idx = np.clip(np.floor(tb - t0[0]).astype(int), 0, len(E) - 1)
    return tb, E[idx]


def test_dcbus_analyze_refuses_an_ac_coupled_trace(tmp_path, capsys):
    tb, pb = _sim_run(tmp_path)
    _write_trace(tmp_path / "ac.csv", tb, pb - pb.mean())
    capsys.readouterr()
    assert main(["dcbus-analyze", "--run", str(tmp_path), "--csv", str(tmp_path / "ac.csv")]) == 2
    out = capsys.readouterr().out
    assert "AC-coupled" in out and "refusing" in out
    assert not (tmp_path / "results_dcbus.json").exists()


def test_dcbus_analyze_scale_fixes_units_and_the_report_carries_the_meter_check(tmp_path, capsys):
    tb, pb = _sim_run(tmp_path)
    _write_trace(tmp_path / "mw.csv", tb, pb * 1000.0)                       # exported in milliwatts
    capsys.readouterr()
    assert main(["dcbus-analyze", "--run", str(tmp_path), "--csv", str(tmp_path / "mw.csv"), "--scale", "0.001"]) == 0
    mc = json.loads((tmp_path / "results_dcbus.json").read_text())["meter_check"]
    assert mc["ok"] and 0.9 < mc["bus_to_nvml_energy_ratio"] < 1.1 and not mc["warnings"]
    assert main(["dcbus-analyze", "--run", str(tmp_path), "--csv", str(tmp_path / "mw.csv")]) == 0       # forgot --scale
    mc = json.loads((tmp_path / "results_dcbus.json").read_text())["meter_check"]
    assert mc["bus_to_nvml_energy_ratio"] > 500 and any("check units" in w for w in mc["warnings"])


def test_dcbus_decimate_cli(tmp_path, capsys):
    t = np.arange(0, 5, 1e-3)
    _write_trace(tmp_path / "r.csv", t, np.full(len(t), 250.0))
    capsys.readouterr()
    assert main(["dcbus-decimate", str(tmp_path / "r.csv"), str(tmp_path / "new" / "dir" / "d.csv"), "--window-ms", "100"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert (tmp_path / "new" / "dir" / "d.csv").exists()
    assert out["rows_in"] == 5000 and abs(out["energy_j_in"] - 250 * 4.999) < 0.01


# ------------------------------------------------------------------ pcap: streaming, IPv6, nothing dropped silently
def _eth(ethertype):
    return bytes(12) + struct.pack(">H", ethertype)


def _v4(proto, total, src="10.0.0.1", dst="10.0.0.2", frag=0, l4=b""):
    ip = struct.pack(">BBHHHBBH4s4s", 0x45, 0, total, 0, frag, 64, proto, 0, socket.inet_aton(src), socket.inet_aton(dst))
    return _eth(0x0800) + ip + l4


def _v6(nh, payload_len, l4, src="2001:db8::1", dst="2001:db8::2"):
    ip = struct.pack(">IHBB", 0x60000000, payload_len, nh, 64) + socket.inet_pton(socket.AF_INET6, src) \
        + socket.inet_pton(socket.AF_INET6, dst)
    return _eth(0x86DD) + ip + l4


def _tcp(sport, dport):
    return struct.pack(">HHIIBBHHH", sport, dport, 0, 0, 5 << 4, 0x18, 65535, 0, 0)


def _pcap(records):
    out = bytearray(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
    for ts, frame, orig in records:
        sec = int(ts)
        out += struct.pack("<IIII", sec, int(round((ts - sec) * 1e6)), len(frame), orig) + frame
    return bytes(out)


def _mixed_capture():
    rec = []
    for i in range(10):                                                   # IPv6 TCP, 1000 B payload each (frame truncated)
        rec.append((1.0 + i * 0.01, _v6(6, 20 + 1000, _tcp(5000, 443)), 14 + 40 + 20 + 1000))
    for i in range(5):                                                    # IPv4 TCP, 500 B each
        rec.append((2.0 + i * 0.01, _v4(6, 20 + 20 + 500, l4=_tcp(6000, 80)), 14 + 20 + 20 + 500))
    rec.append((3.0, _eth(0x0806) + bytes(28), 60))                       # ARP
    rec.append((3.1, _v4(1, 28, l4=bytes(8)), 14 + 28))                   # ICMP
    rec.append((3.2, _v4(6, 1500, frag=200, l4=_tcp(1, 2)), 14 + 1500))   # non-first IP fragment
    rec.append((3.3, _v6(0, 40, bytes(8)), 14 + 40 + 40))                 # IPv6 with an extension header
    return _pcap(rec)


V6 = (6, tuple(sorted([("2001:db8::1", 5000), ("2001:db8::2", 443)])))
V4 = (6, tuple(sorted([("10.0.0.1", 6000), ("10.0.0.2", 80)])))


def test_iter_pcap_is_a_generator_parses_ipv6_and_counts_what_it_cannot_attribute():
    data = _mixed_capture()
    st = T.PcapStats()
    it = T.iter_pcap(data, st)
    assert inspect.isgenerator(it)
    pk = list(it)
    assert len(pk) == 15 and sum(p.payload_len for p in pk if p.src.startswith("2001")) == 10_000
    assert st.total_packets == 19 and st.unparsed_packets == {"non_ip": 1, "non_tcp_udp": 2, "ip_fragment": 1}
    assert st.unparsed_wire_bytes["non_ip"] == 60 and st.unparsed_wire_bytes["ip_fragment"] == 14 + 1500
    assert [p.payload_len for p in T.read_pcap(data)] == [p.payload_len for p in pk]        # list API unchanged


def test_unattributed_frames_fail_the_closure_unless_explicitly_tolerated():
    data = _mixed_capture()
    verified = {V6: 10_000, V4: 2_500}
    st = T.PcapStats()
    r = T.traffic_closure(T.iter_pcap(data, st), verified, stats=st)
    assert r["unexplained_bytes"] == 0 and r["missing_bytes"] == 0           # every parsed byte is explained ...
    assert not r["pass"] and r["unparsed_packets"] == 4                       # ... but ARP, ICMP and fragments are not
    assert r["unparsed_by_reason"]["ip_fragment"] == 1514
    st2 = T.PcapStats()
    ok = T.traffic_closure(T.iter_pcap(data, st2), verified, stats=st2, unparsed_tol_bytes=2_000)
    assert ok["pass"] and ok["unparsed_wire_bytes"] == sum(st2.unparsed_wire_bytes.values())
    assert T.traffic_closure(T.read_pcap(data), verified)["pass"]             # no stats given: old behaviour


def test_pcapng_and_garbage_are_refused_clearly():
    with pytest.raises(ValueError, match="pcapng"):
        list(T.iter_pcap(b"\x0a\x0d\x0d\x0a" + bytes(40)))
    with pytest.raises(ValueError, match="not a classic pcap"):
        list(T.iter_pcap(b"nonsense" + bytes(40)))


def test_a_truncated_file_is_counted_not_ignored():
    data = _mixed_capture()[:-30]
    st = T.PcapStats()
    list(T.iter_pcap(data, st))
    assert st.unparsed_packets.get("truncated_file") == 1


def test_traffic_check_cli_streams_ipv6_and_reports_unparsed(tmp_path, capsys):
    (tmp_path / "t.pcap").write_bytes(_mixed_capture())
    (tmp_path / "v.json").write_text(json.dumps({"6|2001:db8::1:5000|2001:db8::2:443": 10_000,
                                                 "6|10.0.0.1:6000|10.0.0.2:80": 2_500}))
    capsys.readouterr()
    assert main(["traffic-check", str(tmp_path / "t.pcap"), str(tmp_path / "v.json")]) == 1
    assert json.loads(capsys.readouterr().out)["unparsed_packets"] == 4
    assert main(["traffic-check", str(tmp_path / "t.pcap"), str(tmp_path / "v.json"), "--unparsed-tol-bytes", "5000"]) == 0
