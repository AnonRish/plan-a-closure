"""Chip authorization: the enforcement mechanism of FLI's Draft Articles (Annex C.1, a State Party signs; Annex C.2,
the Agency signs), which follows Petrie's firmware-based offline licensing (2024).

As the Annex and its commentary describe it, every chip used for AI development or deployment needs an authorization:
a file naming the chip, a number of allowed clock cycles and an identification number, signed with the enforcer's
private key(s). The chip's security processor checks the signature against the public key(s) in its firmware, records
the identification number so the file cannot be used twice, and refuses new computation when the allowed cycles run
out. Renewal is automatic and frequent ("potentially every few minutes") unless the Agency verifies a violation of
Article 3; then no new authorization is issued and the chips stop. Re-authorization after a correction is possible
(commentary (4)); a tamper attempt wipes the firmware and blows fuses (hardware, modelled here as a flag).

This module is that protocol in software, as a stand-in for the security processor, plus one option the text does not
have. An authorization that carries a number of cycles and a fresh identification number can be held unused: the
provider takes delivery of every renewal, hands the chip one only when it runs low, and keeps the rest. When renewal
stops, the provider still holds everything the chip did not use, so the chip runs on for as long as that lasts:
`simulate` and `bank_days` measure it. mode="fresh" binds each authorization to a nonce the chip has just generated
and is waiting on, as Petrie's later security-block design does (2025); an authorization cannot then be obtained
before the chip asks for it, so at most one is ever held back, and with a cap on the stored allowance the run-on is
bounded by about one renewal period however long the chip has been in use.

Units: an allowance is in cycles; `simulate` uses one cycle a second so that allowances read as seconds of running.
"""
from __future__ import annotations

import secrets

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from . import quorum as Q

MODES = ("as-written", "fresh")
DAY_S = 86400.0


def authorization(chip: str, cycles: int, auth_id: int, nonce: str = None, issuer: str = None) -> dict:
    """The file of Annex C's commentary (2): the chip it applies to, the number of allowed clock cycles and an
    identification number. `nonce` (fresh mode) is the challenge the chip is waiting on."""
    rec = {"type": "chip-authorization", "chip": str(chip), "cycles": int(cycles), "id": int(auth_id)}
    if nonce is not None:
        rec["nonce"] = str(nonce)
    if issuer:
        rec["issuer"] = str(issuer)
    return rec


def firmware_update(version: int, trusted: dict = None, k: int = None, cap_cycles: int = None, mode: str = None) -> dict:
    """A signed update to the security processor: it may change the 'ruleset' (commentary (4)): the trusted keys, how
    many signatures an authorization needs, the cap on the stored allowance, the mode. Annex C.1: States Parties
    install updates as regularly as needed; C.2: the Agency may require them."""
    rec = {"type": "firmware-update", "version": int(version)}
    for name, v in (("trusted", trusted), ("k", k), ("cap_cycles", cap_cycles), ("mode", mode)):
        if v is not None:
            rec[name] = v
    return rec


class Enforcer:
    """Holds the signing key(s): the State Party where the provider is located (C.1) or the Agency (C.2). Issues
    authorizations automatically unless renewal for the chip has been withheld after a verified violation."""

    def __init__(self, name: str, keys=None, n_keys: int = 1):
        self.name = str(name)
        self.keys = list(keys) if keys else [Ed25519PrivateKey.generate() for _ in range(int(n_keys))]
        self.withheld = set()
        self.next_id = 1
        self.answered = set()          # nonces already answered: one authorization per challenge

    def public(self) -> dict:
        return {Q.public_hex(k): f"{self.name}#{i}" for i, k in enumerate(self.keys)}

    def sign(self, record: dict) -> list:
        return [Q.sign(k, record) for k in self.keys]

    def issue(self, chip: str, cycles: int, nonce: str = None):
        """(record, approvals), or None if renewal is withheld for this chip or the nonce was already answered."""
        if chip in self.withheld or (nonce is not None and nonce in self.answered):
            return None
        rec = authorization(chip, cycles, self.next_id, nonce, self.name)
        self.next_id += 1
        if nonce is not None:
            self.answered.add(nonce)
        return rec, self.sign(rec)

    def cosign(self, record: dict) -> list:
        """A second enforcer's signatures on another's authorization, for k-of-n key sets (the enforcer's "private
        key(s)"); nothing if it withholds renewal for that chip."""
        return [] if record.get("chip") in self.withheld else self.sign(record)

    def withhold(self, chip: str):
        """A violation of Article 3 verified: no new authorization for the chips running the system (Annex C)."""
        self.withheld.add(chip)

    def resume(self, chip: str):
        """Corrective action: re-authorization once the provider corrects its conduct or shows the finding was wrong
        (commentary (4); Article 6(3))."""
        self.withheld.discard(chip)


class GuaranteeProcessor:
    """The chip side. trusted: {public key hex: name} as in the firmware binary; k: valid signatures an authorization
    needs; ids: "set" stores every identification number used (the text), "increasing" accepts only numbers above the
    last one (constant storage, and an old file cannot be replayed after a newer one, but files must arrive in order);
    cap_cycles: the most allowance the chip will hold (None: no cap)."""

    def __init__(self, chip: str, trusted: dict, k: int = 1, mode: str = "as-written", cap_cycles: int = None,
                 ids: str = "set", firmware_version: int = 1):
        if mode not in MODES:
            raise ValueError(f"mode is one of {MODES}")
        if ids not in ("set", "increasing"):
            raise ValueError("ids is 'set' or 'increasing'")
        self.chip, self.trusted, self.k, self.mode = str(chip), dict(trusted), int(k), mode
        self.cap, self.ids, self.firmware_version = cap_cycles, ids, int(firmware_version)
        self.allowance, self.ran = 0, 0
        self.used, self.last_id = set(), 0
        self.outstanding = None
        self.fused = False

    def challenge(self) -> str:
        """Fresh mode: a new nonce to send to the enforcer; it replaces any earlier one."""
        self.outstanding = secrets.token_hex(16)
        return self.outstanding

    def receive(self, record: dict, approvals: list) -> dict:
        problems = []
        if self.fused:
            return {"accepted": False, "problems": ["the chip is permanently disabled"]}
        if record.get("type") != "chip-authorization":
            problems.append("not an authorization")
        if record.get("chip") != self.chip:
            problems.append("issued for another chip")
        q = Q.verify(record, approvals, self.trusted, self.k, 0.0)
        if not q["approved"]:
            problems.append(f"{len(q['valid'])} valid signatures from trusted keys, {self.k} needed")
        rid = record.get("id")
        if not isinstance(rid, int):
            problems.append("no identification number")
        elif self.ids == "set" and rid in self.used:
            problems.append(f"identification number {rid} was already used")
        elif self.ids == "increasing" and rid <= self.last_id:
            problems.append(f"identification number {rid} is not above the last one used ({self.last_id})")
        if self.mode == "fresh" and (self.outstanding is None or record.get("nonce") != self.outstanding):
            problems.append("not bound to the challenge the chip is waiting on")
        if problems:
            return {"accepted": False, "problems": problems}
        self.used.add(rid)
        self.last_id = max(self.last_id, rid)
        self.allowance += int(record["cycles"])
        if self.cap is not None:
            self.allowance = min(self.allowance, int(self.cap))
        if self.mode == "fresh":
            self.outstanding = None
        return {"accepted": True, "allowance": self.allowance, "problems": []}

    def run(self, cycles: int) -> int:
        """Do up to `cycles` cycles of work; returns how many ran. At zero allowance the chip refuses new computation
        until a valid authorization arrives."""
        if self.fused:
            return 0
        n = max(0, min(int(cycles), self.allowance))
        self.allowance -= n
        self.ran += n
        return n

    def tamper(self):
        """A tamper attempt: firmware wiped and fuses blown (Annex C). Hardware; here a flag that never clears."""
        self.fused, self.allowance = True, 0

    def install_firmware(self, update: dict, approvals: list) -> dict:
        """A signed firmware update, accepted only with k valid signatures from the keys trusted now and a version
        above the current one (rollback protection, which Petrie (2024) lists among the security features needed)."""
        problems = []
        if self.fused:
            problems.append("the chip is permanently disabled")
        if update.get("type") != "firmware-update":
            problems.append("not a firmware update")
        if not Q.verify(update, approvals, self.trusted, self.k, 0.0)["approved"]:
            problems.append("not signed by enough trusted keys")
        if int(update.get("version", 0)) <= self.firmware_version:
            problems.append(f"version {update.get('version')} is not above {self.firmware_version}: rollback refused")
        if problems:
            return {"installed": False, "problems": problems}
        self.firmware_version = int(update["version"])
        if "trusted" in update:
            self.trusted = dict(update["trusted"])
        if "k" in update:
            self.k = int(update["k"])
        if "cap_cycles" in update:
            self.cap = update["cap_cycles"]
            if self.cap is not None:
                self.allowance = min(self.allowance, int(self.cap))
        if "mode" in update:
            if update["mode"] not in MODES:
                return {"installed": False, "problems": ["unknown mode"]}
            self.mode = update["mode"]
        return {"installed": True, "version": self.firmware_version, "problems": []}


def bank_days(days: float, period_s: float, allowance_s: float, duty: float = 1.0) -> float:
    """As written, the full-speed days of authorizations a provider holds after `days` of operation: everything issued
    (one authorization worth `allowance_s` every `period_s`) minus what the chip used (a share `duty` of full speed),
    since nothing stops the provider from taking delivery of a renewal it does not need yet."""
    return max(0.0, float(days) * (float(allowance_s) / float(period_s) - float(duty)))


def simulate(mode: str = "as-written", period_s: float = 300.0, allowance_s: float = 600.0, duty: float = 1.0,
             days: float = 30.0, hoard: bool = True, cap_s: float = None, ids: str = "set") -> dict:
    """Run one chip for `days` with the enforcer renewing every `period_s` (each authorization worth `allowance_s` of
    full-speed running), then the Agency verifies a violation and renewal stops. Returns how long the chip can keep
    computing at full speed after the stop ('run_on_s'), from what it holds and what its provider still holds.

    as-written: each period the enforcer issues an authorization and the provider takes it; with hoard=True the
    provider hands the chip one only when the chip is about to run out and keeps the rest; with hoard=False it hands
    over each one at once. fresh: the enforcer answers only the nonce the chip is waiting on, once; the chip makes a new
    nonce after accepting an authorization, so the provider can hold back at most the one it was just given."""
    if mode not in MODES:
        raise ValueError(f"mode is one of {MODES}")
    agency = Enforcer("Agency")
    chip = GuaranteeProcessor("chip-0", agency.public(), mode=mode, ids=ids,
                              cap_cycles=None if cap_s is None else int(cap_s))
    per, allow = int(period_s), int(allowance_s)
    need_per_period = int(round(float(duty) * per))
    held = []                                       # authorizations the provider has and the chip does not
    periods = int(float(days) * DAY_S / per)
    short = 0
    if mode == "fresh":
        chip.challenge()
    for _ in range(periods):
        nonce = chip.outstanding if mode == "fresh" else None
        if mode == "as-written" or nonce is not None:
            got = agency.issue(chip.chip, allow, nonce)
            if got is not None:
                held.append(got)
        if not hoard:
            while held:
                chip.receive(*held.pop(0))
                if mode == "fresh":
                    chip.challenge()
        while chip.allowance < need_per_period and held:
            chip.receive(*held.pop(0))
            if mode == "fresh":
                chip.challenge()
        short += need_per_period - chip.run(need_per_period)
    agency.withhold(chip.chip)                       # violation verified: renewal stops
    held_at_stop, run_on = len(held), 0
    while True:                                      # run flat out; hand over what is held, one file at a time
        run_on += chip.run(chip.allowance)
        delivered = False
        while held and not delivered:
            delivered = chip.receive(*held.pop(0))["accepted"]
        if not delivered:
            break
        if mode == "fresh":
            chip.challenge()
    if mode == "fresh":
        assert agency.issue(chip.chip, allow, chip.outstanding) is None    # renewal really stopped
    return {"mode": mode, "hoard": bool(hoard), "period_s": per, "allowance_s": allow, "duty": float(duty),
            "days": float(days), "cap_s": cap_s, "run_on_s": float(run_on), "run_on_days": run_on / DAY_S,
            "held_by_provider_at_stop": held_at_stop, "seconds_short_before_stop": float(short),
            "predicted_bank_days": bank_days(days, per, allow, duty) if mode == "as-written" else None}
