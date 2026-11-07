"""A conserving stock ledger: accounts keyed by (owner, category), changed only by posted events.

Events are atomic: one that would break an invariant (negative balance, bad amount) raises and leaves the
ledger exactly as it was.  Production adds to the world total, retirement removes from it, a transfer moves
stock between accounts and never changes the total.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

Key = Tuple[str, str]


class LedgerError(ValueError):
    pass


@dataclass(frozen=True)
class Event:
    kind: str                       # produce | retire | transfer
    amount: float
    to: Optional[Key] = None        # produce, transfer
    frm: Optional[Key] = None       # retire, transfer
    memo: str = ""

    def to_dict(self) -> dict:
        d = {"kind": self.kind, "amount": self.amount}
        if self.to:
            d["to"] = list(self.to)
        if self.frm:
            d["from"] = list(self.frm)
        if self.memo:
            d["memo"] = self.memo
        return d

    @staticmethod
    def from_dict(d: dict) -> "Event":
        return Event(d["kind"], float(d["amount"]), tuple(d["to"]) if d.get("to") else None,
                     tuple(d["from"]) if d.get("from") else None, d.get("memo", ""))


def produce(to: Key, amount: float, memo: str = "") -> Event:
    return Event("produce", amount, to=to, memo=memo)


def retire(frm: Key, amount: float, memo: str = "") -> Event:
    return Event("retire", amount, frm=frm, memo=memo)


def transfer(frm: Key, to: Key, amount: float, memo: str = "") -> Event:
    return Event("transfer", amount, to=to, frm=frm, memo=memo)


def _undo(bal: Dict[Key, float], events: Iterable[Event]) -> None:
    """Reverse ``events`` (given newest first) on ``bal`` in place."""
    for ev in events:
        if ev.kind == "produce":
            bal[ev.to] = bal.get(ev.to, 0.0) - ev.amount
        elif ev.kind == "retire":
            bal[ev.frm] = bal.get(ev.frm, 0.0) + ev.amount
        else:
            bal[ev.to] = bal.get(ev.to, 0.0) - ev.amount
            bal[ev.frm] = bal.get(ev.frm, 0.0) + ev.amount


class Ledger:
    def __init__(self, unit: str = "H100e", opening: Optional[Dict[Key, float]] = None):
        self.unit = unit
        self._bal: Dict[Key, float] = {}
        self.history: List[Event] = []
        self.opening_total = 0.0
        self.produced = 0.0
        self.retired = 0.0
        for k, v in (opening or {}).items():
            if v < 0:
                raise LedgerError("opening balance of %s is negative" % (k,))
            self._bal[k] = float(v)
            self.opening_total += float(v)

    # -- queries ----------------------------------------------------------------------------------------
    def balance(self, owner: str, category: str) -> float:
        return self._bal.get((owner, category), 0.0)

    def total(self, owner: Optional[str] = None, category: Optional[str] = None) -> float:
        return sum(v for (o, c), v in self._bal.items()
                   if (owner is None or o == owner) and (category is None or c == category))

    def by_owner(self) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for (o, _), v in self._bal.items():
            out[o] = out.get(o, 0.0) + v
        return out

    def by_category(self) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for (_, c), v in self._bal.items():
            out[c] = out.get(c, 0.0) + v
        return out

    def accounts(self) -> Dict[Key, float]:
        return dict(self._bal)

    # -- posting ----------------------------------------------------------------------------------------
    def post(self, ev: Event) -> None:
        amt = ev.amount
        if not (amt > 0) or amt != amt or amt == float("inf"):
            raise LedgerError("amount must be a positive finite number")
        if ev.kind == "produce":
            if ev.to is None or ev.frm is not None:
                raise LedgerError("produce needs a destination and no source")
            self._bal[ev.to] = self._bal.get(ev.to, 0.0) + amt
            self.produced += amt
        elif ev.kind == "retire":
            if ev.frm is None or ev.to is not None:
                raise LedgerError("retire needs a source and no destination")
            if self._bal.get(ev.frm, 0.0) < amt:
                raise LedgerError("retiring %g from %s exceeds its balance %g" % (amt, ev.frm, self._bal.get(ev.frm, 0.0)))
            self._bal[ev.frm] -= amt
            self.retired += amt
        elif ev.kind == "transfer":
            if ev.frm is None or ev.to is None:
                raise LedgerError("transfer needs a source and a destination")
            if self._bal.get(ev.frm, 0.0) < amt:
                raise LedgerError("transferring %g from %s exceeds its balance %g" % (amt, ev.frm, self._bal.get(ev.frm, 0.0)))
            self._bal[ev.frm] -= amt
            self._bal[ev.to] = self._bal.get(ev.to, 0.0) + amt
        else:
            raise LedgerError("unknown event kind %r" % ev.kind)
        self.history.append(ev)

    def post_all(self, events: Iterable[Event]) -> None:
        """All or nothing: if any event fails the ledger is restored to its state before the call."""
        snap = (dict(self._bal), len(self.history), self.produced, self.retired)
        try:
            for ev in events:
                self.post(ev)
        except LedgerError:
            self._bal, n, self.produced, self.retired = snap
            del self.history[n:]
            raise

    # -- invariants and serialisation --------------------------------------------------------------------
    def conservation_error(self) -> float:
        """Total minus (opening + produced - retired); zero up to floating-point rounding."""
        return self.total() - (self.opening_total + self.produced - self.retired)

    def check(self, tol: float = 1e-9) -> None:
        scale = max(1.0, abs(self.opening_total) + self.produced + self.retired)
        if any(v < -tol * scale for v in self._bal.values()):
            raise LedgerError("negative balance")
        if abs(self.conservation_error()) > tol * scale:
            raise LedgerError("conservation violated by %g" % self.conservation_error())

    def opening_position(self) -> Dict[Key, float]:
        """The balances before any posted event, recovered by undoing the history."""
        bal = dict(self._bal)
        _undo(bal, reversed(self.history))
        return {k: v for k, v in bal.items() if abs(v) >= 1e-9}

    def to_dict(self) -> dict:
        return {"unit": self.unit, "opening": [[o, c, v] for (o, c), v in sorted(self.opening_position().items())],
                "events": [e.to_dict() for e in self.history]}

    def digest(self) -> str:
        """SHA-256 of the canonical JSON of the opening position and the event history."""
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    @staticmethod
    def from_dict(d: dict) -> "Ledger":
        led = Ledger(d.get("unit", "H100e"), {(o, c): float(v) for o, c, v in d.get("opening", [])})
        led.post_all(Event.from_dict(e) for e in d.get("events", []))
        return led
