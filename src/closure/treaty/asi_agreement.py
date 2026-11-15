"""The draft agreement of MIRI's Technical Governance Team as rules a computer can apply.

Source: Scher, Abecassis, Barnett and Abeyta, *An International Agreement to Prevent the Premature Creation of
Artificial Superintelligence* (arXiv:2511.10783, v3); article references are to the agreement's text, "Appendix D"
to the paper's appendix on chip consolidation. What is here: what counts as a FLOP, an H100-equivalent and a covered
chip cluster (Art. II); which training runs are banned, which need declaring and both sides' inspectors, and which
need nothing (Art. IV); Council consensus, vetoes over the CTB and the Director-General's 30-day emergency changes
(Art. III); the register, transfers and certified destruction (Arts. V and VI); powered-off verification (Art. VII
s.3); challenge inspections (Art. X s.3); Protective Action Statements (Art. XII s.6); and the paper's Tables 1 and 2
and staged registration (Appendix D.3). Deadlines (120 and 90 days, 14 days, 24 and 36 hours, 5 days, 3 years, 12
months) are in obligations.py.

Where the text leaves something open, the function takes it as a parameter and says so: how a non-FP16 operation
converts to FP16-equivalent ones (Art. II s.4 gives no method), whether post-training compute counts toward the Strict
Threshold, whether the Party to be inspected takes part in the consensus that approves a challenge inspection (Art. X
s.3(b) does not say), and whether "20 times per year" means a calendar year (Art. X s.3(e)).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np

from . import bandwidth as W
from . import quorum as Q

DAY_S, HOUR_S = 86400.0, 3600.0

# ---- Article II: definitions ---------------------------------------------------------------------------------------
STRICT_FLOP = 1e24                   # s.8; Art. IV s.1 bans training above it
STRICT_POST_TRAINING_FLOP = 1e23     # s.9; Art. IV s.1 bans post-training above it
MONITORED_FLOP = 1e22                # s.10; Art. IV s.2: declared, approved by both sides' inspectors, monitored
ADVANCED_NODE_NM = 28.0              # s.11: made on a process at least as advanced as the 28 nm node
H100E_FP16_FLOP_S = 989e12           # s.15: one H100 SXM, 989 TFLOP/s in FP16 ...
H100E_TPP = 15_824.0                 # ... or a TPP of 15,824 TFLOP-bit/s
H100E_MEMORY_GB = 80.0               # s.16 note: 16 H100s have 1,280 GB of accelerator memory
CCC_H100E = 16.0                     # s.16: more than 16 H100e of computing capacity or of accelerator memory
CCC_LINK_GBPS = 25.0                 # s.16: inter-node aggregate bandwidth greater than 25 Gbit/s
AIRPORT_REACH_H = 12.0               # Art. V s.1(b)
H100_FP8_DENSE_TFLOP_S = 1979.0      # H100 SXM, dense FP8 (the "On the Definition of CCCs" note's 7.3 days use FP8)

# ---- Appendix D.3: Tables 1 and 2 as printed -------------------------------------------------------------------------
TABLE_SIZES = (100_000, 10_000, 1_000, 100, 16, 1)
TABLE_PRINTED = {
    "seconds_to_monitored": ("1.0e2", "1.0e3", "1.0e4", "1.0e5", "6.3e5", "1.0e7"),
    "seconds_to_strict": ("1.0e4", "1.0e5", "1.0e6", "1.0e7", "6.3e7", "1.0e9"),
    "days_to_monitored": ("0.001", "0.012", "0.1", "1.2", "7.3", "116.9"),
    "days_to_strict": ("0.1", "1.2", "11.7", "116.9", "730.7", "11691.0"),
    "days_to_register": ("Day 1", "Day 1", "Day 10", "Day 100", "Year 2", "Never"),
}
TABLE_FLOP_S_PER_H100E = 990e12      # the rate every printed cell matches (time_to_thresholds, compare_tables)


def tpp(mac_tops: float, bits: int) -> float:
    """Art. II s.15: Total Processing Performance = 2 x non-sparse MacTOPS x bit length of the multiply input."""
    return 2.0 * float(mac_tops) * int(bits)


def tpp_from_tflops(dense_tflop_s: float, bits: int) -> float:
    """The same from dense TFLOP/s: a multiply-accumulate is two operations, so TPP = TFLOP/s x bit length."""
    return tpp(float(dense_tflop_s) / 2.0, bits)


def chip_tpp(dense_tflop_s_by_bits: dict) -> float:
    """A chip's TPP, the largest over the formats it supports ({bits: dense TFLOP/s}), as export controls compute it.
    An H100 SXM gives 15,824 in FP16 (989 x 16) and 15,832 in FP8 (1,979 x 8)."""
    return max(tpp_from_tflops(v, b) for b, v in dense_tflop_s_by_bits.items())


def h100e_compute(tpp_total: float) -> float:
    return float(tpp_total) / H100E_TPP


def h100e_memory(memory_gb: float) -> float:
    return float(memory_gb) / H100E_MEMORY_GB


def counted_flop(native_ops: float, bits: int = 16, fp16_per_op: float = None) -> float:
    """Art. II s.4: FLOP are counted as FP16-equivalent operations or as operations in the format used, whichever is
    higher. The text gives no conversion. By default an operation on b-bit inputs is b/16 FP16 operations (the
    bit-length scaling of the TPP definition), so 8-bit and 4-bit runs count their own operations and a 32-bit run
    counts twice its own; pass fp16_per_op for another conversion."""
    k = int(bits) / 16.0 if fp16_per_op is None else float(fp16_per_op)
    return max(float(native_ops), float(native_ops) * k)


def is_advanced_chip(process_nm: float) -> bool:
    """Art. II s.11: made on a process node at least as advanced as 28 nm (a smaller number is more advanced)."""
    return float(process_nm) <= ADVANCED_NODE_NM


# ---- Article IV: which runs are banned, monitored or free --------------------------------------------------------------
BASE_THRESHOLDS = {"strict": STRICT_FLOP, "post_training": STRICT_POST_TRAINING_FLOP, "monitored": MONITORED_FLOP,
                   "ccc_h100e": CCC_H100E}


@dataclass(frozen=True)
class RunClass:
    category: str          # "prohibited" | "monitored" | "unmonitored"
    reasons: tuple
    needs: tuple = ()      # what Art. IV s.2 asks before a monitored run may start


MONITORED_NEEDS = ("report to the CTB before starting: training code, training data and a FLOP estimate (s.2(a))",
                   "explicit approval from inspectors of the U.S. and of the PRC, present at the facility (s.2(b))",
                   "only techniques on the AI Technique Whitelist (Art. II s.20, Art. IV s.2(b))")


def classify_run(pretraining_flop: float, post_training_flop: float = 0.0, cumulative: bool = True,
                 thresholds: dict = None) -> RunClass:
    """Art. IV ss.1-3. Banned above the Strict Threshold (1e24) or with post-training above 1e23; declared, approved and
    monitored above the Monitored Threshold (1e22); free below it. "Above" is strict, as the text says. The text does
    not say whether post-training counts toward the 1e24: with cumulative=True (the default) it does, which is the
    reading that cannot be evaded by calling the last part of a pretraining run post-training. `thresholds` takes
    the values in force (thresholds_in_force) when the Director-General has changed them."""
    t = {**BASE_THRESHOLDS, **(thresholds or {})}
    pre, post = float(pretraining_flop), float(post_training_flop)
    total = pre + post if cumulative else pre
    why = []
    if total > t["strict"]:
        why.append(f"training compute {total:.3g} FLOP is above the Strict Threshold {t['strict']:.0e} (Art. IV s.1)")
    if post > t["post_training"]:
        why.append(f"post-training {post:.3g} FLOP is above the Strict Post-training Threshold {t['post_training']:.0e} "
                   "(Art. IV s.1)")
    if why:
        return RunClass("prohibited", tuple(why))
    if max(total, post) > t["monitored"]:
        return RunClass("monitored", (f"{max(total, post):.3g} FLOP is above the Monitored Threshold "
                                      f"{t['monitored']:.0e} (Art. IV s.2)",), MONITORED_NEEDS)
    return RunClass("unmonitored", (f"at or below the Monitored Threshold {t['monitored']:.0e}: no CTB oversight or "
                                    "approval (Art. IV s.3)",))


DECLARATION_FIELDS = ("training_code", "training_data", "flop_estimate")


def declaration(run_id: str, facility: str, training_code: str, training_data: str, flop_estimate: float,
                techniques: list, post_training_flop: float = 0.0) -> dict:
    """The record a Party reports to the CTB before a run above the Monitored Threshold (Art. IV s.2(a)), and that the
    inspectors sign. Code and data are named by digest here; the CTB's access to them is supervised, not in the record."""
    return {"type": "training-declaration", "run": str(run_id), "facility": str(facility),
            "training_code": str(training_code), "training_data": str(training_data),
            "flop_estimate": float(flop_estimate), "post_training_flop": float(post_training_flop),
            "techniques": sorted(str(x) for x in techniques)}


def declaration_problems(decl: dict) -> list:
    out = [f"missing {f} (Art. IV s.2(a))" for f in DECLARATION_FIELDS if decl.get(f) in (None, "")]
    if decl.get("type") != "training-declaration":
        out.append("not a training declaration")
    return out


def approve_monitored_run(decl: dict, approvals: list, inspectors: dict, whitelist, now: float = 0.0,
                          parties=("US", "PRC"), thresholds: dict = None) -> dict:
    """May this declared run start? Art. IV s.2(b): runs above the Monitored Threshold need explicit approval from
    inspectors representing the U.S. and the PRC, and use only whitelisted techniques; either side may withhold.

    `inspectors` is the CTB's list, {public key hex: {"name", "party"}}; `approvals` are Ed25519 signatures over the
    exact declaration (quorum.sign). A run needs at least one valid signature from an inspector of every party in
    `parties`. Whether the inspectors were physically present is not something a signature shows."""
    problems = declaration_problems(decl)
    cls = classify_run(decl.get("flop_estimate") or 0.0, decl.get("post_training_flop") or 0.0,
                       thresholds=thresholds)
    out = {"category": cls.category, "reasons": list(cls.reasons), "by_party": {}, "problems": problems}
    if cls.category == "prohibited":
        out["problems"] = problems + ["prohibited: no approval can allow it (Art. IV s.1)"]
        out["may_start"] = False
        return out
    if cls.category == "unmonitored":
        out.update(problems=[], may_start=True,
                   note="at or below the Monitored Threshold: no declaration or approval is needed (Art. IV s.3)")
        return out
    off = [x for x in decl.get("techniques", []) if x not in set(whitelist)]
    if off:
        problems.append(f"techniques not on the AI Technique Whitelist: {', '.join(off)} (Art. II s.20)")
    known = set(inspectors)
    for a in approvals:
        if a.get("signer") not in known:
            problems.append(f"signer {str(a.get('signer'))[:16]} is not on the CTB's inspector list")
    for party in parties:
        members = {k: v["name"] for k, v in inspectors.items() if v.get("party") == party}
        mine = [a for a in approvals if a.get("signer") in members]
        q = Q.verify(decl, mine, members, 1, now)
        out["by_party"][party] = {"approved": q["approved"], "valid": q["valid"], "problems": q["problems"]}
        if not q["approved"]:
            problems.append(f"no valid approval from an inspector of {party} (Art. IV s.2(b))")
    out["problems"] = problems
    out["may_start"] = not problems
    return out


def within_declaration(decl: dict, counted_flop_at_most: float, thresholds: dict = None) -> dict:
    """A finished (or stopped) run against its declaration: the FLOP it can have done (for a mock run, drill.json's
    job_flop_at_most) against the estimate it was approved for and the Strict Threshold."""
    t = {**BASE_THRESHOLDS, **(thresholds or {})}
    c = float(counted_flop_at_most)
    return {"counted_flop_at_most": c, "declared": float(decl["flop_estimate"]),
            "within_estimate": c <= float(decl["flop_estimate"]), "below_strict": c <= t["strict"]}


# ---- Article II s.16: covered chip clusters ----------------------------------------------------------------------------
@dataclass(frozen=True)
class Host:
    id: str
    site: str
    tpp: float               # aggregate TPP of the host's chips
    memory_gb: float         # aggregate accelerator memory


def covered_clusters(hosts, links=(), together=(), link_gbps: float = CCC_LINK_GBPS,
                     ccc_h100e: float = CCC_H100E) -> list:
    """Art. II s.16. Chips are networked if they are physically co-located (here: the same site), if the inter-node
    aggregate bandwidth between them (the sum over links between distinct hosts) is greater than 25 Gbit/s, or if they
    are networked to perform workloads together (`together`: groups of host ids known to run one workload). A
    networked set is a covered chip cluster (CCC) if its computing capacity or its accelerator memory is more than 16
    H100e (TPP 253,184; 1,280 GB).

    Groups (sites, then declared work groups) are merged while the links between two groups add up to more than
    `link_gbps`, until nothing changes. `links` are (host id, host id, Gbit/s). Returns every networked group with its
    hosts, H100e by compute and by memory, the bandwidth that joined it, and whether it is covered."""
    hosts = list(hosts)
    by_id = {h.id: h for h in hosts}
    parent = {h.id: h.id for h in hosts}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    reason = {}
    sites = {}
    for h in hosts:
        sites.setdefault(h.site, []).append(h.id)
    for ids in sites.values():
        for x in ids[1:]:
            union(ids[0], x)
    for g in together:
        g = [x for x in g if x in by_id]
        for x in g[1:]:
            union(g[0], x)
            reason[find(g[0])] = "networked to perform workloads together"
    links = [(a, b, float(g)) for a, b, g in links if a in by_id and b in by_id]
    changed = True
    while changed:
        changed = False
        between = {}
        for a, b, g in links:
            ra, rb = find(a), find(b)
            if ra != rb:
                key = (min(ra, rb), max(ra, rb))
                between[key] = between.get(key, 0.0) + g
        for (ra, rb), g in sorted(between.items(), key=lambda kv: -kv[1]):
            if g > link_gbps and find(ra) != find(rb):
                union(ra, rb)
                reason[find(ra)] = f"links between them add up to {g:g} Gbit/s, more than {link_gbps:g}"
                changed = True
                break
    groups = {}
    for h in hosts:
        groups.setdefault(find(h.id), []).append(h)
    out = []
    for root, hs in sorted(groups.items(), key=lambda kv: -sum(h.tpp for h in kv[1])):
        ids = {h.id for h in hs}
        bw = sum((g for a, b, g in links if a in ids and b in ids and by_id[a].site != by_id[b].site), 0.0)
        hc, hm = h100e_compute(sum(h.tpp for h in hs)), h100e_memory(sum(h.memory_gb for h in hs))
        out.append({"hosts": sorted(ids), "sites": sorted({h.site for h in hs}), "h100e_compute": hc,
                    "h100e_memory": hm, "cross_site_gbps": bw,
                    "joined_by": reason.get(root, "co-located" if len({h.site for h in hs}) == 1 else ""),
                    "covered": bool(hc > ccc_h100e or hm > ccc_h100e)})
    return out


def cross_site_training_gbps(h100e_per_site: float = 16.0, sites: int = 2, utilization: float = 0.4,
                             tokens_per_step: float = 4e6, sync_every: int = 1, bytes_per_value: float = 2.0,
                             compression: float = 1.0, cap_gbps: float = CCC_LINK_GBPS,
                             flop_s_per_h100e: float = H100E_FP16_FLOP_S) -> dict:
    """What synchronous data-parallel training across `sites` sets of chips needs from each set's uplink, against the
    25 Gbit/s of Art. II s.16 (whose note says the bounds should make training across sub-CCC sets difficult).

    6 FLOP per parameter per token and a ring all-reduce of the gradients (bandwidth.py). The model size cancels: a
    model k times bigger takes k times fewer steps a second, so the bytes a second depend only on the cluster's FLOP/s,
    the tokens per step, the bytes per value and how often the sets synchronise."""
    flop_s = float(sites) * float(h100e_per_site) * float(flop_s_per_h100e) * float(utilization)
    params = 1e9                                                 # any value: it cancels (see the test)
    steps_per_s = flop_s / (6.0 * params * float(tokens_per_step))
    need = W.needed_gbps(params, steps_per_s, int(sites), int(sync_every), bytes_per_value, compression)
    return {"sites": int(sites), "h100e_per_site": float(h100e_per_site), "utilization": float(utilization),
            "tokens_per_step": float(tokens_per_step), "sync_every": int(sync_every),
            "bytes_per_value": float(bytes_per_value), "compression": float(compression),
            "needs_gbps": need, "cap_gbps": float(cap_gbps),
            "slowdown_at_cap": W.slowdown(cap_gbps, params, steps_per_s, int(sites), int(sync_every), bytes_per_value,
                                          compression),
            "each_set_is_a_ccc": float(h100e_per_site) > CCC_H100E,
            "link_counts_as_networked": float(cap_gbps) > CCC_LINK_GBPS}


# ---- Appendix D.3: time to the thresholds and staged registration --------------------------------------------------------
def time_to_thresholds(h100e: float, flop_s_per_h100e: float = TABLE_FLOP_S_PER_H100E, utilization: float = 1.0,
                       thresholds: dict = None) -> dict:
    t = {**BASE_THRESHOLDS, **(thresholds or {})}
    rate = float(h100e) * float(flop_s_per_h100e) * float(utilization)
    sm, ss = t["monitored"] / rate, t["strict"] / rate
    return {"h100e": float(h100e), "seconds_to_monitored": sm, "seconds_to_strict": ss,
            "days_to_monitored": sm / DAY_S, "days_to_strict": ss / DAY_S}


def registration_stage(h100e: float, boundaries: str = "table") -> str:
    """When a cluster must be registered and consolidated in the staged implementation (Appendix D.3.1, Table 1): Day 1
    above 10,000 H100e, Day 10 above 1,000, Day 100 above 100, Year 2 for all covered clusters, never below that.

    boundaries="table" puts each boundary size in the earlier stage, as Table 1 does (10,000 on Day 1, 16 in Year 2).
    boundaries="text" reads "above" and Art. II s.16's "greater than 16" strictly, so a cluster of exactly 16 H100e,
    which Table 1 registers in Year 2, is never covered."""
    x = float(h100e)
    ge = (lambda a, b: a >= b) if boundaries == "table" else (lambda a, b: a > b)
    if boundaries not in ("table", "text"):
        raise ValueError("boundaries is 'table' or 'text'")
    if ge(x, 10_000):
        return "Day 1"
    if ge(x, 1_000):
        return "Day 10"
    if ge(x, 100):
        return "Day 100"
    if ge(x, CCC_H100E):
        return "Year 2"
    return "Never"


def _round_as_printed(value: float, printed: str) -> str:
    if "e" in printed:                                         # two significant figures, as 6.3e5
        m, e = f"{value:.1e}".split("e")
        return f"{m}e{int(e)}"
    decimals = len(printed.split(".")[1]) if "." in printed else 0
    return f"{value:.{decimals}f}"


def tables(flop_s_per_h100e: float = TABLE_FLOP_S_PER_H100E, boundaries: str = "table") -> dict:
    """Tables 1 and 2 of Appendix D.3, recomputed: {row: [cell for each of TABLE_SIZES]}, each cell rounded the way
    the paper prints it."""
    out = {k: [] for k in TABLE_PRINTED}
    for i, size in enumerate(TABLE_SIZES):
        r = time_to_thresholds(size, flop_s_per_h100e)
        for k in ("seconds_to_monitored", "seconds_to_strict", "days_to_monitored", "days_to_strict"):
            out[k].append(_round_as_printed(r[k], TABLE_PRINTED[k][i]))
        out["days_to_register"].append(registration_stage(size, boundaries))
    return out


def compare_tables(flop_s_per_h100e: float = TABLE_FLOP_S_PER_H100E, boundaries: str = "table") -> list:
    """Cells where the recomputed table differs from the printed one: [(row, H100e, printed, recomputed)]."""
    got = tables(flop_s_per_h100e, boundaries)
    return [(k, size, TABLE_PRINTED[k][i], got[k][i]) for k in TABLE_PRINTED for i, size in enumerate(TABLE_SIZES)
            if got[k][i] != TABLE_PRINTED[k][i]]


# ---- Article III: Council consensus, vetoes over the CTB, emergency changes ------------------------------------------------
EMERGENCY_DAYS = 30.0
EMERGENCY_KEYS = ("monitored", "strict", "post_training", "ccc_h100e")


def council_consensus(record: dict, approvals: list, council: dict, now: float = 0.0) -> dict:
    """Art. III s.3(c)(i): proactive Council decisions need consensus among members; without it the proposal fails.
    Read as every member signing the exact record. `council` is {public key hex: member}."""
    return Q.verify(record, approvals, council, len(council), now)


def veto_record(decision: dict) -> dict:
    return {"type": "veto", "decision": Q.action_digest(decision).hex()}


def ctb_decision_stands(decision: dict, vetoes: list, council: dict, now: float = 0.0) -> dict:
    """Art. III s.3(c)(ii): each Council member has a veto over CTB decisions. A veto is a member's signature over
    veto_record(decision). The text sets no window for vetoing, so a decision stands only until a member vetoes it."""
    q = Q.verify(veto_record(decision), vetoes, council, 1, now)
    return {"stands": not q["approved"], "vetoed_by": q["valid"], "problems": q["problems"]}


def emergency_change(changes: dict, issued: float, note: str = "") -> dict:
    """The record of a Director-General's time-sensitive change to thresholds or the covered cluster size (Art. III
    s.4(d)(i)); changes to research boundaries are not numbers and are not modelled."""
    bad = set(changes) - set(EMERGENCY_KEYS)
    if bad:
        raise ValueError(f"not something the Director-General can change here: {sorted(bad)}")
    rec = {"type": "emergency-change", "changes": {k: float(v) for k, v in changes.items()}, "issued": float(issued)}
    if note:
        rec["note"] = str(note)
    return rec


def thresholds_in_force(now: float, changes=(), council: dict = None) -> dict:
    """The thresholds in force at `now`. `changes` is a list of {"record": emergency_change(...), "approvals": [...]}:
    each is in force for 30 days from its issue (Art. III s.4(d)(i)) and after that only if the Council approved it by
    consensus (signatures of every member over the record). Later changes override earlier ones key by key."""
    t = dict(BASE_THRESHOLDS)
    log = []
    for c in sorted(changes, key=lambda c: c["record"]["issued"]):
        rec = c["record"]
        if rec["issued"] > now:
            continue
        age = (now - rec["issued"]) / DAY_S
        if age <= EMERGENCY_DAYS:
            state = "in force (within 30 days)"
        elif council and council_consensus(rec, c.get("approvals") or [], council, now)["approved"]:
            state = "in force (approved by the Council)"
        else:
            state = "lapsed (30 days passed without Council approval)"
        if state.startswith("in force"):
            t.update(rec["changes"])
        log.append({"issued": rec["issued"], "changes": rec["changes"], "state": state})
    return {**t, "log": log}


# ---- Articles V and VI: register, transfers, destruction ---------------------------------------------------------------
REGISTER_FIELDS = ("location", "type", "quantity", "interconnect")    # identifiers only "where available"


def register_problems(entries: list) -> list:
    """Art. V s.5: each register entry gives location, type, quantity and interconnects, and serial numbers or other
    unique identifiers where available. Duplicated identifiers are flagged."""
    out, seen = [], set()
    for i, e in enumerate(entries):
        out += [f"entry {i}: missing {f}" for f in REGISTER_FIELDS if e.get(f) in (None, "")]
        q = e.get("quantity")
        if q is not None and (not isinstance(q, (int, float)) or q < 0):
            out.append(f"entry {i}: quantity must be a non-negative number")
        for s in e.get("identifiers") or []:
            if s in seen:
                out.append(f"entry {i}: identifier {s} appears twice")
            seen.add(s)
    return out


TRANSFER_NOTICE_DAYS = 14.0
ITEMS = ("ai_chips", "manufacturing_equipment", "non_ai_advanced_chips")


def transfer_check(item: str, notified_at: float = None, planned_at: float = None, ctb_approved: bool = False,
                   to_non_party: bool = False, emergency: bool = False, from_production: bool = False,
                   ctb_objected: bool = False, council_consensus_given: bool = False, tracked: bool = True) -> dict:
    """May a transfer go ahead?

    AI chips (Art. V s.6): notice no less than 14 days before the planned transfer, and the CTB must approve before it
    proceeds; an emergency transfer is notified as soon as practicable and verified afterwards. For new chips from
    monitored production (Art. VI s.4) a transfer within Parties is presumed approved, so it goes ahead unless the CTB
    objects, and one to a non-Party is presumed denied. Manufacturing equipment needs Council consensus, with no
    presumption either way (VI s.4(b)). Advanced chips that are not AI chips may go to non-Parties only if the CTB
    authorises and tracks them (VI s.5) and move freely among Parties (VI s.6)."""
    if item not in ITEMS:
        raise ValueError(f"item is one of {ITEMS}")
    need, missing = [], []
    if item == "manufacturing_equipment":
        need.append("Executive Council consensus (Art. VI s.4(b))")
        if not council_consensus_given:
            missing.append("Council consensus")
    elif item == "non_ai_advanced_chips":
        if to_non_party:
            need.append("CTB authorisation and tracking (Art. VI s.5)")
            if not (ctb_approved and tracked):
                missing.append("CTB authorisation and tracking")
        else:
            need.append("nothing under Article VI (s.6)")
    else:
        if from_production and not to_non_party:
            need.append("tracked by the CTB; presumed approved unless the CTB objects (Art. VI s.4(a))")
            if ctb_objected:
                missing.append("the CTB objected")
        elif from_production and to_non_party:
            need.append("presumed denied: only an explicit CTB approval overrides it (Art. VI s.4(c))")
            if not ctb_approved:
                missing.append("CTB approval of a transfer to a non-Party")
        if emergency:
            need.append("notice to the CTB and the Council as soon as practicable; the CTB verifies it (Art. V s.6)")
            if notified_at is None:
                missing.append("emergency notice")
        else:
            need.append("notice no less than 14 days before the planned transfer (Art. V s.6)")
            if notified_at is None or planned_at is None:
                missing.append("notice")
            elif (planned_at - notified_at) / DAY_S < TRANSFER_NOTICE_DAYS:
                missing.append(f"notice was {(planned_at - notified_at) / DAY_S:.1f} days, under 14")
            if not from_production or to_non_party:
                need.append("CTB approval before it proceeds (Art. V s.6)")
                if not ctb_approved and "CTB approval of a transfer to a non-Party" not in missing:
                    missing.append("CTB approval")
    return {"item": item, "may_proceed": not missing, "requirements": need, "missing": missing}


class ChipStock:
    """Declared chips, with Art. V s.7's rule that decommissioned chips stay functional until the CTB certifies their
    destruction: a certificate names the chips and a CTB-approved method and carries a CTB signature."""

    STATES = ("declared", "decommissioned", "destroyed")

    def __init__(self, ctb_signers: dict, approved_methods=("shredding", "incineration")):
        self.ctb, self.methods = dict(ctb_signers), set(approved_methods)
        self.chips = {}

    def declare(self, serial: str, h100e: float, site: str):
        if serial in self.chips:
            raise ValueError("serial already declared")
        self.chips[serial] = {"h100e": float(h100e), "site": site, "state": "declared"}

    def decommission(self, serial: str):
        self.chips[serial]["state"] = "decommissioned"

    def certify_destruction(self, certificate: dict, approvals: list, now: float = 0.0) -> dict:
        problems = []
        if certificate.get("method") not in self.methods:
            problems.append(f"method {certificate.get('method')!r} is not CTB-approved")
        q = Q.verify(certificate, approvals, self.ctb, 1, now)
        if not q["approved"]:
            problems.append("no valid CTB signature on the certificate")
        unknown = [s for s in certificate.get("serials", []) if s not in self.chips]
        if unknown:
            problems.append(f"not declared: {unknown}")
        if not problems:
            for s in certificate["serials"]:
                self.chips[s]["state"] = "destroyed"
        return {"certified": not problems, "problems": problems}

    def resale_allowed(self, serial: str, ctb_authorised: bool = False) -> bool:
        """Salvage or resale of decommissioned chips is prohibited unless the CTB authorises it (Art. V s.7)."""
        return bool(ctb_authorised) and self.chips[serial]["state"] == "decommissioned"

    def functional_h100e(self) -> float:
        return sum(c["h100e"] for c in self.chips.values() if c["state"] != "destroyed")


def airport_reach_problems(travel_hours: dict) -> list:
    """Art. V s.1(b): verification teams can reach every CCC from an airport with scheduled international service
    within 12 hours. travel_hours: {facility: best door-to-door hours, as surveyed}."""
    return [f"{f}: {h:g} h from the nearest international airport, over 12" for f, h in travel_hours.items()
            if float(h) > AIRPORT_REACH_H]


# ---- Article VII s.3: powered off, verified continually ---------------------------------------------------------------
def powered_off(t, p, off_w: float, max_gap_s: float) -> dict:
    """Art. VII s.3: where verification is not sufficient, hardware is powered off and its non-operation verified
    continually. From an independent meter's trace (dcbus.py, meter-log): every sample at or under `off_w`, and no gap
    in the record longer than `max_gap_s`, since time without a reading is time not verified."""
    t, p = np.asarray(t, float), np.asarray(p, float)
    if len(t) < 2:
        return {"verified_off": False, "problems": ["fewer than two samples"]}
    gaps = np.diff(t)
    over = int(np.sum(p > off_w))
    problems = []
    if over:
        problems.append(f"{over} samples above {off_w:g} W (largest {float(p.max()):.1f} W)")
    if float(gaps.max()) > max_gap_s:
        problems.append(f"a gap of {float(gaps.max()):.1f} s in the record, over {max_gap_s:g} s")
    if np.any(gaps <= 0):
        problems.append("timestamps do not increase")
    return {"verified_off": not problems, "samples": int(len(t)), "max_w": float(p.max()),
            "longest_gap_s": float(gaps.max()), "covered_s": float(t[-1] - t[0]), "problems": problems}


# ---- Article X s.3: challenge inspections -----------------------------------------------------------------------------
CHALLENGE_ACCESS_H = 24.0
CHALLENGE_QUOTA = 20


def _year_key(ts: float) -> int:
    return datetime.fromtimestamp(float(ts), tz=timezone.utc).year


@dataclass
class ChallengeInspections:
    """Art. X s.3: approval by Council consensus (b); access within 24 hours of the Council's call (c); inspectors
    approved by both the inspected and the requesting Party, from lists the CTB keeps (d); at most 20 a year in a
    Party's territory unless the Council changes the limit by consensus (e).

    council: {public key hex: Party}. approved_inspectors: {Party: set of inspector ids that Party approved}.
    exclude_inspected: the text does not say whether the Party to be inspected joins the consensus. On the plain
    reading (False) it does, so a Council member can refuse an inspection of its own territory. year: "rolling" (any
    365 days) or "calendar"; on the calendar reading 40 inspections can fall within a few weeks around 1 January."""
    council: dict
    approved_inspectors: dict
    quota: int = CHALLENGE_QUOTA
    exclude_inspected: bool = False
    year: str = "rolling"
    done: list = field(default_factory=list)          # [(territory, called_at)]

    def _count(self, territory: str, now: float) -> int:
        if self.year == "calendar":
            return sum(1 for t, at in self.done if t == territory and _year_key(at) == _year_key(now))
        if self.year != "rolling":
            raise ValueError("year is 'rolling' or 'calendar'")
        return sum(1 for t, at in self.done if t == territory and now - 365 * DAY_S < at <= now)

    def call(self, record: dict, approvals: list, now: float) -> dict:
        """record: {"type": "challenge-inspection", "requested_by", "territory", "site", ...}; approvals: Council
        members' signatures over it."""
        territory = record.get("territory")
        members = {k: v for k, v in self.council.items() if not (self.exclude_inspected and v == territory)}
        q = Q.verify(record, approvals, members, len(members), now)
        problems = list(q["problems"])
        if not q["approved"]:
            missing = sorted(set(members.values()) - set(q["valid"]))
            problems.append(f"no Council consensus: missing {', '.join(missing) or 'nothing'} (Art. X s.3(b))")
        n = self._count(territory, now)
        if n >= self.quota:
            problems.append(f"{n} challenge inspections in {territory} within the year already: the limit is "
                            f"{self.quota} (Art. X s.3(e))")
        ok = q["approved"] and n < self.quota
        if ok:
            self.done.append((territory, float(now)))
        return {"approved": ok, "access_due": float(now) + CHALLENGE_ACCESS_H * HOUR_S if ok else None,
                "inspections_this_year": n + (1 if ok else 0), "problems": problems}

    def team_problems(self, team, inspected: str, requesting: str) -> list:
        """Art. X s.3(d): every inspector approved by both Parties."""
        out = []
        for x in team:
            for party in (inspected, requesting):
                if x not in self.approved_inspectors.get(party, set()):
                    out.append(f"{x} is not approved by {party}")
        return out


def access_in_time(called_at: float, granted_at: float) -> bool:
    """Art. X s.3(c): access within 24 hours of the Council's call."""
    return float(granted_at) - float(called_at) <= CHALLENGE_ACCESS_H * HOUR_S


# ---- Article XII s.6: Protective Action Statements ------------------------------------------------------------------
STATEMENT_ELEMENTS = {"purpose": "explains the protective purpose of the action (a)",
                      "targets": "identifies the specific AI-enabling activities and assets targeted (b)",
                      "cessation_conditions": "states the conditions for cessation (c)",
                      "commitment_to_cease": "commits to cease once those conditions are met (d)"}


def statement_problems(statement: dict) -> list:
    """Art. XII s.6: a public Protective Action Statement accompanies each action, with four elements."""
    return [f"missing: {v}" for k, v in STATEMENT_ELEMENTS.items() if not statement.get(k)]


def fp8_note_days(chips: int = 16, utilization: float = 0.5) -> dict:
    """The "On the Definition of CCCs" note: 16 H100s at FP8 and 50% utilization reach 1e22 FLOP in 7.3 days and
    1e24 in 2 years."""
    rate = int(chips) * H100_FP8_DENSE_TFLOP_S * 1e12 * float(utilization)
    return {"days_to_monitored": MONITORED_FLOP / rate / DAY_S, "years_to_strict": STRICT_FLOP / rate / DAY_S / 365.25}


def ccc_reference() -> dict:
    """Art. II s.16's note: 16 H100s are TPP 253,184 and 1,280 GB."""
    return {"tpp": CCC_H100E * H100E_TPP, "memory_gb": CCC_H100E * H100E_MEMORY_GB,
            "h100_tpp_fp16": tpp_from_tflops(989.0, 16)}
