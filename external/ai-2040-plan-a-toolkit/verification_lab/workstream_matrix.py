from __future__ import annotations
from .core import VALID_STATES
WORKSTREAMS=(
(1,'Passive optical taps','hardware','physical capture hardware + independent inspection'),
(2,'Recomputation server capture','hardware','measured capture/recomputation throughput'),
(3,'New tap types and bandwidth limits','hardware','multi-link capture results at target rates'),
(4,'Storage bank to inference units','hardware','isolated physical path evidence'),
(5,'Reproducible inference stack','software','reproducible runtime and model manifests'),
(6,'Network reproducibility','software','packet ordering/reassembly and loss accounting'),
(7,'Recomputation algorithms','software','independent recomputation validation'),
(8,'Frontier recomputation algorithms','research','model-family-specific frontier algorithms'),
(9,'Recomputation red-teaming','software','adversarial campaign with preregistered cases'),
(10,'Recomputation server security','hardware','attested boot + independent observation'),
(11,'Tap installation and monitoring','hardware','installation acceptance and tamper telemetry'),
(12,'Verification reporting','software','hash-chained reports + signed receipts'),
(13,'Physical security and audits','field','independent physical inspection evidence'),
(14,'Memory wipes','hardware','measured erase + challenge-bound verification'),
(15,'Side-channel mitigation','hardware','measured channel characterization'),
(16,'Side-channel wardens','field','independent continuous monitoring'),
(17,'Completeness invariants','international','closed population + independent external evidence'),
)

def build_matrix():
    entries=[]
    for wid,name,maturity,required in WORKSTREAMS:
        software='IMPLEMENTED' if wid in {5,6,7,9,12} else ('INTERFACE_AND_TESTBED' if wid in {1,2,4,10,11,14,15} else 'EVIDENCE_INTERFACE')
        entries.append({'id':wid,'name':name,'software_surface':software,'required_real_evidence':required,'physical_or_external_gate':maturity in {'hardware','field','international'},'promotion_rule':'No PASS promotion without evidence at the declared maturity level.'})
    return {'schema_version':1,'count':len(entries),'entries':entries,'unresolved_workstreams':[1,2,3,4,8,10,11,13,14,15,16,17],'valid_states':sorted(VALID_STATES),'global_statement':'RVP-1 software coverage is not equivalent to physical, field, or international completion.'}
