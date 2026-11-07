#!/usr/bin/env python3
"""
guard_registry_refresh.py
=========================

Sanity gate that sits between the monthly pipeline and embed_registry_data.py.

ingest_grid_queues.py wraps every source separately, so when one feed is
blocked, moved or reformatted the run still exits 0 with a partial CSV, and
embed_registry_data.py then replaces that RTO's rows in index.html with
whatever came back. For a public dashboard that is cited in regulatory
filings, "SPP silently dropped from 139 rows to 11" must not be published
automatically. This script compares each refreshed RTO with what index.html
currently holds and decides, per RTO:

  accepted     within the allowed range of the current row count AND capacity
  rejected     outside that range, an unknown RTO label, duplicate queue IDs,
               or unreadable capacities -- the previous rows stay untouched
  unavailable  the pipeline produced no rows for it (feed blocked / failed) --
               the previous rows stay untouched
  new          not in index.html yet -- accepted

Only accepted RTOs are written to --out-raw / --out-enriched, and those are
what embed_registry_data.py should read. Nothing is decided by guesswork about
whether a change is "real": a genuine 60% drop in one month is rejected too,
and shows up as an error for a human to look at.

USAGE
    python guard_registry_refresh.py --html index.html \\
        --raw fresh/registry_raw.csv --enriched fresh/computational_load_estimates.csv \\
        --out-raw data/registry_raw.csv --out-enriched data/computational_load_estimates.csv \\
        [--min-ratio 0.5] [--max-ratio 2.0] [--min-old-rows 5] \\
        [--summary-md "$GITHUB_STEP_SUMMARY"] [--github-output "$GITHUB_OUTPUT"]
    python guard_registry_refresh.py --selftest

EXIT CODES
    0 at least one RTO accepted (rejections are reported, and listed in the
      `rejected` output so the workflow can fail after committing the rest)
    2 unusable input (missing file / required column)
    3 nothing accepted -- there is nothing to embed
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

KNOWN_RTOS = ("PJM", "ERCOT", "SPP", "MISO", "CAISO", "NYISO", "ISO-NE", "IESO", "AESO")

KNOWN_PJM_TERMINAL_STATUSES = {
    "WITHDRAWN", "CANCELLED", "CANCELED", "IN SERVICE", "TERMINATED",
    "RETIRED", "DEACTIVATED", "SUSPENDED", "RETRACTED", "ANNULLED",
    "PENDING TERMINATION",
}

# Exactly the columns embed_registry_data.rows_from_csvs reads.
ENRICHED_REQUIRED = ("queue_id", "rto_region", "state", "county", "capacity_mw", "developer_entity_raw",
                     "entity_category", "load_type_tier", "gpus_estimate_reference",
                     "run_flops_90d_reference", "review_priority")
RAW_REQUIRED = ("queue_id", "rto_region", "poi_substation", "status", "project_name")

_DATA_RE = re.compile(r"const REGISTRY_DATA = (\[.*?\]);\n", re.S)


class GuardInputError(Exception):
    """Unusable input (exit code 2)."""


@dataclass
class Decision:
    rto: str
    outcome: str            # accepted | rejected | unavailable | new
    old_rows: int = 0
    old_mw: float = 0.0
    new_rows: int = 0
    new_mw: float = 0.0
    reason: str = ""


def read_source_health(path: Optional[Path]) -> dict[str, dict]:
    """Read optional source-health evidence produced by the ingest pipeline."""
    if path is None or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    sources = payload.get("sources", {})
    return sources if isinstance(sources, dict) else {}


def shrink_is_explainable(
    rto: str, old_rows: int, new_rows: int, health: dict[str, dict],
) -> bool:
    """Allow a large PJM shrink only when raw-feed health explains it."""
    if rto != "PJM" or new_rows >= old_rows:
        return False
    h = health.get(rto)
    if not isinstance(h, dict) or h.get("fetch_errors"):
        return False
    try:
        rows_fetched = int(h.get("rows_fetched", 0))
        excluded_by_status = int(h.get("excluded_by_status", 0))
        status_values = h.get("excluded_status_values", {})
        if rows_fetched < max(1000, old_rows * 2):
            return False
        if not isinstance(status_values, dict):
            return False
        if excluded_by_status != sum(int(v) for v in status_values.values()):
            return False
        return all(
            str(raw).strip().upper() in KNOWN_PJM_TERMINAL_STATUSES
            for raw in status_values
        )
    except (TypeError, ValueError):
        return False


def safe_label(label: str) -> str:
    """RTO labels end up in GITHUB_OUTPUT, workflow annotations and Markdown, so
    anything outside a harmless alphabet is replaced (a label can never inject
    an extra output line or a workflow command)."""
    return re.sub(r"[^A-Za-z0-9._-]", "?", label)[:40] or "?"


def registry_stats(html_text: str) -> dict[str, tuple[int, float]]:
    """(rows, MW) per RTO currently embedded in index.html."""
    m = _DATA_RE.search(html_text)
    if not m:
        raise GuardInputError("no 'const REGISTRY_DATA = [...];' found in the HTML file")
    stats: dict[str, list] = {}
    for row in json.loads(m.group(1)):
        entry = stats.setdefault(row["rto"], [0, 0.0])
        entry[0] += 1
        entry[1] += float(row["mw"])
    return {k: (v[0], v[1]) for k, v in stats.items()}


def read_table(path: Path, required: tuple[str, ...]) -> tuple[list[str], list[list[str]]]:
    if not path.exists():
        raise GuardInputError(f"{path} does not exist")
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        header = next(reader, None)
        if header is None:
            raise GuardInputError(f"{path} is empty")
        missing = [c for c in required if c not in header]
        if missing:
            hint = (" (re-run ingest_grid_queues.py with --include-raw-fields)"
                    if "poi_substation" in missing or "project_name" in missing else "")
            raise GuardInputError(f"{path} is missing column(s) {missing}{hint}")
        return header, [row for row in reader if any(cell.strip() for cell in row)]


def _range_problem(old_rows: int, old_mw: float, new_rows: int, new_mw: float,
                   min_ratio: float, max_ratio: float, min_old_rows: int) -> str:
    if old_rows < max(min_old_rows, 1):
        return ""  # too small a baseline for a ratio to mean anything (and never divide by zero)
    rows_ratio = new_rows / old_rows
    if not min_ratio <= rows_ratio <= max_ratio:
        return (f"row count {old_rows} -> {new_rows} ({rows_ratio:.0%} of current; "
                f"allowed {min_ratio:.0%}-{max_ratio:.0%})")
    if old_mw > 0:
        mw_ratio = new_mw / old_mw
        if not min_ratio <= mw_ratio <= max_ratio:
            return (f"capacity {old_mw / 1000:.1f} -> {new_mw / 1000:.1f} GW ({mw_ratio:.0%} of current; "
                    f"allowed {min_ratio:.0%}-{max_ratio:.0%})")
    return ""


def decide(
    current: dict[str, tuple[int, float]], raw_header: list[str], raw_rows: list[list[str]],
    enr_header: list[str], enr_rows: list[list[str]], *, min_ratio: float = 0.5,
    max_ratio: float = 2.0, min_old_rows: int = 5,
    source_health: Optional[dict[str, dict]] = None,
) -> list[Decision]:
    """One Decision per RTO seen in either the current registry or the fresh CSVs."""
    e_rto, e_id, e_mw = (enr_header.index(c) for c in ("rto_region", "queue_id", "capacity_mw"))
    r_rto, r_id = raw_header.index("rto_region"), raw_header.index("queue_id")

    fresh: dict[str, dict] = {}
    for row in enr_rows:
        rto = row[e_rto].strip()
        f = fresh.setdefault(rto, {"rows": 0, "mw": 0.0, "bad_mw": 0, "keys": []})
        f["rows"] += 1
        f["keys"].append(row[e_id].strip())
        try:
            f["mw"] += float(row[e_mw])
        except ValueError:
            f["bad_mw"] += 1
    raw_keys: dict[str, list[str]] = {}
    for row in raw_rows:
        raw_keys.setdefault(row[r_rto].strip(), []).append(row[r_id].strip())

    decisions: list[Decision] = []
    for rto in sorted(set(current) | set(fresh)):
        old_rows, old_mw = current.get(rto, (0, 0.0))  # (0, 0.0) = not in the registry yet
        f = fresh.get(rto)
        if f is None:
            decisions.append(Decision(rto, "unavailable", old_rows, old_mw,
                                      reason="no rows in this run's output; previous rows kept"))
            continue
        d = Decision(rto, "accepted", old_rows, old_mw, f["rows"], f["mw"])
        problem = ""
        if rto not in KNOWN_RTOS:
            problem = f"unknown rto_region label {safe_label(rto)!r}"
        elif f["bad_mw"]:
            problem = f"{f['bad_mw']} rows have an unreadable capacity_mw"
        elif len(set(f["keys"])) != len(f["keys"]):
            problem = "duplicate queue_id values within the RTO (embed_registry_data would abort)"
        elif sorted(f["keys"]) != sorted(raw_keys.get(rto, [])):
            problem = "raw and enriched CSVs disagree on this RTO's queue_id set"
        else:
            problem = _range_problem(old_rows, old_mw, f["rows"], f["mw"], min_ratio, max_ratio, min_old_rows)
        if problem:
            if shrink_is_explainable(rto, old_rows, f["rows"], source_health or {}) and problem.startswith("row count "):
                d.reason = (
                    problem + "; accepted because source-health evidence shows a substantial "
                    "raw feed and only known terminal PJM statuses were excluded"
                )
            else:
                d.outcome, d.reason = "rejected", problem + ("; previous rows kept" if old_rows else "")
        elif old_rows == 0:
            d.outcome, d.reason = "new", "not in the registry yet"
        decisions.append(d)
    return decisions


def write_filtered(path_in: Path, header: list[str], rows: list[list[str]], rto_col: str,
                   keep: set[str], path_out: Path) -> int:
    """Copy of the table containing only the accepted RTOs, values byte-for-byte."""
    idx = header.index(rto_col)
    path_out.parent.mkdir(parents=True, exist_ok=True)
    kept = [r for r in rows if r[idx].strip() in keep]
    with path_out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(kept)
    return len(kept)


def _fmt(rows: int, mw: float) -> str:
    return f"{rows} row{'s' if rows != 1 else ''}, {mw / 1000:.1f} GW" if rows else "\u2014"


def render_markdown(decisions: list[Decision]) -> str:
    lines = ["### Registry refresh gate", "", "| RTO | Current | Fresh | Decision |", "|---|---|---|---|"]
    for d in decisions:
        text = d.outcome + (f": {d.reason}" if d.reason else "")
        lines.append(f"| {safe_label(d.rto)} | {_fmt(d.old_rows, d.old_mw)} | {_fmt(d.new_rows, d.new_mw)} | {text} |")
    return "\n".join(lines) + "\n"


def run(args: argparse.Namespace) -> int:
    try:
        current = registry_stats(Path(args.html).read_text(encoding="utf-8"))
        raw_header, raw_rows = read_table(Path(args.raw), RAW_REQUIRED)
        enr_header, enr_rows = read_table(Path(args.enriched), ENRICHED_REQUIRED)
        source_health = read_source_health(Path(args.source_health) if args.source_health else None)
    except (GuardInputError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    decisions = decide(current, raw_header, raw_rows, enr_header, enr_rows, min_ratio=args.min_ratio,
                       max_ratio=args.max_ratio, min_old_rows=args.min_old_rows,
                       source_health=source_health)
    by_outcome = {k: [d.rto for d in decisions if d.outcome == k] for k in ("accepted", "new", "rejected", "unavailable")}
    accepted = set(by_outcome["accepted"]) | set(by_outcome["new"])

    print(f"{'RTO':8s} {'current':>20s}   {'fresh':>20s}   decision")
    for d in decisions:
        print(f"{safe_label(d.rto):8s} {_fmt(d.old_rows, d.old_mw):>20s}   {_fmt(d.new_rows, d.new_mw):>20s}   "
              f"{d.outcome}" + (f": {d.reason}" if d.reason else ""))
    print(f"\n{len(accepted)} accepted, {len(by_outcome['rejected'])} rejected, "
          f"{len(by_outcome['unavailable'])} unavailable")

    if os.environ.get("GITHUB_ACTIONS") == "true":
        for d in decisions:
            if d.outcome == "unavailable" and d.old_rows:
                print(f"::warning title={safe_label(d.rto)} feed unavailable::{safe_label(d.rto)} returned no rows this run; "
                      f"index.html keeps its previous {d.old_rows} rows.")
            elif d.outcome == "rejected":
                print(f"::error title={safe_label(d.rto)} refresh rejected::{safe_label(d.rto)}: {d.reason}")

    if args.summary_md:
        with open(args.summary_md, "a", encoding="utf-8") as fh:
            fh.write(render_markdown(decisions) + "\n")
    if args.github_output:
        with open(args.github_output, "a", encoding="utf-8") as fh:
            fh.write(f"accepted={','.join(sorted(safe_label(r) for r in accepted))}\n")
            fh.write(f"rejected={','.join(safe_label(r) for r in by_outcome['rejected'])}\n")
            fh.write(f"unavailable={','.join(safe_label(r) for r in by_outcome['unavailable'])}\n")

    if not accepted:
        print("ERROR: no RTO passed the gate; nothing to embed", file=sys.stderr)
        return 3
    n_raw = write_filtered(Path(args.raw), raw_header, raw_rows, "rto_region", accepted, Path(args.out_raw))
    n_enr = write_filtered(Path(args.enriched), enr_header, enr_rows, "rto_region", accepted, Path(args.out_enriched))
    print(f"wrote {args.out_raw} ({n_raw} rows) and {args.out_enriched} ({n_enr} rows)")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Per-RTO sanity gate for a refreshed registry (see module docstring).")
    p.add_argument("--html", default="index.html", help="index.html holding the current registry (default: %(default)s)")
    p.add_argument("--raw", help="fresh raw CSV (ingest_grid_queues.py --include-raw-fields)")
    p.add_argument("--enriched", help="fresh enriched CSV (compute_anomaly_detector.py)")
    p.add_argument("--out-raw", help="where to write the accepted rows of --raw")
    p.add_argument("--out-enriched", help="where to write the accepted rows of --enriched")
    p.add_argument("--min-ratio", type=float, default=0.5, help="lowest fresh/current ratio accepted (default: %(default)s)")
    p.add_argument("--max-ratio", type=float, default=2.0, help="highest fresh/current ratio accepted (default: %(default)s)")
    p.add_argument("--min-old-rows", type=int, default=5,
                   help="RTOs with fewer current rows skip the ratio test (default: %(default)s)")
    p.add_argument("--source-health",
                   help="Optional JSON source-health manifest for evidence-based "
                        "acceptance of a large PJM shrink.")
    p.add_argument("--summary-md", help="append a Markdown table here (e.g. $GITHUB_STEP_SUMMARY)")
    p.add_argument("--github-output", help="append accepted=/rejected=/unavailable= lines here (e.g. $GITHUB_OUTPUT)")
    p.add_argument("--selftest", action="store_true", help="run against synthetic fixtures and exit")
    return p


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.selftest:
        return 0 if run_selftest() else 1
    for name in ("raw", "enriched", "out_raw", "out_enriched"):
        if not getattr(args, name):
            parser.error(f"--{name.replace('_', '-')} is required")
    if not 0 < args.min_ratio <= 1 <= args.max_ratio:
        parser.error("need 0 < --min-ratio <= 1 <= --max-ratio")
    return run(args)


# --------------------------------------------------------------------------
# Self-test
# --------------------------------------------------------------------------

def _html(counts: dict[str, tuple[int, float]]) -> str:
    rows = [{"id": f"{rto}-{i}", "rto": rto, "mw": mw} for rto, (n, mw) in counts.items() for i in range(n)]
    return "<script>\nconst REGISTRY_DATA = " + json.dumps(rows) + ";\n\nconst X = 1;\n</script>"


def _tables(spec: dict[str, tuple[int, float]], dup: Optional[str] = None, bad_mw: Optional[str] = None
            ) -> tuple[str, str]:
    """(raw CSV text, enriched CSV text) with `n` rows of `mw` MW per RTO in `spec`."""
    raw, enr = io.StringIO(), io.StringIO()
    rw, ew = csv.writer(raw, lineterminator="\n"), csv.writer(enr, lineterminator="\n")
    rw.writerow(RAW_REQUIRED)
    ew.writerow(ENRICHED_REQUIRED)
    for rto, (n, mw) in spec.items():
        for i in range(n):
            qid = "DUP" if dup == rto and i > 0 else f"0{i}"  # leading zero must survive byte-for-byte
            rw.writerow([qid, rto, "Some Substation, 345 kV", "Active", "Proj"])
            ew.writerow([qid, rto, "NY", "Kings", "unreadable" if bad_mw == rto and i == 0 else mw,
                         "Dev, Inc.", "Developer Not Disclosed", "Genuinely Ambiguous / Unclassified Large Load",
                         "100", "1e26", "True"])
    return raw.getvalue(), enr.getvalue()


def run_selftest() -> bool:
    passed = failed = 0

    def check(name: str, ok: bool, detail: str = "") -> None:
        nonlocal passed, failed
        if ok:
            passed += 1
            print(f"  [PASS] {name}")
        else:
            failed += 1
            print(f"  [FAIL] {name}" + (f" -- {detail}" if detail else ""))

    check("large PJM shrink accepted when source health explains it",
          shrink_is_explainable("PJM", 281, 37, {
              "PJM": {
                  "rows_fetched": 9263,
                  "excluded_by_status": 8,
                  "excluded_status_values": {
                      "Withdrawn": 3, "In Service": 2, "Retracted": 1,
                      "Deactivated": 1, "Suspended": 1,
                  },
                  "fetch_errors": [],
              }
          }))
    check("large PJM shrink rejected with an unknown status",
          not shrink_is_explainable("PJM", 281, 37, {
              "PJM": {
                  "rows_fetched": 9263,
                  "excluded_by_status": 9,
                  "excluded_status_values": {
                      "Withdrawn": 8, "Brand New Status": 1,
                  },
                  "fetch_errors": [],
              }
          }))
    check("large PJM shrink rejected when raw feed is too small",
          not shrink_is_explainable("PJM", 281, 37, {
              "PJM": {
                  "rows_fetched": 500,
                  "excluded_by_status": 8,
                  "excluded_status_values": {"Withdrawn": 8},
                  "fetch_errors": [],
              }
          }))

    current = {"MISO": (10, 100.0), "SPP": (10, 100.0), "CAISO": (10, 100.0), "NYISO": (10, 100.0),
               "ISO-NE": (10, 100.0), "IESO": (3, 100.0), "PJM": (10, 100.0), "AESO": (10, 100.0)}
    fresh = {"MISO": (9, 100.0),        # -10%: fine
             "SPP": (4, 100.0),         # 40% of the rows: rejected
             "CAISO": (25, 100.0),      # 250% of the rows: rejected
             "ISO-NE": (10, 8.0),       # rows fine, capacity collapsed to 8%: rejected
             "IESO": (1, 100.0),        # tiny baseline (3 rows): ratio test skipped
             "AESO": (10, 100.0),       # duplicate IDs (set below)
             "ERCOT": (5, 100.0),       # not in the registry yet: new
             "FOO": (2, 100.0)}         # unknown label: rejected   (NYISO and PJM are absent: unavailable)
    raw_t, enr_t = _tables(fresh, dup="AESO")
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "index.html").write_text(_html(current), encoding="utf-8")
        (d / "raw.csv").write_text(raw_t, encoding="utf-8")
        (d / "enr.csv").write_text(enr_t, encoding="utf-8")
        argv = ["--html", str(d / "index.html"), "--raw", str(d / "raw.csv"), "--enriched", str(d / "enr.csv"),
                "--out-raw", str(d / "out_raw.csv"), "--out-enriched", str(d / "out_enr.csv"),
                "--summary-md", str(d / "summary.md"), "--github-output", str(d / "gh_output")]
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(argv)
        out = {k: v for k, v in (line.split("=", 1) for line in (d / "gh_output").read_text().splitlines())}
        check("run completes with exit 0 when at least one RTO is accepted", rc == 0, buf.getvalue())
        check("in-range RTO accepted; brand-new RTO accepted as 'new'; tiny baseline skips the ratio test",
              out["accepted"] == "ERCOT,IESO,MISO", out["accepted"])
        check("row-count collapse, row-count spike, capacity collapse, unknown label and duplicate IDs are rejected",
              out["rejected"] == "AESO,CAISO,FOO,ISO-NE,SPP", out["rejected"])
        check("an RTO absent from the fresh output is 'unavailable', not rejected", out["unavailable"] == "NYISO,PJM", out["unavailable"])
        text = buf.getvalue()
        check("reasons are specific (ratios and both counts shown)",
              "10 -> 4 (40% of current" in text and "10 -> 25 (250% of current" in text and "capacity 1.0 -> 0.1 GW (8% of current" in text
              and "unknown rto_region label 'FOO'" in text and "duplicate queue_id" in text)
        out_enr = (d / "out_enr.csv").read_text().splitlines()
        rtos_out = {line.split(",")[1] for line in out_enr[1:]}
        check("only accepted RTOs are written, in both files, header intact",
              rtos_out == {"ERCOT", "IESO", "MISO"} and out_enr[0].startswith("queue_id,rto_region")
              and {l.split(",")[1] for l in (d / "out_raw.csv").read_text().splitlines()[1:]} == {"ERCOT", "IESO", "MISO"})
        check("row counts survive: 9 MISO + 1 IESO + 5 ERCOT", len(out_enr) - 1 == 15)
        check("values are copied verbatim (queue ID '00' keeps its leading zero)", any(l.startswith("00,MISO,") for l in out_enr))
        md = (d / "summary.md").read_text()
        check("Markdown summary has a row per RTO", "| SPP |" in md and "| PJM |" in md and md.startswith("### Registry refresh gate"))

        # nothing acceptable -> exit 3 and no output written
        raw2, enr2 = _tables({"SPP": (2, 100.0)})
        (d / "raw2.csv").write_text(raw2, encoding="utf-8")
        (d / "enr2.csv").write_text(enr2, encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc3 = main(["--html", str(d / "index.html"), "--raw", str(d / "raw2.csv"), "--enriched", str(d / "enr2.csv"),
                        "--out-raw", str(d / "n_raw.csv"), "--out-enriched", str(d / "n_enr.csv")])
        check("nothing accepted -> exit 3 and no output files", rc3 == 3 and not (d / "n_raw.csv").exists())

        # header-only CSV (every feed failed / everything filtered out)
        (d / "hdr_raw.csv").write_text(",".join(RAW_REQUIRED) + "\n", encoding="utf-8")
        (d / "hdr_enr.csv").write_text(",".join(ENRICHED_REQUIRED) + "\n", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc4 = main(["--html", str(d / "index.html"), "--raw", str(d / "hdr_raw.csv"), "--enriched", str(d / "hdr_enr.csv"),
                        "--out-raw", str(d / "h_raw.csv"), "--out-enriched", str(d / "h_enr.csv")])
        check("header-only CSVs -> exit 3 (every RTO unavailable)", rc4 == 3)

        # raw CSV written without --include-raw-fields
        (d / "noraw.csv").write_text("queue_id,rto_region,state\n", encoding="utf-8")
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            rc5 = main(["--html", str(d / "index.html"), "--raw", str(d / "noraw.csv"), "--enriched", str(d / "enr.csv"),
                        "--out-raw", str(d / "x1.csv"), "--out-enriched", str(d / "x2.csv")])
        check("raw CSV lacking the extra columns -> exit 2 with the --include-raw-fields hint",
              rc5 == 2 and "--include-raw-fields" in err.getvalue())
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc6 = main(["--html", str(d / "missing.html"), "--raw", str(d / "raw.csv"), "--enriched", str(d / "enr.csv"),
                        "--out-raw", str(d / "y1.csv"), "--out-enriched", str(d / "y2.csv")])
        check("missing HTML -> exit 2", rc6 == 2)

        # thresholds are inclusive at the boundary
        boundary = decide({"MISO": (10, 100.0)}, list(RAW_REQUIRED), [[f"{i}", "MISO", "", "", ""] for i in range(5)],
                          list(ENRICHED_REQUIRED),
                          [[f"{i}", "MISO", "NY", "K", "20", "", "", "", "", "", ""] for i in range(5)])
        check("exactly 50% of the current rows and capacity is accepted (bounds are inclusive)",
              boundary[0].outcome == "accepted", str(boundary[0]))
        mism = decide({"MISO": (10, 100.0)}, list(RAW_REQUIRED), [[f"{i}", "MISO", "", "", ""] for i in range(8)],
                      list(ENRICHED_REQUIRED),
                      [[f"{i}", "MISO", "NY", "K", "100", "", "", "", "", "", ""] for i in range(9)])
        check("raw and enriched CSVs that disagree on an RTO's queue IDs are rejected (embed would abort)",
              mism[0].outcome == "rejected" and "disagree" in mism[0].reason, str(mism[0]))
        hostile = "EVIL\naccepted=PJM"
        h_raw, h_enr = _tables({hostile: (1, 100.0), "MISO": (10, 100.0)})
        (d / "h_raw.csv").write_text(h_raw, encoding="utf-8")
        (d / "h_enr.csv").write_text(h_enr, encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc7 = main(["--html", str(d / "index.html"), "--raw", str(d / "h_raw.csv"), "--enriched", str(d / "h_enr.csv"),
                        "--out-raw", str(d / "h_out_raw.csv"), "--out-enriched", str(d / "h_out_enr.csv"),
                        "--github-output", str(d / "gh2")])
        gh2 = (d / "gh2").read_text().splitlines()
        check("a hostile RTO label cannot inject a GITHUB_OUTPUT line or a workflow command",
              rc7 == 0 and len(gh2) == 3 and gh2[0] == "accepted=MISO" and "EVIL?accepted?PJM" in gh2[1], str(gh2))
        newrto = decide({}, list(RAW_REQUIRED), [["1", "ERCOT", "", "", ""]], list(ENRICHED_REQUIRED),
                        [["1", "ERCOT", "TX", "K", "100", "", "", "", "", "", ""]], min_old_rows=0)
        check("--min-old-rows 0 does not divide by zero for an RTO that is new to the registry",
              newrto[0].outcome == "new", str(newrto[0]))
        check("registry_stats sums rows and MW per RTO", registry_stats(_html({"MISO": (3, 10.0)})) == {"MISO": (3, 30.0)})
    print()
    if failed:
        print(f"{failed} CHECK(S) FAILED ({passed} passed)")
        return False
    print(f"ALL CHECKS PASSED ({passed}/{passed})")
    return True


if __name__ == "__main__":
    sys.exit(main())
