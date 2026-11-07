"""Units and conventions shared by the hardwired-pause modules (paper section 3.2.1, footnotes 14-15 and 50)."""
from __future__ import annotations

import math

H100E_FLOPS = 989e12                                    # FLOP/s of one H100e: H100 SXM, dense 16-bit, 32-bit accumulate
SECONDS_PER_YEAR = 365 * 24 * 3600                      # the paper's conventions use 365-day years
H100E_FLOP_PER_YEAR = H100E_FLOPS * SECONDS_PER_YEAR    # about 3.1e22 (paper section 3.2.1)


def h100e(flop_per_s: float) -> float:
    """Peak FLOP/s -> H100-equivalents."""
    return flop_per_s / H100E_FLOPS


def h100e_years(flop: float) -> float:
    """FLOP -> H100e-years at peak throughput."""
    return flop / H100E_FLOP_PER_YEAR


def oom(x: float) -> float:
    """Orders of magnitude (log10)."""
    return math.log10(x)


def sig(x: float, n: int = 2) -> float:
    """Round to n significant figures, the way the paper prints derived quantities (footnote 50)."""
    return float(f"{x:.{n - 1}e}")
