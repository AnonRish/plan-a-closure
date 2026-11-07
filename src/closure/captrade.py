"""Cap and trade accounting (Plan A 2032): production permits under a doubling-time cap, the unverified edge-compute
cap, and the inference-fleet caps of the zero-data-retention tiers. Pure ledgers with conservation checks."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CapPath:
    stock0: float
    doubling_months: float = 6.0

    def cap_at(self, months: float) -> float:
        return self.stock0 * 2.0 ** (months / self.doubling_months)


class PermitLedger:
    def __init__(self, path: CapPath):
        self.path, self.issued, self.bal = path, 0.0, {}

    def issue(self, owner: str, amount: float, months: float):
        if self.path.stock0 + self.issued + amount > self.path.cap_at(months) + 1e-9:
            raise ValueError("issuance would exceed the cap path")
        self.issued += amount
        self.bal[owner] = self.bal.get(owner, 0.0) + amount

    def transfer(self, a: str, b: str, amount: float):
        if self.bal.get(a, 0.0) < amount:
            raise ValueError("insufficient permits")
        self.bal[a] -= amount
        self.bal[b] = self.bal.get(b, 0.0) + amount

    def retire(self, owner: str, amount: float):
        """Permits are consumed when the units they cover are produced."""
        if self.bal.get(owner, 0.0) < amount:
            raise ValueError("insufficient permits")
        self.bal[owner] -= amount

    def outstanding(self) -> float:
        return sum(self.bal.values())


@dataclass
class EdgeCap:
    cap: float = 30e6
    existing: float = 25e6
    used: float = 0.0

    @property
    def credits(self) -> float:
        return self.cap - self.existing - self.used

    def register(self, h100e: float, verified: bool) -> str:
        if verified:
            return "exempt"                      # verified edge compute does not consume credits
        if h100e > self.credits + 1e-9:
            raise ValueError("no unverified edge-compute credits left")
        self.used += h100e
        return "credit-consumed"


@dataclass
class FleetCaps:
    caps: dict = field(default_factory=lambda: {"total_zdr": 1e5, "probabilistic_zdr": 1e8, "no_zdr": 1e11})
    used: dict = field(default_factory=dict)

    def allocate(self, tier: str, h100e: float):
        if self.used.get(tier, 0.0) + h100e > self.caps[tier] + 1e-9:
            raise ValueError(f"{tier} inference-fleet cap exceeded")
        self.used[tier] = self.used.get(tier, 0.0) + h100e
