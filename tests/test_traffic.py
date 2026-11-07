import numpy as np

from closure import traffic as T


def _flow(n, src="10.0.0.1", dst="10.0.0.2", sport=5000, dport=443, plen=1000, t0=1.0, dt=0.01):
    return [T.Pkt(t0 + i * dt, src, dst, sport, dport, 6, plen) for i in range(n)]


def test_pcap_roundtrip(tmp_path):
    pk = _flow(20) + [T.Pkt(2.0, "10.0.0.2", "10.0.0.1", 443, 5000, 6, 300), T.Pkt(2.1, "10.0.0.3", "10.0.0.2", 9, 9, 17, 77)]
    f = tmp_path / "t.pcap"
    T.write_pcap(f, pk)
    back = T.read_pcap(f)
    assert len(back) == len(pk)
    assert [p.payload_len for p in back] == [p.payload_len for p in pk]
    assert back[20].src == "10.0.0.2" and back[21].proto == 17
    assert abs(back[3].ts - pk[3].ts) < 1e-5


def test_closure_passes_when_everything_is_explained(tmp_path):
    pk = _flow(50)
    f = tmp_path / "a.pcap"
    T.write_pcap(f, pk)
    r = T.traffic_closure(T.read_pcap(f), {T.flow_key(pk[0]): 50_000})
    assert r["pass"] and r["unexplained_bytes"] == 0


def test_closure_flags_unknown_flow_and_extra_bytes():
    pk = _flow(50) + _flow(10, dst="10.9.9.9", sport=777, dport=4444)
    ver = {T.flow_key(pk[0]): 50_000}
    r = T.traffic_closure(pk, ver)
    assert not r["pass"] and r["unexplained_bytes"] == 10_000 and len(r["unknown_flows"]) == 1
    pk2 = _flow(60)                                           # 10 kB more than verified on a known flow
    r2 = T.traffic_closure(pk2, ver)
    assert 8_000 < r2["unexplained_bytes"] < 10_000 and not r2["pass"]   # 10 kB extra minus the 2% + 256 B tolerance


def test_closure_reports_tap_loss_as_missing():
    pk = _flow(30)
    r = T.traffic_closure(pk, {T.flow_key(pk[0]): 50_000})
    assert r["missing_bytes"] > 15_000 and not r["pass"]


def test_timing_grid_conformance_and_capacity_bound():
    rng = np.random.default_rng(0)
    grid = np.arange(1000) * 0.005 + rng.normal(0, 1e-5, 1000)
    assert T.timing_grid_conformance(grid, 0.005, 1e-4)["conforming_fraction"] > 0.99
    free = np.cumsum(rng.uniform(0.001, 0.009, 1000))
    assert T.timing_grid_conformance(free, 0.005, 1e-4)["conforming_fraction"] < 0.2
    assert abs(T.covert_capacity_bound_bps(200, 0.015, 0.005) - 200 * 2.0) < 1e-9   # 4 slots -> 2 bits
