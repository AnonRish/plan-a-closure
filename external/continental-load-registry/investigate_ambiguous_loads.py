#!/usr/bin/env python3
"""
investigate_ambiguous_loads.py
==============================

Turns the registry's "genuinely ambiguous" large loads into an investigative
worklist (ambiguous_facilities_dossier.md): for each facility, where the public
record for it is most likely to live.

WHAT IT DOES
------------
1. Loads the registry (see INPUTS) and keeps every record where
       capacity_mw    >= 100.0
       load_type_tier == "Genuinely Ambiguous / Unclassified Large Load"
       entity_category in ("Developer Not Matched To Known List",
                           "Developer Not Disclosed")
   sorted by capacity_mw, largest first.
2. Builds search leads for each facility -- query text plus a ready-to-click
   search URL -- in three groups: municipal council minutes and zoning /
   development approvals; provincial or state environmental and utility-
   regulator registries; substation / interconnection filings.
3. Applies human-verified identities from ground_truth_overrides.json (a
   verified label plus evidence citations) and marks them in the dossier.

WHAT IT DOES NOT DO
-------------------
It never touches the network and it verifies nothing. A search URL is a lead,
not a finding. "Developer Not Disclosed" is usually a property of what the
source register publishes (SPP, MISO, CAISO, ISO-NE and AESO publish no
applicant), not evidence about the developer. Only an entry in the overrides
file changes how a facility is labelled in the dossier, and overrides never
modify the CSVs or index.html.

INPUTS
------
The registry embedded in index.html (`const REGISTRY_DATA = [...]`, written by
embed_registry_data.py) is the complete nine-RTO registry, so it is the base.
An enriched CSV from compute_anomaly_detector.py replaces the HTML rows of
every RTO it contains -- the same replace-by-RTO rule embed_registry_data.py
uses -- so a freshly generated CSV is honoured before it has been embedded.
The matching raw CSV (ingest_grid_queues.py --include-raw-fields) supplies the
substation, project name, status, projected date and source technology that the
enriched CSV does not carry; it is looked up next to the enriched CSV.

  default enriched CSV : ./computational_load_estimates.csv, else
                         ./data/computational_load_estimates.csv, else none
  default raw CSV      : derived from the enriched CSV's name
                         (computational_load_estimates_X.csv -> registry_raw_X.csv),
                         then registry_raw.csv, then megawatt_interconnect_registry_raw.csv
  default HTML         : ./index.html (use --no-html for CSV-only)

A CSV that covers only some RTOs (a partial refresh) is therefore safe: the
other RTOs still come from index.html and are not silently dropped.

LOCATION FIELDS ARE NOT ALWAYS MUNICIPALITIES
---------------------------------------------
The registry's `county` column means different things by source. For IESO it
holds the IESO electrical zone (Essa, West, Toronto, Southwest, East,
Northeast, ...), a large grid region -- "Essa" is the zone around Essa TS, not
the Township of Essa. For AESO it holds the planning area (a hub named for a
town). Searching a zone as if it were a municipality gives confident-looking
wrong answers, so IESO leads are built from project and developer names only,
and AESO leads use the planning area as a soft hint.

OVERRIDES (ground_truth_overrides.json)
---------------------------------------
    {
      "schema_version": 1,
      "overrides": [
        {
          "rto": "IESO",
          "queue_id": "2026-903",
          "verified_label": "Confirmed Data Center Campus",
          "verified_operator": "Example Operator Inc.",          (optional)
          "confirmed_by": "A. Researcher",
          "confirmed_on": "2026-10-04",
          "evidence": [
            {"citation": "Town of X council minutes, 2026-06-10, item 7.2",
             "url": "https://example.org/minutes.pdf"}           (url optional)
          ],
          "notes": "free text"                                   (optional)
        }
      ]
    }
An override needs at least one evidence citation, a label from ALLOWED_LABELS,
and an rto + queue_id pair (queue_id is matched as text; leading zeros do not
matter for all-digit IDs). Anything malformed stops the run with exit code 2
and a list of every problem, instead of quietly producing an unverified
dossier. Overrides that match nothing in the registry are listed in the
dossier's audit section.

USAGE
-----
    python investigate_ambiguous_loads.py
    python investigate_ambiguous_loads.py --input data/computational_load_estimates_new5.csv
    python investigate_ambiguous_loads.py --rto PJM,ERCOT,SPP,IESO   # the original four sources
    python investigate_ambiguous_loads.py --top 25 --engine bing --json leads.json
    python investigate_ambiguous_loads.py --selftest

EXIT CODES
----------
0 dossier written (or self-test passed) | 1 input problem or self-test failure
| 2 invalid overrides file
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, quote_plus, urlparse

# --------------------------------------------------------------------------
# The filter, exactly as specified
# --------------------------------------------------------------------------

MIN_CAPACITY_MW = 100.0
AMBIGUOUS_TIER = "Genuinely Ambiguous / Unclassified Large Load"
TARGET_ENTITY_CATEGORIES = (
    "Developer Not Matched To Known List",
    "Developer Not Disclosed",
)

KNOWN_RTOS = ("PJM", "ERCOT", "SPP", "MISO", "CAISO", "NYISO", "ISO-NE", "IESO", "AESO")

# Domains used for `site:` searches of each operator's own documents.
RTO_SITE = {
    "PJM": "pjm.com", "ERCOT": "ercot.com", "SPP": "spp.org", "MISO": "misoenergy.org",
    "CAISO": "caiso.com", "NYISO": "nyiso.com", "ISO-NE": "iso-ne.com",
    "IESO": "ieso.ca", "AESO": "aeso.ca",
}

# Entry points taken from the repo's own docs/log messages (SOURCES.md and
# ingest_grid_queues.py) where a stable page is known; otherwise the home page.
RTO_PORTALS = {
    "PJM": "https://www.pjm.com/",
    "ERCOT": "https://www.ercot.com/services/rq/large-load-integration",
    "SPP": "https://opsportal.spp.org/Studies/GIActive",
    "MISO": "https://www.misoenergy.org/",
    "CAISO": "https://www.caiso.com/",
    "NYISO": "https://www.nyiso.com/",
    "ISO-NE": "https://irtt.iso-ne.com/reports/external",
    "IESO": "https://www.ieso.ca/Sector-Participants/Connection-Process/Application-Status",
    "AESO": "https://www.aeso.ca/",
}

ALLOWED_LABELS = (
    "Confirmed Data Center Campus",
    "Confirmed Industrial Park / Manufacturing",
    "Confirmed Utility / Distribution Load Growth",
    "Confirmed Cryptocurrency Mining",
    "Confirmed Other Large Load",
    "Ruled Out (Duplicate / Withdrawn / Data Error)",
)

ENGINES = {
    "google": "https://www.google.com/search?q={q}",
    "bing": "https://www.bing.com/search?q={q}",
    "duckduckgo": "https://duckduckgo.com/?q={q}",
}

FERC_ELIBRARY = "https://elibrary.ferc.gov/"


class DataError(Exception):
    """Registry input missing or malformed (exit code 1)."""


class OverrideError(Exception):
    """ground_truth_overrides.json is invalid (exit code 2)."""

    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


# --------------------------------------------------------------------------
# Text helpers
# --------------------------------------------------------------------------

_PLACEHOLDER_VALUES = {"", "UNKNOWN", "N/A", "NA", "NAN", "NONE", "NULL", "TBD", "-"}


def clean(value: Any) -> str:
    """Text with NBSPs and runs of whitespace collapsed; None / NaN -> ''."""
    if value is None:
        return ""
    if isinstance(value, float) and value != value:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\u00a0", " ")).strip()


def is_placeholder(value: Any) -> bool:
    """True for blanks, 'UNKNOWN', and the registry's 'NOT PUBLISHED ...' sentinels."""
    text = clean(value).upper()
    return text in _PLACEHOLDER_VALUES or text.startswith("NOT PUBLISHED")


def usable(value: Any) -> str:
    """Cleaned text, or '' when the value is blank or a placeholder."""
    text = clean(value)
    return "" if is_placeholder(text) else text


_RTO_ALIASES = {"ISONE": "ISO-NE", "ISO NE": "ISO-NE", "ISO-NEW ENGLAND": "ISO-NE"}


def normalize_rto(value: Any) -> str:
    text = clean(value).upper()
    return _RTO_ALIASES.get(text, text)


def normalize_id(value: Any) -> str:
    """Queue IDs are compared as text; all-digit IDs ignore leading zeros
    (NYISO has both '0979' and '1743', and a researcher may type 979)."""
    text = clean(value).upper()
    return (text.lstrip("0") or "0") if text.isdigit() else text


def parse_mw(value: Any) -> Optional[float]:
    text = clean(value).replace(",", "")
    if not text:
        return None
    try:
        mw = float(text)
    except ValueError:
        return None
    return mw if mw == mw and abs(mw) != float("inf") else None


def truncate_words(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0] or text[:max_chars]
    return cut.rstrip(" ,;:-")


def phrase(text: Any, max_chars: int = 80) -> str:
    """One quoted search phrase, or '' if nothing is usable. Inner double quotes
    are dropped (they would unbalance the query); long text is cut at a word."""
    t = re.sub(r"\s+", " ", clean(text).replace('"', " ")).strip()
    t = truncate_words(t, max_chars)
    return f'"{t}"' if t else ""


def any_of(*terms: str) -> str:
    """('multi word' OR single) -- terms with spaces or punctuation are quoted."""
    parts = []
    for term in terms:
        t = re.sub(r"\s+", " ", clean(term).replace('"', " ")).strip()
        if t:
            parts.append(f'"{t}"' if re.search(r"[\s#'/&.-]", t) else t)
    if not parts:
        return ""
    return parts[0] if len(parts) == 1 else "(" + " OR ".join(parts) + ")"


def join_query(*parts: str) -> str:
    return " ".join(p for p in parts if p)


# Search engines silently ignore words past a limit (Google documents 32), so a
# query that grows too long loses its *last* terms without any warning. Optional
# terms are therefore added only while the query stays under this budget.
MAX_QUERY_WORDS = 30


def query_words(query: str) -> int:
    return len(re.findall(r"[^\s()\"]+", query))


def compose(required: list[str], optional: list[str], max_words: int = MAX_QUERY_WORDS) -> str:
    """Join the required parts, then add each optional part that still fits."""
    query = join_query(*required)
    for part in optional:
        if part and query_words(join_query(query, part)) <= max_words:
            query = join_query(query, part)
    return query


def search_url(query: str, engine: str = "google") -> str:
    return ENGINES[engine].format(q=quote_plus(query))


_CORP_SUFFIX_RE = re.compile(
    r"[,\s]+(?:INC|LLC|L\.L\.C|LTD|LIMITED|CORP|CORPORATION|CO|COMPANY|LP|L\.P|LLP|ULC)\.?$",
    re.I,
)


def strip_corporate_suffix(name: str) -> str:
    """'Greenidge Generation, LLC' -> 'Greenidge Generation' (documents rarely
    repeat the legal suffix exactly). Never returns an empty string."""
    text = clean(name)
    for _ in range(2):
        shorter = _CORP_SUFFIX_RE.sub("", text).rstrip(" ,")
        if not shorter or shorter == text:
            break
        text = shorter
    return text


_PROJ_TAIL_RES = (
    re.compile(r"(?:\s+[-\u2013\u2014:]\s*|\s+)\(?Phase\s+[0-9A-Za-z.]+\)?$", re.I),
    re.compile(r"(?:\s+[-\u2013\u2014:]\s*|\s+)(?:MPC\s+)?Load(?:\s+Increase)?$", re.I),
)


def core_project_name(name: str) -> str:
    """Drop register jargon that will not appear in local documents:
    'Newell Data Center MPC Load' -> 'Newell Data Center',
    'GLDC Load Phase 1.1' -> 'GLDC'. Never returns an empty string."""
    text = clean(name)
    previous = None
    while previous != text:
        previous = text
        for rx in _PROJ_TAIL_RES:
            shorter = rx.sub("", text).strip(" -\u2013\u2014:,")
            if shorter:
                text = shorter
    return text


_TO_RE = re.compile(r"Transmission Owner:\s*([^)]+)\)", re.I)
_TO_CODE_RE = re.compile(r"^(?P<name>.*?\b(?i:INC\.?|LLC|COMPANY|CORPORATION|CORP\.?|CO\.?|LP|L\.P\.))\s+[A-Z]{2,6}$")


def transmission_owner(poi: str, explicit: str = "") -> str:
    """The transmission owner, from the enriched CSV's column or from the
    '(Transmission Owner: X)' text the PJM/MISO adapters put in the POI
    sentinel. MISO's trailing internal code is dropped ('ENTERGY TEXAS, INC.
    ETTO' -> 'ENTERGY TEXAS, INC.')."""
    name = usable(explicit)
    if not name:
        m = _TO_RE.search(clean(poi))
        name = clean(m.group(1)) if m else ""
    m = _TO_CODE_RE.match(name)
    if m:
        name = m.group("name")
    return name.rstrip(", ").strip()


def poi_phrase(poi: str) -> str:
    text = usable(poi)
    if not text:
        return ""
    text = re.sub(r"(?<=\w)\?(?=\w)", " ", text)  # a lost en dash in some source files
    return phrase(text, 70)


def fmt_mw(mw: Optional[float]) -> str:
    if mw is None:
        return "?"
    return f"{mw:,.0f}" if float(mw).is_integer() else f"{mw:,.1f}"


# --------------------------------------------------------------------------
# Jurisdictions: vocabulary and agency hints
# --------------------------------------------------------------------------

STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan",
    "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota",
    "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee",
    "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
    "AB": "Alberta", "BC": "British Columbia", "MB": "Manitoba", "NB": "New Brunswick",
    "NL": "Newfoundland and Labrador", "NS": "Nova Scotia", "ON": "Ontario",
    "PE": "Prince Edward Island", "QC": "Quebec", "SK": "Saskatchewan",
}
_CANADIAN = {"AB", "BC", "MB", "NB", "NL", "NS", "ON", "PE", "QC", "SK"}
_UNIT = {"LA": "Parish", "AK": "Borough"}

TOPIC_US = any_of("data center", "large load")
TOPIC_CA = any_of("data centre", "data center")

# Local vocabulary differs by jurisdiction (an Ontario rezoning is a "zoning
# by-law amendment"; an Alberta one is a "redesignation"), so the queries use
# the terms that jurisdiction's documents actually contain.
_VOCAB = {
    "*US": {
        "bodies": any_of("planning commission", "county commissioners", "board of supervisors", "city council"),
        "zoning": any_of("rezoning", "conditional use permit", "special use permit", "site plan"),
        "env_terms": any_of("air permit", "construction permit", "environmental assessment"),
        "reg_terms": any_of("certificate of public convenience", "siting", "large load"),
    },
    "*CA": {
        "bodies": any_of("council", "planning committee", "committee of the whole"),
        "zoning": any_of("zoning by-law amendment", "official plan amendment", "site plan", "development permit"),
        "env_terms": any_of("environmental assessment", "approval"),
        "reg_terms": any_of("application", "leave to construct", "substation"),
    },
    "ON": {
        "zoning": any_of("zoning by-law amendment", "official plan amendment", "site plan", "minister's zoning order"),
        "env_terms": any_of("Environmental Compliance Approval", "environmental assessment"),
        "reg_terms": any_of("leave to construct", "section 92", "application"),
    },
    "AB": {
        "bodies": any_of("council", "municipal planning commission", "development authority"),
        "zoning": any_of("development permit", "land use bylaw", "redesignation", "area structure plan"),
        "env_terms": any_of("EPEA", "environmental impact assessment", "approval"),
        "reg_terms": any_of("application", "power plant", "substation", "needs identification"),
    },
    "NY": {
        "bodies": any_of("planning board", "town board", "zoning board of appeals", "county legislature"),
        "zoning": any_of("site plan", "special use permit", "rezoning", "IDA", "PILOT"),
        "env_terms": any_of("SEQRA", "environmental notice bulletin", "air permit"),
        "reg_terms": any_of("siting", "large load", "Article VII", "petition"),
    },
}

# state/province -> (environmental agency names, env site hint,
#                    utility regulator names, regulator site hint).
# The site hints are search restrictions, not authorities: a wrong hint yields
# an empty search, never a wrong answer. States without a confident hint use
# the agency names alone, and states missing from this table fall back to
# generic wording.
_AGENCIES: dict[str, tuple[tuple[str, ...], str, tuple[str, ...], str]] = {
    "ON": (("Environmental Registry of Ontario",), "ero.ontario.ca", ("Ontario Energy Board",), "oeb.ca"),
    "AB": (("Alberta Environment and Protected Areas",), "", ("Alberta Utilities Commission", "AUC"), "auc.ab.ca"),
    "NY": (("NYSDEC", "New York State Department of Environmental Conservation"), "dec.ny.gov",
           ("New York Public Service Commission", "NY DPS"), "dps.ny.gov"),
    "PA": (("Pennsylvania Department of Environmental Protection", "PA DEP"), "dep.pa.gov",
           ("Pennsylvania Public Utility Commission",), "puc.pa.gov"),
    "TX": (("TCEQ", "Texas Commission on Environmental Quality"), "tceq.texas.gov",
           ("Public Utility Commission of Texas", "PUCT"), "puc.texas.gov"),
    "OK": (("Oklahoma Department of Environmental Quality", "Oklahoma DEQ"), "",
           ("Oklahoma Corporation Commission",), ""),
    "MI": (("EGLE", "Michigan Department of Environment, Great Lakes, and Energy"), "",
           ("Michigan Public Service Commission", "MPSC"), ""),
    "MO": (("Missouri Department of Natural Resources",), "dnr.mo.gov",
           ("Missouri Public Service Commission",), "psc.mo.gov"),
    "MN": (("Minnesota Pollution Control Agency", "MPCA"), "", ("Minnesota Public Utilities Commission",), ""),
    "AR": (("Arkansas Division of Environmental Quality", "ADEQ"), "", ("Arkansas Public Service Commission",), ""),
    "IL": (("Illinois EPA", "Illinois Environmental Protection Agency"), "epa.illinois.gov",
           ("Illinois Commerce Commission",), "icc.illinois.gov"),
    "LA": (("Louisiana Department of Environmental Quality", "LDEQ"), "deq.louisiana.gov",
           ("Louisiana Public Service Commission",), "lpsc.louisiana.gov"),
    "NE": (("Nebraska Department of Environment and Energy", "NDEE"), "dee.ne.gov",
           ("Nebraska Power Review Board",), ""),
    "SD": (("South Dakota Department of Agriculture and Natural Resources", "DANR"), "danr.sd.gov",
           ("South Dakota Public Utilities Commission",), "puc.sd.gov"),
    "IN": (("IDEM", "Indiana Department of Environmental Management"), "",
           ("Indiana Utility Regulatory Commission", "IURC"), ""),
    "WI": (("Wisconsin Department of Natural Resources",), "dnr.wisconsin.gov",
           ("Public Service Commission of Wisconsin",), "psc.wi.gov"),
    "VA": (("Virginia Department of Environmental Quality", "Virginia DEQ"), "deq.virginia.gov",
           ("Virginia State Corporation Commission",), "scc.virginia.gov"),
    "OH": (("Ohio EPA",), "epa.ohio.gov", ("Ohio Power Siting Board", "PUCO"), "opsb.ohio.gov"),
    "MD": (("Maryland Department of the Environment", "MDE"), "mde.maryland.gov",
           ("Maryland Public Service Commission",), "psc.state.md.us"),
    "NJ": (("NJDEP", "New Jersey Department of Environmental Protection"), "",
           ("New Jersey Board of Public Utilities", "NJBPU"), ""),
    "KS": (("KDHE", "Kansas Department of Health and Environment"), "kdhe.ks.gov",
           ("Kansas Corporation Commission",), "kcc.ks.gov"),
    "IA": (("Iowa Department of Natural Resources",), "iowadnr.gov",
           ("Iowa Utilities Commission", "Iowa Utilities Board"), ""),
    "ND": (("North Dakota Department of Environmental Quality",), "",
           ("North Dakota Public Service Commission",), "psc.nd.gov"),
    "MS": (("Mississippi Department of Environmental Quality", "MDEQ"), "mdeq.ms.gov",
           ("Mississippi Public Service Commission",), "psc.ms.gov"),
    "KY": (("Kentucky Energy and Environment Cabinet",), "", ("Kentucky Public Service Commission",), "psc.ky.gov"),
    "WV": (("West Virginia Department of Environmental Protection", "WVDEP"), "dep.wv.gov",
           ("West Virginia Public Service Commission",), ""),
    "NC": (("North Carolina Department of Environmental Quality", "NCDEQ"), "deq.nc.gov",
           ("North Carolina Utilities Commission",), "ncuc.gov"),
    "DE": (("DNREC", "Delaware Department of Natural Resources and Environmental Control"), "dnrec.delaware.gov",
           ("Delaware Public Service Commission",), ""),
    "CA": (("California Environmental Quality Act", "CEQA"), "",
           ("California Public Utilities Commission", "CPUC", "California Energy Commission"), ""),
    "CT": (("CT DEEP", "Connecticut Department of Energy and Environmental Protection"), "",
           ("Connecticut Siting Council", "PURA"), ""),
    "MA": (("MassDEP",), "", ("Massachusetts Energy Facilities Siting Board", "EFSB"), ""),
    "ME": (("Maine Department of Environmental Protection",), "", ("Maine Public Utilities Commission",), ""),
    "NH": (("NHDES",), "des.nh.gov", ("New Hampshire Site Evaluation Committee",), "nhsec.nh.gov"),
    "VT": (("Vermont Agency of Natural Resources",), "anr.vermont.gov",
           ("Vermont Public Utility Commission",), "puc.vermont.gov"),
    "RI": (("Rhode Island Department of Environmental Management",), "dem.ri.gov",
           ("Rhode Island Public Utilities Commission",), "ripuc.ri.gov"),
}


@dataclass(frozen=True)
class Jurisdiction:
    code: str
    name: str
    country: str          # "US" | "CA"
    unit: str             # county-equivalent word ("" for Canada)
    bodies: str           # OR-group: governing bodies whose minutes to search
    zoning: str           # OR-group: local land-use approvals
    env_names: tuple[str, ...]
    env_site: str
    env_terms: str
    reg_names: tuple[str, ...]
    reg_site: str
    reg_terms: str


def jurisdiction_for(state: str) -> Jurisdiction:
    """Vocabulary and agency hints for a state/province code. Unknown codes get
    generic US wording and use the code itself as the name (no exception)."""
    code = clean(state).upper()
    canadian = code in _CANADIAN
    vocab = dict(_VOCAB["*CA" if canadian else "*US"])
    vocab.update(_VOCAB.get(code, {}))
    env_names, env_site, reg_names, reg_site = _AGENCIES.get(code, ((), "", (), ""))
    return Jurisdiction(
        code=code, name=STATE_NAMES.get(code, code), country="CA" if canadian else "US",
        unit="" if canadian else _UNIT.get(code, "County"),
        bodies=vocab["bodies"], zoning=vocab["zoning"],
        env_names=env_names, env_site=env_site, env_terms=vocab["env_terms"],
        reg_names=reg_names, reg_site=reg_site, reg_terms=vocab["reg_terms"],
    )


# --------------------------------------------------------------------------
# Records and loading
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Facility:
    rto: str
    queue_id: str
    state: str
    county: str
    capacity_mw: Optional[float]
    entity_category: str
    tier: str
    developer: str = ""
    project_name: str = ""
    poi: str = ""
    status: str = ""
    technology: str = ""
    projected_date: str = ""
    transmission_owner: str = ""
    source: str = ""

    @property
    def key(self) -> tuple[str, str]:
        return (self.rto, normalize_id(self.queue_id))


@dataclass
class SourceInfo:
    label: str
    kind: str            # "html" | "csv"
    rows: int
    rtos: tuple[str, ...]
    note: str = ""


_HTML_DATA_RE = re.compile(r"const REGISTRY_DATA = (\[.*?\]);\n", re.S)
_ENRICHED_REQUIRED = ("queue_id", "rto_region", "state", "county", "capacity_mw",
                      "entity_category", "load_type_tier")


def _rtos(facilities: list[Facility]) -> tuple[str, ...]:
    return tuple(sorted({f.rto for f in facilities}))


def load_html_registry(path: Path) -> list[Facility]:
    """The registry embedded in index.html (`const REGISTRY_DATA = [...]`)."""
    text = path.read_text(encoding="utf-8")
    m = _HTML_DATA_RE.search(text)
    if not m:
        raise DataError(f"no 'const REGISTRY_DATA = [...];' found in {path}")
    try:
        rows = json.loads(m.group(1))
    except json.JSONDecodeError as exc:
        raise DataError(f"REGISTRY_DATA in {path} is not valid JSON: {exc}") from exc
    return [
        Facility(
            rto=normalize_rto(r.get("rto")), queue_id=clean(r.get("id")),
            state=clean(r.get("st")).upper(), county=clean(r.get("co")),
            capacity_mw=parse_mw(r.get("mw")), entity_category=clean(r.get("ent")),
            tier=clean(r.get("tier")), developer=clean(r.get("dev")),
            project_name=clean(r.get("proj")), poi=clean(r.get("poi")),
            status=clean(r.get("status")), source=path.name,
        )
        for r in rows
    ]


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def load_raw_index(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    """Raw registry CSV (ingest_grid_queues.py --include-raw-fields) keyed by (rto, id)."""
    fields, rows = _read_csv(path)
    missing = [c for c in ("queue_id", "rto_region") if c not in fields]
    if missing:
        raise DataError(f"{path}: missing required column(s) {missing}")
    return {(normalize_rto(r["rto_region"]), normalize_id(r["queue_id"])): r for r in rows}


def load_enriched_csv(path: Path, raw_path: Optional[Path] = None) -> tuple[list[Facility], int]:
    """Enriched CSV from compute_anomaly_detector.py, joined to the raw CSV when
    one is available. Returns (facilities, rows with no raw match)."""
    fields, rows = _read_csv(path)
    missing = [c for c in _ENRICHED_REQUIRED if c not in fields]
    if missing:
        raise DataError(f"{path}: missing required column(s) {missing}")
    raw = load_raw_index(raw_path) if raw_path is not None else {}
    out: list[Facility] = []
    unmatched = 0
    for r in rows:
        key = (normalize_rto(r["rto_region"]), normalize_id(r["queue_id"]))
        extra = raw.get(key)
        if raw_path is not None and extra is None:
            unmatched += 1
        extra = extra or {}
        poi = clean(extra.get("poi_substation"))
        out.append(Facility(
            rto=key[0], queue_id=clean(r["queue_id"]), state=clean(r["state"]).upper(),
            county=clean(r["county"]), capacity_mw=parse_mw(r["capacity_mw"]),
            entity_category=clean(r["entity_category"]), tier=clean(r["load_type_tier"]),
            developer=clean(r.get("developer_entity_raw")) or clean(extra.get("developer_entity")),
            project_name=clean(extra.get("project_name")), poi=poi,
            status=clean(extra.get("status")), technology=clean(extra.get("raw_fuel_technology")),
            projected_date=clean(extra.get("projected_date")),
            transmission_owner=transmission_owner(poi, r.get("transmission_owner", "")),
            source=path.name,
        ))
    return out, unmatched


_DEFAULT_INPUTS = (Path("computational_load_estimates.csv"), Path("data") / "computational_load_estimates.csv")


def derive_raw_path(input_csv: Path) -> Optional[Path]:
    """Find the raw CSV that goes with an enriched CSV."""
    d = input_csv.parent
    candidates = [
        d / input_csv.name.replace("computational_load_estimates", "registry_raw"),
        d / "registry_raw.csv",
        d / "megawatt_interconnect_registry_raw.csv",
    ]
    return next((c for c in candidates if c != input_csv and c.exists()), None)


def load_registry(
    input_csv: Optional[Path] = None, raw_csv: Optional[Path] = None,
    html: Optional[Path] = None, use_html: bool = True,
) -> tuple[list[Facility], list[SourceInfo]]:
    """Base = index.html registry; an enriched CSV replaces the rows of every
    RTO it contains (the replace-by-RTO rule embed_registry_data.py uses)."""
    sources: list[SourceInfo] = []
    base: list[Facility] = []
    html_path: Optional[Path] = None
    if use_html:
        if html is not None:
            if not html.exists():
                raise DataError(f"--html file not found: {html}")
            html_path = html
        elif Path("index.html").exists():
            html_path = Path("index.html")
    if html_path is not None:
        base = load_html_registry(html_path)
        sources.append(SourceInfo(str(html_path), "html", len(base), _rtos(base)))

    if input_csv is not None and not input_csv.exists():
        raise DataError(f"--input file not found: {input_csv}")
    if raw_csv is not None and not raw_csv.exists():
        raise DataError(f"--raw file not found: {raw_csv}")
    csv_path = input_csv or next((p for p in _DEFAULT_INPUTS if p.exists()), None)

    records = base
    if csv_path is not None:
        raw_path = raw_csv if raw_csv is not None else derive_raw_path(csv_path)
        enriched, unmatched = load_enriched_csv(csv_path, raw_path)
        replaced = sorted({f.rto for f in enriched})
        dropped = sum(1 for f in base if f.rto in replaced)
        records = [f for f in base if f.rto not in replaced] + enriched
        notes = []
        if replaced and base:
            notes.append(f"replaces {dropped} index.html rows for {', '.join(replaced)}")
        if raw_path is None:
            notes.append("no raw CSV found: substation, project name and status unavailable for these rows")
        elif unmatched:
            notes.append(f"{unmatched} rows have no match in {raw_path.name}")
        sources.append(SourceInfo(str(csv_path), "csv", len(enriched), _rtos(enriched), "; ".join(notes)))
    if not records:
        raise DataError("no registry data found: pass --input <enriched CSV> and/or --html index.html")
    return records, sources


# --------------------------------------------------------------------------
# Filtering
# --------------------------------------------------------------------------

@dataclass
class Funnel:
    """Rows are counted under the first rule they fail, in this order."""
    rows_in: int = 0
    dropped_rto: int = 0
    dropped_tier: int = 0
    capacity_unparseable: int = 0
    dropped_capacity: int = 0
    dropped_entity: int = 0
    selected: int = 0


def filter_ambiguous(
    records: list[Facility], *, min_mw: float = MIN_CAPACITY_MW,
    tier: str = AMBIGUOUS_TIER, categories: tuple[str, ...] = TARGET_ENTITY_CATEGORIES,
    rtos: Optional[set[str]] = None,
) -> tuple[list[Facility], Funnel]:
    """capacity_mw >= min_mw AND tier AND entity_category in categories, sorted by
    capacity_mw descending (ties: RTO, then queue id, so output is deterministic)."""
    tier, wanted = clean(tier), {clean(c) for c in categories}
    funnel = Funnel(rows_in=len(records))
    kept: list[Facility] = []
    for f in records:
        if rtos and f.rto not in rtos:
            funnel.dropped_rto += 1
        elif clean(f.tier) != tier:
            funnel.dropped_tier += 1
        elif f.capacity_mw is None:
            funnel.capacity_unparseable += 1
        elif f.capacity_mw < min_mw:
            funnel.dropped_capacity += 1
        elif clean(f.entity_category) not in wanted:
            funnel.dropped_entity += 1
        else:
            kept.append(f)
    kept.sort(key=lambda f: (-(f.capacity_mw or 0.0), f.rto, f.queue_id))
    funnel.selected = len(kept)
    return kept, funnel


# --------------------------------------------------------------------------
# Ground-truth overrides
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Evidence:
    citation: str
    url: str = ""
    accessed_on: str = ""
    kind: str = ""


@dataclass(frozen=True)
class Override:
    rto: str
    queue_id: str
    label: str
    confirmed_by: str
    confirmed_on: str
    evidence: tuple[Evidence, ...]
    operator: str = ""
    notes: str = ""

    @property
    def key(self) -> tuple[str, str]:
        return (self.rto, normalize_id(self.queue_id))


_TOP_KEYS = {"schema_version", "overrides"}
_OVERRIDE_KEYS = {"rto", "queue_id", "verified_label", "verified_operator", "confirmed_by",
                  "confirmed_on", "evidence", "notes"}
_EVIDENCE_KEYS = {"citation", "url", "accessed_on", "type"}
_LABELS_BY_CASEFOLD = {label.casefold(): label for label in ALLOWED_LABELS}


def _is_iso_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        dt.date.fromisoformat(value.strip())
    except ValueError:
        return False
    return True


def _id_text(value: Any) -> str:
    """queue_id as text. JSON numbers (979, 979.0) are accepted; booleans are not."""
    if isinstance(value, bool):
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return clean(value) if isinstance(value, (str, int)) else ""


def _parse_evidence(value: Any, local: list[str]) -> list[Evidence]:
    if not isinstance(value, list) or not value:
        local.append("evidence must be a non-empty list: an override without a citation is not accepted")
        return []
    out: list[Evidence] = []
    for j, ev in enumerate(value, 1):
        tag = f"evidence[{j}]"
        if not isinstance(ev, dict):
            local.append(f"{tag} must be an object with a 'citation'")
            continue
        for k in ev:
            if k not in _EVIDENCE_KEYS and not str(k).startswith("_"):
                local.append(f"{tag}: unknown key {k!r} (allowed: {', '.join(sorted(_EVIDENCE_KEYS))})")
        citation = clean(ev.get("citation")) if isinstance(ev.get("citation"), str) else ""
        if not citation:
            local.append(f"{tag}: citation is required")
        url = ev.get("url")
        if url not in (None, "") and not (isinstance(url, str) and re.match(r"^https?://\S+$", url.strip())):
            local.append(f"{tag}: url must start with http:// or https://")
            url = ""
        accessed = ev.get("accessed_on")
        if accessed not in (None, "") and not _is_iso_date(accessed):
            local.append(f"{tag}: accessed_on must be an ISO date (YYYY-MM-DD)")
            accessed = ""
        out.append(Evidence(citation=citation, url=clean(url), accessed_on=clean(accessed),
                            kind=clean(ev.get("type"))))
    return out


def parse_overrides(data: Any) -> tuple[dict[tuple[str, str], Override], list[str]]:
    """Validate and index an overrides document. Returns (overrides by key,
    problems); a caller should treat any problem as fatal."""
    if not isinstance(data, dict):
        return {}, ["top level must be a JSON object with an 'overrides' list"]
    problems: list[str] = []
    for k in data:
        if k not in _TOP_KEYS and not str(k).startswith("_"):
            problems.append(f"unknown top-level key {k!r} (allowed: schema_version, overrides; "
                            "keys starting with '_' are ignored)")
    if data.get("schema_version", 1) != 1:
        problems.append(f"unsupported schema_version {data.get('schema_version')!r} (this script reads version 1)")
    items = data.get("overrides", [])
    if not isinstance(items, list):
        return {}, problems + ["'overrides' must be a list"]

    result: dict[tuple[str, str], Override] = {}
    for i, item in enumerate(items, 1):
        where = f"overrides[{i}]"
        if not isinstance(item, dict):
            problems.append(f"{where}: must be an object")
            continue
        rto, qid = normalize_rto(item.get("rto")), _id_text(item.get("queue_id"))
        if rto and qid:
            where = f"overrides[{i}] ({rto} {qid})"
        local: list[str] = []
        for k in item:
            if k not in _OVERRIDE_KEYS and not str(k).startswith("_"):
                local.append(f"unknown key {k!r} (allowed: {', '.join(sorted(_OVERRIDE_KEYS))})")
        if rto not in KNOWN_RTOS:
            local.append(f"rto {item.get('rto')!r} is not one of {', '.join(KNOWN_RTOS)}")
        if not qid:
            local.append("queue_id is required (text or a whole number)")
        label = _LABELS_BY_CASEFOLD.get(clean(item.get("verified_label")).casefold())
        if label is None:
            local.append(f"verified_label {item.get('verified_label')!r} is not allowed; use one of: "
                         + "; ".join(ALLOWED_LABELS))
        confirmed_by = clean(item.get("confirmed_by"))
        if not confirmed_by:
            local.append("confirmed_by is required")
        if not _is_iso_date(item.get("confirmed_on")):
            local.append("confirmed_on must be an ISO date (YYYY-MM-DD)")
        evidence = _parse_evidence(item.get("evidence"), local)
        for k in ("verified_operator", "notes"):
            if item.get(k) is not None and not isinstance(item.get(k), str):
                local.append(f"{k} must be text")
        if local:
            problems.extend(f"{where}: {p}" for p in local)
            continue
        ov = Override(rto=rto, queue_id=qid, label=label, confirmed_by=confirmed_by,
                      confirmed_on=item["confirmed_on"].strip(), evidence=tuple(evidence),
                      operator=clean(item.get("verified_operator")), notes=clean(item.get("notes")))
        if ov.key in result:
            problems.append(f"{where}: duplicate override for {rto} {qid}")
            continue
        result[ov.key] = ov
    return result, problems


def load_overrides(path: Path) -> dict[tuple[str, str], Override]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OverrideError([f"{path}: not valid JSON (line {exc.lineno}, column {exc.colno}): {exc.msg}"]) from exc
    overrides, problems = parse_overrides(data)
    if problems:
        raise OverrideError([f"{path}: {p}" for p in problems])
    return overrides


@dataclass
class OverrideAudit:
    applied: dict[tuple[str, str], Override] = field(default_factory=dict)  # facility is in this dossier's set
    excluded: list[Override] = field(default_factory=list)  # in the registry, but fails this run's filter
    orphans: list[Override] = field(default_factory=list)   # no such (rto, queue_id) in the loaded registry


def audit_overrides(
    overrides: dict[tuple[str, str], Override], all_records: list[Facility], selected: list[Facility],
) -> OverrideAudit:
    loaded = {f.key for f in all_records}
    chosen = {f.key for f in selected}
    audit = OverrideAudit()
    for key, ov in sorted(overrides.items()):
        if key in chosen:
            audit.applied[key] = ov
        elif key in loaded:
            audit.excluded.append(ov)
        else:
            audit.orphans.append(ov)
    return audit


# --------------------------------------------------------------------------
# Search-lead generation
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Lead:
    id: str
    category: str        # "municipal" | "environmental" | "substation"
    label: str
    query: str
    url: str


@dataclass(frozen=True)
class Anchor:
    expr: str                 # query fragment naming the facility
    kind: str                 # "name" (project/developer), "poi" (substation), or "id" (queue ID only)
    terms: tuple[str, ...]    # the phrases behind expr (unquoted)

    @property
    def strong(self) -> bool:
        return self.kind == "name"


def build_anchor(fac: Facility) -> Anchor:
    """What to search for. A project or developer name identifies the facility on
    its own, so location and topic words are left out of the query instead of
    narrowing it. Without a name the substation is used, and without that only
    the queue ID remains -- an operator-internal number that local documents
    never contain, so it is kept out of municipal and environmental queries
    and those lean on place and topic words instead."""
    names: list[str] = []
    for cand in (core_project_name(usable(fac.project_name)), strip_corporate_suffix(usable(fac.developer))):
        if len(cand) >= 3 and cand.casefold() not in {n.casefold() for n in names}:
            names.append(cand)
    if names:
        expr = phrase(names[0], 45) if len(names) == 1 else "(" + " OR ".join(phrase(n, 45) for n in names) + ")"
        return Anchor(expr, "name", tuple(names))
    poi = poi_phrase(fac.poi)
    if poi:
        return Anchor(poi, "poi", (poi.strip('"'),))
    qid = clean(fac.queue_id)
    return Anchor(phrase(qid), "id", (qid,))


def location_kind(fac: Facility) -> str:
    """What the registry's `county` column means for this facility's source."""
    return {"IESO": "zone", "AESO": "planning area"}.get(fac.rto, "county")


def place_terms(fac: Facility, j: Jurisdiction) -> str:
    place = clean(usable(fac.county).replace(";", "."))  # source typo: 'St; Lawrence'
    kind = location_kind(fac)
    if kind == "zone":
        return j.name  # IESO zones are far too coarse to search as places
    if kind == "planning area":
        parts = [p.strip() for p in place.split("/") if p.strip()]
        area = any_of(*parts) if len(parts) > 1 else (phrase(parts[0]) if parts else "")
        return join_query(area, j.name)
    if not place:
        return j.name
    has_unit = re.search(r"\b(county|parish|borough|city|town|township)\b", place, re.I)
    return join_query(phrase(place), "" if has_unit else j.unit, j.name)


def queue_id_variants(rto: str, queue_id: str) -> list[str]:
    """How other documents cite this ID: NYISO 'Q#1743', ISO-NE 'QP 1595'."""
    qid = clean(queue_id)
    if rto == "NYISO" and qid.isdigit():
        return [f"Q#{qid}", f"Q{qid}", f"Queue #{qid}", qid]
    if rto == "ISO-NE" and qid.isdigit():
        return [f"QP {qid}", f"QP{qid}"]
    return [qid]


def build_leads(fac: Facility, engine: str = "google") -> list[Lead]:
    """Up to seven leads: municipal (M1, M2), environmental / regulator (E1, E2),
    substation (S1 POI, S2 the operator's own documents, S3 transmission owner).
    S1 and S3 are omitted when the register publishes no substation / owner."""
    j = jurisdiction_for(fac.state)
    a = build_anchor(fac)
    topic = "" if a.strong else (TOPIC_CA if j.country == "CA" else TOPIC_US)
    where = j.name if a.strong else place_terms(fac, j)   # a strong anchor needs no county
    leads: list[Lead] = []

    def add(lead_id: str, category: str, label: str, query: str) -> None:
        leads.append(Lead(lead_id, category, label, query, search_url(query, engine)))

    def assemble(scope: list[str], anchor: str) -> str:
        """Scope terms + the facility anchor; place and topic words are optional
        extras when an anchor names the facility, and required when none does."""
        if anchor:
            return compose(scope + [anchor], [where, topic])
        return compose(scope + [where, topic], [])

    # Environmental permits do not name substations, so a substation anchor is dropped there.
    env_anchor = a.expr if a.kind == "name" else ""
    local_anchor = a.expr if a.kind in ("name", "poi") else ""

    add("M1", "municipal", "Council / commission minutes", assemble([j.bodies, "minutes"], local_anchor))
    add("M2", "municipal", "Zoning & development applications", assemble([j.zoning], local_anchor))

    if j.env_site:
        add("E1", "environmental", "Environmental registry / permits", assemble([f"site:{j.env_site}"], env_anchor))
    else:
        agency = any_of(*j.env_names) if j.env_names else j.name
        add("E1", "environmental", "Environmental registry / permits", assemble([agency, j.env_terms], env_anchor))
    if j.reg_site:
        add("E2", "environmental", "Utility-commission / siting filings", assemble([f"site:{j.reg_site}"], local_anchor))
    else:
        agency = any_of(*j.reg_names) if j.reg_names else j.name
        add("E2", "environmental", "Utility-commission / siting filings", assemble([agency, j.reg_terms], local_anchor))

    poi = poi_phrase(fac.poi)
    if poi:
        add("S1", "substation", "Substation / point of interconnection",
            compose([poi, any_of("substation", "interconnection", "facilities study", "system impact study")], [j.name]))
    if fac.rto in RTO_SITE:
        exact = truncate_words(usable(fac.project_name), 60)
        add("S2", "substation", "RTO / ISO documents",
            compose([f"site:{RTO_SITE[fac.rto]}",
                     any_of(*(queue_id_variants(fac.rto, fac.queue_id) + ([exact] if exact else [])))], []))
    owner = transmission_owner(fac.poi, fac.transmission_owner)
    if owner:
        add("S3", "substation", "Transmission-owner filings",
            compose([phrase(owner), any_of("large load", "data center", "interconnection", "substation")], [j.name]))
    return leads


# --------------------------------------------------------------------------
# Dossier rendering
# --------------------------------------------------------------------------

_CATEGORY_NAMES = {"municipal": "Municipal", "environmental": "Environmental / regulator",
                   "substation": "Substation"}


def md_cell(value: Any) -> str:
    """Text safe inside a Markdown table cell."""
    return clean(value).replace("|", "\\|").replace("`", "'") or "\u2014"


def short_location(fac: Facility) -> str:
    """State plus the location field, tagged so an IESO zone or AESO planning area
    is not mistaken for a municipality in the ranked summary."""
    place = usable(fac.county)
    suffix = {"zone": " zone", "planning area": " area"}.get(location_kind(fac), "")
    return fac.state + (f" \u00b7 {place}{suffix}" if place else "")


def facility_title(fac: Facility) -> str:
    return usable(fac.project_name) or usable(fac.developer) or "(no project name published)"


def location_description(fac: Facility) -> str:
    place = clean(usable(fac.county).replace(";", "."))
    kind = location_kind(fac)
    state = STATE_NAMES.get(fac.state, fac.state)
    if kind == "zone":
        return (f'IESO electrical zone "{place}" (a grid region, not a municipality)' if place
                else "IESO zone not published")
    if kind == "planning area":
        return (f'AESO planning area "{place}" (a hub named for a town, not a municipality boundary)'
                if place else "AESO planning area not published")
    return f'county field "{place}", {state}' if place else f"county not published, {state}"


def _developer_line(fac: Facility) -> str:
    dev = usable(fac.developer)
    if dev:
        return f"{dev} \u2014 {fac.entity_category}"
    return f"not published by the source register \u2014 {fac.entity_category}"


def render_leads_table(leads: list[Lead]) -> list[str]:
    lines = ["| Lead | Query (click to search) |", "|---|---|"]
    for lead in leads:
        query = lead.query.replace("`", "'").replace("|", "\\|")
        lines.append(f"| {_CATEGORY_NAMES[lead.category]} \u00b7 {lead.label} | [`{query}`]({lead.url}) |")
    return lines


def render_verified(ov: Override) -> list[str]:
    lines = [f"> **VERIFIED \u2014 {ov.label}**",
             f"> Confirmed by {ov.confirmed_by} on {ov.confirmed_on}."]
    if ov.operator:
        lines.append(f"> Operator: {ov.operator}")
    lines.append(">")
    for n, ev in enumerate(ov.evidence, 1):
        cite = ev.citation + (f" \u2014 <{ev.url}>" if ev.url else "") + (f" (accessed {ev.accessed_on})" if ev.accessed_on else "")
        lines.append(f"> {n}. {cite}")
    if ov.notes:
        lines += [">", f"> Notes: {ov.notes}"]
    return lines


def render_facility(rank: int, fac: Facility, leads: list[Lead], ov: Optional[Override]) -> list[str]:
    title = facility_title(fac)
    lines = [f"### {rank}. {fac.rto} {fac.queue_id} \u2014 {title} \u00b7 {fmt_mw(fac.capacity_mw)} MW \u00b7 {fac.state}", ""]
    if ov is not None:
        lines += render_verified(ov) + [""]
    rows = [
        ("Status (as published)", md_cell(fac.status)),
        ("Developer (as published)", md_cell(_developer_line(fac))),
        ("Point of interconnection", md_cell(usable(fac.poi) or "not published by the source register")),
        ("Location field", md_cell(location_description(fac))),
    ]
    owner = transmission_owner(fac.poi, fac.transmission_owner)
    if owner:
        rows.append(("Transmission owner", md_cell(owner)))
    if fac.technology:
        rows.append(("Source technology / end-use", md_cell(fac.technology)))
    if fac.projected_date:
        rows.append(("Projected date", md_cell(fac.projected_date)))
    lines += ["| | |", "|---|---|"] + [f"| {k} | {v} |" for k, v in rows] + [""]
    if ov is not None:
        lines += ["<details><summary>Search leads (facility already verified)</summary>", ""]
        lines += render_leads_table(leads) + ["", "</details>", ""]
    else:
        lines += ["**Search leads** (nothing below has been fetched or verified)", ""]
        lines += render_leads_table(leads) + [""]
    return lines


def _gw(mw: float) -> str:
    return f"{mw / 1000:,.1f}"


def render_portals(selected: list[Facility]) -> list[str]:
    rtos = [r for r in KNOWN_RTOS if any(f.rto == r for f in selected)]
    states = sorted({f.state for f in selected})
    lines = ["## Where the records live", "",
             "Static entry points for the jurisdictions in this dossier. The per-facility queries use `site:` "
             "restrictions only where the domain is confidently known; treat every domain as a search hint.", "",
             "| Operator | Entry point | `site:` used for its documents |", "|---|---|---|"]
    for rto in rtos:
        lines.append(f"| {rto} | <{RTO_PORTALS[rto]}> | `{RTO_SITE[rto]}` |")
    lines += ["", "| State / province | Environmental | Utility regulator / siting |", "|---|---|---|"]
    for st in states:
        j = jurisdiction_for(st)

        def cell(names: tuple[str, ...], site: str) -> str:
            text = "; ".join(md_cell(n) for n in names[:2]) if names else "\u2014"
            return f"{text} (<https://{site}/>)" if site and names else (f"<https://{site}/>" if site else text)

        lines.append(f"| {st} ({j.name}) | {cell(j.env_names, j.env_site)} | {cell(j.reg_names, j.reg_site)} |")
    lines += ["", f"Federal filings: FERC eLibrary <{FERC_ELIBRARY}> (interconnection agreements and "
              "large-load or co-location proceedings).", ""]
    return lines


def render_dossier(
    facilities: list[Facility], selected: list[Facility], funnel: Funnel,
    sources: list[SourceInfo], audit: OverrideAudit, *, engine: str, generated_on: dt.date,
    min_mw: float = MIN_CAPACITY_MW, rtos: Optional[set[str]] = None,
    overrides_path: Optional[str] = None,
) -> str:
    total_mw = sum(f.capacity_mw or 0.0 for f in selected)
    by_rto: dict[str, list[Facility]] = {}
    for f in selected:
        by_rto.setdefault(f.rto, []).append(f)
    verified_mw = sum(f.capacity_mw or 0.0 for f in selected if f.key in audit.applied)

    out: list[str] = [
        "# Ambiguous large-load facilities \u2014 investigative dossier", "",
        f"Generated {generated_on.isoformat()} by `investigate_ambiguous_loads.py`.", "",
        "**Read this first.** This is a worklist of leads, not a set of findings. Nothing here was fetched "
        "or verified: each search URL points at a public search engine, and results still need a human to "
        "read them. The broad ambiguity filter is not a load-classification proof: a candidate must pass the strict source-level load-admission gate before it is treated as a load-discovery case. \"Developer Not Disclosed\" is usually a property of what the source register publishes "
        "(SPP, MISO, CAISO, ISO-NE and AESO publish no applicant), not evidence about the developer. A "
        "facility's label changes only when a researcher records a verified identity with evidence in "
        "`ground_truth_overrides.json`.", "",
        "## Scope", "",
        f"Filter: `capacity_mw >= {min_mw:g}`, `load_type_tier == \"{AMBIGUOUS_TIER}\"`, "
        "`entity_category` in (" + ", ".join(f'"{c}"' for c in TARGET_ENTITY_CATEGORIES) + ")"
        + (f", RTOs limited to {', '.join(sorted(rtos))}" if rtos else "") + ".", "",
        "| Filter step | Rows |", "|---|---:|",
        f"| Registry rows loaded | {funnel.rows_in:,} |",
    ]
    if rtos:
        out.append(f"| Outside the requested RTOs | {funnel.dropped_rto:,} |")
    out += [
        f"| Not in the ambiguous tier | {funnel.dropped_tier:,} |",
        f"| Capacity missing or unreadable | {funnel.capacity_unparseable:,} |",
        f"| Below {min_mw:g} MW | {funnel.dropped_capacity:,} |",
        f"| Developer resolved to a known entity (outside the two categories) | {funnel.dropped_entity:,} |",
        f"| **Facilities in this dossier** | **{funnel.selected:,}** ({_gw(total_mw)} GW) |", "",
        "Data sources:", "",
    ]
    for s in sources:
        note = f" \u2014 {s.note}" if s.note else ""
        out.append(f"- `{s.label}`: {s.rows:,} rows, {', '.join(s.rtos)}{note}")
    out.append("")

    out += ["| RTO | Facilities | GW | Verified |", "|---|---:|---:|---:|"]
    for rto in sorted(by_rto, key=lambda r: -sum(f.capacity_mw or 0.0 for f in by_rto[r])):
        group = by_rto[rto]
        n_ver = sum(1 for f in group if f.key in audit.applied)
        out.append(f"| {rto} | {len(group)} | {_gw(sum(f.capacity_mw or 0.0 for f in group))} | {n_ver} |")
    out.append("")
    if audit.applied:
        by_label: dict[str, int] = {}
        for ov in audit.applied.values():
            by_label[ov.label] = by_label.get(ov.label, 0) + 1
        out.append(f"**Verified: {len(audit.applied)} of {len(selected)}** ({_gw(verified_mw)} GW) \u2014 "
                   + "; ".join(f"{n} \u00d7 {label}" for label, n in sorted(by_label.items())) + ".")
    else:
        out.append(f"**Ground-truth overrides: 0 of {len(selected)}.** This pool is not a set of confirmed discoveries; promote cases only after strict load-admission review. Record confirmed identities in "
                   f"`{overrides_path or 'ground_truth_overrides.json'}` and re-run.")
    out.append("")

    shown = f"Showing the largest {len(facilities)} of {len(selected)}" if len(facilities) < len(selected) else "All facilities"
    out += [f"## Ranked summary", "", f"{shown}, by capacity.", "",
            "| # | RTO | Queue ID | MW | Location | Project / developer | Status | Verified |",
            "|--:|---|---|--:|---|---|---|---|"]
    for rank, f in enumerate(facilities, 1):
        ov = audit.applied.get(f.key)
        title = facility_title(f)
        title = title if len(title) <= 60 else truncate_words(title, 60) + "\u2026"
        out.append(f"| {rank} | {f.rto} | {md_cell(f.queue_id)} | {fmt_mw(f.capacity_mw)} | {md_cell(short_location(f))} | "
                   f"{md_cell(title)} | {md_cell(f.status)} | {md_cell(ov.label) if ov else '\u2014'} |")
    out.append("")
    out += render_portals(selected)
    out += ["## Facility dossiers", ""]
    for rank, f in enumerate(facilities, 1):
        out += render_facility(rank, f, build_leads(f, engine), audit.applied.get(f.key))

    out += ["## Overrides audit", ""]
    if not (audit.applied or audit.excluded or audit.orphans):
        out += ["No overrides were loaded.", ""]
    else:
        out += [f"- Applied to a facility in this dossier: {len(audit.applied)}",
                f"- Match a registry record that this run's filter excludes: {len(audit.excluded)}",
                f"- Match nothing in the loaded registry (check the RTO and queue_id): {len(audit.orphans)}", ""]
        for title, group in (("Excluded by this run's filter", audit.excluded), ("No matching record", audit.orphans)):
            if group:
                out += [f"**{title}:** " + ", ".join(f"{o.rto} {o.queue_id}" for o in group), ""]
    return "\n".join(out).rstrip() + "\n"


def dossier_json(facilities: list[Facility], audit: OverrideAudit, engine: str) -> dict[str, Any]:
    rows = []
    for rank, f in enumerate(facilities, 1):
        ov = audit.applied.get(f.key)
        rows.append({
            "rank": rank, **asdict(f),
            "verified": asdict(ov) if ov is not None else None,
            "leads": [asdict(lead) for lead in build_leads(f, engine)],
        })
    return {"facilities": rows}


# --------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------

DEFAULT_OVERRIDES = Path("ground_truth_overrides.json")


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Build an investigative dossier for the registry's ambiguous large loads: "
                    "public-record search leads per facility, plus human-verified overrides.",
        epilog="See the module docstring (or README) for the overrides schema and input rules.",
    )
    p.add_argument("--input", type=Path, default=None,
                   help="Enriched CSV from compute_anomaly_detector.py (default: "
                        "computational_load_estimates.csv in . or data/, if present)")
    p.add_argument("--raw", type=Path, default=None,
                   help="Raw CSV from ingest_grid_queues.py --include-raw-fields (default: found next "
                        "to --input)")
    p.add_argument("--html", type=Path, default=None,
                   help="index.html holding the embedded registry (default: ./index.html)")
    p.add_argument("--no-html", action="store_true", help="Use the CSV only; do not read index.html")
    p.add_argument("--overrides", type=Path, default=None,
                   help="Overrides JSON (default: ground_truth_overrides.json if it exists)")
    p.add_argument("--output", type=Path, default=Path("ambiguous_facilities_dossier.md"),
                   help="Dossier path (default: %(default)s)")
    p.add_argument("--json", type=Path, default=None, dest="json_out",
                   help="Also write the facilities and leads as JSON")
    p.add_argument("--min-mw", type=float, default=MIN_CAPACITY_MW,
                   help="Minimum capacity in MW (default: %(default)s)")
    p.add_argument("--rto", action="append", default=None,
                   help="Only these RTOs, comma-separated or repeated (e.g. PJM,ERCOT,SPP,IESO for the "
                        "original four sources)")
    p.add_argument("--top", type=int, default=None, help="Only the N largest facilities")
    p.add_argument("--engine", choices=sorted(ENGINES), default="google",
                   help="Search engine for the URLs (default: %(default)s)")
    p.add_argument("--generated-on", type=dt.date.fromisoformat, default=None, help=argparse.SUPPRESS)
    p.add_argument("--selftest", action="store_true",
                   help="Run against synthetic fixtures (no network) and report pass/fail, then exit")
    return p


def _label_counts(values: list[str], limit: int = 8) -> str:
    counts: dict[str, int] = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: -kv[1])[:limit]
    return "; ".join(f"{k!r} x{n}" for k, n in ranked) or "(none)"


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.selftest:
        return 0 if run_selftest() else 1
    if args.top is not None and args.top < 1:
        parser.error("--top must be at least 1")

    rtos: Optional[set[str]] = None
    if args.rto:
        rtos = {normalize_rto(x) for chunk in args.rto for x in chunk.split(",") if x.strip()}
        unknown = sorted(rtos - set(KNOWN_RTOS))
        if unknown:
            print(f"ERROR: unknown RTO(s) {', '.join(unknown)}; known: {', '.join(KNOWN_RTOS)}", file=sys.stderr)
            return 1

    try:
        records, sources = load_registry(args.input, args.raw, args.html, use_html=not args.no_html)
    except DataError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    for s in sources:
        print(f"Loaded {s.rows:,} rows from {s.label} ({', '.join(s.rtos)})" + (f" -- {s.note}" if s.note else ""))

    selected, funnel = filter_ambiguous(records, min_mw=args.min_mw, rtos=rtos)
    if not selected:
        print("ERROR: no record matched the filter. Labels present in the loaded data:", file=sys.stderr)
        print(f"  load_type_tier: {_label_counts([f.tier for f in records])}", file=sys.stderr)
        print(f"  entity_category (ambiguous tier only): "
              f"{_label_counts([f.entity_category for f in records if clean(f.tier) == AMBIGUOUS_TIER])}",
              file=sys.stderr)
        print(f"  expected tier {AMBIGUOUS_TIER!r} and categories {list(TARGET_ENTITY_CATEGORIES)}", file=sys.stderr)
        return 1

    overrides_path = args.overrides
    if overrides_path is None and DEFAULT_OVERRIDES.exists():
        overrides_path = DEFAULT_OVERRIDES
    if overrides_path is not None and not overrides_path.exists():
        print(f"ERROR: --overrides file not found: {overrides_path}", file=sys.stderr)
        return 1
    try:
        overrides = load_overrides(overrides_path) if overrides_path is not None else {}
    except OverrideError as exc:
        print("ERROR: invalid overrides file, nothing written:", file=sys.stderr)
        for problem in exc.problems:
            print(f"  - {problem}", file=sys.stderr)
        return 2
    audit = audit_overrides(overrides, records, selected)

    shown = selected[: args.top] if args.top else selected
    generated_on = args.generated_on or dt.datetime.now(dt.timezone.utc).date()
    text = render_dossier(
        shown, selected, funnel, sources, audit, engine=args.engine, generated_on=generated_on,
        min_mw=args.min_mw, rtos=rtos, overrides_path=str(overrides_path) if overrides_path else None,
    )
    args.output.write_text(text, encoding="utf-8")
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(dossier_json(shown, audit, args.engine), indent=2) + "\n",
                                 encoding="utf-8")

    total_mw = sum(f.capacity_mw or 0.0 for f in selected)
    per_rto: dict[str, int] = {}
    for f in selected:
        per_rto[f.rto] = per_rto.get(f.rto, 0) + 1
    print(f"Matched {len(selected)} facilities ({_gw(total_mw)} GW): "
          + ", ".join(f"{r} {n}" for r, n in sorted(per_rto.items(), key=lambda kv: -kv[1])))
    if funnel.dropped_entity:
        n = funnel.dropped_entity
        print(f"  ({n} ambiguous-tier row{'s' if n != 1 else ''} excluded: developer resolved to a known entity)")
    print(f"Overrides: {len(audit.applied)} applied, {len(audit.excluded)} outside this filter, "
          f"{len(audit.orphans)} matching nothing")
    for o in audit.orphans:
        print(f"  WARNING: override {o.rto} {o.queue_id} matches no record in the loaded registry")
    print(f"Wrote {args.output}" + (f" and {args.json_out}" if args.json_out else "")
          + (f" (top {len(shown)} of {len(selected)})" if len(shown) < len(selected) else ""))
    return 0


# --------------------------------------------------------------------------
# Self-test: synthetic fixtures, no network
# --------------------------------------------------------------------------

class _Checks:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        if ok:
            self.passed += 1
            print(f"  [PASS] {name}")
        else:
            self.failed += 1
            print(f"  [FAIL] {name}" + (f" -- {detail}" if detail else ""))


def _fx(rto: str = "IESO", qid: str = "1", mw: Optional[float] = 100.0, *, tier: str = AMBIGUOUS_TIER,
        ent: str = "Developer Not Disclosed", state: str = "ON", county: str = "", poi: str = "",
        proj: str = "", dev: str = "", status: str = "Under Study", tech: str = "") -> Facility:
    return Facility(rto=rto, queue_id=qid, state=state, county=county, capacity_mw=mw, entity_category=ent,
                    tier=tier, developer=dev, project_name=proj, poi=poi, status=status, technology=tech)


def _html_row(rto: str, qid: str, mw: float, *, tier: str = AMBIGUOUS_TIER, ent: str = "Developer Not Disclosed",
              st: str = "ON", co: str = "", poi: str = "", proj: str = "", dev: str = "") -> dict[str, Any]:
    return {"id": qid, "rto": rto, "st": st, "co": co, "poi": poi, "mw": mw, "status": "Under Study",
            "proj": proj, "dev": dev, "ent": ent, "tier": tier, "gpu": 1, "flops": 1.0, "flag": True}


def _html_text(rows: list[dict[str, Any]]) -> str:
    return ("<html><script>\nconst REGISTRY_DATA = " + json.dumps(rows, separators=(",", ":"))
            + ";\n\nconst FILINGS = [];\n</script></html>")


def _raises(fn: Any, exc: type, needle: str = "") -> bool:
    try:
        fn()
    except exc as e:
        return needle in str(e)
    return False


def _quiet_main(argv: list[str]) -> tuple[int, str, str]:
    import contextlib
    import io
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            rc = main(argv)
        except SystemExit as e:  # argparse errors
            rc = int(e.code or 0)
    return rc, out.getvalue(), err.getvalue()


def _selftest_filtering(c: _Checks) -> None:
    ENT_OK = "Developer Not Matched To Known List"
    rows = [
        _fx("IESO", "at-100", 100.0),
        _fx("IESO", "below", 99.9),
        _fx("MISO", "other-tier", 500.0, tier="Confirmed Grid-Scale Storage (BESS)"),
        _fx("IESO", "colo", 450.0, ent="Wholesale Colocation Developer"),
        _fx("NYISO", "matched-cat", 300.0, ent=ENT_OK),
        _fx("SPP", "no-mw", None),
        _fx("SPP", "padded", 250.0, tier="  Genuinely Ambiguous  /  Unclassified Large Load "),
        _fx("AESO", "big", 1864.0),
    ]
    sel, fn = filter_ambiguous(rows)
    ids = [f.queue_id for f in sel]
    c.check("capacity filter is >= (100.0 kept), 99.9 dropped", "at-100" in ids and "below" not in ids)
    c.check("rows outside the ambiguous tier are dropped", "other-tier" not in ids and fn.dropped_tier == 1)
    c.check("entity_category outside the two allowed values is dropped", "colo" not in ids and fn.dropped_entity == 1)
    c.check("both allowed entity categories are kept", "matched-cat" in ids and "at-100" in ids)
    c.check("unreadable capacity is dropped and counted separately, not a crash",
            "no-mw" not in ids and fn.capacity_unparseable == 1)
    c.check("labels with stray/doubled whitespace still match", "padded" in ids)
    c.check("sorted by capacity_mw descending", ids == ["big", "matched-cat", "padded", "at-100"], str(ids))
    c.check("funnel accounts for every input row",
            fn.rows_in == fn.dropped_rto + fn.dropped_tier + fn.capacity_unparseable + fn.dropped_capacity
            + fn.dropped_entity + fn.selected == len(rows))
    tie = [_fx("SPP", "b", 200.0), _fx("IESO", "z", 200.0), _fx("IESO", "a", 200.0)]
    c.check("capacity ties break by RTO then queue id (deterministic)",
            [f.queue_id for f in filter_ambiguous(tie)[0]] == ["a", "z", "b"])
    sel_r, fn_r = filter_ambiguous(rows, rtos={"IESO", "SPP"})
    c.check("--rto restricts the set and is counted in the funnel",
            {f.rto for f in sel_r} <= {"IESO", "SPP"} and fn_r.dropped_rto == 3, str(fn_r))
    c.check("no matches returns an empty list, not an error", filter_ambiguous([_fx(mw=5.0)])[0] == [])
    c.check("parse_mw handles commas, text, NaN, blanks",
            parse_mw("1,200.5") == 1200.5 and parse_mw("abc") is None and parse_mw("nan") is None
            and parse_mw("") is None and parse_mw(None) is None)


def _selftest_helpers(c: _Checks) -> None:
    c.check("placeholders: sentinels, UNKNOWN and blanks are placeholders; real text is not",
            all(is_placeholder(v) for v in ("NOT PUBLISHED IN AESO CONNECTION PROJECT LIST",
                                            "NOT PUBLISHED BY PJM (Transmission Owner: Dominion)",
                                            "UNKNOWN", "", None, "N/A"))
            and not is_placeholder("Norman Hills 345 kV"))
    c.check("core_project_name drops register jargon (AESO 'MPC Load', 'Load Phase 1.1')",
            core_project_name("Newell Data Center MPC Load") == "Newell Data Center"
            and core_project_name("GLDC Load Phase 1.1") == "GLDC"
            and core_project_name("IBM Markham CTS - Load Increase") == "IBM Markham CTS"
            and core_project_name("EPC/PUC TransCo TS - Phase 1A") == "EPC/PUC TransCo TS")
    c.check("core_project_name leaves real names alone and never returns empty",
            core_project_name("Project IQ197") == "Project IQ197"
            and core_project_name("Mikinak Phase 2 Data Center") == "Mikinak Phase 2 Data Center"
            and core_project_name("Overload") == "Overload" and core_project_name("Load") == "Load")
    c.check("strip_corporate_suffix removes legal suffixes, never empties a name",
            strip_corporate_suffix("197 McKay Barrie Corp") == "197 McKay Barrie"
            and strip_corporate_suffix("N49 Digital Ltd.") == "N49 Digital"
            and strip_corporate_suffix("Greenidge Generation, LLC") == "Greenidge Generation"
            and strip_corporate_suffix("ALECTRA UTILITIES CORPORATION") == "ALECTRA UTILITIES"
            and strip_corporate_suffix("LLC") == "LLC")
    c.check("transmission_owner parses the POI sentinel and drops MISO's trailing code",
            transmission_owner("NOT PUBLISHED BY MISO (Transmission Owner: ENTERGY TEXAS, INC. ETTO)") == "ENTERGY TEXAS, INC."
            and transmission_owner("NOT PUBLISHED BY MISO (Transmission Owner: OTTER TAIL POWER COMPANY OTP)") == "OTTER TAIL POWER COMPANY"
            and transmission_owner("NOT PUBLISHED BY MISO (Transmission Owner: METC)") == "METC"
            and transmission_owner("NOT PUBLISHED BY MISO (Transmission Owner: AMEREN MISSOURI)") == "AMEREN MISSOURI")
    c.check("transmission_owner prefers an explicit value and is empty when there is none",
            transmission_owner("x", "Dominion") == "Dominion" and transmission_owner("Norman Hills 345 kV") == "")
    c.check("normalize_id ignores leading zeros on all-digit IDs only",
            normalize_id("0979") == normalize_id("979") == "979" and normalize_id("p3066") == "P3066"
            and normalize_id("2026-903") == "2026-903")
    c.check("normalize_rto maps aliases", normalize_rto("isone") == "ISO-NE" and normalize_rto(" ieso ") == "IESO")
    c.check("phrase/any_of never emit empty quotes and drop inner double quotes",
            phrase("") == "" and phrase('a "b" c') == '"a b c"' and any_of("", " ") == ""
            and any_of("x", "y z") == '(x OR "y z")')
    c.check("truncate_words cuts at a word boundary", truncate_words("alpha beta gamma", 12) == "alpha beta")
    c.check("fmt_mw drops a needless .0", fmt_mw(1935.0) == "1,935" and fmt_mw(176.6) == "176.6")


def _selftest_leads(c: _Checks) -> None:
    def by_id(f: Facility, engine: str = "google") -> dict[str, Lead]:
        return {lead.id: lead for lead in build_leads(f, engine)}

    def roundtrips(leads: dict[str, Lead]) -> bool:
        return all(parse_qs(urlparse(l.url).query)["q"][0] == l.query for l in leads.values())

    # IESO: county holds an electrical ZONE, not a municipality
    iq = _fx("IESO", "2026-903", 1380.0, ent="Developer Not Matched To Known List", state="ON", county="Essa",
             proj="Project IQ197", dev="197 McKay Barrie Corp")
    L = by_id(iq)
    c.check("IESO leads: M1 M2 E1 E2 S2 (no POI / owner published, so no S1 / S3)", list(L) == ["M1", "M2", "E1", "E2", "S2"], str(list(L)))
    c.check("IESO leads never search the zone name as a place (Essa zone != Township of Essa)",
            not any("essa" in l.query.lower() for l in L.values()))
    c.check("project and developer names anchor the query (legal suffix dropped)",
            '"Project IQ197"' in L["M1"].query and '"197 McKay Barrie"' in L["M1"].query and "Corp" not in L["M1"].query)
    c.check("Ontario vocabulary: council minutes, zoning by-law amendment, ERO, OEB",
            "council" in L["M1"].query and "minutes" in L["M1"].query
            and '"zoning by-law amendment"' in L["M2"].query
            and L["E1"].query.startswith("site:ero.ontario.ca") and L["E2"].query.startswith("site:oeb.ca"))
    c.check("S2 searches the operator's own site for the application ID", L["S2"].query.startswith("site:ieso.ca") and "2026-903" in L["S2"].query)
    c.check("every URL decodes back to exactly its query", roundtrips(L))
    c.check("strong anchors add no topic words that could exclude the real document",
            "data center" not in L["M1"].query and "large load" not in L["M1"].query)

    # AESO: sentinel developer/POI, register jargon in the name, planning area location
    ae = _fx("AESO", "P3109", 1200.0, state="AB", county="Brooks", proj="Newell Data Center MPC Load",
             dev="NOT PUBLISHED IN AESO CONNECTION PROJECT LIST", poi="NOT PUBLISHED IN AESO CONNECTION PROJECT LIST")
    A = by_id(ae)
    c.check("'NOT PUBLISHED' sentinels never reach a query", not any("NOT PUBLISHED" in l.query.upper() for l in A.values()))
    c.check("core name used for local documents, exact register name kept for the operator's own site",
            '"Newell Data Center"' in A["M1"].query and "MPC Load" not in A["M1"].query
            and '"Newell Data Center MPC Load"' in A["S2"].query and "P3109" in A["S2"].query
            and A["S2"].query.startswith("site:aeso.ca"))
    c.check("Alberta vocabulary: development permit, AUC",
            '"development permit"' in A["M2"].query and A["E2"].query.startswith("site:auc.ab.ca"))

    # MISO: nothing but an ID, a transmission owner and an unknown county
    mi = _fx("MISO", "S1156", 632.0, state="TX", county="UNKNOWN",
             poi="NOT PUBLISHED BY MISO (Transmission Owner: ENTERGY TEXAS, INC. ETTO)")
    M = by_id(mi)
    c.check("queue ID only: local and environmental queries are place-led with topic words, the ID stays out",
            all("S1156" not in M[k].query for k in ("M1", "M2", "E1", "E2"))
            and '"data center"' in M["M1"].query and "Texas" in M["M1"].query and '"data center"' in M["E1"].query)
    c.check("queue ID only: the operator-site lead is where the ID is searched", "S1156" in M["S2"].query and M["S2"].query.startswith("site:misoenergy.org"))
    c.check("county 'UNKNOWN' is never searched", not any("UNKNOWN" in l.query for l in M.values()))
    c.check("transmission-owner lead uses the cleaned owner name", '"ENTERGY TEXAS, INC."' in M["S3"].query and "ETTO" not in M["S3"].query)
    c.check("Texas agencies: TCEQ and PUCT site restrictions", M["E1"].query.startswith("site:tceq.texas.gov")
            and M["E2"].query.startswith("site:puc.texas.gov"))

    # SPP: substation is the anchor; no site hint for Oklahoma so agency names are used
    sp = _fx("SPP", "GEN-2024-013", 496.0, state="OK", county="McClain", poi="Norman Hills 345 kV")
    S = by_id(sp)
    c.check("substation name is the anchor when no name is published (municipal, regulator, substation leads)",
            all('"Norman Hills 345 kV"' in S[k].query for k in ("M1", "M2", "E2", "S1")))
    c.check("environmental-permit queries drop the substation name and lean on place and topic instead",
            "Norman Hills" not in S["E1"].query and '"McClain" County Oklahoma' in S["E1"].query and '"data center"' in S["E1"].query)
    c.check("county searched as '<county> County <State>'", '"McClain" County Oklahoma' in S["M2"].query)
    c.check("no confident site hint -> agency names, not a guessed domain", '"Oklahoma DEQ"' in S["E1"].query and "site:" not in S["E1"].query)
    c.check("SPP ID searched on spp.org, quoted", S["S2"].query == 'site:spp.org "GEN-2024-013"', S["S2"].query)

    # NYISO: numeric IDs are cited as Q#nnnn; long free-text POI is truncated
    ny = _fx("NYISO", "1743", 1935.0, ent="Developer Not Matched To Known List", state="NY", county="St. Lawrence",
             proj="St. Lawrence Infrastructure 2", dev="St. Lawrence Infrastructure, LLC",
             poi="NYPA's 230kV Moses Massena 1 (MMS-1) and 230kV Moses Massena 2 (MMS-2)")
    N = by_id(ny)
    c.check("NYISO numeric ID searched in the forms other documents use", '"Q#1743"' in N["S2"].query and "site:nyiso.com" in N["S2"].query)
    c.check("a named facility's queries carry the state but not the county (minutes rarely repeat it)",
            '"St. Lawrence" County' not in N["M1"].query and N["M1"].query.endswith("New York"))
    c.check("distinct project and developer names are OR-ed", " OR " in N["M1"].query and '"St. Lawrence Infrastructure 2"' in N["M1"].query)
    c.check("New York vocabulary: planning board, DEC", '"planning board"' in N["M1"].query and N["E1"].query.startswith("site:dec.ny.gov"))
    c.check("long POI text is truncated inside its phrase", len(N["S1"].query) < 200 and N["S1"].query.startswith('"NYPA'))
    c.check("county source typo 'St; Lawrence' is repaired when the county is searched",
            '"St. Lawrence" County New York' in by_id(_fx("NYISO", "9", 150.0, state="NY", county="St; Lawrence"))["M2"].query)
    c.check("Louisiana uses 'Parish'", "Parish Louisiana" in by_id(_fx("MISO", "J2", 200.0, state="LA", county="Ouachita"))["M2"].query)

    # place handling when nothing names the facility
    wz = by_id(_fx("IESO", "2026-1", 200.0, state="ON", county="Essa"))
    c.check("IESO facility with no names: the zone is still never searched as a place",
            not any("essa" in l.query.lower() for l in wz.values()) and "Ontario" in wz["M1"].query)
    wa = by_id(_fx("AESO", "P1", 200.0, state="AB", county="Strathmore/Blackie"))
    c.check("AESO facility with no names: a 'Town/Town' planning area becomes alternatives plus the province",
            "(Strathmore OR Blackie) Alberta" in wa["M1"].query)

    # robustness
    odd = _fx("MISO", "J9", 100.0, state="MN", proj='The "Big" One & Co <x>')
    O = by_id(odd)
    c.check("quotes and ampersands in names keep queries balanced and URLs lossless",
            all(l.query.count('"') % 2 == 0 for l in O.values()) and roundtrips(O))
    bare = by_id(_fx("MISO", "J1", 100.0, state="MN"))
    c.check("a facility with every identifying field blank still gets leads and no empty phrases",
            len(bare) >= 5 and not any('""' in l.query for l in bare.values()), str(list(bare)))
    c.check("an unknown state code degrades to generic wording (no exception)",
            "ZZ" in by_id(_fx("MISO", "J3", 100.0, state="ZZ", poi="Foo 345 kV"))["M1"].query)
    c.check("search engines: bing and duckduckgo hosts",
            urlparse(by_id(iq, "bing")["M1"].url).netloc == "www.bing.com"
            and urlparse(by_id(iq, "duckduckgo")["M1"].url).netloc == "duckduckgo.com"
            and all(l.url.startswith("https://") for l in L.values()))
    c.check("no lead query is long enough to be truncated by a search engine",
            all(len(l.query) < 500 for f in (iq, ae, mi, sp, ny, odd) for l in build_leads(f)))
    long_names = _fx("NYISO", "1", 300.0, state="NY", county="Onondaga",
                     proj="An Extraordinarily Long Project Name For A Very Large Campus Development Phase",
                     dev="Another Remarkably Long Developer Entity Name Holdings And Partners Limited Partnership",
                     poi="A very long free-text point of interconnection description that keeps going and going on")
    c.check("query word budget: no lead exceeds 32 words even for worst-case long names (engines drop the rest)",
            all(query_words(l.query) <= 32 for f in (iq, ae, mi, sp, ny, odd, long_names) for l in build_leads(f)),
            str(max(query_words(l.query) for l in build_leads(long_names))))
    c.check("compose keeps required parts and drops optional ones that would overflow the budget",
            compose(["a b c"], ["d e", "f g h i j"], max_words=6) == "a b c d e"
            and compose(["a b c d e f g h"], ["x"], max_words=4) == "a b c d e f g h")
    c.check("jurisdiction data: every Canadian province and US state resolves without error",
            all(jurisdiction_for(code).name for code in STATE_NAMES))


def _selftest_overrides(c: _Checks) -> None:
    good_ev = [{"citation": "Council minutes, 2026-06-10, item 7.2", "url": "https://example.org/m.pdf"}]

    def item(**kw: Any) -> dict[str, Any]:
        base = {"rto": "IESO", "queue_id": "2026-903", "verified_label": "confirmed data center campus",
                "confirmed_by": "A. Researcher", "confirmed_on": "2026-10-04", "evidence": good_ev}
        base.update(kw)
        return base

    ov, problems = parse_overrides({"schema_version": 1, "overrides": [item(), item(rto="NYISO", queue_id=979)]})
    c.check("a valid document parses with no problems", not problems and len(ov) == 2, str(problems))
    c.check("labels match case-insensitively and are stored canonically",
            ov[("IESO", "2026-903")].label == "Confirmed Data Center Campus")
    c.check("numeric JSON queue_id is accepted and matches the zero-padded registry ID",
            ("NYISO", "979") in ov and ov[("NYISO", "979")].key == (normalize_rto("NYISO"), normalize_id("0979")))
    c.check("evidence citation and url are retained",
            ov[("IESO", "2026-903")].evidence[0].url == "https://example.org/m.pdf")

    def bad(**kw: Any) -> list[str]:
        return parse_overrides({"overrides": [item(**kw)]})[1]

    c.check("no evidence -> rejected", any("evidence" in p for p in bad(evidence=[])))
    c.check("evidence without a citation -> rejected", any("citation is required" in p for p in bad(evidence=[{"url": "https://x.org"}])))
    c.check("unknown label -> rejected and the allowed labels are listed",
            any("Confirmed Data Center Campus" in p and "not allowed" in p for p in bad(verified_label="Probably a data center")))
    c.check("unknown RTO -> rejected", any("is not one of" in p for p in bad(rto="PJMM")))
    c.check("bad date and bad URL -> rejected",
            any("ISO date" in p for p in bad(confirmed_on="10/04/2026"))
            and any("http" in p for p in bad(evidence=[{"citation": "x", "url": "ftp://x"}])))
    c.check("a mistyped key is an error, not silently ignored", any("verifed_operator" in p for p in bad(verifed_operator="X")))
    c.check("keys starting with '_' are allowed as comments", not bad(_note="scratch"))
    c.check("missing confirmed_by -> rejected", any("confirmed_by" in p for p in bad(confirmed_by=" ")))
    dup = parse_overrides({"overrides": [item(), item(queue_id=" 2026-903 ")]})[1]
    c.check("duplicate (rto, queue_id) -> rejected", any("duplicate" in p for p in dup))
    many = parse_overrides({"overrides": [item(rto="X"), item(evidence=[]), "nope"]})[1]
    c.check("all problems are reported at once, not just the first", len(many) >= 3, str(many))
    c.check("wrong top-level shapes are rejected",
            parse_overrides([])[1] != [] and parse_overrides({"overrides": "x"})[1] != []
            and parse_overrides({"schema_version": 2})[1] != [])
    c.check("the shipped empty template is valid", parse_overrides({"schema_version": 1, "_help": "x", "overrides": []}) == ({}, []))
    example = Path(__file__).resolve().parent / "ground_truth_overrides.example.json"
    if example.exists():
        ex, ex_problems = parse_overrides(json.loads(example.read_text(encoding="utf-8")))
        c.check("ground_truth_overrides.example.json (shipped with the tool) is itself valid and fictional",
                not ex_problems and len(ex) == 1 and next(iter(ex))[1].startswith("EXAMPLE"), str(ex_problems))
    else:
        print("  [SKIP] ground_truth_overrides.example.json not next to the script")

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "o.json"
        p.write_text('{"overrides": [', encoding="utf-8")
        c.check("invalid JSON -> OverrideError naming the line", _raises(lambda: load_overrides(p), OverrideError, "line"))

    recs = [_fx("IESO", "2026-903", 1380.0), _fx("NYISO", "0979", 435.0), _fx("IESO", "colo", 450.0, ent="Wholesale Colocation Developer")]
    sel, _ = filter_ambiguous(recs)
    ovs = parse_overrides({"overrides": [item(), item(rto="ISONE", queue_id="1"), item(rto="NYISO", queue_id="979"),
                                        item(queue_id="colo"), item(queue_id="gone")]})[0]
    audit = audit_overrides(ovs, recs + [_fx("ISO-NE", "1", 100.0, tier="x")], sel)
    c.check("audit separates applied / excluded-by-filter / orphan overrides",
            sorted(k[1] for k in audit.applied) == ["2026-903", "979"]
            and sorted(o.queue_id for o in audit.excluded) == ["1", "colo"] and [o.queue_id for o in audit.orphans] == ["gone"],
            f"{list(audit.applied)} {[o.queue_id for o in audit.excluded]} {[o.queue_id for o in audit.orphans]}")
    c.check("the same queue ID in another RTO is not overridden",
            audit_overrides(parse_overrides({"overrides": [item(rto="SPP")]})[0], recs, sel).applied == {})


def _selftest_loading(c: _Checks) -> None:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        rows = [_html_row("IESO", "2026-903", 1380.0, co="Essa", proj="Project IQ197", dev="197 McKay Barrie Corp"),
                _html_row("IESO", "2026-885", 1000.0, co="West"),
                _html_row("MISO", "J1490", 1000.0, st="MO", co="Randolph"),
                _html_row("MISO", "OLD", 300.0, st="MO")]
        (d / "index.html").write_text(_html_text(rows), encoding="utf-8")
        got = load_html_registry(d / "index.html")
        c.check("index.html registry parses into facilities", len(got) == 4 and got[0].project_name == "Project IQ197"
                and got[0].developer == "197 McKay Barrie Corp" and got[0].capacity_mw == 1380.0)
        (d / "bad.html").write_text("<html>no data</html>", encoding="utf-8")
        c.check("index.html without REGISTRY_DATA -> DataError", _raises(lambda: load_html_registry(d / "bad.html"), DataError, "REGISTRY_DATA"))

        enriched = ("queue_id,rto_region,state,county,capacity_mw,developer_entity_raw,entity_category,"
                    "load_type_tier,transmission_owner\n"
                    f"J1490,MISO,MO,Randolph,1000.0,NOT PUBLISHED IN MISO GI QUEUE DATA,Developer Not Disclosed,{AMBIGUOUS_TIER},\n"
                    f"J2000,MISO,MI,Kent,250.0,NOT PUBLISHED IN MISO GI QUEUE DATA,Developer Not Disclosed,{AMBIGUOUS_TIER},METC\n")
        raw = ("queue_id,rto_region,state,county,poi_substation,capacity_mw,projected_date,developer_entity,status,project_name,raw_fuel_technology\n"
               "J1490,MISO,MO,Randolph,McCredie - Montgomery 345 kV Line Tap,1000.0,2029-01-01,x,IA in Progress,,Load - Data Center (AI)\n")
        (d / "computational_load_estimates_t.csv").write_text(enriched, encoding="utf-8")
        (d / "registry_raw_t.csv").write_text(raw, encoding="utf-8")
        facs, unmatched = load_enriched_csv(d / "computational_load_estimates_t.csv", d / "registry_raw_t.csv")
        c.check("enriched CSV is joined to the raw CSV (POI, status, technology, date)",
                facs[0].poi.startswith("McCredie") and facs[0].status == "IA in Progress"
                and facs[0].technology == "Load - Data Center (AI)" and facs[0].projected_date == "2029-01-01")
        c.check("a CSV row with no raw match is counted, kept, and has blank raw fields", unmatched == 1 and facs[1].poi == "" and facs[1].transmission_owner == "METC")
        c.check("raw CSV is found next to the enriched CSV by name",
                derive_raw_path(d / "computational_load_estimates_t.csv") == d / "registry_raw_t.csv")

        recs, srcs = load_registry(d / "computational_load_estimates_t.csv", None, d / "index.html")
        miso = sorted(f.queue_id for f in recs if f.rto == "MISO")
        c.check("CSV replaces the HTML rows of its RTO (no duplicates, stale MISO row gone)", miso == ["J1490", "J2000"], str(miso))
        c.check("RTOs the CSV lacks are kept from index.html", sorted(f.queue_id for f in recs if f.rto == "IESO") == ["2026-885", "2026-903"])
        c.check("the load report says what was replaced", "replaces 2 index.html rows for MISO" in srcs[1].note, srcs[1].note)
        recs_csv_only, _ = load_registry(d / "computational_load_estimates_t.csv", None, None, use_html=False)
        c.check("--no-html loads the CSV alone", {f.rto for f in recs_csv_only} == {"MISO"})
        (d / "noreq.csv").write_text("queue_id,rto_region\n1,MISO\n", encoding="utf-8")
        c.check("missing required column -> DataError naming it", _raises(lambda: load_enriched_csv(d / "noreq.csv"), DataError, "capacity_mw"))
        c.check("explicit --input that does not exist -> DataError", _raises(lambda: load_registry(d / "nope.csv"), DataError, "not found"))
        c.check("nothing to load -> DataError with guidance", _raises(lambda: load_registry(None, None, None, use_html=False), DataError, "--input"))

        try:  # the loader must read exactly what embed_registry_data.py writes
            import embed_registry_data as _embed  # needs pandas; skipped without it
        except ImportError:
            print("  [SKIP] round-trip with embed_registry_data.serialize (module or pandas not importable)")
        else:
            emb_rows = [{"id": "0979", "rto": "NYISO", "st": "NY", "co": "St. Lawrence", "poi": "Reynolds 115kV",
                         "mw": 435.0, "status": "Under Study", "proj": "North Country </script> Data Center",
                         "dev": "North Country Data Center", "ent": "Developer Not Matched To Known List",
                         "tier": AMBIGUOUS_TIER, "gpu": 1, "flops": 1.5e26, "flag": True}]
            html = "<script>\nconst REGISTRY_DATA = " + _embed.serialize(emb_rows) + ";\n\nconst X=1;</script>"
            (d / "emb.html").write_text(html, encoding="utf-8")
            back = load_html_registry(d / "emb.html")
            c.check("loader reads embed_registry_data.serialize output (incl. escaped '</script>' and leading-zero IDs)",
                    len(back) == 1 and back[0].queue_id == "0979" and "</script>" in back[0].project_name)


def _selftest_end_to_end(c: _Checks) -> None:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        rows = [
            _html_row("IESO", "2026-903", 1380.0, ent="Developer Not Matched To Known List", co="Essa", proj="Project IQ197", dev="197 McKay Barrie Corp"),
            _html_row("AESO", "P3066", 1864.0, st="AB", co="Caroline", proj="Leedale Data Load", dev="NOT PUBLISHED IN AESO CONNECTION PROJECT LIST"),
            _html_row("SPP", "GEN-1", 496.0, st="OK", co="McClain", poi="Norman Hills 345 kV"),
            _html_row("NYISO", "0979", 435.0, st="NY", co="St. Lawrence", proj="Pipe | Name"),
            _html_row("PJM", "X1", 900.0, tier="Confirmed Grid-Scale Storage (BESS)"),
        ]
        (d / "index.html").write_text(_html_text(rows), encoding="utf-8")
        ov = {"schema_version": 1, "overrides": [
            {"rto": "IESO", "queue_id": "2026-903", "verified_label": "Confirmed Data Center Campus",
             "verified_operator": "Example Operator Inc.", "confirmed_by": "A. Researcher", "confirmed_on": "2026-10-04",
             "evidence": [{"citation": "Council minutes 2026-06-10, item 7.2", "url": "https://example.org/m.pdf"}],
             "notes": "site visit pending"},
            {"rto": "SPP", "queue_id": "GEN-404", "verified_label": "Confirmed Other Large Load",
             "confirmed_by": "A. Researcher", "confirmed_on": "2026-10-04", "evidence": [{"citation": "n/a"}]}]}
        (d / "o.json").write_text(json.dumps(ov), encoding="utf-8")
        out, js = d / "dossier.md", d / "dossier.json"
        argv = ["--html", str(d / "index.html"), "--overrides", str(d / "o.json"), "--output", str(out),
                "--json", str(js), "--generated-on", "2026-10-01"]
        rc, stdout, stderr = _quiet_main(argv)
        text = out.read_text(encoding="utf-8") if out.exists() else ""
        c.check("end to end: exit code 0 and a dossier is written", rc == 0 and bool(text), f"rc={rc} {stderr}")
        order = [text.find(f"### {i}.") for i in (1, 2, 3, 4)]
        c.check("facilities appear ranked by capacity (AESO 1,864 > IESO 1,380 > SPP 496 > NYISO 435)",
                all(o > 0 for o in order) and order == sorted(order)
                and text.find("AESO P3066") < text.find("IESO 2026-903") < text.find("SPP GEN-1") < text.find("NYISO 0979"))
        c.check("the BESS row is not in the dossier", "PJM X1" not in text)
        c.check("verified facility shows label, operator, evidence and citation URL",
                "**VERIFIED \u2014 Confirmed Data Center Campus**" in text and "Example Operator Inc." in text
                and "Council minutes 2026-06-10, item 7.2" in text and "<https://example.org/m.pdf>" in text)
        c.check("verified facility's leads are collapsed; unverified facilities say nothing was verified",
                text.count("<details>") == 1 and text.count("nothing below has been fetched or verified") == 3)
        c.check("summary counts: 1 of 4 verified; orphan override listed in the audit",
                "**Verified: 1 of 4**" in text and "SPP GEN-404" in text and "Match nothing in the loaded registry" in text)
        c.check("IESO location is described as a zone, AESO as a planning area",
                'IESO electrical zone "Essa" (a grid region, not a municipality)' in text
                and 'AESO planning area "Caroline"' in text)
        c.check("pipes in names are escaped so tables do not break", "Pipe \\| Name" in text)
        c.check("ranked summary tags IESO zones and AESO areas; county rows say 'county field'",
                "ON \u00b7 Essa zone" in text and "AB \u00b7 Caroline area" in text and 'county field "McClain"' in text
                and "| OK \u00b7 McClain |" in text)
        c.check("portals section lists the operators and agencies involved", "## Where the records live" in text and "ero.ontario.ca" in text and "spp.org" in text.lower())
        data = json.loads(js.read_text(encoding="utf-8"))
        c.check("JSON export has every facility, its leads and its verification",
                len(data["facilities"]) == 4 and data["facilities"][1]["verified"]["label"] == "Confirmed Data Center Campus"
                and all(f["leads"] for f in data["facilities"]))
        rc2, _, _ = _quiet_main(argv)
        c.check("re-running with the same inputs gives byte-identical output", rc2 == 0 and out.read_text(encoding="utf-8") == text)
        rc3, _, _ = _quiet_main(argv + ["--top", "2"])
        top2 = out.read_text(encoding="utf-8")
        c.check("--top limits the facility sections and says so", rc3 == 0 and "### 2." in top2 and "### 3." not in top2 and "Showing the largest 2 of 4" in top2)
        rc4, _, _ = _quiet_main(argv[:-2] + ["--rto", "IESO,SPP"])
        only = out.read_text(encoding="utf-8")
        c.check("--rto limits the RTOs and the scope line records it", rc4 == 0 and "AESO P3066" not in only and "RTOs limited to IESO, SPP" in only)

        (d / "bad.json").write_text(json.dumps({"overrides": [{"rto": "IESO", "queue_id": "1"}]}), encoding="utf-8")
        before = out.read_text(encoding="utf-8")
        rc5, _, err5 = _quiet_main(["--html", str(d / "index.html"), "--overrides", str(d / "bad.json"), "--output", str(out)])
        c.check("invalid overrides -> exit 2, problems listed, existing dossier untouched",
                rc5 == 2 and "verified_label" in err5 and out.read_text(encoding="utf-8") == before)
        rc6, _, err6 = _quiet_main(["--html", str(d / "nope.html"), "--output", str(out)])
        c.check("missing input -> exit 1 with a message", rc6 == 1 and "not found" in err6)
        (d / "empty.html").write_text(_html_text([_html_row("PJM", "X", 900.0, tier="Confirmed Grid-Scale Storage (BESS)")]), encoding="utf-8")
        rc7, _, err7 = _quiet_main(["--html", str(d / "empty.html"), "--output", str(out)])
        c.check("zero matches -> exit 1 and the labels actually present are shown", rc7 == 1 and "Confirmed Grid-Scale Storage (BESS)" in err7)
        rc8, _, _ = _quiet_main(["--html", str(d / "index.html"), "--rto", "MARS"])
        c.check("unknown --rto -> exit 1", rc8 == 1)


def run_selftest() -> bool:
    """Runs every group inside an empty scratch directory. main() looks for
    ./index.html, ./data/computational_load_estimates.csv and
    ./ground_truth_overrides.json by default, so a self-test that ran in the
    repository would silently pick up the real registry and real overrides
    (it did: the monthly workflow's second run failed this way in simulation)."""
    checks = _Checks()
    original_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as sandbox:
        os.chdir(sandbox)
        try:
            print("[isolation]")
            checks.check("self-test runs in an empty scratch directory (files in the caller's cwd cannot leak in)",
                         not any(Path(".").iterdir()))
            for name, fn in (("filtering", _selftest_filtering), ("helpers", _selftest_helpers),
                             ("query generation", _selftest_leads), ("overrides", _selftest_overrides),
                             ("loading", _selftest_loading), ("end to end", _selftest_end_to_end)):
                print(f"[{name}]")
                try:
                    fn(checks)
                except Exception as exc:  # noqa: BLE001 - a crash in a group is a failed check, not a lost report
                    checks.failed += 1
                    print(f"  [FAIL] {name}: raised {type(exc).__name__}: {exc}")
        finally:
            os.chdir(original_cwd)
    print()
    if checks.failed:
        print(f"{checks.failed} CHECK(S) FAILED ({checks.passed} passed)")
        return False
    print(f"ALL CHECKS PASSED ({checks.passed}/{checks.passed})")
    return True


if __name__ == "__main__":
    sys.exit(main())
