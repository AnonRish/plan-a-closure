"""Deadlines in the two draft agreements, checked against a log of dated events.

[MA] MIRI's draft agreement (arXiv:2511.10783): the first register of covered chip clusters and their consolidation
within 120 days of entry into force, an updated register no later than every 90 days (Art. V ss.3, 5); notice no
less than 14 days before a chip transfer (V s.6); access within 24 hours of a challenge inspection being called
(X s.3(c)); acknowledgement within 36 hours and clarification within 5 days of a concern (XI s.1(a)); review
conferences three years after entry into force and every three years after (XIV s.5); 12 months' notice of withdrawal
(XV s.2); and the Director-General's emergency changes, which lapse after 30 days without the Council's approval
(III s.4(d)(i)).

[FLI] FLI's Draft Articles: certificates of compliance renewed every six months (Art. 7(4)); a challenge accepted or
rejected within a week (7(10)); rules of procedure no later than 15 days after entry into force (12(3)); a Conference
session every quarter (12(2)); a yearly report on emergency measures from each State Party (8(2)); a yearly review of
the annexes (13(9)(l), 15(3)).

An event is {"type", "at", "subject"}: `at` is Unix seconds or an ISO 8601 time (UTC if no offset is given);
`subject` names what the deadline is about (a Party, a provider, a transfer, a concern), so a renewal by one provider
does not count for another. Events without a subject (entry into force) start the clock for every subject in
`subjects`. Months are calendar months (31 January + 1 month = 28 or 29 February).
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import datetime, timezone

UNITS = ("hours", "days", "months", "years")


@dataclass(frozen=True)
class Rule:
    key: str
    source: str            # "MA" or "FLI"
    ref: str
    start: tuple           # event types that start (or, if repeat, restart) the clock
    due: tuple             # event types that satisfy it
    amount: float
    unit: str
    what: str
    repeat: bool = False   # every due event restarts the clock (renewals, register updates, review conferences)
    notice: bool = False   # the due event may come no sooner than the period after the start (notice periods)
    lapse: bool = False    # missing it is not a breach: the thing started simply lapses
    per_subject: bool = True


RULES = (
    Rule("ma-register", "MA", "Art. V s.5", ("entry_into_force",), ("register_submitted",), 120, "days",
         "first register of covered chip clusters to the CTB"),
    Rule("ma-register-update", "MA", "Art. V s.5", ("register_submitted",), ("register_submitted",), 90, "days",
         "updated and accurate register no later than every 90 days", repeat=True),
    Rule("ma-consolidation", "MA", "Art. V s.3", ("entry_into_force",), ("consolidated",), 120, "days",
         "covered chip clusters located, inventoried and consolidated into declared facilities"),
    Rule("ma-transfer-notice", "MA", "Art. V s.6", ("transfer_notified",), ("transfer",), 14, "days",
         "notice no less than 14 days before a planned transfer of AI chips", notice=True),
    Rule("ma-challenge-access", "MA", "Art. X s.3(c)", ("challenge_called",), ("access_granted",), 24, "hours",
         "access to the site within 24 hours of the Council calling a challenge inspection"),
    Rule("ma-dispute-ack", "MA", "Art. XI s.1(a)", ("concern_notified",), ("acknowledged",), 36, "hours",
         "the Requested Party acknowledges the concern"),
    Rule("ma-dispute-clarify", "MA", "Art. XI s.1(a)", ("concern_notified",), ("clarified",), 5, "days",
         "the Requested Party provides clarification"),
    Rule("ma-review-first", "MA", "Art. XIV s.5", ("entry_into_force",), ("review_conference",), 3, "years",
         "first review conference", per_subject=False),
    Rule("ma-review", "MA", "Art. XIV s.5", ("review_conference",), ("review_conference",), 3, "years",
         "a review conference every three years", repeat=True, per_subject=False),
    Rule("ma-withdrawal", "MA", "Art. XV s.2", ("withdrawal_notified",), ("withdrawal_effective",), 12, "months",
         "withdrawal takes effect no sooner than 12 months after notice to the CTB", notice=True),
    Rule("ma-emergency-change", "MA", "Art. III s.4(d)(i)", ("emergency_change",), ("council_approval",), 30, "days",
         "the Council approves the Director-General's change, or it lapses", lapse=True),
    Rule("fli-certificate", "FLI", "Art. 7(4)", ("certificate_issued",), ("certificate_renewed", "certificate_issued"),
         6, "months", "certificate of compliance renewed by a licensed evaluator every six months", repeat=True),
    Rule("fli-challenge", "FLI", "Art. 7(10)", ("challenge_filed",), ("challenge_decided",), 7, "days",
         "the Dispute Settlement Panel accepts or rejects a challenge within a week"),
    Rule("fli-rules-of-procedure", "FLI", "Art. 12(3)", ("entry_into_force",), ("rules_of_procedure_adopted",), 15,
         "days", "the Conference adopts its rules of procedure", per_subject=False),
    Rule("fli-emergency-report", "FLI", "Art. 8(2)", ("entry_into_force", "emergency_report"), ("emergency_report",),
         1, "years", "each State Party's annual report on emergency measures", repeat=True),
    Rule("fli-annex-review", "FLI", "Art. 13(9)(l), 15(3)", ("entry_into_force", "annex_review"), ("annex_review",),
         1, "years", "the Agency's annual review of the annexes", repeat=True, per_subject=False),
)
QUARTERLY = {"key": "fli-conference", "source": "FLI", "ref": "Art. 12(2)", "due": "conference_session",
             "what": "the Conference meets once per quarter"}


def ts(x) -> float:
    """Unix seconds from a number or an ISO 8601 string (UTC unless it carries an offset)."""
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace("Z", "+00:00")
    d = datetime.fromisoformat(s)
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.timestamp()


def iso(t: float) -> str:
    return datetime.fromtimestamp(float(t), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def add_months(t: float, months: int) -> float:
    d = datetime.fromtimestamp(float(t), tz=timezone.utc)
    m = d.month - 1 + int(months)
    y, m = d.year + m // 12, m % 12 + 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return d.replace(year=y, month=m, day=day).timestamp()


def add(t: float, amount: float, unit: str) -> float:
    if unit == "hours":
        return float(t) + float(amount) * 3600.0
    if unit == "days":
        return float(t) + float(amount) * 86400.0
    if unit == "months":
        return add_months(t, int(amount))
    if unit == "years":
        return add_months(t, 12 * int(amount))
    raise ValueError(f"unit is one of {UNITS}")


def _late(t_due: float, t_done: float) -> str:
    h = (t_done - t_due) / 3600.0
    return f"{h:.1f} h late" if h < 48 else f"{h / 24.0:.1f} days late"


def _row(rule: Rule, subject: str, start: float, deadline: float, done, status: str, note: str = "") -> dict:
    return {"rule": rule.key, "source": rule.source, "ref": rule.ref, "what": rule.what, "subject": subject,
            "started": iso(start), "deadline": iso(deadline), "done": iso(done) if done is not None else None,
            "status": status, "note": note}


def _check_rule(rule: Rule, events: list, subject: str, now: float) -> list:
    mine = (lambda e: True) if not rule.per_subject else (lambda e: e.get("subject", "") == subject)
    starts = sorted(e["_t"] for e in events if e["type"] in rule.start and (mine(e) or not e.get("subject")))
    dues = sorted(e["_t"] for e in events if e["type"] in rule.due and mine(e))
    out = []
    if not starts:
        return out
    if rule.repeat:
        t0 = starts[0]
        last = t0
        for d in [x for x in dues if x > t0]:
            dl = add(last, rule.amount, rule.unit)
            out.append(_row(rule, subject, last, dl, d, "met" if d <= dl else "missed",
                            "" if d <= dl else _late(dl, d)))
            last = d
        dl = add(last, rule.amount, rule.unit)
        out.append(_row(rule, subject, last, dl, None, "overdue" if now > dl else "pending"))
        return out
    for s in starts:
        dl = add(s, rule.amount, rule.unit)
        after = [d for d in dues if d >= s]
        done = after[0] if after else None
        if rule.notice:
            if done is None:
                out.append(_row(rule, subject, s, dl, None, "pending", "nothing has happened yet"))
            else:
                ok = done >= dl
                out.append(_row(rule, subject, s, dl, done, "met" if ok else "missed",
                                "" if ok else f"only {(done - s) / 86400.0:.1f} days after notice"))
        elif done is not None:
            ok = done <= dl
            out.append(_row(rule, subject, s, dl, done, "met" if ok else ("lapsed" if rule.lapse else "missed"),
                            "" if ok else _late(dl, done)))
        else:
            late = now > dl
            out.append(_row(rule, subject, s, dl, None,
                            ("lapsed" if rule.lapse else "overdue") if late else "pending"))
    return out


def _quarter(t: float) -> tuple:
    d = datetime.fromtimestamp(float(t), tz=timezone.utc)
    return d.year, (d.month - 1) // 3


def _quarter_start(year: int, q: int) -> float:
    return datetime(year, 3 * q + 1, 1, tzinfo=timezone.utc).timestamp()


def _check_quarters(events: list, now: float) -> list:
    """Art. 12(2): a session in every full calendar quarter after entry into force (the quarter of entry into force
    and the quarter still running are not judged)."""
    eif = sorted(e["_t"] for e in events if e["type"] == "entry_into_force")
    if not eif:
        return []
    sessions = [e["_t"] for e in events if e["type"] == QUARTERLY["due"]]
    y, q = _quarter(eif[0])
    out, (ny, nq) = [], _quarter(now)
    q += 1
    while True:
        y, q = y + q // 4, q % 4
        if (y, q) >= (ny, nq):
            break
        a = _quarter_start(y, q)
        b = _quarter_start(y + (q + 1) // 4, (q + 1) % 4)
        hit = [s for s in sessions if a <= s < b]
        out.append({"rule": QUARTERLY["key"], "source": "FLI", "ref": QUARTERLY["ref"], "what": QUARTERLY["what"],
                    "subject": f"{y} Q{q + 1}", "started": iso(a), "deadline": iso(b - 1),
                    "done": iso(hit[0]) if hit else None, "status": "met" if hit else "missed", "note": ""})
        q += 1
    return out


def check(events: list, now, subjects=None, source: str = None) -> list:
    """Every deadline the events start, with its status: met, missed (done late, or a notice period cut short),
    overdue (not done and past due), pending (not due yet), lapsed (an emergency change the Council let lapse).
    `subjects` lists who owes per-subject duties when the clock starts for everyone (the Parties, at entry into
    force); subjects named in the events are added. `source` keeps one agreement ("MA" or "FLI")."""
    now = ts(now)
    evs = [{**e, "_t": ts(e["at"])} for e in events]
    evs = [e for e in evs if e["_t"] <= now]
    out = []
    for r in RULES:
        if source and r.source != source:
            continue
        if not r.per_subject:
            out += _check_rule(r, evs, "", now)
            continue
        subs = [e["subject"] for e in evs if e["type"] in r.start and e.get("subject")]
        if any(e["type"] in r.start and not e.get("subject") for e in evs):
            subs = list(subjects or []) + subs           # a clock started for everyone runs for each named subject
        for s in dict.fromkeys(subs):
            out += _check_rule(r, evs, s, now)
    if source in (None, "FLI"):
        out += _check_quarters(evs, now)
    return out


def failures(rows: list) -> list:
    return [r for r in rows if r["status"] in ("missed", "overdue")]


def term_problems(appointments: list, max_terms: int) -> list:
    """Term limits: FLI Art. 13(3), a Director-General's three-year term renewable once; MIRI Art. III s.4(b), a
    four-year term renewable once. appointments: [{"person", "start"}]; nobody may serve more than max_terms."""
    seen = {}
    for a in sorted(appointments, key=lambda a: ts(a["start"])):
        seen[a["person"]] = seen.get(a["person"], 0) + 1
    return [f"{p} appointed {n} times; at most {max_terms} terms" for p, n in seen.items() if n > int(max_terms)]


def until(t, amount: float, unit: str) -> str:
    """When a period that starts at t ends (ISO), e.g. until(notice, 12, 'months') for a withdrawal."""
    return iso(add(ts(t), amount, unit))
