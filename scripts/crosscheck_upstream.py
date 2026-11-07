"""Cross-check closure.pause against the reference code published with the hardwired-pause paper.

The paper's authors published a calculations notebook (MIT) and an economics repository (MIT). Neither is vendored here; clone
them yourself and point this script at them:

    git clone https://github.com/Berkeley-AI-Risk/pause-ledger-calculations
    git clone https://github.com/Berkeley-AI-Risk/econ-of-MSICs
    python scripts/crosscheck_upstream.py --calc pause-ledger-calculations --msic econ-of-MSICs

--msic imports their msic_analysis.py (needs matplotlib) and compares its Figure 7.1 grid, cell by cell, with
closure.pause.msic_econ on their own demand data. --calc reads the numbers their notebook printed (to three figures) from
feasibility_calculations.html and compares them with closure.pause. Exit status is non-zero on any mismatch."""
from __future__ import annotations

import argparse
import html
import importlib
import re
import sys
from pathlib import Path

from closure.pause import census, msic_econ, thresholds

# Figure 7.1 as printed in the paper: (B, NRE) -> (designs, % of tokens on MSICs)
FIGURE_7_1 = {(500e9, 10e6): (196, 99.93), (500e9, 50e6): (134, 99.6), (500e9, 200e6): (86, 98.3), (500e9, 500e6): (60, 96.3),
              (1e12, 10e6): (221, 99.97), (1e12, 50e6): (157, 99.8), (1e12, 200e6): (111, 99.2), (1e12, 500e6): (81, 98.1),
              (2e12, 10e6): (241, 99.99), (2e12, 50e6): (185, 99.9), (2e12, 200e6): (134, 99.6), (2e12, 500e6): (102, 98.9)}


def check_msic(path: Path) -> int:
    sys.path.insert(0, str(path))
    try:
        up = importlib.import_module("msic_analysis")
    except ModuleNotFoundError as e:
        print(f"cannot import the authors' msic_analysis: missing package '{e.name}'. Install their requirements first:\n"
              f"    pip install -r {path}/requirements.txt")
        return 1
    demand, _ = up.load_demand()
    bad = 0
    for b in up.B_VALUES:
        for nre, n, cov, sav in up.panel_rows(demand, b):
            mine = msic_econ.panel(demand, up.S, b, nre)
            printed = FIGURE_7_1.get((b, nre))
            ok = (mine["designs"] == n and abs(mine["msic_token_share"] * 100 - cov) < 1e-9
                  and abs(mine["savings_vs_all_flexible"] * 100 - sav) < 1e-9)
            ok_paper = printed is None or (printed[0] == n and abs(printed[1] - cov) < 0.06)
            bad += (not ok) + (not ok_paper)
            print(f"{'OK ' if ok and ok_paper else 'BAD'} B=${b / 1e9:.0f}B NRE=${nre / 1e6:.0f}M designs {mine['designs']} (upstream {n}, "
                  f"paper {printed[0] if printed else '-'}) tokens {mine['msic_token_share'] * 100:.3f}% (upstream {cov:.3f}%)")
    top = sorted(demand.values(), reverse=True)
    print(f"top model share {top[0]:.4f}: worst-case savings / NRE = {up.S * top[0] * 500e9 / 500e6:.1f}x (paper: roughly 120x)")
    cum, k = 0.0, 0
    for x in top:
        cum += x
        k += 1
        if cum >= 0.75:
            break
    print(f"{k} models serve three quarters of tokens; the smallest still clears {up.S * top[k - 1] * 500e9 / 500e6:.1f}x (paper: at least 10x)")
    return bad


def _notebook_text(path: Path) -> list:
    raw = (path / "feasibility_calculations.html").read_text(encoding="utf-8", errors="ignore")
    raw = re.sub(r"<(script|style).*?</\1>", " ", raw, flags=re.S)
    return re.sub(r"\n\s*\n+", "\n", html.unescape(re.sub(r"<[^>]+>", "\n", raw))).split("\n")


def _printed(lines: list, label: str):
    """The first number on the output line after a printed header containing `label` (R console output starts with ##)."""
    for i, line in enumerate(lines):
        if line.startswith("##") and label in line and i + 1 < len(lines):
            m = re.search(r"-?\d[\d.]*(?:e[+-]?\d+)?", lines[i + 1].lstrip("# "))
            if m:
                return float(m.group(0))
    return None


def check_calc(path: Path) -> int:
    lines = _notebook_text(path)
    t = thresholds.treaty_thresholds()
    tab = census.table_5_1()
    want = [("F_E (H100e)", t["F_E"], 0.005), ("F_B at T_B = 2 (adopted)", t["F_B"], 0.005), ("F_P (H100e)", t["F_P"], 0.005),
            ("K_M, U.S. (k)", tab["United States"]["K_M"] / 1e3, 0.01), ("K_M, China (k)", tab["China"]["K_M"] / 1e3, 0.01)]
    bad = 0
    for label, mine, tol in want:
        ref = _printed(lines, label)
        if ref is None:
            print(f"?   {label}: not found in the notebook output (format changed?)")
            continue
        ok = abs(mine - ref) <= tol * abs(ref)
        bad += not ok
        print(f"{'OK ' if ok else 'BAD'} {label}: mine {mine:.6g}, notebook printed {ref:.6g} (tolerance {tol:.1%})")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--msic", type=Path, help="clone of Berkeley-AI-Risk/econ-of-MSICs")
    ap.add_argument("--calc", type=Path, help="clone of Berkeley-AI-Risk/pause-ledger-calculations")
    a = ap.parse_args()
    if not (a.msic or a.calc):
        ap.error("give --msic and/or --calc")
    bad = (check_msic(a.msic) if a.msic else 0) + (check_calc(a.calc) if a.calc else 0)
    print("\nall cross-checks agree" if not bad else f"\n{bad} MISMATCH(ES)")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
