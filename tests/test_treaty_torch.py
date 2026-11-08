"""A Narrow Path's mock training run (treaty/mockrun.py), on CPU torch: the FLOP formula against torch's own counter,
and the provider stopping the job at its budget from an energy meter alone. Skipped where torch is not installed."""
import pytest

torch = pytest.importorskip("torch")

from closure.treaty import mockrun as M  # noqa: E402


def test_step_flop_formula_matches_torchs_flop_counter():
    from torch.utils.flop_counter import FlopCounterMode
    dim, layers, batch = 64, 3, 8
    model = M._model(torch, dim, layers, seed=0)
    opt = torch.optim.SGD(model.parameters(), lr=1e-3)
    x = torch.randn(batch, dim)
    with FlopCounterMode(display=False) as fc:
        loss = model(x).pow(2).mean()
        opt.zero_grad()
        loss.backward()
        opt.step()
    assert fc.get_total_flops() == M.step_flop(dim, layers, batch) == 2 * batch * dim ** 2 * (3 * layers - 1)


def test_the_provider_stops_the_job_within_its_budget_and_checks_its_start(tmp_path):
    floor = M.cpu_energy_floor()
    r = M.run_drill(4e11, floor, M.ProcCpuMeter(), tmp_path / "ok", dim=256, layers=4, batch=64, count_from="start")
    assert r["stopped_by_provider"] and r["job_started_training"] and r["compliant"], r
    assert 0 < r["budget_used"] <= 1.0 and r["job_flop_at_most"] <= r["budget_flop"] <= r["provider_bound_flop"] * 1.05
    assert r["init_weights_match_seed"] is True and r["stop_to_exit_s"] < 5.0
    assert (tmp_path / "ok" / "drill.json").exists()


def test_a_floor_that_is_not_a_floor_lets_the_job_run_past_its_budget(tmp_path):
    r = M.run_drill(1e10, 1e-6, M.ProcCpuMeter(), tmp_path / "bad", dim=256, layers=4, batch=64, max_steps=200)
    assert not r["stopped_by_provider"] and not r["compliant"] and r["job_flop_logged"] > r["budget_flop"]


def test_weights_that_do_not_start_from_the_seed_are_flagged(tmp_path):
    r = M.run_drill(4e11, M.cpu_energy_floor(), M.ProcCpuMeter(), tmp_path / "ckpt", dim=256, layers=4, batch=64,
                    not_from_scratch=True, count_from="start")
    assert r["job_started_training"] and r["init_weights_match_seed"] is False


def test_charging_from_spawn_counts_start_up_against_the_budget(tmp_path):
    floor = M.cpu_energy_floor()
    r = M.run_drill(4e11, floor, M.ProcCpuMeter(), tmp_path / "spawn", dim=256, layers=4, batch=64)
    assert r["counted_from"] == "spawn" and r["compliant"] and r["stopped_by_provider"]
