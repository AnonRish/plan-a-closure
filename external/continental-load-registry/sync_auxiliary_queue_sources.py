#!/usr/bin/env python3
"""Capture public queue/connection sources that do not yet have dedicated normalized adapters.

This is a raw-source ingestion layer:
- ERCOT GIS workbook: captured and, where parsing is available, normalized.
- ISO-NE external reports: HTML snapshot captured.
- IESO Application Status: HTML snapshot captured.
- AESO Connection Project List: XLSX snapshot captured.

Raw capture is explicitly distinct from successful site-level parsing.
"""
from __future__ import annotations
import hashlib,json,io
from datetime import datetime,timezone
from pathlib import Path
import requests,pandas as pd

ROOT=Path(__file__).resolve().parent; DATA=ROOT/"data"; OUT=DATA/"automation"/"auxiliary_sources"; NOW=datetime.now(timezone.utc).isoformat()
UA="continental-load-registry/auxiliary-source-capture"
TIMEOUT=90

SOURCES={
 "ERCOT-GIS":{"kind":"workbook_discovery","url":"https://www.ercot.com/mp/data-products/data-product-details?id=pg7-200-er","output":"ercot_gis_source.bin"},
 "ISO-NE":{"kind":"html","url":"https://irtt.iso-ne.com/reports/external","output":"iso_ne_public_queue.html"},
 "IESO":{"kind":"html","url":"https://ieso.ca/Sector-Participants/Connection-Process/Application-Status","output":"ieso_application_status.html"},
 "AESO":{"kind":"xlsx","url":"https://www.aeso.ca/assets/Uploads/project-reporting/September-2026-Project-List.xlsx","output":"aeso_connection_project_list.xlsx"},
}

def get(url):
    r=requests.get(url,headers={"User-Agent":UA,"Accept":"text/html,application/xhtml+xml,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,*/*"},timeout=TIMEOUT)
    r.raise_for_status()
    if not r.content: raise RuntimeError("empty response")
    return r

def capture_direct(sid,spec):
    r=get(spec["url"])
    path=OUT/spec["output"]; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(r.content)
    item={"source_id":sid,"url":spec["url"],"captured_at_utc":NOW,"http_status":r.status_code,"bytes":len(r.content),"sha256":hashlib.sha256(r.content).hexdigest(),"content_type":r.headers.get("Content-Type"),"status":"RAW_CAPTURED","path":str(path.relative_to(ROOT)).replace("\\","/")}
    if sid=="ISO-NE":
        try:
            tables=pd.read_html(io.StringIO(r.text))
            item["table_count"]=len(tables); item["table_row_counts"]=[len(t) for t in tables]
        except Exception as exc: item["table_parse_error"]=str(exc)
    elif sid=="IESO":
        try:
            tables=pd.read_html(io.StringIO(r.text))
            item["table_count"]=len(tables); item["table_row_counts"]=[len(t) for t in tables]
        except Exception as exc: item["table_parse_error"]=str(exc)
    elif sid=="AESO":
        try:
            sheets=pd.read_excel(io.BytesIO(r.content),sheet_name=None)
            item["sheet_names"]=list(sheets); item["sheet_row_counts"]={k:len(v) for k,v in sheets.items()}
            normalized=[]
            for name,df in sheets.items():
                normalized.append({"sheet":name,"columns":[str(x) for x in df.columns],"rows":len(df)})
            item["normalized_sheet_catalog"]=normalized
        except Exception as exc: item["parse_error"]=str(exc)
    return item

def capture_ercot():
    # Reuse the researched, source-specific discovery/HTTP logic.
    import ingest_grid_queues as g
    session=g.build_http_session()
    data=g.fetch_ercot_gis_workbook(session)
    path=OUT/SOURCES["ERCOT-GIS"]["output"]; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
    return {"source_id":"ERCOT-GIS","url":SOURCES["ERCOT-GIS"]["url"],"captured_at_utc":NOW,"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest(),"status":"RAW_CAPTURED","path":str(path.relative_to(ROOT)).replace("\\","/"),"discovery_method":"ingest_grid_queues.fetch_ercot_gis_workbook"}

def json_value(v):
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass
    if isinstance(v, (datetime,)):
        return v.isoformat()
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    if hasattr(v, "item"):
        try:
            return v.item()
        except Exception:
            pass
    return v

def flatten_dataframe(df, source_sheet=None):
    columns=[str(x).strip() for x in df.columns]
    rows=[]
    for row_num,(_,row) in enumerate(df.iterrows(),1):
        raw={columns[i]:json_value(row.iloc[i]) for i in range(len(columns))}
        if all(v is None or str(v).strip()=="" for v in raw.values()):
            continue
        rows.append({"source_sheet":source_sheet,"source_row_number":row_num,"raw":raw,"normalized":raw})
    return rows

def build_normalized_auxiliary_artifacts(capture_manifest):
    outputs=[]
    for item in capture_manifest:
        sid=item.get("source_id")
        if item.get("status")!="RAW_CAPTURED":
            continue
        source_path=ROOT/item["path"]
        if not source_path.exists():
            continue
        captured=item.get("captured_at_utc")
        if sid=="ERCOT-GIS":
            try:
                import ingest_grid_queues as g
                raw=source_path.read_bytes()
                df=g.parse_workbook_sheets_dynamically(
                    raw,
                    g.ERCOT_COLUMN_ALIASES,
                    g.ERCOT_HEADER_SIGNAL_ALIASES,
                    sheet_name_exclude_keywords=g.ERCOT_EXCLUDE_SHEET_KEYWORDS,
                )
                all_rows=[]
                for sheet,frame in df.groupby("_source_sheet",dropna=False):
                    all_rows.extend(flatten_dataframe(frame.drop(columns=["_source_sheet"]), str(sheet)))
                stats=g.SourceStats("ERCOT-GIS")
                candidates=g.normalize_ercot_records(df,stats)
                base={"schema_version":1,"title":"ERCOT GIS public report — complete parsed rows","source_url":SOURCES["ERCOT-GIS"]["url"],"captured_at":captured,"record_count":len(all_rows),"rows":all_rows,"accounting":{"candidate_large_load_rows":len(candidates),"candidate_large_load_mw":round(sum(x["capacity_mw"] for x in candidates),2),"candidate_filter_min_mw":g.MIN_CAPACITY_MW},"semantics":"Complete parsed project-detail rows from the public GIS report. The candidate subset applies the registry's large-load filter; it is not the entire ERCOT generation universe."}
                cand={"schema_version":1,"title":"ERCOT GIS large-load candidate layer","source_url":SOURCES["ERCOT-GIS"]["url"],"captured_at":captured,"record_count":len(candidates),"records":[r.model_dump() if hasattr(r,"model_dump") else r for r in candidates],"semantics":"Filtered candidate layer from the public GIS report. This does not assert that every candidate is an AI data center or that capacity is currently load."}
                (DATA/"ercot_gis_public_records.json").write_text(json.dumps(base,indent=2,ensure_ascii=False,default=json_value)+"\n",encoding="utf-8")
                (DATA/"ercot_large_load_candidates.json").write_text(json.dumps(cand,indent=2,ensure_ascii=False,default=json_value)+"\n",encoding="utf-8")
                outputs.extend([str((DATA/"ercot_gis_public_records.json").relative_to(ROOT)),str((DATA/"ercot_large_load_candidates.json").relative_to(ROOT))])
            except Exception as exc:
                item["normalization_error"]=str(exc)
        elif sid in {"ISO-NE","IESO"}:
            try:
                html=source_path.read_text(encoding="utf-8",errors="replace")
                tables=pd.read_html(io.StringIO(html))
                rows=[]
                for table_idx,table in enumerate(tables):
                    rows.extend(flatten_dataframe(table, f"table_{table_idx+1}"))
                name="iso_ne_public_queue" if sid=="ISO-NE" else "ieso_public_connection_applications"
                title="ISO-NE public external reports — parsed tables" if sid=="ISO-NE" else "IESO public application status — parsed tables"
                obj={"schema_version":1,"title":title,"source_url":SOURCES[sid]["url"],"captured_at":captured,"record_count":len(rows),"table_count":len(tables),"rows":rows,"semantics":"Parsed public publisher tables retained row-by-row with source table and row numbers. Normalization is structural only; no site-level AI inference is made."}
                (DATA/f"{name}.json").write_text(json.dumps(obj,indent=2,ensure_ascii=False,default=json_value)+"\n",encoding="utf-8")
                outputs.append(str((DATA/f"{name}.json").relative_to(ROOT)))
            except Exception as exc:
                if sid=="IESO":
                    # Preserve the captured official HTML and publish an explicit parse-blocked
                    # envelope. This is a source-format limitation, not a zero-row claim.
                    name="ieso_public_connection_applications"
                    obj={
                        "schema_version":1,
                        "title":"IESO public application status — captured, parser blocked",
                        "source_url":SOURCES[sid]["url"],
                        "captured_at":captured,
                        "status":"PARSE_BLOCKED",
                        "record_count":0,
                        "rows":[],
                        "raw_capture":item.get("path"),
                        "parse_error":str(exc),
                        "semantics":"Official page captured successfully, but automated HTML-table extraction did not expose the application grid. Zero rows here means 'not parsed', not 'no applications'. Retry with a browser-rendered/API adapter before using row-level IESO application data."
                    }
                    (DATA/f"{name}.json").write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
                    item["normalization_status"]="PARSE_BLOCKED"
                    item["parse_blocked_error"]=str(exc)
                    outputs.append(str((DATA/f"{name}.json").relative_to(ROOT)))
                else:
                    item["normalization_error"]=str(exc)
        elif sid=="AESO":
            try:
                sheets=pd.read_excel(io.BytesIO(source_path.read_bytes()),sheet_name=None)
                rows=[]
                for sheet,table in sheets.items():
                    rows.extend(flatten_dataframe(table,str(sheet)))
                obj={"schema_version":1,"title":"AESO Connection Project List — complete parsed rows","source_url":SOURCES[sid]["url"],"captured_at":captured,"record_count":len(rows),"sheet_count":len(sheets),"rows":rows,"semantics":"Complete rows parsed from the public AESO connection-project workbook; source field names are preserved and no AI/load interpretation is imposed."}
                (DATA/"aeso_connection_projects.json").write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
                outputs.append(str((DATA/"aeso_connection_projects.json").relative_to(ROOT)))
            except Exception as exc:
                item["normalization_error"]=str(exc)
    return outputs


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    DATA.mkdir(parents=True,exist_ok=True)
    results=[]
    try: results.append(capture_ercot())
    except Exception as exc: results.append({"source_id":"ERCOT-GIS","status":"FAILED","error":str(exc),"url":SOURCES["ERCOT-GIS"]["url"],"captured_at_utc":NOW})
    for sid in ("ISO-NE","IESO","AESO"):
        try: results.append(capture_direct(sid,SOURCES[sid]))
        except Exception as exc: results.append({"source_id":sid,"status":"FAILED","error":str(exc),"url":SOURCES[sid]["url"],"captured_at_utc":NOW})
    normalized=build_normalized_auxiliary_artifacts(results)
    out={"schema_version":1,"generated_at_utc":NOW,"source_count":len(results),"failed_count":sum(x["status"]=="FAILED" for x in results),"normalized_artifacts":normalized,"sources":results}
    (OUT/"manifest.json").write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2))
    return 1 if out["failed_count"] else 0
if __name__=="__main__": raise SystemExit(main())
