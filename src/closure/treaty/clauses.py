"""Suspended clauses: measures agreed in advance that stay off until a named panel signs a finding, then switch on.

An agreement can carry its enforcement inside it: a ladder of measures, each tied to a threshold, none in force until
the body the agreement names finds that the threshold was crossed. Nothing is negotiated at that point; the finding is
the switch. CBPAI's Deal of the Century asks for clauses of this kind, and the middle-powers paper's ladder
(coalition.py) is one.

Here the finding is a record ({"type": "finding", "actor", "findings", "issued", "expires"}) and the switch is a
k-of-n signature over that exact record by the panel's members (quorum.py). `in_force` checks the signatures first and
reads the ladder only if they hold, so a finding that is unsigned, short of its quorum, expired, altered after
signing, or signed by people who are not on the panel switches nothing on. Whether the finding is true is the panel's
business; that it was made, by whom, about what, is what this makes checkable by anyone.
"""
from __future__ import annotations

from . import coalition as C
from . import quorum as Q


def finding(actor: str, findings: dict, issued: float, expires: float = None, note: str = None) -> dict:
    """The record a panel signs. `findings` uses coalition.FINDINGS' keys; unknown keys raise now, not at signing."""
    C.assess(findings)
    rec = {"type": "finding", "actor": str(actor), "findings": dict(findings), "issued": float(issued)}
    if expires is not None:
        rec["expires"] = float(expires)
    if note:
        rec["note"] = str(note)
    return rec


def in_force(record: dict, approvals: list, members: dict, k: int, now: float) -> dict:
    """What a signed finding switches on. {in_force, level, measure, reasons, actor, quorum}: level 0 and nothing in
    force unless at least k distinct panel members signed this exact record and it has not expired."""
    q = Q.verify(record, approvals, members, k, now)
    ok = bool(q["approved"]) and record.get("type") == "finding"
    if q["approved"] and not ok:
        q = {**q, "problems": q["problems"] + ["the signed record is not a finding"]}
    level, reasons = C.assess(record.get("findings") or {}) if ok else (0, [])
    return {"in_force": bool(ok and level > 0), "level": level, "measure": C.LEVELS[level], "reasons": reasons,
            "actor": record.get("actor"), "quorum": q}


def timeline(monthly: list, members: dict, k: int) -> list:
    """Month by month, the measure in force for one actor: `monthly` is a list of {"record", "approvals"} (or None for
    a month with no finding). A month counts only if its finding carried a quorum when it was issued; the six-month
    persistence rules of the ladder (coalition.run_timeline) then apply to the months that count."""
    counted, checks = [], []
    for m in monthly:
        if not m:
            counted.append({})
            checks.append(None)
            continue
        rec = m["record"]
        q = Q.verify(rec, m.get("approvals") or [], members, k, rec.get("issued", 0.0))
        signed = bool(q["approved"]) and rec.get("type") == "finding"
        counted.append(rec["findings"] if signed else {})
        checks.append(signed)
    out = C.run_timeline(counted)
    for row, signed in zip(out, checks):
        row["finding_signed"] = signed
    return out
