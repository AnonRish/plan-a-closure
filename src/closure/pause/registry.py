"""Chip registry and latency-based location checks (paper section 3.3.2).

Pre-pause chips enter by registration when the regime starts and new chips at manufacture; the only exit is verified
destruction. Chips attest their location; chips that move unexpectedly or fall silent must be produced for inspection;
chips lost to the regime are presumed dark compute and charged to the host state's ledgers at near-full capacity."""
from __future__ import annotations

import math
from dataclasses import dataclass

STATES = ("registered", "in_service", "silent", "lost", "destroyed")
EARTH_RADIUS_KM = 6371.0
FIBRE_KM_PER_MS = 200.0     # one-way signal speed in fibre, about two thirds of c


def haversine_km(a: tuple, b: tuple) -> float:
    (la1, lo1), (la2, lo2) = map(lambda p: (math.radians(p[0]), math.radians(p[1])), (a, b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))


def max_distance_km(rtt_ms: float, km_per_ms: float = FIBRE_KM_PER_MS) -> float:
    """A round trip of rtt_ms bounds the one-way distance. Delay can only be added, so this is an upper bound on how far
    away the chip is, never a lower one."""
    return km_per_ms * rtt_ms / 2.0


def consistent_with_claim(claimed: tuple, measurements: list, km_per_ms: float = FIBRE_KM_PER_MS) -> bool:
    """measurements: [((lat, lon) of a landmark, rtt_ms)]. A claimed location is physically impossible if it lies farther
    from any landmark than the measured round trip allows."""
    return all(haversine_km(claimed, lm) <= max_distance_km(r, km_per_ms) for lm, r in measurements)


def verify_in_region(center: tuple, radius_km: float, measurements: list, km_per_ms: float = FIBRE_KM_PER_MS) -> bool:
    """Sufficient test that the chip is inside the disc (center, radius_km): some landmark's feasible disc lies wholly
    inside it (triangle inequality: d(landmark, center) + feasible radius <= radius_km). Conservative by construction."""
    return any(haversine_km(center, lm) + max_distance_km(r, km_per_ms) <= radius_km for lm, r in measurements)


@dataclass
class Chip:
    serial: str
    h100e: float
    entry: str                      # pre_pause | manufactured
    operator: str
    site: str
    host_state: str
    kind: str = "training_capable"  # or inference_only
    state: str = "registered"
    last_seen: float = 0.0


class Registry:
    def __init__(self, chain=None, silence_limit_s: float = 3600.0, lost_limit_s: float = 7 * 24 * 3600.0):
        self.chips, self.chain = {}, chain
        self.silence_limit, self.lost_limit = silence_limit_s, lost_limit_s

    def _log(self, event: str, c: Chip, now: float, **extra):
        if self.chain is not None:
            self.chain.append({"phase": "registry", "event": event, "serial": c.serial, "state": c.state,
                               "host_state": c.host_state, "at": now, **extra})

    def register(self, serial: str, h100e: float, entry: str, operator: str, site: str, host_state: str, now: float,
                 kind: str = "training_capable") -> Chip:
        if serial in self.chips:
            raise ValueError("serial already registered")
        c = self.chips[serial] = Chip(serial, h100e, entry, operator, site, host_state, kind, "registered", now)
        self._log("registered", c, now)
        return c

    def heartbeat(self, serial: str, now: float, claimed: tuple = None, measurements: list = None) -> Chip:
        """An attestation. If a location is claimed and the latency measurements make it impossible, the chip goes silent:
        it has to be produced for inspection."""
        c = self.chips[serial]
        if c.state in ("destroyed",):
            raise ValueError("destroyed chips do not attest")
        if claimed is not None and measurements and not consistent_with_claim(claimed, measurements):
            c.state = "silent"
            self._log("location_impossible", c, now)
            return c
        c.last_seen, c.state = now, "in_service"
        return c

    def sweep(self, now: float) -> list:
        """Mark chips silent, then lost. Returns the serials whose state changed."""
        changed = []
        for c in self.chips.values():
            if c.state in ("destroyed", "lost"):
                continue
            gap = now - c.last_seen
            new = "lost" if gap > self.lost_limit else "silent" if gap > self.silence_limit else c.state
            if new != c.state:
                c.state = new
                changed.append(c.serial)
                self._log("state_change", c, now)
        return changed

    def produce_for_inspection(self, serial: str, now: float) -> Chip:
        c = self.chips[serial]
        if c.state == "lost":
            raise ValueError("a chip presumed lost is charged until it is produced and re-registered by the authorities")
        c.state, c.last_seen = "in_service", now
        self._log("inspected", c, now)
        return c

    def transfer(self, serial: str, operator: str, site: str, host_state: str, now: float) -> Chip:
        """A change of owner, location or jurisdiction needs re-registration."""
        c = self.chips[serial]
        if c.state not in ("registered", "in_service"):
            raise ValueError("only a chip in good standing can be transferred")
        c.operator, c.site, c.host_state, c.last_seen = operator, site, host_state, now
        self._log("transferred", c, now)
        return c

    def destroy(self, serial: str, witness: str, now: float) -> Chip:
        """The only approved exit from governance."""
        c = self.chips[serial]
        c.state = "destroyed"
        self._log("destroyed", c, now, witness=witness)
        return c

    def charged_as_dark(self, charge: float = 1.0) -> dict:
        """H100e charged to each host state's ledgers as dark compute: chips presumed lost, at `charge` of full capacity."""
        out = {}
        for c in self.chips.values():
            if c.state == "lost":
                out[c.host_state] = out.get(c.host_state, 0.0) + charge * c.h100e
        return out

    def in_good_standing(self) -> float:
        return sum(c.h100e for c in self.chips.values() if c.state in ("registered", "in_service"))
