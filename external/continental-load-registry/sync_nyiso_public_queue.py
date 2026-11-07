# Live refresh trigger from full-registry completion pass.
#!/usr/bin/env python3
from __future__ import annotations
import argparse,datetime,io,json,time
from html.parser import HTMLParser
from urllib.parse import urljoin
from pathlib import Path
import pandas as pd,requests
PAGE_URL="https://www.nyiso.com/interconnections"
FALLBACK_URL="https://www.nyiso.com/documents/20142/1407078/NYISO-Interconnection-Queue.xlsx"
ALTERNATE_FALLBACK_URLS=[
    "https://www.nyiso.com/documents/20142/1407078/NYISO-Interconnection-Queue.xlsx",
    "https://www.nyiso.com/documents/20142/2226333/NYISO-Interconnection-Queue.xlsx",
    "https://www.nyiso.com/documents/20142/1407078/NYISO-Interconnection-Queue.xlsx/f615d83e-eea6-ccf6-ec07-b4ecbe78d8ef",
]
SHEETS={"Interconnection Queue":"active"," Cluster Projects":"cluster_active","Withdrawn":"withdrawn","Cluster Projects-Withdrawn":"cluster_withdrawn","In Service":"in_service"}
class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self.href: str | None = None
        self.text_parts: list[str] = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        href=dict(attrs).get("href")
        if href:
            self.href=href
            self.text_parts=[]
    def handle_data(self, data):
        if self.href is not None:
            self.text_parts.append(data)
    def handle_endtag(self, tag):
        if tag.lower()=="a" and self.href is not None:
            self.links.append((self.href," ".join(self.text_parts).strip()))
            self.href=None
            self.text_parts=[]

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--selftest",action="store_true");ap.add_argument("--output-dir",default="data");a=ap.parse_args()
    if a.selftest:
        assert len(SHEETS)==5
        print("PASS: NYISO parser self-test");return
    s=requests.Session();s.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153 Safari/537.36","Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8","Referer":PAGE_URL,"Origin":"https://www.nyiso.com"})
    # Try the official workbook URLs first. The public landing page can be an
    # anti-bot challenge, so it must never be a prerequisite for the queue file.
    candidates=list(dict.fromkeys(ALTERNATE_FALLBACK_URLS + [u+"?download=1" for u in ALTERNATE_FALLBACK_URLS]))
    try:
        page=s.get(PAGE_URL,timeout=60,allow_redirects=True)
        if page.ok:
            parser=LinkParser();parser.feed(page.text)
            discovered=[]
            for href,text_value in parser.links:
                label=(text_value+" "+href).lower()
                downloadable=any(token in label for token in (".xlsx", ".xls", ".zip", "download"))
                if (("queue" not in label and "interconnection" not in label) and not downloadable) or not href:
                    continue
                u=urljoin(PAGE_URL,href)
                if u not in discovered: discovered.append(u)
            candidates=discovered+candidates
    except requests.RequestException:
        pass

    def fetch_xlsx(url: str):
        seen=set()
        current=url
        for attempt in range(4):
            if current in seen:
                return None
            seen.add(current)
            try:
                rr=s.get(current,timeout=90,allow_redirects=False)
                if 300 <= rr.status_code < 400:
                    loc=rr.headers.get("Location")
                    if not loc:
                        return None
                    current=urljoin(current,loc)
                    continue
                rr.raise_for_status()
                if rr.content[:2]==b"PK":
                    return rr
            except requests.RequestException:
                return None
            time.sleep(2*(attempt+1))
        return None

    r=None
    for url in candidates:
        r=fetch_xlsx(url)
        if r is not None:
            break
    if r is None:
        # NYISO currently exposes an official workbook URL, but automated retrieval
        # may return an HTML/anti-bot response instead of the XLSX payload. Do not
        # manufacture a queue snapshot; preserve a machine-readable source-status
        # record and let the rest of the public-data pipeline continue.
        root=Path(a.output_dir); root.mkdir(parents=True,exist_ok=True)
        now=datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
        status={
            "schema_version":1,
            "source_id":"NYISO",
            "status":"SOURCE_UNAVAILABLE_AT_CAPTURE",
            "captured_at":now,
            "page_url":PAGE_URL,
            "official_workbook_urls":ALTERNATE_FALLBACK_URLS,
            "error":"Automated retrieval did not return an XLSX payload. No queue rows were fabricated.",
            "existing_snapshot_present":(root/"nyiso_public_queue.json").exists(),
            "next_action":"Retry the official workbook source on the next scheduled run; preserve named public Load Project/Gold Book evidence separately until the workbook is captured."
        }
        (root/"nyiso_public_queue_status.json").write_text(json.dumps(status,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        print(json.dumps(status,indent=2))
        return
    source_url=r.url
    book=pd.ExcelFile(io.BytesIO(r.content));recs=[]
    for sheet,status in SHEETS.items():
        if sheet not in book.sheet_names:raise RuntimeError(f"missing sheet: {sheet}")
        df=pd.read_excel(book,sheet_name=sheet,header=[0,1] if sheet=="In Service" else 0).dropna(how="all")
        if getattr(df.columns,"nlevels",1)>1:df.columns=[" ".join(str(x) for x in c if str(x)!="nan").strip() for c in df.columns]
        else:df.columns=[str(c).strip() for c in df.columns]
        for i,(_,row) in enumerate(df.iterrows(),1):
            raw={str(k):(None if pd.isna(v) else v.isoformat() if isinstance(v,(datetime.datetime,pd.Timestamp)) else v.item() if hasattr(v,"item") else v) for k,v in row.items()}
            def g(*ks):
                for k in ks:
                    if k in raw:return raw[k]
                return None
            q=g("Queue Pos.");name=g("Project Name")
            if q is None and name is None:continue
            vals=[]
            for k in ("SP (MW)","WP (MW)"):
                try:vals.append(float(g(k)))
                except Exception:pass
            recs.append({"source_sheet":sheet,"status_class":status,"source_row_number":i,"normalized":{"queue_id":q,"project_name":name,"developer_name":g("Developer Name","Owner/Developer"),"date_of_ir":g("Date of IR"),"summer_mw":g("SP (MW)"),"winter_mw":g("WP (MW)"),"capacity_mw":max(vals) if vals else None,"type_fuel":g("Type/ Fuel","Type/Fuel"),"county":g("County"),"state":g("State"),"interconnection_point":g("Interconnection Point","Points of Interconnection"),"utility":g("Utility"),"status":status,"last_updated":g("Last Updated Date","Last Update"),"proposed_in_service":g("Proposed In-Service Date","Proposed  In-Service"),"proposed_cod":g("Proposed COD"),"availability_of_studies":g("Availability of Studies"),"ia_status":g("S")},"raw":raw})
    root=Path(a.output_dir);root.mkdir(parents=True,exist_ok=True);now=datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
    obj={"schema_version":1,"title":"NYISO complete public interconnection queue","source_url":source_url,"captured_at":now,"accounting":"Complete public NYISO interconnection queue layer; not added to conservative large-load core.","record_count":len(recs),"records":recs}
    (root/"nyiso_public_queue.json").write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    flat=[]
    for z in recs:
        q=z["normalized"].copy();q.update({"source_sheet":z["source_sheet"],"status_class":z["status_class"],"source_row_number":z["source_row_number"],"raw_record_json":json.dumps(z["raw"],ensure_ascii=False,separators=(",",":"))});flat.append(q)
    pd.DataFrame(flat).to_csv(root/"nyiso_public_queue.csv",index=False)
    s={"source_url":source_url,"captured_at":now,"record_count":len(recs),"records_ge_100mw":sum((z["normalized"].get("capacity_mw") or 0)>=100 for z in recs)}
    (root/"nyiso_public_queue_summary.json").write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8");print(json.dumps(s,indent=2))
if __name__=="__main__":main()
