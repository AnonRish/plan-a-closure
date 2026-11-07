from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict

@dataclass(frozen=True)
class Position:
    position_id:str; lot_id:str; owner_id:str; quantity:int; observed_at:int; evidence_refs:tuple[str,...]=()

@dataclass(frozen=True)
class Transfer:
    transfer_id:str; lot_id:str; src_owner:str; dst_owner:str; quantity:int; occurred_at:int; evidence_refs:tuple[str,...]=(); independence_group:str|None=None

@dataclass(frozen=True)
class Disposition:
    disposition_id:str; lot_id:str; owner_id:str; kind:str; quantity:int; occurred_at:int; evidence_refs:tuple[str,...]=()

TERMINAL_KINDS=frozenset({'DEPLOYED','RETIRED','DESTROYED'})

def validate_events(positions,transfers,dispositions):
    errors=[]
    for items,label,attr in ((positions,'position_id','position_id'),(transfers,'transfer_id','transfer_id'),(dispositions,'disposition_id','disposition_id')):
        ids=[getattr(x,attr) for x in items]
        if len(ids)!=len(set(ids)): errors.append(f'duplicate {label}')
    if any(x.quantity<0 for x in [*positions,*transfers,*dispositions]): errors.append('negative quantity')
    if any(x.src_owner==x.dst_owner for x in transfers): errors.append('self-transfer')
    if any(d.kind not in TERMINAL_KINDS for d in dispositions): errors.append('unknown disposition kind')
    return {'status':'PASS' if not errors else 'FAIL','errors':errors}

def reconcile(start_positions,transfers,end_positions,dispositions,closed_population):
    validation=validate_events(start_positions+end_positions,transfers,dispositions)
    if validation['status']=='FAIL': return validation
    start=defaultdict(int); end=defaultdict(int); incoming=defaultdict(int); outgoing=defaultdict(int)
    for p in start_positions: start[(p.lot_id,p.owner_id)]+=p.quantity
    for p in end_positions: end[(p.lot_id,p.owner_id)]+=p.quantity
    for t in transfers:
        incoming[(t.lot_id,t.dst_owner)]+=t.quantity; outgoing[(t.lot_id,t.src_owner)]+=t.quantity
    for d in dispositions: outgoing[(d.lot_id,d.owner_id)]+=d.quantity
    keys=sorted(set(start)|set(end)|set(incoming)|set(outgoing)); mismatches=[]
    for k in keys:
        lhs=start[k]+incoming[k]; rhs=end[k]+outgoing[k]
        if lhs!=rhs: mismatches.append({'lot_owner':k,'available':lhs,'resolved':rhs,'delta':lhs-rhs})
    missing=[]
    for x in [*start_positions,*end_positions,*transfers,*dispositions]:
        if not getattr(x,'evidence_refs',()): missing.append(getattr(x,'position_id',getattr(x,'transfer_id',getattr(x,'disposition_id',''))))
    status='FAIL' if mismatches else ('UNKNOWN' if not closed_population or missing else 'PASS')
    return {'status':status,'closed_population':closed_population,'mismatch_count':len(mismatches),'mismatches':mismatches,'missing_evidence':sorted(set(missing)),'lot_count':len({x.lot_id for x in [*start_positions,*end_positions,*transfers,*dispositions]}),'independence_groups':len({t.independence_group for t in transfers if t.independence_group})}

def trace_lot(lot_id,transfers,start_owners,terminal_dispositions):
    edges=[t for t in transfers if t.lot_id==lot_id and t.quantity>0]; owners=set(start_owners)
    for t in edges: owners.update((t.src_owner,t.dst_owner))
    unreachable=[o for o in sorted(owners-start_owners) if not any(o==t.dst_owner for t in edges)]
    terminals=[d for d in terminal_dispositions if d.lot_id==lot_id and d.quantity>0]
    return {'status':'PASS' if not unreachable else 'UNKNOWN','owners':sorted(owners),'unreachable_non_source_owners':unreachable,'terminal_dispositions':[d.disposition_id for d in terminals],'note':'Owner graph cycles are not treated as errors; legitimate resale can revisit an owner.'}
