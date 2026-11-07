#!/usr/bin/env python3
from __future__ import annotations
import csv, json
from datetime import datetime, timezone
from pathlib import Path
from acquire_physical_verification import geocode, process_site
ROOT=Path(__file__).resolve().parent
TARGETS=ROOT/'data/track3/ambiguous_case_physical_targets.json'
OBS=ROOT/'data/track3/ambiguous_case_physical_observations.json'
CSV=ROOT/'data/track3/ambiguous_case_physical_observations.csv'
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def save(p,o): p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def main():
    manifest=load(TARGETS); rows=[]; coords=[]
    for t in manifest['targets']:
        coord={'lat':t.get('latitude'),'lon':t.get('longitude'),'precision':t.get('coordinate_precision')}
        if coord['lat'] is None or coord['lon'] is None:
            country='United States' if t.get('state_province')=='NY' else 'Canada'
            hit=geocode(t['address'],t['project_name'],t.get('state_province'),country)
            if hit: coord.update(lat=hit['lat'],lon=hit['lon'],precision='address geocode',geocoder=hit.get('geocoder'),geocode_query=hit.get('geocode_query'))
            else: coord['status']='UNRESOLVED'
        coords.append({'case_id':t['case_id'],**coord})
        if coord.get('lat') is None or coord.get('lon') is None:
            rows.append({'case_id':t['case_id'],'queue_id':t['queue_id'],'project_name':t['project_name'],'status':'PHYSICAL_TARGET_UNRESOLVED','coordinate_precision':coord.get('precision')}); continue
        site={'epoch_id':t['case_id'],'normalized':{'name':t['project_name'],'address':t['address']}}
        for r in process_site(site,coord,2):
            r['case_id']=t['case_id']; r['queue_id']=t['queue_id']; rows.append(r)
    derived=[r for r in rows if r.get('status')=='INGESTED_DERIVED']
    save(OBS,{'schema_version':1,'generated_at_utc':datetime.now(timezone.utc).isoformat(),'case_count':len(manifest['targets']),'coordinate_records':coords,'observation_count':len(rows),'derived_observation_count':len(derived),'records':rows,'semantics':'Derived from public raw COG windows; physical observations are not proof of AI compute or facility operation.'})
    fields=['case_id','queue_id','project_name','modality','sensor','scene_id','observed_on','stac_item_url','source_collection','cloud_cover_pct','status','quality_flag','processing_version','latitude','longitude','coordinate_precision','metrics_json','error']
    with CSV.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for r in rows:
            row={k:r.get(k) for k in fields if k!='metrics_json'}; row['metrics_json']=json.dumps(r.get('metrics') or {},sort_keys=True); w.writerow(row)
    print(json.dumps({'cases':len(manifest['targets']),'derived_observations':len(derived),'by_case':{t['case_id']:sum(1 for r in derived if r.get('case_id')==t['case_id']) for t in manifest['targets']}},indent=2))
if __name__=='__main__': raise SystemExit(main())
