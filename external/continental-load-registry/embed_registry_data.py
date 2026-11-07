#!/usr/bin/env python3
"""
embed_registry_data.py
======================

Updates the `const REGISTRY_DATA = [...]` array embedded in index.html from
the CSVs the two pipeline scripts write, so a data refresh is a command
instead of a hand edit:

    python ingest_grid_queues.py --include-raw-fields --output registry_raw.csv
    python compute_anomaly_detector.py --input registry_raw.csv --output computational_load_estimates.csv
    python embed_registry_data.py --raw registry_raw.csv --enriched computational_load_estimates.csv

Merge rule: every RTO that appears in the CSVs REPLACES that RTO's existing
rows in the page; RTOs absent from the CSVs are left exactly as they are.
That is what lets you refresh MISO alone (or add a new RTO) without
re-running the other eight, and it makes the command idempotent. The final
array is ordered the way the page has always been: review-flagged rows first,
then by capacity descending (a stable sort, so ties keep their prior order).

Field mapping (verified against the 1,164 rows already in the page: the
embedded gpu/flops differ from a recomputation from `mw` by at most 0.05%,
purely because `mw` is stored rounded to one decimal while gpu/flops were
computed from the unrounded capacity):

    id    <- queue_id                  st    <- state          co  <- county
    rto   <- rto_region                poi   <- poi_substation (raw CSV)
    mw    <- round(capacity_mw, 1)     status<- status (raw CSV)
    proj  <- project_name (raw CSV)    dev   <- developer_entity_raw
    ent   <- entity_category           tier  <- load_type_tier
    gpu   <- gpus_estimate_reference   flops <- run_flops_90d_reference
    flag  <- review_priority

The raw CSV must have been written with --include-raw-fields (it supplies
poi / status / project name, which the enriched CSV does not carry).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any

import pandas as pd

DATA_RE = re.compile(r"const REGISTRY_DATA = (\[.*?\]);\n", re.S)
KEY_ORDER = ["id", "rto", "st", "co", "poi", "mw", "status", "proj", "dev", "ent", "tier", "gpu", "flops", "flag"]


def _text(v: Any) -> str:
    return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)


def rows_from_csvs(raw_path: Path, enriched_path: Path) -> list[dict]:
    raw = pd.read_csv(raw_path, dtype={"queue_id": str})
    enriched = pd.read_csv(enriched_path, dtype={"queue_id": str})
    needed_raw = {"queue_id", "rto_region", "poi_substation", "status", "project_name"}
    if not needed_raw <= set(raw.columns):
        raise SystemExit(
            f"{raw_path} is missing {sorted(needed_raw - set(raw.columns))}: re-run "
            "ingest_grid_queues.py with --include-raw-fields"
        )
    merged = enriched.merge(
        raw[["queue_id", "rto_region", "poi_substation", "status", "project_name"]],
        on=["queue_id", "rto_region"], how="left", validate="one_to_one",
    )
    if merged["status"].isna().any():
        raise SystemExit("some enriched rows have no match in the raw CSV (queue_id / rto_region mismatch)")
    rows = []
    for _, r in merged.iterrows():
        rows.append(OrderedDict([
            ("id", _text(r["queue_id"])), ("rto", _text(r["rto_region"])),
            ("st", _text(r["state"])), ("co", _text(r["county"])),
            ("poi", _text(r["poi_substation"])), ("mw", round(float(r["capacity_mw"]), 1)),
            ("status", _text(r["status"])), ("proj", _text(r["project_name"])),
            ("dev", _text(r["developer_entity_raw"])), ("ent", _text(r["entity_category"])),
            ("tier", _text(r["load_type_tier"])), ("gpu", int(r["gpus_estimate_reference"])),
            ("flops", float(r["run_flops_90d_reference"])), ("flag", bool(r["review_priority"])),
        ]))
    return rows


def merge_rows(existing: list[dict], new_rows: list[dict]) -> list[dict]:
    replaced = {r["rto"] for r in new_rows}
    kept = [r for r in existing if r["rto"] not in replaced]
    merged = kept + new_rows
    merged.sort(key=lambda r: (not r["flag"], -r["mw"]))  # stable
    return merged


def serialize(rows: list[dict]) -> str:
    text = json.dumps([OrderedDict((k, r[k]) for k in KEY_ORDER) for r in rows],
                      separators=(",", ":"), ensure_ascii=True)
    return text.replace("</", "<\\/")  # never let data close the <script> element


def summarize(rows: list[dict]) -> dict[str, tuple[int, float]]:
    out: dict[str, list] = {}
    for r in rows:
        n, mw = out.setdefault(r["rto"], [0, 0.0])
        out[r["rto"]] = [n + 1, mw + r["mw"]]
    return {k: (v[0], v[1]) for k, v in out.items()}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--html", type=Path, default=Path("index.html"))
    ap.add_argument("--raw", type=Path, required=True, help="registry CSV from ingest_grid_queues.py --include-raw-fields")
    ap.add_argument("--enriched", type=Path, required=True, help="CSV from compute_anomaly_detector.py")
    ap.add_argument("--output", type=Path, default=None, help="write here instead of overwriting --html")
    ap.add_argument("--dry-run", action="store_true", help="print the before/after summary and write nothing")
    args = ap.parse_args(argv)

    html = args.html.read_text(encoding="utf-8")
    m = DATA_RE.search(html)
    if not m:
        raise SystemExit(f"no 'const REGISTRY_DATA = [...];' found in {args.html}")
    existing = json.loads(m.group(1))
    new_rows = rows_from_csvs(args.raw, args.enriched)
    merged = merge_rows(existing, new_rows)

    before, after = summarize(existing), summarize(merged)
    print(f"{'RTO':8s} {'before':>18s}   {'after':>18s}")
    for rto in sorted(set(before) | set(after)):
        b, a = before.get(rto, (0, 0.0)), after.get(rto, (0, 0.0))
        print(f"{rto:8s} {b[0]:6d} rows {b[1]/1000:7.1f} GW   {a[0]:6d} rows {a[1]/1000:7.1f} GW")
    print(f"{'TOTAL':8s} {len(existing):6d} rows {sum(r['mw'] for r in existing)/1000:7.1f} GW   "
          f"{len(merged):6d} rows {sum(r['mw'] for r in merged)/1000:7.1f} GW")
    if args.dry_run:
        return 0

    new_html = html[:m.start(1)] + serialize(merged) + html[m.end(1):]
    (args.output or args.html).write_text(new_html, encoding="utf-8")
    print(f"written: {args.output or args.html}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
