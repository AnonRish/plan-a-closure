"""Reproducible simulation study over seeds. Validates the ESTIMATORS (error rates, bounds,
power) -- not GPU physics. Usage: python scripts/sim_study.py [n_seeds] > docs/SIM_STUDY.md"""
import sys
import tempfile

import numpy as np

from closure.cli import _cfg
from closure.sim import SimConfig, SimSource
from closure.trial import run_trial


def main(n: int = 10):
    rows = []
    for seed in range(1, n + 1):
        with tempfile.TemporaryDirectory() as d:
            r = run_trial(SimSource(SimConfig(), seed=seed), _cfg("sim", seed, "SIMULATED"), d)
        fp = r["false_positive"]["combined"]
        rows.append(dict(seed=seed, fp=f"{fp['k']}/{fp['n']}", fpr=fp["rate"], up=fp["cp95_upper"],
                         gap=r["closure_gap_fraction"], e=r["f95_pooled_hidden_fraction"]["energy"],
                         b=r["f95_pooled_hidden_fraction"]["busy"], cov=r["bound"]["coverage_nonslack"],
                         slack=r["bound"]["coverage_slack_expected_to_fail"], tight=r["bound"]["median_tightness_ratio"]))
    pct = lambda x: "n/a" if x is None else f"{100 * x:.2f}%"
    print("# Simulation study (estimator validation only)\n")
    print(f"{n} independent simulated clusters, default profile (600 reference blocks, 1,200 audit blocks, "
          "L=300 s, alpha=1e-3 combined). SIMULATED data: says nothing about real GPU physics.\n")
    print("| seed | null FP (combined) | FPR | FPR 95% upper | closure gap | f95 energy-only | f95 busy-only | bound coverage (non-slack) | coverage (slack, expected to fail) | median bound/truth |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in rows:
        print(f"| {r['seed']} | {r['fp']} | {pct(r['fpr'])} | {pct(r['up'])} | {pct(r['gap'])} | {pct(r['e'])} | "
              f"{pct(r['b'])} | {pct(r['cov'])} | {pct(r['slack'])} | {r['tight']:.2f} |")
    g = np.array([r["gap"] for r in rows if r["gap"] is not None])
    f = np.array([r["fpr"] for r in rows])
    c = np.array([r["cov"] for r in rows])
    print(f"\nMean FPR {100 * f.mean():.3f}% (max {100 * f.max():.2f}%); closure gap mean {100 * g.mean():.2f}% "
          f"(range {100 * g.min():.2f}% to {100 * g.max():.2f}%); non-slack bound coverage mean {100 * c.mean():.2f}% "
          f"(min {100 * c.min():.2f}%).")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 10)
