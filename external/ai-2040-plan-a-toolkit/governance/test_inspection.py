from governance.inspection import *
def test_assignment_requires_independent_groups():
    ins=[Inspector("a","A","g1",frozenset({"site"})),Inspector("b","B","g2",frozenset({"site"}))]
    req=InspectionRequest("r","site","party",2,commit_seed("seed"))
    a=assign_inspectors(req,ins,"seed")
    assert validate_assignment(a,req,{x.inspector_id:x for x in ins})["status"]=="PASS"
def test_collocated_same_group_is_rejected():
    ins=[Inspector("a","A","g1",frozenset({"site"})),Inspector("b","B","g1",frozenset({"site"}))]
    req=InspectionRequest("r","site","party",2,commit_seed("seed"))
    try: assign_inspectors(req,ins,"seed")
    except ValueError: pass
    else: assert False
