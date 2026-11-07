import pytest

from closure.pause import gemm_audit as G
from closure.pause import inference_only as IO
from closure.pause.units import H100E_FLOPS


def test_residual_training_factor_and_fleet_exposure():
    assert IO.residual_training_factor(10.0, 1000.0) == pytest.approx(0.01)
    assert IO.training_capacity_reduction(0.001) == pytest.approx(0.999)
    r = IO.Rating("chip", 100.0, 0.01)
    assert r.phi == pytest.approx(1e-4)
    # section 6.4.4: 100x today's 31M inference-H100e at phi = 1e-4 is 310k H100e of breakout exposure
    assert IO.seized_fleet_exposure(100 * 31e6, 1e-4) == pytest.approx(310e3)
    assert IO.servable_demand(1e6, 0.01) == pytest.approx(100e6) and IO.servable_demand(1e6, 0.001) == pytest.approx(1e9)
    assert IO.max_phi(31e6, 31e3) == pytest.approx(1e-3)
    assert IO.inference_h100e(5e6, 1e6, 8.0) == pytest.approx(40.0)


def test_fleet_phi_weighting():
    good, bad = IO.Rating("good", 100.0, 0.01), IO.Rating("bad", 100.0, 10.0)
    # weighted by inference-H100e: a single chip 1000x worse than the other thousand doubles the fleet average, so the
    # worst chips dominate and a certification has to bound every design, not the typical one
    mixed = IO.fleet_phi([(1000, good), (1, bad)])
    assert mixed == pytest.approx((1000 * 0.01 + 10.0) / (1001 * 100.0))
    assert mixed == pytest.approx(2 * good.phi, rel=0.01)
    assert IO.fleet_phi([(10, good)]) == pytest.approx(good.phi)
    # equal training bound, different inference rating: the better-rated chip pulls the average down
    assert IO.fleet_phi([(1, IO.Rating("a", 100.0, 1.0)), (1, IO.Rating("b", 300.0, 1.0))]) == pytest.approx(2 / 400)


def test_token_oracle_bound():
    rate = IO.token_oracle_gemm_rate(1e9, 1e6)
    assert rate == pytest.approx(12.17e9, rel=0.001)
    assert IO.machines_to_match(H100E_FLOPS, rate) > 80_000
    # rate grows as the square root of the context and linearly with token throughput
    assert IO.token_oracle_gemm_rate(4e9, 1e6) == pytest.approx(2 * rate)
    assert IO.token_oracle_gemm_rate(1e9, 3e6) == pytest.approx(3 * rate)
    assert IO.inference_speed_as_training_multiple(50.0) == pytest.approx(15.5, abs=0.1)


def test_attention_flop_share():
    assert G.attention_flop_share(4096, 2048) == pytest.approx(2048 / (6 * 4096 + 2048))
    assert G.attention_flop_share(4096, 8192) == pytest.approx(0.25)
    assert G.attention_flop_share(4096, 131072) > 0.8                    # a majority at long context


def test_gemm_audit_open_design_is_exposed():
    r = G.audit(G.example_attention_block())
    byid = {m["id"]: m for m in r.matmuls}
    assert byid["score"]["class"] == "exposed" and byid["score"]["depth"] == 0
    assert byid["value"]["class"] == "obstructed" and byid["value"]["depth"] >= 1      # behind the score product and the softmax
    assert not r.passes_licensing_criterion
    assert r.exposed_fraction == pytest.approx(0.125) and r.exposed_or_obstructed_fraction == pytest.approx(0.25)
    assert any("score" in f for f in r.findings())


def test_gemm_audit_sealed_or_authenticated_passes():
    for kw in ({"sealed_package": True}, {"authenticated_links": True}, {"open_links": False}):
        r = G.audit(G.example_attention_block(**kw))
        assert r.passes_licensing_criterion and r.exposed_or_obstructed_fraction == 0.0, kw
        assert all(m["class"] == "sealed" for m in r.matmuls)


def test_gemm_audit_partial_protection_and_multi_feeder():
    # protecting only the memory bus already satisfies the paper's criterion: one operand (K) is no longer writable
    d = G.example_attention_block()
    d.protect("hbm_bus")
    assert G.audit(d).passes_licensing_criterion
    # protecting only the inter-chip link leaves K and V writable but Q and the outputs sealed: also passes
    d = G.example_attention_block()
    d.protect("cxl_link")
    assert G.audit(d).passes_licensing_criterion
    # an operand with two feeders (a multiplexer) is as exposed as its most exposed feeder
    m = G.Design("mux")
    m.add("port", "port", writable=True, readable=True).add("w", "buffer").add("mm", "matmul_dynamic", flops=1.0)
    m.add("static", "linear").add("tok", "token_port")
    m.connect("tok", "static").connect("static", "mm", "a").connect("port", "w").connect("w", "mm", "a")
    m.add("w2", "buffer").connect("port", "w2").connect("w2", "mm", "b").connect("mm", "port")
    assert G.audit(m).matmuls[0]["class"] == "exposed"


def test_token_port_is_not_an_attack_surface():
    d = G.Design("tokens only")
    d.add("in", "token_port").add("emb", "linear").add("a", "matmul_dynamic", flops=1.0).add("out", "token_port")
    d.connect("in", "emb").connect("emb", "a", "a").connect("emb", "a", "b").connect("a", "out")
    assert G.audit(d).passes_licensing_criterion


def test_design_json_roundtrip_and_validation():
    d = G.example_attention_block()
    again = G.design_from_dict(G.design_to_dict(d))
    assert G.audit(again).exposed_fraction == G.audit(d).exposed_fraction
    with pytest.raises(ValueError):
        G.design_from_dict({"nodes": {"a": {"kind": "buffer"}}, "edges": [["a", "ghost"]]})
    with pytest.raises(ValueError):
        G.Design("x").add("n", "flux_capacitor")
