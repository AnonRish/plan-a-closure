
from provenance.gate import *
def art(i,l,ind=False,raw=False): return EvidenceArtifact(i,l,"d","e",ind,raw)
def test_software_cannot_become_hardware_claim():
    c=Claim("tap",EvidenceLevel.BENCH_HARDWARE,("x",))
    assert can_promote(c,{"x":art("x",EvidenceLevel.SOFTWARE_TESTED)})["status"]=="UNKNOWN"
def test_hardware_requires_raw_data():
    c=Claim("tap",EvidenceLevel.BENCH_HARDWARE,("x",))
    assert can_promote(c,{"x":art("x",EvidenceLevel.BENCH_HARDWARE,raw=False)})["status"]=="UNKNOWN"
def test_independent_replication_can_promote():
    c=Claim("tap",EvidenceLevel.INDEPENDENT_REPLICATION,("x",))
    assert can_promote(c,{"x":art("x",EvidenceLevel.INDEPENDENT_REPLICATION,ind=True,raw=True)})["status"]=="PASS"
