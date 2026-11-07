"""Covert-evasion and overt-breakout ledgers (paper sections 3.2.3, 6.4, 6.5).

Each compute source c held by state s has a raw capacity K0 in H100e and two pairs of discounts: pi, the share that could
plausibly be marshalled (politics, secrecy, legal barriers) and tau, the utilisation it would reach relative to frontier
training (hardware, interconnect, overhead). Per scenario:

    K_E(c,s) = pi_E * tau_E * K0        K_B(c,s) = pi_B * tau_B * K0
    L_E(s) = sum_c K_E(c,s)  <=  alpha_E * F_E        L_B(s) = sum_c K_B(c,s)  <=  alpha_B * F_B

The paper reads headroom line by line (orders of magnitude of erosion before one line alone reaches the allowance) and
says the lines are separate estimates. The ledger is a sum, so this module reports both; the difference is small when one
line dominates and worth knowing when none does."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import census, thresholds
from .units import H100E_FLOPS


def headroom_oom(k: float, f: float, alpha: float) -> float:
    """Orders of magnitude of erosion of f before a capacity k alone reaches alpha*f."""
    return math.inf if k <= 0 else math.log10(alpha * f / k)


@dataclass
class Source:
    name: str
    k0: float
    pi_e: float = 1.0
    tau_e: float = 1.0
    pi_b: float = 1.0
    tau_b: float = 1.0
    retires: bool = False       # leaves the ledger once transitional service ends (phase 3)
    note: str = ""

    @property
    def k_e(self) -> float:
        return self.pi_e * self.tau_e * self.k0

    @property
    def k_b(self) -> float:
        return self.pi_b * self.tau_b * self.k0


@dataclass
class Ledger:
    state: str
    f_e: float
    f_b: float
    alpha_e: float = 0.25
    alpha_b: float = 0.25
    sources: list = field(default_factory=list)

    def add(self, source: Source) -> "Ledger":
        self.sources.append(source)
        return self

    def _active(self, durable: bool):
        return [s for s in self.sources if not (durable and s.retires)]

    def l_e(self, durable: bool = False) -> float:
        return sum(s.k_e for s in self._active(durable))

    def l_b(self, durable: bool = False) -> float:
        return sum(s.k_b for s in self._active(durable))

    def lines(self, durable: bool = False) -> list:
        return [{"name": s.name, "K_E": s.k_e, "share_E": s.k_e / self.f_e,
                 "headroom_E_oom": headroom_oom(s.k_e, self.f_e, self.alpha_e),
                 "K_B": s.k_b, "share_B": s.k_b / self.f_b,
                 "headroom_B_oom": headroom_oom(s.k_b, self.f_b, self.alpha_b)} for s in self._active(durable)]

    def headroom(self, durable: bool = False) -> dict:
        """Summed ledger against its allowances, and the single line with the least headroom."""
        ls = self.lines(durable)
        return {"E_sum_oom": headroom_oom(self.l_e(durable), self.f_e, self.alpha_e),
                "B_sum_oom": headroom_oom(self.l_b(durable), self.f_b, self.alpha_b),
                "E_line_oom": min((x["headroom_E_oom"] for x in ls), default=math.inf),
                "B_line_oom": min((x["headroom_B_oom"] for x in ls), default=math.inf),
                "binding_E": min(ls, key=lambda x: x["headroom_E_oom"])["name"] if ls else None,
                "binding_B": min(ls, key=lambda x: x["headroom_B_oom"])["name"] if ls else None}

    def certify(self, erosion: float = 1.0, durable: bool = False) -> dict:
        """Do both ledgers fit under their allowances once the fleet thresholds have shrunk by `erosion`?"""
        ae, ab = self.alpha_e * self.f_e / erosion, self.alpha_b * self.f_b / erosion
        le, lb = self.l_e(durable), self.l_b(durable)
        return {"ok_E": le <= ae, "ok_B": lb <= ab, "L_E": le, "allow_E": ae, "L_B": lb, "allow_B": ab}

    def max_licensed(self, name: str, erosion: float = 1.0, durable: bool = False) -> float:
        """The paper's main lever (section 3.2.3): the largest raw capacity of source `name` that can be licensed while both
        inequalities still hold with the other lines fixed and the thresholds shrunk by `erosion`. 0 if already over."""
        src = next(s for s in self.sources if s.name == name)
        others_e = sum(s.k_e for s in self._active(durable) if s is not src)
        others_b = sum(s.k_b for s in self._active(durable) if s is not src)
        room_e = self.alpha_e * self.f_e / erosion - others_e
        room_b = self.alpha_b * self.f_b / erosion - others_b
        per_e, per_b = src.pi_e * src.tau_e, src.pi_b * src.tau_b
        caps = [room / per for room, per in ((room_e, per_e), (room_b, per_b)) if per > 0]
        return max(min(caps), 0.0) if caps else math.inf

    def years_of_durability(self, annual_gain: float, durable: bool = True) -> float:
        """Years of training-efficiency gains (e.g. 1.57x per year) the summed ledger survives."""
        h = self.headroom(durable)
        return min(h["E_sum_oom"], h["B_sum_oom"]) / math.log10(annual_gain)


def allowance(erosion_oom: float, a_start: float = 1.0, a_end: float = 0.25, oom_to_end: float = 1.0) -> float:
    """Shrinking allowance schedule: starts near a_start at entry into force and falls geometrically to a_end by the time
    `oom_to_end` orders of magnitude of training-efficiency gains have accumulated (section 6.5)."""
    x = min(max(erosion_oom, 0.0), oom_to_end) / oom_to_end
    return a_start * (a_end / a_start) ** x


# ---- the paper's illustrative ledger lines (section 6.4) --------------------------------------------------------------------
# Table 6.1: installed accelerator stocks at year-end 2026 (H100e) and the ranges the paper shows
TABLE_6_1 = {"world": (47e6, (45e6, 47e6)), "United States": (35e6, (26e6, 44e6)), "China": (3.1e6, (2.6e6, 4.5e6))}
WORLD_FLEET_YE2026 = 46.96e6          # H100e, derived in the paper's calculation supplement and printed as 47M
US_FRACTION = 0.75                    # share of the world fleet located in the US
CHINA_FLEET_YE2026 = 3.111e6
INFERENCE_COMPUTE_SHARE = 2 / 3       # Deloitte: share of 2026 AI compute used for inference
CONSUMER_CARDS, CONSUMER_TFLOPS = 100e6, 30.0
EL_CAPITAN_APUS, EL_CAPITAN_TFLOPS = 46e3, 980.6


def section_6_4(state: str, scenario: str = "high", phi: float = 1e-4, inference_replication: float = 100.0,
                params: thresholds.ThresholdParams = thresholds.ThresholdParams(), stock: float = None,
                world_fleet: float = None) -> Ledger:
    """The ledger lines of section 6.4 for "United States" or "China" under a dark-compute scenario.

    Transitional service uses pi_E = 0.001 (10% of operators evade, each diverting 1%) in the US and 0.01 in China
    (every operator suborned); the paper calls both pessimistic. Inference-only fleets serve `inference_replication`
    times today's inference demand at residual training factor phi. `stock` overrides the state's installed fleet (Table 6.1
    shows 26M-44M for the US and 2.6M-4.5M for China) and `world_fleet` the world total behind inference demand."""
    f_e, f_b = thresholds.covert_evasion_fleet(params), thresholds.overt_breakout_fleet(params)
    us = state == "United States"
    world = WORLD_FLEET_YE2026 if world_fleet is None else world_fleet
    if stock is None:
        stock = US_FRACTION * world if us else CHINA_FLEET_YE2026
    k_m = census.k_missing(census.TABLE_5_1[state])
    dark = census.dark_compute(k_m, state, scenario)
    inference_demand = inference_replication * INFERENCE_COMPUTE_SHARE * world
    led = Ledger(state, f_e, f_b)
    led.add(Source("transitional service", stock, pi_e=0.001 if us else 0.01, retires=True,
                   note="training-capable chips in commercial data centres, until inference-only chips replace them"))
    led.add(Source("dark compute", dark["k0"], pi_e=dark["pi"], pi_b=dark["pi"], note=f"{scenario}-cooperation scenario"))
    led.add(Source("inference-only fleet", phi * inference_demand, pi_e=0.001,
                   note="residual training factor phi times the inference demand served"))
    led.add(Source("consumer GPUs", CONSUMER_CARDS * CONSUMER_TFLOPS * 1e12 / H100E_FLOPS, pi_e=0.01, tau_e=0.1, pi_b=0.25,
                   tau_b=0.1, note="diffusely held, so heavily discounted"))
    led.add(Source("sovereign supercomputer (El Capitan scale)", EL_CAPITAN_APUS * EL_CAPITAN_TFLOPS * 1e12 / H100E_FLOPS,
                   pi_e=0.2, note="one machine; a state may run several"))
    return led


def strategic_reserve(k0: float, name: str = "strategic reserve (sealed)") -> Source:
    """Powered-off chips under seal in a monitored facility (section 3.3.1): nothing for covert evasion, because they are
    verifiably off, but fully available in an overt breakout, so they count at pi = tau = 1."""
    return Source(name, k0, pi_e=0.0, pi_b=1.0, tau_b=1.0, note="verifiably powered off under seal")


def scientific_preserve(k0: float, neutral_host: bool = True, name: str = "scientific preserve") -> Source:
    """Treaty-run data centres for declared, replayable workloads (sections 3.3.1 and 6.4.7). Covert use is hard in front of
    the operators; breakout exposure is removed if the host is neutral or monitors can incapacitate the chips on seizure."""
    return Source(name, k0, pi_e=0.0, pi_b=0.0 if neutral_host else 1.0,
                  note="neutral host or incapacitation on seizure" if neutral_host else "host state could seize it")


def offshore(ledger: Ledger, name: str, fraction: float) -> Ledger:
    """Move `fraction` of a source's overt-breakout exposure out of reach (custody of a neutral state or an international
    body that would not return it after a breakout, section 6.5.2). The chips still count towards covert evasion."""
    for s in ledger.sources:
        if s.name == name:
            s.pi_b *= (1.0 - fraction)
    return ledger
