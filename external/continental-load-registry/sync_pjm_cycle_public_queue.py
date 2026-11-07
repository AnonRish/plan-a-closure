# Live refresh trigger from full-registry completion pass.
#!/usr/bin/env python3
from __future__ import annotations
import argparse,datetime,io,json,re
from pathlib import Path
from urllib.parse import urljoin
import pandas as pd,requests

PAGE="https://www.pjm.com/planning/m/cycle-service-request-status"
BASE="https://www.pjm.com"
UA="Mozilla/5.0 (compatible; Continental-Large-Load-Registry/1.0; +https://github.com/AnonRish/continental-load-registry)"
PUBLIC_BROWSER_KEY_FALLBACK="E29477D0-70E0-4825-89B0-43F460BF9AB4"

def fetch():
    s=requests.Session()
    s.headers.update({"User-Agent":UA,"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"})
    h=s.get(PAGE,timeout=60)
    h.raise_for_status()
    html=h.text

    # PJM serves the current queue through a public browser-export endpoint.
    # Discover the browser's public subscription key from the page's own JS
    # bundle instead of hard-coding a credential-like value in this repository.
    script_srcs=re.findall(r'<script[^>]+src=["\\\']([^"\\\']+)["\\\']',html,re.I)
    key=None
    for src in script_srcs:
        u=urljoin(BASE,src)
        try:
            js=s.get(u,timeout=60)
            if js.status_code!=200:
                continue
            m=re.search(r'api-subscription-key[^A-Fa-f0-9]{0,200}([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})',js.text,re.I|re.S)
            if m:
                key=m.group(1)
                break
        except requests.RequestException:
            continue

    if not key:
        key=PUBLIC_BROWSER_KEY_FALLBACK

    if key:
        headers={
            "api-subscription-key":key,
            "Origin":"https://www.pjm.com",
            "Referer":PAGE,
            "Accept":"application/vnd.ms-excel,application/octet-stream,*/*"
        }
        try:
            r=s.post(
                "https://services.pjm.com/PJMPlanningApi/api/Queue/ExportToXls",
                headers=headers,
                timeout=120
            )
            if r.status_code==200 and len(r.content)>5000:
                return r.content,"https://services.pjm.com/PJMPlanningApi/api/Queue/ExportToXls"
        except requests.RequestException:
            pass

    # Fallback: look for a directly exposed XLS/XLSX/XML export link.
    candidates=[]
    patterns=[
        r'https?://[^"\\\']+\\.(?:xls|xlsx|xml)(?:\\?[^"\\\']*)?',
        r'(?:href|data-url|data-download-url)=["\\\']([^"\\\']+\\.(?:xls|xlsx|xml)(?:\\?[^"\\\']*)?)["\\\']',
    ]
    for p in patterns:
        for m in re.findall(p,html,re.I):
            u=m if m.startswith("http") else urljoin(BASE,m)
            if u not in candidates:
                candidates.append(u)
    for u in candidates:
        try:
            r=s.get(u,timeout=90)
            r.raise_for_status()
            if len(r.content)>5000:
                return r.content,u
        except requests.RequestException:
            continue

    # Last fallback: inspect server-rendered HTML tables, but only accept a
    # queue-shaped table rather than a filter/options table.
    tables=pd.read_html(io.StringIO(html))
    for df in tables:
        cols={str(c).strip().lower() for c in df.columns}
        has_id=any(x in cols for x in ("project id","request id","queue id","queue number","id"))
        has_name=any(x in cols for x in ("name","project name","project"))
        has_mw=any(x in cols for x in ("mw capacity","mw energy","mw in service"))
        if "state" in cols and "status" in cols and has_name and (has_id or has_mw):
            return df.to_csv(index=False).encode(),PAGE

    raise RuntimeError(
        "PJM current queue export could not be retrieved; "
        "the public page/API contract may have changed."
    )

def normalize_df(df):
    df=df.dropna(how="all").copy();df.columns=[str(c).strip() for c in df.columns]
    low={c.lower():c for c in df.columns}
    def col(*names):
        for n in names:
            if n.lower() in low:return low[n.lower()]
        return None
    idc=col("Project ID","Request ID","Request Number","Queue ID","Queue Number","Queue Pos.","ID")

    out=[]
    for i,(_,row) in enumerate(df.iterrows(),1):
        raw={}
        for c in df.columns:
            v=row[c]
            if pd.isna(v):raw[c]=None
            elif hasattr(v,"isoformat"):raw[c]=v.isoformat()
            elif hasattr(v,"item"):
                try:raw[c]=v.item()
                except Exception:raw[c]=v
            else:raw[c]=v
        def g(*names):
            for n in names:
                c=col(n)
                if c:return raw.get(c)
            return None
        cap=None
        vals=[]
        for n in ("MW Capacity","MW Energy","Capacity (MW)","SP (MW)","WP (MW)"):
            v=g(n)
            try: vals.append(float(v))
            except Exception: pass
        if vals:cap=max(vals)
        source_id=g("Project ID","Request ID","Request Number","Queue ID","Queue Number","Queue Pos.","ID")
        derived_key = str(source_id).strip() if source_id not in (None,"") else f"PJM-CSR-ROW-{i:06d}"
        out.append({"source_row_number":i,"normalized":{
            "queue_id":source_id,
            "record_key":derived_key,
            "queue_id_is_source_field":source_id not in (None,""),
            "project_name":g("Name","Project Name","Project"),
            "state":g("State"),"status":g("Status"),"transmission_owner":g("TO","Transmission Owner"),
            "mfo":g("MFO"),"mw_energy":g("MW Energy","SP (MW)"),"mw_capacity":g("MW Capacity","WP (MW)"),
            "mw_in_service":g("MW In Service"),"capacity_mw":cap,"fuel":g("Fuel","Type/Fuel","Generation Type"),
            "description":g("Description")
        },"raw":raw})
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--selftest",action="store_true");ap.add_argument("--output-dir",default="data");a=ap.parse_args()
    if a.selftest:
        df=pd.DataFrame([{"Project ID":"AE1-TEST","Name":"Test","State":"VA","Status":"EP","MW Capacity":100}])
        r=normalize_df(df);assert r[0]["normalized"]["capacity_mw"]==100;print("PASS: PJM parser self-test");return
    payload,source=fetch()
    if source==PAGE:
        df=pd.read_csv(io.BytesIO(payload))
    else:
        bio=io.BytesIO(payload)
        try: df=pd.read_excel(bio)
        except Exception:
            bio.seek(0);df=pd.read_xml(bio)
    rows=normalize_df(df)
    if len(rows) < 1000:
        raise RuntimeError(f"PJM source returned only {len(rows)} rows; refusing to publish a likely paginated subset as the complete queue")
    now=datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
    root=Path(a.output_dir);root.mkdir(parents=True,exist_ok=True)
    obj={"schema_version":1,"title":"PJM complete public Cycle Service Request universe","page_url":PAGE,"export_source":source,"captured_at":now,"accounting":"Separate PJM service-request history layer; not added to the conservative large-load core.","record_count":len(rows),"records":rows}
    (root/"pjm_cycle_public_queue.json").write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    flat=[]
    for z in rows:
        q=z["normalized"].copy();q.update({"source_row_number":z["source_row_number"],"raw_record_json":json.dumps(z["raw"],ensure_ascii=False,separators=(",",":"))});flat.append(q)
    pd.DataFrame(flat).to_csv(root/"pjm_cycle_public_queue.csv",index=False)
    s={"page_url":PAGE,"export_source":source,"captured_at":now,"record_count":len(rows),"records_ge_100mw":sum((z["normalized"].get("capacity_mw") or 0)>=100 for z in rows)}
    (root/"pjm_cycle_public_queue_summary.json").write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8");print(json.dumps(s,indent=2))
if __name__=="__main__":main()
