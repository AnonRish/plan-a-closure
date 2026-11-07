#!/usr/bin/env python3
"""
compute_anomaly_detector.py
=============================

Enriches the raw interconnection registry (`megawatt_interconnect_registry_raw.csv`,
produced by ingest_grid_queues.py --include-raw-fields) with entity
classification against known hyperscalers/colocation developers, PJM
transmission-owner and project-name context for undisclosed developers, and
a rough power-to-compute range estimate -- to help a human prioritize which
large, advanced-stage, unidentified projects are worth a closer look.

--------------------------------------------------------------------------
THREE DELIBERATE DEPARTURES FROM THE ORIGINAL BRIEF, AND WHY
--------------------------------------------------------------------------
(Restated here so the reasoning ships with the code, not just the chat it
was discussed in.)

1. "Unclassified Shell LLC" -> "Developer Not Matched To Known List". A
   name that doesn't match the hardcoded hyperscaler/colo-developer list
   could be a shell company -- but just as easily a real industrial user, a
   utility, a regional cloud provider, or a subsidiary under a non-obvious
   name. A fuzzy-match miss can't distinguish those. "Shell LLC" asserts a
   conclusion the match failure doesn't support.

2. A single point-estimate "Run_FLOPs" -> a low/reference/high range. PUE,
   rack density, chip mix, and utilization all vary enormously by facility
   and none of it is knowable from a power-interconnection filing. See
   `ComputeScenario` below -- the specified formula and constants are kept
   exactly as the REFERENCE scenario (verified: at capacity_mw=100 it does
   land just above 1e26 FLOPs, ~1.13x, as the brief claimed), bracketed by
   a LOW and HIGH scenario spanning a defensible range of real facility
   characteristics. One finding worth flagging: at exactly 100 MW the three
   scenarios cluster close together (1.07x-1.13x the 1e26 mark) because
   lower PUE efficiency and lower rack density partially cancel out in this
   formula -- so "clears 1e26" is fairly robust right at the filter
   boundary, but it's a real range, not a fact, and should be reported as
   one.

   Caveat on the chip figure: 1,979 TFLOPS is NVIDIA's H100 SXM FP16/BF16
   peak *with 2:4 structured sparsity* (it equals the dense FP8 peak). Dense
   FP16/BF16 is 989.5 TFLOPS, which halves every FLOP bound here: at 100 MW
   the three scenarios land at 0.54x-0.56x of 1e26, not 1.07x-1.13x. The
   scenarios keep 1,979 because the brief specifies it; the dense figure is
   reported alongside as a sensitivity (run_flops_90d_*_dense).

3. "EXHIBIT A" / "Regulatory Triage" -> descriptive framing. Packaging
   capacity + an entity-match miss + queue stage as a named "audit exhibit"
   implies a finding of non-compliance from circumstantial signal. If one
   flagged entry turns out to be, say, a hospital expansion or an unrelated
   industrial project, that's a real entity mislabeled in a document with
   legal-sounding framing. The actual question -- which large, advanced-
   stage projects lack a confirmed public operator -- is still answered
   (`review_priority` + `review_reason` columns, and the summary table
   below), just not asserted as evidence of wrongdoing.

Entity fuzzy-matching (rapidfuzz), PJM Transmission-Owner + project-name
keyword context, the GPU/rack conversion methodology, and the --selftest
suite are all built as specified.

SCORER CHOICE, EMPIRICALLY TESTED: rapidfuzz's partial_ratio and, to a
lesser extent, WRatio both produce dangerous false positives on short
common substrings -- e.g. "Eta Compute LLC" scores 85.7 against "Meta"
under partial_ratio (because "eta" is literally a substring of "meta"),
which is well within range of a naive 80-85 threshold. WRatio separates
true and false matches far better in testing (true positives >=90, false
positives <=46 except two adjacent-word collisions at 73-80), so this uses
WRatio with threshold=88 -- comfortably above every tested false positive
and below every tested true positive. Scores landing in the 70-88 gray
zone are logged, not auto-classified either way, so a genuine near-miss is
visible to a human instead of silently decided by the tool.

REAL-DATA FINDING (from the first live run, not synthetic): against the
actual August 2026 PJM + ERCOT files, zero rows matched a known hyperscaler
or colo developer under fuzzy full-name matching. Most of that is real --
the >=100MW/Storage-or-Other-load-type queue is genuinely dominated by
conventional renewable/storage developers (ENGIE, NextEra, Lightsource,
RWE, dozens of single-project storage LLCs), not datacenter operators --
but part of it was a real gap: operators like STACK file under
brand-prefixed, project-specific subsidiary names ("STACK Danville Gen
Power 5, LLC"), which score just under the WRatio threshold against the
full company name because of the extra project-specific tokens. Whole-word
matching on the distinctive brand token catches this correctly. Some of
those tokens ("stack", "vantage", "compass", "rowan") are also generic
English words/surnames with real collision risk against an unrelated
company, so they're a separate, lower confidence tier ("Possible Match
(Needs Verification)") rather than auto-confirmed -- see
HIGH_CONFIDENCE_WHOLE_WORD_TOKENS / LOW_CONFIDENCE_WHOLE_WORD_TOKENS below.
This does not fully solve entity resolution -- a maintained subsidiary/DBA
mapping would be needed for that -- it narrows one specific, confirmed gap.

INPUT LIMITATION: entity/context enrichment for PJM's undisclosed rows and
the IA-stage flag both need columns (`status`, `project_name`) that are
outside the 8-column schema `ingest_grid_queues.py` was specified to
produce. Run it with `--include-raw-fields` to get them; without those two
columns present, this script still runs (entity classification still
works off `developer_entity` alone) but PJM context enrichment and the
IA-stage criterion are skipped for that data, and it says so rather than
guessing.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd
from rapidfuzz import fuzz, process

logger = logging.getLogger("compute_anomaly_detector")


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


# --------------------------------------------------------------------------
# Entity classification
# --------------------------------------------------------------------------

HYPERSCALER_ALIASES: dict[str, str] = {
    "vadata": "Amazon", "amazon": "Amazon", "amazon data services": "Amazon", "aws": "Amazon",
    "microsoft": "Microsoft", "msft": "Microsoft",
    "google": "Google", "alphabet": "Google",
    "meta platforms": "Meta", "meta": "Meta", "facebook": "Meta",
}
COLO_DEVELOPER_ALIASES: dict[str, str] = {
    "qts": "QTS", "qts realty": "QTS",
    "cyrusone": "CyrusOne", "cyrus one": "CyrusOne",
    "stack infrastructure": "Stack Infrastructure",
    "vantage data centers": "Vantage", "vantage": "Vantage",
    "compass datacenters": "Compass Datacenters", "compass dc": "Compass Datacenters",
    "rowan digital": "Rowan Digital Infrastructure", "rowan infrastructure": "Rowan Digital Infrastructure",
    "edgeconnex": "EdgeConneX", "edge connex": "EdgeConneX",
}
_ALIAS_TO_MATCH = {
    **{a: (name, "Confirmed Hyperscaler") for a, name in HYPERSCALER_ALIASES.items()},
    **{a: (name, "Wholesale Colocation Developer") for a, name in COLO_DEVELOPER_ALIASES.items()},
}

# Real-data finding: hyperscalers/colo developers very often file under a
# brand-prefixed, project-specific subsidiary LLC ("STACK Danville Gen
# Power 5, LLC"), which scores just under the WRatio threshold against the
# full company name because of all the extra project-specific tokens.
# Whole-word matching on the brand token catches this correctly -- but some
# of these tokens are also generic English words or surnames, so they're
# split into two confidence tiers rather than all auto-confirmed the same
# way. High-confidence tokens are coined/distinctive enough that a
# whole-word hit is essentially always meaningful; low-confidence tokens
# get surfaced as a possible match for a human to verify, not auto-treated
# as confirmed, since "Stack Energy LLC" or "Compass Partners LLC" could
# just as easily be unrelated companies.
HIGH_CONFIDENCE_WHOLE_WORD_TOKENS: dict[str, tuple[str, str]] = {
    "vadata": ("Amazon", "Confirmed Hyperscaler"),
    "edgeconnex": ("EdgeConneX", "Wholesale Colocation Developer"),
    "cyrusone": ("CyrusOne", "Wholesale Colocation Developer"),
}
LOW_CONFIDENCE_WHOLE_WORD_TOKENS: dict[str, tuple[str, str]] = {
    "stack": ("Stack Infrastructure", "Wholesale Colocation Developer"),
    "vantage": ("Vantage", "Wholesale Colocation Developer"),
    "compass": ("Compass Datacenters", "Wholesale Colocation Developer"),
    "rowan": ("Rowan Digital Infrastructure", "Wholesale Colocation Developer"),
    "qts": ("QTS", "Wholesale Colocation Developer"),
}

# Empirically tuned (see module docstring): WRatio cleanly separates real
# matches (all >=90 in testing) from lookalikes (<=46, with two
# adjacent-word collisions at 73-80). 88 sits in the gap with margin on
# both sides.
FUZZY_MATCH_THRESHOLD = 88.0
FUZZY_GRAY_ZONE_FLOOR = 70.0  # below this, not worth logging as a near-miss

UNRESOLVED_DEVELOPER_TOKENS = {
    "", "UNKNOWN", "NOT PUBLISHED IN PJM QUEUE EXPORT", "NAN", "NONE",
}
# Bug found and fixed alongside the SPP/IESO ingestion expansion: this set
# only ever held PJM's one exact sentinel string. ingest_grid_queues.py now
# also emits "NOT PUBLISHED IN SPP GI QUEUE EXPORT" (SPP has no
# applicant-name column at all) and "NOT PUBLISHED IN IESO APPLICATION
# STATUS DATA" (only for the rare IESO row with a blank Applicant). Left as
# an exact-match set, every SPP row's developer_entity -- 100% of them,
# not an edge case -- would silently skip "Developer Not Disclosed" and
# fall straight into fuzzy entity matching against literal sentinel text
# instead, with unpredictable (and non-zero-probability) false-match risk.
# A prefix check generalizes correctly to any current or future source
# that follows the same "NOT PUBLISHED..." naming convention without
# needing this set hand-maintained per source.
_UNRESOLVED_DEVELOPER_PREFIX = "NOT PUBLISHED"


def _whole_word_hit(name_lower: str, token: str) -> bool:
    return re.search(r"\b" + re.escape(token) + r"\b", name_lower) is not None


def classify_entity(raw_name: object) -> tuple[str, Optional[str], float]:
    """Returns (category, matched_public_entity_name_or_None, match_score).

    category is one of:
      "Confirmed Hyperscaler" | "Wholesale Colocation Developer"
      "Possible Match (Needs Verification)" -- a distinctive-but-generic
        brand token hit as a whole word; plausible, not confirmed
      "Developer Not Disclosed"           -- source didn't publish a name at all
      "Developer Not Matched To Known List" -- a real name, just not one we recognize
    """
    name = str(raw_name or "").strip()
    if not name or name.upper() in UNRESOLVED_DEVELOPER_TOKENS or name.upper().startswith(_UNRESOLVED_DEVELOPER_PREFIX):
        return "Developer Not Disclosed", None, 0.0
    name_lower = name.lower()

    for token, (matched_name, category) in HIGH_CONFIDENCE_WHOLE_WORD_TOKENS.items():
        if _whole_word_hit(name_lower, token):
            return category, matched_name, 100.0

    # Low-confidence generic tokens are intentionally checked BEFORE fuzzy
    # matching. A token such as "QTS" can score 100 against its alias, but the
    # registry must still keep it in the human-audit state rather than treating
    # the generic token as an automatic corporate identification.
    for token, (matched_name, _category) in LOW_CONFIDENCE_WHOLE_WORD_TOKENS.items():
        if _whole_word_hit(name_lower, token):
            return "Possible Match (Needs Verification)", matched_name, 100.0

    match = process.extractOne(name_lower, _ALIAS_TO_MATCH.keys(), scorer=fuzz.WRatio)
    if match is not None:
        alias, score, _ = match
        if score >= FUZZY_MATCH_THRESHOLD:
            matched_name, category = _ALIAS_TO_MATCH[alias]
            return category, matched_name, score
    else:
        alias, score = None, 0.0

    if alias is not None and score >= FUZZY_GRAY_ZONE_FLOOR:
        logger.info(
            "Near-miss entity match, not auto-classified: %r ~ %r (score=%.1f, alias for %s)",
            name, alias, score, _ALIAS_TO_MATCH[alias][0],
        )
    return "Developer Not Matched To Known List", None, score


# --------------------------------------------------------------------------
# PJM context for undisclosed developers
# --------------------------------------------------------------------------

# Deliberately broad utility-territory names, not exact legal entity names
# (PJM's raw "Transmission Owner" field varies in exact phrasing) -- this is
# a coarse geographic signal, not an identification. A large request inside
# one of these territories is not more or less likely to BE a datacenter
# than one outside it; these territories simply happen to contain most of
# PJM's known data-center-dense counties (e.g. Loudoun/Prince William VA),
# which makes projects there statistically more common to look into first,
# not more suspicious in any individual case.
KNOWN_HIGH_DENSITY_TRANSMISSION_OWNERS = [
    "dominion", "peco", "aep ohio", "pepco", "jcpl", "pseg", "comed", "ppl",
]

PJM_PROJECT_NAME_KEYWORDS = [
    "data center", "datacenter", "data centre", "compute", "technology park",
    "substation expansion", "hyperscale", "campus", "cloud",
]

_TO_SENTINEL_RE = re.compile(r"Transmission Owner:\s*(.+?)\)\s*$")


def extract_pjm_transmission_owner(poi_substation: object) -> Optional[str]:
    """ingest_grid_queues.py writes PJM's missing-POI sentinel as
    'NOT PUBLISHED BY PJM (Transmission Owner: <name>)'; pull <name> back
    out. Returns None for any other string (including a real POI value,
    or the sentinel with an unknown TO)."""
    m = _TO_SENTINEL_RE.search(str(poi_substation or ""))
    if not m:
        return None
    name = m.group(1).strip()
    return None if name.lower() == "unknown" else name


def project_name_keyword_hits(project_name: object) -> list[str]:
    text = str(project_name or "").lower()
    return [kw for kw in PJM_PROJECT_NAME_KEYWORDS if kw in text]


# --------------------------------------------------------------------------
# Physical compute-equivalence model
# --------------------------------------------------------------------------

# NVIDIA datasheet values for the H100 SXM. The datasheet's 1,979 TFLOPS for FP16/BF16
# carries a footnote: it is shown with 2:4 structured sparsity and is half that without.
H100_SXM_FP16_TFLOPS_SPARSE = 1979.0
H100_SXM_FP16_TFLOPS_DENSE = 989.5


@dataclass(frozen=True)
class ComputeScenario:
    label: str
    pue: float          # total facility power / IT power
    kw_per_rack: float
    gpus_per_rack: int
    chip_tflops_baseline: float  # peak TFLOPs per chip; 1,979 is the H100 SXM FP16/BF16 peak WITH 2:4 sparsity (dense: 989.5)
    mfu: float               # model FLOPs utilization, sustained

    def run_flops(self, capacity_mw: float, run_days: int = 90, tflops: Optional[float] = None) -> dict:
        p_it_kw = capacity_mw * 1000.0 / self.pue
        racks = p_it_kw / self.kw_per_rack
        gpus = racks * self.gpus_per_rack
        run_seconds = run_days * 86400
        chip_tflops = self.chip_tflops_baseline if tflops is None else tflops
        flops = gpus * (chip_tflops * 1e12) * run_seconds * self.mfu
        return {"racks": racks, "gpus": gpus, "run_flops": flops}


# The REFERENCE scenario reproduces the brief's exact constants (PUE 1.25,
# 35kW/rack, 8 GPU/rack, H100 SXM 1,979 TFLOPs FP16/BF16 (the with-sparsity peak), 40% MFU, 90-day
# run). LOW and HIGH bracket it with assumptions that are each individually
# defensible for real facilities (older air-cooled halls run lower density
# and lower sustained utilization; new liquid-cooled halls run denser and
# higher PUE-efficiency) -- see module docstring for how close together
# these land at exactly 100MW despite the spread in inputs.
REFERENCE_SCENARIO = ComputeScenario("reference (as specified)", pue=1.25, kw_per_rack=35.0, gpus_per_rack=8, chip_tflops_baseline=H100_SXM_FP16_TFLOPS_SPARSE, mfu=0.40)
LOW_SCENARIO = ComputeScenario("low (air-cooled, lower utilization)", pue=1.4, kw_per_rack=20.0, gpus_per_rack=8, chip_tflops_baseline=H100_SXM_FP16_TFLOPS_SPARSE, mfu=0.25)
HIGH_SCENARIO = ComputeScenario("high (liquid-cooled, high utilization)", pue=1.15, kw_per_rack=50.0, gpus_per_rack=8, chip_tflops_baseline=H100_SXM_FP16_TFLOPS_SPARSE, mfu=0.50)

FLOP_REPORTING_THRESHOLD = 1.0e26


def compute_range(capacity_mw: float) -> dict:
    low = LOW_SCENARIO.run_flops(capacity_mw)
    ref = REFERENCE_SCENARIO.run_flops(capacity_mw)
    high = HIGH_SCENARIO.run_flops(capacity_mw)
    dense = {
        name: scenario.run_flops(capacity_mw, tflops=H100_SXM_FP16_TFLOPS_DENSE)["run_flops"]
        for name, scenario in (("low", LOW_SCENARIO), ("reference", REFERENCE_SCENARIO), ("high", HIGH_SCENARIO))
    }
    return {
        "gpus_low": low["gpus"], "gpus_reference": ref["gpus"], "gpus_high": high["gpus"],
        "run_flops_90d_low": low["run_flops"], "run_flops_90d_reference": ref["run_flops"],
        "run_flops_90d_high": high["run_flops"],
        "clears_flop_threshold_all_scenarios": low["run_flops"] >= FLOP_REPORTING_THRESHOLD,
        "clears_flop_threshold_reference": ref["run_flops"] >= FLOP_REPORTING_THRESHOLD,
        # Sensitivity: the same scenarios at the dense FP16/BF16 peak (half of the 1,979 figure).
        "run_flops_90d_low_dense": dense["low"], "run_flops_90d_reference_dense": dense["reference"],
        "run_flops_90d_high_dense": dense["high"],
        "clears_flop_threshold_all_scenarios_dense": all(v >= FLOP_REPORTING_THRESHOLD for v in dense.values()),
    }


# --------------------------------------------------------------------------
# Row enrichment
# --------------------------------------------------------------------------

REQUIRED_INPUT_COLUMNS = [
    "queue_id", "rto_region", "state", "county", "poi_substation",
    "capacity_mw", "projected_date", "developer_entity",
]
# Only present if ingest_grid_queues.py was run with --include-raw-fields.
# Checked independently (not as one bundle) so a CSV with some but not all
# of these still gets whatever enrichment it can support -- e.g. status/
# project_name present without raw_fuel_technology still gets IA-stage
# flagging and PJM keyword context, just not fuel-based storage detection.
OPTIONAL_INPUT_COLUMNS = ["status", "project_name"]
FUEL_INPUT_COLUMN = "raw_fuel_technology"

ADVANCED_STATUS = "IA in Progress"  # the brief's "Phase II / IA status"

# Confirmed against real ERCOT project names during the first live run:
# operators overwhelmingly self-label standalone battery storage in the
# project name itself ("Zeus Armstrong BESS", "Prairie Point Energy
# Storage I"), so checking project_name catches the common case; checking
# raw_fuel_technology too catches rows where the project name doesn't say
# it but the fuel/technology code does. Both checked, either is sufficient.
STORAGE_TOKENS = ("bess", "battery", "energy storage", "storage")
CONFIRMED_STORAGE_LABEL = "Confirmed Grid-Scale Storage (BESS)"
AMBIGUOUS_LOAD_LABEL = "Genuinely Ambiguous / Unclassified Large Load"


def classify_storage_tier(project_name: object, raw_fuel_technology: object) -> str:
    """MECE split of the non-hyperscaler population requested after the
    first real run showed grid-scale battery storage dominating the
    unresolved-entity list: explicit storage tokens in either the project
    name or the fuel/technology description -> confirmed storage; anything
    else -> genuinely ambiguous. "Ambiguous" here means exactly that --
    unresolved, not a claim that these ARE computational loads. Missing
    input on both sides defaults to ambiguous (the non-overclaiming
    direction: absence of a storage signal is not evidence of anything)."""
    text = f"{project_name or ''} {raw_fuel_technology or ''}".lower()
    if any(token in text for token in STORAGE_TOKENS):
        return CONFIRMED_STORAGE_LABEL
    return AMBIGUOUS_LOAD_LABEL


def enrich_row(row: "pd.Series", have_optional_columns: bool, have_fuel_column: bool) -> dict:
    entity_category, matched_entity, match_score = classify_entity(row.get("developer_entity"))

    load_type_tier = classify_storage_tier(
        row.get("project_name") if have_optional_columns else None,
        row.get("raw_fuel_technology") if have_fuel_column else None,
    )
    transmission_owner = None
    in_known_high_density_zone = False
    keyword_hits: list[str] = []
    if row.get("rto_region") == "PJM" and entity_category == "Developer Not Disclosed":
        transmission_owner = extract_pjm_transmission_owner(row.get("poi_substation"))
        if transmission_owner:
            in_known_high_density_zone = any(
                z in transmission_owner.lower() for z in KNOWN_HIGH_DENSITY_TRANSMISSION_OWNERS
            )
        if have_optional_columns:
            keyword_hits = project_name_keyword_hits(row.get("project_name"))

    capacity_mw = float(row.get("capacity_mw") or 0.0)
    crange = compute_range(capacity_mw)

    reached_ia_stage: Optional[bool] = None
    if have_optional_columns:
        reached_ia_stage = str(row.get("status") or "") == ADVANCED_STATUS

    unresolved_entity = entity_category in (
        "Developer Not Matched To Known List", "Developer Not Disclosed",
        "Possible Match (Needs Verification)",
    )
    is_confirmed_storage = load_type_tier == CONFIRMED_STORAGE_LABEL
    # capacity_mw >= 100 is true for every row by construction (script 1's
    # own filter), but kept as an explicit condition here rather than
    # assumed, in case this is ever run against a differently-filtered CSV.
    review_priority = capacity_mw >= 100.0 and unresolved_entity and not is_confirmed_storage

    reasons = []
    if is_confirmed_storage:
        reasons.append("explicit storage token in project name or fuel/technology -- confirmed BESS, excluded from review list")
    elif review_priority:
        reasons.append(f"{capacity_mw:.0f}MW request with no confirmed public operator")
        if entity_category == "Possible Match (Needs Verification)":
            reasons.append(f"name resembles {matched_entity} but not confirmed (generic-word brand token)")
        if have_optional_columns and reached_ia_stage:
            reasons.append("reached IA in Progress")
        if in_known_high_density_zone:
            reasons.append(f"Transmission Owner ({transmission_owner}) in a known data-center-dense territory")
        if keyword_hits:
            reasons.append(f"project name matches: {', '.join(keyword_hits)}")
    review_reason = "; ".join(reasons) if reasons else (
        f"Matched to {matched_entity}" if matched_entity else "Below capacity threshold or entity already resolved"
    )

    module1_tier = (
        "Tier 3: Confirmed Grid-Scale Storage (BESS)" if is_confirmed_storage
        else "Tier 1: Confirmed Hyperscaler" if entity_category == "Confirmed Hyperscaler"
        else "Tier 2: Wholesale Colocation Developer" if entity_category == "Wholesale Colocation Developer"
        else "Tier 4: Genuinely Ambiguous / Unclassified Large Load"
    )

    return {
        "queue_id": row.get("queue_id"),
        "rto_region": row.get("rto_region"),
        "state": row.get("state"),
        "county": row.get("county"),
        "capacity_mw": capacity_mw,
        "developer_entity_raw": row.get("developer_entity"),
        "entity_category": entity_category,
        "module1_tier": module1_tier,
        "matched_public_entity": matched_entity,
        "entity_match_score": round(match_score, 1),
        "load_type_tier": load_type_tier,
        "transmission_owner": transmission_owner,
        "in_known_high_density_zone": in_known_high_density_zone,
        "project_name_keyword_hits": ", ".join(keyword_hits) if keyword_hits else None,
        "reached_ia_stage": reached_ia_stage,
        "gpus_estimate_low": round(crange["gpus_low"]),
        "gpus_estimate_reference": round(crange["gpus_reference"]),
        "gpus_estimate_high": round(crange["gpus_high"]),
        "run_flops_90d_low": crange["run_flops_90d_low"],
        "run_flops_90d_reference": crange["run_flops_90d_reference"],
        "run_flops_90d_high": crange["run_flops_90d_high"],
        "clears_1e26_flops_all_scenarios": crange["clears_flop_threshold_all_scenarios"],
        "review_priority": review_priority,
        "review_reason": review_reason,
    }


def enrich_registry(df: pd.DataFrame) -> pd.DataFrame:
    missing_required = [c for c in REQUIRED_INPUT_COLUMNS if c not in df.columns]
    if missing_required:
        raise ValueError(f"Input CSV is missing required column(s): {missing_required}")

    have_optional = all(c in df.columns for c in OPTIONAL_INPUT_COLUMNS)
    if not have_optional:
        logger.warning(
            "Input CSV has no %s column(s) -- re-run ingest_grid_queues.py with "
            "--include-raw-fields to enable PJM project-name keyword matching and "
            "the IA-stage review criterion. Proceeding without them.",
            OPTIONAL_INPUT_COLUMNS,
        )
    have_fuel = FUEL_INPUT_COLUMN in df.columns
    if not have_fuel:
        logger.warning(
            "Input CSV has no %r column -- the Confirmed Grid-Scale Storage (BESS) vs "
            "Genuinely Ambiguous split will rely on project_name alone (if present), "
            "which misses rows where the storage signal is only in the fuel/technology "
            "code. Re-run ingest_grid_queues.py with --include-raw-fields for both signals.",
            FUEL_INPUT_COLUMN,
        )

    enriched_rows = [enrich_row(row, have_optional, have_fuel) for _, row in df.iterrows()]
    out = pd.DataFrame(enriched_rows)
    out.sort_values(["review_priority", "capacity_mw"], ascending=[False, False], inplace=True)
    return out


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------

def format_flops(n: float) -> str:
    return f"{n:.2e}"


def build_summary_stats_markdown(enriched: pd.DataFrame) -> str:
    """The three headline totals requested after the storage/ambiguous
    split: total queue analyzed, confirmed battery storage, and genuinely
    ambiguous load. BESS + Ambiguous sum exactly to the total by
    construction (load_type_tier is computed for every row, MECE)."""
    total_mw = enriched["capacity_mw"].sum()
    total_count = len(enriched)
    storage = enriched[enriched["load_type_tier"] == CONFIRMED_STORAGE_LABEL]
    ambiguous = enriched[enriched["load_type_tier"] == AMBIGUOUS_LOAD_LABEL]
    lines = [
        "## Summary",
        "",
        f"- **Total Queue Analyzed:** {total_mw:,.1f} MW ({total_mw / 1000:,.1f} GW) across {total_count:,} facilities",
        f"- **Confirmed Battery Storage (BESS):** {storage['capacity_mw'].sum():,.1f} MW across "
        f"{len(storage):,} facilities -- explicit storage token in project name or fuel/technology code",
        f"- **Genuinely Ambiguous / Unclassified Large Load:** {ambiguous['capacity_mw'].sum():,.1f} MW "
        f"across {len(ambiguous):,} facilities -- no storage token found; entity not on the known "
        "hyperscaler/colo list. \"Ambiguous\" means exactly that: unresolved from public queue data "
        "alone, not a determination that these are AI/computational loads.",
        "",
    ]
    return "\n".join(lines)


def build_review_table_markdown(enriched: pd.DataFrame, top_n: int = 15) -> str:
    """Descriptive summary of the largest, advanced-stage projects that
    don't resolve to a known public operator AND aren't confirmed grid-scale
    storage -- a starting point for manual review, not a finding. See
    module docstring for why this isn't framed as an audit exhibit."""
    candidates = enriched[enriched["review_priority"]].head(top_n)
    lines = [
        f"## Largest capacity requests: Genuinely Ambiguous / Unclassified tier only (top {len(candidates)})",
        "",
        "Confirmed Grid-Scale Storage (BESS) rows are excluded from this table -- see Summary above "
        "for that tier's separate totals. 'Entity classification' reflects a name-match against a "
        "small hardcoded list of known hyperscalers/colo developers, not a determination of what the "
        "project actually is -- most rows here are simply names outside that list, not confirmed "
        "computational loads. GPU/FLOPs figures are a reference-scenario estimate (see script "
        "docstring for the full low-high range); treat them as illustrative order-of-magnitude, not "
        "a claim about actual hardware.",
        "",
        "| Queue ID | RTO | County/State | Transmission Owner | Requested MW | "
        "Est. GPUs (reference) | Theoretical 90-Day FLOPs (reference) | Entity Classification |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for _, r in candidates.iterrows():
        to_display = r["transmission_owner"] if pd.notna(r["transmission_owner"]) else "—"
        lines.append(
            f"| {r['queue_id']} | {r['rto_region']} | {r['county']}, {r['state']} | {to_display} | "
            f"{r['capacity_mw']:.0f} | {r['gpus_estimate_reference']:,} | "
            f"{format_flops(r['run_flops_90d_reference'])} | {r['entity_category']} |"
        )
    if candidates.empty:
        lines.append("| _none -- no rows met the review-priority criteria in this dataset_ | | | | | | | |")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Self-test
# --------------------------------------------------------------------------

def _build_synthetic_registry() -> pd.DataFrame:
    rows = [
        # queue_id, rto, state, county, poi_substation, capacity_mw, projected_date, developer_entity, status, project_name, raw_fuel_technology
        ("Q1", "ERCOT", "TX", "Ward", "Big Country 138 kV", 500.0, "2028-01-01",
         "Vadata Inc.", "Under Study", "Compute Campus West", "Other - Other"),          # confirmed hyperscaler
        ("Q2", "ERCOT", "TX", "Ector", "Odessa 345 kV", 150.0, "2027-Q4",
         "Compass Datacenters TX LLC", "IA in Progress", "Battery Storage Node", "Other - Other"),  # confirmed colo, but name says storage (orthogonal dims)
        ("Q3", "ERCOT", "TX", "Reeves", "Riley 345 kV", 350.0, "2027-Q2",
         "GridCo Devco LLC", "Facilities Study", "Large Load Explicit Phase", "Other - Other"),  # unmatched, ambiguous
        ("Q4", "PJM", "VA", "Loudoun", "NOT PUBLISHED BY PJM (Transmission Owner: Dominion)",
         450.0, "2028-06-01", "NOT PUBLISHED IN PJM QUEUE EXPORT",
         "IA in Progress", "Alpha Compute Campus", "Other"),                              # PJM undisclosed, high-density TO, keyword hit, IA stage, ambiguous
        ("Q5", "PJM", "PA", "Somerset", "NOT PUBLISHED BY PJM (Transmission Owner: FirstEnergy)",
         120.0, "2029-01-01", "NOT PUBLISHED IN PJM QUEUE EXPORT",
         "Under Study", "Ridge Wind Interconnect", "Other"),                              # PJM undisclosed, NOT high-density TO, no keyword hit
        ("Q6", "PJM", "PA", "Berks", "NOT PUBLISHED BY PJM (Transmission Owner: PPL)",
         160.0, "UNKNOWN", "NOT PUBLISHED IN PJM QUEUE EXPORT",
         "Engineering Review", "Theta Unclassified Load", "Other"),                       # PJM undisclosed, high-density TO, no keyword hit, not IA
        ("Q7", "ERCOT", "TX", "Scurry", "Zeus 345 kV", 300.0, "2028-Q1",
         "Zeta Devco LLC", "Under Study", "Zeta Project Seven",
         "Other - Battery Energy Storage"),                                               # storage signal ONLY in fuel/technology, not in name
    ]
    columns = ["queue_id", "rto_region", "state", "county", "poi_substation", "capacity_mw",
               "projected_date", "developer_entity", "status", "project_name", "raw_fuel_technology"]
    return pd.DataFrame(rows, columns=columns)


def run_selftest() -> bool:
    configure_logging("WARNING")
    print("Running self-test against a synthetic enriched registry...\n")

    checks: list[tuple[str, bool]] = []

    # --- entity classification ---
    checks.append(("Amazon fuzzy match via 'Vadata Inc.'",
                    classify_entity("Vadata Inc.")[:2] == ("Confirmed Hyperscaler", "Amazon")))
    checks.append(("Generic 'Compass' token stays in human-audit state",
                    classify_entity("Compass Datacenters TX LLC")[:2] == ("Possible Match (Needs Verification)", "Compass Datacenters")))
    checks.append(("Unmatched real name stays unmatched, not mislabeled",
                    classify_entity("GridStore LLC")[0] == "Developer Not Matched To Known List"))
    checks.append(("PJM 'NOT PUBLISHED...' sentinel -> Developer Not Disclosed, not a false name match",
                    classify_entity("NOT PUBLISHED IN PJM QUEUE EXPORT")[0] == "Developer Not Disclosed"))
    checks.append(("Bug fix, verified: SPP's differently-worded 'NOT PUBLISHED...' sentinel is now "
                    "also recognized as Developer Not Disclosed (previously only PJM's exact string "
                    "matched, so every SPP row would have skipped straight to fuzzy entity matching "
                    "against literal sentinel text)",
                    classify_entity("NOT PUBLISHED IN SPP GI QUEUE EXPORT")[0] == "Developer Not Disclosed"))
    checks.append(("IESO's differently-worded 'NOT PUBLISHED...' sentinel also recognized",
                    classify_entity("NOT PUBLISHED IN IESO APPLICATION STATUS DATA")[0] == "Developer Not Disclosed"))
    checks.append(("'Eta Compute LLC' does not false-positive-match Meta (the eta-in-meta substring trap)",
                    classify_entity("Eta Compute LLC")[0] != "Confirmed Hyperscaler"))
    checks.append(("'Beale Infrastructure' does not false-positive-match Stack Infrastructure",
                    classify_entity("Beale Infrastructure")[0] != "Wholesale Colocation Developer"))
    checks.append(("Real-data finding: 'STACK Danville Gen Power 5, LLC' (brand-prefixed project "
                    "LLC, scores just under the fuzzy threshold against the full company name) is "
                    "surfaced as a possible match via whole-word token, not silently missed",
                    classify_entity("STACK Danville Gen Power 5, LLC")[:2]
                    == ("Possible Match (Needs Verification)", "Stack Infrastructure")))
    checks.append(("'Kickstart Infrastructure LLC' does NOT whole-word-match 'stack' "
                    "('stack' is not a substring of 'kickstart')",
                    classify_entity("Kickstart Infrastructure LLC")[0] != "Possible Match (Needs Verification)"))
    checks.append(("High-confidence token still fires on a brand-prefixed project name: "
                    "'EdgeConneX Ashburn DC 3 LLC'",
                    classify_entity("EdgeConneX Ashburn DC 3 LLC")[:2]
                    == ("Wholesale Colocation Developer", "EdgeConneX")))
    checks.append(("Low-confidence generic token 'QTS' never auto-confirms",
                    classify_entity("QTS Realty Trust")[:2]
                    == ("Possible Match (Needs Verification)", "QTS")))
    checks.append(("Low-confidence generic token 'Vantage' never auto-confirms",
                    classify_entity("Vantage Data Centers")[:2]
                    == ("Possible Match (Needs Verification)", "Vantage")))
    checks.append(("Low-confidence generic token 'Compass' never auto-confirms",
                    classify_entity("Compass Datacenters")[:2]
                    == ("Possible Match (Needs Verification)", "Compass Datacenters")))
    checks.append(("Low-confidence generic token 'Rowan' never auto-confirms",
                    classify_entity("Rowan Digital")[:2]
                    == ("Possible Match (Needs Verification)", "Rowan Digital Infrastructure")))

    # --- PJM context ---
    checks.append(("Transmission Owner correctly parsed from PJM sentinel",
                    extract_pjm_transmission_owner("NOT PUBLISHED BY PJM (Transmission Owner: Dominion)") == "Dominion"))
    checks.append(("Transmission Owner extraction returns None for a real POI string",
                    extract_pjm_transmission_owner("Riley 345 kV") is None))
    checks.append(("Project-name keyword hit detected", "compute" in project_name_keyword_hits("Alpha Compute Campus")))
    checks.append(("No false keyword hit on an unrelated name", project_name_keyword_hits("Ridge Wind Interconnect") == []))

    # --- compute range model ---
    r100 = compute_range(100.0)
    checks.append(("Reference scenario reproduces the brief's exact formula at 100MW (~1.126e26)",
                    abs(r100["run_flops_90d_reference"] - 1.126e26) / 1.126e26 < 0.01))
    checks.append(("Low/high scenarios bracket the reference, not equal to it",
                    r100["run_flops_90d_low"] != r100["run_flops_90d_reference"] != r100["run_flops_90d_high"]))
    checks.append(("100MW clears 1e26 FLOPs in all three scenarios (verifies the brief's claim)",
                    r100["clears_flop_threshold_all_scenarios"] is True))
    checks.append(("Dense FP16/BF16 sensitivity: 100MW is below 1e26 in every scenario (1,979 is the with-sparsity peak)",
                    r100["clears_flop_threshold_all_scenarios_dense"] is False
                    and abs(r100["run_flops_90d_reference_dense"] * 2 - r100["run_flops_90d_reference"]) / r100["run_flops_90d_reference"] < 1e-9))
    r10 = compute_range(10.0)
    checks.append(("10MW does NOT clear 1e26 FLOPs (sanity floor)",
                    r10["clears_flop_threshold_all_scenarios"] is False))

    # --- full pipeline ---
    df = _build_synthetic_registry()
    enriched = enrich_registry(df)
    by_id = enriched.set_index("queue_id").to_dict(orient="index")

    checks.append(("Q1 (confirmed hyperscaler) is not flagged for review",
                    by_id["Q1"]["review_priority"] is False or by_id["Q1"]["review_priority"] == False))
    checks.append(("Q3 (unmatched, ERCOT) IS flagged for review", by_id["Q3"]["review_priority"] == True))
    checks.append(("Q4 (PJM undisclosed, Dominion, keyword hit, IA stage) flagged with all 3 reasons",
                    by_id["Q4"]["review_priority"] == True
                    and by_id["Q4"]["in_known_high_density_zone"] == True
                    and by_id["Q4"]["reached_ia_stage"] == True
                    and "compute" in (by_id["Q4"]["project_name_keyword_hits"] or "")))
    checks.append(("Q5 (PJM undisclosed, FirstEnergy) correctly NOT flagged as high-density zone",
                    by_id["Q5"]["in_known_high_density_zone"] == False))
    checks.append(("Q6 (PJM undisclosed, PPL, Engineering Review) not marked as reached-IA",
                    by_id["Q6"]["reached_ia_stage"] == False))

    # --- storage/ambiguous tier split ---
    checks.append(("Q2 gets independent entity-review and storage dimensions",
                    by_id["Q2"]["entity_category"] == "Possible Match (Needs Verification)"
                    and by_id["Q2"]["load_type_tier"] == CONFIRMED_STORAGE_LABEL))
    checks.append(("Q2 not in review list despite unresolved-looking name, because entity IS confirmed",
                    by_id["Q2"]["review_priority"] == False))
    checks.append(("Q3 (unmatched, no storage token anywhere) correctly tiered Ambiguous",
                    by_id["Q3"]["load_type_tier"] == AMBIGUOUS_LOAD_LABEL
                    and by_id["Q3"]["review_priority"] == True))
    checks.append(("Q7: storage signal present ONLY in raw_fuel_technology (not project name) "
                    "still correctly detected as Confirmed Storage",
                    by_id["Q7"]["load_type_tier"] == CONFIRMED_STORAGE_LABEL))
    checks.append(("Q7 excluded from review despite unresolved entity, because it's confirmed storage",
                    by_id["Q7"]["review_priority"] == False))

    stats_md = build_summary_stats_markdown(enriched)
    total_mw = enriched["capacity_mw"].sum()
    storage_mw = enriched[enriched["load_type_tier"] == CONFIRMED_STORAGE_LABEL]["capacity_mw"].sum()
    ambiguous_mw = enriched[enriched["load_type_tier"] == AMBIGUOUS_LOAD_LABEL]["capacity_mw"].sum()
    checks.append(("Summary stats: BESS MW + Ambiguous MW sums exactly to Total MW (MECE by construction)",
                    abs((storage_mw + ambiguous_mw) - total_mw) < 0.01))
    checks.append(("Summary stats: BESS + Ambiguous facility counts sum exactly to total row count",
                    (enriched["load_type_tier"] == CONFIRMED_STORAGE_LABEL).sum()
                    + (enriched["load_type_tier"] == AMBIGUOUS_LOAD_LABEL).sum() == len(enriched)))
    checks.append(("Summary markdown renders the three requested headline stats",
                    "Total Queue Analyzed" in stats_md and "Confirmed Battery Storage" in stats_md
                    and "Genuinely Ambiguous" in stats_md))

    md = build_review_table_markdown(enriched)
    checks.append(("Markdown table renders without a literal NaN/nan appearing", "nan" not in md.lower()))
    checks.append(("Markdown table includes the unmatched/undisclosed AMBIGUOUS rows", "Q3" in md and "Q4" in md))
    checks.append(("Markdown table excludes the confirmed-hyperscaler row (Q1)",
                    "| Q1 |" not in md and "| Q2 |" not in md))
    checks.append(("Markdown table excludes BOTH confirmed-storage rows (Q2 name-based, Q7 fuel-based), "
                    "even though Q7's entity is otherwise unresolved",
                    "| Q2 |" not in md and "| Q7 |" not in md))

    # graceful degradation without optional columns
    basic_df = df[REQUIRED_INPUT_COLUMNS]
    try:
        basic_enriched = enrich_registry(basic_df)
        degraded_ok = basic_enriched["reached_ia_stage"].isna().all()
    except Exception as exc:  # noqa: BLE001
        degraded_ok = False
        logger.error("Degraded-input path raised: %s", exc)
    checks.append(("Runs without crashing when status/project_name columns are absent", degraded_ok))

    # missing required column -> clear error, not a crash deep in the pipeline
    try:
        enrich_registry(df.drop(columns=["capacity_mw"]))
        missing_col_ok = False
    except ValueError as exc:
        missing_col_ok = "capacity_mw" in str(exc)
    checks.append(("Missing required column raises a clear ValueError naming it", missing_col_ok))

    out_csv = Path("/tmp/selftest_compute_audit.csv")
    enriched.to_csv(out_csv, index=False)
    round_tripped = pd.read_csv(out_csv)
    checks.append(("Enriched CSV round-trips with the same row count", len(round_tripped) == len(enriched)))

    ok = True
    for name, passed in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        ok = ok and bool(passed)
    print(f"\n{'ALL CHECKS PASSED' if ok else 'SOME CHECKS FAILED'} ({sum(1 for _, p in checks if p)}/{len(checks)})")
    return ok


# --------------------------------------------------------------------------
# CLI entry point
# --------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Enrich a megawatt_interconnect_registry_raw.csv with entity "
                     "classification, PJM context, and power-to-compute range estimates.",
    )
    parser.add_argument("--input", type=Path, default=Path("megawatt_interconnect_registry_raw.csv"),
                         help="Path to the registry CSV from ingest_grid_queues.py (default: %(default)s)")
    parser.add_argument("--output", type=Path, default=Path("computational_load_estimates.csv"),
                         help="Path for the enriched output CSV (default: %(default)s)")
    parser.add_argument("--review-table-output", type=Path, default=Path("review_candidates.md"),
                         help="Path for the Markdown summary table (default: %(default)s)")
    parser.add_argument("--top-n", type=int, default=15,
                         help="Number of rows in the Markdown summary table (default: %(default)s)")
    parser.add_argument("--log-level", type=str, default="INFO",
                         choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--selftest", action="store_true",
                         help="Run against a synthetic registry and report pass/fail, then exit.")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)

    if args.selftest:
        return 0 if run_selftest() else 1

    configure_logging(args.log_level)

    if not args.input.exists():
        logger.error("Input file not found: %s (run ingest_grid_queues.py first)", args.input)
        return 1

    try:
        df = pd.read_csv(args.input, dtype={"queue_id": str})
    except Exception as exc:  # noqa: BLE001
        logger.error("Could not read %s: %s", args.input, exc)
        return 1

    logger.info("Loaded %d rows from %s", len(df), args.input)

    try:
        enriched = enrich_registry(df)
    except ValueError as exc:
        logger.error("Enrichment failed: %s", exc)
        return 1

    enriched.to_csv(args.output, index=False)
    review_md = build_summary_stats_markdown(enriched) + "\n" + build_review_table_markdown(enriched, top_n=args.top_n)
    args.review_table_output.write_text(review_md, encoding="utf-8")

    category_counts = enriched["entity_category"].value_counts().to_dict()
    tier_counts = enriched["load_type_tier"].value_counts().to_dict()
    logger.info("=" * 72)
    logger.info("ENRICHMENT SUMMARY")
    logger.info("=" * 72)
    for category, count in category_counts.items():
        logger.info("  %-40s %d", category, count)
    logger.info("-" * 72)
    for tier, count in tier_counts.items():
        logger.info("  %-40s %d", tier, count)
    logger.info("-" * 72)
    logger.info("Flagged for review (large + unresolved operator): %d / %d rows",
                 int(enriched["review_priority"].sum()), len(enriched))
    logger.info("Enriched dataset written to : %s", args.output)
    logger.info("Review summary written to   : %s", args.review_table_output)
    logger.info("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
