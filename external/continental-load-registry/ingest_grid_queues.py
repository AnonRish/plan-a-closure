#!/usr/bin/env python3
"""
ingest_grid_queues.py
======================

Autonomous ETL pipeline over the two largest public U.S. high-voltage
interconnection queues -- PJM and ERCOT -- normalized into one schema and
filtered down to large (>=100 MW), currently-active, load-class requests:
the segment of the queue that large AI/data-center campuses show up in.

--------------------------------------------------------------------------
WHAT IS AND ISN'T VERIFIED (read this before you trust the output)
--------------------------------------------------------------------------
Every endpoint, column name, and quirk below was confirmed against current
(Sept 2026) primary sources before this file was written: PJM's and ERCOT's
own site/API documentation, ERCOT's own market notices describing its
current public-report URL scheme, and the current open-source `gridstatus`
library (github.com/gridstatus/gridstatus), which implements working
scrapers against both queues and whose source this script's HTTP mechanics
were checked against line-by-line. This environment has no network route to
pjm.com/ercot.com, so none of this has been exercised against a live
response; everything downstream of the HTTP call *was* exercised, against
synthetic workbooks hand-built to match the real, documented column layouts
(run `python ingest_grid_queues.py --selftest` to reproduce). Treat the
parsing/normalization/filtering logic as tested and the two fetch functions
as "correct as researched, not yet run against a live server."

Three real, non-obvious data gaps are baked into the design rather than
papered over:

1. PJM's public queue export has no interconnection-substation column and
   no applicant/developer-entity column at all (confirmed against the
   `missing=[...]` list in gridstatus's own PJM normalizer). This script
   tries a set of plausible aliases for both anyway (in case a future PJM
   export adds them) and otherwise fills a clearly-labeled sentinel --
   it does not invent a substation name or a company name.

2. "PJM Data Miner 2" does not appear to publish the interconnection queue
   as a queryable feed at all -- every other PJM dataset lives at
   dataminer2.pjm.com/feed/<name>, but the queue is served from a separate,
   unauthenticated planning-site endpoint. The Data Miner 2 path in this
   script is a real, working code path (if you supply a feed name you know
   about via --pjm-dataminer-feed plus a PJM_API_KEY), but it is not the
   default, because the verified, always-public source is the direct
   export. Relatedly: Data Miner 2's own terms restrict *redistribution* of
   data pulled through it without a separate license, which matters if this
   pipeline's output is meant to be published -- the direct queue export
   used by default carries no such restriction.

3. ERCOT does not currently publish a granular, per-project "Large Load"
   register as a stable single-URL CSV/XLSX the way it does for generation
   (the GIS Report). As of this research, ERCOT's Large Load Interconnection
   process (PGRR145 / "Batch Zero") is still forms-and-attestations based,
   and ERCOT's own site says a public "Large Load Portal" is still in
   development. This script's ERCOT large-load path is fully implemented
   and will parse a real file the moment you (or ERCOT) point it at one via
   --ercot-large-load-url; absent that, it says so and moves on rather than
   silently returning nothing or fabricating a URL that happens to 404.

The generation-side ERCOT GIS Report is real, stable, and fully wired up by
default; it also captures a meaningful slice of large-load signal on its
own, because co-located and private-network load (the structure many AI
campuses actually use to interconnect in ERCOT) shows up in it under
Fuel/Technology codes like "Other" and "Battery Energy Storage" -- which is
exactly why the load-type filter below keeps "Storage/Other" in play rather
than treating the GIS Report as generation-only noise.

--------------------------------------------------------------------------
USAGE
--------------------------------------------------------------------------
    python ingest_grid_queues.py
    python ingest_grid_queues.py --min-mw 200 --output my_registry.csv
    python ingest_grid_queues.py --pjm-dataminer-feed some_feed --pjm-api-key XXXX
    python ingest_grid_queues.py --ercot-large-load-url https://.../large_load.xlsx
    python ingest_grid_queues.py --selftest        # run against synthetic fixtures

Dependencies: requests, pandas, openpyxl, pydantic>=2. `fake-useragent` is
used if already installed; otherwise a hardcoded rotating pool is used (see
"USER AGENT HANDLING" below for why that's the safer default here).
"""

from __future__ import annotations

import argparse
from collections import Counter
import io
import json
import logging
import math
import os
import random
import re
import sys
import time
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Literal, Optional

import pandas as pd
import requests
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------

logger = logging.getLogger("ingest_grid_queues")


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


# --------------------------------------------------------------------------
# Filter criteria (as specified)
# --------------------------------------------------------------------------

MIN_CAPACITY_MW = 100.0

STATUS_CANONICAL = [
    "Active",
    "Under Study",
    "Facilities Study",
    "Engineering Review",
    "IA in Progress",
]
VALID_STATUSES_UPPER = {s.upper() for s in STATUS_CANONICAL}

# Fuel/technology/project-type signatures that mean "this is a generation
# resource, not a load" -- rejected even though they legitimately appear in
# the same queues. Everything NOT matched here is kept (mirrors the spec's
# "...or unclassified high-density commercial service": ambiguous rows are
# included, not dropped).
LOAD_TYPE_REJECT_KEYWORDS = [
    # Deliberately includes both bare fuel words (PJM's "Fuel" column
    # commonly holds single words like "Wind"/"Solar"/"Coal") and the
    # longer ERCOT-style expanded fuel-technology phrases, since which
    # form shows up depends on the source. NOTE: a project filed as pure
    # "Gas" or "Coal" generation is rejected here even though some gas
    # plants are increasingly built specifically to power a co-located
    # datacenter -- the queue record itself carries no signal distinguishing
    # a merchant plant from one dedicated to a behind-the-meter AI load, so
    # that specific pattern is a real blind spot of fuel/technology-based
    # filtering, not something this script can see from queue data alone.
    # "water" covers ERCOT's literal Fuel-code expansion for conventional
    # hydro ("Water", fuel code WAT) -- confirmed via exhaustive real-code
    # testing that "hydro"/"hydroelectric" alone don't match that string,
    # letting conventional-hydro projects fall through to the unmatched-
    # defaults-to-accept path.
    "solar", "photovoltaic", "wind", "hydro", "hydroelectric", "water", "nuclear",
    "geothermal", "biomass", "landfill gas", "methane", "fuel cell",
    "combined-cycle", "combined cycle", "combustion (gas) turbine",
    "combustion turbine", "steam turbine", "coal", "petcoke", "fuel oil",
    "concentrated solar", "gas",
]
LOAD_TYPE_ACCEPT_KEYWORDS = [
    "industrial", "large load", "data center", "datacenter", "data centre",
    "storage", "battery", "other", "colocation", "co-location",
    "private use network", "crypto", "bitcoin", "mining", "compute",
]

# --------------------------------------------------------------------------
# USER AGENT HANDLING
# --------------------------------------------------------------------------
# `fake-useragent` fetches a live UA list from a remote source on first use,
# which means the one package added specifically to make this pipeline more
# resilient would itself be a second, uncontrolled network dependency -- in
# a script whose whole point is not falling over when a remote endpoint is
# flaky. So: use it if it's already installed and its cache is warm, but
# always fall back to a hardcoded pool of current desktop browser UAs rather
# than let a UA-fetch failure take down the whole run.

_UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) "
    "Gecko/20100101 Firefox/129.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0",
]

try:  # pragma: no cover - exercised only when the optional dep is present
    from fake_useragent import UserAgent as _FakeUserAgent

    _fake_ua_instance: Optional[_FakeUserAgent]
    try:
        _fake_ua_instance = _FakeUserAgent()
    except Exception:  # network fetch failed, cache missing, etc.
        _fake_ua_instance = None
except ImportError:  # pragma: no cover
    _fake_ua_instance = None


def pick_user_agent() -> str:
    if _fake_ua_instance is not None:
        try:
            return _fake_ua_instance.random
        except Exception:
            pass
    return random.choice(_UA_POOL)


# --------------------------------------------------------------------------
# HTTP session: retries with exponential backoff, sane timeouts, UA rotation
# --------------------------------------------------------------------------

DEFAULT_TIMEOUT = 30  # seconds


def build_http_session(
    total_retries: int = 5,
    backoff_factor: float = 1.5,
) -> requests.Session:
    """A requests.Session with exponential-backoff retries mounted for both
    schemes, retrying on connection errors and the usual transient/rate-limit
    status codes."""
    session = requests.Session()
    retry = Retry(
        total=total_retries,
        connect=total_retries,
        read=total_retries,
        status=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST"]),
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"Accept-Language": "en-US,en;q=0.9"})
    return session


def request_with_retries(
    session: requests.Session,
    method: str,
    url: str,
    **kwargs: Any,
) -> requests.Response:
    """Thin wrapper that rotates the User-Agent per call (the mounted Retry
    adapter already handles backoff/retries) and enforces a default
    timeout."""
    headers = dict(kwargs.pop("headers", None) or {})
    headers.setdefault("User-Agent", pick_user_agent())
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
    response = session.request(method, url, headers=headers, **kwargs)
    response.raise_for_status()
    return response


# --------------------------------------------------------------------------
# Normalization schema
# --------------------------------------------------------------------------

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_QUARTER_RE = re.compile(r"^\d{4}-Q[1-4]$")
_UNKNOWN_TOKENS = {"", "UNKNOWN", "NAN", "NAT", "TBD", "NONE", "N/A"}

_STATE_NAME_TO_ABBR = {
    "TEXAS": "TX", "PENNSYLVANIA": "PA", "NEW JERSEY": "NJ", "MARYLAND": "MD",
    "VIRGINIA": "VA", "OHIO": "OH", "MICHIGAN": "MI", "ILLINOIS": "IL",
    "INDIANA": "IN", "NORTH CAROLINA": "NC", "TENNESSEE": "TN",
    "KENTUCKY": "KY", "WEST VIRGINIA": "WV", "DELAWARE": "DE",
    "DISTRICT OF COLUMBIA": "DC",
}


class InterconnectionRecord(BaseModel):
    """One row of the normalized, filtered output."""

    model_config = ConfigDict(str_strip_whitespace=True)

    queue_id: str
    rto_region: Literal["PJM", "ERCOT"]
    state: str
    county: str
    poi_substation: str
    capacity_mw: float
    projected_date: str
    developer_entity: str

    # Optional, source-internal fields -- NOT part of the 8-column schema
    # specified for the default output and not written to the CSV unless
    # --include-raw-fields is passed. Populated here (rather than dropped
    # at normalize-time) so downstream tooling -- e.g. an entity-resolution
    # or anomaly-flagging pass over this data -- can opt into them without
    # this script needing to re-derive them from raw source bytes it no
    # longer has. Absent from a raw dict, both simply default to None, so
    # every existing call site and the default 8-column output are
    # unaffected.
    status: Optional[str] = None
    project_name: Optional[str] = None
    raw_fuel_technology: Optional[str] = None

    @field_validator("queue_id", "poi_substation", "developer_entity", mode="before")
    @classmethod
    def _coerce_nonempty_str(cls, v: Any) -> str:
        if v is None:
            return "UNKNOWN"
        s = str(v).strip()
        if not s or s.upper() in _UNKNOWN_TOKENS:
            return "UNKNOWN"
        return s

    @field_validator("state", mode="before")
    @classmethod
    def _validate_state(cls, v: Any) -> str:
        s = str(v or "").strip().upper()
        s = _STATE_NAME_TO_ABBR.get(s, s)
        if len(s) != 2 or not s.isalpha():
            raise ValueError(f"state must be a 2-letter postal code, got {v!r}")
        return s

    @field_validator("county", mode="before")
    @classmethod
    def _titlecase_county_field(cls, v: Any) -> str:
        return titlecase_county(str(v or ""))

    @field_validator("capacity_mw", mode="before")
    @classmethod
    def _coerce_capacity(cls, v: Any) -> float:
        parsed = parse_capacity_mw(v)
        if parsed is None or parsed <= 0:
            raise ValueError(f"capacity_mw must be a positive number, got {v!r}")
        return round(parsed, 2)

    @field_validator("projected_date", mode="before")
    @classmethod
    def _validate_projected_date(cls, v: Any) -> str:
        s = normalize_projected_date(v)
        if s == "UNKNOWN" or _DATE_RE.match(s) or _QUARTER_RE.match(s):
            return s
        raise ValueError(
            f"projected_date not in YYYY-MM-DD or YYYY-Q# form (or UNKNOWN): {v!r}"
        )


# --------------------------------------------------------------------------
# Shared normalization helpers
# --------------------------------------------------------------------------

_MC_PREFIXES = ("Mc", "Mac")


def titlecase_county(raw: str) -> str:
    """Title-case a county name without mangling McXxx/MacXxx/O'Xxx and
    without upper-casing connector words unnecessarily. Pure capitalization
    fix-up -- does not add or strip a 'County'/'Parish' suffix, since the
    source data is trusted for which suffix (or none) applies."""
    raw = (raw or "").strip()
    if not raw:
        return "UNKNOWN"

    def fix_word(word: str) -> str:
        if not word:
            return word
        lower = word.lower()
        if lower in {"of", "the", "and"}:
            return lower
        if word[:2].lower() == "mc" and len(word) > 2:
            return "Mc" + word[2].upper() + word[3:].lower()
        if word[:3].lower() == "mac" and len(word) > 3 and word[3].isalpha():
            return "Mac" + word[3].upper() + word[4:].lower()
        if "'" in word:
            parts = word.split("'")
            return "'".join(p[:1].upper() + p[1:].lower() for p in parts if True)
        return word[:1].upper() + word[1:].lower()

    words = re.split(r"(\s+|-)", raw)
    fixed = [fix_word(w) if w.strip() and w not in ("-",) else w for w in words]
    result = "".join(fixed)
    # Capitalize first letter regardless (handles leading connector edge case)
    return result[:1].upper() + result[1:] if result else "UNKNOWN"


def parse_capacity_mw(raw: Any) -> Optional[float]:
    """Best-effort numeric MW parse. Handles plain numbers, '150 MW',
    comma-thousands, and 'A-B' ranges (takes the higher bound, since queue
    "requested capacity" ranges are conventionally reported as the ceiling
    the applicant asked for). Returns None (never raises) on anything it
    can't parse, so callers can drop/flag the row instead of crashing."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        if isinstance(raw, float) and math.isnan(raw):
            return None
        return float(raw)
    s = str(raw).strip()
    if not s or s.upper() in _UNKNOWN_TOKENS:
        return None
    s = s.upper().replace("MW", "").replace(",", "").strip()
    range_match = re.match(r"^(-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)$", s)
    if range_match:
        return max(float(range_match.group(1)), float(range_match.group(2)))
    try:
        return float(s)
    except ValueError:
        digits = re.findall(r"-?\d+(?:\.\d+)?", s)
        return float(digits[0]) if digits else None


_MONTH_ABBR = {
    m.lower(): i
    for i, m in enumerate(
        [
            "jan", "feb", "mar", "apr", "may", "jun",
            "jul", "aug", "sep", "oct", "nov", "dec",
        ],
        start=1,
    )
}

_DATE_FORMATS = (
    "%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%d/%m/%Y", "%Y/%m/%d",
    "%B %d, %Y", "%b %d, %Y", "%m/%d/%y",
)


def normalize_projected_date(raw: Any) -> str:
    """Best-effort projected-date normalization to YYYY-MM-DD or YYYY-Q#.
    Never raises; returns 'UNKNOWN' for anything unparseable so a single bad
    date string can't take down the whole row (or the whole pipeline)."""
    if raw is None:
        return "UNKNOWN"
    if isinstance(raw, pd.Timestamp):
        if pd.isna(raw):
            return "UNKNOWN"
        return raw.strftime("%Y-%m-%d")
    if isinstance(raw, datetime):
        return raw.strftime("%Y-%m-%d")

    s = str(raw).strip()
    if not s or s.upper() in _UNKNOWN_TOKENS:
        return "UNKNOWN"

    # Already-normalized forms
    if _DATE_RE.match(s):
        return s
    if _QUARTER_RE.match(s):
        return s

    # "Q3 2027" / "3Q27" / "Q3-2027"
    m = re.match(r"^Q?([1-4])[\s\-/]?Q?[\s\-/]?(\d{2,4})$", s, re.IGNORECASE)
    if m and s[:1].upper() == "Q":
        quarter, year = m.group(1), m.group(2)
        year = ("20" + year) if len(year) == 2 else year
        return f"{year}-Q{quarter}"
    m = re.match(r"^(\d)Q(\d{2,4})$", s, re.IGNORECASE)
    if m:
        quarter, year = m.group(1), m.group(2)
        year = ("20" + year) if len(year) == 2 else year
        return f"{year}-Q{quarter}"

    # "June 2027" / "Jun 2027" / "6/2027"
    m = re.match(r"^([A-Za-z]{3,9})\s+(\d{4})$", s)
    if m:
        mon = m.group(1).lower()[:3]
        if mon in _MONTH_ABBR:
            return f"{m.group(2)}-{_MONTH_ABBR[mon]:02d}-01"
    m = re.match(r"^(\d{1,2})/(\d{4})$", s)
    if m and 1 <= int(m.group(1)) <= 12:
        return f"{m.group(2)}-{int(m.group(1)):02d}-01"

    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    try:
        parsed = pd.to_datetime(s, errors="raise")
        return parsed.strftime("%Y-%m-%d")
    except Exception:
        logger.debug("Could not parse projected date %r; using UNKNOWN", raw)
        return "UNKNOWN"


def classify_status(raw: Any) -> Optional[str]:
    """Map a raw status string onto the canonical vocabulary via
    case-insensitive substring matching. Returns the canonical label if the
    row qualifies, else None (caller drops the row). Anything that doesn't
    match a reject *or* accept signature is logged, not guessed at."""
    s = str(raw or "").strip()
    if not s or s.upper() in _UNKNOWN_TOKENS:
        return None
    upper = s.upper()
    if upper in VALID_STATUSES_UPPER:
        return next(c for c in STATUS_CANONICAL if c.upper() == upper)

    # PJM short status codes -- exact match only. These are short codes, so
    # they intentionally stay outside the fuzzy substring matcher.
    PJM_SHORT_STATUS_CODES = {
        "EP": "Engineering Review",
        "UC": "IA in Progress",
        "UC-ISP": "IA in Progress",
    }
    if upper in PJM_SHORT_STATUS_CODES:
        return PJM_SHORT_STATUS_CODES[upper]

    # Exclusion-first gate: reject terminal/inactive states before any accept-side
    # substring matching. This prevents INACTIVE from satisfying ACTIVE and keeps
    # terminal words from leaking through a later fuzzy match.
    reject_patterns = (
        r"\bWITHDRAWN\b", r"\bCANCELLED\b", r"\bCANCELED\b",
        r"\bDEACTIVATED\b", r"\bDEACTIVATION\b", r"\bTERMINATED\b",
        r"\bSUSPENDED\b", r"\bCOMPLETED\b", r"\bRETIRED\b",
        r"\bPENDING\s+TERMINATION\b", r"\bINACTIVE\b",
        # Treat a completed/in-service terminal state as excluded, while
        # allowing the distinct live status "Active - In Service Partially".
        r"\bIN[\s-]+SERVICE\b(?!\s+PARTIALLY\b)",
    )
    normalized_upper = re.sub(r"[_-]+", " ", upper)
    if any(re.search(pattern, normalized_upper) for pattern in reject_patterns):
        return None

    # Fuzzy fallback across common real-world phrasings for the same states.
    fuzzy_map = [
        (("ACTIVE", "IN QUEUE", "CONFIRMED"), "Active"),
        (("UNDER STUDY", "SCREENING", "FEASIBILITY", "SYSTEM IMPACT"), "Under Study"),
        (("FACILITIES STUDY", "FACILITY STUDY", "FIS "), "Facilities Study"),
        (("ENGINEERING REVIEW", "ENGINEERING & PROCUREMENT", "ENGINEERING AND PROCUREMENT", "E&P"),
         "Engineering Review"),
        (("IA IN PROGRESS", "INTERCONNECTION AGREEMENT", "IA DRAFT", "IA NEGOTIATION",
          "UNDER CONSTRUCTION", "UNDERCONSTRUCTION - IN SERVICE PARTIALLY"),
         "IA in Progress"),
    ]
    for keywords, canonical in fuzzy_map:
        if any(k in upper for k in keywords):
            return canonical


    logger.debug("Unrecognized status value %r (row excluded)", raw)
    return None


_OTHER_KEYWORD_RE = re.compile(r"\bother\b(?!\s+than)")


def _accept_keyword_hits(lower: str) -> list[str]:
    """Substring/whole-word scan against LOAD_TYPE_ACCEPT_KEYWORDS, with one
    precision fix: "other" is checked as a whole word excluding "other
    than" -- confirmed necessary against real ERCOT data, where the
    technology-code description "Steam Turbine other than Combined-Cycle"
    otherwise false-triggers the accept path via ordinary English ("other
    than X" = "except X"), not ERCOT's actual "Other" fuel category. Every
    other keyword keeps plain substring matching."""
    hits = []
    for k in LOAD_TYPE_ACCEPT_KEYWORDS:
        if k == "other":
            if _OTHER_KEYWORD_RE.search(lower):
                hits.append(k)
        elif k in lower:
            hits.append(k)
    return hits


def classify_load_type(raw: Any) -> tuple[bool, str]:
    """(qualifies, label) for the load-type filter. Rejects recognized pure
    generation signatures; everything else -- including blank/unrecognized
    values -- qualifies as 'unclassified high-density commercial service'
    per the filter spec, rather than being silently dropped."""
    s = str(raw or "").strip()
    lower = s.lower()
    if not lower:
        return True, "Unclassified"
    if any(k in lower for k in LOAD_TYPE_REJECT_KEYWORDS):
        # A bare "other" hit does NOT override a reject match here -- found
        # against real ERCOT data via exhaustive fuel x technology testing:
        # "Nuclear" fuel paired with Technology="Other" isn't a genuine
        # hybrid facility, it's just a nuclear plant whose technology
        # sub-type has no more specific ERCOT code. Overriding a reject
        # needs a real, distinctive co-located signal (storage/battery/
        # data center/industrial/etc.), which "other" alone isn't.
        override_hits = [k for k in _accept_keyword_hits(lower) if k != "other"]
        if override_hits:
            return True, "Storage/Other"  # e.g. "solar + storage hybrid"
        return False, s
    for k in _accept_keyword_hits(lower):
        if k in ("storage", "battery"):
            return True, "Storage/Other"
        if k in ("data center", "datacenter", "data centre"):
            return True, "Data Center"
        if k == "industrial":
            return True, "Industrial"
        if k == "large load":
            return True, "Large Load"
        return True, "Storage/Other"
    return True, "Unclassified"


def locate_column(columns: Iterable[str], aliases: list[str]) -> Optional[str]:
    """Fuzzy column finder: case/space/punctuation-insensitive match of a
    real column name against a list of acceptable aliases, first exact then
    substring. Returns the *original* column label, or None."""

    def norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]", "", s.lower())

    cols = list(columns)
    norm_cols = {norm(c): c for c in cols if isinstance(c, str)}
    norm_aliases = [norm(a) for a in aliases]

    for na in norm_aliases:
        if na in norm_cols:
            return norm_cols[na]
    for nc_norm, nc_orig in norm_cols.items():
        for na in norm_aliases:
            if na and (na in nc_norm or nc_norm in na):
                return nc_orig
    return None


def locate_header_row(
    raw: pd.DataFrame,
    alias_groups: dict[str, list[str]],
    max_scan_rows: int = 60,
    min_hits: int = 3,
) -> Optional[int]:
    """Scan the first `max_scan_rows` rows of a header-less dataframe (i.e.
    read with header=None) for the row that looks most like the real column
    header: the row with the most cells matching a known alias group. Handles
    title rows, merged-cell artifacts, and blank spacer rows above the real
    header without hardcoding a fixed skiprows count."""
    best_row, best_hits = None, 0
    scan_limit = min(max_scan_rows, len(raw))
    for row_idx in range(scan_limit):
        row_values = [str(v) for v in raw.iloc[row_idx].tolist() if pd.notna(v)]
        if not row_values:
            continue
        hits = 0
        for aliases in alias_groups.values():
            if locate_column(row_values, aliases) is not None:
                hits += 1
        if hits > best_hits:
            best_hits, best_row = hits, row_idx
    if best_hits >= min_hits:
        return best_row
    return None


# --------------------------------------------------------------------------
# PJM ingestion
# --------------------------------------------------------------------------
# Verified (Sept 2026) against the open-source gridstatus library's PJM
# module (github.com/gridstatus/gridstatus, MIT licensed) and PJM's own
# Data Miner 2 documentation.
#
#   * The public queue export lives at services.pjm.com, NOT dataminer2 --
#     it is fetched with a POST carrying a client-side "api-subscription-key"
#     that PJM's own public queue-status page embeds in its JS bundle to
#     power its own "Export" button for any visitor. That means it is
#     public-by-design, not a credential this script is bypassing anything
#     to obtain -- but PJM controls it and could rotate it; if you start
#     getting 401s, pull the current value from the Network tab while
#     loading https://www.pjm.com/planning/service-requests/services-request-status
#     and pass it via --pjm-export-key.
#   * The raw export has NO POI/substation column and NO applicant/developer
#     column (PJM confirms both are simply absent from the file, not that
#     gridstatus chooses to drop them). This script still tries a set of
#     plausible aliases for both, in case PJM adds them later, and only
#     falls back to a labeled sentinel if nothing matches.
#   * "PJM Data Miner 2" (api.pjm.com, subscription-key gated, one feed per
#     dataset at dataminer2.pjm.com/feed/<name>) does not appear to expose
#     the queue as a feed at all -- every feed gridstatus maps for PJM is a
#     market/ops dataset (LMPs, load, outages, etc.), never the queue. The
#     Data Miner 2 path below is real and will work *if* you know a feed
#     name (pass --pjm-dataminer-feed), but it is not attempted by default
#     since there's nothing to point it at.

PJM_QUEUE_EXPORT_URL = "https://services.pjm.com/PJMPlanningApi/api/Queue/ExportToXls"
PJM_QUEUE_EXPORT_DEFAULT_KEY = "E29477D0-70E0-4825-89B0-43F460BF9AB4"
PJM_DATAMINER_BASE = "https://api.pjm.com/api/v1/"

PJM_COLUMN_ALIASES = {
    "queue_id": ["project id", "queue id", "queue number"],
    "project_name": ["name", "project name"],
    "county": ["county"],
    "state": ["state"],
    "status": ["status"],
    "capacity_mw": ["mw capacity", "mfo", "summer capacity (mw)", "requested mw"],
    "projected_date": [
        "projected in service date", "proposed completion date",
        "projected cod", "projected completion date",
    ],
    "fuel": ["fuel", "generation type"],
    "transmission_owner": ["transmission owner"],
    # Not present in the confirmed export layout; kept so a future PJM
    # export that adds either is picked up automatically instead of ignored.
    "poi_substation": [
        "interconnection location", "poi", "point of interconnection",
        "substation",
    ],
    # Deliberately excludes "Commercial Name": PJM's export does carry that
    # column, but it's ambiguous whether it names the project or the
    # applicant company, and gridstatus's own normalizer leaves it in its
    # unmapped "extra" bucket rather than treating it as the applicant
    # entity. Guessing wrong here would mislabel a project's marketing name
    # as a company name with false confidence, so this is left to the
    # explicit "not published" fallback unless a clearer alias matches.
    "developer_entity": ["interconnecting entity", "developer", "applicant"],
}


@dataclass
class SourceStats:
    """Per-source pipeline counters, surfaced in the final run summary."""

    source: str
    rows_fetched: int = 0
    excluded_by_status: int = 0
    excluded_status_values: Counter = field(default_factory=Counter)
    excluded_by_capacity: int = 0
    excluded_by_load_type: int = 0
    passed_filters: int = 0
    rows_valid: int = 0
    rows_rejected_validation: int = 0
    aggregate_mw: float = 0.0
    fetch_errors: list[str] = field(default_factory=list)


def fetch_pjm_raw_bytes(
    session: requests.Session,
    export_key: str = PJM_QUEUE_EXPORT_DEFAULT_KEY,
) -> bytes:
    """POST to PJM's public planning-queue export endpoint and return the
    raw response body (an .xlsx). Raises requests.HTTPError / RequestException
    on failure after the session's retry policy is exhausted -- callers
    decide whether that's fatal or falls back to a CSV file on disk."""
    logger.info("Fetching PJM interconnection queue export")
    response = request_with_retries(
        session,
        "POST",
        PJM_QUEUE_EXPORT_URL,
        headers={
            "api-subscription-key": export_key,
            "Host": "services.pjm.com",
            "Origin": "https://www.pjm.com",
            "Referer": "https://www.pjm.com/",
        },
    )
    return response.content


def fetch_pjm_dataminer_feed(
    session: requests.Session,
    feed: str,
    api_key: str,
) -> pd.DataFrame:
    """Optional path: query a specific Data Miner 2 feed directly. Not used
    by default (see module docstring) -- exists for the case where you know
    of a real feed name this research didn't surface, or PJM adds one."""
    logger.info("Querying PJM Data Miner 2 feed '%s'", feed)
    response = request_with_retries(
        session,
        "GET",
        PJM_DATAMINER_BASE + feed,
        headers={"Ocp-Apim-Subscription-Key": api_key},
        params={"rowCount": 50000},
    )
    payload = response.json()
    items = payload.get("items", payload) if isinstance(payload, dict) else payload
    return pd.DataFrame(items)


def unwrap_zip_if_needed(raw_bytes: bytes, wanted_exts: tuple[str, ...]) -> bytes:
    """Both PJM and ERCOT occasionally serve a workbook wrapped in a zip
    (and a genuine .xlsx *is* a valid zip container, which this must not
    confuse for a wrapper). If `raw_bytes` is a zip that contains a file
    with one of `wanted_exts`, return that member's bytes; otherwise return
    `raw_bytes` unchanged."""
    if raw_bytes[:2] != b"PK":
        return raw_bytes
    # NB: a genuine .xlsx IS a zip container, but its internal members are
    # XML parts (xl/workbook.xml, [Content_Types].xml, ...) -- never a file
    # named *.xlsx/*.csv. So this only ever matches an actual wrapper zip.
    buf = io.BytesIO(raw_bytes)
    try:
        with zipfile.ZipFile(buf) as zf:
            candidates = [n for n in zf.namelist() if n.lower().endswith(wanted_exts)]
            if candidates:
                return zf.read(candidates[0])
    except zipfile.BadZipFile:
        pass
    return raw_bytes


def load_pjm_dataframe_from_bytes(raw_bytes: bytes) -> pd.DataFrame:
    """Parse the raw PJM export into a DataFrame. Defensive against the
    workbook being wrapped in a zip (some PJM export paths do this) and
    against a clean top-of-file header (the normal case, confirmed against
    gridstatus's straight `pd.read_excel(raw_data)` call) as well as a
    stray title row above it (defensive; costs nothing if absent)."""
    raw_bytes = unwrap_zip_if_needed(raw_bytes, (".xlsx", ".xls"))
    buf = io.BytesIO(raw_bytes)
    raw_headerless = pd.read_excel(buf, header=None, dtype=object)
    header_row = locate_header_row(
        raw_headerless,
        {k: v for k, v in PJM_COLUMN_ALIASES.items() if k in ("queue_id", "county", "status")},
        max_scan_rows=10,
        min_hits=2,
    )
    buf.seek(0)
    if header_row is None:
        return pd.read_excel(buf, dtype=object)
    return pd.read_excel(buf, header=header_row, dtype=object)


def normalize_pjm_records(df: pd.DataFrame, stats: SourceStats) -> list[dict]:
    """Map PJM's raw columns onto the shared schema and apply the shared
    filters. Returns plain dicts (not yet pydantic-validated) so the caller
    can validate + count rejects centrally for both sources."""
    stats.rows_fetched = len(df)
    columns = list(df.columns)

    col_queue_id = locate_column(columns, PJM_COLUMN_ALIASES["queue_id"])
    col_name = locate_column(columns, PJM_COLUMN_ALIASES["project_name"])
    col_county = locate_column(columns, PJM_COLUMN_ALIASES["county"])
    col_state = locate_column(columns, PJM_COLUMN_ALIASES["state"])
    col_status = locate_column(columns, PJM_COLUMN_ALIASES["status"])
    col_capacity = locate_column(columns, PJM_COLUMN_ALIASES["capacity_mw"])
    col_date = locate_column(columns, PJM_COLUMN_ALIASES["projected_date"])
    col_fuel = locate_column(columns, PJM_COLUMN_ALIASES["fuel"])
    col_to = locate_column(columns, PJM_COLUMN_ALIASES["transmission_owner"])
    col_poi = locate_column(columns, PJM_COLUMN_ALIASES["poi_substation"])
    col_dev = locate_column(columns, PJM_COLUMN_ALIASES["developer_entity"])

    missing_required = [
        name for name, col in [
            ("queue id", col_queue_id), ("county", col_county),
            ("status", col_status), ("capacity", col_capacity),
        ] if col is None
    ]
    if missing_required:
        msg = f"PJM export missing required column(s): {missing_required}; skipping source"
        logger.error(msg)
        stats.fetch_errors.append(msg)
        return []

    out: list[dict] = []
    for _, row in df.iterrows():
        try:
            status_label = classify_status(row.get(col_status))
            if status_label is None:
                stats.excluded_by_status += 1
                stats.excluded_status_values[str(row.get(col_status) or "BLANK")] += 1
                continue
            capacity = parse_capacity_mw(row.get(col_capacity))
            if capacity is None or capacity < MIN_CAPACITY_MW:
                stats.excluded_by_capacity += 1
                continue
            qualifies, _load_label = classify_load_type(row.get(col_fuel) if col_fuel else "")
            if not qualifies:
                stats.excluded_by_load_type += 1
                continue
            stats.passed_filters += 1

            to_name = str(row.get(col_to) or "").strip() if col_to else ""
            poi_raw = row.get(col_poi) if col_poi else None
            poi_val = (
                str(poi_raw).strip()
                if poi_raw and str(poi_raw).strip() and str(poi_raw).strip().upper() not in _UNKNOWN_TOKENS
                else f"NOT PUBLISHED BY PJM (Transmission Owner: {to_name or 'unknown'})"
            )
            dev_raw = row.get(col_dev) if col_dev else None
            dev_val = (
                str(dev_raw).strip()
                if dev_raw and str(dev_raw).strip() and str(dev_raw).strip().upper() not in _UNKNOWN_TOKENS
                else "NOT PUBLISHED IN PJM QUEUE EXPORT"
            )

            out.append({
                "queue_id": row.get(col_queue_id),
                "rto_region": "PJM",
                "state": row.get(col_state) or "PA",
                "county": row.get(col_county),
                "poi_substation": poi_val,
                "capacity_mw": capacity,
                "projected_date": row.get(col_date) if col_date else None,
                "developer_entity": dev_val,
                "status": status_label,
                "project_name": row.get(col_name) if col_name else None,
                "raw_fuel_technology": row.get(col_fuel) if col_fuel else None,
            })
        except Exception as exc:  # noqa: BLE001 - one bad row must not kill the run
            logger.debug("Skipping malformed PJM row: %s", exc)
            continue
    return out


# --------------------------------------------------------------------------
# ERCOT ingestion
# --------------------------------------------------------------------------
# Verified (Sept 2026) against: ERCOT's own market notice documenting its
# current (post legacy-URL-decommission) public report scheme; the
# gridstatus library's ERCOT module, which implements a working scraper
# against this exact mechanism; and ERCOT's public GIS Report product page
# (Report Type ID 15933).
#
#   * Report listing:  GET  https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=<id>
#   * Report download: GET  https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId=<docId>
#   * GIS Report (generation interconnection status), RTID 15933, has a
#     "Project Details - Large Gen" sheet (and, per gridstatus's own
#     in-progress TODOs, likely a small-gen / inactive / cancelled sheet
#     too) with roughly 30+ rows of title/legend content above the real
#     header row -- confirmed via gridstatus's `skiprows=30` -- which is
#     exactly the "messy real workbook" case the dynamic header/column
#     finders below exist for, rather than a hardcoded skip count.
#   * ERCOT sits behind bot-mitigation (Incapsula/Imperva); a realistic,
#     rotating desktop User-Agent (see USER AGENT HANDLING above) is a
#     normal, non-adversarial way to reliably reach a page that is public
#     by ERCOT's own design -- it is what any ordinary browser sends.
#
# Large Load: as of this research, ERCOT does not publish a stable,
# single-URL, per-project CSV/XLSX register of Large Load interconnection
# requests the way it does generation (see module docstring, point 3). The
# function below is fully implemented against a URL you supply and will
# parse a real file the moment one exists at a stable address; absent that
# URL it logs why and returns an empty frame instead of guessing.

ERCOT_DOC_LIST_URL = "https://www.ercot.com/misapp/servlets/IceDocListJsonWS"
ERCOT_DOC_DOWNLOAD_URL = "https://www.ercot.com/misdownload/servlets/mirDownload"
ERCOT_GIS_REPORT_TYPE_ID = 15933
ERCOT_GIS_NAME_CONTAINS = "GIS_Report"
ERCOT_LARGE_LOAD_INFO_PAGE = "https://www.ercot.com/services/rq/large-load-integration"

# ERCOT's GIS Report stores Fuel/Technology as short internal codes, not
# words -- confirmed against gridstatus's ERCOT normalizer. classify_load_type()
# matches against human-readable keywords, so these codes must be expanded
# before classification or every row silently falls through as "unclassified"
# instead of being correctly identified/rejected.
ERCOT_FUEL_CODE_MAP = {
    "BIO": "Biomass", "COA": "Coal", "GAS": "Gas", "GEO": "Geothermal",
    "HYD": "Hydrogen", "NUC": "Nuclear", "OIL": "Fuel Oil", "OTH": "Other",
    "PET": "Petcoke", "SOL": "Solar", "WAT": "Water", "WIN": "Wind",
}
ERCOT_TECHNOLOGY_CODE_MAP = {
    "BA": "Battery Energy Storage", "CC": "Combined-Cycle",
    "CE": "Compressed Air Energy Storage", "CP": "Concentrated Solar Power",
    "EN": "Energy Storage", "FC": "Fuel Cell",
    "GT": "Combustion (gas) Turbine, not part of a Combined-Cycle",
    "HY": "Hydroelectric Turbine",
    "IC": "Internal Combustion Engine, eg. Reciprocating",
    "OT": "Other", "PV": "Photovoltaic Solar",
    "ST": "Steam Turbine other than Combined-Cycle", "WT": "Wind Turbine",
}


def expand_ercot_code(raw: Any, code_map: dict[str, str]) -> str:
    """Expand a short ERCOT fuel/technology code to its full name; passes
    unrecognized values through unchanged (rather than dropping them) since
    an unmapped code is still meaningful input to classify_load_type."""
    s = str(raw or "").strip()
    return code_map.get(s.upper(), s)

ERCOT_COLUMN_ALIASES = {
    "queue_id": ["inr", "queue id", "interconnection request"],
    "project_name": ["project name"],
    "county": ["county"],
    "poi_substation": ["poi location", "point of interconnection", "substation"],
    "capacity_mw": ["capacity (mw)", "capacity mw", "requested mw", "mw"],
    "projected_date": ["projected cod", "projected in-service date", "projected in service date"],
    "developer_entity": ["interconnecting entity", "developer", "applicant"],
    "fuel": ["fuel"],
    "technology": ["technology"],
    "gim_study_phase": ["gim study phase", "study phase"],
    "screening_started": ["screening study started"],
    "screening_complete": ["screening study complete"],
    "fis_requested": ["fis requested"],
    "fis_approved": ["fis approved"],
    "ia_signed": ["ia signed"],
    "approved_energization": ["approved for energization"],
    "approved_synchronization": ["approved for synchronization"],
    "voltage": ["kv", "voltage", "poi voltage"],
}

# Columns whose presence is enough to call a scanned row a plausible header
# for an ERCOT project-detail sheet (kept short and high-signal so summary/
# definitions/notes tabs don't get misidentified as data sheets).
ERCOT_HEADER_SIGNAL_ALIASES = {
    "queue_id": ERCOT_COLUMN_ALIASES["queue_id"],
    "county": ERCOT_COLUMN_ALIASES["county"],
    "capacity_mw": ERCOT_COLUMN_ALIASES["capacity_mw"],
    "project_name": ERCOT_COLUMN_ALIASES["project_name"],
}

# Confirmed against a real ERCOT GIS Report (see parse_workbook_sheets_dynamically
# docstring): these sheet names carry real project rows with a header that
# would otherwise pass detection, but represent projects that have exited
# the active queue (or, for "Commissioning Update", already completed it) --
# status derivation has nothing to key off for them, so they must be
# excluded by name rather than left to fall through to a default.
ERCOT_EXCLUDE_SHEET_KEYWORDS = ("inactive", "cancel", "commissioning", "withdrawn", "summary", "trends")


def ercot_list_documents(session: requests.Session, report_type_id: int) -> list[dict]:
    """List all published documents for an ERCOT report type."""
    response = request_with_retries(
        session, "GET", ERCOT_DOC_LIST_URL, params={"reportTypeId": report_type_id},
    )
    payload = response.json()
    raw_docs = payload.get("ListDocsByRptTypeRes", {}).get("DocumentList", [])
    docs = []
    for entry in raw_docs:
        d = entry.get("Document", entry)
        docs.append({
            "doc_id": d.get("DocID"),
            "publish_date": d.get("PublishDate"),
            "constructed_name": d.get("ConstructedName", ""),
            "friendly_name": d.get("FriendlyName", ""),
        })
    return docs


def ercot_pick_latest_document(docs: list[dict], name_contains: str) -> Optional[dict]:
    matches = [d for d in docs if name_contains.lower() in (d.get("constructed_name") or "").lower()]
    if not matches:
        return None

    def sort_key(d: dict):
        try:
            return pd.Timestamp(d["publish_date"])
        except Exception:
            return pd.Timestamp.min

    return max(matches, key=sort_key)


def fetch_ercot_document_bytes(session: requests.Session, doc_id: Any) -> bytes:
    response = request_with_retries(
        session, "GET", ERCOT_DOC_DOWNLOAD_URL, params={"doclookupId": doc_id},
    )
    return response.content


def fetch_ercot_gis_workbook(session: requests.Session) -> bytes:
    logger.info("Listing ERCOT GIS Report documents (reportTypeId=%s)", ERCOT_GIS_REPORT_TYPE_ID)
    docs = ercot_list_documents(session, ERCOT_GIS_REPORT_TYPE_ID)
    latest = ercot_pick_latest_document(docs, ERCOT_GIS_NAME_CONTAINS)
    if latest is None:
        raise RuntimeError(
            f"No ERCOT document found whose name contains {ERCOT_GIS_NAME_CONTAINS!r} "
            f"among {len(docs)} listed documents for reportTypeId={ERCOT_GIS_REPORT_TYPE_ID}"
        )
    logger.info(
        "Downloading ERCOT GIS Report doc_id=%s published=%s",
        latest["doc_id"], latest["publish_date"],
    )
    return fetch_ercot_document_bytes(session, latest["doc_id"])


def drop_leading_sparse_rows(df: pd.DataFrame, key_columns: list[str], max_drop: int = 10) -> pd.DataFrame:
    """After locating the header row, real data sometimes doesn't start
    immediately below it (a units row, a sub-header, blank spacer rows --
    confirmed present in the real ERCOT GIS sheet via gridstatus's own
    `.iloc[4:]`). Drop leading rows where every key column is blank, up to
    `max_drop` rows, rather than hardcoding how many to skip."""
    present_keys = [c for c in key_columns if c in df.columns]
    if not present_keys:
        return df
    dropped = 0
    idx = df.index.tolist()
    for i in idx[:max_drop]:
        row = df.loc[i, present_keys]
        if row.isna().all() or all(str(v).strip() == "" for v in row):
            dropped += 1
        else:
            break
    return df.iloc[dropped:] if dropped else df


def parse_workbook_sheets_dynamically(
    raw_bytes: bytes,
    alias_groups: dict[str, list[str]],
    header_signal_aliases: dict[str, list[str]],
    max_scan_rows: int = 60,
    min_header_hits: int = 3,
    sheet_name_exclude_keywords: tuple[str, ...] = (),
) -> pd.DataFrame:
    """Generic multi-tab workbook parser: for every sheet, dynamically find
    the header row (if any) by fuzzy-matching against `header_signal_aliases`,
    parse that sheet from there, drop sparse leading rows, tag the sheet
    name, and concatenate every sheet that produced a plausible header.
    Sheets with no recognizable header (Summary/Definitions/Notes/etc.) are
    skipped, not treated as errors.

    `sheet_name_exclude_keywords`: sheet names containing any of these
    (case-insensitive) are skipped regardless of whether their columns would
    otherwise match -- for sheets that are structurally plausible but
    semantically wrong. Confirmed necessary against a real ERCOT GIS Report:
    its "Inactive Projects" and "Cancellation Update" sheets both carry a
    real INR/Project Name/County/MW header (enough to pass header detection)
    but none of the milestone columns status derivation depends on, so
    without this exclusion every row on those two sheets would silently
    default to "Active" and pollute the output with projects that are, by
    definition, no longer in the queue.
    """
    raw_bytes = unwrap_zip_if_needed(raw_bytes, (".xlsx", ".xls"))
    buf = io.BytesIO(raw_bytes)
    try:
        sheet_names = pd.ExcelFile(buf).sheet_names
    except Exception as exc:
        raise RuntimeError(f"Could not open workbook: {exc}") from exc

    frames = []
    for sheet in sheet_names:
        if sheet_name_exclude_keywords and any(
            kw.lower() in sheet.lower() for kw in sheet_name_exclude_keywords
        ):
            logger.debug("Skipping sheet %r (matches exclude keyword)", sheet)
            continue
        buf.seek(0)
        try:
            raw_headerless = pd.read_excel(buf, sheet_name=sheet, header=None, dtype=object)
        except Exception as exc:
            logger.debug("Skipping unreadable sheet %r: %s", sheet, exc)
            continue
        header_row = locate_header_row(
            raw_headerless, header_signal_aliases,
            max_scan_rows=max_scan_rows, min_hits=min_header_hits,
        )
        if header_row is None:
            logger.debug("No data-like header found in sheet %r; skipping", sheet)
            continue

        buf.seek(0)
        sheet_df = pd.read_excel(buf, sheet_name=sheet, header=header_row, dtype=object)
        sheet_df = sheet_df.dropna(how="all")

        real_key_cols = [
            locate_column(sheet_df.columns, alias_groups.get(k, [k]))
            for k in ("queue_id", "capacity_mw")
        ]
        real_key_cols = [c for c in real_key_cols if c]
        if real_key_cols:
            sheet_df = drop_leading_sparse_rows(sheet_df, real_key_cols)

        sheet_df["_source_sheet"] = sheet
        frames.append(sheet_df)
        logger.info("Parsed %d rows from sheet %r (header at row %d)", len(sheet_df), sheet, header_row)

    if not frames:
        raise RuntimeError(
            f"No sheet in this workbook matched the expected column layout "
            f"(sheets present: {sheet_names})"
        )
    return pd.concat(frames, ignore_index=True, sort=False)


def derive_ercot_status(row: "pd.Series", cols: dict[str, Optional[str]]) -> Optional[str]:
    """Status classification for ERCOT rows. ERCOT's GIS report has no
    single free-text Status column the way PJM's export does; gridstatus
    itself only derives a binary Active/Completed split from IA Signed. This
    tries the richer 'GIM Study Phase' text first (fuzzy-matched the same
    way as PJM's Status column) and falls back to the study-milestone
    columns (Screening/FIS/IA Signed/Approved-for-*) when that's blank or
    unrecognized, so the same five-category filter the user specified can
    still be applied meaningfully to ERCOT's differently-shaped data."""

    def val(key: str) -> Any:
        col = cols.get(key)
        return row.get(col) if col else None

    phase_label = classify_status(val("gim_study_phase"))
    if phase_label is not None:
        return phase_label

    def populated(key: str) -> bool:
        v = val(key)
        return v is not None and str(v).strip() != "" and str(v).strip().upper() not in _UNKNOWN_TOKENS

    if populated("approved_synchronization") or populated("approved_energization"):
        return None  # already energized/in service -- not a pipeline load anymore
    if populated("ia_signed"):
        return "IA in Progress"
    if populated("fis_requested"):
        return "Facilities Study"
    if populated("screening_started"):
        return "Under Study"
    return "Active"  # still an open queue position; no milestones recorded yet


def normalize_ercot_records(df: pd.DataFrame, stats: SourceStats) -> list[dict]:
    stats.rows_fetched = len(df)
    columns = list(df.columns)

    col_map = {k: locate_column(columns, aliases) for k, aliases in ERCOT_COLUMN_ALIASES.items()}

    missing_required = [
        name for name in ("queue_id", "county", "capacity_mw") if col_map.get(name) is None
    ]
    if missing_required:
        msg = f"ERCOT workbook missing required column(s): {missing_required}; skipping source"
        logger.error(msg)
        stats.fetch_errors.append(msg)
        return []

    out: list[dict] = []
    for _, row in df.iterrows():
        try:
            status_label = derive_ercot_status(row, col_map)
            if status_label is None:
                stats.excluded_by_status += 1
                continue

            capacity = parse_capacity_mw(row.get(col_map["capacity_mw"]))
            if capacity is None or capacity < MIN_CAPACITY_MW:
                stats.excluded_by_capacity += 1
                continue

            fuel_raw = row.get(col_map["fuel"]) if col_map.get("fuel") else ""
            tech_raw = row.get(col_map["technology"]) if col_map.get("technology") else ""
            fuel_val = expand_ercot_code(fuel_raw, ERCOT_FUEL_CODE_MAP)
            tech_val = expand_ercot_code(tech_raw, ERCOT_TECHNOLOGY_CODE_MAP)
            combined_type = f"{fuel_val} - {tech_val}"
            qualifies, _load_label = classify_load_type(combined_type)
            if not qualifies:
                stats.excluded_by_load_type += 1
                continue
            stats.passed_filters += 1

            poi_raw = row.get(col_map["poi_substation"]) if col_map.get("poi_substation") else None
            poi_str = str(poi_raw).strip() if poi_raw is not None else ""
            if poi_str and poi_str.upper() not in _UNKNOWN_TOKENS:
                if col_map.get("voltage") and "kv" not in poi_str.lower():
                    v = row.get(col_map["voltage"])
                    if v is not None and str(v).strip() and str(v).strip().upper() not in _UNKNOWN_TOKENS:
                        poi_str = f"{poi_str} ({str(v).strip()} kV)"
            else:
                poi_str = "UNKNOWN"

            dev_raw = row.get(col_map["developer_entity"]) if col_map.get("developer_entity") else None
            dev_val = (
                str(dev_raw).strip()
                if dev_raw is not None and str(dev_raw).strip()
                and str(dev_raw).strip().upper() not in _UNKNOWN_TOKENS
                else "UNKNOWN"
            )

            out.append({
                "queue_id": row.get(col_map["queue_id"]),
                "rto_region": "ERCOT",
                "state": "TX",
                "county": row.get(col_map["county"]),
                "poi_substation": poi_str,
                "capacity_mw": capacity,
                "projected_date": row.get(col_map["projected_date"]) if col_map.get("projected_date") else None,
                "developer_entity": dev_val,
                "status": status_label,
                "project_name": row.get(col_map["project_name"]) if col_map.get("project_name") else None,
                "raw_fuel_technology": combined_type,
            })
        except Exception as exc:  # noqa: BLE001
            logger.debug("Skipping malformed ERCOT row: %s", exc)
            continue
    return out


def fetch_ercot_large_load_status(
    session: requests.Session, url: Optional[str] = None,
) -> Optional[pd.DataFrame]:
    """Real, working code path for a per-project ERCOT Large Load register
    -- IF you have a URL for one. As of the research behind this script
    (Sept 2026), ERCOT does not publish one at a stable address: the Large
    Load Interconnection process (PGRR145 / 'Batch Zero') is currently
    forms-and-attestations based, and ERCOT's own Large Load Integration
    page describes a public 'Large Load Portal' as still in development.
    Pass --ercot-large-load-url once that changes (or if you have separately
    authorized access to a members-only extract in the same shape), and
    this will parse it with the same dynamic multi-sheet engine used for
    the GIS Report. Returns None (not an exception) when no URL is given,
    so the pipeline continues normally on GIS-report-derived data alone."""
    if not url:
        logger.warning(
            "No ERCOT large-load register URL configured -- as researched, ERCOT "
            "does not currently publish one at a stable public address (see %s). "
            "Skipping; pass --ercot-large-load-url if you have one.",
            ERCOT_LARGE_LOAD_INFO_PAGE,
        )
        return None
    logger.info("Fetching ERCOT large-load status file from %s", url)
    response = request_with_retries(session, "GET", url)
    return parse_workbook_sheets_dynamically(
        response.content, ERCOT_COLUMN_ALIASES, ERCOT_HEADER_SIGNAL_ALIASES,
        sheet_name_exclude_keywords=ERCOT_EXCLUDE_SHEET_KEYWORDS,
    )


# --------------------------------------------------------------------------
# Validation, dedup, output
# --------------------------------------------------------------------------

OUTPUT_COLUMNS = [
    "queue_id", "rto_region", "state", "county", "poi_substation",
    "capacity_mw", "projected_date", "developer_entity",
]
# Opt-in only (--include-raw-fields): status and project_name aren't part of
# the specified schema, but downstream tooling (entity resolution, anomaly
# flagging) can use them if present -- see InterconnectionRecord docstring.
EXTENDED_OUTPUT_COLUMNS = OUTPUT_COLUMNS + ["status", "project_name", "raw_fuel_technology"]


def validate_records(raw_dicts: list[dict], stats: SourceStats) -> list[InterconnectionRecord]:
    """Run each already-filtered raw dict through the strict Pydantic schema.
    A single malformed row is logged and dropped, never allowed to crash the
    run -- matches the 'no unhandled exceptions' requirement while still
    making every rejection visible via --log-level DEBUG."""
    validated: list[InterconnectionRecord] = []
    for d in raw_dicts:
        clean = {k: v for k, v in d.items() if not k.startswith("_")}
        try:
            record = InterconnectionRecord(**clean)
        except ValidationError as exc:
            stats.rows_rejected_validation += 1
            logger.debug(
                "Row failed schema validation (source=%s queue_id=%r): %s",
                stats.source, d.get("queue_id"), exc.errors()[0].get("msg", exc),
            )
            continue
        validated.append(record)
        stats.rows_valid += 1
        stats.aggregate_mw += record.capacity_mw
    return validated


def dedupe_records(records: list[InterconnectionRecord]) -> list[InterconnectionRecord]:
    """De-dupe on (rto_region, queue_id); first occurrence wins. Matters
    because a queue id can legitimately reappear across sheets (e.g. an
    ERCOT project present in both a fuel-specific tab and a rolled-up tab)."""
    seen: set[tuple[str, str]] = set()
    out: list[InterconnectionRecord] = []
    for r in records:
        key = (r.rto_region, r.queue_id)
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def write_output_csv(
    records: list[InterconnectionRecord], path: Path, include_extra_fields: bool = False,
) -> None:
    rows = [r.model_dump() for r in records]
    columns = EXTENDED_OUTPUT_COLUMNS if include_extra_fields else OUTPUT_COLUMNS
    df = pd.DataFrame(rows, columns=columns)
    df.sort_values(["capacity_mw"], ascending=False, inplace=True)
    df.to_csv(path, index=False)


# --------------------------------------------------------------------------
# Pipeline orchestration
# --------------------------------------------------------------------------

@dataclass
class PipelineResult:
    records: list[InterconnectionRecord]
    stats: dict[str, SourceStats]
    elapsed_seconds: float


def run_pipeline(
    pjm_export_key: str = PJM_QUEUE_EXPORT_DEFAULT_KEY,
    pjm_dataminer_feed: Optional[str] = None,
    pjm_api_key: Optional[str] = None,
    ercot_large_load_url: Optional[str] = None,
    fixture_bytes: Optional[dict[str, bytes]] = None,
) -> PipelineResult:
    """Run the full extract -> normalize -> filter -> validate pipeline
    against both sources. Each source is wrapped independently so a failure
    in one (dead endpoint, changed schema, network outage) still lets the
    other complete and produce partial output rather than aborting the run.

    `fixture_bytes`, keyed by "pjm" / "ercot_gis" / "ercot_large_load", lets
    --selftest (and anyone else) substitute synthetic workbooks for the live
    HTTP fetch without touching any other code path -- the parse/normalize/
    filter/validate logic exercised is identical either way.
    """
    start = time.monotonic()
    session = build_http_session()
    fixture_bytes = fixture_bytes or {}
    all_records: list[InterconnectionRecord] = []
    stats: dict[str, SourceStats] = {}

    # --- PJM -------------------------------------------------------------
    pjm_stats = SourceStats(source="PJM")
    try:
        if "pjm" in fixture_bytes:
            raw_bytes = fixture_bytes["pjm"]
        else:
            raw_bytes = fetch_pjm_raw_bytes(session, export_key=pjm_export_key)
        pjm_df = load_pjm_dataframe_from_bytes(raw_bytes)
        pjm_raw_records = normalize_pjm_records(pjm_df, pjm_stats)
        all_records.extend(validate_records(pjm_raw_records, pjm_stats))
    except Exception as exc:  # noqa: BLE001
        logger.error("PJM ingestion failed: %s", exc)
        pjm_stats.fetch_errors.append(str(exc))
    stats["PJM"] = pjm_stats

    if pjm_dataminer_feed and pjm_api_key:
        dm_stats = SourceStats(source="PJM-DataMiner2")
        try:
            dm_df = fetch_pjm_dataminer_feed(session, pjm_dataminer_feed, pjm_api_key)
            dm_raw_records = normalize_pjm_records(dm_df, dm_stats)
            all_records.extend(validate_records(dm_raw_records, dm_stats))
        except Exception as exc:  # noqa: BLE001
            logger.error("PJM Data Miner 2 ingestion failed: %s", exc)
            dm_stats.fetch_errors.append(str(exc))
        stats["PJM-DataMiner2"] = dm_stats

    # --- ERCOT: GIS Report -------------------------------------------------
    ercot_gis_stats = SourceStats(source="ERCOT-GIS")
    try:
        if "ercot_gis" in fixture_bytes:
            raw_bytes = fixture_bytes["ercot_gis"]
        else:
            raw_bytes = fetch_ercot_gis_workbook(session)
        ercot_df = parse_workbook_sheets_dynamically(
            raw_bytes, ERCOT_COLUMN_ALIASES, ERCOT_HEADER_SIGNAL_ALIASES,
            sheet_name_exclude_keywords=ERCOT_EXCLUDE_SHEET_KEYWORDS,
        )
        ercot_raw_records = normalize_ercot_records(ercot_df, ercot_gis_stats)
        all_records.extend(validate_records(ercot_raw_records, ercot_gis_stats))
    except Exception as exc:  # noqa: BLE001
        logger.error("ERCOT GIS Report ingestion failed: %s", exc)
        ercot_gis_stats.fetch_errors.append(str(exc))
    stats["ERCOT-GIS"] = ercot_gis_stats

    # --- ERCOT: Large Load (best-effort; see fetch_ercot_large_load_status) -
    ercot_ll_stats = SourceStats(source="ERCOT-LargeLoad")
    try:
        if "ercot_large_load" in fixture_bytes:
            ll_df = parse_workbook_sheets_dynamically(
                fixture_bytes["ercot_large_load"], ERCOT_COLUMN_ALIASES, ERCOT_HEADER_SIGNAL_ALIASES,
            )
        else:
            ll_df = fetch_ercot_large_load_status(session, url=ercot_large_load_url)
        if ll_df is not None:
            ll_raw_records = normalize_ercot_records(ll_df, ercot_ll_stats)
            all_records.extend(validate_records(ll_raw_records, ercot_ll_stats))
    except Exception as exc:  # noqa: BLE001
        logger.error("ERCOT large-load ingestion failed: %s", exc)
        ercot_ll_stats.fetch_errors.append(str(exc))
    stats["ERCOT-LargeLoad"] = ercot_ll_stats

    deduped = dedupe_records(all_records)
    elapsed = time.monotonic() - start
    return PipelineResult(records=deduped, stats=stats, elapsed_seconds=elapsed)


def write_source_health(result: PipelineResult, path: Path) -> None:
    """Write source-level health evidence used by the registry refresh guard."""
    payload = {
        "version": 1,
        "generated_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "sources": {
            name: {
                "rows_fetched": s.rows_fetched,
                "excluded_by_status": s.excluded_by_status,
                "excluded_by_capacity": s.excluded_by_capacity,
                "excluded_by_load_type": s.excluded_by_load_type,
                "passed_filters": s.passed_filters,
                "rows_valid": s.rows_valid,
                "rows_rejected_validation": s.rows_rejected_validation,
                "aggregate_mw": round(s.aggregate_mw, 3),
                "fetch_errors": list(s.fetch_errors),
                "excluded_status_values": dict(s.excluded_status_values),
            }
            for name, s in result.stats.items()
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def log_run_summary(result: PipelineResult, output_path: Path) -> None:
    logger.info("=" * 72)
    logger.info("PIPELINE RUN SUMMARY")
    logger.info("=" * 72)
    total_fetched = total_valid = total_rejected = 0
    for name, s in result.stats.items():
        logger.info(
            "[%s] fetched=%d  excluded(status=%d capacity=%d load_type=%d)  "
            "passed_filters=%d  valid=%d  schema_rejected=%d  aggregate_mw=%.1f",
            name, s.rows_fetched, s.excluded_by_status, s.excluded_by_capacity,
            s.excluded_by_load_type, s.passed_filters, s.rows_valid,
            s.rows_rejected_validation, s.aggregate_mw,
        )
        if s.excluded_status_values:
            top = s.excluded_status_values.most_common(8)
            logger.info(
                "[%s] top excluded-by-status values: %s",
                name,
                ", ".join(f"{v!r}={n}" for v, n in top),
            )
        if s.fetch_errors:
            for err in s.fetch_errors:
                logger.warning("[%s] error: %s", name, err)
        total_fetched += s.rows_fetched
        total_valid += s.rows_valid
        total_rejected += s.rows_rejected_validation
    deduped_count = len(result.records)
    total_mw = sum(r.capacity_mw for r in result.records)
    logger.info("-" * 72)
    logger.info("Total rows parsed across all sources : %d", total_fetched)
    logger.info("Total rows passing schema validation  : %d", total_valid)
    logger.info("Total rows rejected by schema          : %d", total_rejected)
    logger.info("Final rows after cross-source dedup    : %d", deduped_count)
    logger.info("Aggregate MW in final registry          : %.1f MW", total_mw)
    logger.info("Elapsed time                             : %.2fs", result.elapsed_seconds)
    logger.info("Output written to                        : %s", output_path)
    logger.info("=" * 72)


# --------------------------------------------------------------------------
# Self-test: synthetic fixtures built to match the *real* confirmed layouts
# --------------------------------------------------------------------------
# These are not round-trip-with-itself tests -- they're hand-built to
# reproduce the specific real quirks this script has to survive: PJM's
# clean single-row header with no POI/developer columns; ERCOT's ~30 junk
# rows before the header, sparse rows immediately below it, short fuel/tech
# codes, and a non-data "Summary" tab sitting alongside the real one.

def _build_synthetic_pjm_xlsx() -> bytes:
    columns = [
        "Project ID", "Name", "County", "State", "Transmission Owner", "Status",
        "MW Capacity", "MFO", "Projected In Service Date", "Fuel", "Commercial Name",
    ]
    rows = [
        ["AF2-045", "Alpha Compute Campus", "Loudoun", "VA", "Dominion", "Active",
         450, 460, "2028-06-01", "Storage", "Alpha DC Holdco"],
        ["AF2-046", "Beta Solar Farm", "Fauquier", "VA", "Dominion", "Active",
         180, 190, "2027-03-01", "Solar", "Beta Solar LLC"],
        ["AF2-047", "Gamma Industrial Load", "Prince William", "VA", "Dominion",
         "Facilities Study", 220, 230, "2029-Q1", "Other", "Gamma Industrial Inc"],
        ["AF2-048", "Delta Small Battery", "Culpeper", "PA", "PPL", "Under Study",
         40, 45, "2028-01-01", "Storage", "Delta Storage LLC"],       # <100MW -> excluded
        ["AF2-049", "Epsilon Wind", "Somerset", "PA", "PPL", "Active",
         300, 310, "2028-09-01", "Wind", "Epsilon Wind LLC"],         # wind -> excluded
        ["AF2-050", "Zeta Withdrawn DC", "York", "PA", "PPL", "Withdrawn",
         500, 500, "2027-01-01", "Other", "Zeta LLC"],                # withdrawn -> excluded
        ["AF2-051", "Eta IA Progress Load", "Chester", "PA", "PECO", "IA in Progress",
         275, 280, "06/2029", "Storage", "Eta Compute LLC"],
        ["AF2-052", "Theta Unclassified Load", "Berks", "PA", "PPL", "Engineering Review",
         160, 165, None, "Load", "Theta Devco"],                      # malformed/missing date -> UNKNOWN
    ]
    df = pd.DataFrame(rows, columns=columns)
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Queue")
    return bio.getvalue()


def _build_synthetic_ercot_xlsx() -> bytes:
    header = [
        "INR", "Project Name", "Interconnecting Entity", "POI Location", "County",
        "Capacity (MW)", "Fuel", "Technology", "GIM Study Phase",
        "Screening Study Started", "Screening Study Complete", "FIS Requested",
        "FIS Approved", "IA Signed", "Approved for Energization",
        "Approved for Synchronization", "Projected COD",
    ]
    width = len(header)
    data_rows = [
        ["23INR0001", "Large Load Explicit Phase", "GridCo Devco LLC", "Riley 345 kV", "Reeves",
         350, "OTH", "OT", "Facilities Study", "2024-01-01", "2024-06-01", "2024-07-01",
         None, None, None, None, "2027-Q2"],
        ["23INR0007", "Pure Solar Farm Explicit Status", "SolarCo LLC", "Odessa 138 kV", "Ector",
         300, "SOL", "PV", "Facilities Study", "2024-01-01", "2024-06-01", "2024-07-01",
         None, None, None, None, "2027-Q3"],                          # valid status, wrong load type -> excluded
        ["23INR0002", "Compute Campus West", "Hyperscale Devco LLC", "Big Country 138 kV",
         "Ward", 500, "OTH", "OT", None, "2024-02-01", None, None, None, None, None,
         None, "2028-01-01"],                                        # no phase -> derived "Under Study"
        ["23INR0003", "Battery Storage Node", "GridStore LLC", "Odessa 345 kV", "Ector",
         150, "OTH", "BA", None, "2024-01-15", "2024-05-01", "2024-06-01", "2024-08-01",
         "2024-09-01", None, None, "2027-Q4"],                       # IA signed -> "IA in Progress"
        ["23INR0004", "Small Wind Farm", "WindCo", "Panhandle 138 kV", "Moore",
         80, "WIN", "WT", "Under Study", "2024-03-01", None, None, None, None, None,
         None, "2028-06-01"],                                        # <100MW -> excluded
        ["23INR0005", "Big Wind Farm", "WindCo", "Panhandle 345 kV", "Moore",
         400, "WIN", "WT", "Under Study", "2024-03-01", None, None, None, None, None,
         None, "2028-06-01"],                                        # wind -> excluded by load type
        ["23INR0006", "Energized DC Campus", "AlreadyLiveCo", "Sandow 345 kV", "Milam",
         600, "OTH", "OT", None, "2022-01-01", "2022-06-01", "2022-07-01", "2022-09-01",
         "2022-10-01", "2023-01-01", "2023-03-01", "2023-06-01"],    # already energized -> excluded
    ]
    for r in data_rows:
        assert len(r) == width, f"fixture row width mismatch: {r}"

    title_block = [
        ["ERCOT GIS REPORT"] + [None] * (width - 1),
        ["Interconnection milestone and trend information for generation resources"] + [None] * (width - 1),
        ["Report generated 2026-09-01"] + [None] * (width - 1),
    ]
    blank_rows = [[None] * width for _ in range(26)]           # pad to ~30 junk rows before header
    sparse_rows_below_header = [[None] * width for _ in range(3)]  # units/sub-header/blank rows

    all_rows = title_block + blank_rows + [header] + sparse_rows_below_header + data_rows
    large_gen_df = pd.DataFrame(all_rows)

    summary_rows = [
        ["ERCOT GIS SUMMARY"] + [None] * 3,
        ["Total Capacity by Fuel Type"] + [None] * 3,
        [None, None, None, None],
        ["Solar", 50000, None, None],
        ["Wind", 42000, None, None],
    ]
    summary_df = pd.DataFrame(summary_rows)

    # Reproduces the real ERCOT layout that caused a genuine bug (see
    # parse_workbook_sheets_dynamically docstring): a real header with no
    # milestone columns, and a capacity comfortably over the 100MW filter --
    # this row must NOT appear in output, and only because it's excluded by
    # sheet name, since on columns alone it would otherwise pass.
    inactive_header = ["INR", "Size Category", "Project Name", "Fuel", "County", "Inactive Date", "MW **"]
    inactive_rows = [
        ["ERCOT Inactive Projects"] + [None] * 6,
        [None] * 7,
        inactive_header,
        ["23INR9001", "Large", "Formerly Big Solar Farm", "SOL", "Pecos", "2025-01-01", 450],
    ]
    inactive_df = pd.DataFrame(inactive_rows)

    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        large_gen_df.to_excel(writer, index=False, header=False, sheet_name="Project Details - Large Gen")
        summary_df.to_excel(writer, index=False, header=False, sheet_name="Summary")
        inactive_df.to_excel(writer, index=False, header=False, sheet_name="Inactive Projects")
    return bio.getvalue()


def run_selftest() -> bool:
    """Exercise the full pipeline end-to-end against synthetic workbooks
    built to match the real, researched column layouts (see the two builder
    functions above for exactly what each simulates and why). Prints a
    pass/fail per assertion and returns True only if everything held."""
    configure_logging("WARNING")  # keep selftest output readable
    print("Running self-test against synthetic PJM + ERCOT fixtures...\n")

    fixtures = {
        "pjm": _build_synthetic_pjm_xlsx(),
        "ercot_gis": _build_synthetic_ercot_xlsx(),
    }
    result = run_pipeline(fixture_bytes=fixtures)

    checks: list[tuple[str, bool]] = []

    checks.append((
        "PJM short status 'EP' maps to Engineering Review",
        classify_status("EP") == "Engineering Review",
    ))
    checks.append((
        "PJM short status 'UC' maps to IA in Progress",
        classify_status("UC") == "IA in Progress",
    ))
    checks.append((
        "PJM live status 'Confirmed' maps to Active",
        classify_status("Confirmed") == "Active",
    ))
    checks.append((
        "PJM live status 'Active - In Service Partially' maps to Active",
        classify_status("Active - In Service Partially") == "Active",
    ))
    checks.append((
        "PJM live status 'Engineering and Procurement' maps to Engineering Review",
        classify_status("Engineering and Procurement") == "Engineering Review",
    ))
    checks.append((
        "PJM live status 'Under Construction' maps to IA in Progress",
        classify_status("Under Construction") == "IA in Progress",
    ))
    checks.append((
        "PJM live status 'Pending Termination' remains excluded",
        classify_status("Pending Termination") is None,
    ))
    checks.append((
        "Status gate: 'INACTIVE' is rejected before 'ACTIVE'",
        classify_status("INACTIVE") is None,
    ))
    checks.append((
        "Status gate: 'Deactivated' is terminal",
        classify_status("Deactivated") is None,
    ))
    checks.append((
        "Status gate: exact 'In Service' is terminal",
        classify_status("In Service") is None,
    ))
    checks.append((
        "Status gate: 'Active - In Service Partially' remains live",
        classify_status("Active - In Service Partially") == "Active",
    ))
    checks.append((
        "Other-than technology guard rejects the exact false-positive phrase",
        classify_load_type("Steam Turbine other than Combined-Cycle")[0] is False,
    ))


    # Real-data finding (see classify_load_type / _accept_keyword_hits
    # docstrings): ERCOT's own technology-code description for Steam
    # Turbine contains the literal substring "other" as ordinary English
    # ("other than Combined-Cycle"), which used to false-trigger the
    # "Other" fuel-category accept path for an unrelated nuclear turbine
    # upgrade. Checked directly against the exact real strings involved.
    nuc_fuel = expand_ercot_code("NUC", ERCOT_FUEL_CODE_MAP)
    steam_tech = expand_ercot_code("ST", ERCOT_TECHNOLOGY_CODE_MAP)
    checks.append((
        "Real-data finding: nuclear steam-turbine upgrade no longer false-accepted "
        "via 'other than Combined-Cycle' containing the substring 'other'",
        classify_load_type(f"{nuc_fuel} - {steam_tech}")[0] is False,
    ))
    checks.append(("Genuine ERCOT 'Other' fuel category still correctly accepted",
                    classify_load_type("Other - Other")[0] is True))
    checks.append(("PJM plain 'Other' fuel value still correctly accepted",
                    classify_load_type("Other")[0] is True))
    checks.append(("Exhaustive fuel x technology sweep: every reject-fuel x "
                    "non-storage-technology combination correctly rejected "
                    "(catches the broader 'bare other overrides any reject' class of bug)",
                    all(
                        classify_load_type(f"{fdesc} - {tdesc}")[0] is False
                        for fcode, fdesc in ERCOT_FUEL_CODE_MAP.items()
                        for tcode, tdesc in ERCOT_TECHNOLOGY_CODE_MAP.items()
                        if fcode in {"BIO", "COA", "GAS", "GEO", "HYD", "NUC", "OIL", "PET", "SOL", "WAT", "WIN"}
                        and tcode not in ("BA", "EN", "CE")
                    )))
    checks.append(("Explicit hybrid wording still correctly accepted ('Solar - Storage Hybrid')",
                    classify_load_type("Solar - Storage Hybrid")[0] is True))
    checks.append(("Conventional hydro ('Water' fuel code) now correctly rejected",
                    classify_load_type("Water - Hydroelectric Turbine")[0] is False))
    checks.append(("Real-data finding: 'Methane' (a real PJM fuel-type value, biogas/landfill-gas "
                    "generation) now correctly rejected -- was previously falling through "
                    "unmatched-defaults-to-accept",
                    classify_load_type("Methane")[0] is False))

    by_id = {r.queue_id: r for r in result.records}

    checks.append(("pipeline produced at least one record", len(result.records) > 0))
    checks.append(("PJM: <100MW row excluded (AF2-048)", "AF2-048" not in by_id))
    checks.append(("PJM: wind row excluded (AF2-049)", "AF2-049" not in by_id))
    checks.append(("PJM: withdrawn row excluded (AF2-050)", "AF2-050" not in by_id))
    checks.append(("PJM: qualifying storage row included (AF2-045)", "AF2-045" in by_id))
    checks.append(("PJM: IA-in-progress row included (AF2-051)", "AF2-051" in by_id))
    if "AF2-045" in by_id:
        rec = by_id["AF2-045"]
        checks.append(("PJM: county title-cased", rec.county == "Loudoun"))
        checks.append(("PJM: state passed through", rec.state == "VA"))
        checks.append((
            "PJM: missing POI/developer honestly flagged",
            "NOT PUBLISHED" in rec.poi_substation and "NOT PUBLISHED" in rec.developer_entity,
        ))
    if "AF2-047" in by_id:
        checks.append(("PJM: 'YYYY-Q#' date form preserved", by_id["AF2-047"].projected_date == "2029-Q1"))
    if "AF2-051" in by_id:
        checks.append(("PJM: 'MM/YYYY' date normalized", by_id["AF2-051"].projected_date == "2029-06-01"))
    if "AF2-052" in by_id:
        checks.append(("PJM: missing date -> UNKNOWN sentinel", by_id["AF2-052"].projected_date == "UNKNOWN"))

    checks.append(("ERCOT: <100MW row excluded (23INR0004)", "23INR0004" not in by_id))
    checks.append(("ERCOT: wind row excluded (23INR0005)", "23INR0005" not in by_id))
    checks.append(("ERCOT: already-energized row excluded (23INR0006)", "23INR0006" not in by_id))
    checks.append(("ERCOT: explicit 'Facilities Study' phase + qualifying load included (23INR0001)",
                    "23INR0001" in by_id))
    checks.append((
        "ERCOT: valid status but pure-solar load type still excluded (23INR0007)",
        "23INR0007" not in by_id,
    ))
    checks.append(("ERCOT: derived-status compute row included (23INR0002)", "23INR0002" in by_id))
    checks.append(("ERCOT: derived-status battery row included (23INR0003)", "23INR0003" in by_id))
    if "23INR0002" in by_id:
        rec = by_id["23INR0002"]
        checks.append(("ERCOT: state hardcoded TX", rec.state == "TX"))
        checks.append(("ERCOT: real developer entity captured", rec.developer_entity == "Hyperscale Devco LLC"))
        checks.append(("ERCOT: real POI captured with kV", "Big Country 138 kV" in rec.poi_substation))
        checks.append(("ERCOT: county title-cased", rec.county == "Ward"))
    checks.append((
        "ERCOT: 'Inactive Projects' sheet excluded by name despite a qualifying capacity (23INR9001)",
        "23INR9001" not in by_id,
    ))
    checks.append((
        "ERCOT: header found past ~30 junk rows + sparse rows skipped",
        result.stats["ERCOT-GIS"].rows_fetched == 7,
    ))
    checks.append((
        "ERCOT: non-data 'Summary' sheet safely skipped, not misparsed",
        result.stats["ERCOT-GIS"].fetch_errors == [],
    ))
    checks.append((
        "ERCOT large-load: no URL configured -> graceful None, not an exception",
        "ERCOT-LargeLoad" in result.stats and result.stats["ERCOT-LargeLoad"].rows_fetched == 0
        and result.stats["ERCOT-LargeLoad"].fetch_errors == [],
    ))

    ok = True
    for name, passed in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        ok = ok and passed

    out_path = Path("/tmp/selftest_registry.csv")
    write_output_csv(result.records, out_path)
    written_back = pd.read_csv(out_path)
    checks_csv_roundtrip = list(written_back.columns) == OUTPUT_COLUMNS and len(written_back) == len(result.records)
    print(f"  [{'PASS' if checks_csv_roundtrip else 'FAIL'}] CSV round-trips with correct columns/row count")
    ok = ok and checks_csv_roundtrip

    ext_path = Path("/tmp/selftest_registry_extended.csv")
    write_output_csv(result.records, ext_path, include_extra_fields=True)
    written_ext = pd.read_csv(ext_path)
    checks_extended = list(written_ext.columns) == EXTENDED_OUTPUT_COLUMNS
    if "AF2-045" in by_id:
        row = written_ext[written_ext["queue_id"] == "AF2-045"].iloc[0]
        checks_extended = checks_extended and row["status"] == "Active" and row["project_name"] == "Alpha Compute Campus"
        checks_extended = checks_extended and row["raw_fuel_technology"] == "Storage"
    print(f"  [{'PASS' if checks_extended else 'FAIL'}] --include-raw-fields adds status/project_name correctly")
    ok = ok and checks_extended

    print(f"\n{'ALL CHECKS PASSED' if ok else 'SOME CHECKS FAILED'} "
          f"({sum(1 for _, p in checks if p) + int(checks_csv_roundtrip) + int(checks_extended)}"
          f"/{len(checks) + 2})")
    return ok


# --------------------------------------------------------------------------
# CLI entry point
# --------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract, normalize, and filter PJM + ERCOT interconnection "
                     "queues for large (>=100MW) load-class projects.",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("megawatt_interconnect_registry_raw.csv"),
        help="Output CSV path (default: %(default)s)",
    )
    parser.add_argument("--min-mw", type=float, default=MIN_CAPACITY_MW,
                         help="Minimum requested capacity in MW (default: %(default)s)")
    parser.add_argument("--include-raw-fields", action="store_true",
                         help="Also write 'status' and 'project_name' columns (not part of "
                              "the base schema) for downstream tooling. Off by default so "
                              "the output stays exactly the 8 specified columns.")
    parser.add_argument("--pjm-export-key", type=str, default=PJM_QUEUE_EXPORT_DEFAULT_KEY,
                         help="Override PJM's public queue-export subscription key "
                              "if PJM has rotated it (see module docstring).")
    parser.add_argument("--pjm-dataminer-feed", type=str, default=None,
                         help="Optional Data Miner 2 feed name to query directly "
                              "(requires --pjm-api-key too). Not used by default; "
                              "see module docstring for why.")
    parser.add_argument("--pjm-api-key", type=str, default=None,
                         help="PJM Data Miner 2 API key (or set PJM_API_KEY env var).")
    parser.add_argument("--ercot-large-load-url", type=str, default=None,
                         help="URL of a per-project ERCOT large-load register, if one "
                              "exists at the time you run this (see module docstring).")
    parser.add_argument("--pjm-file", type=Path, default=None,
                         help="Path to a local PJM queue export (.xlsx) to parse instead of "
                              "fetching it live -- same parser either way, just skips the HTTP call.")
    parser.add_argument("--ercot-file", type=Path, default=None,
                         help="Path to a local ERCOT GIS Report workbook (.xlsx) to parse "
                              "instead of fetching it live -- same parser either way, just "
                              "skips the HTTP call.")
    parser.add_argument("--source-health-output", type=Path, default=None,
                         help="Optional JSON source-health manifest for guard reconciliation; "
                              "not part of the public registry schema.")
    parser.add_argument("--log-level", type=str, default="INFO",
                         choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--selftest", action="store_true",
                         help="Run against synthetic fixtures instead of live endpoints "
                              "and report pass/fail for each behavior, then exit.")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)

    if args.selftest:
        ok = run_selftest()
        return 0 if ok else 1

    configure_logging(args.log_level)

    global MIN_CAPACITY_MW  # noqa: PLW0603 - simplest way to make the CLI flag effective
    MIN_CAPACITY_MW = args.min_mw

    pjm_api_key = args.pjm_api_key or os.environ.get("PJM_API_KEY")

    fixture_bytes: dict[str, bytes] = {}
    for flag_name, key, path in (
        ("--pjm-file", "pjm", args.pjm_file),
        ("--ercot-file", "ercot_gis", args.ercot_file),
    ):
        if path is None:
            continue
        if not path.exists():
            logger.error("%s path does not exist: %s", flag_name, path)
            return 1
        fixture_bytes[key] = path.read_bytes()
        logger.info("Using local file for %s: %s (%d bytes)", key, path, len(fixture_bytes[key]))

    logger.info("Starting grid interconnection queue ingestion")
    logger.info("Filters: capacity >= %.1f MW | statuses=%s", MIN_CAPACITY_MW, STATUS_CANONICAL)

    result = run_pipeline(
        pjm_export_key=args.pjm_export_key,
        pjm_dataminer_feed=args.pjm_dataminer_feed,
        pjm_api_key=pjm_api_key,
        ercot_large_load_url=args.ercot_large_load_url,
        fixture_bytes=fixture_bytes or None,
    )

    write_output_csv(result.records, args.output, include_extra_fields=args.include_raw_fields)
    if args.source_health_output:
        write_source_health(result, args.source_health_output)
    log_run_summary(result, args.output)

    any_source_succeeded = any(s.rows_fetched > 0 for s in result.stats.values())
    if not any_source_succeeded:
        logger.error("Every source failed to return data -- see errors above.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
